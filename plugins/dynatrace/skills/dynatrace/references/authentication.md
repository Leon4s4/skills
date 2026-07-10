# Dynatrace authentication reference

Covers token types, the token format, creating each kind of token, the scope/permission catalog, the OAuth bearer-token flow, IAM policies, and how auth differs between Classic and the latest platform.

## Contents
- Token format & prefixes
- Token type decision table
- Creating API tokens (Classic)
- Creating OAuth clients (latest platform)
- Platform tokens
- Authenticating a request
- OAuth `client_credentials` bearer-token flow
- IAM policies (Grail permissions)
- API-token scope catalog
- Grail permission catalog

## Token format & prefixes

Dynatrace tokens are three dot-separated parts: `prefix.publicId.secret`.
Example: `dt0s01.ST2EY72KQINMH574WMNVI7YN.G3DFPBEJ…RZM`
- **token identifier** = `prefix.publicId` (safe to show/log).
- **secret** = the 64-char final part — treat like a password; never display, store in logs, or commit. Rotate immediately if leaked.

| Prefix | Type |
|---|---|
| `dt0c01` | API token (Classic Environment API auth — `Api-Token` realm) |
| `dt0s01` | Account API token (SCIM / account changes) |
| `dt0s02` | OAuth2 client for Dynatrace Apps & Account Management API |
| `dt0s03`/`dt0s08` | OAuth2 client for internal/external services & integrations |
| `dt0s06` | OAuth2 refresh token (rotates every ~5–15 min) |
| `dt0s16` | Platform token — programmatic access to platform services |

> The token you most often create for REST calls on `.live.dynatrace.com` starts with `dt0c01` and is passed as `Api-Token`. OAuth client IDs/secrets start with `dt0s02`.

## Token type decision table

| You are calling | Use | Auth header |
|---|---|---|
| Classic Environment API v2 (`.live.dynatrace.com/api/v2`) | API token `dt0c01` | `Authorization: Api-Token <token>` |
| Classic Environment/Config API v1 | API token `dt0c01` | `Authorization: Api-Token <token>` |
| Grail DQL Query API & other platform services (`.apps.dynatrace.com/platform`) | OAuth client `dt0s02` → bearer | `Authorization: Bearer <bearer>` |
| Classic endpoints proxied under `.apps.dynatrace.com/platform/classic/...` | OAuth bearer (Api-Token NOT accepted here) | `Authorization: Bearer <bearer>` |
| Dynatrace MCP server / personal platform access | Platform token `dt0s16` (recommended) or OAuth bearer | `Authorization: Bearer <token>` |

## Creating API tokens (Classic)

UI: **Access Tokens** → **Generate new token** → name it → select scopes → **Generate**. The secret is shown **once** at creation and cannot be revealed later.

API (manage tokens programmatically) — Access tokens API:
- `POST /api/v2/apiTokens` — create (needs `apiTokens.write`)
- `GET /api/v2/apiTokens` — list (needs `apiTokens.read`)
- `PUT /api/v2/apiTokens/{id}` — update scopes. **Sending scopes replaces the full set** — include existing scopes you want to keep, or they are removed.
- `DELETE /api/v2/apiTokens/{id}` — revoke

**Personal access tokens** (Classic, user context) are created from the user menu → **Personal Access Tokens**; they support a subset of scopes (entities, metrics, problems, settings, slo, releases, security problems, network zones, api tokens).

## Creating OAuth clients (latest platform)

In **Account Management** (`myaccount.dynatrace.com`) → **Identity & access management** → **OAuth clients** → **Create client**:
1. Provide owner email + description.
2. Select the permissions the client needs (these become available scopes).
3. Save the **client secret** (shown once) and note the **client ID** (`dt0s02.…`).

To use the client you also need an **IAM policy** bound to your user/group granting matching permissions (see below).

## Platform tokens

