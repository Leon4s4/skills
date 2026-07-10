---
name: ios-ux-craft
description: Build Apple-quality iOS UX/UI with SwiftUI (iOS 17+). Enforces Apple Human Interface Guidelines, accessibility (VoiceOver, Dynamic Type, contrast), native component patterns, animations, haptics, and visual polish. Use this skill when building, reviewing, or refining any SwiftUI screen, component, or interaction — including new views, UI refactors, design reviews, layout work, form design, navigation structure, animation polish, accessibility audits, or any task where the goal is a native-feeling, HIG-compliant iOS experience.
---

# iOS UX Craft

Build every SwiftUI screen to the standard Apple sets in its own apps: HIG-compliant, fully accessible, and visually polished with native animations and haptics.

## Core Mandates

1. **Accessibility is not optional.** Every screen must work with VoiceOver, scale to the largest Dynamic Type, meet WCAG 2.1 AA contrast ratios, and respect Reduce Motion. A screen that isn't accessible is not done.
2. **Use system components first.** Native `List`, `Form`, `NavigationStack`, `TabView`, `Sheet`, `Alert`, `ConfirmationDialog`, `ContentUnavailableView`, `ProgressView`, `PhotosPicker` — before building custom.
3. **Spring animations are the default.** Never use `.easeInOut` or `.linear` for UI interactions. Use `.spring()` with appropriate duration and bounce.
4. **No magic numbers.** Use design tokens for spacing, corner radii, and animations. Use semantic font styles (`.body`, `.headline`) — never `.system(size:)`.
5. **44x44pt minimum touch targets.** Every tappable element, no exceptions.
6. **Test both modes.** Every view must work in Light Mode, Dark Mode, and with Increase Contrast enabled.

## Workflow

When building or reviewing a SwiftUI view, follow this order:

### 1. Structure & Navigation
Determine the right navigation pattern (push, sheet, fullScreenCover, tab) and set the correct `navigationTitle` and display mode. Reference: [hig-patterns.md](references/hig-patterns.md)

### 2. Layout & Components
Build using native components and standard spacing. Use `List`/`Form` for data-driven content, proper section grouping, and semantic layout. Reference: [swiftui-components.md](references/swiftui-components.md)

### 3. Typography & Color
Apply semantic font styles and system colors. Set up custom colors in Asset Catalog with Light/Dark variants. Use SF Symbols with correct rendering mode. Reference: [typography-colors.md](references/typography-colors.md)

### 4. States
Every data-driven view needs three states:
- **Loading** — `ProgressView()` or `.redacted(reason: .placeholder)`
- **Empty** — `ContentUnavailableView` with an action to resolve
- **Error** — Inline retry, never raw error messages

### 5. Animation & Feedback
Add spring animations to state changes, transitions to appearing/disappearing content, and haptic feedback to meaningful interactions. Reference: [animations-haptics.md](references/animations-haptics.md)

### 6. Accessibility Pass
Apply VoiceOver labels, group related elements, ensure Dynamic Type scaling, verify contrast, and add Reduce Motion fallbacks. This is mandatory, not a nice-to-have. Reference: [accessibility.md](references/accessibility.md)

## Quick Reference — Common Patterns

### Modal with Save/Cancel
```swift
.toolbar {
    ToolbarItem(placement: .cancellationAction) {
        Button("Cancel") { dismiss() }
    }
    ToolbarItem(placement: .confirmationAction) {
        Button("Save") { save() }
            .bold()
            .disabled(!isValid)
    }
}
.interactiveDismissDisabled(hasChanges)
```

### Destructive Action
```swift
Button("Delete", role: .destructive) { showConfirmation = true }
.confirmationDialog("Delete Memory?", isPresented: $showConfirmation, titleVisibility: .visible) {
    Button("Delete", role: .destructive) { performDelete() }
}
```

### Spring Animation
```swift
withAnimation(.spring(duration: 0.3, bounce: 0.2)) {
    isExpanded.toggle()
}
```

### Reduce Motion Fallback
```swift
@Environment(\.accessibilityReduceMotion) private var reduceMotion
withAnimation(reduceMotion ? .none : .spring(duration: 0.3, bounce: 0.2)) { ... }
```

### Dynamic Type Adaptation
```swift
@Environment(\.dynamicTypeSize) private var typeSize
if typeSize.isAccessibilitySize {
    VStack(alignment: .leading) { content }
} else {
    HStack { content }
}
```

## HIG Compliance Checklist

Run through this for every screen before considering it complete:

- [ ] `navigationTitle` set, correct display mode
- [ ] All touch targets >= 44x44pt
- [ ] Standard spacing tokens (no hardcoded values)
- [ ] Safe areas respected
- [ ] Loading, empty, and error states implemented
- [ ] One `.borderedProminent` CTA maximum per screen
- [ ] Destructive actions require confirmation
- [ ] SF Symbols used for icons
- [ ] Dynamic Type supported — no fixed font sizes
- [ ] Dark Mode works correctly
- [ ] VoiceOver navigable with proper labels
- [ ] Reduce Motion respected
- [ ] Color contrast meets WCAG 2.1 AA
- [ ] Information not conveyed by color alone

## References

Detailed patterns and code examples for each area:

- **[hig-patterns.md](references/hig-patterns.md)** — Navigation, layout, spacing, modality, controls, platform conventions
- **[swiftui-components.md](references/swiftui-components.md)** — List rows, forms, cards, media, toolbars, search, scroll behaviors
- **[animations-haptics.md](references/animations-haptics.md)** — Spring presets, transitions, matched geometry, phase/keyframe animations, haptic mapping
- **[accessibility.md](references/accessibility.md)** — VoiceOver, Dynamic Type, contrast, motion, touch targets, focus management
- **[typography-colors.md](references/typography-colors.md)** — Font styles, system colors, SF Symbols, Dark Mode, custom fonts, design tokens
