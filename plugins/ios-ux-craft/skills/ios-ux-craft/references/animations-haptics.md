# Animations, Transitions & Haptics — Apple-Native Feel

## Table of Contents
- [Animation Principles](#animation-principles)
- [Spring Animations](#spring-animations)
- [Transitions](#transitions)
- [Matched Geometry](#matched-geometry)
- [Phase Animations](#phase-animations)
- [Keyframe Animations](#keyframe-animations)
- [Haptic Feedback](#haptic-feedback)
- [Motion Accessibility](#motion-accessibility)
- [Anti-Patterns](#anti-patterns)

---

## Animation Principles

1. **Every animation must have a purpose** — guide attention, show causality, or provide feedback
2. **Use spring animations as the default** — they feel natural and are Apple's standard
3. **Fast in, gentle out** — interactions should feel snappy (200-350ms), ambient animations can be slower
4. **Respect Reduce Motion** — always provide a reduced-motion fallback
5. **Animate one property at a time for clarity** — don't animate size, position, and opacity simultaneously unless they're part of one gesture

---

## Spring Animations

### Recommended Presets
```swift
// Default interactive — snappy response for user actions
.animation(.spring(duration: 0.3, bounce: 0.2), value: trigger)

// Gentle — content appearing, layout changes
.animation(.spring(duration: 0.4, bounce: 0.1), value: trigger)

// Bouncy — playful feedback (like/favorite, success state)
.animation(.spring(duration: 0.35, bounce: 0.4), value: trigger)

// Smooth — sheet resizing, sidebar opening
.animation(.smooth(duration: 0.3), value: trigger)
```

### When to Use What
| Context | Animation |
|---------|-----------|
| Button press feedback | `.spring(duration: 0.2, bounce: 0.3)` |
| Card appearing in feed | `.spring(duration: 0.35, bounce: 0.15)` |
| Sheet/modal presentation | `.smooth(duration: 0.3)` |
| Layout reflow (items added/removed) | `.spring(duration: 0.3, bounce: 0.2)` |
| Error shake | `.spring(duration: 0.3, bounce: 0.5)` |
| Success checkmark | `.spring(duration: 0.4, bounce: 0.4)` |

### withAnimation Blocks
```swift
// Prefer explicit withAnimation for state changes
withAnimation(.spring(duration: 0.3, bounce: 0.2)) {
    isExpanded.toggle()
}
```

---

## Transitions

### Standard Transitions
```swift
// Content appearing (e.g., new list item)
.transition(.opacity.combined(with: .move(edge: .top)))

// Toast/banner appearing from top
.transition(.move(edge: .top).combined(with: .opacity))

// Detail view element
.transition(.scale(scale: 0.9).combined(with: .opacity))

// Slide replacement (e.g., onboarding pages)
.transition(.asymmetric(
    insertion: .move(edge: .trailing).combined(with: .opacity),
    removal: .move(edge: .leading).combined(with: .opacity)
))
```

### Conditional Content Pattern
```swift
VStack {
    if showBanner {
        BannerView()
            .transition(.move(edge: .top).combined(with: .opacity))
    }

    ContentView()
}
.animation(.spring(duration: 0.3, bounce: 0.15), value: showBanner)
```

---

## Matched Geometry

Use for hero transitions between views (e.g., thumbnail → full-screen photo).

```swift
@Namespace private var namespace

// In grid/list
ForEach(items) { item in
    ItemThumbnail(item: item)
        .matchedGeometryEffect(id: item.id, in: namespace)
        .onTapGesture { selectedItem = item }
}

// In overlay/detail
if let item = selectedItem {
    ItemDetail(item: item)
        .matchedGeometryEffect(id: item.id, in: namespace)
        .transition(.opacity)
}
```

**Rules:**
- Use the same `id` and `namespace` on source and destination
- Combine with `.opacity` transition for smooth cross-dissolve
- Matched geometry works best for single hero elements — don't overuse

---

## Phase Animations (iOS 17+)

Multi-step sequenced animations:

```swift
struct PulsingDot: View {
    @State private var isActive = false

    var body: some View {
        Circle()
            .fill(.red)
            .frame(width: 12, height: 12)
            .phaseAnimator([false, true], trigger: isActive) { content, phase in
                content
                    .scaleEffect(phase ? 1.3 : 1.0)
                    .opacity(phase ? 0.7 : 1.0)
            } animation: { phase in
                .spring(duration: 0.6, bounce: 0.3)
            }
    }
}
```

Use for: recording indicators, attention-grabbing dots, subtle pulsing states.

---

## Keyframe Animations (iOS 17+)

Complex multi-property animations:

```swift
struct SuccessCheckmark: View {
    @State private var trigger = false

    var body: some View {
        Image(systemName: "checkmark.circle.fill")
            .font(.largeTitle)
            .foregroundStyle(.green)
            .keyframeAnimator(initialValue: AnimationValues(), trigger: trigger) { content, value in
                content
                    .scaleEffect(value.scale)
                    .rotationEffect(.degrees(value.rotation))
            } keyframes: { _ in
                KeyframeTrack(\.scale) {
                    SpringKeyframe(1.3, duration: 0.2, spring: .bouncy)
                    SpringKeyframe(1.0, duration: 0.3, spring: .smooth)
                }
                KeyframeTrack(\.rotation) {
                    SpringKeyframe(-10, duration: 0.15)
                    SpringKeyframe(5, duration: 0.15)
                    SpringKeyframe(0, duration: 0.2)
                }
            }
    }
}

struct AnimationValues {
    var scale: CGFloat = 1.0
    var rotation: Double = 0.0
}
```

Use for: success/error feedback, celebrations, onboarding highlights.

---

## Haptic Feedback

### UIKit Haptics in SwiftUI
```swift
// Impact — physical collision feel
private let lightImpact = UIImpactFeedbackGenerator(style: .light)
private let mediumImpact = UIImpactFeedbackGenerator(style: .medium)
private let heavyImpact = UIImpactFeedbackGenerator(style: .heavy)

// Notification — result feedback
private let notification = UINotificationFeedbackGenerator()

// Selection — subtle tick
private let selection = UISelectionFeedbackGenerator()
```

### When to Use What
| Action | Haptic |
|--------|--------|
| Tap on button | `.light` impact |
| Toggle switch | `.light` impact |
| Pull-to-refresh threshold | `.medium` impact |
| Long press activated | `.medium` impact |
| Picker value change | Selection tick |
| Success (save, send) | `.success` notification |
| Error (validation fail) | `.error` notification |
| Warning (destructive about to happen) | `.warning` notification |
| Snap to position | `.rigid` impact |
| Swipe action threshold | `.light` impact |

### Sensory Feedback (iOS 17+)
```swift
Button("Save") { save() }
    .sensoryFeedback(.success, trigger: saveCompleted)

Toggle("Notifications", isOn: $enabled)
    .sensoryFeedback(.selection, trigger: enabled)
```

**Rules:**
- **Prepare generators** before use: call `.prepare()` ahead of time for zero-latency
- **Don't overdo it** — haptics for every scroll or minor interaction is annoying
- **Match intensity to importance** — light for routine, medium for significant, heavy rarely
- **Never use haptics as the sole feedback** — always pair with visual/audio

---

## Motion Accessibility

### Always Respect Reduce Motion
```swift
@Environment(\.accessibilityReduceMotion) private var reduceMotion

// Pattern 1: Conditional animation
withAnimation(reduceMotion ? .none : .spring(duration: 0.3, bounce: 0.2)) {
    isExpanded.toggle()
}

// Pattern 2: Simplified transition
.transition(reduceMotion ? .opacity : .move(edge: .bottom).combined(with: .opacity))

// Pattern 3: Disable ambient animations
.phaseAnimator(reduceMotion ? [false] : [false, true]) { content, phase in
    // ...
}
```

**Rules:**
- Reduce Motion should replace motion with dissolve/opacity changes
- Never disable animations entirely — opacity fades are acceptable under Reduce Motion
- Ambient/decorative animations must stop completely under Reduce Motion
- User-initiated animations (direct manipulation, gestures) can still use motion

---

## Anti-Patterns

| Don't | Do Instead |
|-------|-----------|
| `.easeInOut` everywhere | Use `.spring()` — it's Apple's standard |
| Animate on every view appear | Animate only meaningful state changes |
| Duration > 500ms for interactions | Keep interactive animations under 350ms |
| Custom loading spinner animation | Use native `ProgressView()` |
| Animate layout in `onAppear` with delay hacks | Use `.task` or `.transition` properly |
| `.animation(.default)` (implicit, broad) | Explicit `withAnimation` or `.animation(_, value:)` |
| Simultaneous unrelated animations | Stagger or sequence them for clarity |
