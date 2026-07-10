# Consumer Contract Tests

## Full Test Scaffolding

### Project Setup

```xml
<!-- MyApp.Consumer.Pact.csproj -->
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <IsPackable>false</IsPackable>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="PactNet" Version="5.0.0" />
    <PackageReference Include="PactNet.Output.Xunit" Version="5.0.0" />
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.9.0" />
    <PackageReference Include="xunit" Version="2.7.0" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.5.7" />
    <PackageReference Include="FluentAssertions" Version="6.12.0" />
  </ItemGroup>

  <ItemGroup>
    <ProjectReference Include="..\..\src\MyApp.Consumer\MyApp.Consumer.csproj" />
  </ItemGroup>
</Project>
```

### Base Test Class

```csharp
using PactNet;
using PactNet.Output.Xunit;
using Xunit.Abstractions;

namespace MyApp.Consumer.Pact;

public abstract class PactTestBase : IDisposable
{
    protected readonly IPactBuilderV4 PactBuilder;
    protected readonly ITestOutputHelper Output;

    protected PactTestBase(
        ITestOutputHelper output,
        string consumerName,
        string providerName)
    {
        Output = output;
        
        var config = new PactConfig
        {
            PactDir = GetPactDirectory(),
            Outputters = new[] { new XunitOutput(output) },
            LogLevel = PactLogLevel.Debug,
            DefaultJsonSettings = new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase
            }
        };

        PactBuilder = Pact.V4(consumerName, providerName, config)
            .WithHttpInteractions();
    }

    private static string GetPactDirectory()
    {
        // Navigate from bin/Debug/net8.0 to project root/pacts
        var baseDir = AppContext.BaseDirectory;
        return Path.GetFullPath(Path.Combine(baseDir, "..", "..", "..", "pacts"));
    }

    public void Dispose()
    {
        GC.SuppressFinalize(this);
    }
}
```

### Consumer Test Examples

