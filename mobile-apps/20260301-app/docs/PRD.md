# Product Requirements Document: AffirmFlow

**Version:** 1.0.0
**Date:** 2026-03-01
**Status:** APPROVED
**App Name:** AffirmFlow
**Bundle ID:** com.anicca.affirmflow

---

## 1. Executive Summary

AffirmFlow is an AI-powered daily affirmation widget for iOS 26 that generates personalized affirmations using Apple's Foundation Models framework. All processing happens 100% on-device, ensuring user privacy while delivering a unique, personalized wellness experience.

| Attribute | Value |
|-----------|-------|
| **Platform** | iOS 26+ |
| **Category** | Health & Fitness |
| **Monetization** | Freemium Subscription |
| **Pricing** | $2.99/week or $29.99/year |
| **MVP Timeline** | 4 weeks |

---

## 2. Problem Statement

### Core Problem

Generic affirmation apps deliver the same pre-written content to all users, creating an impersonal experience that fails to resonate with individual needs and goals.

### Problem Dimensions

| Dimension | Description | Severity |
|-----------|-------------|----------|
| **Personalization Gap** | Existing apps use pre-written quote databases; no AI-powered personalization | 9/10 |
| **Privacy Concerns** | Cloud-based AI requires uploading personal thoughts/context | 8/10 |
| **Engagement Friction** | Users must open full app to get affirmations; breaks "3-second rule" | 7/10 |
| **Content Fatigue** | Same quotes repeat after using app for weeks | 7/10 |

### Problem Severity Score: 8/10

---

## 3. Features

### 3.1 P0 Features (Must-Have for MVP)

| Feature | Description | Acceptance Criteria |
|---------|-------------|---------------------|
| **F-001: Foundation Models Integration** | AI-powered affirmation generation using on-device model | Affirmations are unique, contextual, and generated in <2 seconds |
| **F-002: Focus Area Selection** | User selects up to 3 focus areas | 5 options: Confidence, Gratitude, Calm, Motivation, Self-Love |
| **F-003: Home Screen Widget** | Medium and Large widget with daily affirmation | Widget displays current affirmation with refresh button |
| **F-004: Basic App Shell** | Settings, history, about screens | Navigation works, settings persist |
| **F-005: Affirmation History** | View past affirmations | Last 30 affirmations stored and viewable |

### 3.2 P1 Features (Should-Have)

| Feature | Description | Acceptance Criteria |
|---------|-------------|---------------------|
| **F-006: Lock Screen Widget** | Small widget for quick glance | Displays shortened affirmation on lock screen |
| **F-007: Refresh Action** | Tap to generate new affirmation | Widget interactive button triggers new generation |
| **F-008: Favorites** | Save favorite affirmations | Heart icon saves, favorites view shows all saved |
| **F-009: Subscription Paywall** | RevenueCat integration | Free tier limited to 3/day, premium unlimited |

### 3.3 P2 Features (Nice-to-Have)

| Feature | Description | Acceptance Criteria |
|---------|-------------|---------------------|
| **F-010: Visual Themes** | 5 premium visual themes | Theme changes widget appearance |
| **F-011: Daily Reminder** | Push notification at set time | Notification links to widget/app |

### 3.4 Deferred Features (Not in v1.0)

| Feature | Reason for Deferral |
|---------|---------------------|
| Social Sharing | Adds complexity; not core value prop |
| Cloud Sync | Violates privacy-first principle |
| Voice Recording | ThinkUp's feature; avoid direct competition |
| Journaling | Scope creep; focus on widget-first |

---

## 4. User Stories

### US-001: First Launch & Onboarding

**As a** new user
**I want to** quickly set up my focus areas
**So that** I can start receiving personalized affirmations

**Acceptance Criteria:**
```gherkin
Given I launch the app for the first time
When the onboarding screen appears
Then I see a welcome message explaining the app's privacy-first AI
And I can select 1-3 focus areas from 5 options
And I can proceed to the main app

Given I complete onboarding
When I add the widget to my home screen
Then I see my first AI-generated affirmation
```

### US-002: View Daily Affirmation on Widget

**As a** user with the widget installed
**I want to** see a personalized affirmation on my home screen
**So that** I can start my day with positivity without opening the app

