# Maximize throughput & parallel requests

How to move large volumes of data into/out of Dataverse without tripping service
protection limits. Dataverse is built for concurrency, so parallel requests on
multiple threads beat sequential sends.

## Contents
- [Core strategy](#core-strategy)
- [Degree of parallelism (x-ms-dop-hint)](#degree-of-parallelism-x-ms-dop-hint)
- [Disable the affinity cookie](#disable-the-affinity-cookie)
- [Optimize the connection (.NET)](#optimize-the-connection-net)
- [Batch vs. parallel](#batch-vs-parallel)
- [Parallel code examples](#parallel-code-examples)

## Core strategy

1. **Let the server set the pace.** Don't precompute a request rate — every
   environment differs. Ramp up gradually until you start getting 429s, then obey
   `Retry-After`. Keeping the retry-after duration low maximizes total throughput
   and minimizes resource spikes. Continuing to hammer extends the duration.
2. **Use multiple threads** — the biggest throughput win when operations are quick.
3. **Disable the affinity cookie** so requests fan out across all web servers
   (each enforces limits independently → more headroom).
4. **Prefer many small requests over big batches.**

> Parallel execution is **not supported inside plug-ins or custom workflow
> activities** — only from external client applications.

## Degree of parallelism (x-ms-dop-hint)

There is no fixed optimal parallelism — allocated servers vary over time. Read
the recommended value from the environment instead of using CPU-core defaults
(which may be too high and over-send):

- Web API: `x-ms-dop-hint` response header (e.g. on a cheap `WhoAmI` call).
- SDK: `ServiceClient.RecommendedDegreesOfParallelism` /
  `CrmServiceClient.RecommendedDegreesOfParallelism`.

Pass it to `ParallelOptions.MaxDegreeOfParallelism`. If you respect this value
you should rarely hit the concurrent-request (52) limit; if you do, lower the
thread count.

## Disable the affinity cookie

Azure returns a cookie that pins subsequent requests to the same server. Good for
interactive/browser clients (server-side cache reuse; browsers can't disable it),
bad for parallel server-to-server work. Disabling spreads load and raises effective
limits.

**SDK (`ServiceClient` / `CrmServiceClient`)** — set the property, or via config:
```csharp
serviceClient.EnableAffinityCookie = false;
```
```xml
<!-- App.config <appSettings> -->
<add key="PreferConnectionAffinity" value="false" />
```
Also settable via the `ServiceClient(ConnectionOptions, bool, ConfigurationOptions)`
constructor and `ConfigurationOptions.EnableAffinityCookie`.

**Web API with `HttpClient`** — turn off cookies on the handler:
```csharp
HttpMessageHandler messageHandler = new OAuthMessageHandler(
    config, new HttpClientHandler() { UseCookies = false });
HttpClient httpClient = new HttpClient(messageHandler);
```
With dependency injection:
```csharp
services.AddHttpClient(name: "ClientName", configureClient: ConfigureHttpClientDelegate)
        .ConfigurePrimaryHttpMessageHandler(() => new HttpClientHandler { UseCookies = false });
```

## Optimize the connection (.NET)

When sending parallel requests, raise default .NET limits. `ServicePointManager`
applies to .NET Framework (and works with `HttpClient` there); on .NET Core, set
the equivalents on `HttpClient`/`HttpClientHandler`.

```csharp
// minWorkerThreads/minIOCP default to 4 — ramp connections faster
ThreadPool.SetMinThreads(100, 100);
// default remote connection limit is 2 — set >= intended concurrency
System.Net.ServicePointManager.DefaultConnectionLimit = 65000;
// don't wait for a 100-Continue round trip
System.Net.ServicePointManager.Expect100Continue = false;
// lowers transmission overhead, may delay packet arrival
System.Net.ServicePointManager.UseNagleAlgorithm = false;
```

- **`DefaultConnectionLimit`** — on .NET Core/`HttpClient`, controlled by
  `HttpClientHandler.MaxConnectionsPerServer` (default `int.MaxValue`).
- **`Expect100Continue`** — `HttpClient` default (`HttpRequestHeaders.ExpectContinue`)
  is already `false`.
- Hardware ultimately caps connections; setting values too high gets throttled elsewhere.

## Batch vs. parallel

- **Default to single requests with high parallelism** — usually fastest.
- **Batching** = multiple ops in one request. If trying it, start at batch size
  **10** and raise concurrency until you get (retried) 429s.
  - SDK: `ExecuteMultipleRequest`, typically up to **1,000** operations/request.
  - Main benefit: smaller total XML payload over the wire → helps when network
    latency is the bottleneck. With Web API's smaller JSON payloads, latency is
    rarely the issue.
  - Cost: larger batches raise per-request **execution time**, so you hit the
    execution-time limit sooner than the request-count limit.
- Batching does **not** bypass entitlement limits (counted per CRUD op regardless).

## Parallel code examples

### ServiceClient + .NET 6+ (`Parallel.ForEachAsync`)
```csharp
static async Task<Guid[]> CreateRecordsInParallel(
    ServiceClient serviceClient, List<Entity> entityList)
{
    ConcurrentBag<Guid> ids = new();
    serviceClient.EnableAffinityCookie = false;

    var parallelOptions = new ParallelOptions()
    { MaxDegreeOfParallelism = serviceClient.RecommendedDegreesOfParallelism };

    await Parallel.ForEachAsync(entityList, parallelOptions, async (entity, token) =>
    {
        ids.Add(await serviceClient.CreateAsync(entity, token));
    });
    return ids.ToArray();
}
```

### CrmServiceClient + .NET Framework (`Parallel.ForEach` with `Clone`)
Clone the client per thread; dispose each clone.
```csharp
static Guid[] CreateRecordsInParallel(
    CrmServiceClient crmServiceClient, List<Entity> entityList)
{
    ConcurrentBag<Guid> ids = new ConcurrentBag<Guid>();
    crmServiceClient.EnableAffinityCookie = false;

    Parallel.ForEach(entityList,
        new ParallelOptions() { MaxDegreeOfParallelism = crmServiceClient.RecommendedDegreesOfParallelism },
        () => crmServiceClient.Clone(),                      // thread-local clone
        (entity, loopState, index, threadLocalSvc) =>
        {
            ids.Add(threadLocalSvc.Create(entity));
            return threadLocalSvc;
        },
        (threadLocalSvc) => threadLocalSvc?.Dispose());      // dispose clone
    return ids.ToArray();
}
```

### Web API + HttpClient (read `x-ms-dop-hint` first)
```csharp
static async Task<Guid[]> CreateRecordsInParallel(HttpClient client, List<JObject> entityList)
{
    ConcurrentBag<Guid> ids = new ConcurrentBag<Guid>();

    HttpResponseMessage whoAmI = await client.SendAsync(
        new HttpRequestMessage(HttpMethod.Get, new Uri("WhoAmI", UriKind.Relative)));
    int dop = int.Parse(whoAmI.Headers.GetValues("x-ms-dop-hint").First());

    var parallelOptions = new ParallelOptions() { MaxDegreeOfParallelism = dop };

    await Parallel.ForEachAsync(entityList, parallelOptions, async (jObject, token) =>
    {
        var resp = await client.SendAsync(new HttpRequestMessage(HttpMethod.Post,
            new Uri("accounts", UriKind.Relative))
        { Content = new StringContent(jObject.ToString(), System.Text.Encoding.UTF8, "application/json") });

        string uri = resp.Headers.GetValues("OData-EntityId").First();
        int a = uri.LastIndexOf('(') + 1, b = uri.LastIndexOf(')');
        if (Guid.TryParse(uri[a..b], out Guid id)) ids.Add(id);
    });
    return ids.ToArray();
}
```

`ConcurrentBag<Guid>` is thread-safe but **unordered** — returned IDs won't match
input order. For non-.NET clients, wrap each send with
[../scripts/dataverse_retry.py](../scripts/dataverse_retry.py).

### See also (official samples)
- Web API WebApiService Parallel Operations Sample (C#)
- Web API Parallel Operations with TPL Dataflow components Sample (C#)
- Task Parallel Library with CrmServiceClient sample