```csharp
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using FluentAssertions;
using PactNet;
using PactNet.Output.Xunit;
using Xunit;
using Xunit.Abstractions;
using static PactNet.Matchers.Match;

namespace MyApp.Consumer.Pact.Consumers;

public class OrderServiceConsumerTests : PactTestBase
{
    public OrderServiceConsumerTests(ITestOutputHelper output) 
        : base(output, "OrderWebApp", "OrderGraphQLApi")
    {
    }

    [Fact]
    public async Task GetOrderById_WhenOrderExists_ReturnsOrder()
    {
        // Arrange
        var orderId = "order-123";
        var request = GraphQL.Query(
            @"query GetOrder($id: ID!) {
                order(id: $id) {
                    id
                    status
                    createdAt
                    customer { id name }
                    items { productId quantity unitPrice }
                }
            }",
            new { id = orderId });

        var expectedOrder = new
        {
            data = new
            {
                order = new
                {
                    id = orderId,
                    status = "PENDING",
                    createdAt = "2025-01-29T10:30:00Z",
                    customer = new { id = "cust-1", name = "John Doe" },
                    items = new[]
                    {
                        new { productId = "prod-1", quantity = 2, unitPrice = 29.99 }
                    }
                }
            }
        };

        PactBuilder
            .UponReceiving("a request to get order order-123")
            .WithRequest(HttpMethod.Post, "/graphql")
            .WithHeader("Content-Type", "application/json")
            .WithJsonBody(request)
            .WillRespond()
            .WithStatus(HttpStatusCode.OK)
            .WithHeader("Content-Type", "application/json")
            .WithJsonBody(expectedOrder);

        // Act & Assert
        await PactBuilder.VerifyAsync(async ctx =>
        {
            var client = CreateClient(ctx.MockServerUri);
            var order = await client.GetOrderAsync(orderId);

            order.Should().NotBeNull();
            order!.Id.Should().Be(orderId);
            order.Status.Should().Be("PENDING");
            order.Customer.Name.Should().Be("John Doe");
            order.Items.Should().HaveCount(1);
        });
    }

    [Fact]
    public async Task GetOrderById_WhenOrderNotFound_ReturnsNull()
    {
        var request = GraphQL.Query(
            @"query GetOrder($id: ID!) { order(id: $id) { id status } }",
            new { id = "nonexistent" });

        var response = new
        {
            data = new { order = (object?)null }
        };

        PactBuilder
            .UponReceiving("a request to get a non-existent order")
            .WithRequest(HttpMethod.Post, "/graphql")
            .WithHeader("Content-Type", "application/json")
            .WithJsonBody(request)
            .WillRespond()
            .WithStatus(HttpStatusCode.OK)
            .WithJsonBody(response);

        await PactBuilder.VerifyAsync(async ctx =>
        {
            var client = CreateClient(ctx.MockServerUri);
            var order = await client.GetOrderAsync("nonexistent");
            order.Should().BeNull();
        });
    }

    [Fact]
    public async Task CreateOrder_WithValidInput_ReturnsCreatedOrder()
    {
        var input = new CreateOrderInput
        {
            CustomerId = "cust-1",
            Items = new[]
            {
                new OrderItemInput { ProductId = "prod-1", Quantity = 2 }
            }
        };

        var request = GraphQL.Mutation(
            @"mutation CreateOrder($input: CreateOrderInput!) {
                createOrder(input: $input) {
                    id
                    status
                    total
                }
            }",
            new { input });

        PactBuilder
            .UponReceiving("a request to create a new order")
            .WithRequest(HttpMethod.Post, "/graphql")
            .WithHeader("Content-Type", "application/json")
            .WithJsonBody(request)
            .WillRespond()
            .WithStatus(HttpStatusCode.OK)
            .WithJsonBody(new
            {
                data = new
                {
                    createOrder = new
                    {
                        id = Type("order-456"),  // Any string
                        status = "PENDING",
                        total = Decimal(59.98m)
                    }
                }
            });

        await PactBuilder.VerifyAsync(async ctx =>
        {
            var client = CreateClient(ctx.MockServerUri);
            var order = await client.CreateOrderAsync(input);

            order.Should().NotBeNull();
            order!.Status.Should().Be("PENDING");
            order.Total.Should().Be(59.98m);
        });
    }

    [Fact]
    public async Task CreateOrder_WithInvalidInput_ReturnsErrors()
    {
        var input = new CreateOrderInput
        {
            CustomerId = "",  // Invalid
            Items = Array.Empty<OrderItemInput>()
        };

        var request = GraphQL.Mutation(
            @"mutation CreateOrder($input: CreateOrderInput!) {
                createOrder(input: $input) { id }
            }",
            new { input });

        PactBuilder
            .UponReceiving("a request to create order with invalid input")
            .WithRequest(HttpMethod.Post, "/graphql")
            .WithHeader("Content-Type", "application/json")
            .WithJsonBody(request)
            .WillRespond()
            .WithStatus(HttpStatusCode.OK)
            .WithJsonBody(new
            {
                data = new { createOrder = (object?)null },
                errors = EachLike(new
                {
                    message = Type("Customer ID is required"),
                    extensions = new { code = "VALIDATION_ERROR" }
                })
            });

        await PactBuilder.VerifyAsync(async ctx =>
        {
            var client = CreateClient(ctx.MockServerUri);
            var result = await client.CreateOrderRawAsync(input);

            result.Errors.Should().NotBeEmpty();
            result.Errors![0].Extensions!["code"].Should().Be("VALIDATION_ERROR");
        });
    }

    [Fact]
    public async Task GetOrders_WithPagination_ReturnsPage()
    {
        var request = GraphQL.Query(
            @"query GetOrders($first: Int!, $after: String) {
                orders(first: $first, after: $after) {
                    edges { node { id status } cursor }
                    pageInfo { hasNextPage endCursor }
                }
            }",
            new { first = 10, after = (string?)null });

        PactBuilder
            .UponReceiving("a request to get first page of orders")
            .WithRequest(HttpMethod.Post, "/graphql")
            .WithHeader("Content-Type", "application/json")
            .WithJsonBody(request)
            .WillRespond()
            .WithStatus(HttpStatusCode.OK)
            .WithJsonBody(new
            {
                data = new
                {
                    orders = new
                    {
                        edges = EachLike(new
                        {
                            node = new { id = Type("order-1"), status = Regex("PENDING|COMPLETED", "PENDING") },
                            cursor = Type("cursor-1")
                        }),
                        pageInfo = new
                        {
                            hasNextPage = Type(true),
                            endCursor = Type("cursor-10")
                        }
                    }
                }
            });

        await PactBuilder.VerifyAsync(async ctx =>
        {
            var client = CreateClient(ctx.MockServerUri);
            var page = await client.GetOrdersAsync(first: 10);

            page.Edges.Should().NotBeEmpty();
            page.PageInfo.HasNextPage.Should().BeTrue();
        });
    }

    private OrderServiceClient CreateClient(Uri baseUri)
    {
        var httpClient = new HttpClient { BaseAddress = baseUri };
        return new OrderServiceClient(httpClient);
    }
}
```

