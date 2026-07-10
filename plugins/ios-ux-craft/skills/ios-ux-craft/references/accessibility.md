# Accessibility — Mandatory Requirements

## Table of Contents
- [Core Principle](#core-principle)
- [VoiceOver](#voiceover)
- [Dynamic Type](#dynamic-type)
- [Color & Contrast](#color--contrast)
- [Motion](#motion)
- [Touch Targets](#touch-targets)
- [Focus Management](#focus-management)
- [Testing Checklist](#testing-checklist)

---

## Core Principle

Every feature ships accessible. Accessibility is not a follow-up task — it's a launch-blocking requirement. If a screen doesn't work with VoiceOver and Dynamic Type, it's not done.

---

## VoiceOver

### Labels & Hints
```swift
Button {
    toggleFavorite()
} label: {
    Image(systemName: isFavorite ? "heart.fill" : "heart")
}
.accessibilityLabel(isFavorite ? "Unfavorite" : "Favorite")
.accessibilityHint("Double tap to \(isFavorite ? "remove from" : "add to") favorites")
```

**Rules:**
- Every interactive element must have an `accessibilityLabel`
- Labels describe **what it is**, hints describe **what happens**
- Labels should be concise: "Favorite" not "Tap this button to favorite this memory"
- Don't include the control type in the label — VoiceOver adds "button" automatically
- Update labels to reflect state: "Unfavorite" when already favorited

### Grouping
```swift
// Group related elements into one VoiceOver stop
HStack {
    Image(systemName: "calendar")
    Text("January 15, 2024")
}
.accessibilityElement(children: .combine) // Reads as one element

// Custom grouped reading
VStack {
    Text(baby.name)
    Text("\(baby.age) months old")
    Text(baby.milestone)
}
.accessibilityElement(children: .ignore)
.accessibilityLabel("\(baby.name), \(baby.age) months old, \(baby.milestone)")
```

**Rules:**
- Group related info so VoiceOver doesn't stop on each piece separately
- Use `.combine` when children read naturally together
- Use `.ignore` + custom label when you need to control the exact reading

### Images
```swift
// Decorative image — skip in VoiceOver
Image("background-pattern")
    .accessibilityHidden(true)

// Informative image
Image("baby-photo")
    .accessibilityLabel("Photo of Emma at the park")

// Icon that conveys meaning
Image(systemName: "checkmark.circle.fill")
    .foregroundStyle(.green)
    .accessibilityLabel("Completed")
```

- Decorative images: `.accessibilityHidden(true)`
- Informative images: descriptive `.accessibilityLabel`
- SF Symbols get automatic labels but override them when context matters

### Custom Actions
```swift
// Memory card with multiple actions
MemoryCardView(memory: memory)
    .accessibilityAction(named: "Edit") { editMemory(memory) }
    .accessibilityAction(named: "Share") { shareMemory(memory) }
    .accessibilityAction(named: "Delete") { deleteMemory(memory) }
```

Use for elements with context menus, swipe actions, or multiple touch interactions.

### Rotor & Custom Content
```swift
// Let VoiceOver announce value changes
.accessibilityValue("\(photoCount) photos")
.accessibilityAddTraits(.updatesFrequently) // For live-updating content

// Sort order for VoiceOver navigation
.accessibilitySortPriority(1) // Higher = read first
```

---

## Dynamic Type

### Text Scaling
```swift
// CORRECT — scales with Dynamic Type
Text("Hello")
    .font(.body)

Text("Title")
    .font(.title2)

// WRONG — fixed size ignores Dynamic Type
Text("Hello")
    .font(.system(size: 16)) // Never do this

// Exception: when space is truly fixed (tab bar badges, avatar initials)
Text("3")
    .font(.system(size: 10))
    .dynamicTypeSize(...DynamicTypeSize.xxxLarge) // Cap the max scaling
```

**Rules:**
- Always use semantic font styles (`.body`, `.headline`, `.caption`, etc.)
- Use `@ScaledMetric` for dimensions that should scale with text size
- Test at `.accessibilityExtraExtraExtraLarge` — layout must not break

### Scaled Metrics
```swift
@ScaledMetric(relativeTo: .body) private var iconSize: CGFloat = 24
@ScaledMetric(relativeTo: .body) private var spacing: CGFloat = 12

Image(systemName: "star")
    .frame(width: iconSize, height: iconSize)
```

### Layout Adaptation
```swift
@Environment(\.dynamicTypeSize) private var typeSize

var body: some View {
    if typeSize.isAccessibilitySize {
        // Stack vertically at very large sizes
        VStack(alignment: .leading, spacing: 8) {
            icon
            labels
        }
    } else {
        // Horizontal layout at normal sizes
        HStack(spacing: 12) {
            icon
            labels
        }
    }
}
```

- At accessibility sizes, switch horizontal layouts to vertical
- Use `ViewThatFits` (iOS 16+) for automatic layout switching
- Never truncate text at large sizes — let it wrap

### ViewThatFits
```swift
ViewThatFits(in: .horizontal) {
    HStack { icon; label; value }  // Preferred: horizontal
    VStack(alignment: .leading) { HStack { icon; label }; value }  // Fallback: stacked
}
```

---

## Color & Contrast

### Minimum Contrast Ratios (WCAG 2.1 AA)
| Element | Ratio |
|---------|-------|
| Body text | 4.5:1 |
| Large text (>= 18pt or 14pt bold) | 3:1 |
| UI components / icons | 3:1 |
| Decorative | No requirement |

### System Colors
```swift
// These automatically adapt to Light/Dark mode and accessibility settings
Text("Primary").foregroundStyle(.primary)     // High contrast text
Text("Secondary").foregroundStyle(.secondary) // Medium contrast
Text("Tertiary").foregroundStyle(.tertiary)   // Low contrast (decorative)

// Background colors
.background(.background)           // System background
.background(.secondarySystemBackground) // Grouped content
```

**Rules:**
- Use `.primary`, `.secondary`, `.tertiary` for text — they handle contrast automatically
- Custom colors must provide both Light and Dark variants in the asset catalog
- Never rely on color alone to convey information — always pair with icons or text
- Test with Increase Contrast accessibility setting enabled

### Differentiate Without Color
```swift
// BAD: Color-only status
Circle().fill(isOnline ? .green : .red)

// GOOD: Color + icon
Image(systemName: isOnline ? "checkmark.circle.fill" : "xmark.circle.fill")
    .foregroundStyle(isOnline ? .green : .red)
    .accessibilityLabel(isOnline ? "Online" : "Offline")
```

---

## Motion

See [animations-haptics.md](animations-haptics.md#motion-accessibility) for full Reduce Motion patterns.

```swift
@Environment(\.accessibilityReduceMotion) private var reduceMotion
```

- Replace movement with opacity fades when Reduce Motion is on
- Disable all ambient/decorative animations
- Keep user-initiated direct-manipulation animations

---

## Touch Targets

### Minimum 44x44pt
```swift
// Small icon button — expand touch target
Button {
    action()
} label: {
    Image(systemName: "ellipsis")
        .font(.body)
}
.frame(minWidth: 44, minHeight: 44)
.contentShape(.rect)

// Text link in a paragraph
Button("Terms of Service") { showTerms() }
    .padding(.vertical, 8) // Ensure adequate vertical target
```

**Rules:**
- Every tappable element: minimum 44x44pt touch target
- Use `.contentShape(.rect)` to expand tap area beyond visible bounds
- Adjacent touch targets should have at least 8pt gap between them
- Test with "Show Accessibility Inspector" > "Point and Speak" in simulator

---

## Focus Management

### Focus State for Forms
```swift
enum FormField: Hashable {
    case name, email, message
}

@FocusState private var focusedField: FormField?

var body: some View {
    Form {
        TextField("Name", text: $name)
            .focused($focusedField, equals: .name)
            .submitLabel(.next)
            .onSubmit { focusedField = .email }

        TextField("Email", text: $email)
            .focused($focusedField, equals: .email)
            .submitLabel(.next)
            .onSubmit { focusedField = .message }

        TextField("Message", text: $message)
            .focused($focusedField, equals: .message)
            .submitLabel(.done)
            .onSubmit { submit() }
    }
}
```

- Chain focus through form fields with `.submitLabel` and `.onSubmit`
- Dismiss keyboard with `focusedField = nil`
- Set initial focus with `.onAppear { focusedField = .name }` when appropriate

### VoiceOver Focus Announcements
```swift
// Post notification when content changes dynamically
.onChange(of: saveCompleted) { _, completed in
    if completed {
        AccessibilityNotification.Announcement("Memory saved successfully").post()
    }
}

// Move VoiceOver focus to new content
.accessibilityFocused($isErrorFocused)
```

---

## Testing Checklist

For every screen, verify all of the following:

### VoiceOver
- [ ] Navigate the entire screen with VoiceOver — every element is reachable
- [ ] All interactive elements have clear, concise labels
- [ ] Decorative elements are hidden from VoiceOver
- [ ] Related elements are grouped logically
- [ ] State changes are announced (e.g., "Favorited", "Saved")
- [ ] Reading order is logical (top to bottom, leading to trailing)
- [ ] Custom actions available for elements with swipe/context menu actions

### Dynamic Type
- [ ] All text scales up to `.accessibilityExtraExtraExtraLarge`
- [ ] Layout doesn't break or overlap at largest type sizes
- [ ] Horizontal layouts adapt to vertical at accessibility sizes
- [ ] No text is truncated at large sizes (unless explicitly designed with `lineLimit`)
- [ ] Icons scale proportionally (via `@ScaledMetric`)

### Color & Contrast
- [ ] All text meets 4.5:1 contrast ratio (3:1 for large text)
- [ ] UI works correctly in Dark Mode
- [ ] UI works correctly with Increase Contrast enabled
- [ ] Information is not conveyed by color alone
- [ ] Custom colors have Light and Dark variants

### Motion
- [ ] Animations are reduced/eliminated with Reduce Motion enabled
- [ ] No auto-playing animations that can't be paused

### General
- [ ] All touch targets are at least 44x44pt
- [ ] Form fields have proper keyboard types and submit labels
- [ ] Focus moves logically through form fields
- [ ] Error messages are accessible and announced
