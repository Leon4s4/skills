# Dynamics 365 CRM Review Rules

## Plugin Development

### Critical Issues

#### Missing ITracingService

```csharp
// ❌ Bad: No tracing
public void Execute(IServiceProvider serviceProvider)
{
    var context = (IPluginExecutionContext)serviceProvider.GetService(typeof(IPluginExecutionContext));
    // No way to debug in production
}

// ✅ Good: Always get tracing service
public void Execute(IServiceProvider serviceProvider)
{
    var tracingService = (ITracingService)serviceProvider.GetService(typeof(ITracingService));
    var context = (IPluginExecutionContext)serviceProvider.GetService(typeof(IPluginExecutionContext));
    tracingService.Trace("Plugin started: {0}", context.MessageName);
}
```

#### Unsafe Target Entity Access

```csharp
// ❌ Bad: Assumes target exists and has attributes
var target = (Entity)context.InputParameters["Target"];
var name = target["name"].ToString();

// ✅ Good: Defensive checks
if (!context.InputParameters.Contains("Target") || 
    !(context.InputParameters["Target"] is Entity target))
{
    tracingService.Trace("Target not found");
    return;
}

if (target.Contains("name") && target["name"] != null)
{
    var name = target.GetAttributeValue<string>("name");
}
```

#### Missing Exception Handling

```csharp
// ❌ Bad: Unhandled exceptions
public void Execute(IServiceProvider serviceProvider)
{
    var service = GetOrganizationService(serviceProvider);
    service.Update(entity); // May throw
}

// ✅ Good: Proper exception handling
public void Execute(IServiceProvider serviceProvider)
{
    var tracingService = GetTracingService(serviceProvider);
    try
    {
        var service = GetOrganizationService(serviceProvider);
        service.Update(entity);
    }
    catch (FaultException<OrganizationServiceFault> ex)
    {
        tracingService.Trace("Org service error: {0}", ex.Detail.Message);
        throw new InvalidPluginExecutionException(
            $"Error updating record: {ex.Detail.Message}", ex);
    }
    catch (Exception ex)
    {
        tracingService.Trace("Unexpected error: {0}", ex.ToString());
        throw new InvalidPluginExecutionException(
            "An unexpected error occurred. Please contact support.", ex);
    }
}
```

### Warning Issues

#### Depth Check Missing (Infinite Loop Risk)

```csharp
// ❌ Bad: May trigger itself infinitely
public void Execute(IServiceProvider serviceProvider)
{
    var context = GetContext(serviceProvider);
    var service = GetOrganizationService(serviceProvider);
    service.Update(entity); // Triggers another Update
}

// ✅ Good: Check depth
public void Execute(IServiceProvider serviceProvider)
{
    var context = GetContext(serviceProvider);
    if (context.Depth > 1)
    {
        tracingService.Trace("Skipping: depth = {0}", context.Depth);
        return;
    }
    // Continue processing
}
```

#### Inefficient Query Patterns

```csharp
// ❌ Bad: RetrieveMultiple in loop
foreach (var id in accountIds)
{
    var account = service.Retrieve("account", id, new ColumnSet("name"));
}

// ✅ Good: Single query with IN condition
var query = new QueryExpression("account")
{
    ColumnSet = new ColumnSet("name"),
    Criteria = new FilterExpression
    {
        Conditions =
        {
            new ConditionExpression("accountid", ConditionOperator.In, accountIds.ToArray())
        }
    }
};
var accounts = service.RetrieveMultiple(query);
```

#### Using AllColumns

```csharp
// ❌ Bad: Retrieves all columns
var entity = service.Retrieve("account", id, new ColumnSet(true));

// ✅ Good: Specify needed columns only
var entity = service.Retrieve("account", id, new ColumnSet("name", "accountnumber"));
```

#### Late-Bound vs Early-Bound

```csharp
// ⚠️ Late-bound: Error-prone, no compile-time checks
entity["new_customfield"] = "value"; // Typo won't be caught

// ✅ Early-bound: Compile-time safety
account.new_CustomField = "value";
```

### Suggestions

#### ExecuteMultipleRequest for Bulk Operations

