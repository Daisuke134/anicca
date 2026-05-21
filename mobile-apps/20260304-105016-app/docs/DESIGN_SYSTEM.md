# Design System: Chi Daily

**Version:** 1.0
**Date:** 2026-03-04

---

## 1. Color Palette

### Brand Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `brand-earth` | `#8B7355` | Primary accent — Earth/warm tone |
| `brand-sage` | `#7A9E7E` | Secondary — Wood/nature |
| `brand-cream` | `#F5F0E8` | Background (light mode) |
| `brand-ink` | `#1C1C1E` | Primary text |

### Constitution Colors

| Constitution | Hex | SF Symbol |
|-------------|-----|-----------|
| Wood 木 | `#5C8A4F` | leaf.fill |
| Fire 火 | `#C85A3C` | flame.fill |
| Earth 土 | `#A07840` | mountain.2.fill |
| Metal 金 | `#888888` | circle.hexagongrid.fill |
| Water 水 | `#4472A8` | drop.fill |

### Semantic Colors (SwiftUI adaptive)

| Token | Light Mode | Dark Mode |
|-------|-----------|-----------|
| `background` | `#F5F0E8` | `#1C1C1E` |
| `surface` | `#FFFFFF` | `#2C2C2E` |
| `textPrimary` | `#1C1C1E` | `#F5F0E8` |
| `textSecondary` | `#6D6D72` | `#8D8D92` |
| `accent` | `#8B7355` | `#C4A882` |

```swift
// DesignTokens.swift
extension Color {
    static let brandEarth = Color(hex: "#8B7355")
    static let brandSage = Color(hex: "#7A9E7E")
    static let brandCream = Color(hex: "#F5F0E8")
    static let chiBackground = Color(.systemBackground)
    static let chiSurface = Color(.secondarySystemBackground)
    static let chiAccent = Color.brandEarth
}
```

---

## 2. Typography

Uses iOS Dynamic Type — all text scales automatically with user's preferred text size.

| Style | SwiftUI | Use Case |
|-------|---------|---------|
| `.largeTitle` | `Font.largeTitle` | Screen headings |
| `.title` | `Font.title` | Section headers |
| `.title2` | `Font.title2` | Constitution name |
| `.headline` | `Font.headline` | Card titles, question text |
| `.body` | `Font.body` | Recommendation body text |
| `.subheadline` | `Font.subheadline` | Metadata, secondary labels |
| `.caption` | `Font.caption` | TCM reasoning, fine print |

**Font weight:**
- `.bold` for question text + card titles
- `.regular` for body content

---

## 3. Spacing (8-pt Grid)

| Token | Value | Usage |
|-------|-------|-------|
| `xs` | 4pt | Tight internal spacing |
| `sm` | 8pt | Between related elements |
| `md` | 16pt | Standard component padding |
| `lg` | 24pt | Section separation |
| `xl` | 32pt | Screen-level separation |
| `xxl` | 48pt | Major visual breaks |

```swift
// Spacing.swift
enum Spacing {
    static let xs: CGFloat = 4
    static let sm: CGFloat = 8
    static let md: CGFloat = 16
    static let lg: CGFloat = 24
    static let xl: CGFloat = 32
    static let xxl: CGFloat = 48
}
```

---

## 4. Corner Radii

| Token | Value | Usage |
|-------|-------|-------|
| `sm` | 8 | Small chips, tags |
| `md` | 12 | Cards, buttons |
| `lg` | 16 | Full-screen sheets |
| `pill` | 999 | Rounded pill buttons |

---

## 5. Components

### PrimaryButton

```swift
struct PrimaryButton: View {
    let title: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.headline)
                .foregroundStyle(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, Spacing.md)
                .background(Color.chiAccent)
                .cornerRadius(12)
        }
    }
}
```

### SecondaryButton (text-only, "Maybe Later")

```swift
struct SecondaryButton: View {
    let title: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.subheadline)
                .foregroundStyle(Color.chiAccent)
        }
    }
}
```

### RecommendationCard

```swift
struct RecommendationCard: View {
    let category: RecommendationCategory  // food / movement / rest
    let title: String
    let body: String

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            HStack {
                Text(category.rawValue)   // 食 / 動 / 息
                    .font(.title2).bold()
                    .foregroundStyle(category.color)
                Text(category.localizedName)
                    .font(.headline)
                    .foregroundStyle(.secondary)
            }
            Text(body)
                .font(.body)
                .foregroundStyle(Color.primary)
        }
        .padding(Spacing.md)
        .background(Color.chiSurface)
        .cornerRadius(12)
    }
}
```

### QuestionRow

```swift
struct QuestionRow: View {
    let option: Int     // 1–5
    let label: String
    let emoji: String
    let isSelected: Bool
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            HStack {
                Text(emoji).font(.title2)
                Text(label).font(.body)
                Spacer()
                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(Color.chiAccent)
                }
            }
            .padding(Spacing.md)
            .background(isSelected ? Color.chiAccent.opacity(0.12) : Color.chiSurface)
            .cornerRadius(12)
        }
        .buttonStyle(.plain)
    }
}
```

### ConstitutionBadge

```swift
struct ConstitutionBadge: View {
    let type: ConstitutionType

    var body: some View {
        VStack(spacing: Spacing.sm) {
            Image(systemName: type.icon)
                .font(.system(size: 48))
                .foregroundStyle(type.color)
            Text(type.rawValue)
                .font(.title2).bold()
            Text(type.japaneseName)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }
}
```

---

## 6. Animations

| Action | Animation |
|--------|-----------|
| Question transition (Next) | `.transition(.asymmetric(insertion: .move(edge: .trailing), removal: .move(edge: .leading)))` |
| Result appear | `.transition(.opacity).animation(.easeInOut(duration: 0.4))` |
| Card appear (staggered) | Delay 0.1s between each card |
| Loading (Foundation Models) | `ProgressView()` with pulsing opacity |

---

## 7. Iconography

Uses SF Symbols throughout. No custom icon assets needed for MVP.

| UI Element | SF Symbol |
|-----------|-----------|
| Today tab | `sun.max` |
| History tab | `calendar` |
| Check-in | `checkmark.circle` |
| Food | `fork.knife` |
| Movement | `figure.walk` |
| Rest | `moon.fill` |
| Wood constitution | `leaf.fill` |
| Fire constitution | `flame.fill` |
| Earth constitution | `mountain.2.fill` |
| Metal constitution | `circle.hexagongrid.fill` |
| Water constitution | `drop.fill` |

---

## 8. App Icon Concept

- **Style:** Minimalist yin-yang merged with leaf motif
- **Background:** Warm gradient (cream → sand)
- **Foreground:** Single TCM symbol in `brand-earth` color
- **Size:** 1024×1024px (Xcode asset catalog handles all sizes)
- **No text** in icon (App Store guidelines)
