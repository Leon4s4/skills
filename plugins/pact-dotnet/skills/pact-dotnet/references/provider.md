# Provider Verification

## Full Test Scaffolding

### Project Setup

```xml
<!-- MyApp.Provider.Pact.csproj -->
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <IsPackable>false</IsPackable>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="PactNet" Version="5.0.0" />
    <PackageReference Include="PactNet.Output.Xunit" Version="5.0.0" />
    <PackageReference Include="Microsoft.AspNetCore.Mvc.Testing" Version="8.0.0" />
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.9.0" />
    <PackageReference Include="xunit" Version="2.7.0" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.5.7" />
  </ItemGroup>

  <ItemGroup>
    <ProjectReference Include="..\..\src\MyApp.Provider\MyApp.Provider.csproj" />
  </ItemGroup>
</Project>
```

### Basic Provider Verification

```csharp
using Microsoft.AspNetCore.Mvc.Testing;
using PactNet;
using PactNet.Output.Xunit;
using PactNet.Verifier;
using Xunit;
using Xunit.Abstractions;

namespace MyApp.Provider.Pact.Verification;

public class ProviderPactTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly WebApplicationFactory<Program> _factory;
    private readonly ITestOutputHelper _output;

    public ProviderPactTests(
        WebApplicationFactory<Program> factory,
        ITestOutputHelper output)
    {
        _factory = factory;
        _output = output;
    }

    [Fact]
    public void VerifyOrderServicePacts()
    {
        var config = new PactVerifierConfig
        {
            Outputters = new[] { new XunitOutput(_output) },
            LogLevel = PactLogLevel.Debug
        };

        // Start the test server
        var client = _factory.CreateClient();
        var baseUri = client.BaseAddress!;

        using var verifier = new PactVerifier("OrderGraphQLApi", config);

        verifier
            .WithHttpEndpoint(baseUri)
            .WithPactBrokerSource(new Uri("https://your-broker.pactflow.io"), options =>
            {
                options.TokenAuthentication(Environment.GetEnvironmentVariable("PACT_BROKER_TOKEN")!);
                options.PublishResults(
                    Environment.GetEnvironmentVariable("GIT_COMMIT") ?? "local",
                    options => options.ProviderBranch(
                        Environment.GetEnvironmentVariable("GIT_BRANCH") ?? "local"));
                options.EnablePending();
                options.ConsumerVersionSelectors(
                    new ConsumerVersionSelector { MainBranch = true },
                    new ConsumerVersionSelector { DeployedOrReleased = true }
                );
            })
            .WithProviderStateUrl(new Uri(baseUri, "/_pact/provider-states"))
            .Verify();
    }
}
```

### Verify from Local Pact Files

```csharp
[Fact]
public void VerifyLocalPacts()
{
    var config = new PactVerifierConfig
    {
        Outputters = new[] { new XunitOutput(_output) }
    };

    var client = _factory.CreateClient();

    using var verifier = new PactVerifier("OrderGraphQLApi", config);

    verifier
        .WithHttpEndpoint(client.BaseAddress!)
        .WithDirectorySource(new DirectoryInfo(
            Path.Combine("..", "..", "..", "..", "MyApp.Consumer.Pact", "pacts")))
        .WithProviderStateUrl(new Uri(client.BaseAddress!, "/_pact/provider-states"))
        .Verify();
}
```

## Provider States Handler

Provider states let consumers specify test data scenarios. The provider must handle these.

### Provider State Endpoint

```csharp
// In Program.cs or Startup.cs - only for test environment
if (app.Environment.IsDevelopment() || app.Environment.IsEnvironment("PactVerification"))
{
    app.MapPost("/_pact/provider-states", async (HttpContext context) =>
    {
        var request = await context.Request.ReadFromJsonAsync<ProviderStateRequest>();
        
        var handler = context.RequestServices.GetRequiredService<IProviderStateHandler>();
        await handler.HandleAsync(request!);
        
        return Results.Ok();
    });
}

public record ProviderStateRequest(
    string State,
    Dictionary<string, object>? Params,
    string Action  // "setup" or "teardown"
);
```

### Provider State Handler

