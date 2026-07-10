---
name: dynatrace-dashboards
description: >-
  Create, modify, analyze, and deploy Dynatrace platform (Gen3 / Grail) dashboards via the dtctl CLI.
  Use this skill whenever the user wants a Dynatrace dashboard, an observability/monitoring/diagnostics
  view, an SRE or golden-signals board, a service-health or infrastructure board, wants to write or fix
  DQL for tiles, wants honeycomb health grids, single-value KPIs, or problem feeds, or wants to read,
  audit, or update an existing dashboard. Trigger it even when the word "dashboard" isn't used — e.g.
  "visualize our service latency in Dynatrace", "a diagnostics view for our Kafka services", "chart host
  saturation in Grail", "turn these queries into a board", or "what does this dashboard show". Also covers
  deploying via dtctl, the Document API, Monaco, or Terraform. Prefer this skill over hand-writing JSON:
  the schema is exact and unforgiving, and this skill encodes the validated workflow.
---

# Dynatrace Dashboards

Build, analyze, and deploy Gen3 (Grail-backed) Dynatrace dashboards. The operational spine is the **`dtctl` CLI** — it validates DQL, downloads current server state, and deploys with automatic validation. Layered on top is a **design library** (proven diagnostic layouts) so the boards you produce are not just valid but useful.

> **Provenance:** the schema, `dtctl` workflow, and the `tiles.md` / `variables.md` / `create-update.md` / `analyzing.md` references + `ExampleDashboard.json` / `visualization-settings.reference.jsonc` assets are from Dynatrace's official `dt-app-dashboards` skill (Apache-2.0; see `ATTRIBUTION.md`). The design patterns (`patterns.md`), the DQL launchpad (`dql-cookbook.md`), the non-`dtctl` deploy paths (`deploy-without-dtctl.md`), the corrected templates, and the pre-flight validator are additions.

## Dashboard JSON structure (get this exactly right)

A dashboard is a document with a `content` body. **Two separate maps** — `tiles` and `layouts` — keyed by the same tile IDs:

```json
{
  "name": "My Dashboard",
  "type": "dashboard",
  "content": {
    "version": 21,
    "variables": [],
    "tiles":  { "0": { "type": "markdown", "content": "# Title" },
                "1": { "type": "data", "title": "…", "query": "…",
                       "visualization": "lineChart",
                       "visualizationSettings": {}, "querySettings": {} } },
    "layouts": { "0": { "x": 0, "y": 0, "w": 24, "h": 1 },
                 "1": { "x": 0, "y": 1, "w": 24, "h": 8 } }
  }
}
```

Non-negotiables (these are the errors that silently break a board):

- **`layouts` is a separate top-level map inside `content`**, NOT a `layout` field inside each tile. Every tile ID in `tiles` MUST have a matching entry in `layouts`.
- **The grid is 24 columns** (`content.settings.gridLayout.columnsCount`, default 24). Full width `w:24`, half `w:12`, quarter `w:6`. `x + w > 24` makes the tile wrap; never let tiles overlap.
- The dashboard needs a top-level **`name`**. On a **new** dashboard, no `id` (the server assigns one). On an **update**, the `id` comes from the downloaded file — never inject one by hand.
- Tile types: `markdown`, `data` (DQL + visualization), `code` (JS), `slo`. Data tiles carry `visualizationSettings` and `querySettings` (often `{}`).

## Workflow (dtctl — the primary path)

Follow the mandatory 7-step order in `references/create-update.md`. In brief:

