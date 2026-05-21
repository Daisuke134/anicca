# UX Specification: FrostDip

## 1. User Personas

Source: PRD.md §2 Target User, product-plan.md §1

### Primary Persona: "Cold Plunge Chris"

| Attribute | Detail |
|-----------|--------|
| Age | 25-45 |
| Archetype | Biohacker / athlete / wellness enthusiast |
| Equipment | Owns $1K-9K cold plunge tub (portable or built-in) |
| Frequency | Cold plunges 3-7x/week |
| Goals | Track exposure duration precisely, monitor heart rate adaptation, build consistency via streaks |
| Frustrations | Phone stopwatch loses context, hardware-tied apps crash/disconnect, no cross-device standalone tracker exists |
| Emotional State | Motivated but needs reinforcement; cold plunging is inherently uncomfortable — app must reward effort |
| Tech Savvy | High — follows Huberman Lab, Wim Hof, reads biohacking blogs |
| WTP | High — already spends $50-200/mo on wellness subscriptions |

### Secondary Persona: "Contrast Therapy Dana"

| Attribute | Detail |
|-----------|--------|
| Age | 30-50 |
| Archetype | Recovery-focused athlete, sauna + cold plunge user |
| Equipment | Gym/spa access or home sauna + cold plunge |
| Frequency | 2-4x/week contrast sessions |
| Goals | Alternate hot/cold with structured timing, track total contrast minutes |
| Frustrations | No app supports alternating hot/cold timer with round tracking |

---

## 2. Information Architecture

```
FrostDipApp
├── [Gate] OnboardingView (if !has_completed_onboarding)
│   ├── Step 1: WelcomeView
│   ├── Step 2: ExperienceLevelView
│   ├── Step 3: NotificationPermissionView
│   └── Step 4: PaywallView
│
└── [Main] TabView (4 tabs)
    ├── Tab 1: Timer
    │   ├── TimerView (F-001)
    │   │   ├── Protocol selector (F-005/F-009)
    │   │   ├── Temperature input (F-003)
    │   │   └── HR display (F-007, premium)
    │   ├── BreathingPrepView (F-002)
    │   └── SessionSummaryView (F-003)
    │
    ├── Tab 2: History
    │   ├── HistoryView (F-004 free / F-008 premium)
    │   │   ├── 7-day filter (free)
    │   │   └── Full history + search (premium)
    │   └── SessionDetailView
    │
    ├── Tab 3: Progress (premium, F-011)
    │   └── ProgressDashboardView
    │       ├── StreakCalendarView (F-010)
    │       ├── Duration chart
    │       ├── HR trend chart
    │       └── Temperature trend chart
    │
    └── Tab 4: Settings (F-014)
        └── SettingsView
            ├── Temperature unit (C/F)
            ├── Notifications (F-015)
            ├── Upgrade to Premium → PaywallView
            ├── Restore Purchases
            └── About / Privacy Policy
```

---

## 3. Navigation Structure

