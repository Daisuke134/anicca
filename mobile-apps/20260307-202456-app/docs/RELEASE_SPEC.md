# Release Specification: EyeRest

## 1. Pre-Submission Checklist

Source: [Apple App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) — Pre-submission requirements
Source: CLAUDE.md — Greenlight preflight, quality gates

| # | Gate | Command | Pass Criteria |
|---|------|---------|--------------|
| 1 | Build succeeds | `cd EyeRestios && fastlane build` | 0 errors, 0 warnings |
| 2 | Unit tests pass | `cd EyeRestios && fastlane test` | 0 failures |
| 3 | E2E tests pass | `maestro test maestro/` | All 6 flows pass |
| 4 | Greenlight preflight | `greenlight preflight EyeRestios` | CRITICAL = 0 |
| 5 | Screenshots captured | `find screenshots/ -name '*.png' \| wc -l` | >= 8 (4 en-US + 4 ja) |
| 6 | Metadata synced | `asc app-store-version-localizations list --version-id $VER_ID` | en-US + ja both present |
| 7 | Build valid in ASC | `asc builds list --app $APP_ID --sort -uploadedDate --limit 1` | processingState = VALID |
| 8 | Subscriptions ready | `asc subscriptions list --group $GROUP_ID` | 2 products, state = READY_TO_SUBMIT |
| 9 | Privacy manifest | `find EyeRestios -name 'PrivacyInfo.xcprivacy' \| wc -l` | >= 1 |

---

## 2. App Store Metadata

Source: PRD.md §14 — App Store Metadata (SSOT)

### en-US

| Field | Value |
|-------|-------|
| app_name | EyeRest |
| subtitle | Rest Your Eyes, Protect Your Vision |
| keywords | eye care,20-20-20,eye strain relief,eye break,digital eye strain,eye exercise,screen break timer,eye health |
| promotional_text | The 20-20-20 eye care timer that actually works. No login. Reliable background reminders. Guided eye exercises. |
| description | EyeRest helps you follow the 20-20-20 rule recommended by the American Optometric Association: every 20 minutes, look at something 20 feet away for 20 seconds. Unlike other eye care apps, EyeRest works reliably in the background — no login required, no ads, no account creation. Just open and go. FREE FEATURES: - 20-20-20 timer with reliable background notifications - Guided 20-second eye rest countdown - Daily break completion tracking - Palming eye exercise demo PREMIUM FEATURES ($4.99/mo or $29.99/yr): - Custom timer intervals (10-30 minutes) - 8 guided eye exercises (palming, figure-8, near-far focus, blink drill, and more) - Eye fatigue tracking with weekly charts - Working hours schedule (timer pauses after work) - Weekly eye health insights dashboard Whether you're a developer, designer, student, or anyone who spends hours on screens — EyeRest is the simplest way to protect your eyes every day. |
| privacy_policy_url | https://daisuke134.github.io/anicca-products/eyerest/privacy-policy |
| support_url | https://daisuke134.github.io/anicca-products/eyerest/support |
| marketing_url | https://daisuke134.github.io/anicca-products/eyerest |

### ja

| Field | Value |
|-------|-------|
| app_name | EyeRest |
| subtitle | 目を休めて、視力を守る |
| keywords | アイケア,20-20-20,眼精疲労,目の休憩,デジタルアイストレイン,目の体操,スクリーンブレイク,目の健康 |
| promotional_text | 20-20-20ルールに基づくアイケアタイマー。ログイン不要。バックグラウンドで確実に通知。目の体操付き。 |
| description | EyeRestはアメリカ検眼協会が推奨する20-20-20ルールを実践するためのアプリです。20分ごとに6メートル先を20秒間見ることで、デジタルアイストレインを予防します。他のアイケアアプリと違い、EyeRestはバックグラウンドで確実に動作します。ログイン不要、広告なし、アカウント作成不要。開いてすぐ使えます。無料機能: - 20-20-20タイマー（バックグラウンド通知対応） - ガイド付き20秒アイレスト - 1日の休憩回数トラッキング - パーミング体操デモ プレミアム機能（$4.99/月 または $29.99/年）: - カスタムタイマー間隔（10-30分） - 8種類のガイド付き目の体操 - 眼精疲労トラッキング（週間チャート） - 勤務時間スケジュール設定 - 週間アイヘルスインサイト エンジニア、デザイナー、学生、長時間画面を見るすべての方に — EyeRestは毎日の目の健康を守る最もシンプルな方法です。 |
| privacy_policy_url | https://daisuke134.github.io/anicca-products/eyerest/privacy-policy |
| support_url | https://daisuke134.github.io/anicca-products/eyerest/support |
| marketing_url | https://daisuke134.github.io/anicca-products/eyerest |

---

## 3. Screenshots

