# Design System: AffirmFlow

**Version:** 1.0.0
**Date:** 2026-03-01
**Status:** APPROVED

---

## 1. Brand Identity

### 1.1 Brand Values

| Value | Expression |
|-------|------------|
| **Calm** | Soft colors, gentle gradients, breathing room |
| **Personal** | AI-powered, unique content |
| **Private** | On-device, no cloud |
| **Simple** | Minimal UI, one purpose |

### 1.2 App Icon

```
┌─────────────────────────────────────┐
│                                     │
│       ┌─────────────────┐           │
│       │                 │           │
│       │     🧘‍♀️        │           │
│       │                 │           │
│       │  Gradient       │           │
│       │  background     │           │
│       │                 │           │
│       └─────────────────┘           │
│                                     │
│  1024x1024 PNG                      │
│  Rounded corners (iOS automatic)    │
│  Soft gradient: Lavender to Peach   │
│                                     │
└─────────────────────────────────────┘
```

---

## 2. Color Palette

### 2.1 Primary Colors

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `primary` | #7C3AED (Violet 600) | #A78BFA (Violet 400) | Buttons, links, accent |
| `primaryContainer` | #EDE9FE (Violet 100) | #4C1D95 (Violet 900) | Card backgrounds |
| `onPrimary` | #FFFFFF | #FFFFFF | Text on primary |

### 2.2 Neutral Colors

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `background` | #FAFAF9 (Stone 50) | #1C1917 (Stone 900) | App background |
| `surface` | #FFFFFF | #292524 (Stone 800) | Cards, sheets |
| `surfaceVariant` | #F5F5F4 (Stone 100) | #44403C (Stone 700) | Secondary surfaces |
| `onBackground` | #1C1917 (Stone 900) | #FAFAF9 (Stone 50) | Primary text |
| `onSurface` | #44403C (Stone 700) | #D6D3D1 (Stone 300) | Secondary text |

### 2.3 Semantic Colors

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `success` | #16A34A (Green 600) | #4ADE80 (Green 400) | Success states |
| `warning` | #CA8A04 (Yellow 600) | #FACC15 (Yellow 400) | Warnings |
| `error` | #DC2626 (Red 600) | #F87171 (Red 400) | Errors |
| `favorite` | #EC4899 (Pink 500) | #F472B6 (Pink 400) | Heart/favorite |

### 2.4 Focus Area Colors

| Focus Area | Color | Hex |
|------------|-------|-----|
| Confidence | Gold | #F59E0B |
| Gratitude | Rose | #F43F5E |
| Calm | Teal | #14B8A6 |
| Motivation | Orange | #F97316 |
| Self-Love | Purple | #A855F7 |

### 2.5 SwiftUI Implementation

```swift
extension Color {
    static let appPrimary = Color("Primary")
    static let appBackground = Color("Background")
    static let appSurface = Color("Surface")
    static let appFavorite = Color("Favorite")
}

// Assets.xcassets structure:
// Colors/
//   Primary.colorset/
//   Background.colorset/
//   Surface.colorset/
//   Favorite.colorset/
//   FocusArea/
//     Confidence.colorset/
//     Gratitude.colorset/
//     Calm.colorset/
//     Motivation.colorset/
//     SelfLove.colorset/
```

---

## 3. Typography

### 3.1 Type Scale

| Style | Font | Size | Weight | Line Height | Usage |
|-------|------|------|--------|-------------|-------|
| `largeTitle` | SF Pro Display | 34pt | Bold | 41pt | Affirmation text |
| `title` | SF Pro Display | 28pt | Bold | 34pt | Screen titles |
| `title2` | SF Pro Display | 22pt | Bold | 28pt | Section headers |
| `title3` | SF Pro Display | 20pt | Semibold | 25pt | Card titles |
| `headline` | SF Pro Text | 17pt | Semibold | 22pt | Emphasis |
| `body` | SF Pro Text | 17pt | Regular | 22pt | Body text |
| `callout` | SF Pro Text | 16pt | Regular | 21pt | Secondary text |
| `subheadline` | SF Pro Text | 15pt | Regular | 20pt | Captions |
| `footnote` | SF Pro Text | 13pt | Regular | 18pt | Timestamps |
| `caption` | SF Pro Text | 12pt | Regular | 16pt | Labels |