### GraphQL Helper

```csharp
namespace MyApp.Consumer.Pact;

public static class GraphQL
{
    public static object Query(string query, object? variables = null) => new
    {
        query = NormalizeQuery(query),
        variables
    };

    public static object Mutation(string mutation, object? variables = null) => new
    {
        query = NormalizeQuery(mutation),
        variables
    };

    private static string NormalizeQuery(string query)
    {
        // Normalize whitespace for consistent matching
        return string.Join(" ", query.Split(default(char[]), StringSplitOptions.RemoveEmptyEntries));
    }
}
```

## Matching Rules

### Type Matchers

```csharp
using static PactNet.Matchers.Match;

// Match any string
Type("example")

// Match any integer
Integer(42)

// Match any decimal
Decimal(99.99m)

// Match any boolean
Type(true)

// Match null explicitly
Null()
```

### Collection Matchers

```csharp
// Array with at least one element matching shape
EachLike(new { id = Type("x"), name = Type("y") })

// Array with minimum count
MinType(new { id = Type("x") }, min: 2)

// Array with exact count
MaxType(new { id = Type("x") }, max: 5)
```

### String Matchers

```csharp
// Regex pattern
Regex(@"^[A-Z]{2}-\d{4}$", "AB-1234")

// Date/time formats
Regex(@"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", "2025-01-29T10:30:00Z")

// UUID
Regex(@"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", 
      "550e8400-e29b-41d4-a716-446655440000")

// Enum-like values
Regex("PENDING|PROCESSING|COMPLETED|CANCELLED", "PENDING")
```

## Provider States

Use provider states to set up test data on the provider side:

```csharp
PactBuilder
    .UponReceiving("a request to get order when order exists")
    .Given("an order with ID order-123 exists", new Dictionary<string, string>
    {
        ["orderId"] = "order-123",
        ["status"] = "PENDING"
    })
    .WithRequest(HttpMethod.Post, "/graphql")
    .WithJsonBody(request)
    .WillRespond()
    .WithStatus(HttpStatusCode.OK)
    .WithJsonBody(expectedResponse);
```

Multiple states:

```csharp
PactBuilder
    .UponReceiving("get order with customer details")
    .Given("an order with ID order-123 exists")
    .Given("customer cust-1 exists with name John Doe")
    .WithRequest(...)
```

## Handling GraphQL Errors

### Partial Errors (some fields fail)

```csharp
PactBuilder
    .UponReceiving("get order when inventory service is down")
    .Given("inventory service is unavailable")
    .WithRequest(HttpMethod.Post, "/graphql")
    .WithJsonBody(request)
    .WillRespond()
    .WithStatus(HttpStatusCode.OK)
    .WithJsonBody(new
    {
        data = new
        {
            order = new
            {
                id = "order-123",
                status = "PENDING",
                inventory = (object?)null  // Failed to resolve
            }
        },
        errors = new[]
        {
            new
            {
                message = Type("Failed to fetch inventory"),
                path = new[] { "order", "inventory" },
                extensions = new { code = "DOWNSTREAM_ERROR" }
            }
        }
    });
```

### Authorization Errors

```csharp
PactBuilder
    .UponReceiving("get admin data without admin role")
    .Given("user is authenticated but not admin")
    .WithRequest(HttpMethod.Post, "/graphql")
    .WithHeader("Authorization", "Bearer user-token")
    .WithJsonBody(GraphQL.Query("{ adminSettings { maxUsers } }"))
    .WillRespond()
    .WithStatus(HttpStatusCode.OK)
    .WithJsonBody(new
    {
        data = (object?)null,
        errors = new[]
        {
            new
            {
                message = Type("Not authorized"),
                extensions = new { code = "FORBIDDEN" }
            }
        }
    });
```

## Tips

1. **Normalize queries** — Whitespace differences break matching
2. **Use matchers** — Avoid brittle exact-value matching
3. **Test error cases** — GraphQL returns 200 with errors array
4. **Provider states** — Set up data scenarios, don't assume data exists
5. **One interaction per test** — Easier to debug failures
6. **Descriptive descriptions** — "a request to get order order-123" not "test 1"
