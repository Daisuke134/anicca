# Design System: EyeRest

## 1. Color Tokens

Source: [Apple HIG — Color](https://developer.apple.com/design/human-interface-guidelines/color) — "Use semantic and system colors to adapt to various contexts"
Source: [iOS UX Design Skill](ios-ux-design/SKILL.md) — "Semantic colors required for dark mode"

### Brand Colors

| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `brand.primary` | #2E86AB | #5BB5D5 | Primary CTA, timer ring, active states |
| `brand.secondary` | #1B998B | #3FC4B5 | Rest screen gradient, exercise accents |
| `brand.accent` | #F46036 | #FF8A65 | Streak badge, urgency indicators |
| `brand.premium` | #8338EC | #B388FF | Premium feature locks, paywall CTA |
| `brand.calm` | #7EC8E3 | #90D5EC | Rest screen background, calming animations |

### Semantic Colors (System — Auto Light/Dark)

| Token | SwiftUI | Usage |
|-------|---------|-------|
| `text.primary` | `.label` | Headlines, body text, timer digits |
| `text.secondary` | `.secondaryLabel` | Subtitles, descriptions, inactive states |
| `text.tertiary` | `.tertiaryLabel` | Placeholder text, disabled labels |
| `bg.primary` | `.systemBackground` | Screen backgrounds |
| `bg.secondary` | `.secondarySystemBackground` | Card backgrounds, grouped list |
| `bg.tertiary` | `.tertiarySystemBackground` | Nested card backgrounds |
| `separator` | `.separator` | List dividers, section borders |
| `success` | `.systemGreen` | Break completed, streak active |
| `warning` | `.systemOrange` | Fatigue level 3-4 |
| `danger` | `.systemRed` | Fatigue level 5, error states, destructive actions |

### Gradient Definitions

| Name | Colors | Usage |
|------|--------|-------|
| `restGradient` | `brand.calm` → `brand.secondary` | RestView background pulse animation |
| `premiumGradient` | `brand.premium` → `brand.primary` | PaywallView header background |
| `timerRingGradient` | `brand.primary` → `brand.secondary` | Circular timer progress ring |

### Implementation

```swift
// Resources/Assets.xcassets — Color Set definitions
// Each brand color: Light Appearance + Dark Appearance variants
// Access: Color("brand.primary") or extension:

extension Color {
    static let brandPrimary = Color("brand.primary")
    static let brandSecondary = Color("brand.secondary")
    static let brandAccent = Color("brand.accent")
    static let brandPremium = Color("brand.premium")
    static let brandCalm = Color("brand.calm")
}
```

---

## 2. Typography

Source: [Apple HIG — Typography](https://developer.apple.com/design/human-interface-guidelines/typography) — "Use built-in text styles whenever possible"
Source: San Francisco system font — Dynamic Type support required

| Style | Text Style | Size (Default) | Weight | Line Height | Usage |
|-------|-----------|----------------|--------|-------------|-------|
| `display` | `.largeTitle` | 34pt | Bold | 41pt | Timer countdown digits |
| `h1` | `.title` | 28pt | Bold | 34pt | Screen titles (Timer, Exercises, Stats) |
| `h2` | `.title2` | 22pt | Bold | 28pt | Section headers, paywall feature titles |
| `h3` | `.title3` | 20pt | Semibold | 25pt | Card titles, exercise names |
| `headline` | `.headline` | 17pt | Semibold | 22pt | List row primary text, button labels |
| `body` | `.body` | 17pt | Regular | 22pt | Descriptions, instructions, settings labels |
| `callout` | `.callout` | 16pt | Regular | 21pt | Secondary descriptions, tips |
| `subhead` | `.subheadline` | 15pt | Regular | 20pt | Metadata, timestamps |
| `footnote` | `.footnote` | 13pt | Regular | 18pt | Legal text, restore purchases link |
| `caption` | `.caption` | 12pt | Regular | 16pt | Badge labels, unit labels (min, sec) |

### Timer Display (Special)

| Element | Font | Size | Weight | Tracking |
|---------|------|------|--------|----------|
| Timer digits (MM:SS) | `.monospacedDigit` + `.largeTitle` | 72pt | Ultralight | -0.5pt |
| Rest countdown (20s) | `.monospacedDigit` + `.largeTitle` | 96pt | Thin | 0pt |

### Implementation

```swift
// All text uses system text styles — Dynamic Type automatic
Text("19:42")
    .font(.system(size: 72, weight: .ultraLight, design: .rounded))
    .monospacedDigit()

Text("Time until next break")
    .font(.headline)

Text("Look 20 feet away")
    .font(.title2)
    .fontWeight(.bold)
```

---

## 3. Spacing & Layout

Source: [Apple HIG — Layout](https://developer.apple.com/design/human-interface-guidelines/layout) — "Use consistent margins and padding"

### Spacing Scale (4pt Base)

| Token | Value | Usage |
|-------|-------|-------|
| `space.xxs` | 4pt | Icon-to-label gap, tight inline spacing |
| `space.xs` | 8pt | List row internal padding, badge padding |
| `space.sm` | 12pt | Card internal padding, between related items |
| `space.md` | 16pt | Standard content margins, section gap |
| `space.lg` | 24pt | Between sections, card-to-card gap |
| `space.xl` | 32pt | Screen edge to content (horizontal margins) |
| `space.xxl` | 48pt | Major section separation, paywall header spacing |

### Layout Constants

| Constant | Value | Usage |
|----------|-------|-------|
| `screenHorizontalPadding` | 20pt | Standard horizontal inset (matches system) |
| `cardCornerRadius` | 16pt | Card and container corners |
| `smallCornerRadius` | 8pt | Buttons, badges, small elements |
| `timerRingSize` | 280pt | Main timer circle diameter |
| `timerRingStroke` | 12pt | Timer progress ring width |
| `minTouchTarget` | 44pt | Minimum interactive element size (HIG) |
| `tabBarHeight` | 49pt | System tab bar height |
| `navBarHeight` | 44pt | System navigation bar height |

### Safe Area

```swift
// All layouts respect safe areas
VStack {
    content
}
.padding(.horizontal, 20)  // screenHorizontalPadding
.ignoresSafeArea(.container, edges: [])  // Never ignore safe areas for content
```

---

## 4. Components

Source: ARCHITECTURE.md §3 — Directory structure defines reusable components

| Component | Props | Usage | Screen(s) |
|-----------|-------|-------|-----------|
| `TimerRing` | progress: Double, remainingSeconds: Int, isRunning: Bool | Circular progress indicator for 20-20-20 countdown | TimerView |
| `BreakCountBadge` | count: Int, streakDays: Int | Daily break counter with streak indicator | TimerView, StatsView |
| `ExerciseCard` | exercise: EyeExercise, isPremiumLocked: Bool | Exercise preview card with lock overlay for premium | ExerciseListView |
| `FatigueLevelPicker` | selectedLevel: Binding<Int> | 1-5 scale selector with face icons | RestView (after completion) |
| `PremiumBadge` | — | Small "PRO" label for premium-locked features | ExerciseCard, SettingsView |
| `StatCard` | title: String, value: String, icon: String | Metric display card (breaks, streak, fatigue avg) | StatsView |
| `WeeklyChart` | data: [DayData] | 7-day bar chart for breaks or fatigue | StatsView |
| `PlanToggle` | selectedPlan: Binding<PlanType> | Monthly / Annual subscription toggle | PaywallView |
| `FeatureRow` | icon: String, title: String, description: String | Paywall feature benefit row with checkmark | PaywallView |
| `OnboardingPage` | imageName: String, title: String, subtitle: String | Single onboarding page template | OnboardingView |

### Component Hierarchy

```
ContentView
├── OnboardingView (if !hasCompletedOnboarding)
│   ├── OnboardingPage × 3
│   └── PaywallView (soft, final screen)
│       ├── PlanToggle
│       └── FeatureRow × 5
└── MainTabView (after onboarding)
    ├── Tab 1: TimerView
    │   ├── TimerRing
    │   ├── BreakCountBadge
    │   └── RestView (modal overlay)
    │       └── FatigueLevelPicker (premium)
    ├── Tab 2: ExerciseListView
    │   └── ExerciseCard × 8
    │       └── PremiumBadge (if locked)
    └── Tab 3: StatsView
        ├── StatCard × 3
        └── WeeklyChart
```

---

## 5. Icons

Source: [Apple SF Symbols](https://developer.apple.com/sf-symbols/) — "6,900+ symbols, nine weights, three scales"

| Name | SF Symbol | Usage | Screen |
|------|-----------|-------|--------|
| Timer tab | `timer` | Tab bar icon — Timer | TabView |
| Exercises tab | `eye` | Tab bar icon — Exercises | TabView |
| Stats tab | `chart.bar.fill` | Tab bar icon — Stats | TabView |
| Settings | `gearshape` | Settings navigation | SettingsView |
| Play | `play.fill` | Start timer button | TimerView |
| Pause | `pause.fill` | Pause timer button | TimerView |
| Stop | `stop.fill` | Stop timer button | TimerView |
| Checkmark | `checkmark.circle.fill` | Break completed, feature check | RestView, PaywallView |
| Streak flame | `flame.fill` | Streak indicator | BreakCountBadge |
| Lock | `lock.fill` | Premium locked feature | PremiumBadge |
| Crown | `crown.fill` | Premium upgrade CTA | SettingsView |
| Bell | `bell.fill` | Notification permission | OnboardingView |
| Eye open | `eye.fill` | Exercise active state | ExerciseCard |
| Eye closed | `eye.slash` | Eye rest / look away | RestView |
| Close | `xmark` | Dismiss modal | PaywallView |
| Chevron right | `chevron.right` | List disclosure | SettingsView |
| Calendar | `calendar` | Working hours schedule | SettingsView |
| Chart | `chart.line.uptrend.xyaxis` | Weekly insights | StatsView |
| Clock | `clock.fill` | Timer interval setting | SettingsView |
| Face smile | `face.smiling` | Fatigue level 1 (fine) | FatigueLevelPicker |
| Face frown | `face.dashed` | Fatigue level 5 (severe) | FatigueLevelPicker |

### Rendering Modes

| Context | Rendering | Example |
|---------|-----------|---------|
| Tab bar | Monochrome | `timer`, `eye`, `chart.bar.fill` |
| Feature list | Hierarchical | `checkmark.circle.fill` in PaywallView |
| Status indicators | Palette | `flame.fill` (orange/red) |
| Interactive buttons | Monochrome + tint | `play.fill` with `.brandPrimary` |

---

## 6. Animations

Source: [Apple HIG — Motion](https://developer.apple.com/design/human-interface-guidelines/motion) — "Use animation to communicate status, provide feedback, and enhance direct manipulation"

| Trigger | Animation | Duration | Type | Screen |
|---------|-----------|----------|------|--------|
| Timer tick | Ring progress update | 1.0s | `.linear` | TimerView |
| Timer reaches zero | Ring pulse + haptic | 0.5s | `.easeOut` | TimerView |
| Rest screen appear | Gradient fade-in | 0.6s | `.easeInOut` | RestView |
| Rest countdown pulse | Gradient opacity oscillation | 3.0s loop | `.easeInOut.repeatForever` | RestView |
| Rest complete | Checkmark scale-in + haptic | 0.4s | `.spring(response: 0.4, dampingFraction: 0.7)` | RestView |
| Break count increment | Count scale bounce | 0.3s | `.spring(response: 0.3, dampingFraction: 0.6)` | BreakCountBadge |
| Onboarding page transition | Horizontal slide | 0.35s | `.easeInOut` | OnboardingView |
| Paywall feature rows | Staggered slide-up | 0.3s each, 0.1s delay | `.spring(response: 0.4)` | PaywallView |
| Premium lock tap | Shake + lock icon bounce | 0.3s | `.default` | ExerciseCard |
| Fatigue picker selection | Scale bounce + tint | 0.2s | `.spring` | FatigueLevelPicker |
| Tab switch | System cross-fade | System | System | TabView |
| Navigation push/pop | System slide | System | System | NavigationStack |

### Haptic Feedback

| Event | Haptic Type | Intensity |
|-------|------------|-----------|
| Timer start | `.impact(.medium)` | Medium |
| Break notification | `.notification(.success)` | Strong |
| Break complete | `.notification(.success)` | Strong |
| Purchase success | `.notification(.success)` | Strong |
| Premium lock tap | `.notification(.warning)` | Light |
| Fatigue level select | `.selection` | Light |
| Button tap | `.impact(.light)` | Light |

### Reduced Motion Support

```swift
// All custom animations respect reduced motion
@Environment(\.accessibilityReduceMotion) var reduceMotion

withAnimation(reduceMotion ? .none : .easeInOut(duration: 0.6)) {
    showRestScreen = true
}
```

---

## 7. Accessibility

Source: [Apple HIG — Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) — "Approximately one in seven people have a disability"
Source: [WCAG 2.1 AA](https://www.w3.org/WAI/WCAG21/quickref/) — Contrast, text scaling, keyboard access

### Color Contrast (WCAG AA Minimum)

| Element | Ratio Requirement | Validation |
|---------|------------------|------------|
| Body text on `bg.primary` | 4.5:1 minimum | `.label` on `.systemBackground` = system-guaranteed |
| Large text (>= 18pt bold) on `bg.primary` | 3:1 minimum | `.title` styles = system-guaranteed |
| `brand.primary` #2E86AB on white | 4.15:1 | PASS for large text (timer ring labels) |
| `brand.primary` #2E86AB on `bg.primary` | 4.15:1 light / 6.2:1 dark | PASS |
| `brand.accent` #F46036 on white | 3.28:1 | PASS for large text only — use with `.headline` or larger |
| Interactive elements | 3:1 against background | All brand colors meet this on both modes |

### Contrast Usage Rules (MUST)

| Rule | Detail |
|------|--------|
| `brand.primary` text | MUST only be used for large text (>= 18pt bold / 14pt bold) or non-text UI elements (rings, icons). Body text MUST use `text.primary` (`.label`) |
| `brand.accent` text | MUST only be used as background tint/icon color on badges, NOT for small text labels. Badge label text MUST use `text.primary` for readability |
| `BreakCountBadge` | Badge background: `brand.accent` tint. Badge label: `text.primary` (not accent color) |
| Normal body text | MUST always use semantic colors (`text.primary`, `text.secondary`) — never brand colors |

### Dynamic Type Support

| Requirement | Implementation |
|-------------|---------------|
| All text uses text styles | `.font(.body)`, `.font(.headline)` etc. — never fixed pt |
| Layout adapts to larger sizes | `ScrollView` wraps all content, no fixed heights |
| Timer digits scale | `.minimumScaleFactor(0.5)` for timer display |
| Truncation policy | `.lineLimit(nil)` for descriptions — allow wrapping |

### VoiceOver Labels

| Element | Label | Hint |
|---------|-------|------|
| Timer ring | "Timer: {minutes} minutes {seconds} seconds remaining" | "Double tap to start or pause" |
| Start button | "Start timer" | "Starts 20 minute eye break countdown" |
| Break count | "{count} breaks completed today" | — |
| Streak badge | "{days} day streak" | — |
| Exercise card | "{name}, {duration} seconds" | "Double tap to start exercise" |
| Premium lock | "Premium feature" | "Double tap to view upgrade options" |
| Fatigue picker | "Eye fatigue level {level} of 5" | "Swipe up or down to adjust" |
| Maybe Later | "Maybe later" | "Dismisses paywall" |
| Plan toggle | "{Monthly or Annual} plan selected" | "Double tap to switch plans" |

### Accessibility Identifiers (Maestro E2E)

Defined in UX_SPEC.md §7 — all identifiers follow `{screen}_{element}` naming convention for Maestro test selectors.
