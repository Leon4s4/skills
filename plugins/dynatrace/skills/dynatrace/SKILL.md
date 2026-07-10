---
name: dynatrace
description: |
  Query, ingest, and automate Dynatrace observability data. Use when working with
  Dynatrace: writing or running DQL (Dynatrace Query Language) queries against Grail
  (logs, metrics, events, bizevents, spans); using the dtctl CLI to manage workflows,
  dashboards, notebooks, SLOs, settings and run queries; calling the Environment API
  v2 (metrics, problems, logs, entities, events) or the Grail DQL Query API; setting
  up authentication (API tokens, OAuth clients, platform tokens) and choosing scopes;
  ingesting custom metrics, logs, or business events; or distinguishing Dynatrace
  Classic (.live.dynatrace.com) from the latest platform (.apps.dynatrace.com).
  Triggers on "Dynatrace", "DQL", "Grail", "dtctl", "timeseries query", "fetch logs",
  or any Dynatrace API/CLI/token question.
---

# Dynatrace

Dynatrace has **two generations** that differ in URL, auth, and how you query data. Identify which one you are targeting before doing anything else.

| | Dynatrace Classic | Latest Dynatrace (apps / Grail) |
|---|---|---|
| Base URL | `https://{env-id}.live.dynatrace.com` | `https://{env-id}.apps.dynatrace.com` |
| Primary query method | Environment API v2 REST (metric/entity selectors) | **DQL** over Grail data lakehouse |
| Auth | API token (`Api-Token` header) | OAuth bearer / platform token (`Bearer` header) |
| Example call | `GET /api/v2/metrics/query?metricSelector=...` | `POST /platform/storage/query/v1/query:execute` |

`{env-id}` is the environment ID (e.g. `abc12345`). Managed clusters use `https://{cluster}/e/{env-id}`. The latest platform also exposes classic endpoints under `https://{env-id}.apps.dynatrace.com/platform/classic/environment-api/v2/...` (OAuth only).

**If unsure which generation:** DQL / Grail / `fetch` / `timeseries` / Notebooks / Dashboards apps → latest platform. `metricSelector` / `entitySelector` / `Api-Token` → Classic Environment API. When in doubt, prefer DQL — it is the modern path and covers logs, metrics, events, bizevents, and spans in one language.

## Choosing how to query

1. **Need logs, events, bizevents, spans, or ad-hoc analytics?** → DQL (`fetch`). See [references/dql-reference.md](references/dql-reference.md).
2. **Need a metric time series?** → DQL `timeseries` (latest) or Metrics API v2 `metricSelector` (classic).
3. **Need problems / vulnerabilities / entity topology as JSON?** → Environment API v2 REST. See [references/environment-api-v2.md](references/environment-api-v2.md).
4. **Running DQL from code/automation?** → Grail DQL Query API (execute → poll). Use [scripts/dt_dql.py](scripts/dt_dql.py) or see [references/grail-dql-query-api.md](references/grail-dql-query-api.md).
5. **Managing platform resources (workflows, dashboards, notebooks, SLOs, settings) or want a one-liner for DQL?** → the **dtctl CLI** (see below).

## dtctl CLI

[`dtctl`](references/dtctl-cli.md) is the official open-source, kubectl-style CLI for the **latest platform** (`.apps.dynatrace.com`). It is usually the fastest path for platform work and config-as-code, and it handles the DQL execute/poll flow for you. Full command catalog, resources, and flags in [references/dtctl-cli.md](references/dtctl-cli.md).

```bash
brew install dynatrace-oss/tap/dtctl        # install
dtctl auth login --context prod --environment "https://abc12345.apps.dynatrace.com"
dtctl doctor                                 # verify config/token/connectivity
dtctl query "fetch logs | filter status='ERROR' | limit 100"
dtctl get workflows -o json                  # manage resources (dashboards, notebooks, slos, settings, …)
dtctl apply -f my-workflow.yaml --write-id   # config-as-code: get -o yaml → edit → diff → apply
```

When **you (an AI agent) drive dtctl**, prefer it over hand-rolled API calls and:
- Pass `-A`/`--agent` to get a structured JSON envelope (`{ok, result, error, context}`) instead of parsing tables.
- Discover capabilities at runtime with `dtctl commands -o json` (or `dtctl commands howto`) rather than guessing command names.
- Optionally install dtctl's own version-pinned skill: `dtctl skills install --for claude`.

## Authentication quick guide

Pick the token type by target. Full scope catalog and setup steps in [references/authentication.md](references/authentication.md).

| Target | Token type | Header |
|---|---|---|
| Classic Environment API v2 (`.live`) | API token (`dt0c01…`) | `Authorization: Api-Token dt0c01.<id>.<secret>` |
| Grail DQL Query API & platform services | OAuth client (`dt0s02…`) → bearer | `Authorization: Bearer <token>` |
| Dynatrace MCP server / personal platform access | Platform token (`dt0s16…`) | `Authorization: Bearer <token>` |

OAuth bearer tokens are short-lived (often **~5 min**) — request a fresh one per session. Get one via `client_credentials`:

