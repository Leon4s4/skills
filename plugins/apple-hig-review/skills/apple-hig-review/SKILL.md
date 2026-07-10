---
name: apple-hig-review
description: Review SwiftUI code and design specs against Apple Human Interface Guidelines (HIG). Use when reviewing iOS/iPadOS/macOS/watchOS/visionOS screens, components, or flows for HIG compliance. Triggers on requests like "review this against HIG", "check HIG compliance", "does this follow Apple guidelines", "HIG review", "Apple design review", or when reviewing SwiftUI views, navigation patterns, accessibility, typography, color, layout, haptics, permissions, onboarding, or any iOS design decision.
---

# Apple HIG Review

Review SwiftUI code and/or design specs against Apple's Human Interface Guidelines, providing detailed findings with rationale and direct HIG references.

## Workflow

1. **Determine review mode** based on input:
   - **Code review** → User provides SwiftUI files or points to code
   - **Design review** → User provides specs, mockups, or describes a screen/flow
   - **Both** → User provides code + spec together

2. **Identify relevant HIG domains** from the input. Map each screen/component to the checklist domains below.

3. **Fetch live HIG docs** for the relevant domains. Consult [references/hig-urls.md](references/hig-urls.md) and use Firecrawl (`mcp__firecrawl__firecrawl_scrape`) or WebFetch to retrieve the specific HIG pages. Only fetch pages relevant to the review — not all of them.

4. **Audit** against each applicable checklist domain.

5. **Report findings** using the output format below.

## Checklist Domains

For each domain, check the items listed. Skip domains that are clearly irrelevant to the input.

### 1. Navigation & Structure
- Correct use of `NavigationStack` / `NavigationSplitView` (not deprecated `NavigationView`)
- Tab bar has 3–5 tabs, uses SF Symbols, labels are short nouns
- Modal sheets used for focused tasks, not main navigation
- Back button shows parent title (no custom back chevrons replacing system behavior)
- Correct push vs. present semantics

### 2. Layout & Spacing
- Safe area insets respected (no content under notch/home indicator)
- Standard margins: 16pt leading/trailing on iPhone
- Minimum tap target: 44×44 pt
- Content adapts across device sizes (iPhone SE → Pro Max → iPad)
- Scroll views used when content may exceed visible area
- Alignment with system grid and layout guides

### 3. Typography
- Uses system Dynamic Type styles (`title`, `headline`, `body`, `caption`, etc.) — not hardcoded font sizes
- Supports Dynamic Type accessibility sizes (test with largest accessibility size)
- Text truncation handled gracefully (`.lineLimit` with sensible fallbacks)
- No ALL CAPS except for short UI labels where appropriate

### 4. Color & Dark Mode
- Uses semantic colors (`Color.primary`, `.secondary`, `.accentColor`, system backgrounds)
- Full Dark Mode support — no hardcoded `Color.white` / `Color.black` for text/backgrounds
- Sufficient contrast ratios (4.5:1 for body text, 3:1 for large text)
- Vibrancy and materials used correctly on overlays and blurs
- Custom colors defined in asset catalog with light/dark variants

### 5. Icons & Images
- SF Symbols used for system-style icons (not custom PNGs for standard actions)
- Symbol rendering mode correct (monochrome, hierarchical, palette, multicolor)
- Images scaled properly (@1x/@2x/@3x or vector assets)
- Content mode appropriate (`.fit` vs `.fill`)
- Decorative images excluded from accessibility

### 6. Accessibility
- Every interactive element has an accessibility label
- VoiceOver navigation order is logical
- `accessibilityHint` used for non-obvious actions
- Grouping with `accessibilityElement(children: .combine)` where appropriate
- Supports Bold Text, Reduce Motion, Reduce Transparency, Increase Contrast
- Color is not the only indicator of state (use icons/text too)
- Custom actions for complex gestures

