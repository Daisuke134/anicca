# UI/UX Specification: AffirmFlow

**Version:** 1.0.0
**Date:** 2026-03-01
**Status:** APPROVED

---

## 1. Design Principles

| Principle | Description | Implementation |
|-----------|-------------|----------------|
| **Widget-First** | Primary experience is on home screen, not in app | Widget is hero, app is settings |
| **Glanceable** | Content readable in 3 seconds | Short affirmations, large typography |
| **Calming** | Visual design promotes tranquility | Soft colors, gentle gradients |
| **Privacy-Confident** | Design reinforces on-device messaging | Privacy badges, no cloud icons |
| **Minimal** | Remove unnecessary elements | Single purpose per screen |

---

## 2. Screen Inventory

| Screen | Priority | Purpose |
|--------|----------|---------|
| Onboarding: Welcome | P0 | First launch, value proposition |
| Onboarding: Focus Areas | P0 | Select personal focus |
| Onboarding: Widget Tutorial | P0 | Guide widget setup |
| Home | P0 | Current affirmation + actions |
| History | P0 | Past affirmations |
| Favorites | P1 | Saved affirmations |
| Settings | P0 | App preferences |
| Paywall | P1 | Premium conversion |
| Widget: Small | P1 | Lock screen glance |
| Widget: Medium | P0 | Home screen primary |
| Widget: Large | P0 | Home screen expanded |

---

## 3. Wireframes

### 3.1 Onboarding: Welcome

```
┌─────────────────────────────────────┐
│                                     │
│                                     │
│           ┌─────────┐               │
│           │  🧘‍♀️   │               │
│           │ (icon)  │               │
│           └─────────┘               │
│                                     │
│         AffirmFlow                  │
│                                     │
│    AI-powered affirmations          │
│    100% on your device              │
│                                     │
│   ┌─────────────────────────────┐   │
│   │  🔒 Your thoughts never     │   │
│   │     leave your phone        │   │
│   └─────────────────────────────┘   │
│                                     │
│                                     │
│                                     │
│   ┌─────────────────────────────┐   │
│   │        Get Started          │   │
│   └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

**Interactions:**
- Tap "Get Started" → Navigate to Focus Areas

**Accessibility:**
- VoiceOver: "AffirmFlow. AI-powered affirmations, 100% on your device. Your thoughts never leave your phone. Get Started button."
- Dynamic Type: Title scales to Accessibility sizes

---

### 3.2 Onboarding: Focus Areas

```
┌─────────────────────────────────────┐
│  ←                                  │
│                                     │
│    Choose Your Focus                │
│    Select up to 3 areas             │
│                                     │
│   ┌─────────────────────────────┐   │
│   │  ⭐ Confidence              │   │
│   │     Believe in yourself     │   │
│   └─────────────────────────────┘   │
│                                     │
│   ┌─────────────────────────────┐   │
│   │  ❤️ Gratitude          [✓] │   │
│   │     Appreciate life         │   │
│   └─────────────────────────────┘   │
│                                     │
│   ┌─────────────────────────────┐   │
│   │  🍃 Calm                [✓] │   │
│   │     Find inner peace        │   │
│   └─────────────────────────────┘   │
│                                     │
│   ┌─────────────────────────────┐   │
│   │  🔥 Motivation              │   │
│   │     Stay driven             │   │
│   └─────────────────────────────┘   │
│                                     │
│   ┌─────────────────────────────┐   │
│   │  💜 Self-Love               │   │
│   │     Accept yourself         │   │
│   └─────────────────────────────┘   │
│                                     │
│   ┌─────────────────────────────┐   │
│   │         Continue            │   │
│   └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

**Interactions:**
- Tap focus area → Toggle selection (max 3)
- Tap "Continue" → Navigate to Widget Tutorial (disabled if 0 selected)
- Haptic feedback on selection

**Accessibility:**
- Each area announced with name and description
- Selection state announced

---

### 3.3 Onboarding: Widget Tutorial

```
┌─────────────────────────────────────┐
│  ←                                  │
│                                     │
│    Add Your Widget                  │
│                                     │
│   ┌─────────────────────────────┐   │
│   │                             │   │
│   │   ┌─────────────────────┐   │   │
│   │   │   "You have the     │   │   │
│   │   │    power to create  │   │   │
│   │   │    positive change" │   │   │
│   │   │                     │   │   │
│   │   │    ❤️      🔄       │   │   │
│   │   └─────────────────────┘   │   │
│   │                             │   │
│   │   (Widget Preview)          │   │
│   └─────────────────────────────┘   │
│                                     │
│    1. Long press your home screen   │
│    2. Tap the + button              │
│    3. Search "AffirmFlow"           │
│    4. Add the widget                │
│                                     │
│   ┌─────────────────────────────┐   │
│   │     Done, Let's Go!         │   │
│   └─────────────────────────────┘   │
│                                     │
│         Skip for now                │
│                                     │
└─────────────────────────────────────┘
```

