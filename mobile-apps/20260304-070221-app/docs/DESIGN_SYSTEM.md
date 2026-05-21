# Design System: BreathStory

**Date:** 2026-03-04
**Version:** 1.0.0

Source: [Apple HIG — Color](https://developer.apple.com/design/human-interface-guidelines/color)
Source: [Apple HIG — Typography](https://developer.apple.com/design/human-interface-guidelines/typography)

---

## Brand Identity

**Mood:** Calm, natural, trustworthy, modern
**Aesthetic:** Soft gradients + clean typography + ample white space
**Inspiration:** Linear, Headspace (calm), Nothing Phone UI (minimal)

---

## Color Palette

### Primary Colors

| Name | Light Mode | Dark Mode | Usage |
|------|-----------|-----------|-------|
| `breathBlue` | `#4A90D9` | `#6BB3F5` | Breathing ring, primary CTA |
| `breathGreen` | `#34C759` | `#30D158` | Exhale phase, success |
| `breathPurple` | `#7C5CBF` | `#A78BFA` | Premium badge, paywall accent |

### Neutral Colors

| Name | Light Mode | Dark Mode | Usage |
|------|-----------|-----------|-------|
| `backgroundPrimary` | `#FFFFFF` | `#000000` | Main background |
| `backgroundSecondary` | `#F2F2F7` | `#1C1C1E` | Card backgrounds |
| `textPrimary` | `#000000` | `#FFFFFF` | Headlines |
| `textSecondary` | `#6C6C70` | `#8E8E93` | Body, captions |

### Story World Gradients

| World | From | To |
|-------|------|----|
| Forest Path | `#2D6A4F` | `#74C69D` |
| Ocean Drift | `#1E3A5F` | `#4DABF7` |
| Rain in the City | `#4A4E69` | `#9A8C98` |
| Starfield | `#0B0B1A` | `#2D2B55` |
| Mountain Summit | `#6B705C` | `#C8D5B9` |

---

## Typography

All text uses San Francisco (SF Pro) — Apple system font.

| Style | SwiftUI | Weight | Size |
|-------|---------|--------|------|
| Large Title | `.largeTitle` | Bold | 34pt |
| Title | `.title` | Semibold | 28pt |
| Title 2 | `.title2` | Semibold | 22pt |
| Headline | `.headline` | Semibold | 17pt |
| Body | `.body` | Regular | 17pt |
| Callout | `.callout` | Regular | 16pt |
| Subheadline | `.subheadline` | Regular | 15pt |
| Footnote | `.footnote` | Regular | 13pt |
| Caption | `.caption` | Regular | 12pt |

---

## Spacing System (8pt grid)

| Token | Value |
|-------|-------|
| `spacing2` | 2pt |
| `spacing4` | 4pt |
| `spacing8` | 8pt |
| `spacing12` | 12pt |
| `spacing16` | 16pt |
| `spacing24` | 24pt |
| `spacing32` | 32pt |
| `spacing48` | 48pt |

---

## Component Specifications

### Story Card

```
Width: fill container (grid column)
Height: 160pt
Corner radius: 16pt
Padding: 16pt internal
Background: world gradient (LinearGradient)
Shadow: 0pt (flat design)

Title: .headline, white, bottom-left
Duration badge: .caption, white/70%, bottom-right
Lock icon: SF Symbol "lock.fill", white, center-right overlay
```

### Breathing Ring

```
Outer ring: Circle, stroke 4pt, breathBlue
Inner fill: Circle, fill breathBlue/10%
Size (rest): 100pt diameter
Size (inhale): 180pt diameter
Animation: .easeInOut, duration = breath_phase_seconds
Phase label: .title2, textSecondary, below ring, 24pt gap
```

### Primary Button (CTA)

```
Height: 56pt
Corner radius: 14pt
Background: breathBlue
Text: .headline, white
Padding: 16pt horizontal
Width: fill container
```

### Secondary Button / Maybe Later

```
Height: 44pt
Background: clear
Text: .subheadline, textSecondary
No border
```

### Paywall Card

```
Background: backgroundSecondary
Corner radius: 16pt
Padding: 20pt
Border: 2pt breathPurple (selected), 1pt textSecondary/20% (unselected)
```

---

## Icons

All icons use SF Symbols (system-provided, no custom icons needed for MVP).

| Usage | SF Symbol |
|-------|-----------|
| Lock (premium) | `lock.fill` |
| Play | `play.fill` |
| Pause | `pause.fill` |
| Stop | `stop.fill` |
| Settings | `gearshape.fill` |
| Streak | `flame.fill` |
| Premium | `crown.fill` |
| Back | `chevron.left` |

Source: [SF Symbols 5](https://developer.apple.com/sf-symbols/)

---

## Dark Mode

- All colors use `Color(uiColor: .label)` / `.secondaryLabel` patterns where possible
- Custom colors defined with light/dark variants in Asset Catalog
- Background: pure black in dark mode (true black for OLED)
- Story world gradients: same in both modes (intentional — they're "worlds")