```csharp
public interface IProviderStateHandler
{
    Task HandleAsync(ProviderStateRequest request);
}

public class ProviderStateHandler : IProviderStateHandler
{
    private readonly AppDbContext _db;
    private readonly Dictionary<string, Func<Dictionary<string, object>?, Task>> _handlers;

    public ProviderStateHandler(AppDbContext db)
    {
        _db = db;
        _handlers = new Dictionary<string, Func<Dictionary<string, object>?, Task>>
        {
            ["an order with ID order-123 exists"] = SetupOrder,
            ["customer cust-1 exists with name John Doe"] = SetupCustomer,
            ["no orders exist"] = ClearOrders,
            ["inventory service is unavailable"] = SetupInventoryUnavailable,
        };
    }

    public async Task HandleAsync(ProviderStateRequest request)
    {
        if (request.Action == "teardown")
        {
            // Optional: clean up after each interaction
            return;
        }

        if (_handlers.TryGetValue(request.State, out var handler))
        {
            await handler(request.Params);
        }
        else
        {
            throw new InvalidOperationException($"Unknown provider state: {request.State}");
        }
    }

    private async Task SetupOrder(Dictionary<string, object>? parameters)
    {
        var orderId = parameters?["orderId"]?.ToString() ?? "order-123";
        var status = parameters?["status"]?.ToString() ?? "PENDING";

        // Clear existing and create test data
        _db.Orders.RemoveRange(_db.Orders.Where(o => o.Id == orderId));
        
        _db.Orders.Add(new Order
        {
            Id = orderId,
            Status = Enum.Parse<OrderStatus>(status),
            CustomerId = "cust-1",
            CreatedAt = DateTime.UtcNow,
            Items = new List<OrderItem>
            {
                new() { ProductId = "prod-1", Quantity = 2, UnitPrice = 29.99m }
            }
        });

        await _db.SaveChangesAsync();
    }

    private async Task SetupCustomer(Dictionary<string, object>? parameters)
    {
        var existing = await _db.Customers.FindAsync("cust-1");
        if (existing == null)
        {
            _db.Customers.Add(new Customer
            {
                Id = "cust-1",
                Name = "John Doe"
            });
            await _db.SaveChangesAsync();
        }
    }

    private async Task ClearOrders(Dictionary<string, object>? _)
    {
        _db.Orders.RemoveRange(_db.Orders);
        await _db.SaveChangesAsync();
    }

    private Task SetupInventoryUnavailable(Dictionary<string, object>? _)
    {
        // Set a flag or configure mock to simulate failure
        InventoryServiceMock.ShouldFail = true;
        return Task.CompletedTask;
    }
}
```

### Register in Test Startup

```csharp
public class PactWebApplicationFactory : WebApplicationFactory<Program>
{
    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("PactVerification");
        
        builder.ConfigureServices(services =>
        {
            // Use in-memory database for isolation
            services.RemoveAll<DbContextOptions<AppDbContext>>();
            services.AddDbContext<AppDbContext>(options =>
                options.UseInMemoryDatabase("PactVerification"));

            // Register provider state handler
            services.AddScoped<IProviderStateHandler, ProviderStateHandler>();
        });
    }
}

// Use in tests
public class ProviderPactTests : IClassFixture<PactWebApplicationFactory>
{
    private readonly PactWebApplicationFactory _factory;
    // ...
}
```

## Consumer Version Selectors

Control which pacts to verify:

```csharp
options.ConsumerVersionSelectors(
    // Always verify main branch
    new ConsumerVersionSelector { MainBranch = true },
    
    // Verify deployed/released versions
    new ConsumerVersionSelector { DeployedOrReleased = true },
    
    // Verify specific branch
    new ConsumerVersionSelector { Branch = "feature/new-api" },
    
    // Verify matching branch (same name as provider branch)
    new ConsumerVersionSelector { MatchingBranch = true },
    
    // Verify specific consumer
    new ConsumerVersionSelector { Consumer = "OrderWebApp", MainBranch = true }
);
```

### Recommended Selectors

```csharp
// For main/master branch builds
options.ConsumerVersionSelectors(
    new ConsumerVersionSelector { MainBranch = true },
    new ConsumerVersionSelector { DeployedOrReleased = true }
);

// For feature branch builds
options.ConsumerVersionSelectors(
    new ConsumerVersionSelector { MainBranch = true },
    new ConsumerVersionSelector { DeployedOrReleased = true },
    new ConsumerVersionSelector { MatchingBranch = true }  // Same branch name
);
```

## Pending Pacts

Pending pacts allow new consumers to be added without breaking provider builds:

```csharp
options.EnablePending();
options.IncludeWipPactsSince(new DateTime(2025, 1, 1));
```

- **Pending**: New pact, verification failures don't fail the build
- **WIP (Work In Progress)**: Recently published, included for visibility

Once verified successfully, pacts are no longer pending.

## Request Filtering

Filter which interactions to verify:

```csharp
verifier
    .WithFilter(description: "a request to get order")  // Match description
    .WithFilter(providerState: "order exists")          // Match provider state
    .Verify();
```

## Verification in CI

```yaml
# GitHub Actions example
- name: Verify Pacts
  env:
    PACT_BROKER_TOKEN: ${{ secrets.PACT_BROKER_TOKEN }}
    GIT_COMMIT: ${{ github.sha }}
    GIT_BRANCH: ${{ github.ref_name }}
  run: dotnet test MyApp.Provider.Pact --filter "FullyQualifiedName~ProviderPactTests"
```

## Troubleshooting

### Common Failures

| Error | Cause | Fix |
|-------|-------|-----|
| "No pacts found" | Wrong broker URL or selectors | Check broker URL and consumer version selectors |
| "Provider state not found" | Missing handler | Add handler for the state |
| "Request mismatch" | Query/body doesn't match | Check GraphQL query normalization |
| "Missing field in response" | Schema changed | Update consumer or provider |

### Debug Logging

```csharp
var config = new PactVerifierConfig
{
    LogLevel = PactLogLevel.Trace,  // Maximum detail
    Outputters = new[] { new XunitOutput(_output) }
};
```

### Verify Single Interaction

```csharp
verifier
    .WithFilter(description: "a request to get order order-123")
    .Verify();
```
