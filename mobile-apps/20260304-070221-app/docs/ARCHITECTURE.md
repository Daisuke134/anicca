# Architecture Specification: BreathStory

**Date:** 2026-03-04
**Version:** 1.0.0

---

## Overview

BreathStory is a fully offline, no-backend iOS app. All data is local. No network calls except RevenueCat SDK (subscription validation) and optional App Store receipt validation.

Source: Apple Human Interface Guidelines — [Local Data](https://developer.apple.com/design/human-interface-guidelines/privacy) — offline-first improves trust and performance.

---

## Layer Architecture

```
┌─────────────────────────────────────┐
│           Views (SwiftUI)           │
│  HomeView / PlayerView / Paywall    │
│  OnboardingView / SettingsView      │
├─────────────────────────────────────┤
│         ViewModels (ObservableObject)│
│  PlayerViewModel / LibraryViewModel │
│  SubscriptionViewModel              │
├─────────────────────────────────────┤
│           Services                  │
│  AudioService (AVSpeechSynthesizer) │
│  SubscriptionService (RevenueCat)   │
│  StreakService (UserDefaults)       │
├─────────────────────────────────────┤
│           Models                    │
│  Story / BreathingPattern / Session │
├─────────────────────────────────────┤
│          Resources                  │
│  Local .mp3 soundscapes             │
│  Story scripts (Swift strings)      │
└─────────────────────────────────────┘
```

---

## Directory Structure

```
BreathStoryios/
├── App/
│   ├── BreathStoryApp.swift          # @main, RevenueCat.configure()
│   └── AppDelegate.swift
├── Views/
│   ├── HomeView.swift                # Story grid
│   ├── PlayerView.swift              # Breathing player
│   ├── PaywallView.swift             # Custom soft paywall (NO RevenueCatUI)
│   ├── OnboardingView.swift          # 3-step onboarding
│   └── SettingsView.swift           # Restore, streak
├── ViewModels/
│   ├── PlayerViewModel.swift
│   ├── LibraryViewModel.swift
│   └── SubscriptionViewModel.swift
├── Models/
│   ├── Story.swift                   # Story struct
│   ├── BreathingPattern.swift        # Inhale/hold/exhale timings
│   └── Session.swift                # Completed session record
├── Services/
│   ├── AudioService.swift            # AVSpeechSynthesizer + AVPlayer
│   ├── SubscriptionService.swift     # RevenueCat wrapper
│   └── StreakService.swift           # UserDefaults-backed streak
└── Resources/
    ├── Sounds/
    │   ├── forest_ambient.mp3
    │   ├── ocean_ambient.mp3
    │   ├── cityrain_ambient.mp3
    │   ├── space_ambient.mp3
    │   └── mountain_ambient.mp3
    ├── PrivacyInfo.xcprivacy
    └── Info.plist
```

---

## Data Flow

```
User taps story
        ↓
LibraryViewModel checks isPremium (SubscriptionService)
        ↓
if free story: → PlayerViewModel.play(story)
if locked:     → PaywallView (soft, [Maybe Later] visible)
                        ↓
                 User subscribes → RevenueCat validates
                 OR taps Maybe Later → dismiss
        ↓
PlayerViewModel:
  1. AudioService.startSoundscape(story.soundFile)   [AVPlayer]
  2. AudioService.startNarration(story.script)       [AVSpeechSynthesizer]
  3. Start breathing animation timer (story.pattern)
        ↓
StreakService.recordSession() on completion
```

---

## RevenueCat Integration

| Key | Value |
|-----|-------|
| SDK | `RevenueCat` (SPM: `github.com/RevenueCat/purchases-ios`) |
| Configure | `BreathStoryApp.init()` — `Purchases.configure(withAPIKey:)` |
| Products | `com.anicca.breathstory.monthly`, `com.anicca.breathstory.annual` |
| Offering | `default` offering with `Monthly` + `Annual` packages |
| Paywall | Custom SwiftUI — `Purchases.shared.purchase(package:)` |

**CRITICAL:** RevenueCatUI is PROHIBITED. Use `Purchases.shared.purchase(package:)` directly.

```swift
// CORRECT
Purchases.shared.purchase(package: package) { transaction, info, error, cancelled in ... }

// PROHIBITED
PaywallView()  // from RevenueCatUI — DO NOT USE
```

---

## Key Technical Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| TTS | AVSpeechSynthesizer | Free, offline, no API key, built-in iOS |
| Audio | AVPlayer + local .mp3 | Offline, no streaming cost |
| Analytics | NONE | Mixpanel prohibited (CRITICAL rule) |
| Paywall | Custom SwiftUI | RevenueCatUI prohibited (CRITICAL rule) |
| Backend | NONE | MVP scope, offline-first |
| Database | UserDefaults | Streak + onboarding state only — no complex data |

---

## Dependencies (SPM)

```swift
// Package.swift dependencies
.package(url: "https://github.com/RevenueCat/purchases-ios", from: "5.0.0")
// NO other third-party dependencies
```

Source: [RevenueCat SPM Installation](https://docs.revenuecat.com/docs/installation#swift-package-manager)

---

## Privacy

- No analytics SDK
- No tracking
- No network requests (except RevenueCat receipt validation)
- `PrivacyInfo.xcprivacy` declares: `NSPrivacyAccessedAPICategoryUserDefaults` (CA92.1)
- `Info.plist` declares: `ITSAppUsesNonExemptEncryption = NO`