**Interactions:**
- "Done, Let's Go!" → Navigate to Home
- "Skip for now" → Navigate to Home

---

### 3.4 Home Screen

```
┌─────────────────────────────────────┐
│                            ⚙️       │
│                                     │
│                                     │
│   ┌─────────────────────────────┐   │
│   │                             │   │
│   │                             │   │
│   │    "I embrace each day      │   │
│   │     with confidence and     │   │
│   │     gratitude"              │   │
│   │                             │   │
│   │                             │   │
│   │                             │   │
│   │   🍃 Calm                   │   │
│   └─────────────────────────────┘   │
│                                     │
│        ❤️            🔄             │
│       Save        Refresh           │
│                                     │
│                                     │
│   ─────────────────────────────     │
│                                     │
│     📜 History    ⭐ Favorites      │
│                                     │
│                                     │
│      3 of 3 today (Free)            │
│      Upgrade for unlimited          │
│                                     │
└─────────────────────────────────────┘
```

**Interactions:**
- Tap ❤️ → Save to favorites (haptic feedback)
- Tap 🔄 → Generate new affirmation (or show paywall if limit)
- Tap ⚙️ → Navigate to Settings
- Tap History → Navigate to History
- Tap Favorites → Navigate to Favorites
- Tap "Upgrade" → Show Paywall

**States:**
- Loading: Shimmer effect on card
- Error: "Unable to generate. Tap to retry."
- Limit reached: Refresh button shows lock icon

---

### 3.5 History Screen

```
┌─────────────────────────────────────┐
│  ←       History                    │
│                                     │
│  Today                              │
│  ┌─────────────────────────────┐    │
│  │ "I embrace confidence..."   │    │
│  │ 🍃 Calm · 9:30 AM       ❤️  │    │
│  └─────────────────────────────┘    │
│  ┌─────────────────────────────┐    │
│  │ "I am grateful for..."      │    │
│  │ ❤️ Gratitude · 8:15 AM  ○   │    │
│  └─────────────────────────────┘    │
│                                     │
│  Yesterday                          │
│  ┌─────────────────────────────┐    │
│  │ "My inner peace guides..."  │    │
│  │ 🍃 Calm · 7:00 PM       ○   │    │
│  └─────────────────────────────┘    │
│                                     │
│  March 1, 2026                      │
│  ┌─────────────────────────────┐    │
│  │ "I trust my journey..."     │    │
│  │ ⭐ Confidence · 6:45 AM ○   │    │
│  └─────────────────────────────┘    │
│                                     │
│                                     │
└─────────────────────────────────────┘
```

**Interactions:**
- Tap ❤️/○ → Toggle favorite
- Tap row → Show full affirmation detail (optional)
- Pull to refresh → Load more history
- Swipe left → Delete option

---

### 3.6 Favorites Screen

```
┌─────────────────────────────────────┐
│  ←       Favorites                  │
│                                     │
│  ┌─────────────────────────────┐    │
│  │                             │    │
│  │  "I embrace each day with   │    │
│  │   confidence and gratitude" │    │
│  │                             │    │
│  │  🍃 Calm · March 1          │    │
│  └─────────────────────────────┘    │
│                                     │
│  ┌─────────────────────────────┐    │
│  │                             │    │
│  │  "I am worthy of love and   │    │
│  │   all good things"          │    │
│  │                             │    │
│  │  💜 Self-Love · Feb 28      │    │
│  └─────────────────────────────┘    │
│                                     │
│                                     │
│                                     │
│                                     │
│                                     │
│                                     │
│                                     │
└─────────────────────────────────────┘
```

**Empty State:**
```
┌─────────────────────────────────────┐
│  ←       Favorites                  │
│                                     │
│                                     │
│                                     │
│           ❤️                        │
│                                     │
│    No favorites yet                 │
│                                     │
│    Tap the heart on any             │
│    affirmation to save it           │
│                                     │
│                                     │
│                                     │
└─────────────────────────────────────┘
```

