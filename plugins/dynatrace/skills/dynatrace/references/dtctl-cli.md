# dtctl CLI reference

`dtctl` (github.com/dynatrace-oss/dtctl) is the official open-source, **kubectl-style** CLI for the Dynatrace **platform** (`.apps.dynatrace.com`). It manages workflows, dashboards, notebooks, SLOs, settings, and runs DQL — "built for humans and AI agents alike." It targets the latest platform and authenticates with OAuth/SSO or platform tokens (not Classic `.live` Api-Token).

## Contents
- Install
- Configuration & contexts
- Authentication
- Command grammar & verbs
- Global flags & output formats
- Resource catalog (short names)
- Querying DQL (`dtctl query`)
- Executing things (`dtctl exec`)
- Apply / create / edit / diff
- Agent mode (use this when driving dtctl as an AI agent)
- Self-discovery: `dtctl commands`
- Aliases
- Installing the official dtctl skill

## Install

```bash
brew install dynatrace-oss/tap/dtctl                                   # macOS/Linux (recommended; sets up completions)
curl -fsSL https://raw.githubusercontent.com/dynatrace-oss/dtctl/main/install.sh | sh   # shell script
# Windows PowerShell:  irm https://raw.githubusercontent.com/dynatrace-oss/dtctl/main/install.ps1 | iex
dtctl version
dtctl doctor          # health check: config, context, token, connectivity, auth
```
Binaries on the releases page; build from source needs Go 1.24+ (`make build`). macOS unsigned-binary warning → `sudo xattr -r -d com.apple.quarantine dtctl`.

## Configuration & contexts

dtctl is **context-based** like kubectl. A context = environment URL + credentials + safety level. Config lives at `~/.config/dtctl/` (Linux) / `~/Library/Application Support/dtctl` (macOS).

```bash
dtctl config set-context my-env \
  --environment "https://abc12345.apps.dynatrace.com" \
  --token-ref my-token
dtctl config set-credentials my-token --token <platform-token>   # stored securely (OS keychain)
dtctl config get-contexts        # list (shows safety levels)
dtctl config use-context prod    # switch
dtctl config current-context
dtctl config describe-context prod
dtctl config delete-context old-env
dtctl ctx                        # shortcut: list contexts
dtctl ctx prod                   # shortcut: switch
dtctl get workflows --context prod   # one-off override without switching
```

**Safety levels** — set per context (e.g. `read-only` vs `unrestricted`) to guard prod against writes. **Per-project config:** `dtctl config init` writes a `.dtctl.yaml` in the cwd (supports env-var expansion) for team/CI use; commands in that dir use it automatically. `dtctl --config <path> ...` selects a config file explicitly.

## Authentication

```bash
dtctl auth login --context my-env --environment "https://abc12345.apps.dynatrace.com"  # browser SSO; tokens refreshed automatically
dtctl auth whoami            # current user (--id-only, -o json)
dtctl auth status            # token health: auth type, storage, access/refresh token expiry (-o json)
dtctl auth logout
```
Two auth modes: **OAuth SSO** (`dtctl auth login`, auto-refresh) or a **platform token** referenced by a context (`set-credentials`). See [authentication.md](authentication.md) for token types/scopes.

## Command grammar & verbs

```
dtctl [verb] [resource-type] [resource-name] [flags]
```

| Verb | Purpose |
|---|---|
| `get` | List/retrieve resources |
| `describe` | Detailed info about a resource |
| `create` | Create from file/args |
| `apply` | Create-or-update from file (templates; idempotent) |
| `edit` | Edit interactively (YAML default, `--format=json`) |
| `delete` | Delete resources |
| `query` | Run a DQL query (template support) |
| `exec` | Execute a workflow, SLO, function, analyzer, or copilot |
| `logs` | Print logs for a resource |
| `history` / `restore` | Document version snapshots |
| `diff` | Local file vs remote resource |
| `wait` | Block until a condition (query result / resource state) |
| `watch` (`-w`) | Stream changes |
| `alias` | Manage aliases (set/list/delete/import/export) |
| `ctx` | Quick context management |
| `doctor` | Health check |
| `commands` | Machine-readable command catalog (for AI agents) |
| `skills` | Install AI-assistant skill files |

## Global flags & output formats

```
--context <name>          Use a specific context
-o, --output <fmt>        json | yaml | toon | csv | table | wide | chart | sparkline | barchart | braille
--plain                   No colors / no interactive prompts (machine-friendly)
--no-headers              Omit table headers
-v / -vv                  Verbose / full HTTP debug   (--debug == -vv)
--dry-run                 Print what would happen, do nothing
--field-selector <f>      Filter by fields, e.g. owner=me,type=notebook
-A, --agent               Wrap output in a structured JSON envelope (for AI agents)
--no-agent                Disable auto-detected agent mode
-w, --watch               Watch for changes (with --interval, --watch-only)
```

I/O philosophy: **"Humans write YAML, machines speak JSON."** Input accepts commented YAML (converted to API JSON); default human output is ASCII tables; `-o json` for piping to `jq`; `-o yaml` for copy-paste. Timeseries can render as `chart`/`sparkline`/`barchart`.

## Resource catalog (short names)

Singular/plural both accepted, plus short aliases (kubectl-style):

