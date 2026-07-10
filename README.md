# Leon4s4 Skills Marketplace

A [Claude Code plugin marketplace](https://docs.claude.com/en/docs/claude-code/plugins) of agent skills.

## Install

```
/plugin marketplace add Leon4s4/skills
/plugin install <plugin-name>@leon4s4-skills
```

## Plugins

| Plugin | Description |
|--------|-------------|
| `apple-hig-review` | Review SwiftUI code and design specs against Apple Human Interface Guidelines (HIG) |
| `cf-cli-mastery` | Deploy, manage, troubleshoot, and operate applications on Cloud Foundry via the CF CLI |
| `csharp-code-reviewer` | Review C# code changes with Dynamics 365 CRM, Hot Chocolate GraphQL, and .NET expertise |
| `dataverse-api-limits` | Handle Microsoft Dataverse / Power Apps service protection API limits and throttling |
| `dotnet-memory-checker` | Scan C# .NET 8+ projects for memory leaks, GC issues, and high memory usage |
| `dynatrace` | Query, ingest, and automate Dynatrace observability data (DQL, Grail, dtctl, APIs) |
| `dynatrace-dashboards` | Create, modify, analyze, and deploy Dynatrace platform (Gen3 / Grail) dashboards |
| `ios-ux-craft` | Build Apple-quality iOS UX/UI with SwiftUI (iOS 17+) |
| `pact-dotnet` | Build consumer and provider contract tests using PactNet 5.x for GraphQL APIs |
| `spec-verifier` | Pre-development specification validator and completeness checker |

## Layout

Each plugin lives under `plugins/<name>/` with a `.claude-plugin/plugin.json` manifest and its
skill in `skills/<name>/` (SKILL.md plus optional `references/`, `assets/`, `scripts/`).
The catalog is `.claude-plugin/marketplace.json`.
