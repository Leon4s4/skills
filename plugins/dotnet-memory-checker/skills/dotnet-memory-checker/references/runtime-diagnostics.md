# Runtime Diagnostics Reference (.NET 8+)

## Tool Installation

```bash
dotnet tool install -g dotnet-counters
dotnet tool install -g dotnet-trace
dotnet tool install -g dotnet-dump
dotnet tool install -g dotnet-gcdump
```

## 1. Live Monitoring (dotnet-counters)

### Memory & GC counters
```bash
dotnet-counters monitor -p <PID> --counters \
  "System.Runtime[gc-heap-size,gen-0-gc-count,gen-1-gc-count,gen-2-gc-count,\
  gen-0-size,gen-1-size,gen-2-size,loh-size,poh-size,\
  alloc-rate,gc-fragmentation,time-in-gc,working-set]"
```

### Collect to CSV
```bash
dotnet-counters collect -p <PID> --format csv -o memory_counters.csv --counters \
  "System.Runtime[gc-heap-size,gen-0-gc-count,gen-1-gc-count,gen-2-gc-count,alloc-rate,time-in-gc,working-set]"
```

### Key indicators

| Counter | Healthy | Warning | Critical |
|---------|---------|---------|----------|
| `time-in-gc` | <5% | 5-15% | >15% |
| `gen-2-gc-count` | Rare | Frequent (>1/min) | Very frequent |
| `gc-fragmentation` | <10% | 10-30% | >30% |
| `alloc-rate` | Stable | Growing | Unbounded growth |
| `gc-heap-size` vs `working-set` | Close | Diverging | Large gap (native leak) |

## 2. Heap Snapshots (dotnet-gcdump)

Lightweight, safe for production. Triggers Gen2 GC and captures type-level info.

```bash
dotnet-gcdump collect -p <PID> -o snapshot1.gcdump
# Wait, then capture another
dotnet-gcdump collect -p <PID> -o snapshot2.gcdump
# Generate text report
dotnet-gcdump report snapshot1.gcdump
```

Compare two snapshots in Visual Studio to see what types are growing.

## 3. Full Dump Analysis (dotnet-dump)

```bash
dotnet-dump collect -p <PID> --type Full -o app.dmp
dotnet-dump analyze app.dmp
```

### SOS Commands

| Command | Purpose |
|---------|---------|
| `dumpheap -stat` | All types by count and total size |
| `dumpheap -type <TypeName>` | All instances of a type |
| `dumpheap -min 85000` | LOH objects (>=85KB) |
| `gcroot <address>` | Why an object is alive (root chain) |
| `dumpobj <address>` | Inspect object fields |
| `objsize <address>` | Retained size of object graph |
| `eeheap -gc` | GC segment layout |
| `gcheapstat` | Per-generation sizes |
| `finalizequeue` | Objects awaiting finalization |
| `gchandles` | GC handle summary (strong, pinned, weak) |
| `gcwhere <address>` | Which generation an object is in |

### Leak investigation workflow
```
1. dumpheap -stat              → find suspiciously large type counts
2. dumpheap -type <Suspect>    → get instance addresses
3. gcroot <address>            → find what roots it alive
4. dumpobj <root-address>      → inspect the rooting object
5. Repeat until root cause found
```

## 4. Event Tracing (dotnet-trace)

```bash
# GC-focused (verbose)
dotnet-trace collect -p <PID> --profile gc-verbose -o gc_trace.nettrace

# GC + allocation type names
dotnet-trace collect -p <PID> \
  --providers "Microsoft-Windows-DotNETRuntime:0x100001:5" -o gc_alloc.nettrace

# Convert for viewing
dotnet-trace convert gc_trace.nettrace --format speedscope
```

### Provider keywords

| Keyword (hex) | Name | What it captures |
|---------------|------|------------------|
| `0x1` | GC | GC start/stop, heap stats |
| `0x100000` | GCHeapAndTypeNames | Type names in GC events |
| `0x200000` | GCHeapCollect | Explicit collection triggers |
| `0x800` | GCHeapSurvivalAndMovement | Object survival data |

## 5. Production Monitoring (dotnet-monitor)

```bash
dotnet tool install -g dotnet-monitor
dotnet-monitor collect --urls http://+:52323
```

### Auto-capture on high GC time
```json
{
  "CollectionRules": {
    "HighGC": {
      "Trigger": {
        "Type": "EventCounter",
        "Settings": {
          "ProviderName": "System.Runtime",
          "CounterName": "time-in-gc",
          "GreaterThan": 30
        }
      },
      "Actions": [{
        "Type": "CollectGCDump",
        "Settings": { "Egress": "artifacts" }
      }]
    }
  }
}
```

## 6. Programmatic Analysis (ClrMD)

```xml
<PackageReference Include="Microsoft.Diagnostics.Runtime" Version="3.1.0" />
```

```csharp
using Microsoft.Diagnostics.Runtime;

using DataTarget target = DataTarget.LoadDump("app.dmp");
using ClrRuntime runtime = target.ClrVersions[0].CreateRuntime();
ClrHeap heap = runtime.Heap;

// Top types by size
var stats = heap.EnumerateObjects()
    .GroupBy(o => o.Type?.Name ?? "<unknown>")
    .Select(g => new { Type = g.Key, Count = g.Count(), Size = g.Sum(o => (long)o.Size) })
    .OrderByDescending(x => x.Size)
    .Take(20);
```

## Decision Tree

| Symptom | First step | Next step |
|---------|-----------|-----------|
| Memory growing over time | `dotnet-counters` (gc-heap-size) | `dotnet-gcdump` at intervals, diff |
| Need to find leaked types | `dotnet-gcdump report` | `dotnet-dump` + `dumpheap -stat` |
| Need root cause of leak | `dotnet-dump` + `gcroot` | Trace reference chain |
| High allocation rate | `dotnet-counters` (alloc-rate) | `dotnet-trace` with GC alloc events |
| Gen2/LOH growing | `dotnet-counters` | `dumpheap -min 85000` |
| High % time in GC | `dotnet-counters` (time-in-gc) | Reduce alloc rate, try Server GC |
| Finalizer queue backup | `dotnet-dump` + `finalizequeue` | Fix slow/blocking finalizers |
| Working set >> GC heap | `dotnet-counters` | Native leak — check P/Invoke, GCHandle |
