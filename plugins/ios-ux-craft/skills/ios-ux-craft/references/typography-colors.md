# Typography, Color System & SF Symbols

## Table of Contents
- [Typography System](#typography-system)
- [Color System](#color-system)
- [SF Symbols](#sf-symbols)
- [Dark Mode](#dark-mode)
- [Custom Fonts](#custom-fonts)
- [Design Tokens Pattern](#design-tokens-pattern)

---

## Typography System

### System Font Styles (Use These)
| Style | Weight | Size (default) | Usage |
|-------|--------|----------------|-------|
| `.largeTitle` | Regular | 34pt | Screen titles (with large title bar) |
| `.title` | Regular | 28pt | Section/card titles |
| `.title2` | Regular | 22pt | Subtitles |
| `.title3` | Regular | 20pt | Small titles |
| `.headline` | Semibold | 17pt | Row titles, emphasized labels |
| `.subheadline` | Regular | 15pt | Secondary labels, metadata |
| `.body` | Regular | 17pt | Primary content text |
| `.callout` | Regular | 16pt | Call-to-action text |
| `.footnote` | Regular | 13pt | Timestamps, attributions |
| `.caption` | Regular | 12pt | Badges, tags, tertiary info |
| `.caption2` | Regular | 11pt | Smallest text (legal, fine print) |

### Weight Modifiers
```swift
Text("Section Title")
    .font(.title3.weight(.semibold))

Text("Emphasize this")
    .font(.body.bold())

// Monospaced for numbers/code
Text("12:45 PM")
    .monospacedDigit()
```

### Text Style Rules
1. **Never use `.system(size:)`** for user-facing text — it breaks Dynamic Type
2. **One `.headline` per row** — it's the row's title, not decoration
3. **Body text is `.body`** — always 17pt at default, scales up/down
4. **Metadata is `.subheadline` or `.footnote`** — with `.secondary` color
5. **Line spacing:** trust system defaults. Only adjust for long-form reading:
   ```swift
   Text(longText)
       .font(.body)
       .lineSpacing(4)
   ```

### Text Hierarchy Pattern
```swift
VStack(alignment: .leading, spacing: 4) {
    Text("Emma's First Steps")           // Title
        .font(.headline)
        .foregroundStyle(.primary)

    Text("A big milestone today!")        // Subtitle/body
        .font(.subheadline)
        .foregroundStyle(.secondary)

    Text("January 15, 2024 · 3:42 PM")   // Metadata
        .font(.caption)
        .foregroundStyle(.tertiary)
}
```

---

## Color System

### Semantic System Colors (Primary Palette)
Use these as the foundation — they adapt to Light/Dark mode automatically.

```swift
// Text colors
.foregroundStyle(.primary)      // High contrast main text
.foregroundStyle(.secondary)    // Medium contrast secondary text
.foregroundStyle(.tertiary)     // Low contrast tertiary text

// Background colors
Color(.systemBackground)                // Main background
Color(.secondarySystemBackground)       // Grouped/card background
Color(.tertiarySystemBackground)        // Inner nested background

// Grouped variant
Color(.systemGroupedBackground)         // Full-screen grouped bg
Color(.secondarySystemGroupedBackground) // Section within grouped
Color(.tertiarySystemGroupedBackground)  // Inner element
```

### Accent Color
```swift
// Set app-wide accent in Asset Catalog → AccentColor
// Or per-view:
.tint(.appCoral) // Custom accent color
```

- The accent color is used for interactive elements: buttons, links, toggles, tab selection
- Define it once in the Asset Catalog as `AccentColor`
- Override with `.tint()` only for specific components that need differentiation

### Semantic UI Colors
```swift
Color(.label)              // Adaptable text (same as .primary foreground)
Color(.secondaryLabel)     // Same as .secondary
Color(.separator)          // Thin line dividers
Color(.opaqueSeparator)    // Opaque dividers
Color(.link)               // Tappable link color (system blue unless overridden)
Color(.placeholderText)    // TextField placeholder
Color(.systemFill)         // Thin overlay fill
Color(.secondarySystemFill)
Color(.tertiarySystemFill)
Color(.quaternarySystemFill)
```

### Custom Colors — Asset Catalog Pattern
1. Create colors in `Assets.xcassets` with both Any Appearance and Dark Appearance variants
2. Reference in code:

```swift
extension Color {
    static let appCoral = Color("AppCoral")          // #EC8E78
    static let appSage = Color("AppSage")            // #78AE97
    static let appAmber = Color("AppAmber")           // #DFB34A
    static let appBackground = Color("AppBackground")
}

extension ShapeStyle where Self == Color {
    static var appCoral: Color { .appCoral }
    static var appSage: Color { .appSage }
}
```

**Rules for Custom Colors:**
- Always provide Light + Dark variants
- Test with Increase Contrast — provide high-contrast variants if needed
- Custom colors for branding only — use system colors for standard UI

### Material Backgrounds
```swift
.background(.ultraThinMaterial)  // Blurred background, very transparent
.background(.thinMaterial)       // Slightly more opaque
.background(.regularMaterial)    // Standard blur (toolbars, overlays)
.background(.thickMaterial)      // Dense blur
.background(.ultraThickMaterial) // Nearly opaque blur
.background(.bar)                // Match system bar appearance
```

Use materials for overlays, floating elements, and toolbars — they adapt to Light/Dark mode and provide the signature Apple "frosted glass" effect.

---

## SF Symbols

### Selection Guidelines
| Category | Recommended Symbols |
|----------|-------------------|
| Navigation | `chevron.right`, `arrow.left`, `xmark` |
| Actions | `plus`, `pencil`, `trash`, `square.and.arrow.up` |
| Media | `photo`, `video`, `mic`, `play.fill`, `pause.fill` |
| Status | `checkmark.circle.fill`, `exclamationmark.triangle.fill`, `xmark.circle.fill` |
| People | `person`, `person.2`, `person.crop.circle` |
| Time | `calendar`, `clock`, `timer` |
| Favorites | `heart`, `heart.fill`, `star`, `star.fill`, `bookmark`, `bookmark.fill` |

### Rendering Modes
```swift
// Monochrome (default) — single color, follows tint
Image(systemName: "heart.fill")
    .foregroundStyle(.red)

// Hierarchical — automatic layered opacity
Image(systemName: "square.and.arrow.up.circle.fill")
    .symbolRenderingMode(.hierarchical)
    .foregroundStyle(.blue)

// Palette — explicit multi-color layers
Image(systemName: "person.crop.circle.badge.checkmark")
    .symbolRenderingMode(.palette)
    .foregroundStyle(.blue, .green)

// Multicolor — Apple's preset colors (weather, file types)
Image(systemName: "cloud.sun.rain.fill")
    .symbolRenderingMode(.multicolor)
```

### Symbol Effects (iOS 17+)
```swift
// Bounce — attention-grabbing
Image(systemName: "bell.fill")
    .symbolEffect(.bounce, value: notificationCount)

// Pulse — ongoing activity
Image(systemName: "mic.fill")
    .symbolEffect(.pulse, isActive: isRecording)

// Variable color — progress indication
Image(systemName: "wifi")
    .symbolEffect(.variableColor.iterative, isActive: isConnecting)

// Replace — swap symbol with animation
Image(systemName: isFavorite ? "heart.fill" : "heart")
    .contentTransition(.symbolEffect(.replace))

// Scale — emphasis
Image(systemName: "star.fill")
    .symbolEffect(.scale.up, isActive: isHighlighted)
```

### Symbol Sizing
```swift
// Match text size (preferred)
Label("Settings", systemImage: "gear")
    .font(.body)

// Explicit image scale
Image(systemName: "plus")
    .imageScale(.large) // .small, .medium, .large

// Font-relative sizing
Image(systemName: "photo")
    .font(.title2)
```

**Rules:**
- Prefer SF Symbols over custom icons — they scale, adapt, and localize automatically
- Use `.fill` variants for selected/active states, outline for inactive
- Use symbol effects sparingly — one animated symbol per visible area
- Always pair symbols with text labels in toolbars and tabs

---

## Dark Mode

### Implementation Rules
1. **Never use hardcoded colors** like `Color.white` or `Color.black` for UI elements
2. **Use semantic colors** — `.primary`, `.background`, etc. adapt automatically
3. **Custom colors** must have explicit Dark Mode variants in the Asset Catalog
4. **Test every screen** in both modes

### Common Mistakes
```swift
// BAD — white background is blinding in dark mode
.background(Color.white)

// GOOD — adapts automatically
.background(Color(.systemBackground))

// BAD — black text invisible on dark background
.foregroundColor(.black)

// GOOD — high contrast in both modes
.foregroundStyle(.primary)

// BAD — shadow invisible in dark mode
.shadow(color: .black.opacity(0.1), radius: 4)

// GOOD — adapts
.shadow(color: .primary.opacity(0.1), radius: 4)
```

### Preview Both Modes
```swift
#Preview {
    ContentView()
        .preferredColorScheme(.light)
}

#Preview("Dark Mode") {
    ContentView()
        .preferredColorScheme(.dark)
}
```

Always create previews for both modes.

---

## Custom Fonts

When using custom fonts (e.g., Quicksand, Nunito):

```swift
// Register in Info.plist under "Fonts provided by application"
// Then create a type-safe extension:

extension Font {
    static func quicksand(_ style: Font.TextStyle, weight: Font.Weight = .bold) -> Font {
        let size = UIFont.preferredFont(forTextStyle: style.uiTextStyle).pointSize
        return .custom("Quicksand", size: size, relativeTo: style)
    }

    static func nunito(_ style: Font.TextStyle, weight: Weight = .regular) -> Font {
        let size = UIFont.preferredFont(forTextStyle: style.uiTextStyle).pointSize
        let name = weight == .semibold ? "Nunito-SemiBold" : "Nunito-Regular"
        return .custom(name, size: size, relativeTo: style)
    }
}
```

**Critical:** Always use `relativeTo:` parameter — this enables Dynamic Type scaling for custom fonts. Without it, custom fonts are fixed-size and break accessibility.

---

## Design Tokens Pattern

Centralize design values for consistency:

```swift
enum DesignTokens {
    enum Spacing {
        static let micro: CGFloat = 4
        static let small: CGFloat = 8
        static let medium: CGFloat = 16
        static let large: CGFloat = 20
        static let xlarge: CGFloat = 32
    }

    enum CornerRadius {
        static let small: CGFloat = 8
        static let medium: CGFloat = 12
        static let large: CGFloat = 16
        static let pill: CGFloat = .infinity
    }

    enum Shadow {
        static let subtle = (color: Color.primary.opacity(0.06), radius: 4.0, y: 2.0)
        static let medium = (color: Color.primary.opacity(0.1), radius: 8.0, y: 4.0)
    }

    enum Animation {
        static let snappy = SwiftUI.Animation.spring(duration: 0.3, bounce: 0.2)
        static let gentle = SwiftUI.Animation.spring(duration: 0.4, bounce: 0.1)
        static let bouncy = SwiftUI.Animation.spring(duration: 0.35, bounce: 0.4)
    }
}
```

Reference tokens everywhere:
```swift
.padding(DesignTokens.Spacing.medium)
.clipShape(.rect(cornerRadius: DesignTokens.CornerRadius.medium))
```

This prevents magic numbers and ensures consistency across the entire app.