### 3.2 Dynamic Type Support

```swift
Text("Affirmation")
    .font(.largeTitle)
    .dynamicTypeSize(...DynamicTypeSize.accessibility3)
```

All text scales with system Dynamic Type settings.

### 3.3 SwiftUI Implementation

```swift
extension Font {
    static let affirmationText = Font.system(.largeTitle, design: .default, weight: .bold)
    static let sectionTitle = Font.system(.title2, design: .default, weight: .bold)
    static let focusAreaLabel = Font.system(.footnote, design: .default, weight: .medium)
}
```

---

## 4. Spacing

### 4.1 Spacing Scale (8pt Grid)

| Token | Value | Usage |
|-------|-------|-------|
| `xxs` | 4pt | Icon padding |
| `xs` | 8pt | Tight spacing |
| `sm` | 12pt | Related elements |
| `md` | 16pt | Default padding |
| `lg` | 24pt | Section spacing |
| `xl` | 32pt | Screen margins |
| `xxl` | 48pt | Large gaps |
| `xxxl` | 64pt | Hero spacing |

### 4.2 SwiftUI Implementation

```swift
enum Spacing {
    static let xxs: CGFloat = 4
    static let xs: CGFloat = 8
    static let sm: CGFloat = 12
    static let md: CGFloat = 16
    static let lg: CGFloat = 24
    static let xl: CGFloat = 32
    static let xxl: CGFloat = 48
    static let xxxl: CGFloat = 64
}

// Usage:
.padding(.horizontal, Spacing.xl)
.padding(.vertical, Spacing.lg)
```

---

## 5. Corner Radius

| Token | Value | Usage |
|-------|-------|-------|
| `small` | 8pt | Chips, tags |
| `medium` | 12pt | Buttons, inputs |
| `large` | 16pt | Cards |
| `xlarge` | 24pt | Modals, sheets |
| `full` | 9999pt | Pills, circles |

```swift
enum CornerRadius {
    static let small: CGFloat = 8
    static let medium: CGFloat = 12
    static let large: CGFloat = 16
    static let xlarge: CGFloat = 24
}
```

---

## 6. Shadows

### 6.1 Shadow Scale

| Token | Values | Usage |
|-------|--------|-------|
| `subtle` | blur: 4, y: 2, opacity: 0.05 | Subtle elevation |
| `medium` | blur: 8, y: 4, opacity: 0.10 | Cards |
| `large` | blur: 16, y: 8, opacity: 0.15 | Modals |

### 6.2 SwiftUI Implementation

```swift
extension View {
    func cardShadow() -> some View {
        self.shadow(color: .black.opacity(0.10), radius: 8, x: 0, y: 4)
    }

    func subtleShadow() -> some View {
        self.shadow(color: .black.opacity(0.05), radius: 4, x: 0, y: 2)
    }
}
```

---

## 7. Components

### 7.1 Buttons

#### Primary Button

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
                .padding(.vertical, Spacing.md)
                .background(Color.appPrimary)
                .cornerRadius(CornerRadius.medium)
        }
    }
}
```

| State | Background | Text |
|-------|------------|------|
| Default | primary | white |
| Pressed | primary.opacity(0.8) | white |
| Disabled | gray.opacity(0.3) | gray |

#### Secondary Button

```swift
struct SecondaryButton: View {
    let title: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.headline)
                .foregroundColor(.appPrimary)
                .frame(maxWidth: .infinity)
                .padding(.vertical, Spacing.md)
                .background(Color.appPrimary.opacity(0.1))
                .cornerRadius(CornerRadius.medium)
        }
    }
}
```

#### Icon Button

```swift
struct IconButton: View {
    let systemName: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: systemName)
                .font(.title2)
                .foregroundColor(.appPrimary)
                .frame(width: 44, height: 44)
                .background(Color.appPrimary.opacity(0.1))
                .clipShape(Circle())
        }
    }
}
```

---

### 7.2 Cards

#### Affirmation Card

```swift
struct AffirmationCard: View {
    let affirmation: Affirmation

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            Text(affirmation.content)
                .font(.affirmationText)
                .foregroundColor(.onBackground)

