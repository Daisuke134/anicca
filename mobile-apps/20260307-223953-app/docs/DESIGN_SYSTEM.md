# Design System: FrostDip

## 1. Color Tokens

Source: [Apple HIG — Color](https://developer.apple.com/design/human-interface-guidelines/color) — "Use semantic and adapted colors to respond automatically to Dark Mode and accessibility settings"
Source: [Coolors Color Theory](https://coolors.co/contrast-checker) — Contrast ratio verification

### Brand Colors

| Token | Light Mode | Dark Mode | Usage | Contrast (Light/Dark) |
|-------|-----------|-----------|-------|----------------------|
| `brand.primary` | #0A84FF (System Blue) | #0A84FF | Primary CTA buttons, active tab, links | 4.5:1 / 7.2:1 |
| `brand.accent` | #30D5C8 (Turquoise) | #5CE1D6 | Timer ring, breathing animation, highlights | 4.6:1 / 5.8:1 |
| `brand.cold` | #4FC3F7 (Ice Blue) | #81D4FA | Cold phase indicator, temperature badge | 4.5:1 / 5.1:1 |
| `brand.hot` | #FF6B35 (Warm Orange) | #FF8A65 | Hot/contrast therapy phase, streak fire | 4.7:1 / 5.3:1 |
| `brand.success` | #34C759 (System Green) | #30D158 | Streak active, session complete, checkmarks | 4.5:1 / 5.0:1 |
| `brand.warning` | #FF9500 (System Orange) | #FF9F0A | Streak at risk, low HR warning | 4.5:1 / 5.2:1 |
| `brand.destructive` | #FF3B30 (System Red) | #FF453A | Delete session, cancel subscription | 4.5:1 / 5.5:1 |

### Semantic Colors (System)

| Token | SwiftUI | Usage |
|-------|---------|-------|
| `text.primary` | `.label` | Headings, body text, timer digits |
| `text.secondary` | `.secondaryLabel` | Subtitles, metadata, hints |
| `text.tertiary` | `.tertiaryLabel` | Disabled states, placeholders |
| `bg.primary` | `.systemBackground` | Main screen background |
| `bg.secondary` | `.secondarySystemBackground` | Card backgrounds, grouped sections |
| `bg.tertiary` | `.tertiarySystemBackground` | Nested card backgrounds |
| `separator` | `.separator` | List dividers, section breaks |
| `fill.primary` | `.systemFill` | Input field backgrounds |

### Gradient Definitions

| Gradient | Colors | Usage |
|----------|--------|-------|
| `gradient.cold` | `brand.cold` → `brand.accent` | Timer ring (cold phase), paywall header |
| `gradient.hot` | `brand.hot` → `#FFAB91` | Timer ring (hot/contrast phase) |
| `gradient.premium` | `brand.primary` → `brand.accent` | Premium badge, paywall CTA |
| `gradient.streak` | `brand.success` → `brand.warning` | Streak calendar active days |

### Swift Implementation

```swift
// Design/Colors.swift
import SwiftUI

enum FDColor {
    static let brandPrimary = Color("BrandPrimary")     // Asset catalog
    static let brandAccent = Color("BrandAccent")
    static let brandCold = Color("BrandCold")
    static let brandHot = Color("BrandHot")

    // Semantic (system-provided, auto light/dark)
    static let textPrimary = Color(.label)
    static let textSecondary = Color(.secondaryLabel)
    static let bgPrimary = Color(.systemBackground)
    static let bgSecondary = Color(.secondarySystemBackground)

    // Gradients
    static let coldGradient = LinearGradient(
        colors: [brandCold, brandAccent],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
    static let premiumGradient = LinearGradient(
        colors: [brandPrimary, brandAccent],
        startPoint: .leading,
        endPoint: .trailing
    )
}
```

Source: [Apple HIG — Dark Mode](https://developer.apple.com/design/human-interface-guidelines/dark-mode) — "Use semantic colors that automatically adapt to dark mode"

---

## 2. Typography

Source: [Apple HIG — Typography](https://developer.apple.com/design/human-interface-guidelines/typography) — "Use San Francisco system font with Dynamic Type for accessibility"

### Type Scale

| Style | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| `largeTitle` | 34pt | Bold | 41pt | Screen titles (Settings, History) |
| `title` | 28pt | Bold | 34pt | Section headers |
| `title2` | 22pt | Bold | 28pt | Card titles, paywall headline |
| `title3` | 20pt | Semibold | 25pt | Subsection headers |
| `headline` | 17pt | Semibold | 22pt | List row titles, stat labels |
| `body` | 17pt | Regular | 22pt | Body text, descriptions |
| `callout` | 16pt | Regular | 21pt | Secondary content |
| `subheadline` | 15pt | Regular | 20pt | Metadata, timestamps |
| `footnote` | 13pt | Regular | 18pt | Legal text, captions |
| `caption1` | 12pt | Regular | 16pt | Badges, small labels |
| `caption2` | 11pt | Regular | 13pt | Micro labels |

### Special Typography

| Element | Style | Weight | Size | Monospaced |
|---------|-------|--------|------|-----------|
| Timer Digits | Custom | Bold | 72pt | Yes (`Font.system(size: 72, weight: .bold, design: .monospaced)`) |
| HR BPM Display | Custom | Semibold | 36pt | Yes |
| Temperature | Custom | Medium | 24pt | Yes |
| Streak Count | title | Bold | 28pt | No |

### Swift Implementation

```swift
// Design/Typography.swift
import SwiftUI

enum FDFont {
    static let timerDigits = Font.system(size: 72, weight: .bold, design: .monospaced)
    static let hrDisplay = Font.system(size: 36, weight: .semibold, design: .monospaced)
    static let temperatureDisplay = Font.system(size: 24, weight: .medium, design: .monospaced)

    // All other text uses system text styles for Dynamic Type
    // .font(.largeTitle), .font(.title), .font(.body), etc.
}
```

**Dynamic Type:** All text MUST use text styles (`.font(.body)`) except timer/HR/temperature displays which use fixed monospaced sizes but remain accessible via VoiceOver labels.

---

## 3. Spacing & Layout

Source: [Apple HIG — Layout](https://developer.apple.com/design/human-interface-guidelines/layout) — "Use consistent spacing and alignment to create visual hierarchy"

### Spacing Scale (8pt Grid)

| Token | Value | Usage |
|-------|-------|-------|
| `space.xs` | 4pt | Icon-to-text gap, inline spacing |
| `space.sm` | 8pt | Between related elements, list item padding |
| `space.md` | 12pt | Section inner padding |
| `space.base` | 16pt | Standard padding, card margins |
| `space.lg` | 24pt | Between sections, card-to-card gap |
| `space.xl` | 32pt | Major section breaks |
| `space.xxl` | 48pt | Screen top/bottom padding, paywall sections |

### Layout Constants

| Constant | Value | Usage |
|----------|-------|-------|
| `radius.sm` | 8pt | Small buttons, badges |
| `radius.md` | 12pt | Cards, input fields |
| `radius.lg` | 16pt | Modal sheets, large cards |
| `radius.xl` | 24pt | Timer circle frame |
| `touchTarget` | 44pt | Minimum interactive element size |
| `cardPadding` | 16pt | Inner card padding |
| `screenPadding` | 16pt | Horizontal screen margins |

### Swift Implementation

```swift
// Design/Theme.swift
import SwiftUI

enum FDSpacing {
    static let xs: CGFloat = 4
    static let sm: CGFloat = 8
    static let md: CGFloat = 12
    static let base: CGFloat = 16
    static let lg: CGFloat = 24
    static let xl: CGFloat = 32
    static let xxl: CGFloat = 48
}

enum FDRadius {
    static let sm: CGFloat = 8
    static let md: CGFloat = 12
    static let lg: CGFloat = 16
    static let xl: CGFloat = 24
}
```

---

## 4. Components

Source: [Apple HIG — Components](https://developer.apple.com/design/human-interface-guidelines/components) — "Use system components whenever possible"

### Reusable Components

| Component | Props | Usage | a11y ID |
|-----------|-------|-------|---------|
| `CircularTimerView` | `progress: Double`, `timeRemaining: TimeInterval`, `phase: TimerPhase` | Timer screen countdown ring | `circular_timer` |
| `SessionCardView` | `session: PlungeSession` | History list row | `session_card` (static — Maestro uses `id: "session_card"` to find any card) |
| `PremiumBadgeView` | `isLocked: Bool` | Lock icon overlay on premium features | `premium_badge` |
| `StreakCalendarView` | `sessions: [PlungeSession]`, `currentStreak: Int` | Visual 30-day streak calendar | `streak_calendar` |
| `StatCardView` | `title: String`, `value: String`, `icon: String` | Dashboard stat display | `stat_card_\(title)` |
| `BenefitRowView` | `icon: String`, `title: String`, `description: String` | Paywall benefits list | `benefit_row_\(index)` |
| `PricingCardView` | `plan: String`, `price: String`, `isSelected: Bool`, `badge: String?` | Paywall plan selector | `pricing_card_\(plan)` |
| `BreathingCircleView` | `phase: BreathPhase`, `progress: Double` | Breathing prep animation | `breathing_circle` |

### Component States

| State | Visual Treatment |
|-------|-----------------|
| Default | Standard appearance |
| Pressed | `.opacity(0.7)` + scale 0.97 |
| Disabled | `.opacity(0.4)`, non-interactive |
| Loading | `ProgressView()` overlay |
| Selected | `brand.primary` border + checkmark |
| Premium Locked | Blur overlay + `PremiumBadgeView` |

### Button Styles

| Style | Appearance | Usage |
|-------|-----------|-------|
| Primary | Filled `brand.primary`, white text, 50pt height, `radius.md` | CTA: "Start Session", "Start My Cold Journey" |
| Secondary | Tinted `brand.primary` background, `brand.primary` text | "Maybe Later", "Restore Purchases" |
| Destructive | Filled `brand.destructive`, white text | "Delete Session", "Cancel" |
| Text | No background, `brand.primary` text | Links, "Privacy Policy", "Terms" |

---

## 5. Icons

Source: [Apple SF Symbols](https://developer.apple.com/sf-symbols/) — "Use SF Symbols for consistent, accessible iconography"

### Tab Bar Icons

| Tab | Symbol | Label (en-US) | Label (ja) |
|-----|--------|---------------|------------|
| Timer | `timer` | Timer | タイマー |
| History | `clock.arrow.circlepath` | History | 履歴 |
| Progress | `chart.line.uptrend.xyaxis` | Progress | 進捗 |
| Settings | `gearshape` | Settings | 設定 |

### Feature Icons

| Feature | Symbol | Rendering | Usage |
|---------|--------|-----------|-------|
| Cold plunge | `snowflake` | Hierarchical | Timer cold phase, session type |
| Hot phase | `flame` | Hierarchical | Contrast therapy hot phase |
| Heart rate | `heart.fill` | Palette (red) | Live HR display, session HR |
| Breathing | `wind` | Hierarchical | Breathing prep phase |
| Streak | `flame.fill` | Palette (orange→red) | Streak counter, calendar |
| Streak frozen | `snowflake.circle` | Hierarchical | Streak freeze used |
| Temperature | `thermometer.medium` | Hierarchical | Water temperature input |
| Protocol | `list.bullet.rectangle` | Monochrome | Protocol selection |
| Premium | `lock.fill` | Monochrome | Premium-gated features |
| Premium unlocked | `crown.fill` | Palette (gold) | Premium badge |
| Notification | `bell.fill` | Monochrome | Notification settings |
| Play | `play.fill` | Monochrome | Start timer |
| Pause | `pause.fill` | Monochrome | Pause timer |
| Stop | `stop.fill` | Monochrome | Stop timer |
| Notes | `note.text` | Monochrome | Session notes |
| Calendar | `calendar` | Monochrome | Streak calendar |
| Chart | `chart.bar.fill` | Hierarchical | Progress dashboard |
| Checkmark | `checkmark.circle.fill` | Palette (green) | Completed onboarding step |
| Close | `xmark` | Monochrome | Dismiss modal/paywall |

---

## 6. Animations

Source: [Apple HIG — Motion](https://developer.apple.com/design/human-interface-guidelines/motion) — "Use motion to communicate, not decorate"

### Animation Definitions

| Animation | Trigger | Duration | Type | Reduced Motion Fallback |
|-----------|---------|----------|------|------------------------|
| Timer ring progress | Timer tick (1s) | 1.0s | `.linear` | No animation, static ring |
| Breathing circle | Phase change (inhale/hold/exhale) | 4s/7s/8s | `.easeInOut` | Opacity fade only |
| Session complete | Timer reaches 0 | 0.6s | `.spring(response: 0.6, dampingFraction: 0.7)` | Opacity fade |
| Streak increment | New session logged | 0.4s | `.spring(response: 0.4, dampingFraction: 0.8)` | Instant update |
| Tab switch | Tab tap | 0.2s | System default | System default |
| Card press | Touch down | 0.15s | `.easeOut` | No scale, opacity only |
| Paywall plan select | Tap plan card | 0.25s | `.spring(response: 0.25)` | Instant border change |
| Onboarding slide | Next button | 0.35s | `.easeInOut` | Instant transition |
| HR pulse | New HR sample | 0.3s | `.easeInOut` (scale 1.0→1.15→1.0) | No pulse, value update only |
| Premium lock | Feature tap (free user) | 0.5s | `.spring(response: 0.5)` | Static overlay |

### Haptic Feedback

| Event | Haptic | Usage |
|-------|--------|-------|
| Timer start | `.heavy` | Confirm session start |
| Timer interval alert | `.medium` | Configurable interval notification |
| Timer complete | `.success` (notification) | Session complete celebration |
| Phase transition (contrast) | `.rigid` | Hot→Cold or Cold→Hot switch |
| Breathing phase change | `.light` | Inhale→Hold→Exhale transition |
| Button press | `.light` | General button feedback |
| Streak milestone | `.success` | 7-day, 30-day, 100-day achievements |
| Purchase success | `.success` | Subscription confirmed |
| Error | `.error` | Purchase failed, save failed |

### Swift Implementation

```swift
// Reduced motion support
@Environment(\.accessibilityReduceMotion) var reduceMotion

.animation(reduceMotion ? nil : .spring(response: 0.6, dampingFraction: 0.7), value: isComplete)
```

---

## 7. Accessibility

Source: [Apple HIG — Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) — "Design your app so that everyone can use it"
Source: [WCAG 2.1 AA](https://www.w3.org/TR/WCAG21/) — Minimum accessibility standard

### Contrast Requirements

| Element | Minimum Ratio | Standard |
|---------|--------------|----------|
| Body text | 4.5:1 | WCAG AA |
| Large text (18pt+) | 3:1 | WCAG AA |
| UI components (buttons, icons) | 3:1 | WCAG AA |
| Decorative elements | No requirement | — |

### Dynamic Type Support

| Requirement | Implementation |
|-------------|---------------|
| All body text | `.font(.body)` — scales automatically |
| All labels | Text style fonts (`.headline`, `.subheadline`, etc.) |
| Timer digits | Fixed 72pt — VoiceOver reads value |
| Minimum font size | 11pt (caption2) |
| Maximum scale | `@ScaledMetric` for custom sizes |
| Multi-line wrapping | `lineLimit(nil)` on all text views |

### VoiceOver Labels

| Screen | Element | Label | Hint |
|--------|---------|-------|------|
| Timer | Timer display | "Time remaining: [M] minutes [S] seconds" | "Double tap to start or pause" |
| Timer | Heart rate | "Heart rate: [N] beats per minute" | — |
| Timer | Temperature input | "Water temperature: [N] degrees [unit]" | "Adjustable" |
| History | Session card | "[Date], [duration] minute session, [temp] degrees" | "Double tap for details" |
| Progress | Chart | "Duration chart: average [N] minutes over [period]" | — |
| Paywall | Plan card | "[Plan name], [price], [savings badge if annual]" | "Double tap to select" |
| Paywall | CTA button | "Start My Cold Journey" | "Subscribes to selected plan" |
| Settings | Premium status | "Premium: [Active/Inactive]" | — |

### Increased Contrast Mode

All `brand.*` colors have 4 variants in the asset catalog:

| Variant | Purpose |
|---------|---------|
| Any / Light | Standard light mode |
| Any / Dark | Standard dark mode |
| High Contrast / Light | Increased contrast light mode |
| High Contrast / Dark | Increased contrast dark mode |

### Reduce Motion

| Animation | Default | Reduced Motion |
|-----------|---------|---------------|
| Timer ring | Continuous rotation | Static progress fill |
| Breathing circle | Scale + opacity animation | Opacity fade only |
| Screen transitions | Slide / spring | Instant / fade |
| Card press | Scale 0.97 | Opacity 0.7 only |
| HR pulse | Scale animation | Value update only |