```csharp
// ❌ Inefficient: Individual calls
foreach (var entity in entities)
{
    service.Create(entity);
}

// ✅ Efficient: Batch with ExecuteMultiple
var request = new ExecuteMultipleRequest
{
    Requests = new OrganizationRequestCollection(),
    Settings = new ExecuteMultipleSettings
    {
        ContinueOnError = false,
        ReturnResponses = true
    }
};
foreach (var entity in entities)
{
    request.Requests.Add(new CreateRequest { Target = entity });
}
service.Execute(request);
```

#### Pre-Image / Post-Image Usage

```csharp
// ❌ Bad: Retrieving data already available in image
var oldValue = service.Retrieve("account", id, new ColumnSet("name"));

// ✅ Good: Use registered images
if (context.PreEntityImages.Contains("PreImage"))
{
    var preImage = context.PreEntityImages["PreImage"];
    var oldName = preImage.GetAttributeValue<string>("name");
}
```

## IOrganizationService Patterns

### Service Factory Usage

```csharp
// ❌ Bad: Using context user without consideration
var factory = (IOrganizationServiceFactory)serviceProvider.GetService(typeof(IOrganizationServiceFactory));
var service = factory.CreateOrganizationService(context.UserId);

// ✅ Good: Explicit choice with documentation
// Use null for SYSTEM context (bypasses security)
var systemService = factory.CreateOrganizationService(null);

// Use context.UserId to run as calling user (respects security)
var userService = factory.CreateOrganizationService(context.UserId);

// Use context.InitiatingUserId for the actual user (not impersonated)
var initiatingService = factory.CreateOrganizationService(context.InitiatingUserId);
```

### QueryExpression Best Practices

```csharp
// ✅ Good: Complete query with paging
var query = new QueryExpression("contact")
{
    ColumnSet = new ColumnSet("fullname", "emailaddress1"),
    Criteria = new FilterExpression(LogicalOperator.And)
    {
        Conditions =
        {
            new ConditionExpression("statecode", ConditionOperator.Equal, 0),
            new ConditionExpression("parentcustomerid", ConditionOperator.Equal, accountId)
        }
    },
    Orders = { new OrderExpression("fullname", OrderType.Ascending) },
    PageInfo = new PagingInfo
    {
        Count = 5000,
        PageNumber = 1,
        ReturnTotalRecordCount = true
    }
};

// Handle paging for large result sets
EntityCollection results;
do
{
    results = service.RetrieveMultiple(query);
    ProcessResults(results.Entities);
    query.PageInfo.PageNumber++;
    query.PageInfo.PagingCookie = results.PagingCookie;
} while (results.MoreRecords);
```

## Custom Workflow Activities

### Required Attributes

```csharp
// ✅ Proper workflow activity structure
public class CalculateDiscountActivity : CodeActivity
{
    [RequiredArgument]
    [Input("Original Price")]
    public InArgument<Money> OriginalPrice { get; set; }

    [Input("Discount Percentage")]
    [Default("0.1")]
    public InArgument<decimal> DiscountPercentage { get; set; }

    [Output("Discounted Price")]
    public OutArgument<Money> DiscountedPrice { get; set; }

    protected override void Execute(CodeActivityContext context)
    {
        var tracingService = context.GetExtension<ITracingService>();
        var workflowContext = context.GetExtension<IWorkflowContext>();
        
        // Implementation
    }
}
```

## Common Pitfalls Checklist

| Issue | Risk | Check |
|-------|------|-------|
| No `ITracingService` | Cannot debug in prod | Every plugin must get tracing |
| No depth check | Infinite loops | Check `context.Depth` |
| `ColumnSet(true)` | Performance | Specify columns explicitly |
| Queries in loops | N+1 problem | Use IN conditions or ExecuteMultiple |
| No null checks on attributes | NullReferenceException | Use `GetAttributeValue<T>()` |
| Throwing generic Exception | Poor UX | Use `InvalidPluginExecutionException` |
| Hardcoded GUIDs | Environment issues | Use configuration or queries |
| Missing transaction awareness | Data inconsistency | Understand plugin pipeline stages |
