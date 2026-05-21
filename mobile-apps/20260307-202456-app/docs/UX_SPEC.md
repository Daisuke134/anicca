# UX Specification: EyeRest

## 1. User Personas

Source: PRD.md §2 — Target User
Source: product-plan.md §1 — Primary persona: knowledge workers 25-45

### Primary Persona: Yuki (Developer)

| Attribute | Value |
|-----------|-------|
| Name | Yuki |
| Age | 32 |
| Role | Full-stack developer, remote |
| Screen Time | 10+ hours/day (MacBook + iPhone) |
| Pain Point | Chronic eye fatigue, tension headaches by 3pm |
| Goals | Build a habit of regular eye breaks without disrupting flow state |
| Frustrations | Tried Eye Care 20 20 20 — required login, timer stopped when switching apps |
| Tech Comfort | High — wants minimal UI, no onboarding friction |
| Willingness to Pay | $5/mo for a tool that reliably works in background |

### Secondary Persona: Sarah (Student)

| Attribute | Value |
|-----------|-------|
| Name | Sarah |
| Age | 24 |
| Role | Graduate student, long study sessions |
| Screen Time | 8 hours/day (laptop + phone) |
| Pain Point | Dry eyes, blurred vision after lecture + study |
| Goals | Follow doctor's 20-20-20 recommendation consistently |
| Frustrations | Forgets to take breaks when focused on studying |
| Tech Comfort | Medium — wants clear instructions and visual guidance |
| Willingness to Pay | $2.50/mo (annual plan) for eye exercises + tracking |

---

## 2. Information Architecture

Source: ARCHITECTURE.md §2 — System Architecture Diagram
Source: PRD.md §6 — 13 MVP Features mapped to screens

```
                    ┌──────────────────┐
                    │    App Launch     │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ hasCompleted      │
                    │ Onboarding?       │
                    └──┬──────────┬────┘
                   NO  │          │ YES
              ┌────────▼──┐  ┌───▼───────────┐
              │ Onboarding │  │  MainTabView  │
              │ Flow       │  │               │
              └────────┬───┘  └───────────────┘
                       │              │
              ┌────────▼───┐    ┌─────┼──────────┐
              │ PaywallView │    │     │          │
              │ (soft)      │    │     │          │
              └────┬───┬───┘    │     │          │
           Purchase│   │Later   │     │          │
              ┌────▼───▼───┐    │     │          │
              │ MainTabView │    │     │          │
              └────────────┘    │     │          │
                                │     │          │
                   ┌────────────▼┐ ┌──▼───────┐ ┌▼──────────┐
                   │ Tab 1:Timer │ │Tab 2:    │ │Tab 3:     │
                   │ (TimerView) │ │Exercises │ │Stats      │
                   └──────┬──────┘ └──┬───────┘ └──┬────────┘
                          │           │             │
                   ┌──────▼──────┐    │        ┌───▼─────────┐
                   │ RestView    │    │        │ WeeklyChart  │
                   │ (modal)     │    │        │ (premium)    │
                   └──────┬──────┘    │        └─────────────┘
                          │      ┌────▼────────┐
                   ┌──────▼────┐ │ExerciseDetail│
                   │ Fatigue   │ │(premium lock)│
                   │ Picker    │ └──────────────┘
                   │ (premium) │
                   └───────────┘

             Settings (gear icon in Timer nav bar)
                   │
              ┌────▼──────────┐
              │ SettingsView  │
              │  ├─Interval   │
              │  ├─Schedule   │
              │  ├─Notif Sound│
              │  └─Upgrade    │───> PaywallView
              └───────────────┘
```

---

## 3. Navigation Structure

