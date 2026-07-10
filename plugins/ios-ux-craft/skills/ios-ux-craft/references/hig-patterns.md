# Apple Human Interface Guidelines — SwiftUI Patterns

## Table of Contents
- [Navigation](#navigation)
- [Layout & Spacing](#layout--spacing)
- [Modality](#modality)
- [Controls & Inputs](#controls--inputs)
- [Feedback & Status](#feedback--status)
- [Platform Conventions](#platform-conventions)
- [HIG Compliance Checklist](#hig-compliance-checklist)

---

## Navigation

### NavigationStack (primary)
Use for hierarchical drill-down flows. Every screen that pushes to a detail uses `NavigationStack` with `navigationDestination(for:)`.

```swift
NavigationStack(path: $path) {
    List(items) { item in
        NavigationLink(value: item) {
            ItemRow(item: item)
        }
    }
    .navigationTitle("Items")
    .navigationDestination(for: Item.self) { item in
        ItemDetail(item: item)
    }
}
```

**Rules:**
- Always set `.navigationTitle()` — never leave a screen untitled
- Use `.navigationBarTitleDisplayMode(.large)` for root screens, `.inline` for pushed screens
- Back button text should be the *previous* screen's short title (auto if using `.navigationTitle`)
- Never hide the back button unless providing a clear alternative (e.g., close button on modal)

### TabView (root)
Use for 3–5 top-level sections. Each tab has its own `NavigationStack`.

```swift
TabView {
    Tab("Feed", systemImage: "rectangle.stack") {
        NavigationStack { FeedView() }
    }
    Tab("Profile", systemImage: "person") {
        NavigationStack { ProfileView() }
    }
}
```

**Rules:**
- 3–5 tabs maximum. Use "More" tab if exceeding 5
- Each tab label: 1 word preferred, 2 words maximum
- SF Symbol must visually match the tab's function
- Tab order: most-used sections first (left to right)
- Tab state should persist when switching tabs (don't reset NavigationStack)

### Sheets vs Full-Screen Covers
| Use case | Presentation | Dismiss |
|----------|-------------|---------|
| Non-blocking task (filter, quick edit) | `.sheet` | Swipe down or Cancel |
| Blocking task (compose, onboarding) | `.fullScreenCover` | Explicit Done/Cancel button |
| Confirmation / small choice | `.confirmationDialog` | Tap option or Cancel |
| Destructive action confirmation | `.alert` | Confirm / Cancel |

**Rules:**
- Sheets should have a visible grabber (`.presentationDragIndicator(.visible)`) for discoverability
- Use `.presentationDetents([.medium, .large])` when content doesn't need full height
- Always provide Cancel/Done buttons in toolbar — don't rely solely on swipe to dismiss
- For forms in sheets: Cancel (leading) + Save/Done (trailing) in `.toolbar`

---

## Layout & Spacing

### Standard Spacing Values
| Token | Value | Usage |
|-------|-------|-------|
| Micro | 4pt | Icon-to-label gaps, tight grouping |
| Small | 8pt | Between related elements within a group |
| Medium | 16pt | Standard padding, between groups |
| Large | 20pt | Section spacing |
| XLarge | 32pt | Major section dividers |

### Content Margins
- Use `.scenePadding()` for automatic system margins on all devices
- For manual control: 16pt horizontal on iPhone, 20pt on iPad
- `List` and `Form` handle their own margins — don't add extra padding

### Safe Areas
- Never place interactive content under safe area insets
- Use `.safeAreaInset(edge:)` for floating buttons/toolbars
- `ignoresSafeArea()` only for background fills (images, colors), never for content

### Alignment
- Left-align body text (in LTR locales)
- Center-align titles, empty states, and onboarding content
- Right-align numeric values in tables/lists
- Respect `.environment(\.layoutDirection)` for RTL locales

---

## Modality

### When to Use Modality
- **Do:** Creation flows (new memory, new profile), multi-step tasks, settings that need Save/Cancel
- **Don't:** Detail views (push instead), simple toggles, anything the user might want to reference while browsing

### Modal Toolbar Pattern
```swift
.toolbar {
    ToolbarItem(placement: .cancellationAction) {
        Button("Cancel") { dismiss() }
    }
    ToolbarItem(placement: .confirmationAction) {
        Button("Save") { save() }
            .bold()
    }
}
```

**Rules:**
- Primary action (Save/Done) is **bold**
- Disable primary action until form is valid
- Prompt to save unsaved changes on cancel (`.interactiveDismissDisabled(hasChanges)`)

---

## Controls & Inputs

### Buttons
| Style | When |
|-------|------|
| `.borderedProminent` | Primary CTA, one per screen |
| `.bordered` | Secondary actions |
| `.borderless` (plain) | Tertiary / inline actions |
| `.destructive` role | Delete, remove, sign out |

```swift
Button("Save Memory") { save() }
    .buttonStyle(.borderedProminent)
    .controlSize(.large)  // 50pt height — thumb-friendly
```

**Rules:**
- One `.borderedProminent` button per screen maximum
- Minimum touch target: 44x44pt (use `.frame(minHeight: 44)` if needed)
- Destructive buttons: red tint, always require confirmation

### Text Fields
```swift
TextField("Baby's name", text: $name)
    .textContentType(.name)        // Autofill support
    .autocorrectionDisabled()       // For names
    .textInputAutocapitalization(.words)
```

- Always set `.textContentType` for system autofill
- Use `@FocusState` to manage keyboard + scroll to active field
- Show inline validation errors below the field, not as alerts

### Toggle, Picker, DatePicker
- Use native controls — don't build custom toggles or date pickers
- `Picker` in a `Form`: automatically renders as navigation link on iOS
- `DatePicker` with `.datePickerStyle(.graphical)` for date selection, `.wheel` only if space-constrained

---

## Feedback & Status

### Loading States
- Use `ProgressView()` (indeterminate spinner) for short operations (<3s)
- Use `ProgressView(value:total:)` for operations with known progress
- Place loading indicators where content will appear (skeleton), not centered on screen
- Overlay content with `.redacted(reason: .placeholder)` for skeleton loading

### Empty States
```swift
ContentUnavailableView {
    Label("No Memories", systemImage: "photo.on.rectangle.angled")
} description: {
    Text("Start capturing your baby's first moments.")
} actions: {
    Button("Add Memory") { showCapture = true }
        .buttonStyle(.borderedProminent)
}
```

- Always provide an action to resolve the empty state
- Use warm, encouraging copy — never "Error" or "Nothing here"

### Error States
- Inline errors > alerts for recoverable issues (network retry, validation)
- Alerts for critical/blocking errors only
- Always provide a retry action or clear next step
- Never show raw error codes or technical messages to users

---

## Platform Conventions

### iPhone Considerations
- Design for one-handed use — primary actions in bottom half of screen
- Use `.safeAreaInset(edge: .bottom)` for floating action buttons
- Support both portrait and landscape unless content doesn't benefit from landscape
- Dynamic Island / notch: never place content that overlaps these areas

### Swipe Actions
```swift
.swipeActions(edge: .trailing) {
    Button(role: .destructive) { delete(item) } label: {
        Label("Delete", systemImage: "trash")
    }
}
.swipeActions(edge: .leading) {
    Button { pin(item) } label: {
        Label("Pin", systemImage: "pin")
    }
    .tint(.yellow)
}
```

- Trailing swipe = destructive/primary actions
- Leading swipe = positive/secondary actions
- Keep to 1-2 actions per side maximum

---

## HIG Compliance Checklist

For every new screen, verify:

- [ ] Has a `navigationTitle`
- [ ] Uses system navigation patterns (push, sheet, or fullScreenCover) appropriately
- [ ] All interactive elements meet 44x44pt minimum touch target
- [ ] Uses standard spacing tokens (no magic numbers)
- [ ] Respects safe areas
- [ ] Has a loading state
- [ ] Has an empty state (if data-driven)
- [ ] Has an error state with recovery action
- [ ] Primary action button is visually prominent
- [ ] Destructive actions require confirmation
- [ ] Uses SF Symbols for icons (no custom icons unless brand-specific)
- [ ] Supports Dynamic Type (no fixed font sizes)
- [ ] Supports Dark Mode
- [ ] Uses system colors (`.primary`, `.secondary`, `.accentColor`) as base
- [ ] Texts use `.font(.body)`, `.font(.headline)`, etc. — not hardcoded sizes