---

### 3.7 Settings Screen

```
┌─────────────────────────────────────┐
│  ←       Settings                   │
│                                     │
│  ACCOUNT                            │
│  ┌─────────────────────────────┐    │
│  │ ⭐ Premium              Free│    │
│  │    Unlock all features   >  │    │
│  └─────────────────────────────┘    │
│                                     │
│  PREFERENCES                        │
│  ┌─────────────────────────────┐    │
│  │ 🎯 Focus Areas              │    │
│  │    Gratitude, Calm       >  │    │
│  └─────────────────────────────┘    │
│  ┌─────────────────────────────┐    │
│  │ 🎨 Theme                    │    │
│  │    Default              >   │    │
│  └─────────────────────────────┘    │
│                                     │
│  SUPPORT                            │
│  ┌─────────────────────────────┐    │
│  │ 🔄 Restore Purchases        │    │
│  └─────────────────────────────┘    │
│  ┌─────────────────────────────┐    │
│  │ 📧 Contact Support          │    │
│  └─────────────────────────────┘    │
│  ┌─────────────────────────────┐    │
│  │ 📜 Privacy Policy           │    │
│  └─────────────────────────────┘    │
│  ┌─────────────────────────────┐    │
│  │ 📄 Terms of Service         │    │
│  └─────────────────────────────┘    │
│                                     │
│  Version 1.0.0                      │
│                                     │
└─────────────────────────────────────┘
```

---

### 3.8 Paywall Screen

```
┌─────────────────────────────────────┐
│                                  ✕  │
│                                     │
│          ⭐                         │
│                                     │
│    Unlock AffirmFlow Premium        │
│                                     │
│   ┌─────────────────────────────┐   │
│   │ ✓ Unlimited affirmations    │   │
│   │ ✓ Lock screen widget        │   │
│   │ ✓ 5 beautiful themes        │   │
│   │ ✓ All focus areas           │   │
│   └─────────────────────────────┘   │
│                                     │
│   ┌─────────────────────────────┐   │
│   │                             │   │
│   │    $29.99/year              │   │
│   │    Save 80%                 │   │
│   │                      ✓      │   │
│   └─────────────────────────────┘   │
│                                     │
│   ┌─────────────────────────────┐   │
│   │    $2.99/week               │   │
│   │                             │   │
│   └─────────────────────────────┘   │
│                                     │
│   ┌─────────────────────────────┐   │
│   │        Continue             │   │
│   └─────────────────────────────┘   │
│                                     │
│      Restore Purchases              │
│                                     │
│  Terms · Privacy · Cancel anytime   │
│                                     │
└─────────────────────────────────────┘
```

**Interactions:**
- Tap pricing option → Select
- Tap "Continue" → Process purchase
- Tap ✕ → Dismiss paywall
- Tap "Restore Purchases" → Restore

---

## 4. Widget Wireframes

### 4.1 Small Widget (Lock Screen)

```
┌─────────────────────┐
│                     │
│  "I embrace        │
│   confidence"       │
│                     │
│            🍃      │
└─────────────────────┘
```

**Specs:**
- Single line or two-line affirmation
- Focus area icon bottom-right
- Tap → Open app

---

### 4.2 Medium Widget

```
┌───────────────────────────────────────────┐
│                                           │
│     "I embrace each day with              │
│      confidence and gratitude"            │
│                                           │
│     🍃 Calm                               │
│                                           │
│              ❤️        🔄                 │
└───────────────────────────────────────────┘
```

**Specs:**
- Full affirmation text (up to 3 lines)
- Focus area with icon
- Save and Refresh buttons (App Intents)
- Tap buttons → Execute intent
- Tap elsewhere → Open app

---

### 4.3 Large Widget

```
┌───────────────────────────────────────────┐
│                                           │
│                                           │
│                                           │
│     "I embrace each day with              │
│      confidence and gratitude.            │
│      I am capable of achieving            │
│      my dreams."                          │
│                                           │
│                                           │
│                                           │
│     🍃 Calm · Today 9:30 AM               │
│                                           │
│              ❤️        🔄                 │
│                                           │
└───────────────────────────────────────────┘
```

**Specs:**
- Extended affirmation text (up to 5 lines)
- Focus area + timestamp
- Save and Refresh buttons
- More visual breathing room

---

## 5. User Flows

