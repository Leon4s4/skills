# DQL (Dynatrace Query Language) reference

DQL is a read-only, pipeline-based language for querying Grail (logs, events, bizevents, spans, metrics, entities). Commands are chained with `|`; each emits a table of records (rows) and fields (columns) fed to the next. Order affects both results and performance.

## Contents
- Data tables (what you can `fetch`)
- Timeframes
- Performance / sampling controls on `fetch`
- Recommended command order
- Command catalog (grep `## command:`)
- The `timeseries` command (deep dive)
- Function catalog (grep `## fn:`)
- Operators
- Reserved field names
- Worked examples

## Data tables (what you can `fetch`)

`fetch <table>` loads raw records. Common tables: `logs`, `events`, `bizevents`, `spans`, `dt.entity.<type>` (entities). Metrics are queried with `timeseries`/`metrics`, not `fetch`.

```
fetch logs
fetch events
fetch bizevents
fetch spans
```
Each table needs the matching Grail permission (`storage:logs:read`, etc.) plus `storage:buckets:read`.

## Timeframes

Default timeframe is **2 hours** when not specified (apps use the UI timeframe; API/automation should set it explicitly).

```
fetch logs, from:now()-24h, to:now()-2h          // relative
fetch logs, timeframe:"2024-01-01T00:00:00Z/2024-01-02T00:00:00Z"   // absolute ISO interval
fetch logs, from:-1d@d                             // 1 day ago, snapped to day boundary (@d)
```

## Performance / sampling controls on `fetch`

- `samplingRatio:` — return `1/ratio` of raw records (allowed: 1, 10, 100, 1000, 10000). Multiply counts back up (`c = c*100`). Logs/spans only.
- `scanLimitGBytes:` — stop after scanning N GB.
- `bucket:{"name", "pattern_*"}` — restrict to specific Grail buckets.

```
fetch spans, samplingRatio:100, from:-1h
| summarize c=count(), by:{span.name}
| fieldsAdd c = c*100
```

## Recommended command order

1. **Filter early** — `filter`/`search` to cut records. Filter on raw fields (`filter k8s.namespace.name ~ "astro*"`), not transformed ones. Prefer inclusive filters over negations. Avoid `join`/`lookup` just to filter.
2. **Trim fields** — `fields`/`fieldsKeep`/`fieldsRemove` to reduce columns.
3. **Process** — `fieldsAdd`, `parse`, `append`.
4. **Aggregate** — `summarize` (tables) or `makeTimeseries` (charts).
5. **Sort/limit LAST** — `sort` at the end (sorting right after `fetch` is slow); don't `limit` before aggregating or aggregates are wrong.

```
fetch logs, bucket:{"astroshop_log_*"}, from:-1d@d, samplingRatio:10
| filter loglevel == "ERROR" and k8s.namespace.name ~ "astroshop"
| summarize count = count(), by:{pod.name}
| sort count desc
| limit 5
```

## Command catalog

### ## command: data-source
- `data` — generate sample data at runtime (testing/docs).
- `describe` — show the on-read schema for a data object.
- `fetch` — load data from a table (logs/events/bizevents/spans/entities).
- `fieldsSnapshot` — snapshot of fields present in records.
- `load` — load lookup data resources.

### ## command: metric
- `timeseries` — load + filter + aggregate metrics into a homogeneous time series. **Starting command.** (See deep dive below.)
- `metrics` — list metric series for exploration (metric keys, dimensions). No timestamps/values — use `timeseries` for charts. Limited to last 10 days, ≤100,000 series.

### ## command: filter & search
- `filter <condition>` — keep records matching a boolean condition.
- `filterOut <condition>` — drop records matching a condition.
- `search "<terms>"` — full-text search across fields.
- `dedup <field>` — remove duplicate records (keep first per key).

### ## command: selection & modification
- `fields a, b` — keep only listed fields.
- `fieldsAdd x = expr` — add/replace a computed field.
- `fieldsKeep "a*", b` — keep matching fields (supports patterns).
- `fieldsRemove a, b` — drop fields.
- `fieldsRename new = old` — rename a field.

### ## command: extraction & parsing
- `parse <field>, "<DPL pattern>"` — extract values into new fields using Dynatrace Pattern Language. Example: `parse content, "ipaddr:ip ld ' POST ' ld:action ' HTTP/1.1 ' long:status ld"`.

### ## command: ordering
- `sort <field> [asc|desc]` — sort (ascending default). Place last.
- `limit <n>` — cap returned records.

### ## command: structuring
- `expand <arrayField>` — explode an array into one record per element.
- `fieldsFlatten <field>` — flatten nested record fields into top-level columns.

### ## command: aggregation
- `summarize <aggs>, by:{<fields>}` — group + aggregate into a table. Example: `summarize errors=count(), by:{host.name}`.
- `makeTimeseries <agg>, by:<field>, interval:5m` — turn raw records into a chartable time series. Example: `makeTimeseries count=count(), by:loglevel, interval:5m`.
- `fieldsSummary <fields>` — cardinality of values per field.

