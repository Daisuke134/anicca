# MindSnap — Design System

---

## Colors

| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `primary` | `#5B6EF5` (indigo) | `#7B8EFF` | CTAs, active states |
| `background` | `#F8F7FF` (off-white) | `#0F0F1A` | App background |
| `surface` | `#FFFFFF` | `#1A1A2E` | Cards, sheets |
| `text.primary` | `#1A1A2E` | `#F0F0FF` | Body text |
| `text.secondary` | `#6B6B8A` | `#8888AA` | Subtitles, hints |
| `mood.low` | `#FF6B6B` (red) | same | Mood 1-3 |
| `mood.mid` | `#FFD93D` (yellow) | same | Mood 4-7 |
| `mood.high` | `#6BCB77` (green) | same | Mood 8-10 |
| `ai.gradient.start` | `#EEF2FF` | `#1E1E3A` | AI prompt card |
| `ai.gradient.end` | `#F5F0FF` | `#1A1A30` | AI prompt card |

---

## Typography

| Style | Font | Size | Weight |
|-------|------|------|--------|
| `.largeTitle` | SF Pro Rounded | 34pt | Bold |
| `.title` | SF Pro Rounded | 28pt | Semibold |
| `.headline` | SF Pro | 17pt | Semibold |
| `.body` | SF Pro | 17pt | Regular |
| `.caption` | SF Pro | 12pt | Regular |
| `.prompt` | SF Pro Rounded | 16pt | Medium (AI prompts) |

---

## Spacing

| Token | Value |
|-------|-------|
| `xs` | 4pt |
| `sm` | 8pt |
| `md` | 16pt |
| `lg` | 24pt |
| `xl` | 32pt |
| `corner.small` | 8pt |
| `corner.medium` | 16pt |
| `corner.large` | 24pt |

---

## Component Specs

### MoodSlider
- Custom slider, pill shape, 280pt wide
- Gradient fill: red → yellow → green
- Emoji above current value, animates on change
- Haptic feedback: `.light` impact on value change

### CheckInCard
- RoundedRectangle cornerRadius: 20
- Shadow: color `.black.opacity(0.05)`, radius 8, y 4
- Background: `surface`

### PremiumBadge
- "✨ Premium" label
- Background: linear gradient `primary` → lighter variant
- Font: caption, bold, white

### PaywallView.MaybeLateLater button
- Text: "Maybe Later"
- Color: `.secondary`
- Font: `.footnote`
- Padding bottom: 32pt
- Must be visible without scrolling

---

## Motion

| Element | Animation | Duration |
|---------|-----------|---------|
| AI prompt appearance | `.spring(response: 0.4)` | ~400ms |
| Mood slider thumb | `.spring(response: 0.3)` | ~300ms |
| Paywall sheet | `.easeInOut` | 300ms |
| Card tap feedback | `.scaleEffect(0.97)` | 100ms |
