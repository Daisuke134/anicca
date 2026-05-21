# Design System: DeskStretch

> **Version:** 1.0 | **Date:** 2026-03-05

---

## 1. Design Tokens

### Colors

| Token | Light Mode | Dark Mode | Usage |
|-------|-----------|-----------|-------|
| `primary` | `#007AFF` (System Blue) | `#0A84FF` | CTA buttons, selected states, links |
| `secondary` | `#5856D6` (System Indigo) | `#5E5CE6` | Secondary actions, accents |
| `background` | `#F2F2F7` (System Gray 6) | `#000000` | Main background |
| `surface` | `#FFFFFF` | `#1C1C1E` | Cards, list rows |
| `textPrimary` | `#000000` | `#FFFFFF` | Headlines, body text |
| `textSecondary` | `#3C3C43` (60% opacity) | `#EBEBF5` (60%) | Subtitles, captions |
| `textTertiary` | `#3C3C43` (30% opacity) | `#EBEBF5` (30%) | Placeholders, disabled |
| `success` | `#34C759` (System Green) | `#30D158` | Completed states, streaks |
| `warning` | `#FF9500` (System Orange) | `#FF9F0A` | Timer warnings |
| `destructive` | `#FF3B30` (System Red) | `#FF453A` | Delete, cancel |

**Rule:** Use SwiftUI semantic colors (`Color.primary`, `Color.secondary`, `Color.accentColor`) wherever possible. Custom colors only for brand-specific elements.