```bash
curl -X POST https://sso.dynatrace.com/sso/oauth2/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=client_credentials' \
  --data-urlencode 'client_id=dt0s02.XXXX' \
  --data-urlencode 'client_secret=dt0s02.XXXX.YYYY' \
  --data-urlencode 'scope=storage:logs:read storage:buckets:read'
```

Tokens have **scopes** (API-token scopes like `metrics.read`, `logs.read`) or **Grail permissions** (`storage:logs:read`, `storage:buckets:read`, `storage:events:read`). DQL almost always needs `storage:buckets:read` **plus** the per-data-type scope. Never log or commit the secret portion of a token; rotate immediately if leaked.

## DQL quick start

A DQL query is a read-only pipeline: commands chained with `|`, each producing a table fed to the next. Order matters for both results and performance.

```
fetch logs, from:now()-2h
| filter loglevel == "ERROR" and k8s.namespace.name == "checkout"
| summarize count(), by:{k8s.pod.name}
| sort `count()` desc
| limit 10
```

Core building blocks:
- **Load:** `fetch logs|events|bizevents|spans` or `timeseries` (metrics) or `metrics`.
- **Timeframe:** default is **2 hours** if unspecified. Override with `fetch logs, from:now()-24h, to:now()-2h` or `timeframe:"2024-01-01T00:00:00Z/2024-01-02T00:00:00Z"`.
- **Filter:** `filter`, `filterOut`, `search`. Use `==`/`!=` when the value is known; use `~` (matchesPhrase) for partial/unknown text.
- **Shape:** `fields`, `fieldsAdd`, `fieldsKeep`, `fieldsRemove`, `parse`.
- **Aggregate:** `summarize ..., by:{...}` for tables; `makeTimeseries` to chart raw records over time.

Metric time series use the dedicated `timeseries` command, which returns arrays per time slot:

```
timeseries cpu=avg(dt.host.cpu.usage), by:{dt.entity.host}, from:-6h, interval:5m
```

```
timeseries p99=percentile(dt.service.request.response_time, 99), by:{dt.entity.service}
| limit 5
```

Full command list, the `timeseries` parameters (`rollup`, `rate`, `union`, `nonempty`, `bins`, `shift`), every function, operators, and best-practice command ordering are in [references/dql-reference.md](references/dql-reference.md).

## Running DQL programmatically

The Grail DQL Query API is **asynchronous**: one request starts the query, a second polls for the result.

```bash
# 1. start
curl -X POST 'https://{env-id}.apps.dynatrace.com/platform/storage/query/v1/query:execute' \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"query":"fetch logs | summarize count()"}'
# → {"state":"SUCCEEDED","requestToken":"...","progress":100}

# 2. poll (URL-encode the request-token)
curl 'https://{env-id}.apps.dynatrace.com/platform/storage/query/v1/query:poll?request-token=...' \
  -H "Authorization: Bearer $TOKEN"
```

For automation, prefer the bundled script — it handles OAuth, execute, and polling:

```bash
python3 scripts/dt_dql.py --env abc12345 \
  --client-id "$DT_CLIENT_ID" --client-secret "$DT_CLIENT_SECRET" \
  --query 'fetch logs | summarize count()'
# or pass an existing token: --token "$BEARER_OR_PLATFORM_TOKEN"
```

Details (state machine, response schema, MCP server) in [references/grail-dql-query-api.md](references/grail-dql-query-api.md).

## Ingesting data

Ingest uses Classic Environment API v2 endpoints (token with the matching `*.ingest` scope). Endpoints, payload formats, and limits are in [references/environment-api-v2.md](references/environment-api-v2.md).

- Metrics (line protocol): `POST /api/v2/metrics/ingest`, scope `metrics.ingest`.
- Logs (JSON): `POST /api/v2/logs/ingest`, scope `logs.ingest`.
- Events: `POST /api/v2/events/ingest`, scope `events.ingest`.
- Business events: `POST /api/v2/bizevents/ingest`, scope `openpipeline.events`/bizevents ingest.
- OpenTelemetry: OTLP endpoints under `/api/v2/otlp/...`.

## Gotchas

- **Default timeframe is 2h** — always set `from:`/`timeframe:` for queries that should cover a known window.
- **Two URLs, two auth schemes** — a `Bearer` token will not work on `.live.dynatrace.com/api/v2`, and an `Api-Token` will not work on platform endpoints. Match token type to base URL.
- **DQL needs `storage:buckets:read`** in addition to the data scope, or queries return permission errors.
- **Reserved field names** — `true false null mod and or xor not` must be wrapped in backticks to use as field names.
- **Put `sort` and `limit` last** (after `filter`/`summarize`); sorting right after `fetch` hurts performance and `limit` before aggregating produces wrong aggregates.
- **429 on ingest** — the per-environment queue is full or a request timed out after 10s; back off and retry. Ingest payloads cap at ~1–5 MB.
- **Deprecated** — Log Monitoring v2 `search`/`export`/`aggregate` endpoints are being removed (end of 2027); use Logs on Grail (DQL `fetch logs`) instead. Timeseries API v1 is replaced by Metrics API v2.