**Acceptance Criteria:**
```gherkin
Given I have the widget on my home screen
When I wake up and look at my phone
Then I see a new affirmation personalized to my focus areas
And the affirmation is different from yesterday

Given I want a new affirmation
When I tap the refresh button on the widget
Then a new affirmation is generated within 2 seconds
```

### US-003: Save Favorite Affirmations

**As a** user who resonates with an affirmation
**I want to** save it to my favorites
**So that** I can revisit it later

**Acceptance Criteria:**
```gherkin
Given I see an affirmation I love
When I tap the heart icon
Then the affirmation is saved to my favorites
And I receive haptic feedback

Given I want to review my favorites
When I open the app and tap Favorites
Then I see a list of all saved affirmations
And I can remove any from favorites
```

### US-004: Subscribe to Premium

**As a** free user hitting the daily limit
**I want to** upgrade to premium
**So that** I can get unlimited affirmations

**Acceptance Criteria:**
```gherkin
Given I am a free user
When I try to refresh after 3 affirmations today
Then I see the paywall with pricing options
And I can select weekly ($2.99) or annual ($29.99)
And I can restore previous purchases

Given I complete purchase
When I return to the app
Then my premium status is active
And I have unlimited affirmations
```

### US-005: View Affirmation History

**As a** user
**I want to** see past affirmations
**So that** I can reflect on my journey

**Acceptance Criteria:**
```gherkin
Given I open the app
When I tap on History
Then I see the last 30 affirmations
And each shows date and focus area
And I can tap any to save to favorites
```

### US-006: Change Focus Areas

**As a** user whose goals have changed
**I want to** update my focus areas
**So that** future affirmations are more relevant

**Acceptance Criteria:**
```gherkin
Given I open Settings
When I tap on Focus Areas
Then I see my current selections
And I can change to different areas (max 3)
And the next affirmation reflects the new focus
```

---

## 5. User Flows

### 5.1 Onboarding Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        ONBOARDING FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Welcome    │ -> │ Focus Areas  │ -> │  Widget      │       │
│  │   Screen     │    │  Selection   │    │  Tutorial    │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                   │               │
│         v                   v                   v               │
│  "AI affirmations    Select 1-3 areas:   "Add widget to        │
│   100% on-device"    [ ] Confidence       home screen"         │
│                      [ ] Gratitude       [Continue]             │
│  [Get Started]       [ ] Calm                                   │
│                      [ ] Motivation                             │
│                      [ ] Self-Love                              │
│                                                                 │
│                      [Continue]                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Widget Interaction Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     WIDGET INTERACTION FLOW                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────┐                                │
│  │      HOME SCREEN WIDGET     │                                │
│  │  ┌───────────────────────┐  │                                │
│  │  │ "You have the power   │  │                                │
│  │  │  to create positive   │  │                                │
│  │  │  change in your life" │  │                                │
│  │  │                       │  │                                │
│  │  │  ❤️ [Refresh] 🔄      │  │                                │
│  │  └───────────────────────┘  │                                │
│  └─────────────────────────────┘                                │
│              │                │                                 │
│              v                v                                 │
│         Tap Heart        Tap Refresh                            │
│              │                │                                 │
│              v                v                                 │
│    Save to Favorites   Generate New (if limit OK)               │
│    Haptic feedback     or Show Paywall                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Premium Conversion Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                   PREMIUM CONVERSION FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Free User                                                      │
│      │                                                          │
│      v                                                          │
│  Hits 3/day limit                                               │
│      │                                                          │
│      v                                                          │
│  ┌──────────────────────────────────┐                           │
│  │           PAYWALL                │                           │
│  │                                  │                           │
│  │  "Unlock Unlimited Affirmations" │                           │
│  │                                  │                           │
│  │  ✓ Unlimited daily affirmations  │                           │
│  │  ✓ Lock screen widget            │                           │
│  │  ✓ 5 visual themes               │                           │
│  │  ✓ All focus areas               │                           │
│  │                                  │                           │
│  │  [$2.99/week]  [$29.99/year]     │                           │
│  │                                  │                           │
│  │  [Restore Purchases]             │                           │
│  │  [Maybe Later]                   │                           │
│  └──────────────────────────────────┘                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Data Requirements

### 6.1 User Data

| Field | Type | Storage | Notes |
|-------|------|---------|-------|
| `focusAreas` | [String] | UserDefaults | Max 3 areas |
| `onboardingComplete` | Bool | UserDefaults | First launch flag |
| `premiumStatus` | Bool | RevenueCat | Subscription state |
| `dailyRefreshCount` | Int | UserDefaults | Reset at midnight |