Source: [Apple HIG — Color](https://developer.apple.com/design/human-interface-guidelines/color) — 「Use semantic colors for most interface elements because they automatically adapt.」

### Typography

| Style | Font | Size | Weight | Usage |
|-------|------|------|--------|-------|
| `largeTitle` | SF Pro | 34pt | Bold | Screen titles |
| `title` | SF Pro | 28pt | Bold | Section headers |
| `title2` | SF Pro | 22pt | Bold | Card titles |
| `headline` | SF Pro | 17pt | Semibold | List row titles |
| `body` | SF Pro | 17pt | Regular | Body text, instructions |
| `callout` | SF Pro | 16pt | Regular | Secondary info |
| `subheadline` | SF Pro | 15pt | Regular | Metadata |
| `footnote` | SF Pro | 13pt | Regular | Legal text, captions |
| `caption` | SF Pro | 12pt | Regular | Timestamps, badges |
| `timer` | SF Pro Rounded | 48pt | Bold | Timer countdown |

**Rule:** Use `.font()` modifier with system text styles. No custom fonts.

Source: [Apple HIG — Typography](https://developer.apple.com/design/human-interface-guidelines/typography) — 「San Francisco is the system font on all Apple platforms. The font automatically adjusts spacing and alignment.」

### Spacing

| Token | Value | Usage |
|-------|-------|-------|
| `xs` | 4pt | Inline spacing, icon-to-text |
| `sm` | 8pt | Compact padding, chip spacing |
| `md` | 16pt | Standard padding, row spacing |
| `lg` | 24pt | Section spacing |
| `xl` | 32pt | Screen top/bottom padding |
| `xxl` | 48pt | Major section breaks |

### Corner Radius

| Token | Value | Usage |
|-------|-------|-------|
| `small` | 8pt | Chips, badges |
| `medium` | 12pt | Cards, buttons |
| `large` | 16pt | Sheets, modals |
| `circular` | `.infinity` | Timer ring, avatar |

---

## 2. Components

### Primary Button

```swift
struct PrimaryButton: View {
    let title: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.headline)
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .frame(height: 50)
                .background(Color.accentColor)
                .cornerRadius(12)
        }
    }
}
```

| Property | Value |
|----------|-------|
| Height | 50pt |
| Corner radius | 12pt |
| Font | Headline (17pt Semibold) |
| Background | accentColor |
| Text | White |

### Secondary Button

| Property | Value |
|----------|-------|
| Height | 50pt |
| Corner radius | 12pt |
| Font | Headline (17pt Semibold) |
| Background | Clear |
| Border | 1pt, accentColor |
| Text | accentColor |

### Pain Area Card

| Property | Value |
|----------|-------|
| Size | 1:1 aspect ratio in 2-column grid |
| Corner radius | 16pt |
| SF Symbol | 40pt, centered |
| Label | Caption below icon |
| Selected state | accentColor background, white text |
| Unselected state | surface background, primary text |

### Exercise Card (List Row)

| Property | Value |
|----------|-------|
| Leading | SF Symbol (28pt, tinted) |
| Title | Headline |
| Subtitle | Subheadline (duration + category) |
| Trailing | Chevron (or lock icon for premium) |
| Padding | 16pt vertical, 16pt horizontal |

### Timer Ring

| Property | Value |
|----------|-------|
| Diameter | 200pt |
| Ring width | 12pt |
| Background ring | Gray (20% opacity) |
| Progress ring | accentColor with gradient |
| Center text | 48pt Bold Monospaced (SF Pro Rounded) |
| Animation | Smooth circular trim |

### Streak Badge

| Property | Value |
|----------|-------|
| Shape | Capsule |
| Background | success (green) at 10% opacity |
| Text | success color, caption weight |
| Icon | Leading flame emoji |

### Filter Chip

| Property | Value |
|----------|-------|
| Shape | Capsule |
| Height | 32pt |
| Padding | 12pt horizontal |
| Selected | accentColor fill, white text |
| Unselected | surface fill, primary text, 1pt border |

---

## 3. Animations

| Animation | Type | Duration | Curve |
|-----------|------|----------|-------|
| Page transition | Slide | 0.3s | easeInOut |
| Button press | Scale | 0.1s | spring |
| Card selection | Scale + color | 0.2s | easeOut |
| Timer tick | Ring trim | 1.0s | linear |
| Session complete | Scale up + bounce | 0.5s | spring(response:0.5, dampingFraction:0.6) |
| Progress update | Number counter | 0.3s | easeOut |

### Motion Reduction

```swift
@Environment(\.accessibilityReduceMotion) var reduceMotion

.animation(reduceMotion ? nil : .spring(), value: isSelected)
```

---

## 4. Accessibility

| Standard | Requirement |
|----------|------------|
| WCAG AA | 4.5:1 contrast for normal text, 3:1 for large text |
| VoiceOver | All interactive elements labeled |
| Dynamic Type | All text scales (no fixed sizes) |
| Reduce Motion | All animations respect system preference |
| Reduce Transparency | Solid backgrounds when enabled |
| Bold Text | Respect system bold preference |

### Accessibility Identifiers (for Maestro)

| Screen | Element | Identifier |
|--------|---------|-----------|
| Onboarding | Get Started button | `onboarding_get_started` |
| Onboarding | Pain area: Neck | `pain_area_neck` |
| Onboarding | Pain area: Back | `pain_area_back` |
| Onboarding | Maybe Later | `paywall_maybe_later` |
| Onboarding | Monthly button | `paywall_monthly` |
| Onboarding | Annual button | `paywall_annual` |
| Timer | Countdown text | `timer_countdown` |
| Timer | Stretch Now button | `timer_stretch_now` |
| Timer | Pause button | `timer_pause` |
| Session | Exercise name | `session_exercise_name` |
| Session | Skip button | `session_skip` |
| Session | Close button | `session_close` |
| Progress | Today count | `progress_today` |
| Progress | Streak count | `progress_streak` |

---

## 5. Dark Mode

| Element | Light | Dark |
|---------|-------|------|
| Background | System Gray 6 | Black |
| Surface (cards) | White | System Gray 5 |
| Text primary | Black | White |
| Timer ring | Blue → gradient | Blue → gradient (brighter) |
| SF Symbols | Tinted | Tinted (same hue, adjusted brightness) |

**Rule:** Use SwiftUI `.preferredColorScheme()` to respect system setting. No manual dark mode toggle in MVP.

---

## 6. App Icon

| Size | Usage |
|------|-------|
| 1024×1024 | App Store |
| 180×180 | iPhone @3x |
| 120×120 | iPhone @2x |
| 167×167 | iPad Pro @2x |
| 152×152 | iPad @2x |

**Design Direction:** Minimalist — person stretching at desk silhouette, blue gradient background, rounded corners (auto-applied by iOS).