Source: [Apple App Store Screenshot Specifications](https://developer.apple.com/help/app-store-connect/reference/screenshot-specifications)

### Device Requirements

| Device | Display Size | Resolution | Required |
|--------|-------------|-----------|----------|
| iPhone 16 Pro Max | 6.9" | 1320 x 2868 | Yes |
| iPhone 16 Pro | 6.3" | 1206 x 2622 | Optional (auto-scaled) |
| iPhone SE (3rd gen) | 4.7" | 750 x 1334 | Optional |

### Screenshot Plan (4 per locale)

| # | Screen | Content | Caption (en-US) | Caption (ja) |
|---|--------|---------|----------------|-------------|
| 1 | TimerView | Timer running, 15:42 remaining, 3 breaks today | "Reliable 20-20-20 Timer" | "確実な20-20-20タイマー" |
| 2 | RestView | 20-second countdown with gradient animation | "Guided Eye Rest" | "ガイド付きアイレスト" |
| 3 | ExerciseListView | 8 exercises grid, palming unlocked | "8 Eye Exercises" | "8種類の目の体操" |
| 4 | StatsView | Weekly chart with 5-day streak | "Track Your Progress" | "進捗をトラッキング" |

### Capture Commands

```bash
# Using AXe + asc screenshots capture
export ASC_BYPASS_KEYCHAIN=true

# en-US
asc screenshots capture --bundle-id com.aniccafactory.eyerest \
  --udid $SIMULATOR_UDID --output-dir screenshots/en-US --output json

# ja (with locale override)
asc screenshots capture --bundle-id com.aniccafactory.eyerest \
  --udid $SIMULATOR_UDID --output-dir screenshots/ja --output json
```

### Upload Commands

```bash
# Get version and localization IDs
VER_ID=$(asc versions list --app $APP_ID --output json | jq -r '.[0].id')
LOC_EN=$(asc app-store-version-localizations list --version-id $VER_ID --output json | jq -r '.[] | select(.attributes.locale=="en-US") | .id')
LOC_JA=$(asc app-store-version-localizations list --version-id $VER_ID --output json | jq -r '.[] | select(.attributes.locale=="ja") | .id')

# Upload
asc screenshots upload --version-localization $LOC_EN --path screenshots/en-US --device-type IPHONE_67
asc screenshots upload --version-localization $LOC_JA --path screenshots/ja --device-type IPHONE_67
```

---

## 4. Privacy

Source: PRD.md §10 — Privacy & Compliance
Source: ARCHITECTURE.md §11 — PrivacyInfo.xcprivacy

### PrivacyInfo.xcprivacy

| Key | Value |
|-----|-------|
| NSPrivacyTracking | false |
| NSPrivacyTrackingDomains | [] (empty) |
| NSPrivacyCollectedDataTypes | [] (empty — no data collection) |
| NSPrivacyAccessedAPITypes | UserDefaults (CA92.1) — app functionality |

### App Privacy Responses (ASC Web)

| Question | Answer | Reason |
|----------|--------|--------|
| Do you collect data? | No | All data stored locally via SwiftData |
| Do you track users? | No | Rule 20b: no ATT, no tracking |
| Do you use third-party SDKs that collect data? | RevenueCat (purchase data only) | RevenueCat processes subscription transactions — Apple standard |
| Do you share data with third parties? | No | No data sharing |
| Do you link data to user identity? | No | No login, no accounts |

### Info.plist Privacy Keys

| Key | Value | Reason |
|-----|-------|--------|
| ITSAppUsesNonExemptEncryption | NO | No custom encryption — HTTPS only via RevenueCat |
| NSUserTrackingUsageDescription | NOT PRESENT | Rule 20b: ATT prohibited |

---

## 5. Build & Archive

Source: IMPLEMENTATION_GUIDE.md §8 — Build & Run
Source: CLAUDE.md — "Fastlane必須: xcodebuild直接実行禁止"

### Build Pipeline

```bash
# 1. Unlock keychain
source ~/.config/mobileapp-builder/.env
security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db

# 2. Run tests
cd EyeRestios && fastlane test

# 3. Archive
cd EyeRestios && fastlane archive

# 4. Upload to ASC
cd EyeRestios && fastlane upload
```

### Signing Configuration

| Item | Value |
|------|-------|
| Team ID | From .env: `$TEAM_ID` |
| Provisioning | Automatic (Xcode Managed) |
| Export Method | app-store |
| Bundle ID | com.aniccafactory.eyerest |

---

## 6. TestFlight

Source: [Apple TestFlight Documentation](https://developer.apple.com/testflight/)

### Beta Test Plan

| Phase | Testers | Duration | Focus |
|-------|---------|----------|-------|
| Internal | 1 (developer) | 1 day | Build stability, critical flows |
| External (if needed) | Up to 5 | 3 days | Subscription flow, background timer |

### TestFlight Setup Commands

```bash
export ASC_BYPASS_KEYCHAIN=true

# Get latest build
BUILD_ID=$(asc builds list --app $APP_ID --sort -uploadedDate --limit 1 --output json | jq -r '.[0].id')

# Add build to beta group
asc builds add-groups --build $BUILD_ID --group $GROUP_ID

# Add tester
asc testflight beta-testers add --app $APP_ID --email "$TESTER_EMAIL" --group "$GROUP_NAME"

# Invite tester
asc testflight beta-testers invite --app $APP_ID --email "$TESTER_EMAIL"
```

---

## 7. Submission

Source: [Apple App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)

### Review Information

| Field | Value |
|-------|-------|
| Contact First Name | Daisuke |
| Contact Last Name | From .env |
| Contact Phone | From .env |
| Contact Email | From .env |
| Demo Account Required | No — app works without login |
| Notes for Reviewer | "EyeRest is a timer-based eye care app. No login is required. To test the timer, open the app and tap Start. The timer will count down from 20 minutes. To test premium features, use the sandbox account. The paywall can be accessed via Settings > Upgrade to Premium." |

### Compliance Answers

| Question | Answer |
|----------|--------|
| Export Compliance | No — uses standard HTTPS only (via RevenueCat SDK) |
| Content Rights | Does not use third-party content |
| Advertising Identifier (IDFA) | No — Rule 20b: no ATT |

---

## 8. Review Notes

Source: [Apple Review Guidelines 3.1.1](https://developer.apple.com/app-store/review/guidelines/#in-app-purchase) — Subscription review requirements

### Key Points for Reviewer

| Topic | Detail |
|-------|--------|
| AI Usage | No AI features, no AI APIs, no machine learning. All content is static and curated. |
| Subscription Management | Uses RevenueCat SDK for subscription management. Users can manage subscriptions via iOS Settings > Subscriptions (standard Apple flow). |
| Offline Operation | App works fully offline. Timer and exercises require no network. Network used only for RevenueCat subscription verification. |
| Background Operation | Uses BGAppRefreshTaskRequest for timer reminders when app is backgrounded. Registered in Info.plist BGTaskSchedulerPermittedIdentifiers. |
| Data Storage | All user data stored locally via SwiftData. No cloud sync. No user accounts. |
| Notifications | Local notifications only via UNUserNotificationCenter. No remote/push notification server. |

---

## 9. Age Rating

Source: [Apple Age Rating Questionnaire](https://developer.apple.com/help/app-store-connect/reference/age-ratings)

All 22 items set to NONE — EyeRest is a health utility with no objectionable content.

| # | Category | Rating |
|---|----------|--------|
| 1 | Cartoon or Fantasy Violence | NONE |
| 2 | Realistic Violence | NONE |
| 3 | Prolonged Graphic or Sadistic Realistic Violence | NONE |
| 4 | Profanity or Crude Humor | NONE |
| 5 | Mature/Suggestive Themes | NONE |
| 6 | Horror/Fear Themes | NONE |
| 7 | Medical/Treatment Information | NONE |
| 8 | Alcohol, Tobacco, or Drug Use or References | NONE |
| 9 | Simulated Gambling | NONE |
| 10 | Sexual Content or Nudity | NONE |
| 11 | Graphic Sexual Content and Nudity | NONE |
| 12 | Unrestricted Web Access | NONE |
| 13 | Gambling with Real Currency | NONE |
| 14 | Contests | NONE |
| 15 | Frequent/Intense Cartoon or Fantasy Violence | NONE |
| 16 | Frequent/Intense Realistic Violence | NONE |
| 17 | Frequent/Intense Sexual Content or Nudity | NONE |
| 18 | Frequent/Intense Profanity or Crude Humor | NONE |
| 19 | Frequent/Intense Mature/Suggestive Themes | NONE |
| 20 | Frequent/Intense Horror/Fear Themes | NONE |
| 21 | Frequent/Intense Medical/Treatment Information | NONE |
| 22 | Frequent/Intense Alcohol, Tobacco, or Drug Use or References | NONE |

**Result: 4+ (Rated 4+)**

---

## 10. Hotfix Protocol

Source: CLAUDE.md — Branch strategy: dev → main → release/x.x.x

### Hotfix Flow

```
1. Branch: release/1.0.x from release/1.0.0
2. Fix: Apply minimal fix
3. Test: fastlane test + maestro test
4. Bump: 1.0.0 → 1.0.1
5. Archive: fastlane archive
6. Upload: fastlane upload
7. Submit: asc review submissions-create
8. Cherry-pick: Fix → dev branch
```

### Version Bump Rules

| Change Type | Bump | Example |
|-------------|------|---------|
| Crash fix | Patch | 1.0.0 → 1.0.1 |
| UI fix | Patch | 1.0.1 → 1.0.2 |
| New feature | Minor | 1.0.2 → 1.1.0 |
| Breaking change | Major | 1.1.0 → 2.0.0 |

---

## 11. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | TBD | Initial release: 20-20-20 timer, 8 eye exercises, fatigue tracking, premium subscriptions ($4.99/mo, $29.99/yr), en-US + ja localization |
