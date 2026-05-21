# Implementation Guide: BreathStory

**Date:** 2026-03-04
**Version:** 1.0.0

---

## Overview

This guide provides the ordered task list for implementing BreathStory iOS app.
All implementation uses RevenueCat SDK (real SDK — no Mock).

Source: [RevenueCat iOS SDK Docs](https://docs.revenuecat.com/docs/ios)
Source: [Apple AVFoundation](https://developer.apple.com/documentation/avfoundation)

---

## Prerequisites

Before implementation:
1. US-005 must be complete (ASC app + IAP products + RevenueCat Offering configured)
2. RC_API_KEY available in `~/.config/mobileapp-builder/.env`
3. Xcode 15+ installed
4. SPM dependency on `RevenueCat` resolved

---

## Phase 1: Project Setup

### Task 1.1: Create Xcode Project

```bash
# Project name: BreathStory
# Bundle ID: com.anicca.breathstory
# Interface: SwiftUI
# Language: Swift
# Minimum Deployment: iOS 15.0
# Team: (from provisioning profile)
```

### Task 1.2: Directory Structure

Create all directories per ARCHITECTURE.md:
```
BreathStoryios/
├── App/
├── Views/
├── ViewModels/
├── Models/
├── Services/
└── Resources/Sounds/
```

### Task 1.3: Add RevenueCat via SPM

```
File → Add Package Dependencies
URL: https://github.com/RevenueCat/purchases-ios
Version: from 5.0.0
Target: BreathStory (main target ONLY — NOT RevenueCatUI)
```

**CRITICAL:** Add `RevenueCat` package only. Do NOT add `RevenueCatUI`.

### Task 1.4: Add PrivacyInfo.xcprivacy

Create `Resources/PrivacyInfo.xcprivacy`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSPrivacyAccessedAPITypes</key>
    <array>
        <dict>
            <key>NSPrivacyAccessedAPIType</key>
            <string>NSPrivacyAccessedAPICategoryUserDefaults</string>
            <key>NSPrivacyAccessedAPITypeReasons</key>
            <array>
                <string>CA92.1</string>
            </array>
        </dict>
    </array>
</dict>
</plist>
```

### Task 1.5: Info.plist

Add these keys:
```xml
<key>ITSAppUsesNonExemptEncryption</key>
<false/>
<key>NSMicrophoneUsageDescription</key>
<string>Not used</string>
```

Remove any `NSUserTrackingUsageDescription` — ATT is PROHIBITED.

---

## Phase 2: Models

### Task 2.1: Story.swift

```swift
struct Story: Identifiable {
    let id: String
    let title: String
    let world: StoryWorld
    let script: String           // Full narration text
    let soundFile: String        // e.g. "forest_ambient"
    let breathingPattern: BreathingPattern
    let durationMinutes: Int
    let isPremium: Bool
}

enum StoryWorld: String {
    case forest, ocean, cityRain, space, mountain
}
```

### Task 2.2: BreathingPattern.swift

```swift
struct BreathingPattern {
    let inhaleDuration: Double
    let holdDuration: Double      // 0 if no hold
    let exhaleDuration: Double
    let name: String              // e.g. "Box Breathing"
}
```

### Task 2.3: Session.swift

```swift
struct Session: Codable {
    let storyId: String
    let completedAt: Date
    let durationSeconds: Int
}
```

---

## Phase 3: Services

### Task 3.1: SubscriptionService.swift (RevenueCat — REAL SDK)

```swift
import RevenueCat

class SubscriptionService: ObservableObject {
    @Published var isPremium: Bool = false
    @Published var offerings: Offerings? = nil

    static let shared = SubscriptionService()

    func configure(apiKey: String) {
        Purchases.configure(withAPIKey: apiKey)
        Purchases.shared.getCustomerInfo { [weak self] info, error in
            self?.isPremium = info?.entitlements["premium"]?.isActive == true
        }
    }

    func fetchOfferings() async throws -> Offerings {
        return try await Purchases.shared.offerings()
    }

    func purchase(package: Package) async throws -> CustomerInfo {
        let result = try await Purchases.shared.purchase(package: package)
        self.isPremium = result.customerInfo.entitlements["premium"]?.isActive == true
        return result.customerInfo
    }

    func restore() async throws {
        let info = try await Purchases.shared.restorePurchases()
        self.isPremium = info.entitlements["premium"]?.isActive == true
    }
}
```

**CRITICAL:**
- Import `RevenueCat` — NOT `RevenueCatUI`
- Use `Purchases.shared.purchase(package:)` — NOT `PaywallView()`
- Entitlement identifier: `"premium"`

### Task 3.2: AudioService.swift

```swift
import AVFoundation

class AudioService: ObservableObject {
    private var speechSynthesizer = AVSpeechSynthesizer()
    private var backgroundPlayer: AVPlayer?

    func startSoundscape(fileName: String) {
        guard let url = Bundle.main.url(forResource: fileName, withExtension: "mp3") else { return }
        backgroundPlayer = AVPlayer(url: url)
        backgroundPlayer?.volume = 0.4
        backgroundPlayer?.play()
        // Loop soundscape
        NotificationCenter.default.addObserver(forName: .AVPlayerItemDidPlayToEndTime,
                                               object: backgroundPlayer?.currentItem,
                                               queue: .main) { [weak self] _ in
            self?.backgroundPlayer?.seek(to: .zero)
            self?.backgroundPlayer?.play()
        }
    }

    func startNarration(text: String) {
        let utterance = AVSpeechUtterance(string: text)
        utterance.rate = 0.48
        utterance.pitchMultiplier = 0.9
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
        speechSynthesizer.speak(utterance)
    }

    func stop() {
        speechSynthesizer.stopSpeaking(at: .immediate)
        backgroundPlayer?.pause()
        backgroundPlayer = nil
    }
}
```

### Task 3.3: StreakService.swift

```swift
class StreakService {
    static let shared = StreakService()
    private let defaults = UserDefaults.standard

    var currentStreak: Int { defaults.integer(forKey: "streak_count") }
    private var lastSessionDate: Date? {
        return defaults.object(forKey: "last_session_date") as? Date
    }

    func recordSession() {
        let today = Calendar.current.startOfDay(for: Date())
        if let last = lastSessionDate, Calendar.current.isDateInYesterday(last) {
            defaults.set(currentStreak + 1, forKey: "streak_count")
        } else if lastSessionDate == nil || !Calendar.current.isDateInToday(lastSessionDate!) {
            defaults.set(1, forKey: "streak_count")
        }
        defaults.set(Date(), forKey: "last_session_date")
    }
}
```

---

## Phase 4: ViewModels

### Task 4.1: LibraryViewModel.swift

- Loads `StoryLibrary.allStories`
- Exposes `isPremium` from `SubscriptionService.shared`
- Determines which stories are locked

### Task 4.2: PlayerViewModel.swift

- Manages play/pause/stop state
- Drives breathing animation timer
- Calls `AudioService.startSoundscape()` + `AudioService.startNarration()`
- Calls `StreakService.recordSession()` on completion

### Task 4.3: SubscriptionViewModel.swift

- Wraps `SubscriptionService.shared`
- Fetches `Offerings` for paywall display
- Exposes `selectedPackage` (default: Annual)

---

## Phase 5: Views

### Task 5.1: BreathStoryApp.swift (@main)

```swift
import SwiftUI
import RevenueCat

@main
struct BreathStoryApp: App {
    init() {
        // RevenueCat configure — REAL SDK
        Purchases.configure(withAPIKey: ProcessInfo.processInfo.environment["RC_API_KEY"]
                           ?? "REPLACE_WITH_RC_API_KEY")
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
```

### Task 5.2: HomeView.swift

- 2-column `LazyVGrid` of story cards
- Lock overlay for premium stories on free tier
- Streak badge in nav bar
- Tap free story → `PlayerView`
- Tap locked story → `PaywallView` (sheet)

### Task 5.3: PlayerView.swift

- Full-screen ZStack
- Background gradient from story world
- `BreathingRingView` in center (animated Circle)
- Phase label ("INHALE" / "HOLD" / "EXHALE")
- Narration text preview (current line)
- Stop / Pause controls

### Task 5.4: PaywallView.swift (Custom SwiftUI — NO RevenueCatUI)

```swift
// Minimum required structure
struct PaywallView: View {
    @Environment(\.dismiss) var dismiss
    @StateObject var vm = SubscriptionViewModel()

    var body: some View {
        VStack {
            // Maybe Later — ALWAYS VISIBLE
            HStack {
                Spacer()
                Button("Maybe Later") { dismiss() }
                    .foregroundColor(.secondary)
            }
            .padding()

            // ... (package selection, CTA, legal links)

            Button("Start 7-Day Free Trial") {
                Task { try? await vm.purchase() }
            }

            Button("Restore Purchases") {
                Task { try? await vm.restore() }
            }

            // Privacy + Terms links ALWAYS VISIBLE
        }
    }
}
```

**CRITICAL:** `dismiss()` MUST work. [Maybe Later] cannot be disabled.

### Task 5.5: OnboardingView.swift

3-screen TabView with `PageTabViewStyle`.

### Task 5.6: SettingsView.swift

Simple List with streak, subscription status, restore, legal links.

---

## Phase 6: Story Content

### Task 6.1: StoryLibrary.swift

Define all 5 stories as static `[Story]` array with:
- Full script text (~300–400 words each)
- Breathing pattern timings per DESIGN_SYSTEM.md
- Sound file names
- Premium flags (stories 4+5 are premium)

### Task 6.2: Audio Assets

Place in `Resources/Sounds/`:
- `forest_ambient.mp3` — birds, gentle wind
- `ocean_ambient.mp3` — waves
- `cityrain_ambient.mp3` — rain, distant café
- `space_ambient.mp3` — deep space tone
- `mountain_ambient.mp3` — wind, silence

Use royalty-free audio from freesound.org or generate with GarageBand.

---

## Build Verification

```bash
# From project root
cd BreathStoryios

# Build check
xcodebuild -scheme BreathStory -destination 'platform=iOS Simulator,name=iPhone 15' build

# Verify no Mock code
grep -r 'Mock' --include='*.swift' . | grep -v 'Tests/' | grep -v '.build/' | wc -l
# Expected: 0

# Verify RevenueCat imported (real SDK)
grep -r 'import RevenueCat' --include='*.swift' . | wc -l
# Expected: > 0

# Verify RevenueCatUI NOT imported (prohibited)
grep -r 'import RevenueCatUI' --include='*.swift' . | wc -l
# Expected: 0
```

---

## RevenueCat API Key Placement

**Never hardcode API key in source.** Load from environment or build configuration:

```swift
// Option A: Build setting (INFOPLIST_KEY)
// Option B: xcconfig file (gitignored)
// Option C: Environment variable in scheme (local dev only)
```

For CI/CD: inject via environment variable `RC_API_KEY`.
