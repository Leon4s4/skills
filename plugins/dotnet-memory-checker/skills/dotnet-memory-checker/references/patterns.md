# Grep Patterns for .NET Memory Issues

All patterns target `.cs` files. Use Grep tool with `glob: "*.cs"` or `type: "cs"`.

## CRITICAL Severity

### CRIT-01: HttpClient instantiation (socket exhaustion + GC pressure)
```
pattern: new\s+HttpClient\s*\(
```
Skip if: inside `IHttpClientFactory`, static field, or `AddHttpClient()` registration.
Fix: Use `IHttpClientFactory` via DI or a static shared instance.

### CRIT-02: Static event handlers (permanent subscriber rooting)
```
pattern: static\s+.*event\s+
```
Fix: Avoid static events. Use a message bus, weak event pattern, or scoped event aggregator.

### CRIT-03: Undisposed SqlConnection/SqlCommand/DbConnection
```
pattern: new\s+(SqlConnection|SqlCommand|NpgsqlConnection|NpgsqlCommand|MySqlConnection|DbConnection|OleDbConnection|OdbcConnection)\s*\(
```
Skip if: preceded by `using` on same line or previous line.
Fix: Always wrap in `using` statement.

### CRIT-04: Undisposed Stream types
```
pattern: (?<!using\s.{0,30})new\s+(FileStream|MemoryStream|StreamReader|StreamWriter|BufferedStream|GZipStream|DeflateStream|BrotliStream|CryptoStream|NetworkStream|SslStream)\s*\(
```
Skip if: preceded by `using` on same line or wrapped in using block.
Fix: Wrap in `using var` or `using () {}`.

## HIGH Severity

### HIGH-01: Event subscription without unsubscription
```
pattern: \.\w+\s*\+=\s*
```
After finding: check if same class has a corresponding `-=` for the same event. Flag if no unsubscription found.
Fix: Unsubscribe in `Dispose()`, destructor, or cleanup method.

### HIGH-02: Unbounded static collections
```
pattern: static\s+(readonly\s+)?(List|Dictionary|HashSet|ConcurrentDictionary|ConcurrentBag|ConcurrentQueue|SortedList|SortedDictionary|SortedSet|LinkedList|BlockingCollection)<
```
After finding: check if `.Remove`, `.Clear`, `.TryRemove`, or size-limiting logic exists in the same file.
Fix: Use `IMemoryCache` with eviction, `ConditionalWeakTable`, or bounded collections.

### HIGH-03: async void methods (unobservable exceptions, lifecycle issues)
```
pattern: async\s+void\s+\w+\s*\(
```
Skip if: method name matches event handler pattern (`_Click|_Changed|_Loaded|_Unloaded|_Closed|_Tapped|_Pressed|OnHandler|On\w+Handler`).
Fix: Change to `async Task`. For event handlers, wrap body in try-catch.

### HIGH-04: Timer creation without disposal tracking
```
pattern: new\s+(System\.)?(Threading\.|Timers\.)?Timer\s*\(
```
After finding: check if enclosing class implements `IDisposable` and disposes the timer.
Fix: Store timer in field, implement `IDisposable`, dispose timer in `Dispose()`.

### HIGH-05: GCHandle allocation without free
```
pattern: GCHandle\.Alloc\s*\(
```
After finding: check for matching `\.Free\(\)` in same class.
Fix: Always free in `finally` or `Dispose()`. For pinned buffers, use `GC.AllocateArray<T>(size, pinned: true)`.

### HIGH-06: String interning of dynamic values
```
pattern: string\.Intern\s*\(
```
Fix: Avoid interning user-generated or dynamic strings. Use `string.IsInterned()` to check without interning.

## MEDIUM Severity

### MED-01: String concatenation in loops
```
pattern: (for|foreach|while)\s*\(
```
After finding loop: check if body contains `+=` with string operand or `string.Concat`.
Fix: Use `StringBuilder` or `string.Create()`.

### MED-02: Unnecessary ToList/ToArray materialization
```
pattern: \.(ToList|ToArray)\(\)
```
Skip if: result is modified (`.Add`, `.Insert`, `.Sort`, `.RemoveAt`, indexer assignment).
Fix: Keep as `IEnumerable<T>` if only enumerated once. Use `.Count()` instead of `.ToList().Count`.

### MED-03: Finalizer without IDisposable
```
pattern: ~\w+\s*\(\s*\)
```
After finding: check if class implements `IDisposable`.
Fix: Implement full `Dispose(bool)` pattern with `GC.SuppressFinalize(this)`.

### MED-04: Empty finalizers (unnecessary GC overhead)
```
pattern: ~\w+\s*\(\s*\)\s*\{\s*\}
```
Fix: Remove empty finalizer. Objects with finalizers survive an extra GC generation.

### MED-05: Large array allocations in hot paths
```
pattern: new\s+byte\[\s*\d{5,}\s*\]
```
Fix: Use `ArrayPool<byte>.Shared.Rent()` and return in `finally`.

### MED-06: GC.Collect() calls (usually a code smell)
```
pattern: GC\.Collect\s*\(
```
Fix: Remove unless benchmarking or releasing a known large object graph. GC is self-tuning.

### MED-07: Marshal.AllocHGlobal without FreeHGlobal
```
pattern: Marshal\.AllocHGlobal\s*\(
```
After finding: check for matching `Marshal.FreeHGlobal` in same class.
Fix: Pair with `FreeHGlobal` in `finally` or `Dispose()`. Prefer `NativeMemory.Alloc` in .NET 8+.

### MED-08: Closure capturing this in long-lived callbacks
```
pattern: \+=\s*\(.*\)\s*=>\s*\{?[^}]*this\.
```
Fix: Extract needed values into local variables before the lambda to avoid capturing `this`.

## LOW Severity

### LOW-01: Zero-length array allocations
```
pattern: new\s+\w+\[\s*0\s*\]
```
Fix: Use `Array.Empty<T>()` to reuse a cached empty array.

### LOW-02: Substring usage (allocates new string)
```
pattern: \.Substring\s*\(
```
Fix: Use `.AsSpan().Slice()` or range indexing on `ReadOnlySpan<char>` in hot paths.

### LOW-03: Missing ConfigureAwait in library code
```
pattern: await\s+\w+(?!.*ConfigureAwait)
```
Only flag in library projects (not ASP.NET apps). Fix: Add `.ConfigureAwait(false)` in libraries.

### LOW-04: Boxing via string interpolation of value types
```
pattern: \$".*\{[a-z]\w*\}
```
Skip if: the interpolated variable is already a string or calls `.ToString()`.
Fix: Call `.ToString()` explicitly on value types in interpolated strings to avoid boxing.

### LOW-05: ThreadLocal without disposal
```
pattern: new\s+ThreadLocal<
```
After finding: check if enclosing class disposes it.
Fix: Dispose `ThreadLocal<T>` in `Dispose()` or use `AsyncLocal<T>` instead.