### 6.2 Affirmation Data

| Field | Type | Storage | Notes |
|-------|------|---------|-------|
| `id` | UUID | SwiftData | Unique identifier |
| `content` | String | SwiftData | Affirmation text |
| `focusArea` | String | SwiftData | Primary focus area |
| `createdAt` | Date | SwiftData | Generation timestamp |
| `isFavorite` | Bool | SwiftData | Favorite flag |

---

## 7. Non-Functional Requirements

### 7.1 Performance

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| App launch time | < 1.5 seconds | Cold start to main screen |
| Affirmation generation | < 2 seconds | Foundation Models inference |
| Widget refresh | < 3 seconds | Background update |
| Memory usage | < 100 MB | Peak during inference |

### 7.2 Privacy & Security

| Requirement | Implementation |
|-------------|----------------|
| On-device processing | Foundation Models (no network calls for AI) |
| No user tracking | No analytics on affirmation content |
| Data persistence | Local SwiftData only |
| Privacy manifest | NSPrivacyAccessedAPITypeReasons declared |

### 7.3 Accessibility

| Requirement | Implementation |
|-------------|----------------|
| VoiceOver | All UI elements labeled |
| Dynamic Type | Text scales with system settings |
| Reduce Motion | Animations respect system preference |
| Color Contrast | Minimum 4.5:1 ratio |

---

## 8. Technical Constraints

| Constraint | Rationale |
|------------|-----------|
| iOS 26+ only | Foundation Models requires iOS 26 |
| iPhone primary | Widget-first design optimized for phone |
| No cloud backend | Privacy-first architecture |
| SwiftUI only | Modern UI framework |
| WidgetKit | Apple's widget framework |

---

## 9. Success Metrics

### 9.1 Launch Readiness

| Metric | Target |
|--------|--------|
| P0 features complete | 100% |
| Crash-free sessions | > 99.5% |
| App Store review | First submission approval |

### 9.2 User Success

| Metric | Target | Timeline |
|--------|--------|----------|
| Widget adoption | > 60% of users | Week 2 |
| Day 1 retention | > 40% | Week 4 |
| Day 7 retention | > 25% | Week 4 |
| App Store rating | > 4.5 stars | Month 1 |

### 9.3 Business Success

| Metric | Target | Timeline |
|--------|--------|----------|
| Free-to-trial | > 15% | Month 1 |
| Trial-to-paid | > 50% | Month 1 |
| Overall conversion | > 3% | Month 3 |
| Year 1 revenue | $50K-100K | Year 1 |

---

## 10. Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: Core MVP** | Week 1-2 | F-001 to F-005 (P0 features) |
| **Phase 2: Complete MVP** | Week 3-4 | F-006 to F-009 (P1 features) |
| **Phase 3: Polish** | Week 5 | Bug fixes, optimization |
| **Phase 4: TestFlight** | Week 5-6 | Beta testing |
| **Phase 5: Submission** | Week 6 | App Store submission |

---

## 11. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Foundation Models API changes | Low | High | Minimal API surface; follow Apple best practices |
| iOS 26 adoption slow | Medium | Medium | Target early adopters; market grows Q4 2026 |
| Low conversion rate | Medium | Medium | A/B test paywall; optimize free tier |
| App Store rejection | Low | High | Follow guidelines; privacy manifest ready |

---

## 12. Appendix

### 12.1 Focus Area Definitions

| Focus Area | Description | Example Affirmations |
|------------|-------------|----------------------|
| **Confidence** | Self-belief and capability | "I trust my abilities to handle challenges" |
| **Gratitude** | Appreciation and thankfulness | "I am grateful for the abundance in my life" |
| **Calm** | Peace and relaxation | "I release tension and embrace tranquility" |
| **Motivation** | Drive and energy | "I am motivated to achieve my goals" |
| **Self-Love** | Self-acceptance | "I deserve love and respect, starting with myself" |

### 12.2 Competitive Positioning

| Competitor | Their Approach | AffirmFlow Advantage |
|------------|----------------|----------------------|
| ThinkUp | Voice recording | AI-generated, no effort required |
| I Am | Pre-written library | Dynamic, never repeats |
| Innertune | Audio playback | Widget-first, glanceable |

---

**Document End**
