# Attribution

This skill is a merge of two sources.

## From Dynatrace's official `dt-app-dashboards` skill (Apache-2.0)

Repository: https://github.com/Dynatrace/dynatrace-for-ai (`skills/dt-app-dashboards`)
License: Apache-2.0

The following files are copied (verbatim or lightly cross-linked) from that skill and remain under Apache-2.0:

- `references/create-update.md`
- `references/analyzing.md`
- `references/tiles.md`
- `references/variables.md`
- `assets/ExampleDashboard.json`
- `assets/visualization-settings.reference.jsonc`

The dashboard JSON schema (separate `tiles`/`layouts` maps, 24-column grid, `{name,type,content}` document envelope) and the `dtctl` create/update/analyze workflow originate from that skill.

## Additions in this merged skill

- `references/patterns.md` — design blueprints (Golden Signals, RED, USE, SRE, Diagnostics Triage) expressed on the 24-column schema.
- `references/dql-cookbook.md` — DQL starting points by signal, subordinated to `dtctl query` validation and domain skills.
- `references/deploy-without-dtctl.md` — fallback deploy paths (UI upload, Document API, Monaco, Terraform).
- `assets/templates/starter.json`, `assets/templates/diagnostics-triage.json` — templates on the correct schema.
- `scripts/validate_dashboard.py` — a pre-flight structural validator (complements, does not replace, `dtctl apply` server validation).
- The unified `SKILL.md` spine.

If you redistribute this skill, keep this attribution and the Apache-2.0 license for the copied files.
