# UI/UX Specification: DeskStretch

> **Version:** 1.0 | **Date:** 2026-03-05

---

## 1. Design Principles

| Principle | Application |
|-----------|------------|
| **Calm Technology** | No anxiety-inducing elements. Gentle reminders, not aggressive alarms |
| **Minimal Interaction** | Notification → 1 tap → stretch starts. Maximum 2 taps to any action |
| **Forgiveness** | Missed a stretch? No guilt. "Welcome back" not "You missed 3 sessions" |
| **Accessibility First** | VoiceOver support, Dynamic Type, sufficient contrast ratios |
| **Desk Context** | All exercises doable at a desk/chair. No floor, no equipment |

Source: [Apple HIG — Designing for iPhone](https://developer.apple.com/design/human-interface-guidelines/designing-for-ios) — 「People generally prefer to use iPhone apps in brief sessions as part of their regular routine.」

---

## 2. Information Architecture

```
DeskStretch
├── Onboarding (first launch only)
│   ├── Problem Empathy
│   ├── Pain Area Selection
│   └── Soft Paywall
├── Tab 1: Timer (default)
│   ├── Countdown Display
│   ├── Quick Start Button
│   └── Timer Settings Sheet
├── Tab 2: Library
│   ├── Category Filter (Neck/Back/Shoulders/Wrists)
│   ├── Exercise List
│   └── Exercise Detail
├── Tab 3: Progress
│   ├── Today's Stretches
│   ├── Current Streak
│   └── Total Sessions
├── Tab 4: Settings
│   ├── Timer Interval
│   ├── Pain Areas
│   ├── Work Hours
│   ├── Notifications
│   ├── Subscription (Manage/Upgrade)
│   └── About (Privacy, Terms, Version)
└── Stretch Session (modal, from notification or manual)
    ├── Exercise Step 1/3
    ├── Exercise Step 2/3
    ├── Exercise Step 3/3
    └── Completion Summary
```

---

## 3. Screen Specifications

### Screen 1: Onboarding — Problem Empathy

```
┌─────────────────────────────┐
│                             │
│      [SF Symbol: figure     │
│       .seated.side]         │
│                             │
│   "Back pain from sitting   │
│      all day?"              │
│                             │
│   80% of office workers     │
│   experience muscle pain    │
│   from prolonged sitting.   │
│                             │
│   DeskStretch reminds you   │
│   to move and guides you    │
│   through personalized      │
│   stretches.                │
│                             │
│                             │
│    ┌─────────────────────┐  │
│    │     Get Started      │  │
│    └─────────────────────┘  │
│                             │
│         ● ○ ○               │
└─────────────────────────────┘
```

| Element | Spec |
|---------|------|
| Illustration | SF Symbol `figure.seated.side` at 80pt |
| Headline | 24pt Bold, primary color |
| Body | 16pt Regular, secondary color |
| CTA Button | Full-width, tinted, 50pt height |
| Page indicator | 3 dots at bottom |

### Screen 2: Onboarding — Pain Area Selection

```
┌─────────────────────────────┐
│                             │
│   "Where does it hurt?"     │
│                             │
│   Select your problem areas │
│   (choose one or more)      │
│                             │
│   ┌───────────┐ ┌─────────┐│
│   │  🔵 Neck  │ │ 🔵 Back ││
│   │  [icon]   │ │ [icon]  ││
│   └───────────┘ └─────────┘│
│   ┌───────────┐ ┌─────────┐│
│   │ Shoulders │ │ Wrists  ││
│   │  [icon]   │ │ [icon]  ││
│   └───────────┘ └─────────┘│
│                             │
│                             │
│    ┌─────────────────────┐  │
│    │     Continue         │  │
│    └─────────────────────┘  │
│                             │
│         ○ ● ○               │
└─────────────────────────────┘
```

| Element | Spec |
|---------|------|
| Pain area cards | 2×2 grid, selectable (toggle), tinted when selected |
| SF Symbols | `neck`, `figure.arms.open`, `hand.raised`, `hand.wave` |
| Selection state | Blue tint + checkmark overlay |
| Minimum selection | 1 area required to proceed |

### Screen 3: Onboarding — Soft Paywall

```
┌─────────────────────────────┐
│                             │
│   "Unlock Your Full         │
│    Stretch Routine"         │
│                             │
│   ✅ Unlimited stretches    │
│   ✅ Pain-targeted          │
│   ✅ All pain areas         │
│   ✅ Custom schedules       │
│   ✅ Progress tracking      │
│                             │
│   ┌─────────────────────┐   │
│   │  Annual $29.99/yr   │   │
│   │  Save 37%           │   │
│   └─────────────────────┘   │
│   ┌─────────────────────┐   │
│   │  Monthly $3.99/mo   │   │
│   └─────────────────────┘   │
│                             │
│   7-day free trial          │
│                             │
│   [Maybe Later]  [Restore]  │
│                             │
│   Terms · Privacy           │
│         ○ ○ ●               │
└─────────────────────────────┘
```

| Element | Spec |
|---------|------|
| Headline | 28pt Bold |
| Benefits | SF Symbol checkmarks, 16pt Regular |
| Annual button | Primary (filled), highlighted with "Save 37%" badge |
| Monthly button | Secondary (outlined) |
| Maybe Later | Text button, 14pt, secondary color |
| Restore | Text button, 14pt, secondary color |
| Legal links | 12pt, tertiary color |

### Screen 4: Timer Tab (Main Screen)

```
┌─────────────────────────────┐
│  DeskStretch          [gear]│
│                             │
│                             │
│         ┌───────┐           │
│         │ 42:15 │           │
│         │       │           │
│         │  min  │           │
│         └───────┘           │
│                             │
│    Next break in 42 min     │
│                             │
│    ┌─────────────────────┐  │
│    │   Stretch Now        │  │
│    └─────────────────────┘  │
│                             │
│    ┌─────────────────────┐  │
│    │   Pause Timer        │  │
│    └─────────────────────┘  │
│                             │
│   Interval: 60 min [Edit]   │
│                             │
├─────────────────────────────┤
│ [Timer]  [Library] [Progress│
│                   ] [Settings]│
└─────────────────────────────┘
```

| Element | Spec |
|---------|------|
| Timer display | Circular progress ring, 160pt diameter |
| Time text | 48pt Bold, monospaced |
| Stretch Now | Primary CTA, full-width |
| Pause Timer | Secondary, full-width |
| Tab bar | 4 tabs with SF Symbols |

### Screen 5: Stretch Library

```
┌─────────────────────────────┐
│  Stretch Library            │
│                             │
│  [All] [Neck] [Back]       │
│  [Shoulders] [Wrists]       │
│                             │
│  ┌─────────────────────────┐│
│  │ [icon] Neck Rolls       ││
│  │ 30 sec · Neck           ││
│  └─────────────────────────┘│
│  ┌─────────────────────────┐│
│  │ [icon] Chin Tucks       ││
│  │ 20 sec · Neck           ││
│  └─────────────────────────┘│
│  ┌─────────────────────────┐│
│  │ [icon] Spinal Twist     ││
│  │ 30 sec · Back           ││
│  └─────────────────────────┘│
│  ┌─────────────────────────┐│
│  │ 🔒 Shoulder Shrugs     ││
│  │ Premium · Shoulders     ││
│  └─────────────────────────┘│
│                             │
├─────────────────────────────┤
│ [Timer]  [Library] [Progress│
│                   ] [Settings]│
└─────────────────────────────┘
```

| Element | Spec |
|---------|------|
| Filter chips | Horizontal scroll, pill-shaped, toggleable |
| Exercise card | Leading SF Symbol, title, duration, category |
| Lock icon | Premium-only exercises show lock for free users |
| Tap action | Navigate to detail or start session |

### Screen 6: Stretch Session (Modal)

```
┌─────────────────────────────┐
│  [X Close]     Step 1 of 3  │
│                             │
│      [SF Symbol: large]     │
│                             │
│      "Neck Rolls"           │
│                             │
│   Slowly roll your head     │
│   in a circle. 5 times      │
│   clockwise, then 5 times   │
│   counter-clockwise.        │
│                             │
│         ┌───────┐           │
│         │  25   │           │
│         │  sec  │           │
│         └───────┘           │
│                             │
│    ┌─────────────────────┐  │
│    │     Skip →           │  │
│    └─────────────────────┘  │
│                             │
│    ─────●───────────────    │
│    1/3                      │
└─────────────────────────────┘
```

| Element | Spec |
|---------|------|
| Close button | Top-left X, dismisses session |
| Step indicator | "Step X of Y" top-right |
| SF Symbol | 80pt, tinted |
| Exercise name | 24pt Bold |
| Instructions | 16pt Regular, multi-line |
| Countdown | Circular, auto-decrement, haptic at 3-2-1 |
| Skip button | Secondary, advances to next exercise |
| Progress bar | Linear, shows position in session |

### Screen 7: Session Complete

```
┌─────────────────────────────┐
│                             │
│      [SF Symbol: checkmark  │
│       .circle.fill]         │
│                             │
│    "Great stretch!"         │
│                             │
│    3 exercises · 2 min      │
│                             │
│    Today: 3 stretches       │
│    Streak: 5 days 🔥        │
│                             │
│                             │
│    ┌─────────────────────┐  │
│    │       Done           │  │
│    └─────────────────────┘  │
│                             │
└─────────────────────────────┘
```

### Screen 8: Progress Dashboard

```
┌─────────────────────────────┐
│  Your Progress              │
│                             │
│  ┌──────┐  ┌──────┐        │
│  │  3   │  │  5   │        │
│  │Today │  │Streak│        │
│  └──────┘  └──────┘        │
│  ┌──────┐  ┌──────┐        │
│  │ 47   │  │ 82   │        │
│  │Total │  │ min  │        │
│  │Sess. │  │Total │        │
│  └──────┘  └──────┘        │
│                             │
│  This Week                  │
│  M  T  W  T  F  S  S       │
│  ●  ●  ●  ●  ●  ○  ○      │
│                             │
├─────────────────────────────┤
│ [Timer]  [Library] [Progress│
│                   ] [Settings]│
└─────────────────────────────┘
```

### Screen 9: Settings

```
┌─────────────────────────────┐
│  Settings                   │
│                             │
│  TIMER                      │
│  ┌─────────────────────────┐│
│  │ Break Interval    60min ││
│  │ Work Hours   9:00-18:00 ││
│  └─────────────────────────┘│
│                             │
│  STRETCH                    │
│  ┌─────────────────────────┐│
│  │ Pain Areas    Neck,Back ││
│  └─────────────────────────┘│
│                             │
│  NOTIFICATIONS              │
│  ┌─────────────────────────┐│
│  │ Break Reminders     [ON]││
│  │ Morning Stretch     [ON]││
│  └─────────────────────────┘│
│                             │
│  SUBSCRIPTION               │
│  ┌─────────────────────────┐│
│  │ Plan          Premium   ││
│  │ Manage Subscription   > ││
│  └─────────────────────────┘│
│                             │
│  ABOUT                      │
│  ┌─────────────────────────┐│
│  │ Privacy Policy        > ││
│  │ Terms of Use          > ││
│  │ Version           1.0.0 ││
│  └─────────────────────────┘│
├─────────────────────────────┤
│ [Timer]  [Library] [Progress│
│                   ] [Settings]│
└─────────────────────────────┘
```

---

## 4. Navigation

### Tab Bar

| Tab | SF Symbol | Label |
|-----|-----------|-------|
| Timer | `timer` | Timer |
| Library | `figure.flexibility` | Library |
| Progress | `chart.bar.fill` | Progress |
| Settings | `gearshape` | Settings |

### Navigation Patterns

| Action | Pattern |
|--------|---------|
| Tab switching | TabView (native) |
| Exercise detail | NavigationStack push |
| Stretch session | Full-screen modal (.fullScreenCover) |
| Timer settings | Sheet (.sheet) |
| Paywall | Sheet (.sheet) |
| Onboarding | Full-screen modal (one-time) |

---

## 5. Animations & Transitions

| Element | Animation | Duration |
|---------|-----------|----------|
| Timer countdown | Circular progress ring, smooth decrement | Continuous |
| Exercise transition | Slide left (next) / right (previous) | 0.3s |
| Session complete | Checkmark scale-up + haptic | 0.5s |
| Streak fire emoji | Subtle pulse | 1.0s loop |
| Pain area selection | Scale + tint toggle | 0.2s |

---

## 6. Accessibility

| Feature | Implementation |
|---------|---------------|
| VoiceOver | All elements labeled with `.accessibilityLabel()` |
| Dynamic Type | All text scales with system font size |
| Color Contrast | WCAG AA minimum (4.5:1 for text) |
| Reduce Motion | Respect `UIAccessibility.isReduceMotionEnabled` |
| Haptics | Timer countdown (3-2-1), session complete, exercise transition |
| Accessibility IDs | All interactive elements have `.accessibilityIdentifier()` for Maestro |

---

## 7. Localization

| String Category | Count (est.) | Notes |
|----------------|--------------|-------|
| Onboarding | 15 | Headlines, body text, CTA buttons |
| Timer | 10 | Labels, states, settings |
| Library | 40+ | Exercise names, instructions, categories |
| Progress | 10 | Metrics labels, streak messages |
| Settings | 20 | Section headers, option labels |
| Paywall | 15 | Benefits, pricing, legal |
| **Total** | **~110** | en-US + ja |

### Localization Rules

| Rule | Detail |
|------|--------|
| No hardcoded strings | All user-facing text in .xcstrings |
| Pluralization | Use String Catalogs plural rules |
| Date/time | `Date.FormatStyle` for locale-aware formatting |
| Currency | RevenueCat SDK provides localized pricing |