### 7. Haptics & Feedback
- Standard haptic patterns: `.success`, `.warning`, `.error`, `.selection`, `.impact`
- Haptics match user expectations (success on completion, not on every tap)
- Respects system "Reduce Motion" and haptic settings
- Visual + haptic feedback together (never haptic-only)

### 8. Alerts, Sheets & Modality
- Alerts used sparingly — only for critical decisions or errors
- Alert button order: default on trailing (right), destructive styled with `.destructive`
- Sheets have clear dismiss affordance (drag or explicit button)
- Confirmation dialogs used for destructive actions
- `.confirmationDialog` preferred over `.alert` for action selection

### 9. Data Entry & Forms
- Correct keyboard type per field (`.emailAddress`, `.numberPad`, `.URL`, etc.)
- Form grouping with `Form` + `Section` for settings-style layouts
- Inline validation with clear error messages
- Secure field for passwords
- Date/time pickers use system styles (not custom wheels)

### 10. Loading & State
- Clear loading indicators (`ProgressView`) for async operations
- Empty states with illustration + message + action button
- Error states with retry affordance
- Skeleton/placeholder views for content-heavy screens
- Pull-to-refresh where content can be stale

### 11. Permissions & Privacy
- Permissions requested in context (at point of use, not at launch)
- Purpose strings (`NSCameraUsageDescription`, etc.) are clear and specific
- Graceful degradation when permission denied
- Settings deep link offered when permission previously denied
- No unnecessary permission requests

### 12. Onboarding
- Max 3–4 screens, skippable
- Shows value, not features
- No login wall before showing value (unless required)
- Welcome screen uses app icon, name, and a clear value proposition

### 13. Search
- Uses `.searchable()` modifier with standard placement
- Search suggestions and recent searches
- Scoped search with tokens where applicable
- Empty search results with helpful message

### 14. Platform Conventions
- Swipe-to-delete with `.onDelete` for list items
- Context menus for secondary actions (`.contextMenu`)
- Share sheet via `ShareLink` or `UIActivityViewController`
- System paste/copy integration
- Respects system text size, bold text, and appearance settings

## Fetching HIG Docs

Consult [references/hig-urls.md](references/hig-urls.md) for the full URL map. Fetch only the pages relevant to the findings.

Example: If reviewing a tab bar implementation, fetch:
- `https://developer.apple.com/design/human-interface-guidelines/tab-bars`
- `https://developer.apple.com/design/human-interface-guidelines/navigation-bars`

Use the fetched content to verify your findings and extract exact HIG quotes for the report.

## Output Format

Use this structure for the review report:

```markdown
# HIG Review: [Screen/Component/Flow Name]

**Review mode:** Code / Design / Both
**Domains checked:** [list of applicable domain numbers]

## Findings

### [PASS | WARN | FAIL] [Domain]: [Short title]

**What:** Description of what was found.

**HIG says:** Direct quote or paraphrase from the fetched HIG page.

**Reference:** [HIG page title](URL)

**In code:** `FileName.swift:lineNumber` (code review only)

**Fix:** Concrete suggestion with code example if applicable.

---

[Repeat for each finding]

## Summary

| Domain | Status | Findings |
|--------|--------|----------|
| Navigation | PASS/WARN/FAIL | count |
| Layout | PASS/WARN/FAIL | count |
| ... | ... | ... |

**Overall:** X passes, Y warnings, Z failures
```

### Severity levels

- **PASS** — Follows HIG correctly. Only mention noteworthy passes (skip obvious ones).
- **WARN** — Technically works but deviates from HIG best practice. Won't cause rejection but reduces polish.
- **FAIL** — Violates HIG. May cause App Store rejection or significant UX degradation.

### Reporting rules

- Lead with FAILs, then WARNs, then notable PASSes.
- Every WARN and FAIL must include a concrete fix.
- Code fixes must show SwiftUI code, not just describe the change.
- Always cite the specific HIG page with URL.
- If unsure whether something violates HIG, fetch the relevant page before ruling.
