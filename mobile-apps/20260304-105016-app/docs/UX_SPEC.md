# UX Specification: Chi Daily

**Version:** 1.0
**Date:** 2026-03-04

---

## 1. Design Principles

| Principle | Description |
|-----------|-------------|
| **Calm & grounded** | Earthy, serene aesthetic — mirrors TCM's connection to nature |
| **5-second entry** | Every screen's primary action is obvious within 5 seconds |
| **Privacy-first** | No login, no account, no "we're collecting data" friction |
| **Bilingual native** | Japanese and English feel equally designed, not translated |

---

## 2. Onboarding Flow (3 Screens)

### Screen 1: Welcome

```
┌─────────────────────────────────┐
│                                 │
│           ☯  Chi Daily          │
│                                 │
│    Your daily TCM wellness      │
│          coach                  │
│                                 │
│   "5 questions. Personalized    │
│    guidance. All on your        │
│    device."                     │
│                                 │
│                                 │
│   ┌───────────────────────┐    │
│   │    Get Started →      │    │
│   └───────────────────────┘    │
│                                 │
│   ○ ○ ○  (page indicator)      │
└─────────────────────────────────┘
```

**Interaction:** "Get Started" → Screen 2. No skip needed.

### Screen 2: TCM Constitution Intro

```
┌─────────────────────────────────┐
│                                 │
│   🌿 What is a TCM              │
│      Constitution?              │
│                                 │
│   In Traditional Chinese        │
│   Medicine, your body has a     │
│   unique type that changes      │
│   day to day.                   │
│                                 │
│   🌳 Wood  🔥 Fire  🌍 Earth    │
│   🪨 Metal  💧 Water            │
│                                 │
│   Chi Daily checks in daily     │
│   and adapts your guidance.     │
│                                 │
│   ┌───────────────────────┐    │
│   │    Continue →         │    │
│   └───────────────────────┘    │
│   ○ ● ○                        │
└─────────────────────────────────┘
```

### Screen 3: Soft Paywall (Onboarding Final)

```
┌─────────────────────────────────┐
│                                 │
│   ✨ Start Your Free Trial      │
│                                 │
│   Unlimited daily check-ins     │
│   On-device AI guidance         │
│   HealthKit integration         │
│   English + Japanese            │
│                                 │
│   ┌───────────────────────┐    │
│   │  Start 7-Day Trial    │    │
│   │  Then $4.99/month     │    │
│   └───────────────────────┘    │
│                                 │
│   ┌───────────────────────┐    │
│   │  $34.99/year (save 42%) │  │
│   └───────────────────────┘    │
│                                 │
│   [Maybe Later]                 │
│   Restore Purchases             │
│                                 │
│   ● Terms · Privacy Policy      │
└─────────────────────────────────┘
```

**CRITICAL:** "Maybe Later" always visible. [Maybe Later] exits to HomeView. Never a hard gate.

---

## 3. Home View

```
┌─────────────────────────────────┐
│  Chi Daily          ☰           │
├─────────────────────────────────┤
│                                 │
│  Good morning, 水曜日           │
│  Wednesday, March 4             │
│                                 │
│  ┌───────────────────────────┐  │
│  │  Today's Check-in         │  │
│  │  "How are you feeling?"   │  │
│  │                           │  │
│  │  ┌─────────────────────┐  │  │
│  │  │ Start Check-in →    │  │  │
│  │  └─────────────────────┘  │  │
│  └───────────────────────────┘  │
│                                 │
│  ── Today's Result ──           │
│  (shown after check-in done)    │
│                                 │
│  🌍 Earth Constitution          │
│                                 │
│  ┌──────┐ ┌──────┐ ┌──────┐   │
│  │ 食   │ │ 動   │ │ 息   │   │
│  │Food  │ │Move  │ │Rest  │   │
│  └──────┘ └──────┘ └──────┘   │
│                                 │
├─────────────────────────────────┤
│  Today  │  History              │
└─────────────────────────────────┘
```

