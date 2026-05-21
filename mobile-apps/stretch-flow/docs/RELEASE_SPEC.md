# Release Specification: DeskStretch

> **Version:** 1.0 | **Date:** 2026-03-05

---

## 1. Pre-Submission Checklist

| # | Gate | Command | Pass Criteria |
|---|------|---------|--------------|
| 1 | **Greenlight scan** | `cd DeskStretchios && /tmp/greenlight/build/greenlight preflight .` | CRITICAL = 0 |
| 2 | **PrivacyInfo.xcprivacy** | Verify file exists with CA92.1 | NSPrivacyAccessedAPICategoryUserDefaults declared |
| 3 | **Unit tests** | `cd DeskStretchios && fastlane test` | All PASS |
| 4 | **E2E tests** | `maestro test maestro/` | All PASS |
| 5 | **Localization** | Verify .xcstrings has en + ja | All strings translated |
| 6 | **No analytics SDK** | `grep -r "Mixpanel\|Analytics\|Firebase" DeskStretchios/` | 0 results |
| 7 | **No RevenueCatUI** | `grep -r "RevenueCatUI\|PaywallView()" DeskStretchios/` | 0 RevenueCatUI imports |
| 8 | **No ATT** | `grep -r "ATTrackingManager\|requestTrackingAuthorization" DeskStretchios/` | 0 results |
| 9 | **RevenueCat real SDK** | Verify `Purchases.shared.purchase(package:)` in code | Real SDK calls present |

---

## 2. App Store Metadata

### App Information

| Field | en-US | ja |
|-------|-------|----|
| **App Name** | DeskStretch | DeskStretch |
| **Subtitle** (30 chars max) | Desk Stretching & Break Timer | デスクストレッチ＆休憩タイマー |
| **Keywords** (100 chars max) | desk stretching,break timer,back pain,office workout,stretch reminder,posture,neck pain,desk exercises | デスクストレッチ,休憩タイマー,腰痛,肩こり,首の痛み,オフィスワークアウト,姿勢改善,ストレッチ |

### Description (4000 chars max)

**en-US:**

```
Back pain from sitting all day? DeskStretch is your smart desk stretching companion that reminds you to take breaks and guides you through personalized stretch routines based on your pain areas.

WHY DESKSTRETCH?

80% of office workers experience muscle pain from prolonged sitting. You know you should stretch, but you forget, don't know what to do, or can't make it a habit. DeskStretch solves all three problems.

HOW IT WORKS

1. Tell us where it hurts — neck, back, shoulders, or wrists
2. Set your break timer — 30, 45, 60, or 90 minutes
3. Get a gentle reminder when it's time to move
4. Follow a personalized 1-3 minute guided stretch session
5. Track your progress and build a streak

KEY FEATURES

- Pain-Targeted Stretches — Your routines adapt to your pain areas and stretch history
- Smart Break Timer — Configurable intervals with gentle notifications during work hours only
- 24+ Guided Exercises — Desk-friendly stretches for neck, back, shoulders, and wrists
- Progress Tracking — Daily count, streak tracking, and weekly history
- 100% Private — No data collection, no tracking, everything stays on your device

DESIGNED FOR DESK WORKERS

Unlike generic workout apps, every exercise in DeskStretch can be done at your desk or chair. No floor space, no equipment, no sweat. Just 1-3 minutes of targeted relief.

PREMIUM ($3.99/mo or $29.99/yr)

- Unlimited daily stretches
- Pain-targeted routines
- All pain area categories
- Custom break schedules
- Full progress tracking

Free users get 3 stretches per day with the basic timer.

Start your 7-day free trial today. Your back will thank you.
```

**ja:**

```
座りっぱなしの腰痛、もう終わりにしませんか？DeskStretchは、あなたの痛みエリアに合わせたストレッチを提案する、デスクワーカー専用の休憩タイマーアプリです。

なぜDeskStretch？

オフィスワーカーの80%以上が筋骨格系の痛みを経験しています。ストレッチすべきだと分かっていても、忘れる・何をすればいいか分からない・続かない。DeskStretchはこの3つの問題を解決します。

使い方

1. 痛い場所を教えてください — 首・腰・肩・手首
2. 休憩タイマーを設定 — 30・45・60・90分
3. 時間が来たら優しく通知
4. 1-3分のパーソナライズされたストレッチを実行
5. 進捗を記録して継続

主な特徴

・痛みエリア特化 — 痛みエリアと履歴に基づいてルーティンを最適化
・スマート休憩タイマー — 勤務時間内のみ通知する設定可能なインターバル
・24以上のガイド付きエクササイズ — 首・腰・肩・手首のデスク向けストレッチ
・進捗トラッキング — 日別カウント、連続日数、週間履歴
・100%プライベート — データ収集なし、トラッキングなし、全てデバイス上で完結

プレミアム（月額$3.99 / 年額$29.99）

7日間の無料トライアルを今すぐ開始。あなたの腰が喜びます。
```

### Promotional Text (170 chars max)

| Language | Text |
|----------|------|
| en-US | Smart desk stretches personalized to your pain areas. Take a 1-minute break, relieve your back pain. Start your free trial today. |
| ja | あなたの痛みに合わせたデスクストレッチを提案。1分の休憩で腰痛を軽減。今すぐ無料トライアル。 |

---

## 3. Screenshots

### Required Devices