            HStack {
                FocusAreaChip(area: affirmation.focusArea)
                Spacer()
            }
        }
        .padding(Spacing.lg)
        .background(Color.appSurface)
        .cornerRadius(CornerRadius.large)
        .cardShadow()
    }
}
```

#### Selection Card

```swift
struct SelectionCard: View {
    let focusArea: FocusArea
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: Spacing.md) {
                Image(systemName: focusArea.systemImage)
                    .foregroundColor(focusArea.color)
                    .font(.title2)

                VStack(alignment: .leading, spacing: Spacing.xxs) {
                    Text(focusArea.rawValue)
                        .font(.headline)
                    Text(focusArea.description)
                        .font(.subheadline)
                        .foregroundColor(.onSurface)
                }

                Spacer()

                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.appPrimary)
                }
            }
            .padding(Spacing.md)
            .background(isSelected ? Color.appPrimary.opacity(0.1) : Color.appSurface)
            .cornerRadius(CornerRadius.large)
            .overlay(
                RoundedRectangle(cornerRadius: CornerRadius.large)
                    .stroke(isSelected ? Color.appPrimary : Color.clear, lineWidth: 2)
            )
        }
        .buttonStyle(.plain)
    }
}
```

---

### 7.3 Chips & Tags

```swift
struct FocusAreaChip: View {
    let area: FocusArea

    var body: some View {
        HStack(spacing: Spacing.xs) {
            Image(systemName: area.systemImage)
                .font(.caption)
            Text(area.rawValue)
                .font(.footnote)
                .fontWeight(.medium)
        }
        .foregroundColor(area.color)
        .padding(.horizontal, Spacing.sm)
        .padding(.vertical, Spacing.xs)
        .background(area.color.opacity(0.15))
        .cornerRadius(CornerRadius.small)
    }
}
```

---

### 7.4 List Rows

```swift
struct SettingsRow: View {
    let icon: String
    let title: String
    let value: String?

    var body: some View {
        HStack(spacing: Spacing.md) {
            Image(systemName: icon)
                .foregroundColor(.appPrimary)
                .frame(width: 24)

            Text(title)
                .font(.body)

            Spacer()

            if let value = value {
                Text(value)
                    .font(.subheadline)
                    .foregroundColor(.onSurface)
            }

            Image(systemName: "chevron.right")
                .font(.caption)
                .foregroundColor(.onSurface.opacity(0.5))
        }
        .padding(.vertical, Spacing.sm)
    }
}
```

---

### 7.5 Loading States

```swift
struct ShimmerView: View {
    @State private var isAnimating = false

    var body: some View {
        Rectangle()
            .fill(
                LinearGradient(
                    colors: [.gray.opacity(0.2), .gray.opacity(0.3), .gray.opacity(0.2)],
                    startPoint: .leading,
                    endPoint: .trailing
                )
            )
            .animation(
                Animation.linear(duration: 1.5).repeatForever(autoreverses: false),
                value: isAnimating
            )
            .onAppear { isAnimating = true }
    }
}
```

---

## 8. Themes (Premium)

### 8.1 Available Themes

| Theme | Background Gradient | Card Color | Description |
|-------|---------------------|------------|-------------|
| **Default** | Stone 50 | White | Clean, minimal |
| **Ocean** | Blue 900 → Cyan 700 | Blue 800 | Calm, water |
| **Sunset** | Orange 300 → Pink 400 | Amber 100 | Warm, energy |
| **Forest** | Green 900 → Emerald 700 | Green 800 | Nature, growth |
| **Midnight** | Slate 900 → Indigo 900 | Slate 800 | Deep, night |

### 8.2 Theme Implementation

```swift
struct Theme: Identifiable {
    let id: String
    let name: String
    let backgroundGradient: LinearGradient
    let surfaceColor: Color
    let textColor: Color
    let isPremium: Bool
}

@Observable
class ThemeManager {
    var currentTheme: Theme = .default

