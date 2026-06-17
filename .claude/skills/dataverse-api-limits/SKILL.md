---
name: dataverse-api-limits
description: |
  Handle Microsoft Dataverse / Power Apps service protection API limits and
  throttling, and connect to Dataverse from .NET. Use when calling the Dataverse
  Web API or SDK for .NET and you hit (or want to prevent) 429 Too Many Requests /
  OrganizationServiceFault errors (codes -2147015902, -2147015903, -2147015898);
  when writing retry logic that honors Retry-After; when maximizing throughput for
  bulk loads / ETL
  (parallel requests, x-ms-dop-hint degree of parallelism, disabling the affinity
  cookie, ExecuteMultiple/$batch sizing); when distinguishing service protection
  from daily entitlement limits; or when connecting with ServiceClient /
  CrmServiceClient (Microsoft.PowerPlatform.Dataverse.Client) via connection
  strings and auth types (OAuth, Certificate, ClientSecret). Triggers on "Dataverse
  429", "service protection limits", "Dataverse throttling", "Retry-After",
  "maximize Dataverse throughput", "connect to Dataverse", "ServiceClient",
  "Dataverse connection string".
---

# Dataverse service protection API limits

Dataverse (Power Apps, Power Automate, Dynamics 365) throttles clients that make
extraordinary API demands, to protect shared availability and performance. This
skill covers detecting, handling, and preventing those errors, and maximizing
bulk throughput.

## Two limit categories — don't confuse them

| | Service protection limits | Entitlement (Power Platform request) limits |
| --- | --- | --- |
| Window | 5-minute sliding | 24-hour |
| On exceed | Immediate `429` / fault | Occasional overages allowed; admin-managed |
| Owner | **Developer** handles retry | **Administrator** buys capacity add-ons |
| Counts | All external web-service requests | CRUD on table rows (incl. plug-ins, `$batch`) |

This skill is about **service protection limits**. Batching does **not** bypass
entitlement limits. Full comparison + FAQ: [references/error-codes-and-limits.md](references/error-codes-and-limits.md).

## When limits apply (and don't)

- Apply to **all external** Web API / SDK requests, **per authenticated user, per
  web server** (most environments have several servers; trials have one).
- Do **NOT** apply to requests originating inside plug-ins / custom workflow
  activities (sandbox, internal) — but their compute time is added to the
  triggering request's execution-time total.
- Do **NOT** apply to Dataverse Search (`/api/search`) — it has its own limit of
  **1 request/second/user**.
- **Application (service principal) users get the same limits** as everyone else.

## Connect with ServiceClient (.NET)

Prefer `ServiceClient` (NuGet `Microsoft.PowerPlatform.Dataverse.Client`) — it
implements `IOrganizationService` and **auto-handles 429s** (pauses for
`Retry-After`, then resends), so it's the easiest correct client. It replaces the
older `CrmServiceClient` and the deprecated `OrganizationServiceProxy`.

```csharp
using Microsoft.PowerPlatform.Dataverse.Client;
IOrganizationService service = new ServiceClient(
   "AuthType=ClientSecret;Url=https://yourorg.crm.dynamics.com;" +
   "ClientId={AppId};ClientSecret={Secret}");
```

Connection-string parameters, auth types per framework (OAuth / Certificate /
ClientSecret), connection-status checks, and `IOrganizationService` operations:
[references/serviceclient-connections.md](references/serviceclient-connections.md).

## Detect the error

- **Web API:** HTTP `429 Too Many Requests` with a `Retry-After` header (seconds).
- **SDK for .NET:** `OrganizationServiceFault` with a `Retry-After` `TimeSpan` in
  `ErrorDetails` and one of these codes:

| Facet | Error code | Hex |
| --- | --- | --- |
| Number of requests | `-2147015902` | `0x80072322` |
| Execution time | `-2147015903` | `0x80072321` |
| Concurrent requests | `-2147015898` | `0x80072326` |

