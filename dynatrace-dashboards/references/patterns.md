# Dashboard Design Patterns (24-column grid)

Proven layouts. Match the user's goal to one of these instead of inventing structure — diagnostic dashboards succeed on scannability. These describe the **design**; express them in JSON using the two-map schema (`content.tiles` + `content.layouts`, matching IDs) on the **24-column grid** (`x + w ≤ 24`, no overlaps). Rows go top (triage) → bottom (detail).

Layout tables below give each tile's `x,y,w,h` for the `layouts` map. Validate every DQL with `dtctl query` before building; source queries from `dql-cookbook.md` or a loaded domain skill.

## Contents
1. Four Golden Signals (service)
2. RED (request-oriented)
3. USE (resource / infra)
4. SRE Overview
5. Diagnostics Triage (the "what's wrong and where" board)
6. Layout cheatsheet

---

## 1. Four Golden Signals (service)

**When:** monitoring a service or set of services. The default starting point.
**Signals:** Latency, Traffic, Errors, Saturation.

| Tile (id) | Type / viz | Cookbook §3 query | `x,y,w,h` |
|---|---|---|---|
| header | markdown | — | 0,0,24,1 |
| kpi-errrate | singleValue + thresholds | failure_rate scalar | 0,1,6,3 |
| kpi-rpm | singleValue | request count scalar | 6,1,6,3 |
| kpi-p90 | singleValue + thresholds | p90 scalar | 12,1,6,3 |
| kpi-problems | singleValue + thresholds | open problems count | 18,1,6,3 |
| latency | lineChart | p50/p90/p99 timeseries | 0,4,12,7 |
| throughput | lineChart | request count timeseries | 12,4,12,7 |
| errors | areaChart | failure_count timeseries | 0,11,12,7 |
| saturation | lineChart | host CPU/mem of service hosts | 12,11,12,7 |

Top row = four instant KPIs; rows below = the trends behind them.

---

## 2. RED (request-oriented)

**When:** request-driven services (APIs, GraphQL resolvers, web).
**Signals:** **R**ate, **E**rrors, **D**uration.

| Tile | Viz | `x,y,w,h` |
|---|---|---|
| header | markdown | 0,0,24,1 |
| rate | singleValue | 0,1,8,3 |
| errpct | singleValue + thresholds | 8,1,8,3 |
| dur-p95 | singleValue + thresholds | 16,1,8,3 |
| rate-trend | lineChart (by endpoint) | 0,4,24,7 |
| err-by-endpoint | categoricalBarChart | 0,11,12,7 |
| dur-dist | histogram | 12,11,12,7 |

For GraphQL, split `by:` the operation/resolver dimension so one slow resolver stands out. Remember `categoricalBarChart` (not `barChart`) for per-category values — see `tiles.md`.

---

## 3. USE (resource / infra)

**When:** hosts, nodes, disks, queues — anything with finite capacity.
**Signals per resource:** **U**tilization, **S**aturation, **E**rrors.

| Tile | Viz | `x,y,w,h` |
|---|---|---|
| header | markdown | 0,0,24,1 |
| host-grid | honeycomb | 0,1,24,7 |
| cpu | lineChart (by host) | 0,8,12,7 |
| mem | lineChart (by host) | 12,8,12,7 |
| disk | lineChart + Davis forecast | 0,15,12,7 |
| net | lineChart (rx/tx) | 12,15,12,7 |

Turn on **Davis AI forecasting** on the disk tile (tile `davis` property) to predict exhaustion.

---

## 4. SRE Overview

**When:** an on-call standing board across a system. Golden signals + SLO burn + predictive capacity.

| Tile | Viz | `x,y,w,h` |
|---|---|---|
| header (+ Problems app link) | markdown | 0,0,24,1 |
| availability | singleValue + thresholds | 0,1,6,3 |
| error-budget | singleValue + thresholds | 6,1,6,3 |
| latency-p99 | singleValue + thresholds | 12,1,6,3 |
| rootcause-problems | singleValue + thresholds | 18,1,6,3 |
| latency | lineChart | 0,4,12,7 |
| throughput | lineChart | 12,4,12,7 |
| resource-forecast | lineChart + Davis forecast | 0,11,12,7 |
| recent-problems | table | 12,11,12,7 |

Consider `slo` tiles for the availability/error-budget cells if SLOs are defined (see `tiles.md`).

---

## 5. Diagnostics Triage (the "what's wrong and where" board)

**When:** the user wants quick visualization of issues / a fast diagnostics entry point. A **funnel**: glance → localize → hand off to the Problems app for root cause. This is the shape implemented in `assets/templates/diagnostics-triage.json`.

**Row 1 — Is anything wrong? (instant)**

| Tile | Viz | `x,y,w,h` |
|---|---|---|
| header (+ Problems app link) | markdown | 0,0,24,1 |
| open-problems | singleValue + thresholds | 0,1,5,3 |
| rootcause | singleValue + thresholds | 5,1,5,3 |
| error-rate | singleValue + thresholds | 10,1,5,3 |
| latency-p99 | singleValue + thresholds | 15,1,5,3 |
| worst-cpu | singleValue + thresholds | 20,1,4,3 |

**Row 2 — Where is it? (localize)**

| Tile | Viz | `x,y,w,h` |
|---|---|---|
| svc-health | honeycomb | 0,4,12,8 |
| host-health | honeycomb | 12,4,12,8 |

**Row 3 — What's the shape of it? (context)**

| Tile | Viz | `x,y,w,h` |
|---|---|---|
| errors-trend | lineChart + Davis anomaly | 0,12,12,6 |
| latency-trend | lineChart + Davis anomaly | 12,12,12,6 |

**Row 4 — Active problems detail (jump-off point)**

| Tile | Viz | `x,y,w,h` |
|---|---|---|
| open-problems-table | table | 0,18,24,6 |

Design intent: the top strip answers "should I care?" in one glance; the honeycombs answer "where?"; the anomaly-annotated charts answer "since when / how bad?"; the table is the jump into guided root cause. **Do not** reproduce Davis root-cause analysis in tiles — link to the Problems app.

---

## 6. Layout cheatsheet (24 columns)

- Section header (markdown): `w:24, h:1`.
- KPI single-value: `w:6` → four per row at x = 0,6,12,18. (For five per row use widths 5,5,5,5,4 at x = 0,5,10,15,20.)
- Half-width chart: `w:12, h:7`. Full-width chart: `w:24, h:7`.
- Honeycomb health grid: `w:12–24, h:7–8`.
- Detail table: `w:24, h:5–6`.
- Every `tiles` entry needs a matching `layouts` entry; keep `x + w ≤ 24`; never overlap. The pre-flight validator enforces all three.
