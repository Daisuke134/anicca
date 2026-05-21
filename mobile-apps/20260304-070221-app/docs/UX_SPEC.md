# UX Specification: BreathStory

**Date:** 2026-03-04
**Version:** 1.0.0

Source: [Apple HIG](https://developer.apple.com/design/human-interface-guidelines/) — all interactions follow Apple HIG.

---

## User Journey

```
Install → Onboarding (3 screens) → Home (story grid)
                                       ↓
                              Tap story (free) → Player
                              Tap story (locked) → Soft Paywall
                                                        ↓
                                              Subscribe → Player
                                              Maybe Later → Home
```

---

## Screen Specifications

### 1. OnboardingView

**Goal:** Establish value proposition in 3 screens before asking for anything.

| Screen | Headline | Body | CTA |
|--------|----------|------|-----|
| 1/3 | "Breathing helps. But it's boring." | "73% of breathing app users quit in 3 days. Not because breathing doesn't work — because apps make it feel like homework." | → |
| 2/3 | "What if breathing felt like a story?" | "BreathStory guides your breath through immersive audio journeys. Just press play and breathe naturally." | → |
| 3/3 | "Try 3 stories, free." | "No credit card. No commitment. Just your first breath." | "Start Breathing" |

**Rules:**
- Skip button visible on all screens
- No paywall on onboarding
- Progress dots indicator
- Auto-advance disabled (user controls pacing)

---

### 2. HomeView

**Layout:** 2-column grid of story cards

**Story Card:**
- Background: gradient thumbnail (world-specific colors)
- Title: story name (e.g. "The Forest Path")
- Duration: "4 min" badge
- Lock icon: shown for premium stories when user is on free tier
- Streak counter: in top-right navigation bar

**Free vs Premium indicator:**
- Free stories: no lock, full color
- Locked stories (non-premium user): lock icon overlay, slightly desaturated
- After subscription: all stories full color, no locks

---

### 3. PlayerView

**Layout:** Full-screen immersive experience

```
┌────────────────────────────────┐
│  ← Back          [story name] │
│                                │
│                                │
│          ⭕ BREATHING RING ⭕   │
│         (animated circle)      │
│                                │
│      "INHALE..." / "EXHALE..."  │
│         (phase label)          │
│                                │
│     ────────────────────       │
│     ▶ Narrative text preview   │
│     (current story text line)  │
│                                │
│  [■ Stop]              [⏸ Pause]│
└────────────────────────────────┘
```

**Breathing Animation (SwiftUI):**
- Inhale: circle expands from 100pt to 180pt (duration = inhale_seconds)
- Hold: circle stays at 180pt
- Exhale: circle contracts from 180pt to 100pt (duration = exhale_seconds)
- Color: calm blue → green during exhale
- Haptic feedback on inhale/exhale transition (Core Haptics, optional)

**AVSpeechSynthesizer narration:**
- Voice: `AVSpeechSynthesisVoiceIdentifier.alexIdentifier` (English) or system default
- Rate: 0.45–0.50 (slower than default for calming effect)
- Pitch: 0.9 (slightly lower than default)
- Background soundscape: plays simultaneously at 40% volume via AVPlayer

**Breathing patterns per story:**

| Story | Pattern | Timing |
|-------|---------|--------|
| The Forest Path | 4-7-8 | inhale:4s, hold:7s, exhale:8s |
| Ocean Drift | Box breathing | 4-4-4-4 |
| Rain in the City | Coherent | 5s-5s |
| Starfield | 4-6 | inhale:4s, exhale:6s |
| Mountain Summit | Physiological sigh | double-inhale:2+2s, exhale:8s |

---

### 4. PaywallView (Custom SwiftUI — NOT RevenueCatUI)

**CRITICAL:** [Maybe Later] MUST always be visible. This is a hard rule.

**Layout:**

```
┌────────────────────────────────┐
│          ✕ Maybe Later         │  ← always visible top-right
│                                │
│    🌊 BreathStory Premium       │
│    Unlimited breathing stories │
│                                │
│  ┌──────────────────────────┐  │
│  │  ⭐ Annual — $49.99/yr   │  │  ← highlighted (best value)
│  │  $4.17/month · Save 48% │  │
│  └──────────────────────────┘  │
│  ┌──────────────────────────┐  │
│  │  Monthly — $7.99/mo     │  │
│  └──────────────────────────┘  │
│                                │
│  [Start 7-Day Free Trial]      │  ← primary CTA
│                                │
│  Cancel anytime · Restore      │
│  Privacy Policy · Terms        │
└────────────────────────────────┘
```

**Rules:**
- Annual plan visually highlighted by default
- "Start 7-Day Free Trial" as primary CTA (not "Subscribe")
- "Restore Purchases" link always visible
- Legal links (Privacy + Terms) always visible
- [Maybe Later] dismisses paywall, does NOT close app

---

### 5. SettingsView

| Item | Action |
|------|--------|
| Current streak | Display only |
| Subscription status | Display: Free / Premium |
| Restore Purchases | `Purchases.shared.restorePurchases()` |
| Privacy Policy | Open Safari |
| Terms of Use | Open Safari |
| App version | Display only |

---

## Accessibility

| Standard | Implementation |
|---------|----------------|
| VoiceOver | All interactive elements labeled |
| Dynamic Type | All text uses system font scales |
| Reduce Motion | Breathing animation respects `accessibilityReduceMotion` |
| Minimum tap target | 44×44pt minimum (Apple HIG) |

Source: [Apple HIG — Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility)
