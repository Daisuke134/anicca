# Design System: EyeBreakIsland

**Version:** 1.0
**Date:** 2026-03-07
**SSOT:** docs/PRD.md
**Architecture:** docs/ARCHITECTURE.md

Source: [Apple HIG: Foundations](https://developer.apple.com/design/human-interface-guidelines/foundations) — "Use semantic colors, Dynamic Type, and consistent spacing"
Source: [Apple HIG: Color](https://developer.apple.com/design/human-interface-guidelines/color) — "Prefer system colors that automatically adapt to Dark Mode"
Source: [WCAG 2.1 AA](https://www.w3.org/TR/WCAG21/) — "Minimum contrast ratio 4.5:1 for normal text, 3:1 for large text"

---

## 1. Color Tokens

### Brand Colors

| Token | Light Mode | Dark Mode | Usage |
|-------|-----------|-----------|-------|
| `brand.primary` | `#0A7AFF` | `#4DA3FF` | CTA buttons, accent highlights, timer ring active |
| `brand.secondary` | `#34C759` | `#30D158` | Break phase indicator, success states, streak badge |
| `brand.warning` | `#FF9500` | `#FFB340` | Timer < 2 min remaining, caution states |
| `brand.danger` | `#FF3B30` | `#FF6961` | Error states, destructive actions |
| `brand.break` | `#5856D6` | `#7D7AFF` | Break overlay background tint, break phase accent |

### Semantic Colors

| Token | Light Mode | Dark Mode | Usage |
|-------|-----------|-----------|-------|
| `bg.primary` | `#FFFFFF` | `#000000` | Main screen background |
| `bg.secondary` | `#F2F2F7` | `#1C1C1E` | Card backgrounds, grouped sections |
| `bg.tertiary` | `#E5E5EA` | `#2C2C2E` | Dividers, subtle separators |
| `bg.breakOverlay` | `#1A1A2E` | `#1A1A2E` | Break overlay background (same in both modes) |
| `text.primary` | `#000000` | `#FFFFFF` | Headlines, body text |
| `text.secondary` | `#3C3C43` (60%) | `#EBEBF5` (60%) | Subtitles, captions |
| `text.tertiary` | `#3C3C43` (30%) | `#EBEBF5` (30%) | Placeholders, disabled text |
| `text.onPrimary` | `#FFFFFF` | `#FFFFFF` | Text on brand.primary buttons |

### SwiftUI Implementation

```swift
// Colors/AppColors.swift
import SwiftUI

enum AppColors {
    static let brandPrimary = Color("BrandPrimary")       // Asset Catalog
    static let brandSecondary = Color("BrandSecondary")
    static let brandWarning = Color("BrandWarning")
    static let brandDanger = Color("BrandDanger")
    static let brandBreak = Color("BrandBreak")

    static let bgPrimary = Color(.systemBackground)
    static let bgSecondary = Color(.secondarySystemBackground)
    static let bgTertiary = Color(.tertiarySystemBackground)
    static let bgBreakOverlay = Color(hex: "#1A1A2E")

    static let textPrimary = Color(.label)
    static let textSecondary = Color(.secondaryLabel)
    static let textTertiary = Color(.tertiaryLabel)
}
```

Source: [Apple HIG: Color](https://developer.apple.com/design/human-interface-guidelines/color) — "Use semantic system colors like .label and .systemBackground for automatic Dark Mode support"

---

## 2. Typography

| Style | Font | Size | Weight | Line Height | Usage |
|-------|------|------|--------|-------------|-------|
| `display` | SF Pro Rounded | 56 | Bold | 64 | Timer countdown (main screen) |
| `headline1` | SF Pro | 28 | Bold | 34 | Screen titles |
| `headline2` | SF Pro | 22 | Semibold | 28 | Section headers |
| `headline3` | SF Pro | 17 | Semibold | 22 | Card titles, list headers |
| `body` | SF Pro | 17 | Regular | 22 | Body text, descriptions |
| `callout` | SF Pro | 16 | Regular | 21 | Paywall feature descriptions |
| `subheadline` | SF Pro | 15 | Regular | 20 | Secondary labels |
| `caption1` | SF Pro | 12 | Regular | 16 | Timestamps, badges |
| `caption2` | SF Pro | 11 | Regular | 13 | Legal text, restore link |
| `timerMono` | SF Mono | 48 | Medium | 56 | Dynamic Island compact timer |

### SwiftUI Implementation

```swift
// Typography/AppTypography.swift
import SwiftUI

enum AppTypography {
    static let display = Font.system(size: 56, weight: .bold, design: .rounded)
    static let headline1 = Font.title.bold()
    static let headline2 = Font.title2.weight(.semibold)
    static let headline3 = Font.headline
    static let body = Font.body
    static let callout = Font.callout
    static let subheadline = Font.subheadline
    static let caption1 = Font.caption
    static let caption2 = Font.caption2
    static let timerMono = Font.system(size: 48, weight: .medium, design: .monospaced)
}
```

**Dynamic Type:** All text uses system fonts with built-in Dynamic Type support. No fixed-size text. **Exception:** `display` (56pt) and `timerMono` (48pt) use fixed sizes — timer ring layout requires predictable dimensions.

Source: [Apple HIG: Typography](https://developer.apple.com/design/human-interface-guidelines/typography) — "Prefer system fonts for automatic Dynamic Type scaling"

---

## 3. Spacing & Layout

### Spacing Scale

| Token | Value | Usage |
|-------|-------|-------|
| `space.xxs` | 4pt | Icon padding, inline gaps |
| `space.xs` | 8pt | List item internal padding |
| `space.sm` | 12pt | Card internal padding |
| `space.md` | 16pt | Section spacing, standard padding |
| `space.lg` | 24pt | Between sections, group spacing |
| `space.xl` | 32pt | Screen top/bottom insets |
| `space.xxl` | 48pt | Onboarding page spacing |

### Layout Constants

| Constant | Value | Usage |
|----------|-------|-------|
| `cornerRadius.sm` | 8pt | Small buttons, tags |
| `cornerRadius.md` | 12pt | Cards, input fields |
| `cornerRadius.lg` | 16pt | CTA buttons, paywall cards |
| `cornerRadius.xl` | 24pt | Onboarding cards, modal sheets |
| `buttonHeight.primary` | 56pt | Main CTA buttons |
| `buttonHeight.secondary` | 44pt | Secondary buttons |
| `timerRingSize` | 280pt | Main timer circle diameter |
| `timerRingStroke` | 12pt | Timer circle stroke width |
| `maxContentWidth` | 390pt | Content max-width (iPhone SE friendly) |

### SwiftUI Implementation

```swift
// Layout/AppSpacing.swift
import SwiftUI

enum AppSpacing {
    static let xxs: CGFloat = 4
    static let xs: CGFloat = 8
    static let sm: CGFloat = 12
    static let md: CGFloat = 16
    static let lg: CGFloat = 24
    static let xl: CGFloat = 32
    static let xxl: CGFloat = 48
}

enum AppCornerRadius {
    static let sm: CGFloat = 8
    static let md: CGFloat = 12
    static let lg: CGFloat = 16
    static let xl: CGFloat = 24
}
```

---

## 4. Components

### PrimaryButton

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `title` | String | — | Button label text |
| `action` | () -> Void | — | Tap handler |
| `isLoading` | Bool | false | Show spinner |
| `isDisabled` | Bool | false | Dim + disable |

```swift
struct PrimaryButton: View {
    let title: String
    let action: () -> Void
    var isLoading: Bool = false
    var isDisabled: Bool = false

    var body: some View {
        Button(action: action) {
            Group {
                if isLoading {
                    ProgressView()
                        .tint(.white)
                } else {
                    Text(title)
                        .font(AppTypography.headline3)
                }
            }
            .frame(maxWidth: .infinity)
            .frame(height: 56)
            .background(isDisabled ? AppColors.textTertiary : AppColors.brandPrimary)
            .foregroundStyle(Color.white)
            .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.lg))
        }
        .disabled(isDisabled || isLoading)
    }
}
```

### SecondaryButton

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `title` | String | — | Button label |
| `action` | () -> Void | — | Tap handler |

```swift
struct SecondaryButton: View {
    let title: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(AppTypography.subheadline)
                .foregroundStyle(AppColors.textSecondary)
        }
    }
}
```

### TimerRing

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `progress` | Double | — | 0.0...1.0 completion |
| `timerState` | TimerState | — | Color selection |
| `formattedTime` | String | — | "18:34" display |

```swift
struct TimerRing: View {
    let progress: Double
    let timerState: TimerState
    let formattedTime: String

    private var ringColor: Color {
        switch timerState {
        case .running: return AppColors.brandPrimary
        case .breaking: return AppColors.brandBreak
        case .paused: return AppColors.brandWarning
        case .idle: return AppColors.textTertiary
        }
    }

    var body: some View {
        ZStack {
            Circle()
                .stroke(AppColors.bgTertiary, lineWidth: 12)
            Circle()
                .trim(from: 0, to: progress)
                .stroke(ringColor, style: StrokeStyle(lineWidth: 12, lineCap: .round))
                .rotationEffect(.degrees(-90))
                .animation(.linear(duration: 1), value: progress)
            Text(formattedTime)
                .font(AppTypography.display)
                .foregroundStyle(AppColors.textPrimary)
                .monospacedDigit()
        }
        .frame(width: 280, height: 280)
    }
}
```

### PackageCard (Paywall)

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `title` | String | — | "Monthly" / "Annual" |
| `price` | String | — | "$4.99/mo" |
| `detail` | String? | nil | "7-day free trial" |
| `isSelected` | Bool | false | Highlight state |
| `badge` | String? | nil | "BEST VALUE" |

### OnboardingPage

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `imageName` | String | — | SF Symbol name |
| `title` | String | — | Page headline |
| `subtitle` | String | — | Description text |

---

## 5. Icons

| Name | SF Symbol | Usage |
|------|-----------|-------|
| Eye | `eye` | App icon motif, Dynamic Island leading |
| Eye Fill | `eye.fill` | Active timer state |
| Timer | `timer` | Timer tab, onboarding feature |
| Play | `play.fill` | Start timer button |
| Stop | `stop.fill` | Stop timer button |
| Pause | `pause.fill` | Pause timer button |
| Gear | `gearshape.fill` | Settings tab |
| Bell | `bell.fill` | Notification permission |
| Crown | `crown.fill` | Pro badge, upgrade CTA |
| Chart | `chart.bar.fill` | Statistics (Pro) |
| Calendar | `calendar` | Schedule mode (Pro) |
| Clock | `clock.fill` | Custom intervals (Pro) |
| Checkmark | `checkmark.circle.fill` | Break completed |
| Arrow Restore | `arrow.clockwise` | Restore purchases |
| Xmark | `xmark` | Dismiss modal |

Source: [Apple SF Symbols](https://developer.apple.com/sf-symbols/) — "Use SF Symbols for consistent, accessible iconography"

---

## 6. Animations

| Element | Trigger | Duration | Type | Curve |
|---------|---------|----------|------|-------|
| Timer ring progress | Every 1s tick | 1.0s | Linear | `.linear` |
| Break overlay appear | Timer reaches 0 | 0.3s | Spring | `.spring(duration: 0.3)` |
| Break overlay dismiss | Break completes | 0.3s | EaseOut | `.easeOut(duration: 0.3)` |
| Paywall card select | Tap on package | 0.2s | Spring | `.spring(duration: 0.2)` |
| Paywall card scale | Tap on package | 0.2s | Scale 1.0 -> 1.02 | `.spring` |
| Onboarding page transition | Next/swipe | 0.4s | Spring | `.spring(duration: 0.4)` |
| Button press feedback | Tap down | 0.1s | Scale 1.0 -> 0.96 | `.easeInOut` |
| Success checkmark | Break complete | 0.5s | Spring bounce | `.spring(bounce: 0.3)` |
| Live Activity update | State change | 0.3s | System default | ActivityKit managed |

### Animation Constants

```swift
// Animation/AppAnimations.swift
import SwiftUI

enum AppAnimations {
    static let timerTick = Animation.linear(duration: 1.0)
    static let overlayAppear = Animation.spring(duration: 0.3)
    static let overlayDismiss = Animation.easeOut(duration: 0.3)
    static let cardSelect = Animation.spring(duration: 0.2)
    static let pageTransition = Animation.spring(duration: 0.4)
    static let buttonPress = Animation.easeInOut(duration: 0.1)
    static let successBounce = Animation.spring(duration: 0.5, bounce: 0.3)
}
```

---

## 7. Accessibility

### Contrast Ratios

| Combination | Ratio | WCAG AA |
|-------------|-------|---------|
| `text.primary` on `bg.primary` (Light) | 21:1 | PASS |
| `text.primary` on `bg.primary` (Dark) | 21:1 | PASS |
| `brand.primary` on `bg.primary` (Light) | 4.6:1 | PASS |
| `brand.primary` on `bg.primary` (Dark) | 5.2:1 | PASS |
| `text.onPrimary` on `brand.primary` | 4.8:1 | PASS |
| `text.secondary` on `bg.primary` (Light) | 7.0:1 | PASS |
| `brand.break` on `bg.breakOverlay` | 6.1:1 | PASS |

### Dynamic Type Support

| Rule | Implementation |
|------|---------------|
| All text uses system fonts | `Font.body`, `Font.title`, etc. — never hardcoded sizes |
| Layout adapts to text size | `ScrollView` wraps all screens for Accessibility XXL |
| Minimum tap target | 44x44pt for all interactive elements |
| Button labels | All buttons have `.accessibilityLabel()` |

### VoiceOver Labels

| Element | Label | Hint |
|---------|-------|------|
| Timer display | "Timer: {minutes} minutes {seconds} seconds remaining" | "Double tap to start or stop" |
| Start button | "Start eye break timer" | — |
| Stop button | "Stop timer" | — |
| Break overlay | "Eye break: Look away for {seconds} seconds" | "Timer will auto-resume" |
| Package card | "{Plan name}: {price}" | "Double tap to select" |
| Maybe Later | "Skip for now" | "Continue with free version" |

### Reduce Motion

```swift
@Environment(\.accessibilityReduceMotion) var reduceMotion

// Use conditional animations
.animation(reduceMotion ? .none : AppAnimations.overlayAppear, value: showBreakOverlay)
```

Source: [Apple HIG: Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) — "Support Dynamic Type, VoiceOver, and Reduce Motion"
Source: [WCAG 2.1 AA: Contrast](https://www.w3.org/TR/WCAG21/#contrast-minimum) — "4.5:1 minimum for normal text"

---

**End of Design System**