### 5.1 First Launch Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                        FIRST LAUNCH FLOW                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  App Launch                                                      │
│      │                                                           │
│      ▼                                                           │
│  Welcome Screen                                                  │
│      │                                                           │
│      ▼                                                           │
│  Focus Area Selection (select 1-3)                               │
│      │                                                           │
│      ▼                                                           │
│  Widget Tutorial                                                 │
│      │                                                           │
│      ├──> "Done, Let's Go!" ──> Home Screen                      │
│      │                                                           │
│      └──> "Skip for now" ──> Home Screen                         │
│                                                                  │
│  (Generate first affirmation automatically)                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Daily Usage Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                       DAILY USAGE FLOW                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User wakes up                                                   │
│      │                                                           │
│      ▼                                                           │
│  Sees widget on home/lock screen                                 │
│      │                                                           │
│      ├──> Reads affirmation ──> Day continues                    │
│      │                                                           │
│      ├──> Taps ❤️ ──> Saves to favorites ──> Haptic feedback     │
│      │                                                           │
│      └──> Taps 🔄 ──> New affirmation generated (if limit OK)    │
│                   │                                              │
│                   └──> Limit reached ──> Opens app ──> Paywall   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. Accessibility

### 6.1 VoiceOver Labels

| Element | Label |
|---------|-------|
| Save button | "Save to favorites" |
| Refresh button | "Generate new affirmation" |
| Focus area chip | "[Area] focus area" |
| Affirmation card | "[Full text]. [Focus area]." |
| Premium badge | "Premium subscription, active/inactive" |

### 6.2 Dynamic Type

| Element | Minimum | Maximum |
|---------|---------|---------|
| Affirmation text | Body | AccessibilityXXL |
| Focus area label | Footnote | AccessibilityL |
| Button labels | Callout | AccessibilityL |

### 6.3 Color Contrast

All text meets WCAG AA (4.5:1 minimum contrast ratio).

### 6.4 Reduce Motion

- Disable spring animations
- Use simple cross-fades
- No parallax effects

---

## 7. Interaction Patterns

### 7.1 Haptic Feedback

| Action | Feedback Type |
|--------|---------------|
| Save to favorites | Success (light) |
| Generate affirmation | Selection |
| Purchase complete | Success (heavy) |
| Error | Error |

### 7.2 Loading States

| Component | Loading State |
|-----------|---------------|
| Affirmation card | Shimmer placeholder |
| Refresh button | Spinning indicator |
| History list | Skeleton rows |

### 7.3 Empty States

| Screen | Empty State |
|--------|-------------|
| History | "Your journey begins here" |
| Favorites | "Tap ❤️ on any affirmation to save it" |

---

## 8. Navigation

### 8.1 Navigation Structure

```
┌──────────────────────────────────────────────────────────────────┐
│                     NAVIGATION STRUCTURE                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Onboarding (Modal, first launch only)                           │
│      │                                                           │
│      ▼                                                           │
│  Home (Root)                                                     │
│      │                                                           │
│      ├──> Settings (Push)                                        │
│      │       ├──> Focus Areas (Push)                             │
│      │       ├──> Theme (Push, Premium)                          │
│      │       └──> Privacy/Terms (Safari)                         │
│      │                                                           │
│      ├──> History (Push)                                         │
│      │                                                           │
│      ├──> Favorites (Push)                                       │
│      │                                                           │
│      └──> Paywall (Sheet)                                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 8.2 Navigation Style

| Transition | Style |
|------------|-------|
| Screen to screen | Push (NavigationStack) |
| Paywall | Sheet (detents: .large) |
| Onboarding | Full screen cover |

---

## 9. Animations

### 9.1 Animation Timings

| Animation | Duration | Curve |
|-----------|----------|-------|
| Screen transition | 0.3s | easeInOut |
| Card appearance | 0.25s | spring(0.8) |
| Button tap | 0.1s | easeOut |
| Favorite toggle | 0.2s | bouncy |

### 9.2 Affirmation Transition

When refreshing:
1. Current card fades out (0.15s)
2. Loading shimmer appears (0.1s)
3. New card fades in (0.2s)

---

## 10. Error States

### 10.1 Generation Failed

```
┌─────────────────────────────────────┐
│                                     │
│   ┌─────────────────────────────┐   │
│   │                             │   │
│   │         ⚠️                  │   │
│   │                             │   │
│   │   Unable to generate        │   │
│   │                             │   │
│   │   [Tap to retry]            │   │
│   │                             │   │
│   └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

### 10.2 No Network (for RevenueCat)

Show cached data, disable purchase buttons with explanation.

---

**Document End**