### ## command: correlation & join
- `append [ <subquery> ]` — union-all the subquery's records (like SQL `UNION ALL`).
- `join on:<keys>, [ <subquery> ], fields:{...}` — join records from a subquery on a condition.
- `joinNested` — attach subquery matches as an array of nested records.
- `lookup [ <subquery> ], sourceField:, lookupField:` — enrich rows with fields from a lookup table on a key match.

### ## command: Smartscape (topology)
- `smartscapeNodes <typePattern>` — load topology nodes (`*` = all types).
- `smartscapeEdges <edgeTypePattern>` — load topology edges.
- `traverse` — walk from source to target nodes following edge types.

## The `timeseries` command (deep dive)

`timeseries` produces homogeneous series: every series shares the same start/end timestamps, interval, and element count. Each aggregation cell is an **array** of values, one per time slot. Output includes `timeframe` (start/end) and `interval` (duration) columns.

**Syntax (key parts):**
```
timeseries [col=]agg(metricKey [, filter:][, default:][, rollup:][, rate:][, scalar:]) [, ...],
  [by:{dims}] [, filter:] [, union:] [, nonempty:] [, interval: | bins:]
  [, from:] [, to:] [, timeframe:] [, shift:]
```

**Aggregations:** `sum`, `avg`, `min`, `max`, `count` (series cardinality per slot), `percentile(key, n)`, `percentRank(key, value)`, `countDistinct`. `start()`/`end()` emit slot timestamps (use alongside an aggregation).

**Per-aggregation parameters:**
- `default:` — fill empty slots with a value instead of `null`.
- `rollup:` — time-aggregation function (`min`/`max`/`sum`/`avg`/`total`) independent of the main aggregation, e.g. `avg(dt.requests.failed, rollup:sum)`. **Required for `percentile` on gauge/count metrics** (except `dt.service.request.response_time` and `…service_mesh.response_time`).
- `rate:` — normalize per duration: `(value/interval)*rate`. E.g. `sum(dt.requests.failed, rate:1s)`.
- `scalar:true` — collapse to a single value over the whole timeframe.
- `filter:` — pre-aggregation filter; a top-level `filter:` applies to all aggregations.

**Query-level parameters:**
- `by:{dims}` — split into series per dimension (e.g. `by:{dt.entity.host}`).
- `interval:` or `bins:` (mutually exclusive) — control slot size / count. Intervals snap to well-known values (1/2/3/5/10/15/30 min; 1/2/3/4/6/8/12/24 h; multiples of 24h ≤30d); max 1,500 slots/series. Slots align to midnight in the timezone, so the returned timeframe may widen slightly.
- `union:` — `false` (default) returns only series present in **all** columns (INNER JOIN); `true` returns all series with `null` fills (OUTER JOIN).
- `nonempty:` — default `false`; if a metric matches no data the column is empty. Combine `default:` + `nonempty:true` to force zero-filled series (e.g. ratio math where the numerator may be absent).
- `shift:` — shift the query window and map results back to the original timestamps (e.g. compare to last week with `shift:-7d`).

**Examples:**
```
timeseries usage=avg(dt.host.cpu.usage)
timeseries min_cpu=min(dt.host.cpu.usage), max(dt.host.cpu.usage, default:99.9),
  by:{dt.entity.host}, filter:in(dt.entity.host,"HOST-1","HOST-2"), interval:1h, from:-7d
timeseries p99=percentile(dt.service.request.response_time, 99), by:{dt.entity.service} | limit 5
timeseries percentile(dt.host.cpu.usage, 90, rollup:avg)         // rollup required for gauge
```

Ratio across two metrics (zero-safe), then join on interval:
```
timeseries http_503=sum(http_requests, default:0), filter:{code==503}, nonempty:true
| join on:interval, [ timeseries http_total=sum(http_requests) ], fields:{http_total}
| fieldsAdd ratio = http_503[]/http_total[]*100
```

Aggregate multiple series (iterative `[]` expressions): `min`/`max`/`sum`/`avg` accept array expressions in `summarize`.
```
timeseries usage=avg(dt.host.cpu.usage), by:{dt.entity.host}
| summarize usage=avg(usage[]), by:{timeframe, interval}
```

> `percentile` on `timeseries` is an estimate accurate to ~2.2%.

## Function catalog

Functions compute values inside expressions. Grouped below; full signatures at the Dynatrace docs (functions page). Grep `## fn:` for a group.

### ## fn: aggregation (used in summarize)
`avg, sum, min, max, count, countIf, countDistinct, countDistinctExact, countDistinctApprox, median, percentile, percentiles, percentRank, percentileFromSamples, stddev, variance, correlation, collectArray, collectDistinct, takeAny, takeFirst, takeLast, takeMax, takeMin`