| Device | Display Size | Required |
|--------|-------------|----------|
| iPhone 16 Pro Max | 6.9" | Yes (primary) |
| iPhone 16 Pro | 6.3" | Yes |
| iPhone SE (3rd gen) | 4.7" | Yes |
| iPad Pro 13" (M4) | 13" | No (iPhone only for MVP) |

### Screenshot List (5 screens)

| # | Screen | Headline | Subheadline |
|---|--------|---------|-------------|
| 1 | Timer (main screen) | Your Break Timer | Smart reminders to stretch throughout the day |
| 2 | Pain area selection | Targets Your Pain | Pain-targeted routines for neck, back, shoulders, wrists |
| 3 | Stretch session | Guided Stretches | 1-3 minute desk-friendly exercise sessions |
| 4 | Progress dashboard | Track Your Streak | Daily progress and consistency tracking |
| 5 | Paywall | Start Free Trial | 7 days free. $3.99/mo or $29.99/yr |

**Screenshot Pipeline:**
```bash
# Capture (via asc-shots-pipeline skill)
asc screenshots capture --bundle-id com.aniccafactory.deskstretch --udid SIMULATOR_UDID --output-dir screenshots/raw --output json

# Frame (via Koubou — Rule 18: screenshot-creator skill forbidden)
asc screenshots frame --input-dir screenshots/raw --output-dir screenshots/framed --device-type IPHONE_67

# Upload
asc screenshots upload --version-localization LOC_ID --path screenshots/framed --device-type IPHONE_67
```

---

## 4. Privacy

### Privacy Manifest (PrivacyInfo.xcprivacy)

| API Category | Reason Code | Justification |
|-------------|------------|--------------|
| NSPrivacyAccessedAPICategoryUserDefaults | CA92.1 | App preferences, progress data, onboarding state |

### App Privacy (App Store Connect)

| Question | Answer |
|----------|--------|
| Does your app collect data? | No |
| Data types collected | None |
| Tracking | No (ATT not used — Rule 20b) |
| Third-party SDKs | RevenueCat (subscription management only) |

### Privacy Policy URL

| Language | URL |
|----------|-----|
| en-US | `https://aniccafactory.com/deskstretch/privacy` |
| ja | `https://aniccafactory.com/deskstretch/privacy` (same, bilingual) |

---

## 5. Build & Archive

```bash
# Set version
cd DeskStretchios && FASTLANE_SKIP_UPDATE_CHECK=1 fastlane set_version version:1.0.0

# Secrets
source ~/.config/mobileapp-builder/.env
security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db
export ASC_BYPASS_KEYCHAIN=true

# Build + Upload + Submit
cd DeskStretchios && FASTLANE_SKIP_UPDATE_CHECK=1 FASTLANE_OPT_OUT_CRASH_REPORTING=1 fastlane full_release
```

---

## 6. TestFlight

### Beta Test Plan

| Phase | Duration | Testers | Focus |
|-------|----------|---------|-------|
| Internal | 2 days | 1-2 (developer) | Core functionality, crash-free |
| External | 5 days | 10-20 | Usability, subscription flow, localization |

### TestFlight Setup

```bash
# Get latest build
asc builds list --app APP_ID --sort -uploadedDate --limit 1

# Add to group
asc builds add-groups --build BUILD_ID --group GROUP_ID

# Add testers
asc testflight beta-testers add --app APP_ID --email tester@example.com --group "Beta Testers"

# Invite
asc testflight beta-testers invite --app APP_ID --email tester@example.com
```

---

## 7. Submission

### Review Information

| Field | Value |
|-------|-------|
| Contact | Developer email |
| Demo Account | Not needed (no login) |
| Notes for Reviewer | "This app provides personalized desk stretching routines based on user-selected pain areas. Stretch content is curated and stored locally. Subscription is managed via RevenueCat SDK." |

### Submission Commands

```bash
# Create submission
asc review submissions-create --app APP_ID

# Add build
asc review items-add --submission SUBMISSION_ID --build BUILD_ID

# Submit for review
asc review submissions-submit --submission SUBMISSION_ID
```

### Compliance

| Question | Answer |
|----------|--------|
| Export compliance (ECCN) | No encryption beyond HTTPS |
| Content rights | All content is original |
| IDFA usage | No (ATT not used) |
| Made for Kids | No |

---

## 8. Post-Approval

| Action | When | How |
|--------|------|-----|
| Release to App Store | Immediately after approval | Manual release or auto-release |
| Slack notification | On approval | US-007 Slack report via webhook |
| TestFlight link | After build processed | `asc testflight builds get-link` |

---

## 9. Monitoring (Post-Launch)

| Metric | Tool | Alert Threshold |
|--------|------|----------------|
| Crash rate | Xcode Organizer | > 1% |
| App Store rating | ASC | < 4.0 |
| Subscription conversion | RevenueCat Dashboard | < 10% trial-to-paid |
| App Store reviews | ASC | Negative trend |

---

## 10. Hotfix Protocol

```bash
# If critical bug found post-release:
# 1. Fix on dev branch
# 2. Bump patch version
cd DeskStretchios && fastlane set_version version:1.0.1

# 3. Run all tests
fastlane test
maestro test maestro/

# 4. Build + Submit
fastlane full_release

# 5. Request expedited review if critical
```

---

## 11. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | TBD | Initial release — Timer, Library, Recommendations, Progress, Paywall |