**States:**
- `no-check-in-today`: Shows "Start Check-in" card prominently
- `check-in-done`: Shows constitution + 3 recommendation cards
- `free-tier-exhausted`: "Start Check-in" shows paywall

---

## 4. Check-in View

```
┌─────────────────────────────────┐
│  ← Today's Check-in             │
│  ━━━━━━━━━━░░░░░  Q1/5          │
├─────────────────────────────────┤
│                                 │
│  How is your energy today?      │
│  今日のエネルギーはどうですか？  │
│                                 │
│  ①  😴  Very Low                │
│  ②  😑  Low                     │
│  ③  😊  Moderate    ← selected │
│  ④  😄  Good                    │
│  ⑤  🌟  Excellent               │
│                                 │
│                                 │
│  ┌───────────────────────────┐  │
│  │       Next →              │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

**5 Questions:**
1. Energy level (今日のエネルギー)
2. Sleep quality last night (昨夜の睡眠)
3. Digestion comfort (消化の状態)
4. Emotional state (気持ちの状態)
5. Physical sensation (体の感覚)

**Progress bar:** Fills as user advances Q1→Q5.
**Back navigation:** Tap `←` to go to previous question.
**Submit:** On Q5, "Get My Plan" button replaces "Next".

---

## 5. Result View

```
┌─────────────────────────────────┐
│  ← Your Daily Plan              │
├─────────────────────────────────┤
│                                 │
│  Today you are...               │
│                                 │
│         🌍                      │
│     Earth Constitution          │
│     土のタイプ                  │
│                                 │
│  ─────────────────────────────  │
│                                 │
│  食 Food                        │
│  ┌───────────────────────────┐  │
│  │ Warm soups and root       │  │
│  │ vegetables today. Your    │  │
│  │ spleen needs grounding.   │  │
│  └───────────────────────────┘  │
│                                 │
│  動 Movement                    │
│  ┌───────────────────────────┐  │
│  │ 20-min gentle walk.       │  │
│  │ Avoid intense cardio —    │  │
│  │ Earth type needs rhythm.  │  │
│  └───────────────────────────┘  │
│                                 │
│  息 Rest                        │
│  ┌───────────────────────────┐  │
│  │ Nap 2–4 PM if possible.   │  │
│  │ Sleep by 10 PM tonight.   │  │
│  └───────────────────────────┘  │
│                                 │
│  ┌───────────────────────────┐  │
│  │       Done ✓              │  │
│  └───────────────────────────┘  │
│                                 │
└─────────────────────────────────┘
```

---

## 6. History View

```
┌─────────────────────────────────┐
│  History                        │
├─────────────────────────────────┤
│  March 2026                     │
│  ─────────────────────────────  │
│  ┌───────────────────────────┐  │
│  │ Mar 4  🌍 Earth    →      │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │ Mar 3  💧 Water    →      │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │ Mar 2  🌳 Wood     →      │  │
│  └───────────────────────────┘  │
│                                 │
│  (empty state if < 1 entry)     │
│  "Complete your first check-in" │
└─────────────────────────────────┘
```

**Tap row:** Opens HistoryDetailView showing full ResultView for that day (read-only).

---

## 7. Paywall View (Mid-App)

Same design as Onboarding Screen 3, presented as a sheet.
- "Maybe Later" always visible (dismisses sheet)
- No progress bar (not onboarding context)
- Shows "You've used your 3 free check-ins" message at top

---

## 8. Accessibility

| Element | Requirement |
|---------|------------|
| All interactive elements | `.accessibilityLabel()` set |
| Question options | Announced as "Option 1 of 5: Very Low" |
| Recommendation cards | Full card text read as one unit |
| Color | Not used as sole indicator of meaning |
| Dynamic Type | All text uses `.font(.headline)` etc. (scales with system size) |
| VoiceOver | Tab order matches visual order |

---

## 9. Empty States

| Screen | Empty State |
|--------|------------|
| HomeView (no check-in) | "Start today's check-in" CTA card |
| HistoryView (0 entries) | Illustration + "Complete your first check-in to see history" |
| HistoryView (< 7 entries) | Shows available entries; no filler |
