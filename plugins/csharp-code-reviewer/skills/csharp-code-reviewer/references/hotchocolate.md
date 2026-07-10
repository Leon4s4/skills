# Hot Chocolate GraphQL Review Rules

## Resolver Patterns

### Critical Issues

#### N+1 Query Problem

```csharp
// ❌ Bad: N+1 - DB call per item
public class OrderType : ObjectType<Order>
{
    protected override void Configure(IObjectTypeDescriptor<Order> descriptor)
    {
        descriptor
            .Field("customer")
            .Resolve(ctx => 
            {
                var order = ctx.Parent<Order>();
                return ctx.Service<ICustomerService>().GetById(order.CustomerId); // Called N times!
            });
    }
}

// ✅ Good: Use DataLoader
public class OrderType : ObjectType<Order>
{
    protected override void Configure(IObjectTypeDescriptor<Order> descriptor)
    {
        descriptor
            .Field("customer")
            .Resolve(ctx => 
            {
                var order = ctx.Parent<Order>();
                return ctx.DataLoader<CustomerByIdDataLoader>().LoadAsync(order.CustomerId);
            });
    }
}
```

#### Missing Cancellation Token

```csharp
// ❌ Bad: No cancellation support
public async Task<Customer> GetCustomerAsync(Guid id)
{
    return await _dbContext.Customers.FindAsync(id);
}

// ✅ Good: Propagate cancellation
public async Task<Customer> GetCustomerAsync(
    Guid id,
    CancellationToken cancellationToken)
{
    return await _dbContext.Customers
        .FindAsync(new object[] { id }, cancellationToken);
}
```

#### Blocking Async Calls

```csharp
// ❌ Bad: Blocking the thread pool
public Customer GetCustomer(Guid id)
{
    return _customerService.GetByIdAsync(id).Result; // Deadlock risk!
}

// ❌ Bad: Also blocking
public Customer GetCustomer(Guid id)
{
    return _customerService.GetByIdAsync(id).GetAwaiter().GetResult();
}

// ✅ Good: Async all the way
public async Task<Customer> GetCustomerAsync(
    Guid id,
    CancellationToken cancellationToken)
{
    return await _customerService.GetByIdAsync(id, cancellationToken);
}
```

### Warning Issues

#### Service Locator Anti-Pattern

```csharp
// ❌ Bad: Service locator in resolver
descriptor.Field("orders")
    .Resolve(ctx => 
    {
        var service = ctx.Service<IOrderService>(); // Hidden dependency
        return service.GetOrders();
    });

// ✅ Good: Constructor injection with [Service] attribute
public class OrderResolver
{
    public async Task<IEnumerable<Order>> GetOrdersAsync(
        [Service] IOrderService orderService,
        CancellationToken cancellationToken)
    {
        return await orderService.GetOrdersAsync(cancellationToken);
    }
}
```

#### Missing Error Handling

```csharp
// ❌ Bad: Exceptions leak to client
public async Task<Order> CreateOrderAsync(CreateOrderInput input)
{
    return await _orderService.CreateAsync(input); // Raw exception if fails
}

// ✅ Good: GraphQL error handling
public async Task<OrderPayload> CreateOrderAsync(
    CreateOrderInput input,
    [Service] IOrderService orderService)
{
    try
    {
        var order = await orderService.CreateAsync(input);
        return new OrderPayload(order);
    }
    catch (ValidationException ex)
    {
        return new OrderPayload(
            new UserError(ex.Message, "VALIDATION_ERROR"));
    }
    catch (Exception ex)
    {
        // Log the exception
        return new OrderPayload(
            new UserError("An unexpected error occurred", "INTERNAL_ERROR"));
    }
}
```

#### Unbounded Queries

```csharp
// ❌ Bad: No pagination - could return millions
[UseProjection]
[UseFiltering]
[UseSorting]
public IQueryable<Order> GetOrders([Service] AppDbContext db)
{
    return db.Orders;
}

// ✅ Good: Enforce pagination
[UsePaging(MaxPageSize = 100, DefaultPageSize = 25)]
[UseProjection]
[UseFiltering]
[UseSorting]
public IQueryable<Order> GetOrders([Service] AppDbContext db)
{
    return db.Orders;
}
```

### Suggestions

#### Projection Optimization

```csharp
// ⚠️ Loads all columns
public IQueryable<Customer> GetCustomers([Service] AppDbContext db)
{
    return db.Customers;
}

// ✅ Better: Enable projection to select only requested fields
[UseProjection]
public IQueryable<Customer> GetCustomers([Service] AppDbContext db)
{
    return db.Customers;
}
```

#### Field Deprecation Pattern

```csharp
// ✅ Proper deprecation with migration path
public class CustomerType : ObjectType<Customer>
{
    protected override void Configure(IObjectTypeDescriptor<Customer> descriptor)
    {
        descriptor
            .Field(c => c.FullName)
            .Deprecated("Use 'displayName' instead. Will be removed in v3.0");
        
        descriptor
            .Field("displayName")
            .Resolve(ctx => ctx.Parent<Customer>().FullName);
    }
}
```

## DataLoader Best Practices

### Proper DataLoader Implementation

