# GC Configuration Reference (.NET 8+)

## Configuration via runtimeconfig.json

```json
{
  "runtimeOptions": {
    "configProperties": {
      "System.GC.Server": true,
      "System.GC.Concurrent": true,
      "System.GC.HeapHardLimit": 524288000,
      "System.GC.HeapHardLimitPercent": 75,
      "System.GC.ConserveMemory": 5,
      "System.GC.HighMemPercent": 85,
      "System.GC.RetainVM": true,
      "System.GC.HeapCount": 4,
      "System.GC.DynamicAdaptationMode": 1
    }
  }
}
```

## Configuration via .csproj

```xml
<PropertyGroup>
  <ServerGarbageCollection>true</ServerGarbageCollection>
  <ConcurrentGarbageCollection>true</ConcurrentGarbageCollection>
</PropertyGroup>
```

## Settings Reference

| Setting | Values | Default | Effect |
|---------|--------|---------|--------|
| `System.GC.Server` | bool | false (true for ASP.NET) | Server GC: 1 heap/CPU, parallel, higher throughput |
| `System.GC.Concurrent` | bool | true | Background Gen2 collection (reduces pauses) |
| `System.GC.HeapHardLimit` | bytes | 0 (none) | Absolute cap on GC heap size |
| `System.GC.HeapHardLimitPercent` | 1-100 | 0 | Cap as % of physical memory |
| `System.GC.ConserveMemory` | 0-9 | 0 | Higher = more aggressive compaction (.NET 8+) |
| `System.GC.HighMemPercent` | 1-100 | 90 | Threshold for aggressive GC |
| `System.GC.RetainVM` | bool | false | Keep decommitted segments for reuse |
| `System.GC.HeapCount` | int | CPU count | Limit heap count in Server GC |
| `System.GC.DynamicAdaptationMode` | 0-1 | 1 (.NET 9) | DATAS: auto-adjust heap count |

## Latency Modes (runtime)

```csharp
GCSettings.LatencyMode = GCLatencyMode.Batch;                // Max throughput, longest pauses
GCSettings.LatencyMode = GCLatencyMode.Interactive;           // Default balanced
GCSettings.LatencyMode = GCLatencyMode.LowLatency;            // Suppress Gen2 (brief only!)
GCSettings.LatencyMode = GCLatencyMode.SustainedLowLatency;   // Suppress blocking Gen2
// No-GC region:
if (GC.TryStartNoGCRegion(1024 * 1024)) { try { /* critical */ } finally { GC.EndNoGCRegion(); } }
```

## Recommended Configurations

### Web API (container, 1GB limit)
```json
{
  "runtimeOptions": {
    "configProperties": {
      "System.GC.Server": true,
      "System.GC.Concurrent": true,
      "System.GC.HeapHardLimit": 838860800,
      "System.GC.HeapCount": 2,
      "System.GC.ConserveMemory": 5,
      "System.GC.DynamicAdaptationMode": 1
    }
  }
}
```

### Background worker (low memory priority)
```json
{
  "runtimeOptions": {
    "configProperties": {
      "System.GC.Server": false,
      "System.GC.Concurrent": true,
      "System.GC.ConserveMemory": 7,
      "System.GC.HeapHardLimitPercent": 50
    }
  }
}
```

### Low-latency service
```json
{
  "runtimeOptions": {
    "configProperties": {
      "System.GC.Server": true,
      "System.GC.Concurrent": true,
      "System.GC.RetainVM": true,
      "System.GC.DynamicAdaptationMode": 1
    }
  }
}
```

## Heap Types

| Heap | Threshold | Compacted? | Notes |
|------|-----------|------------|-------|
| Gen0/1/2 (SOH) | <85KB objects | Yes | Standard small object heap |
| LOH | >=85KB objects | Only on request | `LargeObjectHeapCompactionMode = CompactOnce` |
| POH (.NET 5+) | Pinned allocations | Never | `GC.AllocateArray<T>(size, pinned: true)` |

## Memory Pressure API

For native memory invisible to GC:

```csharp
GC.AddMemoryPressure(nativeBytes);    // tell GC about unmanaged allocation
GC.RemoveMemoryPressure(nativeBytes); // must balance exactly on cleanup
```