Full messages, default limits (6,000 requests / 1,200 s execution / 52 concurrent
per server), and rate-limit headers: [references/error-codes-and-limits.md](references/error-codes-and-limits.md).

## Handle the error (retry)

Never surface the raw error to end users — it is not a user-facing message. Retry:

1. Read the wait time: `Retry-After` header (Web API, seconds) or
   `ErrorDetails["Retry-After"]` (SDK `TimeSpan`).
2. Wait that long, then resend. If no value is present, fall back to exponential
   backoff (`2^attempt` seconds).
3. **Interactive apps:** show "server is busy", block new submissions until the
   in-flight request completes; optionally let the user cancel.
4. **Non-interactive apps:** `await Task.Delay(duration)` (or equivalent), retry.

**Prefer built-in handling over hand-rolling:**
- .NET SDK: use `ServiceClient` (or `CrmServiceClient`). Since Xrm.Tooling
  9.0.2.16+ it auto-pauses and resends after `Retry-After`. Replace the
  deprecated `OrganizationServiceProxy` / `OrganizationWebProxyClient`.
- PowerShell: `Invoke-RestMethod -MaximumRetryCount <n>` retries 400–599/304 (so 429).

Hand-rolled C# (Polly):
```csharp
HttpPolicyExtensions
  .HandleTransientHttpError()
  .OrResult(r => r.StatusCode == HttpStatusCode.TooManyRequests)
  .WaitAndRetryAsync(
     retryCount: config.MaxRetries,
     sleepDurationProvider: (count, response, _) =>
     {
        var headers = response.Result.Headers;
        int seconds = headers.Contains("Retry-After")
           ? int.Parse(headers.GetValues("Retry-After").First())
           : (int)Math.Pow(2, count);            // fallback when header absent
        return TimeSpan.FromSeconds(seconds);
     },
     onRetryAsync: (_, _, _, _) => Task.CompletedTask);
```

For non-.NET clients (Python, etc.), use the ready wrapper
[scripts/dataverse_retry.py](scripts/dataverse_retry.py) — it honors `Retry-After`
with exponential-backoff fallback. Verify offline: `python scripts/dataverse_retry.py --self-test`.

## Maximize throughput (bulk / ETL)

1. **Let the server pace you.** Don't precompute a rate. Ramp up gradually until
   you get 429s, then obey `Retry-After`. Keeping retry-after low maximizes total
   throughput; continuing to hammer extends the wait.
2. **Parallelize; avoid big batches.** Single requests at high parallelism are
   usually fastest. If batching, start at ~10 ops. `ExecuteMultiple`/`$batch`
   allows up to 1,000 ops but raises per-request execution time → execution-time limit.
3. **Use the recommended degree of parallelism** — read `x-ms-dop-hint` /
   `ServiceClient.RecommendedDegreesOfParallelism`, pass to
   `ParallelOptions.MaxDegreeOfParallelism`. Don't trust CPU-core defaults.
4. **Disable the affinity cookie** for parallel server-to-server work so requests
   spread across all web servers (each has its own limit): `EnableAffinityCookie = false`
   / `HttpClientHandler.UseCookies = false`.
5. **Tune .NET connections:** `ThreadPool.SetMinThreads`, `DefaultConnectionLimit`,
   `Expect100Continue = false`, `UseNagleAlgorithm = false`.

Full guidance + parallel code examples: [references/throughput-and-parallelism.md](references/throughput-and-parallelism.md).

> Parallel execution is **not supported inside plug-ins / custom workflow activities**.

## Monitor (debugging only)

`x-ms-ratelimit-burst-remaining-xrm-requests` (remaining requests for the
connection) and `x-ms-ratelimit-time-remaining-xrm-requests` (remaining combined
execution time for the user). Do **not** drive client behavior from these — they
reset across servers when the affinity cookie is off.