1. **Define purpose**, then read the relevant references + `patterns.md` to pick a layout.
2. **Explore data** — confirm fields/metrics exist. Prefer loaded domain skills; don't invent metric keys.
3. **Plan structure** — tiles, variables, and the `layouts` grid (24-col). Use a `patterns.md` blueprint.
4. **Validate every DQL** with `dtctl query '<DQL>' --plain` (single-quote the DQL). Both tile and variable queries. This is mandatory — a query that isn't validated doesn't go in the board.
5. **(Update only) Download first:** `dtctl get dashboard <id> -o json --plain > dashboard.json`. This preserves UI edits the user made since last deploy. Never reconstruct-and-inject-`id`.
6. **Construct** (new) or **modify the downloaded file** (update). Match `tiles` ↔ `layouts` IDs.
7. **Pre-flight, then deploy:**
   ```bash
   python scripts/validate_dashboard.py dashboard.json     # fast local structural check
   dtctl apply -f dashboard.json -o yaml --dry-run          # server validation, no persist
   dtctl apply -f dashboard.json -o yaml                    # deploy; local file deleted on success
   ```
   Fix ALL reported errors before re-running (don't loop fixing one at a time). Present the returned URL.

To **read or audit** an existing dashboard, see `references/analyzing.md` (`dtctl get … -o json --plain`, then iterate `content.layouts` sorted by `y,x`).

## Design principles (what makes a diagnostics board good)

- **Triage top, detail bottom.** The first screenful answers "is something wrong, and where?" — problem counts, golden-signal KPIs, health honeycombs — before any deep time-series. A diagnostics board is a funnel, not a data dump.
- **Dashboard = "what/where"; Problems app = "why."** Don't rebuild Davis root-cause analysis in tiles. Link out to the Problems app; wire **Davis AI Analyzer** (anomaly bands / forecast) onto key time-series tiles instead (tile `davis` property).
- **Fewer, sharper tiles.** Every tile earns its place by answering a question. Group with `markdown` headers.
- **Color carries meaning.** Thresholds (green/yellow/red) on single values and honeycombs let the eye find trouble instantly — see the threshold shape in `ExampleDashboard.json`.
- **Filter with variables, not copy-paste.** One service/namespace variable beats hardcoding a filter into ten queries. See `references/variables.md`.
- **No time-range filters in tile queries** — the dashboard time picker handles that. Only add one if the user explicitly asks.

Naming note: **Davis CoPilot → Dynatrace Assist**, and AI-in-dashboarding is **Dynatrace Intelligence**. The underlying Davis engine (anomaly detection, forecasting, root cause) is unchanged; DQL and JSON are unaffected.

## Visualization types

Time-series (need `timeseries`/`makeTimeseries`; values are numericArrays so the tile must include an `interval` field): `lineChart`, `areaChart`, `barChart`, `bandChart`.
Categorical (`summarize … by:{field}`): `categoricalBarChart`, `pieChart`, `donutChart`.
Single value / gauge (one scalar record): `singleValue`, `meterBar`, `gauge`.
Tabular (any shape): `table`, `raw`, `recordList`. Distribution/status: `histogram`, `honeycomb`.
Maps: `choroplethMap`, `dotMap`, `connectionMap`, `bubbleMap`. Matrix: `heatmap`, `scatterplot`.

Each visualization requires specific field types in the query result or it renders blank — the full table (and gotchas like `barChart` being time-series only, and `heatmap` axes rejecting raw `timestamp`) is in `references/tiles.md`. Per-visualization `visualizationSettings` shapes are in `assets/visualization-settings.reference.jsonc`.

## References

| File | When to load |
|---|---|
| `references/create-update.md` | Creating/updating — the mandatory dtctl workflow + anti-patterns |
| `references/analyzing.md` | Reading/auditing an existing dashboard |
| `references/tiles.md` | Tile types, required field types per visualization, settings |
| `references/variables.md` | Variable types, single/multi-select, modifiers, dependencies |
| `references/patterns.md` | **Design blueprints** — Golden Signals, RED, USE, SRE, Diagnostics Triage (24-col layouts) |
| `references/dql-cookbook.md` | DQL starting points by signal — **validate with `dtctl query` before use** |
| `references/deploy-without-dtctl.md` | Fallback deploy: UI upload, Document API, Monaco, Terraform |

## Assets

- `assets/ExampleDashboard.json` — canonical correct example (copy tile/threshold/unit shapes from here).
- `assets/visualization-settings.reference.jsonc` — per-visualization `visualizationSettings` reference.
- `assets/templates/starter.json` — minimal valid document (correct envelope + separate `layouts` map).
- `assets/templates/diagnostics-triage.json` — a full diagnostics-triage board to adapt (the "what's wrong and where" funnel).

## Scripts

- `scripts/validate_dashboard.py` — fast **pre-flight** structural check to run before a `dtctl apply` round-trip. Verifies the `content` envelope, that `tiles` and `layouts` are maps with matching IDs, the 24-col grid math, tile overlaps, data-tile `query` presence, and flags variables that are never referenced. `dtctl apply` still does the authoritative server-side validation; this just catches the obvious structural breakage locally.
  ```bash
  python scripts/validate_dashboard.py dashboard.json
  ```
