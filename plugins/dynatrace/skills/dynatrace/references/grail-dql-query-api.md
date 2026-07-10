# Grail DQL Query API reference

Run DQL queries programmatically against Grail. This is the latest-platform path (`.apps.dynatrace.com`), **OAuth/bearer only**. It is read-only — you query data, you don't ingest with it. For end-to-end automation use [scripts/dt_dql.py](../scripts/dt_dql.py).

## Contents
- Async model (execute → poll)
- POST /query:execute
- GET /query:poll
- Response schema
- Permissions
- Other query:* endpoints
- Dynatrace MCP server

## Async model (execute → poll)

A query runs in two steps:
1. `POST .../query:execute` with the DQL string → returns a `requestToken` and a `state`.
2. `GET .../query:poll?request-token=<token>` → returns `state` and, when `SUCCEEDED`, the `result`.

Small/fast queries may already be `SUCCEEDED` in the execute response, but you still retrieve records via `query:poll`. Long queries return `RUNNING` — keep polling until `SUCCEEDED` (or `FAILED`/`CANCELLED`).

Base path: `https://{env-id}.apps.dynatrace.com/platform/storage/query/v1`

## POST /query:execute

- Method: `POST`
- Auth: `Authorization: Bearer <token>`
- `Content-Type: application/json`
- Body: `{ "query": "<DQL>" }` (you may also pass `defaultTimeframeStart`/`defaultTimeframeEnd`, `timezone`, `locale`, `fetchTimeoutSeconds`, `requestTimeoutMilliseconds` depending on API version).

```bash
curl -X POST 'https://abc12345.apps.dynatrace.com/platform/storage/query/v1/query:execute' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"query":"fetch bizevents | summarize count()"}'
```

Response:
```json
{ "state": "SUCCEEDED", "requestToken": "+kuSj8qvRvq64GkG5CEHag==", "progress": 100 }
```

## GET /query:poll

- Method: `GET`
- Auth: `Authorization: Bearer <token>`
- Query param: `request-token` — **URL-encode it** (e.g. `+`→`%2B`, `=`→`%3D`).

```bash
curl 'https://abc12345.apps.dynatrace.com/platform/storage/query/v1/query:poll?request-token=%2BkuSj8qvRvq64GkG5CEHag%3D%3D' \
  -H "Authorization: Bearer $TOKEN"
```

Poll until `state` is terminal. Recommended loop: poll, if `state == "RUNNING"` sleep ~1–2s and retry, with a max attempt/timeout cap.

## Response schema

```json
{
  "state": "SUCCEEDED",
  "progress": 100,
  "result": {
    "records": [ { "count()": "0" } ],
    "types": [ { "indexRange": [0,0], "mappings": { "count()": { "type": "long" } } } ],
    "metadata": {
      "grail": {
        "canonicalQuery": "fetch bizevents\n| summarize count()",
        "scannedRecords": 0,
        "scannedBytes": 0,
        "executionTimeMilliseconds": 4155,
        "analysisTimeframe": { "start": "...", "end": "..." },
        "queryId": "fa4b928f-...",
        "sampled": false,
        "notifications": []
      }
    }
  }
}
```

- `result.records` — the rows (your data). `result.types` describes column types.
- `metadata.grail` — `scannedRecords`/`scannedBytes` (cost), `executionTimeMilliseconds`, `analysisTimeframe`, and `notifications` (warnings such as overridden fields).
- The Data Analysis path / MCP caps Grail responses at **1000 records**; for large result sets aggregate in DQL (`summarize`) rather than returning raw rows.

## Permissions

The bearer token needs `storage:buckets:read` **plus** the per-data permission for each table the query touches (`storage:logs:read`, `storage:events:read`, `storage:bizevents:read`, `storage:spans:read`, `storage:metrics:read`, `storage:entities:read`). Missing permission → the query fails or silently omits that data. See [authentication.md](authentication.md) for the OAuth flow and IAM policy syntax.

## Other query:* endpoints

Same base path, same async pattern:
- `query:execute` / `query:poll` — run a read query (above).
- `query:cancel` — cancel a running query by `request-token`.
- Grail record deletion uses a separate `/delete:execute` endpoint with a restricted DQL subset (requires delete permissions).

## Dynatrace MCP server

Dynatrace hosts an official remote MCP server so an external agent (Claude, Copilot, etc.) can run these tasks without hand-writing the execute/poll flow.

- URL: `https://{env-id}.apps.dynatrace.com/platform-reserved/mcp-gateway/v0.1/servers/dynatrace-mcp/mcp`
- Auth: `Authorization: Bearer <token>` — use a **platform token** (`dt0s16`); OAuth clients can't connect to the remote MCP server directly, and OAuth-derived tokens last only ~5 min.
- Required permissions (user + token): `mcp-gateway:servers:invoke`, `mcp-gateway:servers:read`, plus per-tool permissions.

Tools include:
| Tool | Does | Key permission |
|---|---|---|
| Data Analysis Agent | Executes any valid DQL, returns records (≤1000) | `storage:buckets:read` (+ per-data scopes) |
| Grail Query Agent | NL → DQL (does not run it) | `davis-copilot:nl2dql:execute` |
| DQL Explanation Agent | DQL → natural language | `davis-copilot:dql2nl:execute` |
| Help Agent | Answers Dynatrace product questions | `davis-copilot:conversations:execute` |
| Root Cause Agent | Lists active/closed problems | `storage:buckets:read`, `storage:events:read` |

VS Code setup — add to `.vscode/mcp.json`:
```json
{
  "servers": {
    "dynatrace-mcp": {
      "url": "https://{env-id}.apps.dynatrace.com/platform-reserved/mcp-gateway/v0.1/servers/dynatrace-mcp/mcp",
      "headers": { "Authorization": "Bearer YOUR_PLATFORM_TOKEN" }
    }
  }
}
```
VS Code does not auto-refresh expired tokens — regenerate and update the config when it expires.