```csharp
// ✅ Correct DataLoader pattern
public class CustomerByIdDataLoader : BatchDataLoader<Guid, Customer>
{
    private readonly IDbContextFactory<AppDbContext> _dbContextFactory;

    public CustomerByIdDataLoader(
        IDbContextFactory<AppDbContext> dbContextFactory,
        IBatchScheduler batchScheduler,
        DataLoaderOptions? options = null)
        : base(batchScheduler, options)
    {
        _dbContextFactory = dbContextFactory;
    }

    protected override async Task<IReadOnlyDictionary<Guid, Customer>> LoadBatchAsync(
        IReadOnlyList<Guid> keys,
        CancellationToken cancellationToken)
    {
        await using var dbContext = await _dbContextFactory.CreateDbContextAsync(cancellationToken);
        
        return await dbContext.Customers
            .Where(c => keys.Contains(c.Id))
            .ToDictionaryAsync(c => c.Id, cancellationToken);
    }
}
```

### GroupedDataLoader for Collections

```csharp
// ✅ For one-to-many relationships
public class OrdersByCustomerIdDataLoader : GroupedDataLoader<Guid, Order>
{
    private readonly IDbContextFactory<AppDbContext> _dbContextFactory;

    public OrdersByCustomerIdDataLoader(
        IDbContextFactory<AppDbContext> dbContextFactory,
        IBatchScheduler batchScheduler,
        DataLoaderOptions? options = null)
        : base(batchScheduler, options)
    {
        _dbContextFactory = dbContextFactory;
    }

    protected override async Task<ILookup<Guid, Order>> LoadGroupedBatchAsync(
        IReadOnlyList<Guid> keys,
        CancellationToken cancellationToken)
    {
        await using var dbContext = await _dbContextFactory.CreateDbContextAsync(cancellationToken);
        
        var orders = await dbContext.Orders
            .Where(o => keys.Contains(o.CustomerId))
            .ToListAsync(cancellationToken);
            
        return orders.ToLookup(o => o.CustomerId);
    }
}
```

### DataLoader Anti-Patterns

```csharp
// ❌ Bad: Creating new DbContext per batch (connection exhaustion)
protected override async Task<IReadOnlyDictionary<Guid, Customer>> LoadBatchAsync(...)
{
    using var dbContext = new AppDbContext(); // Don't do this!
    // ...
}

// ❌ Bad: Not using IDbContextFactory (scoping issues)
public class CustomerByIdDataLoader : BatchDataLoader<Guid, Customer>
{
    private readonly AppDbContext _dbContext; // Wrong! DbContext is scoped
}

// ❌ Bad: Executing queries synchronously
protected override Task<IReadOnlyDictionary<Guid, Customer>> LoadBatchAsync(...)
{
    var customers = _dbContext.Customers.Where(...).ToDictionary(...); // Sync!
    return Task.FromResult(customers);
}
```

## Schema Design

### Input Types

```csharp
// ✅ Proper input type with validation
public class CreateOrderInput
{
    [GraphQLNonNullType]
    public Guid CustomerId { get; set; }
    
    [GraphQLNonNullType]
    public List<OrderLineInput> Lines { get; set; } = new();
    
    public string? Notes { get; set; }
}

public class OrderLineInput
{
    [GraphQLNonNullType]
    public Guid ProductId { get; set; }
    
    [GraphQLNonNullType]
    [Range(1, 1000)]
    public int Quantity { get; set; }
}
```

### Payload Types (Mutation Responses)

```csharp
// ✅ Union-based error handling
public class CreateOrderPayload
{
    public Order? Order { get; }
    public IReadOnlyList<UserError>? Errors { get; }
    
    public CreateOrderPayload(Order order)
    {
        Order = order;
    }
    
    public CreateOrderPayload(UserError error)
    {
        Errors = new[] { error };
    }
    
    public CreateOrderPayload(IReadOnlyList<UserError> errors)
    {
        Errors = errors;
    }
}

public class UserError
{
    public string Message { get; }
    public string Code { get; }
    
    public UserError(string message, string code)
    {
        Message = message;
        Code = code;
    }
}
```

### Nullability Conventions

```csharp
// ✅ Explicit nullability
public class CustomerType : ObjectType<Customer>
{
    protected override void Configure(IObjectTypeDescriptor<Customer> descriptor)
    {
        // Non-null - always has value
        descriptor.Field(c => c.Id).Type<NonNullType<UuidType>>();
        descriptor.Field(c => c.Name).Type<NonNullType<StringType>>();
        
        // Nullable - may be null
        descriptor.Field(c => c.Email).Type<StringType>();
        
        // Non-null list of non-null items
        descriptor.Field(c => c.Orders).Type<NonNullType<ListType<NonNullType<OrderType>>>>();
    }
}
```

## Authorization

```csharp
// ✅ Field-level authorization
public class QueryType : ObjectType
{
    protected override void Configure(IObjectTypeDescriptor descriptor)
    {
        descriptor
            .Field("adminData")
            .Authorize("AdminPolicy")
            .Resolve(ctx => /* ... */);
            
        descriptor
            .Field("userData")
            .Authorize() // Requires any authenticated user
            .Resolve(ctx => /* ... */);
    }
}

// ✅ Type-level authorization
[Authorize(Policy = "AdminPolicy")]
public class AdminQuery
{
    public IQueryable<AuditLog> GetAuditLogs([Service] AppDbContext db)
        => db.AuditLogs;
}
```

## Common Pitfalls Checklist

| Issue | Risk | Check |
|-------|------|-------|
| No DataLoader | N+1 queries, perf death | Every relationship must use DataLoader |
| Missing `CancellationToken` | Cannot cancel long ops | Propagate token through all async |
| `.Result` / `.Wait()` | Deadlocks | Always `await` |
| No pagination | Memory exhaustion | Use `[UsePaging]` |
| Raw exceptions | Leaks internals | Use typed errors/payloads |
| Unbounded filtering | DoS vector | Limit filter complexity |
| Missing authorization | Security hole | Check all sensitive fields |
| Sync DataLoader fetch | Thread starvation | Always use async |
