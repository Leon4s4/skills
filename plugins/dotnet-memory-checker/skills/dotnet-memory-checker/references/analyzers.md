# Analyzer Packages & Rules Reference

## Recommended NuGet Packages

```xml
<ItemGroup>
  <!-- IDisposable deep analysis -->
  <PackageReference Include="IDisposableAnalyzers" Version="4.*">
    <PrivateAssets>all</PrivateAssets>
    <IncludeAssets>analyzers</IncludeAssets>
  </PackageReference>

  <!-- General quality + allocation awareness -->
  <PackageReference Include="Meziantou.Analyzer" Version="2.*">
    <PrivateAssets>all</PrivateAssets>
    <IncludeAssets>analyzers</IncludeAssets>
  </PackageReference>

  <!-- Broad .NET best practices -->
  <PackageReference Include="SonarAnalyzer.CSharp" Version="10.*">
    <PrivateAssets>all</PrivateAssets>
    <IncludeAssets>analyzers</IncludeAssets>
  </PackageReference>

  <!-- Hidden allocation detection -->
  <PackageReference Include="ClrHeapAllocationAnalyzer" Version="3.*">
    <PrivateAssets>all</PrivateAssets>
    <IncludeAssets>analyzers</IncludeAssets>
  </PackageReference>
</ItemGroup>
```

## Built-in .NET Analyzer Rules (Memory)

### Disposal Rules

| Rule | Name | Severity |
|------|------|----------|
| CA1001 | Types that own disposable fields should be disposable | Error |
| CA1063 | Implement IDisposable correctly | Error |
| CA1816 | Call GC.SuppressFinalize correctly | Warning |
| CA1821 | Remove empty finalizers | Warning |
| CA2000 | Dispose objects before losing scope | Warning |
| CA2213 | Disposable fields should be disposed | Warning |
| CA2215 | Dispose methods should call base class Dispose | Warning |
| CA2216 | Disposable types should declare finalizer | Warning |

### Performance/Allocation Rules

| Rule | Name | Severity |
|------|------|----------|
| CA1825 | Avoid zero-length array allocations | Info |
| CA1834 | Use StringBuilder.Append(char) | Info |
| CA1835 | Prefer Memory/Span overloads for Stream | Warning |
| CA1846 | Prefer AsSpan over Substring | Info |
| CA1850 | Prefer static HashData over ComputeHash | Info |
| CA1858 | Use StartsWith(char) instead of string | Info |

## .editorconfig Configuration

```ini
[*.cs]
# Disposal — high severity
dotnet_diagnostic.CA1001.severity = error
dotnet_diagnostic.CA1063.severity = error
dotnet_diagnostic.CA2000.severity = warning
dotnet_diagnostic.CA2213.severity = warning
dotnet_diagnostic.CA2215.severity = warning
dotnet_diagnostic.CA1816.severity = warning
dotnet_diagnostic.CA1821.severity = warning

# Performance
dotnet_diagnostic.CA1825.severity = suggestion
dotnet_diagnostic.CA1835.severity = warning
dotnet_diagnostic.CA1846.severity = suggestion
```

## IDisposableAnalyzers Rules

| Rule | Description |
|------|-------------|
| IDISP001 | Dispose created |
| IDISP002 | Dispose member |
| IDISP003 | Dispose previous before re-assigning |
| IDISP004 | Don't ignore created IDisposable |
| IDISP006 | Implement IDisposable |
| IDISP007 | Don't dispose injected |
| IDISP014 | Use a single instance of HttpClient |
| IDISP016 | Don't use disposed instance |
| IDISP017 | Prefer using |
| IDISP025 | Class with no virtual dispose should be sealed |

## SonarAnalyzer Rules (Memory)

| Rule | Description |
|------|-------------|
| S2930 | IDisposable should be implemented correctly |
| S2931 | Classes shouldn't have IDisposable members without implementing it |
| S2952 | Classes should dispose members they created |
| S3168 | async void methods should not be used |
| S3966 | Objects should not be disposed more than once |

## Meziantou Rules (Memory)

| Rule | Description |
|------|-------------|
| MA0029 | Combine LINQ methods (reduce intermediate allocations) |
| MA0066 | Use Array.Empty<T>() |
| MA0106 | Avoid closure allocations (use static lambda) |

## BenchmarkDotNet Memory Diagnoser

For measuring allocations in hot paths:

```csharp
[MemoryDiagnoser]
public class MyBenchmarks
{
    [Benchmark]
    public void Method() { /* ... */ }
}
// Shows: Gen0, Gen1, Gen2 collections, Allocated bytes per operation
```