Source: [Apple HIG — Tab bars](https://developer.apple.com/design/human-interface-guidelines/tab-bars) — "Use a tab bar to enable navigation between top-level sections"

### Tab Bar (3 Tabs)

| Tab | Label | Icon | Root View | Features |
|-----|-------|------|-----------|----------|
| 1 | Timer | `timer` | TimerView | F-001, F-002, F-003, F-004 |
| 2 | Exercises | `eye` | ExerciseListView | F-005, F-008 |
| 3 | Stats | `chart.bar.fill` | StatsView | F-004, F-009, F-011 |

### Navigation Stacks

| Tab | Stack Depth | Screens |
|-----|-------------|---------|
| Timer | 1 (flat) + modal | TimerView → RestView (fullScreenCover) |
| Exercises | 2 | ExerciseListView → ExerciseDetailView |
| Stats | 1 (flat) | StatsView (scrollable sections) |

### Modal Presentations

| Modal | Presentation | Trigger | Dismissal |
|-------|-------------|---------|-----------|
| RestView | `.fullScreenCover` | Timer reaches zero / notification tap | Auto-dismiss after 20s countdown |
| PaywallView | `.sheet` (page) | Onboarding final step / Settings "Upgrade" / Premium feature tap | Context-dependent (see below) |

**PaywallView Dismissal Behavior:**

| Context | [Maybe Later] | [X] Close | Swipe Down |
|---------|:---:|:---:|:---:|
| Onboarding (final step) | YES | NO | NO (`.interactiveDismissDisabled`) |
| Settings / Premium feature tap | YES | YES | YES |
| SettingsView | `NavigationLink` push | Gear icon in Timer nav bar | Back button |

---

## 4. Screen Inventory

| Screen ID | Name | Tab | Description | Features |
|-----------|------|-----|-------------|----------|
| SCR-001 | OnboardingWelcome | — | Welcome screen: app name + value proposition | F-006 |
| SCR-002 | OnboardingNotification | — | Notification permission request | F-006, F-003 |
| SCR-003 | PaywallView | — / Modal | Soft paywall with Monthly/Annual toggle | F-006, F-013 |
| SCR-010 | TimerView | Timer | Main countdown timer with circular ring | F-001, F-004 |
| SCR-011 | RestView | Timer (modal) | 20-second guided rest with animation | F-002 |
| SCR-020 | ExerciseListView | Exercises | Grid/list of 8 eye exercises | F-005, F-008 |
| SCR-021 | ExerciseDetailView | Exercises | Step-by-step exercise instructions | F-005, F-008 |
| SCR-030 | StatsView | Stats | Daily/weekly stats dashboard | F-004, F-009, F-011 |
| SCR-040 | SettingsView | Timer (push) | Timer interval, schedule, sound, upgrade | F-007, F-010, F-012 |

---

## 5. Wireframes

Source: DESIGN_SYSTEM.md — Color tokens, typography, spacing applied

### SCR-010: TimerView (Main Screen)

```
┌─────────────────────────────────┐
│ ◀ EyeRest              [gear]  │ ← Nav bar + settings
│                                 │
│                                 │
│        ┌─────────────┐          │
│        │             │          │
│        │   19:42     │          │ ← TimerRing (brand.primary)
│        │             │          │    72pt ultralight monospaced
│        └─────────────┘          │
│                                 │
│     Time until next break       │ ← .headline, text.secondary
│                                 │
│        ┌─────────────┐          │
│        │  ▶  Start   │          │ ← Primary CTA (brand.primary)
│        └─────────────┘          │
│                                 │
│     ┌───────────────────────┐   │
│     │ 🔥 3 breaks today     │   │ ← BreakCountBadge
│     │    5-day streak       │   │    success color
│     └───────────────────────┘   │
│                                 │
│ [Timer]    [Exercises]  [Stats] │ ← Tab bar
└─────────────────────────────────┘
```

### SCR-011: RestView (Full-Screen Modal)

```
┌─────────────────────────────────┐
│                                 │
│         ┌─ restGradient ──┐     │ ← Animated gradient bg
│         │                 │     │
│         │      20         │     │ ← 96pt thin countdown
│         │    seconds      │     │    brand.calm
│         │                 │     │
│         └─────────────────┘     │
│                                 │
│    Look at something            │ ← .title2 bold
│    20 feet away                 │    white on gradient
│                                 │
│    ┌─────────────────────┐      │
│    │  👁️ Rest your eyes  │      │ ← Instruction card
│    │  Focus on a distant │      │
│    │  object and blink   │      │
│    └─────────────────────┘      │
│                                 │
│  [Skip]                         │ ← .footnote, text.tertiary
│                                 │
└─────────────────────────────────┘
```

### SCR-003: PaywallView (Soft Paywall)

```
┌─────────────────────────────────┐
│                          [x]    │ ← Close / dismiss
│                                 │
│    ┌── premiumGradient ────┐    │
│    │  Unlock EyeRest       │    │ ← .title bold, white
│    │  Premium               │    │
│    └───────────────────────┘    │
│                                 │
│  ✓ Custom intervals (10-30m)    │ ← FeatureRow × 5
│  ✓ 8 guided eye exercises       │    brand.premium checkmarks
│  ✓ Eye fatigue tracking         │
│  ✓ Working hours schedule       │
│  ✓ Weekly health insights       │
│                                 │
│  ┌─────────┐ ┌─────────────┐   │
│  │ Monthly │ │  Annual ★   │   │ ← PlanToggle
│  │ $4.99/mo│ │ $29.99/yr   │   │    Annual highlighted
│  └─────────┘ │ 3-day trial │   │
│              └─────────────┘   │
│                                 │
│  ┌─────────────────────────┐   │
│  │    Continue             │   │ ← Primary CTA (brand.premium)
│  └─────────────────────────┘   │
│                                 │
│       Maybe Later               │ ← .footnote, text.tertiary
│    Restore Purchases            │    Rule 20: [Maybe Later]
│                                 │
└─────────────────────────────────┘
```

### SCR-020: ExerciseListView

```
┌─────────────────────────────────┐
│ Eye Exercises                   │ ← .largeTitle
│                                 │
│  ┌──────────┐ ┌──────────┐     │
│  │ 🤲       │ │ 🔒 ∞    │     │ ← ExerciseCard grid
│  │ Palming  │ │ Figure-8 │     │    2 columns
│  │ 60s FREE │ │ 45s PRO  │     │    Lock overlay for premium
│  └──────────┘ └──────────┘     │
│  ┌──────────┐ ┌──────────┐     │
│  │ 🔒 👁️    │ │ 🔒 🔄    │     │
│  │ Near-Far │ │ Extended │     │
│  │ 60s PRO  │ │ 30s PRO  │     │
│  └──────────┘ └──────────┘     │
│  ┌──────────┐ ┌──────────┐     │
│  │ 🔒 👀    │ │ 🔒 ✏️    │     │
│  │ Blink    │ │ Pencil   │     │
│  │ 30s PRO  │ │ 45s PRO  │     │
│  └──────────┘ └──────────┘     │
│  ┌──────────┐ ┌──────────┐     │
│  │ 🔒 🔄    │ │ 🔒 💆    │     │
│  │ Rolling  │ │ Temple   │     │
│  │ 30s PRO  │ │ 60s PRO  │     │
│  └──────────┘ └──────────┘     │
│                                 │
│ [Timer]    [Exercises]  [Stats] │
└─────────────────────────────────┘
```

### SCR-030: StatsView

```
┌─────────────────────────────────┐
│ Eye Health                      │ ← .largeTitle
│                                 │
│ ┌──────────────────────────┐    │
│ │ Today                    │    │
│ │ ┌──────┐ ┌──────┐ ┌────┐│    │ ← StatCard × 3
│ │ │  5   │ │  12  │ │ 2.1││    │
│ │ │breaks│ │streak│ │avg ││    │
│ │ └──────┘ └──────┘ └────┘│    │
│ └──────────────────────────┘    │
│                                 │
│ ┌──────────────────────────┐    │
│ │ This Week (breaks)       │    │
│ │ ██                       │    │ ← WeeklyChart
│ │ ██ ██                    │    │    7-day bars
│ │ ██ ██ ██ ██              │    │
│ │ ██ ██ ██ ██ ██           │    │
│ │ M  T  W  T  F  S  S     │    │
│ └──────────────────────────┘    │
│                                 │
│ ┌──────────────────────────┐    │
│ │ 🔒 Fatigue Trend (PRO)  │    │ ← Premium-locked section
│ │ Upgrade to track fatigue │    │
│ └──────────────────────────┘    │
│                                 │
│ [Timer]    [Exercises]  [Stats] │
└─────────────────────────────────┘
```

### SCR-040: SettingsView

```
┌─────────────────────────────────┐
│ ◀ Settings                      │ ← Nav bar with back
│                                 │
│ TIMER                           │ ← Inset grouped list
│ ┌──────────────────────────┐    │
│ │ Interval     20 min   >  │    │ ← Free: visible but tap → PaywallView. Premium: stepper 10-30
│ │ Sound        [toggle]    │    │
│ └──────────────────────────┘    │
│                                 │
│ SCHEDULE (PRO)                  │
│ ┌──────────────────────────┐    │
│ │ Working Hours [toggle]   │    │ ← Premium-gated
│ │ Start         9:00 AM    │    │
│ │ End           6:00 PM    │    │
│ └──────────────────────────┘    │
│                                 │
│ ACCOUNT                         │
│ ┌──────────────────────────┐    │
│ │ 👑 Upgrade to Premium >  │    │ ← → PaywallView
│ │ Restore Purchases        │    │
│ └──────────────────────────┘    │
│                                 │
│ ABOUT                           │
│ ┌──────────────────────────┐    │
│ │ Privacy Policy        >  │    │
│ │ Terms of Service      >  │    │
│ │ Version           1.0.0  │    │
│ └──────────────────────────┘    │
│                                 │
└─────────────────────────────────┘
```

---

## 6. Onboarding Flow

Source: [ios-ux-design SKILL.md](ios-ux-design/SKILL.md) — Onboarding 8 rules (mau.md)
Source: PRD.md §6 — F-006 Onboarding Flow: 3-screen

### Flow Structure (3-Act)

```
Act 1: Problem                Act 2: Experience           Act 3: Paywall
┌─────────────┐              ┌──────────────┐            ┌──────────────┐
│  Welcome    │  ──Next──>   │ Notification │  ──Next──> │  PaywallView │
│  Screen     │              │ Permission   │            │  (soft)      │
│  (SCR-001)  │              │  (SCR-002)   │            │  (SCR-003)   │
└─────────────┘              └──────────────┘            └──────┬───┬───┘
                                                        Purchase│   │Later
                                                        ┌───────▼───▼───┐
                                                        │  MainTabView  │
                                                        └───────────────┘
```

### Screen 1: Welcome (SCR-001)

| Element | Content (en-US) | Content (ja) |
|---------|----------------|--------------|
| Image | Eye illustration / SF Symbol `eye.circle` | Same |
| Title | "Protect Your Eyes" | "目を守ろう" |
| Subtitle | "The 20-20-20 rule: Every 20 minutes, look 20 feet away for 20 seconds." | "20-20-20ルール：20分ごとに、6メートル先を20秒間見ましょう。" |
| CTA | "Get Started" | "はじめる" |

### Screen 2: Notification Permission (SCR-002)

| Element | Content (en-US) | Content (ja) |
|---------|----------------|--------------|
| Image | SF Symbol `bell.badge` | Same |
| Title | "Never Miss a Break" | "休憩を見逃さない" |
| Subtitle | "Get gentle reminders to rest your eyes throughout the day." | "1日を通して、目を休めるやさしいリマインダーを受け取りましょう。" |
| CTA | "Enable Notifications" | "通知を有効にする" |
| Action | `UNUserNotificationCenter.requestAuthorization` | Same |
| Skip | "Not Now" (small text below CTA) | "あとで" |

### Screen 3: PaywallView (SCR-003)

| Element | Detail |
|---------|--------|
| Presentation | Same PaywallView component used throughout app |
| Trigger | Auto-presented as final onboarding step |
| Dismissal | [Maybe Later] button — Rule 20: soft paywall, always dismissible |
| On Dismiss | Set `hasCompletedOnboarding = true`, navigate to MainTabView |
| On Purchase | Set `hasCompletedOnboarding = true`, navigate to MainTabView with premium |

### Onboarding Rules Applied

| Rule | Application |
|------|-------------|
| 3-act structure | Problem (welcome) → Experience (notification) → Paywall |
| Soft paywall | [Maybe Later] always visible — never force purchase |
| No login | Zero authentication — app works immediately |
| Permission timing | Notification request in Act 2 — after user understands value, before paywall |
| Page indicator | 3 dots at bottom showing progress |
| Skip option | "Not Now" on notification screen — never block progress |

---

## 7. Accessibility

Source: DESIGN_SYSTEM.md §7 — Contrast, Dynamic Type, VoiceOver labels
Source: [Apple HIG — Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility)

### Accessibility Identifiers (Maestro E2E)

All identifiers use `{screen}_{element}` convention. These identifiers are the contract between UX_SPEC, TEST_SPEC, and Maestro E2E flows.

#### Onboarding

| accessibilityIdentifier | Screen | Element |
|-------------------------|--------|---------|
| `onboarding_welcome_title` | SCR-001 | Welcome title label |
| `onboarding_welcome_cta` | SCR-001 | "Get Started" button |
| `onboarding_notification_title` | SCR-002 | Notification title label |
| `onboarding_notification_cta` | SCR-002 | "Enable Notifications" button |
| `onboarding_notification_skip` | SCR-002 | "Not Now" button |
| `onboarding_page_indicator` | SCR-001/002 | Page dots |

#### PaywallView

| accessibilityIdentifier | Screen | Element |
|-------------------------|--------|---------|
| `paywall_title` | SCR-003 | "Unlock EyeRest Premium" header |
| `paywall_plan_monthly` | SCR-003 | Monthly plan option |
| `paywall_plan_annual` | SCR-003 | Annual plan option |
| `paywall_continue` | SCR-003 | Purchase CTA button |
| `paywall_maybe_later` | SCR-003 | "Maybe Later" dismiss button |
| `paywall_restore` | SCR-003 | "Restore Purchases" link |
| `paywall_close` | SCR-003 | Close (X) button |

#### TimerView

| accessibilityIdentifier | Screen | Element |
|-------------------------|--------|---------|
| `timer_ring` | SCR-010 | Circular countdown ring |
| `timer_time_label` | SCR-010 | MM:SS countdown display |
| `timer_start_button` | SCR-010 | Start/Resume button |
| `timer_pause_button` | SCR-010 | Pause button |
| `timer_stop_button` | SCR-010 | Stop button |
| `timer_break_count` | SCR-010 | Break count badge |
| `timer_streak` | SCR-010 | Streak display |
| `timer_settings` | SCR-010 | Settings gear icon |

#### RestView

| accessibilityIdentifier | Screen | Element |
|-------------------------|--------|---------|
| `rest_countdown` | SCR-011 | 20-second countdown display |
| `rest_instruction` | SCR-011 | "Look 20 feet away" text |
| `rest_skip` | SCR-011 | Skip button |
| `rest_fatigue_picker` | SCR-011 | Fatigue level selector (premium) |
| `rest_complete` | SCR-011 | Completion checkmark |

#### ExerciseListView / Detail

| accessibilityIdentifier | Screen | Element |
|-------------------------|--------|---------|
| `exercise_list` | SCR-020 | Exercise grid/list container |
| `exercise_card_{id}` | SCR-020 | Individual exercise card (e.g. `exercise_card_palming`) |
| `exercise_premium_lock` | SCR-020 | Lock overlay on premium exercises |
| `exercise_detail_title` | SCR-021 | Exercise name |
| `exercise_detail_timer` | SCR-021 | Exercise countdown |
| `exercise_detail_step` | SCR-021 | Current step instruction |
| `exercise_detail_start` | SCR-021 | Start exercise button |

#### StatsView

| accessibilityIdentifier | Screen | Element |
|-------------------------|--------|---------|
| `stats_today_breaks` | SCR-030 | Today's break count stat card |
| `stats_streak` | SCR-030 | Streak stat card |
| `stats_fatigue_avg` | SCR-030 | Average fatigue stat card |
| `stats_weekly_chart` | SCR-030 | Weekly break chart |
| `stats_fatigue_chart` | SCR-030 | Fatigue trend chart (premium) |
| `stats_premium_lock` | SCR-030 | Premium lock overlay on fatigue section |

#### SettingsView

| accessibilityIdentifier | Screen | Element |
|-------------------------|--------|---------|
| `settings_interval` | SCR-040 | Timer interval stepper/picker |
| `settings_sound_toggle` | SCR-040 | Notification sound toggle |
| `settings_working_hours_toggle` | SCR-040 | Working hours toggle (premium) |
| `settings_working_hours_start` | SCR-040 | Start time picker |
| `settings_working_hours_end` | SCR-040 | End time picker |
| `settings_upgrade` | SCR-040 | "Upgrade to Premium" row |
| `settings_restore` | SCR-040 | "Restore Purchases" row |
| `settings_privacy` | SCR-040 | Privacy Policy link |
| `settings_version` | SCR-040 | Version number label |

---

## 8. Interaction Patterns

Source: [Apple HIG — Gestures](https://developer.apple.com/design/human-interface-guidelines/gestures) — Standard iOS gesture vocabulary

| Gesture | Screen | Action | Feedback |
|---------|--------|--------|----------|
| Tap | TimerView | Start/pause/stop timer | Haptic `.impact(.medium)` + button state change |
| Tap | ExerciseListView | Open exercise detail (free) or show paywall (premium) | Navigation push or sheet present |
| Tap | PaywallView | Select plan, purchase, dismiss | Plan toggle animation + haptic `.selection` |
| Tap | RestView | Skip rest (small target, intentional) | Dismiss modal |
| Swipe down | PaywallView | Dismiss paywall sheet | Standard sheet dismissal |
| Swipe left | ExerciseDetail | Navigate back | System back navigation |
| Long press | ExerciseCard | Preview exercise info (context menu) | Haptic + preview popup |
| Scroll | StatsView | Scroll through stats sections | Standard scroll physics |
| Swipe horizontal | OnboardingView | Navigate between pages | Page indicator update |

### State Transitions

| State | Visual | Timer Ring | CTA Button |
|-------|--------|------------|------------|
| Idle (not started) | Ring empty, gray | 0% progress | "Start" (brand.primary) |
| Running | Ring filling clockwise | Animated progress | "Pause" (secondary) |
| Paused | Ring frozen, pulse animation | Static progress | "Resume" (brand.primary) |
| Break time | Ring full, pulse + haptic | 100% → RestView modal | — |
| Rest active | Full-screen gradient | — | — (auto-countdown) |
| Rest complete | Checkmark animation | Reset to 0% | Auto-return to idle |

---

## 9. Localization Notes

Source: PRD.md §11 — en-US (primary), ja (secondary)
Source: product-plan.md §5 — Localization key-value pairs

### String Length Considerations

| Key | en-US | ja | Length Ratio | Layout Impact |
|-----|-------|----|-------------|---------------|
| timer_title | "Time until next break" | "次の休憩まで" | 1 : 0.5 | ja shorter — center alignment handles both |
| notification_title | "Time for an eye break!" | "目の休憩の時間です！" | 1 : 0.8 | Minimal impact |
| maybe_later | "Maybe Later" | "あとで" | 1 : 0.3 | ja much shorter — use `.frame(minWidth:)` |
| upgrade_premium | "Unlock Premium" | "プレミアムを解除" | 1 : 0.9 | Similar length |
| rest_instruction | "Look at something 20 feet away" | "6メートル先を見てください" | 1 : 0.7 | ja shorter |

### Layout Adaptation Rules

| Rule | Implementation |
|------|---------------|
| Text wrapping | `.lineLimit(nil)` on all labels — never truncate |
| Button width | `.frame(maxWidth: .infinity)` for full-width CTAs |
| Dynamic height | `ScrollView` wraps content — no fixed heights |
| Number formatting | `Locale`-aware formatters for timer, stats |
| Date formatting | `DateFormatter` with `.locale = .current` |
| Right-to-left | Not required (en-US, ja are LTR) |

### Locale-Specific Content

| Content | en-US | ja |
|---------|-------|----|
| Distance unit | "20 feet" | "6メートル" |
| Currency display | "$4.99/mo" | "$4.99/月" |
| Week start | Sunday | Monday (ISO 8601) |
| AM/PM | 12-hour display | 24-hour display preference |
