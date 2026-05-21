# UX Specification: EyeBreakIsland

**Version:** 1.0
**Date:** 2026-03-07
**SSOT:** docs/PRD.md
**Architecture:** docs/ARCHITECTURE.md
**Design System:** docs/DESIGN_SYSTEM.md

Source: [Apple HIG: Designing for iOS](https://developer.apple.com/design/human-interface-guidelines/designing-for-ios) — "People interact with iOS devices using Multi-Touch gestures, and expect elements that behave in familiar ways"
Source: [Apple HIG: Onboarding](https://developer.apple.com/design/human-interface-guidelines/onboarding) — "Welcome people with a focused, fast onboarding experience"
Source: [Apple HIG: Live Activities](https://developer.apple.com/design/human-interface-guidelines/live-activities) — "Keep content glanceable"

---

## 1. User Personas

### Primary: Alex — The Screen-Bound Professional

| Attribute | Detail |
|-----------|--------|
| Age | 25-45 |
| Occupation | Software engineer, designer, remote worker |
| Device | iPhone 14 Pro+ (Dynamic Island) |
| Screen Time | 6+ hours/day |
| Goals | Reduce eye fatigue, build 20-20-20 habit, stay productive |
| Frustrations | Forgets breaks during deep work, ignores banner notifications, existing apps require login |
| Tech Comfort | High — uses Shortcuts, widget stacks, Focus modes |
| Trigger | End-of-day headache, dry eyes after long coding session |

### Secondary: Yuki — The Health-Conscious Student

| Attribute | Detail |
|-----------|--------|
| Age | 18-25 |
| Occupation | University student (Japan) |
| Device | iPhone 15 |
| Screen Time | 8+ hours/day (study + social media) |
| Goals | Protect eyesight, form study-break rhythm |
| Frustrations | Apps are English-only, too many features, paid walls everywhere |
| Trigger | Optometrist warned about progressive myopia |

Source: PRD.md §2 Target User — "Screen-bound professionals aged 25-45"

---

## 2. Information Architecture

```
                    ┌─────────────────┐
                    │   App Launch    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
              ┌─NO──│ Onboarding Done?│──YES─┐
              │     └─────────────────┘      │
              │                              │
    ┌─────────▼─────────┐          ┌─────────▼─────────┐
    │   Onboarding Flow │          │    Timer Screen    │
    │                   │          │    (Main Home)     │
    │  Page 1: Problem  │          └─────────┬─────────┘
    │  Page 2: Feature  │                    │
    │  Page 3: Notif.   │          ┌─────────┼─────────┐
    │  Page 4: Paywall  │          │         │         │
    └─────────┬─────────┘    ┌─────▼───┐ ┌───▼───┐ ┌──▼──────┐
              │              │ Break   │ │Settings│ │ Paywall │
              │              │ Overlay │ │ Screen │ │ (Modal) │
              ▼              └─────────┘ └───┬───┘ └─────────┘
    ┌─────────────────┐                      │
    │  Timer Screen   │              ┌───────▼───────┐
    └─────────────────┘              │ Upgrade (Pro) │
                                     └───────────────┘
```

### Navigation Model

| Model | Usage |
|-------|-------|
| Single screen + modal | Timer is the home screen. No tab bar (MVP has 2 screens only) |
| Sheet (`.sheet`) | Settings presented as sheet from Timer screen |
| Full-screen cover | Break overlay presented as `.fullScreenCover` |
| Sheet (`.sheet`) | Paywall presented as sheet from Settings or Onboarding |

**Rationale:** A tab bar adds unnecessary complexity for an app with one primary function. The timer IS the app. Settings and paywall are secondary, accessed via gear icon.

Source: [Apple HIG: Navigation](https://developer.apple.com/design/human-interface-guidelines/navigation) — "Flat navigation: Each screen can reach any other"

---

## 3. Navigation Structure

```
Timer Screen (Home)
├── [Gear icon] → Settings (Sheet)
│   ├── Timer Interval (Pro)
│   ├── Schedule Mode (Pro)
│   ├── Notifications toggle
│   ├── Upgrade to Pro → Paywall (Sheet)
│   ├── Restore Purchases
│   └── About / Privacy Policy
├── [Start/Stop] → Timer Running
│   └── [20 min elapsed] → Break Overlay (FullScreenCover)
│       └── [20 sec completed] → Back to Timer Running
└── Dynamic Island (Live Activity)
    ├── Compact: "eye" icon + "18:34"
    ├── Expanded: Eye Break label + time + break count
    └── Lock Screen: Banner with countdown
```

---

## 4. Screen Inventory

| Screen ID | Name | Presented As | Description |
|-----------|------|-------------|-------------|
| SCR-001 | OnboardingContainer | Root (first launch) | PageView container with dot indicator |
| SCR-002 | OnboardingPage: Problem | Embedded in SCR-001 | "Your Eyes Need Breaks" — problem education |
| SCR-003 | OnboardingPage: Feature | Embedded in SCR-001 | "Always Visible Timer" — Dynamic Island demo |
| SCR-004 | OnboardingPage: Notification | Embedded in SCR-001 | "Stay Reminded" — notification permission |
| SCR-005 | PaywallView | Embedded in SCR-001 / Sheet | Soft paywall with Monthly + Annual + Maybe Later |
| SCR-006 | TimerView | Root (main) | Timer ring, start/stop, break count |
| SCR-007 | BreakOverlayView | FullScreenCover | 20-sec countdown, "Look away" instruction |
| SCR-008 | SettingsView | Sheet from SCR-006 | Preferences, upgrade, restore |

---

## 5. Wireframes

### SCR-006: Timer View (Main Screen)

```
┌─────────────────────────────┐
│ ← (none)        ⚙️ Settings │  ← Navigation bar
│                              │
│                              │
│         ┌──────────┐        │
│        ╱            ╲       │
│       │   18:34      │      │  ← TimerRing (brand.primary)
│       │              │      │     280x280, display font
│        ╲            ╱       │
│         └──────────┘        │
│                              │
│      Next break in           │  ← text.secondary, body
│                              │
│    ━━━━━━━━━━━━━━━━━━━━━    │
│    Today: 3 breaks           │  ← text.secondary, subheadline
│    ━━━━━━━━━━━━━━━━━━━━━    │
│                              │
│     ┌────────────────────┐  │
│     │   ▶  Start Timer   │  │  ← PrimaryButton (brand.primary)
│     └────────────────────┘  │     56pt height, cornerRadius.lg
│                              │
│     ┌────────────────────┐  │
│     │   ■  Stop          │  │  ← SecondaryButton (hidden if idle)
│     └────────────────────┘  │
│                              │
└─────────────────────────────┘
```

### SCR-007: Break Overlay

```
┌─────────────────────────────┐
│          bg.breakOverlay     │
│                              │
│                              │
│     👁                      │  ← SF Symbol "eye.fill" 64pt
│                              │     brand.break color
│     Look away now            │  ← headline1, white
│                              │
│         ┌──────┐            │
│        ╱        ╲           │
│       │   15     │          │  ← TimerRing (brand.break)
│        ╲        ╱           │     display font, white text
│         └──────┘            │
│                              │
│     Look 20 feet away        │  ← body, text.secondary
│     for 20 seconds           │
│                              │
│                              │
│                              │
└─────────────────────────────┘
```

### SCR-001/002/003: Onboarding Pages

```
┌─────────────────────────────┐
│                              │
│                              │
│         [SF Symbol]          │  ← 80pt, brand.primary
│          eye / timer         │
│           / bell             │
│                              │
│     Your Eyes Need Breaks    │  ← headline1
│                              │
│     65% of screen workers    │  ← body, text.secondary
│     experience eye strain.   │     max 3 lines
│     The 20-20-20 rule        │
│     can help.                │
│                              │
│                              │
│     ┌────────────────────┐  │
│     │     Next →         │  │  ← PrimaryButton
│     └────────────────────┘  │
│                              │
│          ● ○ ○ ○            │  ← Page indicator dots
│                              │
└─────────────────────────────┘
```

### SCR-005: Paywall View

```
┌─────────────────────────────┐
│                              │
│     👑                      │  ← SF Symbol "crown.fill"
│                              │     brand.primary, 48pt
│     Protect Your Eyes Daily  │  ← headline1
│     Unlock Pro features      │  ← body, text.secondary
│                              │
│  ┌───────────────────────┐  │
│  │ ○ Annual    $29.99/yr │  │  ← PackageCard (selected)
│  │   7-day free trial    │  │     border: brand.primary
│  │   BEST VALUE          │  │     badge: brand.secondary
│  └───────────────────────┘  │
│                              │
│  ┌───────────────────────┐  │
│  │ ○ Monthly   $4.99/mo  │  │  ← PackageCard (unselected)
│  │   No trial            │  │     border: bg.tertiary
│  └───────────────────────┘  │
│                              │
│  ┌────────────────────────┐ │
│  │      Subscribe         │ │  ← PrimaryButton
│  └────────────────────────┘ │
│                              │
│       Maybe Later            │  ← SecondaryButton (REQUIRED Rule 20)
│                              │
│     Restore Purchases        │  ← caption2, text.tertiary
│                              │
└─────────────────────────────┘
```

### SCR-008: Settings View

```
┌─────────────────────────────┐
│  Settings              Done  │  ← Sheet navigation
│                              │
│  ┌───────────────────────┐  │
│  │ Timer                 │  │  ← GroupedList section
│  │ ┌─────────────────┐   │  │
│  │ │ Interval    20m  │🔒│  │  ← Pro lock icon if free
│  │ └─────────────────┘   │  │
│  │ ┌─────────────────┐   │  │
│  │ │ Schedule   Off  │🔒│  │
│  │ └─────────────────┘   │  │
│  └───────────────────────┘  │
│                              │
│  ┌───────────────────────┐  │
│  │ Notifications         │  │
│  │ ┌─────────────────┐   │  │
│  │ │ Enabled     🔘  │   │  │  ← Toggle
│  │ └─────────────────┘   │  │
│  └───────────────────────┘  │
│                              │
│  ┌───────────────────────┐  │
│  │ Account               │  │
│  │ ┌─────────────────┐   │  │
│  │ │ Upgrade to Pro 👑│  │  │  ← Navigate to PaywallView
│  │ └─────────────────┘   │  │
│  │ ┌─────────────────┐   │  │
│  │ │ Restore Purchase│   │  │
│  │ └─────────────────┘   │  │
│  └───────────────────────┘  │
│                              │
│  ┌───────────────────────┐  │
│  │ About                 │  │
│  │ ┌─────────────────┐   │  │
│  │ │ Privacy Policy  │   │  │
│  │ └─────────────────┘   │  │
│  │ ┌─────────────────┐   │  │
│  │ │ Version 1.0     │   │  │
│  │ └─────────────────┘   │  │
│  └───────────────────────┘  │
└─────────────────────────────┘
```

Source: DESIGN_SYSTEM.md §1 Color Tokens — `brand.primary` (#0A7AFF), `bg.breakOverlay` (#1A1A2E)

---

## 6. Onboarding Flow

### Flow Diagram

```
Page 1: Problem     Page 2: Feature     Page 3: Notification    Page 4: Paywall
┌──────────┐       ┌──────────┐        ┌──────────┐           ┌──────────┐
│ eye icon │ Next→ │timer icon│ Next→  │ bell icon│ Allow→    │crown icon│
│          │       │          │        │          │           │          │
│ Your Eyes│       │ Always   │        │ Stay     │           │ Protect  │
│ Need     │       │ Visible  │        │ Reminded │           │ Your Eyes│
│ Breaks   │       │ Timer    │        │          │           │ Daily    │
│          │       │          │        │[Request] │           │          │
│ [Next]   │       │ [Next]   │        │          │           │[Subscribe│
│          │       │          │        │          │           │[Maybe    │
│ ● ○ ○ ○ │       │ ○ ● ○ ○ │        │ ○ ○ ● ○ │           │ Later]   │
└──────────┘       └──────────┘        └──────────┘           └──────────┘
```

### Page Details

| Page | Screen ID | Icon | Title Key | Subtitle Key | Action |
|------|-----------|------|-----------|-------------|--------|
| 1 | SCR-002 | `eye` | `onboarding.welcome.title` | "65% of screen workers experience digital eye strain. The 20-20-20 rule is proven to help." | Next button |
| 2 | SCR-003 | `timer` | `onboarding.feature.title` | "EyeBreakIsland keeps a countdown in your Dynamic Island. Impossible to ignore." | Next button |
| 3 | SCR-004 | `bell.fill` | `onboarding.notification.title` | "Get reminded even when the app is in the background." | Request notification permission → auto-advance |
| 4 | SCR-005 | `crown.fill` | `paywall.title` | "Unlock Schedule Mode, Custom Intervals, and Break Statistics." | Subscribe / **Maybe Later** (Rule 20) |

### Onboarding Rules

| Rule | Implementation |
|------|---------------|
| Max 4 pages | Pages 1-3 education + Page 4 soft paywall |
| Page 3: Notification permission | `UNUserNotificationCenter.requestAuthorization` on button tap |
| Page 4: Soft paywall (Rule 20) | Custom SwiftUI PaywallView. [Maybe Later] dismisses to Timer |
| No ATT (Rule 20b) | No tracking permission request anywhere |
| Completion flag | `UserDefaults.hasCompletedOnboarding = true` after Page 4 dismiss |
| Skip on return | Check `hasCompletedOnboarding` at launch |

Source: [Apple HIG: Onboarding](https://developer.apple.com/design/human-interface-guidelines/onboarding) — "Keep it brief and fun. Let people get started quickly."

---

## 7. Accessibility

### Accessibility Identifiers (for Maestro E2E)

| ID | Screen | Element |
|----|--------|---------|
| `onboarding_container` | SCR-001 | Onboarding page container |
| `onboarding_page_1` | SCR-002 | Problem education page |
| `onboarding_page_2` | SCR-003 | Feature demo page |
| `onboarding_page_3` | SCR-004 | Notification permission page |
| `onboarding_next_button` | SCR-002/003 | Next button |
| `onboarding_allow_notifications` | SCR-004 | Allow notifications button |
| `paywall_container` | SCR-005 | Paywall view root |
| `paywall_package_annual` | SCR-005 | Annual package card |
| `paywall_package_monthly` | SCR-005 | Monthly package card |
| `paywall_subscribe_button` | SCR-005 | Subscribe CTA |
| `paywall_maybe_later` | SCR-005 | Maybe Later button |
| `paywall_restore` | SCR-005 | Restore purchases link |
| `timer_view` | SCR-006 | Timer screen root |
| `timer_ring` | SCR-006 | Timer countdown ring |
| `timer_time_label` | SCR-006 | "18:34" time display |
| `timer_start_button` | SCR-006 | Start timer button |
| `timer_stop_button` | SCR-006 | Stop timer button |
| `timer_pause_button` | SCR-006 | Pause/resume timer button |
| `timer_break_count` | SCR-006 | "Today: 3 breaks" label |
| `break_overlay` | SCR-007 | Break overlay root |
| `break_countdown` | SCR-007 | 20-sec countdown display |
| `break_instruction` | SCR-007 | "Look 20 feet away" text |
| `settings_view` | SCR-008 | Settings sheet root |
| `settings_interval_row` | SCR-008 | Timer interval setting row |
| `settings_schedule_row` | SCR-008 | Schedule mode row |
| `settings_notifications_toggle` | SCR-008 | Notifications toggle |
| `settings_upgrade_button` | SCR-008 | Upgrade to Pro row |
| `settings_restore_button` | SCR-008 | Restore purchases row |
| `settings_privacy_link` | SCR-008 | Privacy policy link |
| `settings_done_button` | SCR-008 | Done/close button |

---

## 8. Interaction Patterns

### Gestures

| Gesture | Screen | Action |
|---------|--------|--------|
| Tap | SCR-006 Start button | Start 20-min timer + Live Activity |
| Tap | SCR-006 Stop button | Stop timer + end Live Activity |
| Tap | SCR-006 Gear icon | Present Settings sheet |
| Swipe down | SCR-008 Settings | Dismiss sheet |
| Tap | SCR-005 Package card | Select subscription package |
| Tap | SCR-005 Subscribe | Initiate purchase flow |
| Tap | SCR-005 Maybe Later | Dismiss paywall, set `hasCompletedOnboarding` |
| Swipe left/right | SCR-001 Onboarding | Navigate between pages |
| Tap | SCR-002/003 Next | Advance to next onboarding page |
| Tap | Dynamic Island (compact) | Expand to show full timer detail |
| Long press | Dynamic Island (compact) | Expand to full Dynamic Island view |

### State Transitions

```
[Idle] ──Start──→ [Running] ──20min──→ [Breaking] ──20sec──→ [Running]
  ↑                  │                                           │
  │                  │ Stop                                      │ Stop
  │                  ↓                                           ↓
  └──────────────[Idle]◄────────────────────────────────────[Idle]

[Running] ──Pause──→ [Paused] ──Resume──→ [Running]
```

### Haptic Feedback

| Event | Haptic | Type |
|-------|--------|------|
| Timer start | Medium impact | `.impactOccurred(.medium)` |
| Break starts | Heavy impact | `.impactOccurred(.heavy)` |
| Break completes | Success notification | `.notificationOccurred(.success)` |
| Purchase success | Success notification | `.notificationOccurred(.success)` |
| Button tap | Light impact | `.impactOccurred(.light)` |

---

## 9. Localization Notes

### String Length Considerations

| Key | en-US | ja | Length Ratio | Layout Impact |
|-----|-------|----|-------------|---------------|
| `timer.start` | "Start Eye Break" (15) | "目休みタイマー開始" (9) | 0.6x | ja shorter — no issue |
| `paywall.title` | "Protect Your Eyes Daily" (23) | "毎日、目を守ろう" (8) | 0.35x | ja much shorter — consider centering |
| `onboarding.welcome.title` | "Your Eyes Need Breaks" (21) | "目に休憩を" (5) | 0.24x | ja very short — headline1 is fine |
| `settings.upgrade` | "Upgrade to Pro" (14) | "Proにアップグレード" (11) | 0.79x | Similar — no issue |
| `paywall.maybe_later` | "Maybe Later" (11) | "あとで" (3) | 0.27x | ja very short — center |

### Layout Rules

| Rule | Detail |
|------|--------|
| No fixed-width text containers | Use `frame(maxWidth: .infinity)` for buttons |
| Right-to-left | Not required (en-US + ja only, both LTR) |
| Number formatting | Use `NumberFormatter` for break counts |
| Date formatting | Use `DateFormatter` with `Locale.current` |
| Pluralization | Use String Catalog `.stringsdict` for "X breaks" |
| Currency | RevenueCat handles localized pricing display |
| Metric units | ja: "6メートル" (meters) vs en-US: "20 feet" — separate string keys |

Source: [Apple: Localization](https://developer.apple.com/localization/) — "Use Auto Layout and String Catalogs for automatic localization"

---

**End of UX Specification**
