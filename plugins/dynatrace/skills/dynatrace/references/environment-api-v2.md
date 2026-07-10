# Environment API v2 (Classic REST) reference

The Environment API v2 is the classic REST surface on `https://{env-id}.live.dynatrace.com/api/v2`. Authenticate with an API token (`dt0c01`) in the `Authorization: Api-Token <token>` header. Each endpoint lists its required scope.

On the latest platform the same endpoints are reachable at `https://{env-id}.apps.dynatrace.com/platform/classic/environment-api/v2/...` but require an **OAuth bearer** token (Api-Token is not accepted there).

## Contents
- Base URLs
- Metrics API v2 (+ metric selector)
- Monitored entities API v2 (+ entity selector → see below)
- Problems API v2
- Events API v2
- Log Monitoring API v2 (deprecated read paths)
- Ingest endpoints
- Entity selector syntax
- Pagination

## Base URLs

| Deployment | Base |
|---|---|
| SaaS Classic | `https://{env-id}.live.dynatrace.com/api/v2` |
| Managed | `https://{cluster}/e/{env-id}/api/v2` |
| Latest platform proxy | `https://{env-id}.apps.dynatrace.com/platform/classic/environment-api/v2` (OAuth) |

## Metrics API v2

Scope: `metrics.read` (read), `metrics.ingest` (ingest), `metrics.write` (delete custom).

- `GET /metrics` — list/explore metric definitions. Supports `metricSelector`, `text`, `fields`, `pageSize`.
- `GET /metrics/query` — read data points. Key params: `metricSelector` (required), `from`, `to`, `resolution`, `entitySelector`, `mzSelector`.
- `GET /metrics/{metricId}` — descriptor of one metric.
- `POST /metrics/ingest` — ingest data points (line protocol).
- `DELETE /metrics/{metricId}` — delete a custom (ingested) metric.

```bash
curl 'https://{env-id}.live.dynatrace.com/api/v2/metrics/query?metricSelector=builtin:host.cpu.usage&from=now-2h&resolution=1m' \
  -H 'Authorization: Api-Token dt0c01.ABC.SECRET'
```

### Metric selector (Classic) basics

A metric selector names a metric key and chains transformations with `:`.
- Base: `builtin:host.cpu.usage`, `builtin:service.response.time`, or a custom `ext:`/ingested key.
- Aggregation: `:avg`, `:max`, `:min`, `:sum`, `:count`, `:percentile(90)`.
- Split: `:splitBy("dt.entity.host")` (group by dimension), `:splitBy()` (no split / total).
- Filter: `:filter(eq("dimension","value"))`, also `and(...)`, `or(...)`, `in(...)`, `prefix(...)`.
- Merge/transform: `:merge("dimension")`, `:fold`, `:names`, `:rate`, `:delta`, `:rollup(avg,1h)`.
- Combine metrics with arithmetic: `(metricA:avg) / (metricB:avg)`.

Example: `builtin:service.response.time:filter(eq("dt.entity.service","SERVICE-123")):splitBy("dt.entity.service"):avg`

Filter to entities via the separate `entitySelector` param (see Entity selector below) instead of, or in addition to, in-selector filters.

> The latest-platform alternative is the DQL `timeseries` command (see dql-reference.md) — prefer it for new work.

## Monitored entities API v2

Scope: `entities.read` / `entities.write`.

- `GET /entities` — list entities. Params: `entitySelector` (required), `from`, `to`, `fields`, `pageSize`.
- `GET /entities/{id}` — full properties of one entity.
- `GET /entityTypes` — all entity types and their properties/relationships.
- `GET /entityTypes/{type}` — one entity type's properties (use to discover valid attributes/relationships).

```bash
curl 'https://{env-id}.live.dynatrace.com/api/v2/entities?entitySelector=type(HOST),tag(env:prod)&fields=+properties.memoryTotal' \
  -H 'Authorization: Api-Token dt0c01.ABC.SECRET'
```

## Problems API v2

Scope: `problems.read` / `problems.write`.

- `GET /problems` — list problems. Params: `problemSelector`, `entitySelector`, `from`, `to`, `fields`, `pageSize`.
- `GET /problems/{problemId}` — full problem details.
- `POST /problems/{problemId}/close` — close a problem.
- `POST /problems/{problemId}/comments` — add a comment; `GET/PUT/DELETE` on comments too.

```bash
curl 'https://{env-id}.live.dynatrace.com/api/v2/problems?from=now-24h&problemSelector=status("OPEN")' \
  -H 'Authorization: Api-Token dt0c01.ABC.SECRET'
```

`problemSelector` supports criteria like `status("OPEN"|"CLOSED")`, `severityLevels(...)`, `impactLevels(...)`, `problemFilterNames(...)`, `managementZones(...)`, `entityTags(...)`.