In **Account Management** → **Identity & access management** → **Platform tokens** (or your user menu → **Platform tokens**). Platform tokens (`dt0s16`) give programmatic access to platform services in your user context and are the recommended way to connect to the Dynatrace MCP server (OAuth clients can't connect to the remote MCP server directly; OAuth-derived tokens there last only ~5 min).

## Authenticating a request

Classic API token — pass in the `Authorization` header (preferred over the `api-token` query param, which can leak via logs/bookmarks):
```bash
curl 'https://{env-id}.live.dynatrace.com/api/v2/metrics' \
  -H 'Authorization: Api-Token dt0c01.ABC123.SECRET'
```

OAuth / platform bearer:
```bash
curl 'https://{env-id}.apps.dynatrace.com/platform/storage/query/v1/query:execute' \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1Qi...'
```

## OAuth `client_credentials` bearer-token flow

Request a bearer token from the SSO endpoint; use it within its short lifetime (`expires_in`, often 300s).

- URL: `https://sso.dynatrace.com/sso/oauth2/token`
- Method: `POST`, `Content-Type: application/x-www-form-urlencoded`
- URL-encode all values.

| Key | Value | Required |
|---|---|---|
| `grant_type` | `client_credentials` | yes |
| `client_id` | `dt0s02.****` | yes |
| `client_secret` | `dt0s02.***.****` | yes |
| `scope` | space-separated scopes, e.g. `storage:logs:read storage:buckets:read` | yes |
| `resource` | `urn:dtaccount:{account-uuid}` | required only if defined on the client |

```bash
curl -X POST https://sso.dynatrace.com/sso/oauth2/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=client_credentials' \
  --data-urlencode 'client_id=dt0s02.XXXX' \
  --data-urlencode 'client_secret=dt0s02.XXXX.YYYY' \
  --data-urlencode 'scope=storage:logs:read storage:buckets:read'
```
Response: `{ "access_token": "...", "token_type": "Bearer", "expires_in": 300, "scope": "..." }`. Use `access_token` as `Authorization: Bearer <access_token>`.

## IAM policies (Grail permissions)

OAuth clients/platform tokens grant access only if the user/group has a matching **IAM policy**. Create in Account Management → **Policy management**, then bind it to a group the user belongs to. Statements use Dynatrace's policy language:

```
ALLOW storage:buckets:read WHERE storage:table-name = "bizevents";
ALLOW storage:bizevents:read;
ALLOW storage:events:write;
```

You can scope a bucket/table with `WHERE storage:table-name = "logs"` (or `metrics`, `events`, `spans`, `bizevents`).

## API-token scope catalog (Classic, common)

Pass these as scopes when creating an API token (`dt0c01`).

**API v2**
| Scope | Grants |
|---|---|
| `metrics.read` / `metrics.ingest` / `metrics.write` | Read / ingest / delete custom metrics (Metrics v2) |
| `logs.read` / `logs.ingest` | Read / ingest logs (Log Monitoring v2) |
| `events.read` / `events.ingest` | Read / ingest events (Events v2) |
| `entities.read` / `entities.write` | Monitored entities & custom tags |
| `problems.read` / `problems.write` | Problems v2 |
| `securityProblems.read` / `securityProblems.write` | Vulnerabilities |
| `settings.read` / `settings.write` | Settings API |
| `slo.read` / `slo.write` | Service-level objectives |
| `releases.read` | Releases API |
| `networkZones.read` / `networkZones.write` | Network zones |
| `activeGates.read` / `activeGates.write` | ActiveGates |
| `apiTokens.read` / `apiTokens.write` | Manage API tokens |
| `auditLogs.read` | Audit log |
| `credentialVault.read` / `credentialVault.write` | Credential vault |
| `extensions.read` / `extensions.write` (+ `extensionConfigurations.*`, `extensionEnvironment.*`) | Extensions 2.0 |
| `hub.read` / `hub.write` / `hub.install` | Hub items |
| `openTelemetryTrace.ingest` | Ingest OTel traces |
| `syntheticLocations.read/write`, `syntheticExecutions.read/write` | Synthetic v2 |

**OpenPipeline ingest**: `openpipeline.events`, `openpipeline.events.custom`, `openpipeline.events_sdlc(.custom)`, `openpipeline.events_security(.custom)`.

**API v1**: `DataExport` (metrics/events/topology), `ReadConfig`/`WriteConfig` (Configuration API), `LogExport`, `DTAQLAccess` (user sessions), `ExternalSyntheticIntegration`, `CaptureRequestData`, `RestRequestForwarding`.

**PaaS**: `InstallerDownload`, `SupportAlert`.

## Grail permission catalog (latest platform / DQL)

Used as OAuth scopes and IAM policy permissions. DQL needs `storage:buckets:read` **plus** the per-data permission.

| Permission | Grants DQL access to |
|---|---|
| `storage:buckets:read` | Grail buckets (required for nearly all DQL) |
| `storage:logs:read` | `fetch logs` |
| `storage:events:read` | `fetch events`, problems via events |
| `storage:bizevents:read` | `fetch bizevents` |
| `storage:spans:read` | `fetch spans` |
| `storage:metrics:read` | `timeseries` / `metrics` commands |
| `storage:entities:read` | entity functions (`entityName`, `entityAttr`), Smartscape |
| `storage:events:write` | ingest events/bizevents |
| `davis-copilot:nl2dql:execute` | natural-language → DQL (MCP Grail Query Agent) |
| `davis-copilot:dql2nl:execute` | DQL → natural-language explanation |
| `mcp-gateway:servers:invoke` / `mcp-gateway:servers:read` | invoke Dynatrace MCP server tools |

You may assign multiple scopes to one token, or split across several tokens with least privilege — follow your org's policy.
