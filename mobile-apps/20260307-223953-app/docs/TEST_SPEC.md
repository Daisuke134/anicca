# Test Specification: FrostDip

## 1. Test Strategy

Source: [Martin Fowler — Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html) — "Unit tests at the base, integration in the middle, E2E at the top"
Source: [Apple XCTest](https://developer.apple.com/documentation/xctest) — "Use XCTest to write unit and performance tests"

### Test Pyramid

```
        ┌─────────┐
        │  E2E    │  10% — Maestro flows (6+ flows)
        │ Maestro │
       ┌┴─────────┴┐
       │ Integration │  20% — Service ↔ Service
       │   Tests     │
      ┌┴─────────────┴┐
      │   Unit Tests    │  70% — Models, Services, ViewModels
      │   (30+ tests)   │
      └─────────────────┘
```

| Layer | Framework | Target | Coverage Goal |
|-------|-----------|--------|---------------|
| Unit | XCTest | FrostDipTests | 80%+ line coverage |
| Integration | XCTest | FrostDipTests | Key flows covered |
| E2E | Maestro | maestro/ | 6+ critical flows |

---

## 2. Unit Tests

Source: ARCHITECTURE.md §5-6, PRD.md §6 Feature IDs

### Model Tests

| Test Name | Target | What It Verifies | Feature |
|-----------|--------|-----------------|---------|
| `testPlungeSessionInit` | PlungeSession | Default values on init (id, date, heartRates=[], isContrastSession=false) | F-003 |
| `testPlungeSessionWithTemperature` | PlungeSession | Optional waterTemperature stored correctly | F-003 |
| `testPlungeSessionWithNotes` | PlungeSession | Notes string stored and retrievable | F-003 |
| `testPlungeSessionHeartRateAggregation` | PlungeSession | heartRateAvg/Max computed from heartRates array | F-007 |
| `testPlungeProtocolInit` | PlungeProtocol | Default values (rounds=1, restTime=0, isDefault=false) | F-005 |
| `testPlungeProtocolBeginnerDefaults` | PlungeProtocol | Beginner: prepTime=30s, coldTime=120s | F-005 |
| `testPlungeProtocolCustom` | PlungeProtocol | Custom protocol with rounds>1 and restTime>0 | F-009 |
| `testUserPreferencesDefaults` | UserPreferences | Default temperatureUnit=.celsius, notificationsEnabled=false | F-014 |
| `testTemperatureUnitToggle` | UserPreferences | Switch between .celsius and .fahrenheit | F-014 |
| `testExperienceLevelCodable` | ExperienceLevel | Encode/decode all 3 levels | F-006 |

### Service Tests

| Test Name | Target | What It Verifies | Feature |
|-----------|--------|-----------------|---------|
| `testTimerStartAndTick` | TimerService | onTick called every second, timeRemaining decrements | F-001 |
| `testTimerPauseAndResume` | TimerService | Pause stops ticking, resume continues from same point | F-001 |
| `testTimerStop` | TimerService | Stop resets timer, no further ticks | F-001 |
| `testTimerCompletion` | TimerService | onComplete called when countdown reaches 0 | F-001 |
| `testBreathingPrepPhases` | TimerService | Phases cycle: inhale→hold→exhale, correct durations | F-002 |
| `testBreathingPrepCompletion` | TimerService | onComplete called after all breathing rounds | F-002 |
| `testHealthKitAvailability` | HealthKitService | isAvailable returns Bool based on HKHealthStore | F-007 |
| `testHealthKitStopReturnsAggregates` | HealthKitService (Mock) | stopHeartRateMonitoring returns avg, max, samples array | F-007 |
| `testSubscriptionServicePremiumCheck` | SubscriptionService (Mock) | isPremium reflects entitlement status | F-013 |
| `testSubscriptionFetchOfferings` | SubscriptionService (Mock) | fetchOfferings returns packages array | F-013 |
| `testSubscriptionPurchaseSuccess` | SubscriptionService (Mock) | purchase returns true, isPremium updated | F-013 |
| `testSubscriptionRestorePurchases` | SubscriptionService (Mock) | restorePurchases updates isPremium | F-013 |
| `testNotificationPermissionRequest` | NotificationService | requestPermission returns Bool | F-015 |
| `testNotificationScheduleReminder` | NotificationService | scheduleReminder creates UNNotificationRequest | F-015 |
| `testNotificationCancelAll` | NotificationService | cancelAll removes all pending notifications | F-015 |

### ViewModel Tests

| Test Name | Target | What It Verifies | Feature |
|-----------|--------|-----------------|---------|
| `testTimerViewModelStartTransition` | TimerViewModel | State changes idle→running, timer starts | F-001 |
| `testTimerViewModelPauseResume` | TimerViewModel | State changes running→paused→running | F-001 |
| `testTimerViewModelSessionCreation` | TimerViewModel | On completion, PlungeSession created with correct duration | F-003 |
| `testTimerViewModelHRIntegration` | TimerViewModel | HR monitoring starts on timer start (premium), stops on complete | F-007 |
| `testHistoryViewModel7DayFilter` | HistoryViewModel | Non-premium: only sessions from last 7 days returned | F-004 |
| `testHistoryViewModelUnlimited` | HistoryViewModel | Premium: all sessions returned | F-008 |
| `testHistoryViewModelSortOrder` | HistoryViewModel | Sessions sorted by date descending | F-004 |
| `testProgressViewModelChartData` | ProgressViewModel | Duration data grouped by week, correct averages | F-011 |
| `testProgressViewModelEmptyState` | ProgressViewModel | No sessions → empty chart data, zero totals | F-011 |
| `testPaywallViewModelFetchPlans` | PaywallViewModel | Offerings loaded, monthly + annual available | F-013 |
| `testPaywallViewModelPurchaseFlow` | PaywallViewModel | Purchase success → isPremium true | F-013 |
| `testPaywallViewModelRestore` | PaywallViewModel | Restore → isPremium updated | F-013 |
| `testOnboardingViewModelStepProgression` | OnboardingViewModel | Steps advance 1→2→3→4 in order | F-006 |
| `testOnboardingViewModelExperienceSave` | OnboardingViewModel | Selected experience level saved to UserDefaults | F-006 |
| `testSettingsViewModelTempUnitToggle` | SettingsViewModel | Toggle updates UserDefaults and publishes change | F-014 |

### Streak Logic Tests

| Test Name | Target | What It Verifies | Feature |
|-----------|--------|-----------------|---------|
| `testStreakIncrementOnNewDay` | Streak Logic | Session today after session yesterday → streak + 1 | F-010 |
| `testStreakResetOnMissedDay` | Streak Logic | Session today, no session yesterday or day before → streak = 1 | F-010 |
| `testStreakFreezePreservesStreak` | Streak Logic | Missed day + freeze available → streak maintained | F-010 |
| `testStreakFreezeOncePerWeek` | Streak Logic | Second freeze in same week → rejected, streak broken | F-010 |
| `testStreakLongestUpdated` | Streak Logic | current > longest → longest updated | F-010 |

**Total: 40 unit tests**

---

## 3. Integration Tests

Source: ARCHITECTURE.md §6 Services, IMPLEMENTATION_GUIDE.md §4-5

| Test Name | Services Involved | What It Verifies | Feature |
|-----------|------------------|-----------------|---------|
| `testTimerCompletionCreatesSession` | TimerService → SwiftData | Timer complete → PlungeSession persisted in ModelContext | F-001 + F-003 |
| `testTimerWithHRSavesToSession` | TimerService + HealthKitService → SwiftData | HR samples collected during timer, saved to session.heartRates | F-001 + F-007 |
| `testSubscriptionGatesHistory` | SubscriptionService → HistoryViewModel | Free: 7-day. Purchase premium: unlimited. Restore: unlimited | F-004 + F-008 + F-013 |
| `testOnboardingCompletesToMainApp` | OnboardingViewModel → UserDefaults | Onboarding final step → has_completed_onboarding = true → TabView shown | F-006 |
| `testProtocolSelectionAffectsTimer` | PlungeProtocol → TimerViewModel | Select protocol → timer duration matches protocol.coldTime | F-005 + F-001 |
| `testContrastTherapyRounds` | TimerService → TimerViewModel | Contrast mode cycles cold→rest→cold for configured rounds | F-012 |
| `testNotificationScheduleOnPreferenceChange` | NotificationService → SettingsViewModel | Enable notifications + set time → notification scheduled | F-014 + F-015 |
| `testStreakUpdateOnSessionSave` | SwiftData → Streak Logic → UserDefaults | New session → streak recalculated → UserDefaults updated | F-003 + F-010 |

---

## 4. E2E Tests (Maestro)

Source: UX_SPEC.md §7 accessibilityIdentifiers
Source: [Maestro Documentation](https://maestro.mobile.dev/) — "Use id: selectors for reliable element identification"

### Flow Files

| File | Scenario | Key Assertions | Tag |
|------|----------|---------------|-----|
| `maestro/onboarding.yaml` | Complete onboarding flow: welcome → experience → notifications → paywall → maybe later | `onboarding_get_started` visible, `onboarding_experience_beginner` tappable, `paywall_maybe_later` dismisses to main app | `smokeTest` |
| `maestro/timer_basic.yaml` | Start timer → wait 5s → stop → save session | `timer_start` → `timer_view` shows countdown → `timer_stop` → `session_summary_save` | `smokeTest` |
| `maestro/settings.yaml` | Open settings → toggle temp unit → verify change | `settings_view` visible, `settings_temp_unit` toggle, verify label updates | — |
| `maestro/payment_monthly.yaml` | Open paywall → select monthly → attempt purchase | `paywall_plan_monthly` tappable, `paywall_cta` triggers purchase flow | — |
| `maestro/payment_annual.yaml` | Open paywall → select annual → attempt purchase | `paywall_plan_annual` tappable, `paywall_cta` triggers purchase flow | — |
| `maestro/payment_failure.yaml` | Open paywall → attempt purchase → handle error | `paywall_cta` tap → error alert displayed | — |
| `maestro/history_browse.yaml` | Skip onboarding → start timer → stop → save → tap History tab → verify session card | `timer_start`, `timer_stop`, `session_summary_save`, `tab_history`, `history_view` visible, `session_card` contains duration text | — |

### Maestro Flow Template

```yaml
# maestro/onboarding.yaml
appId: com.aniccafactory.frostdip
tags:
  - smokeTest
---
- clearState
- launchApp
- assertVisible:
    id: "onboarding_get_started"
- tapOn:
    id: "onboarding_get_started"
- assertVisible:
    id: "onboarding_experience_beginner"
- tapOn:
    id: "onboarding_experience_beginner"
- tapOn:
    id: "onboarding_continue"
- assertVisible:
    id: "onboarding_skip_notifications"
- tapOn:
    id: "onboarding_skip_notifications"
- assertVisible:
    id: "paywall_view"
- assertVisible:
    id: "paywall_maybe_later"
- tapOn:
    id: "paywall_maybe_later"
- assertVisible:
    id: "timer_view"
- takeScreenshot: "onboarding_complete"
```

```yaml
# maestro/timer_basic.yaml
appId: com.aniccafactory.frostdip
tags:
  - smokeTest
---
- clearState
- launchApp
# Skip onboarding first
- tapOn:
    id: "onboarding_get_started"
- tapOn:
    id: "onboarding_experience_beginner"
- tapOn:
    id: "onboarding_continue"
- tapOn:
    id: "onboarding_skip_notifications"
- tapOn:
    id: "paywall_maybe_later"
# Now on timer screen
- assertVisible:
    id: "timer_view"
- tapOn:
    id: "timer_start"
- wait: 5000
- tapOn:
    id: "timer_stop"
- assertVisible:
    id: "session_summary_view"
- tapOn:
    id: "session_summary_save"
- takeScreenshot: "timer_session_saved"
```

```yaml
# maestro/history_browse.yaml
appId: com.aniccafactory.frostdip
---
- clearState
- launchApp
# Skip onboarding
- tapOn:
    id: "onboarding_get_started"
- tapOn:
    id: "onboarding_experience_beginner"
- tapOn:
    id: "onboarding_continue"
- tapOn:
    id: "onboarding_skip_notifications"
- tapOn:
    id: "paywall_maybe_later"
# Complete a short timer session
- assertVisible:
    id: "timer_view"
- tapOn:
    id: "timer_start"
- wait: 3000
- tapOn:
    id: "timer_stop"
- assertVisible:
    id: "session_summary_view"
- tapOn:
    id: "session_summary_save"
# Navigate to History tab
- tapOn:
    id: "tab_history"
- assertVisible:
    id: "history_view"
- assertVisible:
    id: "session_card"
- takeScreenshot: "history_browse_complete"
```

### E2E Requirements

| Requirement | Implementation |
|-------------|---------------|
| All flows use `id:` selectors | No `point:` selectors — UX_SPEC §7 IDs |
| All flows have `clearState` | First command in every flow |
| All flows have `takeScreenshot` | Last command (evidence for quality gate) |
| `smokeTest` tag on 2+ flows | onboarding.yaml + timer_basic.yaml |

---

## 5. Greenlight Checks

Source: CLAUDE.md Rules 17, 20, 20b, 21

### Automated Rule Checks

| Check | Command | Expected | Rule |
|-------|---------|----------|------|
| No analytics SDK | `grep -rE "Mixpanel\|Analytics\|Firebase" FrostDip/ --include="*.swift" \| grep -v "Tests/" \| wc -l` | 0 | Rule 17 |
| No RevenueCatUI | `grep -r "RevenueCatUI" FrostDip/ --include="*.swift" \| wc -l` | 0 | Rule 20 |
| No ATT framework | `grep -rE "ATTrackingManager\|requestTrackingAuthorization\|AppTrackingTransparency" FrostDip/ --include="*.swift" \| wc -l` | 0 | Rule 20b |
| No AI APIs | `grep -rE "OpenAI\|Anthropic\|GoogleGenerativeAI\|FoundationModels" FrostDip/ --include="*.swift" \| wc -l` | 0 | Rule 21 |
| No hardcoded API keys | `grep -rE "appl_[a-zA-Z0-9]+" FrostDip/ --include="*.swift" \| grep -v "PLACEHOLDER" \| wc -l` | 0 | Security |
| PaywallView has Maybe Later | `grep -r "Maybe Later\|maybe_later" FrostDip/ --include="*.swift" \| wc -l` | >= 1 | Rule 20 |
| PrivacyInfo.xcprivacy exists | `test -f FrostDip/Resources/PrivacyInfo.xcprivacy && echo PASS` | PASS | Privacy |
| No Mock in production code | `grep -rw "class Mock" FrostDip/ --include="*.swift" \| grep -v "Tests/" \| wc -l` | 0 | Quality |

### Greenlight Full Command

```bash
greenlight preflight FrostDipios/
# Expected: CRITICAL = 0
```

---

## 6. Performance Targets

Source: [Apple — App Launch Time](https://developer.apple.com/documentation/xcode/reducing-your-app-s-launch-time) — "Apps should launch in under 400ms"

| Metric | Target | Measurement |
|--------|--------|-------------|
| Cold launch | < 1.5s | Xcode Instruments — App Launch template |
| Warm launch | < 0.5s | Xcode Instruments |
| Memory (idle) | < 50MB | Xcode Memory Gauge |
| Memory (timer active + HR) | < 80MB | Xcode Memory Gauge |
| Timer accuracy | ±0.1s over 5min | Unit test: compare elapsed vs expected |
| SwiftData query (100 sessions) | < 100ms | Unit test: measure block |
| Battery impact (30min session) | < 5% | Manual test with battery logging |
| Frame rate (timer animation) | 60fps | Xcode Core Animation instrument |

---

## 7. Test Commands

| Task | Command |
|------|---------|
| Run all unit + integration tests | `cd FrostDipios && fastlane test` |
| Run specific test | `cd FrostDipios && fastlane test` (filter via Xcode scheme or use `scan(only_testing:)` in Fastfile) |
| Run Maestro smoke tests | `maestro test maestro/ --tags smokeTest` |
| Run all Maestro E2E | `maestro test maestro/` |
| Greenlight preflight | `greenlight preflight FrostDipios/` |
| Coverage report | `cd FrostDipios && fastlane test` (coverage output in Xcode) |