### ## fn: string
`concat, contains, startsWith, endsWith, indexOf, lastIndexOf, lower, upper, substring, stringLength, trim, like, splitString, replaceString, splitByPattern, replacePattern, matchesPattern, matchesPhrase, matchesValue, parse, parseAll, punctuation, levenshteinDistance, jsonField, jsonPath, encodeUrl, decodeUrl, escape, unescape, unescapeHtml, getCharacter`

### ## fn: conversion & casting
`toString, toLong, toDouble, toBoolean, toDuration, toTimestamp, toTimeframe, toArray, toUid, toIp` and their `as*` null-safe variants (`asString, asLong, asDouble, asBoolean, asDuration, asTimestamp, asTimeframe, asArray, asRecord, asBinary, asNumber, asIp, asUid`). Also `type, record, decode, encode, hexStringToNumber, numberToHexString`, uid helpers (`uuid, uid64, uid128, isUuid, isUid64, isUid128`).

### ## fn: conditional & boolean
`if(cond, then [, else]), coalesce(...)`, `isNull, isNotNull, isTrueOrNull, isFalseOrNull`.

### ## fn: general
`in(value, ...), exists(field), record(...), entityName(id), entityAttr(id, name), classicEntitySelector("...")`. Entity functions need `storage:entities:read`.

### ## fn: time
`now(), timeframe(start,end), timestamp(...), duration(amount,unit), formatTimestamp(ts, format:"..."), getHour/getMinute/getSecond/getDayOfWeek/getDayOfMonth/getDayOfYear/getWeekOfYear/getMonth/getYear, getStart, getEnd`, Unix converters (`timestampFromUnixSeconds/Millis/Nanos`, `unixSecondsFromTimestamp`, etc.).

### ## fn: array
`array(...), arraySize, arrayElement, arrayFirst, arrayLast, arraySlice, arraySort, arrayReverse, arrayDistinct, arrayConcat, arrayFlatten, arrayRemoveNulls, arrayIndexOf, arrayLastIndexOf, arraySum, arrayAvg, arrayMin, arrayMax, arrayMedian, arrayPercentile, arrayCumulativeSum, arrayDelta, arrayDiff, arrayMovingAvg/Sum/Min/Max, arrayToString`.

### ## fn: math
`abs, ceil, floor, round, signum, power, sqrt, cbrt, exp, log, log10, log1p, bin, range, random, pi, e`, trig (`sin, cos, tan, asin, acos, atan, atan2, sinh, cosh, tanh`), angle (`degreeToRadian, radianToDegree`), `hypotenuse`.

### ## fn: network, hash, bitwise, vector, join
- network: `ip, isIp, isIpV4, isIpV6, ipIn, ipMask, ipIsPrivate/Public/Loopback/LinkLocal`
- hash: `hashMd5, hashSha1, hashSha256, hashSha512, hashCrc32, hashXxHash32, hashXxHash64`
- bitwise: `bitwiseAnd, bitwiseOr, bitwiseXor, bitwiseNot, bitwiseShiftLeft, bitwiseShiftRight, bitwiseCountOnes`
- vector distance: `vectorL1Distance, vectorL2Distance, vectorCosineDistance, vectorInnerProductDistance`
- join: `lookup(...), getNodeName(...), getNodeField(...)`

## Operators

- Comparison: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Text match: `~` (phrase/contains match; use when value is partly known)
- Logical: `and`, `or`, `not`, `xor`
- Arithmetic: `+ - * /`; modulo via `mod`
- Array element access: `field[]` (iterate), `field[i]` (index), `myArray[][fieldName]` (nested field over array of records)

Use `==`/`!=` when the value is known (fastest); use `~` for partial/unknown text.

## Reserved field names

`true false null mod and or xor not` cannot be used bare as field names/dimensions — wrap in backticks:
```
| fields x = `true`      // access a custom field named "true"
| sort `not` desc        // sort by a field named "not"
```

## Worked examples

Count errors by pod:
```
fetch logs, from:now()-2h
| filter loglevel == "ERROR"
| summarize errors=count(), by:{k8s.pod.name}
| sort errors desc | limit 10
```

Business events in business hours only:
```
fetch bizevents
| filter event.type == "booking.process.started"
| fieldsAdd hour=formatTimestamp(timestamp,format:"hh"), dow=formatTimestamp(timestamp,format:"EE")
| filterOut (dow=="Sat" or dow=="Sun") or (toLong(hour)<=8 or toLong(hour)>=17)
| summarize starts=count(), by:{product}
```

Logs as a 5-minute time series by level:
```
fetch logs
| filter loglevel == "SEVERE" or loglevel == "ERROR"
| makeTimeseries count=count(), by:loglevel, interval:5m
```

Compare CPU now vs 7 days ago:
```
timeseries cpu=avg(dt.host.cpu.usage), by:{dt.entity.host}, from:-24h
| append [ timeseries cpu_7d=avg(dt.host.cpu.usage), by:{dt.entity.host}, shift:-7d ]
```
