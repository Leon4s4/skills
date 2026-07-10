---
name: pact-dotnet
description: Build consumer and provider contract tests using PactNet 5.x for GraphQL APIs. Use this skill when creating Pact tests, generating consumer contracts, verifying provider implementations, setting up Pact Broker integration, or scaffolding contract test projects. Supports GraphQL query/mutation testing, xUnit integration, publishing contracts, verification workflows, and can-i-deploy checks. Explains Pact concepts and generates complete test scaffolding.
---

# Pact .NET Contract Testing

Build consumer-driven contract tests for GraphQL APIs using PactNet 5.x and xUnit. Covers consumer tests, provider verification, and Pact Broker workflows.

## Core Concepts

**Consumer**: Service that makes requests (calls the GraphQL API)
**Provider**: Service that fulfills requests (the GraphQL API)
**Contract (Pact)**: JSON file describing expected interactions
**Pact Broker**: Central repository for contracts + verification results

### Workflow

```
1. Consumer writes tests → generates pact JSON
2. Pact published to Broker
3. Provider verifies against pact
4. can-i-deploy checks compatibility before release
```

## References

- **Consumer tests**: See [references/consumer.md](references/consumer.md)
- **Provider verification**: See [references/provider.md](references/provider.md)
- **Pact Broker & CI/CD**: See [references/broker.md](references/broker.md)

## Quick Start

### 1. Install Packages

```bash
# Consumer project
dotnet add package PactNet --version 5.0.0
dotnet add package PactNet.Output.Xunit --version 5.0.0

# Provider project
dotnet add package PactNet --version 5.0.0
dotnet add package PactNet.Output.Xunit --version 5.0.0
dotnet add package Microsoft.AspNetCore.Mvc.Testing --version 8.0.0
```

### 2. Project Structure

```
src/
├── MyApp.Consumer/
├── MyApp.Provider/           # GraphQL API
tests/
├── MyApp.Consumer.Pact/      # Consumer contract tests
│   ├── Consumers/
│   │   └── OrderServiceConsumerTests.cs
│   └── pacts/                # Generated pact files
└── MyApp.Provider.Pact/      # Provider verification
    └── Verification/
        └── ProviderPactTests.cs
```

### 3. Consumer Test (GraphQL)

```csharp
public class OrderServiceConsumerTests : IDisposable
{
    private readonly IPactBuilderV4 _pactBuilder;

    public OrderServiceConsumerTests(ITestOutputHelper output)
    {
        var config = new PactConfig
        {
            PactDir = Path.Combine("..", "..", "..", "pacts"),
            Outputters = new[] { new XunitOutput(output) },
            LogLevel = PactLogLevel.Debug
        };

        _pactBuilder = Pact.V4("OrderConsumer", "OrderProvider", config).WithHttpInteractions();
    }

    [Fact]
    public async Task GetOrder_ReturnsOrder()
    {
        var graphqlRequest = new
        {
            query = @"query GetOrder($id: ID!) { order(id: $id) { id status } }",
            variables = new { id = "order-123" }
        };

        var expectedResponse = new
        {
            data = new
            {
                order = new { id = "order-123", status = "PENDING" }
            }
        };

        _pactBuilder
            .UponReceiving("a request to get order by ID")
            .WithRequest(HttpMethod.Post, "/graphql")
            .WithHeader("Content-Type", "application/json")
            .WithJsonBody(graphqlRequest)
            .WillRespond()
            .WithStatus(HttpStatusCode.OK)
            .WithJsonBody(expectedResponse);

        await _pactBuilder.VerifyAsync(async ctx =>
        {
            var client = new HttpClient { BaseAddress = ctx.MockServerUri };
            var response = await client.PostAsJsonAsync("/graphql", graphqlRequest);
            
            response.StatusCode.Should().Be(HttpStatusCode.OK);
            var result = await response.Content.ReadFromJsonAsync<JsonElement>();
            result.GetProperty("data").GetProperty("order").GetProperty("id")
                .GetString().Should().Be("order-123");
        });
    }

    public void Dispose()
    {
        // Pact file written on dispose
    }
}
```

### 4. Provider Verification

```csharp
public class ProviderPactTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly WebApplicationFactory<Program> _factory;
    private readonly ITestOutputHelper _output;

    public ProviderPactTests(WebApplicationFactory<Program> factory, ITestOutputHelper output)
    {
        _factory = factory;
        _output = output;
    }

    [Fact]
    public void VerifyPacts()
    {
        var config = new PactVerifierConfig
        {
            Outputters = new[] { new XunitOutput(_output) },
            LogLevel = PactLogLevel.Debug
        };

        using var server = _factory.Server;
        var verifier = new PactVerifier("OrderProvider", config);

        verifier
            .WithHttpEndpoint(server.BaseAddress)
            .WithPactBrokerSource(new Uri("https://your-broker.pactflow.io"), options =>
            {
                options.TokenAuthentication("your-token");
                options.PublishResults("1.0.0");
                options.ConsumerVersionSelectors(
                    new ConsumerVersionSelector { MainBranch = true },
                    new ConsumerVersionSelector { DeployedOrReleased = true }
                );
            })
            .Verify();
    }
}
```

## GraphQL-Specific Patterns

### Query with Variables

```csharp
var request = new
{
    query = @"
        query GetOrders($customerId: ID!, $status: OrderStatus) {
            orders(customerId: $customerId, status: $status) {
                id
                total
                items { productId quantity }
            }
        }",
    variables = new { customerId = "cust-1", status = "PENDING" }
};
```

### Mutations

```csharp
var request = new
{
    query = @"
        mutation CreateOrder($input: CreateOrderInput!) {
            createOrder(input: $input) {
                id
                status
            }
        }",
    variables = new
    {
        input = new
        {
            customerId = "cust-1",
            items = new[] { new { productId = "prod-1", quantity = 2 } }
        }
    }
};
```

### Matching Rules for Flexible Contracts

```csharp
using static PactNet.Matchers.Match;

_pactBuilder
    .UponReceiving("get orders")
    .WithRequest(HttpMethod.Post, "/graphql")
    .WithJsonBody(new
    {
        query = Type("string"),  // Match any string
        variables = new { customerId = Type("cust-1") }
    })
    .WillRespond()
    .WithStatus(HttpStatusCode.OK)
    .WithJsonBody(new
    {
        data = new
        {
            orders = EachLike(new  // Array with at least one item
            {
                id = Type("order-123"),
                total = Decimal(99.99m),
                status = Regex("PENDING|COMPLETED|CANCELLED", "PENDING")
            })
        }
    });
```

## When to Load References

| Task | Reference |
|------|-----------|
| Writing consumer tests | [consumer.md](references/consumer.md) |
| Provider verification setup | [provider.md](references/provider.md) |
| Pact Broker, CI/CD, can-i-deploy | [broker.md](references/broker.md) |