## Events API v2

Scope: `events.read` / `events.ingest`.

- `GET /events` — query events. Params: `eventSelector`, `entitySelector`, `from`, `to`.
- `GET /events/{eventId}` — one event.
- `GET /eventProperties`, `GET /eventTypes` — metadata.
- `POST /events/ingest` — ingest a custom event.

## Log Monitoring API v2

Scope: `logs.read` / `logs.ingest`.

- `POST /logs/ingest` — push custom logs (JSON). **Active.**
- `GET /logs/search`, `GET /logs/export`, `GET /logs/aggregate` — **deprecated**, removal by end of 2027. Use Logs on Grail (DQL `fetch logs`) via the Grail DQL Query API instead.

## Ingest endpoints

| Data | Endpoint | Scope | Content-Type / format |
|---|---|---|---|
| Metrics | `POST /api/v2/metrics/ingest` | `metrics.ingest` | line protocol: `metric.key,dim=val value` |
| Logs | `POST /api/v2/logs/ingest` | `logs.ingest` | `application/json` (array of log records) |
| Events | `POST /api/v2/events/ingest` | `events.ingest` | `application/json` |
| Business events | `POST /api/v2/bizevents/ingest` | bizevents ingest | `application/json`, `application/cloudevent+json`, or `application/cloudevents-batch+json` |
| OpenTelemetry | `POST /api/v2/otlp/v1/{traces,metrics,logs}` | `openTelemetryTrace.ingest` / `metrics.ingest` / `logs.ingest` | OTLP |

**Metrics line protocol example:**
```bash
curl -X POST 'https://{env-id}.live.dynatrace.com/api/v2/metrics/ingest' \
  -H 'Authorization: Api-Token dt0c01.ABC.SECRET' \
  -H 'Content-Type: text/plain' \
  --data-binary 'my.custom.metric,host=web01 42'
```

**Business events** — every top-level JSON field is stored as a top-level Grail field; nested objects are stored as JSON strings. `event.type` and `event.provider` are the key routing attributes. Pure JSON has no mandatory fields; CloudEvents requires `specversion`, `source`(→`event.provider`), `type`(→`event.type`), `id`(→`event.id`).

```bash
curl -X POST 'https://{env-id}.live.dynatrace.com/api/v2/bizevents/ingest' \
  -H 'Authorization: Api-Token dt0c01.ABC.SECRET' \
  -H 'Content-Type: application/json' \
  -d '{"event.type":"order.created","event.provider":"checkout","id":"42","total":234}'
```

**Ingest limits:** payload cap ~1 MB (bizevents up to 5 MB per request). When the per-environment thread pool + queue is full, or a request waits >10s, you get HTTP `429` — back off and retry. Many small requests are preferred over few large ones.

## Entity selector syntax

Used by `GET /entities`, Metrics `entitySelector`, Problems `entitySelector`, and elsewhere. Total length ≤2,000 chars. You can select only one entity **type** per query. Provide one of `type(...)` or `entityId(...)`; combine with other criteria (AND between criteria).

| Criterion | Syntax | Operator |
|---|---|---|
| Type | `type("HOST")` | EQUALS |
| Entity ID(s) | `entityId("HOST-1","HOST-2")` | EQUALS |
| Name (contains) | `entityName("web")` | CONTAINS |
| Name (starts/equals/in) | `entityName.startsWith("web")`, `entityName.equals("web01")`, `entityName.in("a","b")` | — |
| Case-sensitive name | `caseSensitive(entityName.equals("Web01"))` | — |
| Attribute | `<attribute>("value")`, `<attribute>.exists()` | EQUALS / EXISTS |
| Tag | `tag("[context]key:value","key:value","value")` (ANY of) | EQUALS |
| Management zone | `mzId("123","456")` / `mzName("Prod","QA")` | EQUALS |
| Health | `healthState("HEALTHY"\|"UNHEALTHY")` | EQUALS |
| First seen | `firstSeenTms.gte(<ms>)` (also `gt/lt/lte`) | comparison |
| Relationship | `fromRelationships.<rel>(<entitySelector>)` / `toRelationships.<rel>(...)` | — |
| Deleted | `deletedEntities.include()` / `.exclude()` (excluded by default) | — |
| Negate | `not(<criterion>)` (cannot negate `type`) | — |

Quote values containing parentheses or commas: `entityName.equals("Server(prod),1")`. Discover valid attributes/relationships via `GET /entityTypes/{type}`.

## Pagination

List endpoints return `nextPageKey` when results exceed `pageSize`. Fetch the next page by passing only `nextPageKey` (no other params):
```bash
curl 'https://{env-id}.live.dynatrace.com/api/v2/entities?nextPageKey=AQAAABQB...' \
  -H 'Authorization: Api-Token dt0c01.ABC.SECRET'
```
