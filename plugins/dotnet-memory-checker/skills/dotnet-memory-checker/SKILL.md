---
name: dotnet-memory-checker
description: Scan C# .NET 8+ projects for memory leaks, GC issues, and high memory usage. Performs static code analysis via grep patterns and provides runtime diagnostic commands. Use when user asks to check for memory leaks, analyze memory usage, find disposal issues, detect GC problems, audit memory patterns, or optimize memory in a .NET/C# project. Produces a structured severity-rated markdown report.
---

# .NET Memory Checker

Scan C# .NET 8+ codebases for memory leaks, GC issues, and high memory usage. Two modes: **static scan** (grep-based code analysis) and **runtime diagnostics** (dotnet tool commands).

## Workflow

1. Determine mode: static scan, runtime diagnostics, or both
2. For static scan: run grep patterns from [patterns.md](references/patterns.md) against `.cs` files
3. For runtime diagnostics: guide user through commands from [runtime-diagnostics.md](references/runtime-diagnostics.md)
4. Generate structured report

## Static Scan

Read [patterns.md](references/patterns.md) for all grep patterns. Run each pattern category using the Grep tool against `*.cs` files in the project. For each match:

- Record file path, line number, matched code
- Assign severity from the pattern definition
- Skip matches in test files (`*Tests.cs`, `*Test.cs`, `*.Spec.cs`) unless user requests otherwise
- Skip matches in `obj/`, `bin/`, `Migrations/` directories

### Scan execution order (by severity)

1. **CRITICAL** — Undisposed resources, HttpClient misuse, static event handlers
2. **HIGH** — Event leaks, unbounded static collections, async void, timer leaks
3. **MEDIUM** — Missing ArrayPool usage, unnecessary ToList/ToArray, string concat in loops, finalizer issues
4. **LOW** — Missing using declarations, optimization opportunities (Span, stackalloc)

### False positive reduction

- `new HttpClient(` — skip if inside a factory method, `IHttpClientFactory`, or a static field assignment
- `+=` on events — skip if a matching `-=` exists in the same class
- `static List/Dictionary` — skip if `.Remove`, `.Clear`, or `.TryRemove` is called on it in the same file
- `.ToList()` / `.ToArray()` — skip if the result is modified (`.Add`, `.Sort`, `.RemoveAt`, index assignment)
- `async void` — skip if method name matches common event handler patterns (`_Click`, `_Changed`, `_Loaded`, `OnHandler`)

## Runtime Diagnostics

Read [runtime-diagnostics.md](references/runtime-diagnostics.md) for commands. Guide the user through:

1. **Live monitoring** — `dotnet-counters` to observe GC heap size, gen counts, alloc rate, time-in-gc
2. **Heap snapshots** — `dotnet-gcdump` for lightweight heap analysis
3. **Full dump analysis** — `dotnet-dump` with SOS commands for root cause
4. **Event tracing** — `dotnet-trace` with GC providers for allocation profiling
5. **GC tuning** — Configuration recommendations from [gc-config.md](references/gc-config.md)

## Analyzer Recommendations

Read [analyzers.md](references/analyzers.md) for NuGet packages and rules to recommend adding to the project's `.csproj` and `.editorconfig`.

## Report Format

Generate the report as a markdown file with this structure:

```markdown
# .NET Memory Analysis Report
**Project:** {project name}
**Date:** {date}
**Scan type:** {Static / Runtime / Both}

## Summary
| Severity | Count |
|----------|-------|
| CRITICAL | N |
| HIGH     | N |
| MEDIUM   | N |
| LOW      | N |

## Critical Issues
### [CRIT-001] {Issue title}
- **File:** `path/to/File.cs:42`
- **Pattern:** {what was detected}
- **Code:** `{matched line}`
- **Risk:** {why this is dangerous}
- **Fix:** {how to fix with code example}

## High Issues
{same format}

## Medium Issues
{same format}

## Low Issues
{same format}

## Recommendations
### Analyzer Packages
{recommended NuGet packages to add}

### GC Configuration
{recommended runtimeconfig.json settings if applicable}

### Runtime Diagnostic Commands
{commands to run for deeper investigation}
```