| Resource | Short | Notes |
|---|---|---|
| `documents` | `doc` | Type-agnostic Documents API (escape hatch for any doc type) |
| `dashboards` | `dash`, `db` | `--mine`, `--name`, `--admin-access`, `--add-fields`, `--filter` |
| `notebooks` | `nb` | |
| `slos` | — | Service-level objectives; `create`, `exec` to evaluate |
| `workflows` | `wf` | Automation workflows; executions, logs, version history |
| `buckets` | `bkt` | Grail buckets |
| `settings` | `setting` | Settings API v2 objects |
| `settings-schemas` | `schema`, `schemas` | Settings schemas |
| `vulnerabilities` | `vuln` | Security problems |
| `notifications` | `notif` | |
| `functions` | `fn`, `func` | App Engine functions (run via `exec`) |
| `analyzers` | `az` | Davis AI analyzers (e.g. forecast) |
| `copilot` | `cp`, `chat` | Davis CoPilot Q&A |
| `extensions` | `ext`, `exts` | Extensions 2.0 (+ `extension-configs`/`ext-config`) |
| `lookups` | `lkup`, `lu` | Grail Resource Store lookup tables |
| `edgeconnects` | `ec` | EdgeConnect |
| `intents` | — | App intents |

Also covered: IAM (users, groups), Davis AI, OpenPipeline, App Engine, Email templates, State management, and cloud connections (Azure/GCP/AWS connection + monitoring config). Some subcommands are marked "not implemented yet" in the design doc — verify with `dtctl <verb> --help` or `dtctl commands`.

## Querying DQL (`dtctl query`)

Runs DQL against Grail and handles the execute/poll flow for you. See [dql-reference.md](dql-reference.md) for the language.

```bash
dtctl query "fetch logs | filter status='ERROR' | limit 100"
dtctl query "fetch logs | summarize count(), by:{status} | sort count desc"
dtctl query -f queries/errors.dql -o json > results.json     # from file
dtctl query -f - -o json <<'EOF'                              # from stdin
fetch logs | limit 10
EOF
dtctl query -f queries/logs-by-host.dql --set host=my-server  # template var substitution
dtctl query "fetch logs" --max-result-records 5000 -o csv > logs.csv
dtctl query "fetch logs | filter status='ERROR'" --live --interval 5s   # live refresh
dtctl query "timeseries avg(dt.host.cpu.usage), by:{dt.entity.host}" -o chart
```
Notes: quote DQL so the shell doesn't split it; use single quotes inside for string literals (`status='ERROR'`). `--max-result-records` raises the default row cap for exports.

## Executing things (`dtctl exec`)

```bash
dtctl exec workflow workflow-123 --wait --timeout 10m --show-results
dtctl exec slo slo-123 -o json | jq '.evaluationResults[].errorBudget'
dtctl exec function dynatrace.automations/execute-dql-query -f input.json
dtctl exec function dynatrace.slack/slack-send-message --param channel=ops --param text="hi"
dtctl exec analyzer dt.statistics.GenericForecastAnalyzer -f forecast-input.json
dtctl exec copilot "What is DQL?"
```

## Apply / create / edit / diff

```bash
dtctl create workflow -f my-workflow.yaml
dtctl apply -f my-workflow.yaml --write-id          # idempotent; --write-id stamps the id back into the file
dtctl apply -f dashboard.yaml --id "$DASHBOARD_ID"  # update a specific resource
dtctl edit workflow "My Workflow"                   # fuzzy name match; opens $EDITOR
dtctl diff -f my-workflow.yaml                      # preview local vs remote before apply
dtctl get dashboard abc-123 -o yaml > dashboard.yaml   # export → edit → apply (GitOps loop)
```
This is the Monaco-style config-as-code bridge: `get -o yaml` → edit → `diff` → `apply`.

## Agent mode (use when driving dtctl as an AI agent)

Pass `-A`/`--agent` to wrap **every** output in a structured JSON envelope — parse this instead of scraping tables:

```json
{
  "ok": true,
  "result": [ ... ],
  "context": { "total": 5, "has_more": true, "verb": "get", "resource": "workflow",
               "suggestions": ["Run 'dtctl describe workflow <id>' for details"] }
}
```
- `ok` (bool, always), `result` (data, always; may be null), `error` (`code`, `message`, `operation`, `status_code`, `request_id`, `suggestions`), `context` (`total`, `has_more`, `suggestions`, `warnings`, `duration`, `links`).
- Auto-enabled when dtctl detects an AI-agent environment; implies `--plain`. Opt out with `--no-agent`. Auto-detection is skipped if an explicit `-o` format is set.

## Self-discovery: `dtctl commands`

A machine-readable catalog of every command — ideal for an agent to discover capabilities at runtime instead of guessing:

```bash
dtctl commands -o json            # full catalog
dtctl commands --brief -o json    # compact
dtctl commands workflow -o json   # one resource's commands
dtctl commands howto              # task-oriented how-to guidance
```

## Aliases

```bash
dtctl alias set wf "get workflows"               # dtctl wf  → dtctl get workflows
dtctl alias set errors "query 'fetch logs | filter status=\$1 | limit 100'"   # params: $1, $2…
dtctl errors ERROR
dtctl alias set wf-names "!dtctl get workflows -o json | jq -r '.workflows[].title'"  # ! = run via shell
dtctl alias list | export -f team-aliases.yaml | import -f team-aliases.yaml [--no-overwrite]
```
Alias names can't shadow built-in verbs.

## Installing the official dtctl skill

dtctl can install its **own** AI-assistant skill (agentskills.io standard) — complementary to this one and always matching the installed version:

```bash
dtctl skills install --for claude            # → .claude/skills/dtctl/ (project)
dtctl skills install --for claude --global   # → ~/.claude/skills/dtctl/
dtctl skills install --cross-client          # → .agents/skills/dtctl/ (any compatible agent)
dtctl skills status      # check install state
dtctl skills install --list   # supported agents: claude, copilot, cursor, junie, kiro, opencode, openclaw
```
Run this to get the canonical, version-pinned command reference straight from the tool.
