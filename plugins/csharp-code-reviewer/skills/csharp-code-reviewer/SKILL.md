---
name: csharp-code-reviewer
description: Review C# code changes in git repositories with deep expertise in Microsoft Dynamics 365 CRM, GraphQL with Hot Chocolate, and .NET best practices. Use this skill when reviewing pull requests, comparing branches, analyzing diffs, or auditing C# code quality. Supports plugin development, Dataverse SDK patterns, IOrganizationService usage, resolver patterns, DataLoader optimization, and schema design. Generates markdown reports with severity-ranked findings and auto-fix suggestions.
---

# C# Code Reviewer

Review C# code changes with specialized knowledge of Dynamics 365 CRM, GraphQL/Hot Chocolate, and modern .NET patterns. Produces markdown reports with actionable findings and fix suggestions.

## Workflow

1. **Get the diff** — Compare branches and extract changed `.cs` files
2. **Analyze changes** — Apply domain-specific review rules
3. **Generate report** — Markdown with severity-ranked findings and fixes

## Git Operations

```bash
# Compare branches (primary workflow)
git diff <base-branch>..<feature-branch> -- "*.cs"

# List changed files
git diff --name-only <base-branch>..<feature-branch> -- "*.cs"

# Show specific file diff with context
git diff <base-branch>..<feature-branch> -- path/to/file.cs

# View file at specific branch
git show <branch>:path/to/file.cs

# Commits between branches
git log --oneline <base-branch>..<feature-branch>

# Blame for context on existing code
git blame -L <start>,<end> path/to/file.cs
```

## Review Process

### Step 1: Extract Changes

```bash
# Get list of changed C# files
git diff --name-only <base>..<feature> -- "*.cs"

# Get full diff for analysis
git diff <base>..<feature> -- "*.cs" > /tmp/changes.diff
```

### Step 2: Categorize Files

Identify file types to apply appropriate rules:

| Pattern | Category | Reference |
|---------|----------|-----------|
| `*Plugin*.cs`, `*Step*.cs` | Dynamics Plugin | [dynamics365.md](references/dynamics365.md) |
| `*Resolver*.cs`, `*Query*.cs`, `*Mutation*.cs` | GraphQL | [hotchocolate.md](references/hotchocolate.md) |
| `*DataLoader*.cs` | DataLoader | [hotchocolate.md](references/hotchocolate.md) |
| `*Service*.cs`, `*Repository*.cs` | Business Logic | General .NET rules |
| `*Test*.cs`, `*Tests.cs` | Unit Tests | Test patterns |

### Step 3: Apply Review Rules

Load the appropriate reference based on file category:

- **Dynamics 365 code**: Read [references/dynamics365.md](references/dynamics365.md)
- **GraphQL/Hot Chocolate code**: Read [references/hotchocolate.md](references/hotchocolate.md)

### Step 4: Generate Report

Output format:

```markdown
# Code Review Report

**Branch**: `feature/xyz` → `main`  
**Files Reviewed**: 12  
**Generated**: 2025-01-29

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 2 |
| 🟠 Warning | 5 |
| 🟡 Suggestion | 8 |
| 🟢 Nitpick | 3 |

## Findings

### 🔴 Critical

#### [CR-001] Missing null check in plugin (AccountPlugin.cs:45)

**Issue**: `target.GetAttributeValue<string>("name")` called without null check.

**Current**:
```csharp
var name = target.GetAttributeValue<string>("name");
var upper = name.ToUpper(); // NullReferenceException risk
```

**Suggested Fix**:
```csharp
var name = target.GetAttributeValue<string>("name");
if (string.IsNullOrEmpty(name)) return;
var upper = name.ToUpper();
```

**Why**: Plugin will throw at runtime if attribute missing.

---

### 🟠 Warning

#### [CR-002] N+1 query in resolver (ContactResolver.cs:23)
...
```

## Severity Definitions

| Level | Meaning | Action |
|-------|---------|--------|
| 🔴 Critical | Runtime errors, data loss, security issues | Must fix before merge |
| 🟠 Warning | Performance issues, maintainability problems | Should fix |
| 🟡 Suggestion | Better patterns exist, minor improvements | Consider fixing |
| 🟢 Nitpick | Style, naming, minor preferences | Optional |

## Common Patterns

### Always Check

1. **Null safety** — Especially in plugins and resolvers
2. **Exception handling** — Proper try-catch with logging
3. **Async/await** — No `.Result` or `.Wait()` blocking calls
4. **Disposal** — `IDisposable` resources properly disposed
5. **Thread safety** — Static fields, shared state

### Code Smells

- Methods > 50 lines
- Classes > 500 lines
- Deeply nested conditionals (> 3 levels)
- Magic strings/numbers without constants
- Commented-out code
- Missing XML documentation on public APIs
