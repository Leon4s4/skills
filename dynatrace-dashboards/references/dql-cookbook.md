# DQL Cookbook — starting points, not trusted keys

Launchpad DQL for the tiles you'll build most. **These are starting shapes, not guaranteed keys.** Metric keys and field names vary by tenant, version, and instrumentation (OneAgent vs. OpenTelemetry vs. extensions). Two rules from `create-update.md` apply to everything here:

1. **Validate every query with `dtctl query '<DQL>' --plain` before it goes in a tile.** Single-quote the DQL so the shell doesn't eat `$`, `\`, etc.
2. **Prefer a loaded domain skill's queries over these.** If a domain skill covers the data model, use its queries and field names; treat this file as a fallback and a shape reference. Don't ship a query whose fields you haven't confirmed with a `| limit 1` sample.

## Contents
1. Metrics — `timeseries`
2. Records — `fetch` / `filter` / `summarize`
3. Scalar extraction for single-value tiles
4. Golden signals (services)
5. Infrastructure / USE (hosts)
6. Logs
7. Davis problems / events (health feed)
8. Kubernetes
9. Kafka / event-driven

---

## 1. Metrics — `timeseries`

```dql
timeseries avg(dt.host.cpu.usage), by:{dt.entity.host}
```
Named expressions + interval:
```dql
timeseries { used = avg(dt.host.memory.used), total = avg(dt.host.memory.total) }, by:{dt.entity.host}, interval:1m
```
Percentiles (latency):
```dql
timeseries p90 = percentile(dt.service.request.response_time, 90)
```
`timeseries` outputs **numericArrays** — time-series charts need the `interval` field present (see `tiles.md`). If you pipe through `| fields`, keep `interval` and `timeframe`.

---

## 2. Records — `fetch` / `filter` / `summarize`

```dql
fetch logs
| filter loglevel == "ERROR"
| summarize errors = count(), by:{bin(timestamp, 1m)}
```
Top-N:
```dql
fetch logs | filter loglevel == "ERROR"
| summarize errors = count(), by:{dt.entity.service}
| sort errors desc | limit 10
```

---

## 3. Scalar extraction for single-value tiles

`singleValue` / `meterBar` / `gauge` / `honeycomb` need a **scalar** (long/double), not a timeseries array. Convert arrays with array functions, then map the field via `visualizationSettings` (e.g. `singleValue.recordField`).

Error rate as one number:
```dql
timeseries { failures = sum(dt.service.request.failure_count), total = sum(dt.service.request.count) }
| fieldsAdd error_rate = (arraySum(failures) / arraySum(total)) * 100
| fields error_rate
```
Peak-of-worst-host (saturation KPI):
```dql
timeseries cpu = avg(dt.host.cpu.usage), by:{dt.entity.host}
| fieldsAdd peak = arrayMax(cpu)
| summarize worst = max(peak)
```
Array helpers: `arraySum`, `arrayAvg`, `arrayMax`, `arrayMin`.

---

## 4. Golden signals (services)

Family is typically `dt.service.request.*`; confirm against the tenant. `response_time` base unit is **microseconds** (set `unitsOverrides` to display ms/s).

Latency (line):
```dql
timeseries {
  p50 = percentile(dt.service.request.response_time, 50),
  p90 = percentile(dt.service.request.response_time, 90),
  p99 = percentile(dt.service.request.response_time, 99)
}, by:{dt.smartscape.service}
```
Throughput:
```dql
timeseries requests = sum(dt.service.request.count), by:{dt.smartscape.service}
```
Errors (area/line): `timeseries failures = sum(dt.service.request.failure_count), by:{dt.smartscape.service}`
Failure-rate KPI: see §3.

Classic fallbacks if `dt.service.request.*` is absent: `builtin:service.response.time`, `builtin:service.requestCount.total`, `builtin:service.errors.total.rate`.

---

## 5. Infrastructure / USE (hosts)

CPU: `timeseries avg(dt.host.cpu.usage), by:{dt.entity.host}`
Memory %: 
```dql
timeseries { used = avg(dt.host.memory.used), total = avg(dt.host.memory.total) }, by:{dt.entity.host}
| fieldsAdd used_pct = (used / total) * 100
```
Disk %: `timeseries avg(dt.host.disk.used.percent), by:{dt.entity.host, dt.entity.disk}`
Network: `timeseries { rx = sum(dt.host.net.nic.bytes_rx), tx = sum(dt.host.net.nic.bytes_tx) }, by:{dt.entity.host}`

Add **Davis forecasting** on CPU/disk tiles to predict exhaustion.

---

## 6. Logs

Error volume: `fetch logs | filter loglevel == "ERROR" | summarize count(), by:{bin(timestamp, 1m)}`
Errors by service (honeycomb/bar):
```dql
fetch logs | filter loglevel == "ERROR"
| summarize errors = count(), by:{dt.entity.service} | sort errors desc
```
Pattern search: `fetch logs | filter matchesPhrase(content, "OutOfMemoryError") | summarize count(), by:{bin(timestamp, 5m), dt.entity.process_group}`

---

## 7. Davis problems / events (health feed)

No dedicated problem tile — query into a `data` tile (table or single value). **Verify field names against the tenant's semantic dictionary** (`event.status`, `event.category`, `dt.davis.is_root_cause`, `affected_entity.name`, `display_id` are the usual suspects).

Open problem count (single value, `recordField: "count"`):
```dql
fetch dt.davis.problems | filter event.status == "ACTIVE" | summarize count = count()
```
Open problems table:
```dql
fetch dt.davis.problems | filter event.status == "ACTIVE"
| sort timestamp desc
| fields display_id, event.name, event.category, affected_entity_ids, timestamp
```
Root-cause only: `… | filter event.status == "ACTIVE" and dt.davis.is_root_cause == true`
Events by category (donut): `fetch dt.davis.events | summarize count(), by:{event.category}`

Pair with a markdown tile linking to the **Problems app** for guided root cause.

---

## 8. Kubernetes

Family `dt.kubernetes.*`; scope with **variables** or segments (cluster/namespace/workload).
Pods by phase: `timeseries sum(dt.kubernetes.pods), by:{k8s.namespace.name, k8s.pod.phase}`
Workload CPU vs limits:
```dql
timeseries { usage = avg(dt.kubernetes.container.cpu.usage), limit = avg(dt.kubernetes.container.limits_cpu) }, by:{k8s.namespace.name, k8s.workload.name}
```
Restarts: `timeseries sum(dt.kubernetes.container.restarts), by:{k8s.namespace.name, k8s.workload.name}`

---

## 9. Kafka / event-driven

For streaming, the signals that hide pain are **consumer lag** and **backpressure**, not CPU — and the keys are entirely instrumentation-dependent. Explore `*kafka*` and `*lag*` in the metric list and confirm before use.
```dql
timeseries max(<your.kafka.consumer.lag.metric>), by:{consumer_group, topic}
```
Throughput → the relevant `*.records.*` / `*.messages.*` counter. Processing errors → the logs pattern (§6) filtered to the consumer service. Treat any key here as a placeholder until `dtctl query` confirms it.