    static let themes: [Theme] = [
        Theme(id: "default", name: "Default", ...),
        Theme(id: "ocean", name: "Ocean", ...),
        Theme(id: "sunset", name: "Sunset", ...),
        Theme(id: "forest", name: "Forest", ...),
        Theme(id: "midnight", name: "Midnight", ...),
    ]
}
```

---

## 9. Iconography

### 9.1 SF Symbols

| Purpose | Symbol | Usage |
|---------|--------|-------|
| Save/Favorite | `heart` / `heart.fill` | Save to favorites |
| Refresh | `arrow.clockwise` | Generate new |
| Settings | `gearshape` | Settings screen |
| History | `clock.arrow.circlepath` | History screen |
| Premium | `star.fill` | Premium badge |
| Privacy | `lock.fill` | Privacy messaging |
| Close | `xmark` | Dismiss sheets |
| Back | `chevron.left` | Navigation back |

### 9.2 Focus Area Icons

| Focus Area | Symbol |
|------------|--------|
| Confidence | `star.fill` |
| Gratitude | `heart.fill` |
| Calm | `leaf.fill` |
| Motivation | `flame.fill` |
| Self-Love | `person.fill` |

---

## 10. Animation Tokens

### 10.1 Timing

| Token | Duration | Easing |
|-------|----------|--------|
| `instant` | 0.1s | easeOut |
| `fast` | 0.2s | easeInOut |
| `normal` | 0.3s | easeInOut |
| `slow` | 0.5s | easeInOut |

### 10.2 Spring

| Token | Response | Damping |
|-------|----------|---------|
| `bouncy` | 0.5 | 0.7 |
| `snappy` | 0.3 | 0.8 |
| `smooth` | 0.6 | 0.9 |

```swift
extension Animation {
    static let bouncy = Animation.spring(response: 0.5, dampingFraction: 0.7)
    static let snappy = Animation.spring(response: 0.3, dampingFraction: 0.8)
    static let smooth = Animation.spring(response: 0.6, dampingFraction: 0.9)
}
```

---

## 11. Accessibility

### 11.1 Minimum Touch Targets

All interactive elements: **44x44pt minimum**

### 11.2 Color Contrast

| Combination | Ratio | WCAG |
|-------------|-------|------|
| Text on Background | 7:1+ | AAA |
| Text on Surface | 4.5:1+ | AA |
| Interactive on Background | 3:1+ | AA |

### 11.3 Reduce Motion

```swift
@Environment(\.accessibilityReduceMotion) var reduceMotion

.animation(reduceMotion ? .none : .bouncy, value: state)
```

---

## 12. Asset Specifications

### 12.1 App Icon

| Size | Scale | Purpose |
|------|-------|---------|
| 1024x1024 | 1x | App Store |
| 180x180 | 3x | iPhone App Icon |
| 120x120 | 2x | iPhone App Icon |
| 87x87 | 3x | iPhone Spotlight |
| 80x80 | 2x | iPhone Spotlight |
| 60x60 | 3x | iPhone Notification |
| 40x40 | 2x | iPhone Notification |

### 12.2 Widget Backgrounds

Export gradients as @2x and @3x PNG for widget backgrounds.

---

## 13. Design Tokens File

```swift
// DesignTokens.swift

import SwiftUI

// MARK: - Spacing
enum Spacing {
    static let xxs: CGFloat = 4
    static let xs: CGFloat = 8
    static let sm: CGFloat = 12
    static let md: CGFloat = 16
    static let lg: CGFloat = 24
    static let xl: CGFloat = 32
    static let xxl: CGFloat = 48
    static let xxxl: CGFloat = 64
}

// MARK: - Corner Radius
enum CornerRadius {
    static let small: CGFloat = 8
    static let medium: CGFloat = 12
    static let large: CGFloat = 16
    static let xlarge: CGFloat = 24
}

// MARK: - Animation
extension Animation {
    static let bouncy = Animation.spring(response: 0.5, dampingFraction: 0.7)
    static let snappy = Animation.spring(response: 0.3, dampingFraction: 0.8)
    static let smooth = Animation.spring(response: 0.6, dampingFraction: 0.9)
}

// MARK: - View Extensions
extension View {
    func cardShadow() -> some View {
        self.shadow(color: .black.opacity(0.10), radius: 8, x: 0, y: 4)
    }

    func subtleShadow() -> some View {
        self.shadow(color: .black.opacity(0.05), radius: 4, x: 0, y: 2)
    }
}
```

---

**Document End**
