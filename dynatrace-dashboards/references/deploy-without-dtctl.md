# Deploying without dtctl (fallback paths)

`dtctl apply` is the primary path (see `create-update.md`) — it validates and deploys in one step. Use these only when `dtctl` isn't available (e.g. a colleague without the CLI, a CI runner, or a GitOps fleet). The dashboard JSON is identical; only the transport differs.

## 1. Upload in the Dashboards app (no CLI)

1. Open **Dashboards** (Gen3 app, not Dashboards Classic).
2. Left **Dashboards** panel → **Upload** → choose the `.json`.
3. It lands in **Recently modified** / **All dashboards**, opened in Dynatrace.

A **"Run code" warning** on upload is expected for dashboards with `code` tiles. Import failures are almost always a `version` mismatch or a malformed `tiles`/`layouts` map — run the pre-flight validator first.

Note: the app upload expects the dashboard `content`; when exporting via the app you get the same `{name,type,content}` document `dtctl` uses.

## 2. Document API (scriptable, single dashboard)

Gen3 dashboards are documents under the **Document API** (`/platform/document/v1/documents`) — distinct from the classic Dashboard API (v1).

```bash
curl -X POST "$DT_URL/platform/document/v1/documents?name=My+Dashboard&type=dashboard" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  --data-binary @dashboard.json
```

**Gotcha:** on creation the document is effectively private regardless of the flag — **PATCH the document after creation** to make it visible to others. Budget a second call. Use a platform token with the right document scopes (e.g. `document:documents:write`); confirm `$DT_URL` and scopes against the tenant.

## 3. Config-as-code (GitOps fleet)

**Monaco** (Dynatrace Configuration as Code): store dashboards as JSON/YAML in Git, deploy with `monaco`. Good for exporting an environment's dashboards and diffing DQL across all of them.
- `docs.dynatrace.com/docs/deliver/configuration-as-code/monaco`

**Terraform** (`dynatrace-oss/dynatrace` provider): the `dynatrace_document` resource (type `dashboard`) holds the JSON `content`:

```hcl
resource "dynatrace_document" "diag_triage" {
  type    = "dashboard"
  name    = "Diagnostics Triage"
  content = file("${path.module}/dashboards/diag-triage.json")
  # private = false   # confirm current attribute name in provider docs
}
```

For Gen3 documents prefer `dynatrace_document` (type `dashboard`) over the older `dynatrace_json_dashboard` resource, which targets **classic** dashboards.

## Which to use

- Have `dtctl` → use `dtctl apply` (primary). Everything below is only for when you don't.
- One-off, no CLI → UI upload.
- CI step stamping out a dashboard per service → Document API (+ visibility PATCH).
- Managed fleet in Git → Monaco or Terraform.