Source: [Apple HIG — Tab Bars](https://developer.apple.com/design/human-interface-guidelines/tab-bars) — "Use a tab bar for flat information architecture with 3-5 sections"

### Tab Bar Configuration

| Tab | Icon | Label (en) | Label (ja) | Nav Stack |
|-----|------|-----------|-----------|-----------|
| Timer | `timer` | Timer | タイマー | `NavigationStack` — push to BreathingPrepView, SessionSummaryView |
| History | `clock.arrow.circlepath` | History | 履歴 | `NavigationStack` — push to SessionDetailView |
| Progress | `chart.line.uptrend.xyaxis` | Progress | 進捗 | `NavigationStack` — standalone (no push) |
| Settings | `gearshape` | Settings | 設定 | `NavigationStack` — push to PaywallView |

### Modal Presentations

| Modal | Presentation | Dismiss |
|-------|-------------|---------|
| PaywallView (from Settings) | `.sheet` (page sheet) | Swipe down or [Maybe Later] |
| PaywallView (from onboarding) | Full screen (no swipe dismiss) | [Maybe Later] button only |
| SessionSummaryView | `.sheet` (page sheet) | "Done" button or swipe |
| Protocol Editor | `.sheet` (page sheet) | "Save" / "Cancel" |

---

## 4. Screen Inventory

| Screen ID | Name | Tab | Description | Premium |
|-----------|------|-----|-------------|---------|
| SCR-001 | OnboardingWelcome | — | App intro with cold plunge imagery and hook | No |
| SCR-002 | OnboardingExperience | — | Experience level selection (beginner/intermediate/advanced) | No |
| SCR-003 | OnboardingNotification | — | Notification permission request with benefits explanation | No |
| SCR-004 | PaywallView | — / Settings | Subscription plans with benefits, pricing, [Maybe Later] | No |
| SCR-005 | TimerView | Timer | Main countdown with circular ring, HR, protocol selector | No (core) |
| SCR-006 | BreathingPrepView | Timer | Guided breathing animation (inhale/hold/exhale) | No |
| SCR-007 | SessionSummaryView | Timer | Post-session stats: duration, temp, HR avg/max, notes | No |
| SCR-008 | HistoryView | History | Session list (7-day free / unlimited premium) | Partial |
| SCR-009 | SessionDetailView | History | Individual session with all data + notes | No |
| SCR-010 | ProgressDashboardView | Progress | Charts, streak calendar, aggregate stats | Yes |
| SCR-011 | SettingsView | Settings | Preferences, subscription status, about | No |

---

## 5. Wireframes

### SCR-005: TimerView (Main Screen)

```
┌─────────────────────────────────┐
│ ◀ Timer              ❄️ protocol│  ← Navigation bar + protocol selector
├─────────────────────────────────┤
│                                 │
│         ┌───────────┐           │
│        /   02:00     \          │  ← CircularTimerView
│       │   remaining   │         │    brand.accent ring
│        \             /          │    FDFont.timerDigits
│         └───────────┘           │
│                                 │
│       ❤️ 72 BPM (live)         │  ← HR display (premium, F-007)
│                                 │
│    ┌─────────────────────┐      │
│    │ 🌡️ Water Temp: 4°C  │      │  ← Temperature input
│    └─────────────────────┘      │
│                                 │
│    ┌──────┐ ┌──────┐ ┌──────┐  │
│    │ Prep │ │ Start│ │ Stop │  │  ← Action buttons
│    │ 🌬️   │ │ ▶️   │ │ ⏹️   │  │    44pt min touch
│    └──────┘ └──────┘ └──────┘  │
│                                 │
│  Protocol: Beginner (2:00)      │  ← Current protocol display
│  [Change Protocol]              │
│                                 │
└─────────────────────────────────┘
│ Timer │History│Progress│Settings│  ← Tab bar
└─────────────────────────────────┘
```

### SCR-006: BreathingPrepView

```
┌─────────────────────────────────┐
│ ◀ Back                    Skip ▶│
├─────────────────────────────────┤
│                                 │
│          Breathe In             │  ← Phase text (changes)
│                                 │
│         ┌───────────┐           │
│        /             \          │  ← BreathingCircleView
│       │               │         │    Scales with inhale/exhale
│        \             /          │    brand.accent
│         └───────────┘           │
│                                 │
│          4s / 7s / 8s           │  ← Phase timer
│     Inhale → Hold → Exhale     │
│                                 │
│        Round 1 of 3             │  ← Round counter
│                                 │
│    ━━━━━━━━━━━━━━━━━━━━━━━━━   │  ← Progress bar
│    ████████░░░░░░░░░░░░░░░░░   │
│                                 │
└─────────────────────────────────┘
```

### SCR-004: PaywallView

```
┌─────────────────────────────────┐
│                           ✕     │  ← Close (Maybe Later)
├─────────────────────────────────┤
│                                 │
│    ❄️ Unlock Your Full          │  ← Headline
│    Cold Potential                │    .title2.bold()
│                                 │
│    ┌─────────────────────────┐  │
│    │ ❤️ Live heart rate       │  │  ← Benefits list
│    │ 📊 Unlimited history     │  │    BenefitRowView x5
│    │ 🏋️ Custom protocols      │  │
│    │ 🔥 Streak tracking       │  │
│    │ 🌡️ Contrast therapy      │  │
│    └─────────────────────────┘  │
│                                 │
│  ┌────────────┐ ┌────────────┐  │  ← PricingCardView x2
│  │  Monthly   │ │  Annual    │  │
│  │  $6.99/mo  │ │ $29.99/yr  │  │
│  │            │ │ Save 64%   │  │    brand.hot badge
│  │            │ │ $2.50/mo   │  │    Strikethrough
│  └────────────┘ └────────────┘  │
│                                 │
│  ┌─────────────────────────┐    │
│  │  Start My Cold Journey  │    │  ← Primary CTA
│  └─────────────────────────┘    │    brand.primary filled
│                                 │
│       Maybe Later               │  ← Secondary (Rule 20)
│                                 │
│  Join 1,000+ cold plungers     │  ← Social proof
│  ⭐⭐⭐⭐⭐                     │
│                                 │
│  Privacy Policy · Terms of Use  │  ← Legal links
│  Restore Purchases              │
│                                 │
└─────────────────────────────────┘
```

### SCR-008: HistoryView

```
┌─────────────────────────────────┐
│ History                   🔍    │  ← Large title + search (premium)
├─────────────────────────────────┤
│                                 │
│  Today                          │
│  ┌─────────────────────────┐    │
│  │ ❄️ Cold Plunge  3:00     │   │  ← SessionCardView
│  │    4°C  ❤️ 68 BPM avg   │   │    Swipe to delete
│  └─────────────────────────┘    │
│                                 │
│  Yesterday                      │
│  ┌─────────────────────────┐    │
│  │ ❄️ Cold Plunge  2:30     │   │
│  │    5°C  ❤️ 72 BPM avg   │   │
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │ 🔥 Contrast   4 rounds  │   │  ← Contrast session
│  │    Hot 3:00 / Cold 2:00  │   │
│  └─────────────────────────┘    │
│                                 │
│  ── 7-day limit ──────────     │
│  🔒 View older sessions        │  ← Premium gate
│  [Upgrade to Premium]           │    → PaywallView
│                                 │
└─────────────────────────────────┘
│ Timer │History│Progress│Settings│
└─────────────────────────────────┘
```

### SCR-010: ProgressDashboardView (Premium)

**Free User Behavior:** Free users see a blurred preview of ProgressDashboardView with a centered "Unlock Progress" button that opens PaywallView as a `.sheet`. This ensures the premium value is visible while gating access.

```
┌─────────────────────────────────┐
│ Progress                        │  ← Large title
├─────────────────────────────────┤
│                                 │
│  🔥 12-day streak    Best: 28   │  ← Streak counters
│                                 │
│  ┌─────────────────────────┐    │
│  │  M  T  W  T  F  S  S   │    │  ← StreakCalendarView
│  │  ●  ●  ●  ●  ○  ●  ●   │    │    30-day grid
│  │  ●  ●  ○  ●  ●  ●  ●   │    │    ● = plunged
│  │  ●  ●  ●  ●  ●  ○  ○   │    │    ○ = missed
│  └─────────────────────────┘    │
│                                 │
│  Duration Trend                 │
│  ┌─────────────────────────┐    │
│  │  3:00 ─╱──╱───────      │    │  ← Swift Charts
│  │  2:00 ╱──╱              │    │
│  │  1:00                    │    │
│  │  W1   W2   W3   W4      │    │
│  └─────────────────────────┘    │
│                                 │
│  ┌──────┐ ┌──────┐ ┌──────┐   │  ← StatCardView x3
│  │ 48   │ │ 2:15 │ │ 4.2° │   │
│  │ total│ │ avg  │ │ avg  │   │
│  │ sess │ │ dur  │ │ temp │   │
│  └──────┘ └──────┘ └──────┘   │
│                                 │
└─────────────────────────────────┘
│ Timer │History│Progress│Settings│
└─────────────────────────────────┘
```

---

## 6. Onboarding Flow

Source: [Mau — 8 Rules for High-Converting Onboarding](references/onboarding.md)
Source: PRD.md §6 F-006, §8 Paywall Design Requirements

### Flow Structure (3-Act)

```
Act 1: Problem & Personalization
  ├── Step 1: WelcomeView (Problem Empathy — Rule 1)
  └── Step 2: ExperienceLevelView (Self-Persuasion — Rule 2)

Act 2: Value & Commitment
  └── Step 3: NotificationPermissionView (Commitment — Rule 7)

Act 3: Paywall
  └── Step 4: PaywallView (Soft Paywall — Rule 5, 8)
```

### Step Details

| Step | Screen | Content | a11y ID | Rule |
|------|--------|---------|---------|------|
| 1 | WelcomeView | Hook: "Tired of timing your cold plunge with a stopwatch?" + App preview imagery + "Get Started" CTA | `onboarding_get_started` | Rule 1 (3-Act) |
| 2 | ExperienceLevelView | "How experienced are you with cold plunging?" → 3 options (Beginner / Intermediate / Advanced). Saves to `experience_level` UserDefaults. Mirror: "Great, we'll set you up with a [level] protocol" | `onboarding_experience_beginner`, `onboarding_experience_intermediate`, `onboarding_experience_advanced`, `onboarding_continue` | Rule 2 (Self-Persuasion), Rule 3 (Mirror) |
| 3 | NotificationPermissionView | "Stay consistent with daily reminders" + benefit bullets + "Enable Notifications" button (calls `NotificationService.requestPermission()`) + "Not Now" skip | `onboarding_enable_notifications`, `onboarding_skip_notifications` | Rule 7 (Commitment) |
| 4 | PaywallView | Full paywall per PRD §8 requirements. [Maybe Later] dismisses and completes onboarding (sets `has_completed_onboarding = true`) | `paywall_view`, `paywall_cta`, `paywall_maybe_later`, `paywall_plan_monthly`, `paywall_plan_annual`, `paywall_restore` | Rule 5 (Experience), Rule 8 (10%+ conversion) |

### Onboarding Navigation

| From | To | Trigger | Animation |
|------|-----|---------|-----------|
| WelcomeView | ExperienceLevelView | "Get Started" tap | Slide left |
| ExperienceLevelView | NotificationPermissionView | Experience selected + "Continue" | Slide left |
| NotificationPermissionView | PaywallView | Permission result (granted or denied) | Slide left |
| PaywallView | Main TabView | Purchase success OR "Maybe Later" | Fade transition |

### Post-Onboarding

| Action | Result |
|--------|--------|
| Purchase completed | `has_completed_onboarding = true`, dismiss onboarding, show TabView |
| "Maybe Later" tapped | `has_completed_onboarding = true`, dismiss onboarding, show TabView (free tier) |
| App killed during onboarding | Resume at step 1 (no partial save) |

---

## 7. Accessibility

Source: [Apple HIG — Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility)
Source: DESIGN_SYSTEM.md §7

### accessibilityIdentifier Table

| ID | Screen | Element | Type |
|----|--------|---------|------|
| `onboarding_get_started` | SCR-001 | "Get Started" button | Button |
| `onboarding_experience_beginner` | SCR-002 | Beginner option | Button |
| `onboarding_experience_intermediate` | SCR-002 | Intermediate option | Button |
| `onboarding_experience_advanced` | SCR-002 | Advanced option | Button |
| `onboarding_continue` | SCR-002 | Continue button | Button |
| `onboarding_enable_notifications` | SCR-003 | Enable notifications button | Button |
| `onboarding_skip_notifications` | SCR-003 | Skip button | Button |
| `paywall_view` | SCR-004 | PaywallView container | View |
| `paywall_headline` | SCR-004 | Headline text | Text |
| `paywall_plan_monthly` | SCR-004 | Monthly plan card | Button |
| `paywall_plan_annual` | SCR-004 | Annual plan card | Button |
| `paywall_cta` | SCR-004 | CTA button | Button |
| `paywall_maybe_later` | SCR-004 | Maybe Later button | Button |
| `paywall_restore` | SCR-004 | Restore Purchases button | Button |
| `timer_view` | SCR-005 | TimerView container | View |
| `circular_timer` | SCR-005 | Circular countdown ring | View |
| `timer_start` | SCR-005 | Start button | Button |
| `timer_pause` | SCR-005 | Pause button | Button |
| `timer_stop` | SCR-005 | Stop button | Button |
| `timer_breathing_prep` | SCR-005 | Breathing prep button | Button |
| `timer_protocol_selector` | SCR-005 | Protocol picker | Picker |
| `timer_temperature_input` | SCR-005 | Temperature stepper | Stepper |
| `timer_hr_display` | SCR-005 | Heart rate BPM label | Text |
| `breathing_circle` | SCR-006 | Breathing animation circle | View |
| `breathing_phase_label` | SCR-006 | Current phase text | Text |
| `breathing_skip` | SCR-006 | Skip button | Button |
| `session_summary_view` | SCR-007 | Summary container | View |
| `session_summary_duration` | SCR-007 | Duration label | Text |
| `session_summary_temp` | SCR-007 | Temperature label | Text |
| `session_summary_hr` | SCR-007 | Heart rate label | Text |
| `session_summary_notes` | SCR-007 | Notes text field | TextField |
| `session_summary_save` | SCR-007 | Save button | Button |
| `history_view` | SCR-008 | HistoryView container | View |
| `history_search` | SCR-008 | Search field (premium) | TextField |
| `session_card` | SCR-008 | Session list row (dynamic) | View |
| `history_upgrade_banner` | SCR-008 | Premium upgrade banner | Button |
| `session_detail_view` | SCR-009 | SessionDetailView container | View |
| `progress_view` | SCR-010 | ProgressDashboardView container | View |
| `streak_calendar` | SCR-010 | Streak calendar grid | View |
| `streak_current` | SCR-010 | Current streak counter | Text |
| `streak_longest` | SCR-010 | Longest streak counter | Text |
| `progress_duration_chart` | SCR-010 | Duration trend chart | View |
| `settings_view` | SCR-011 | SettingsView container | View |
| `settings_temp_unit` | SCR-011 | Temperature unit toggle | Picker |
| `settings_notifications` | SCR-011 | Notification toggle | Toggle |
| `settings_upgrade` | SCR-011 | Upgrade to Premium row | Button |
| `settings_restore` | SCR-011 | Restore Purchases row | Button |
| `settings_privacy` | SCR-011 | Privacy Policy link | Link |

---

## 8. Interaction Patterns

Source: [Apple HIG — Gestures](https://developer.apple.com/design/human-interface-guidelines/gestures)

### Gesture Map

| Screen | Gesture | Action | Feedback |
|--------|---------|--------|----------|
| TimerView | Tap Start | Begin countdown (or breathing prep) | Haptic `.heavy` + ring animation starts |
| TimerView | Tap Pause | Pause countdown | Haptic `.light` + ring pauses |
| TimerView | Tap Stop | Stop and show summary | Confirmation alert → SessionSummaryView |
| BreathingPrepView | Tap Skip | Skip to timer | Slide transition |
| HistoryView | Swipe left on row | Delete session | `.destructive` swipe action + confirmation |
| HistoryView | Tap row | Push to SessionDetailView | Standard push |
| HistoryView | Pull down | Refresh (recalculate) | System refresh control |
| SessionSummaryView | Swipe down | Dismiss sheet | Standard sheet dismiss |
| PaywallView | Tap plan card | Select plan | Haptic `.light` + border highlight |
| PaywallView | Tap CTA | Purchase flow | Loading spinner → success/error |
| SettingsView | Tap temp toggle | Switch C/F | Immediate update across app |
| ProgressDashboardView | Tap chart point | Show detail tooltip | Popover with date + value |
| OnboardingView | Swipe left | Next step (disabled — button only) | — |

### State Transitions

| State | Timer Display | Actions Available | Tab Bar |
|-------|-------------|-------------------|---------|
| Idle | Protocol duration (e.g. "2:00") | Start, Prep, Protocol selector | Visible |
| Breathing Prep | Prep countdown + phase animation | Skip, Stop | Hidden |
| Timer Running | Countdown + HR display | Pause, Stop | Hidden |
| Timer Paused | Frozen countdown | Resume, Stop | Hidden |
| Session Complete | Summary sheet (session auto-saved as draft per F-003) | Done (confirm), Delete, Add Notes | Visible |

---

## 9. Localization Notes

Source: PRD.md §11, product-plan.md §5 Localization

### String Length Considerations

| Element | en-US | ja | Layout Impact |
|---------|-------|-----|---------------|
| Tab labels | 7-8 chars ("History") | 2-3 chars ("履歴") | ja shorter — no overflow risk |
| Button: "Start Session" | 13 chars | 7 chars ("セッション開始") | ja shorter |
| Button: "Maybe Later" | 11 chars | 3 chars ("あとで") | ja significantly shorter |
| Paywall headline | ~30 chars | ~15 chars | ja shorter — may need centering adjustment |
| Notification body | ~50 chars | ~25 chars | ja shorter — fits easily |
| Settings labels | 10-20 chars | 8-15 chars | ja slightly shorter — no issue |

### Layout Rules

| Rule | Implementation |
|------|---------------|
| No fixed-width text containers | Use `.frame(maxWidth: .infinity)` |
| Right-to-left future-proofing | Use `.leading`/`.trailing` not `.left`/`.right` |
| Date formatting | `DateFormatter` with `.locale = Locale.current` |
| Number formatting | `NumberFormatter` for temperature, duration |
| Pluralization | Use String Catalog (`.xcstrings`) substitution rules |
| App name | "FrostDip" — universal, not translated |

### Locale-Specific Behavior

| Feature | en-US | ja |
|---------|-------|----|
| Default temp unit | Fahrenheit | Celsius |
| Date format | MM/dd/yyyy | yyyy/MM/dd |
| Number decimal | Period (4.5) | Period (4.5) |
| Currency display | $6.99 | $6.99 (Apple handles localized pricing) |
