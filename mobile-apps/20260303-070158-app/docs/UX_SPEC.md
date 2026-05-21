# MindSnap — UX Specification

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| **30-second rule** | Every core flow completable in 30 seconds |
| **Calm, not clinical** | Soft colors, rounded shapes, no harsh UI |
| **No anxiety** | No streaks (no shame), no mandatory fields |
| **Privacy visible** | "Stays on device" messaging throughout |

---

## Screen Specifications

### HomeView
- Large greeting: "Good morning, [weekday]"
- Today's mood prompt card (if check-in done: shows today's prompt)
- Quick check-in button: "How are you feeling?" → opens CheckInView
- Last 2 check-in previews (mood color + date)
- Bottom tab: Home | History | Insights | Settings

### CheckInView
- **Step 1:** Mood slider (1–10), custom pill design, color gradient (red→yellow→green)
- Emoji indicator at current value (😔 😐 😊)
- **Step 2:** Note field: "Add a note (optional)" — single-line, no pressure
- **Step 3:** AI Prompt card appears after mood set: loading state → "✨ Generating your prompt..."
- Prompt displayed in card with slight gradient background
- CTA: "Save Check-in" button (primary)
- Navigation: X to dismiss

### HistoryView
- List of past check-ins, newest first
- Each row: date, mood color dot, first line of note
- Free tier: shows last 7 days, older entries blurred with "Upgrade to see full history"
- Pull to refresh (triggers new insights fetch)

### InsightsView (Premium)
- Weekly summary card: "This week you averaged 6.4/10"
- AI-generated pattern text (Foundation Models): "You tend to feel better on weekends..."
- Mood graph (simple bar chart, SwiftUI Charts)
- Locked state for free users: blurred preview + "Unlock with Premium"

### PaywallView (Soft Paywall)
- Shown when free user tries to access week 2+ history or Insights
- Headline: "See your full history"
- Benefits list: Unlimited history, Weekly AI insights, Home screen widget
- Monthly button: "$4.99/month — Start Free Trial"
- Annual button (highlighted): "$29.99/year — Best Value (50% off)"
- **[Maybe Later] link** — bottom, always visible, dismisses paywall

### SettingsView
- Notification toggle + time picker
- Export data (JSON) — free feature
- Restore purchases
- Privacy note: "All data stays on your device"
- Rate MindSnap link

---

## User Flow: First Launch

```
App opens
    ↓
Splash (2 sec) — "MindSnap" logo fade in
    ↓
HomeView (no onboarding screens)
    ↓
"How are you feeling today?" prompt
    ↓
User taps → CheckInView
    ↓
Sets mood → note (optional) → AI prompt generates
    ↓
Saves → HomeView updated
```

**No onboarding carousel. No account creation. Value in first 30 seconds.**

---

## Paywall Trigger Points

| Trigger | Screen |
|---------|--------|
| Access history older than 7 days | HistoryView |
| Access InsightsView | InsightsView |
| Add widget (settings) | SettingsView |
