# Release Specification: Chi Daily

**Version:** 1.0
**Date:** 2026-03-04
**App Name:** Chi Daily: TCM Wellness Coach
**Bundle ID:** com.aniccafactory.chidaily

---

## 1. App Store Metadata

### en-US

| Field | Value |
|-------|-------|
| **Name** | Chi Daily: TCM Wellness Coach |
| **Subtitle** | Daily Check-in, AI Guidance |
| **Keywords** | tcm wellness,chinese medicine,daily check-in,constitution,yin yang,qi gong,herbal,feng shui health,meridian,wellbeing |
| **Promotional Text** | Daily TCM wellness guidance — powered by on-device AI. Private. No cloud. |

**Description (en-US):**
```
Chi Daily is your personal Traditional Chinese Medicine wellness coach.

Every morning, answer 5 simple questions about your energy, sleep, digestion, emotions, and how your body feels. Chi Daily's on-device AI analyzes your responses using TCM constitutional principles and gives you personalized guidance for your food, movement, and rest — all without sending your data to the cloud.

WHAT YOU GET:
• Daily 5-question constitutional check-in (< 2 minutes)
• Personalized food, movement, and rest recommendations
• On-device AI powered by Apple's Foundation Models
• HealthKit integration for mood and energy tracking
• Check-in history (last 7 days)
• English and Japanese — dual-market from day 1

WHY TCM?
Traditional Chinese Medicine has been practiced for over 2,500 years. The "Chinese Baddie" wellness trend has brought TCM principles to millions of TikTok users. Chi Daily makes this ancient wisdom accessible as a daily habit.

PRIVACY FIRST:
Chi Daily uses Apple's Foundation Models framework — all AI inference runs on your device. No data is sent to any server for your wellness check-ins. No account required.

SUBSCRIPTION:
• 7-day free trial
• $4.99/month or $34.99/year (save 42%)
• Cancel anytime in Settings > Apple ID > Subscriptions

Terms of Use: https://aniccafactory.github.io/chidaily/terms
Privacy Policy: https://aniccafactory.github.io/chidaily/privacy
```

### ja

| Field | Value |
|-------|-------|
| **Name** | Chi Daily: TCM Wellness Coach |
| **Subtitle** | 毎日の体質チェック・AIアドバイス |
| **Keywords** | 中医学,漢方,体質チェック,毎日ウェルネス,中国医学,気功,陰陽,ウェルネスアプリ,体質診断,健康習慣 |

**Description (ja):**
```
Chi Dailyは、あなたのパーソナル中医学ウェルネスコーチです。

毎朝5つの質問に答えるだけで、体質に合った食事・運動・休息のアドバイスを受けられます。すべてデバイス上のAIが処理するため、データはクラウドに送られません。

【特徴】
• 毎日の5問体質チェックイン（2分以内）
• 食事・運動・休息のパーソナライズされたアドバイス
• Appleのオンデバイスai（Foundation Models）搭載
• HealthKit連携（気分とエネルギー記録）
• チェックイン履歴（直近7日分）
• 日本語・英語に対応

【なぜ中医学？】
漢方・中医学は2500年以上の歴史を持つ東洋医学の知恵です。Chi Dailyは毎日の習慣として中医学を取り入れるための最も簡単な方法です。

【プライバシー重視】
AppleのFoundation Modelsフレームワークを使用。AIはすべてデバイス上で動作。ウェルネスデータはサーバーに送信されません。アカウント不要。

【サブスクリプション】
• 7日間無料体験
• $4.99/月 または $34.99/年（42%お得）
• いつでもキャンセル可能
```

---

## 2. Asset Requirements

### App Icon

| Asset | Size | Notes |
|-------|------|-------|
| App Icon | 1024×1024px PNG | No alpha channel; Xcode generates all sizes |
| Design concept | Yin-yang + leaf motif on cream background | See DESIGN_SYSTEM.md |

### Screenshots

**Required sizes:**
- iPhone 6.9" (iPhone 16 Pro Max): 1320×2868px — REQUIRED
- iPhone 6.5" (iPhone 14 Pro Max): 1284×2778px — REQUIRED
- iPad 13" (M4): 2064×2752px — OPTIONAL for MVP

**Screenshot content (5 per locale):**

| # | Screen | Caption (en) | Caption (ja) |
|---|--------|-------------|-------------|
| 1 | Home (after check-in, Earth constitution) | "Know your TCM type — every day" | "毎日、あなたの体質を知る" |
| 2 | Check-in Q1 (energy question) | "5 questions. Under 2 minutes." | "5問。2分以内。" |
| 3 | Result (3 recommendation cards) | "Personalized food, movement & rest" | "食事・運動・休息のパーソナルアドバイス" |
| 4 | History view (3 entries) | "Track your pattern over time" | "7日間の体質の変化を追跡" |
| 5 | Constitution intro (onboarding S2) | "On-device AI. Total privacy." | "オンデバイスAI。完全プライベート。" |

**Screenshot tool:** Koubou (`asc screenshots frame`) — per CLAUDE.md Rule #18.

---

## 3. Privacy Manifest (PrivacyInfo.xcprivacy)

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
    <key>NSPrivacyCollectedDataTypes</key>
    <array/>
    <key>NSPrivacyTrackingDomains</key>
    <array/>
    <key>NSPrivacyTracking</key>
    <false/>
</dict>
</plist>
```

**App Privacy Declarations (ASC Web — human must complete):**
- Data Not Linked to You: Health & Fitness (HealthKit data, stays on device)
- No data collected or sent to developer

---

## 4. Info.plist Required Keys

```xml
<!-- Encryption: required for App Store -->
<key>ITSAppUsesNonExemptEncryption</key>
<false/>

<!-- HealthKit -->
<key>NSHealthShareUsageDescription</key>
<string>Chi Daily reads your health data to improve personalized recommendations.</string>
<key>NSHealthUpdateUsageDescription</key>
<string>Chi Daily logs your daily mood and energy to Apple Health for trend tracking.</string>
```

---

## 5. Subscription Configuration (ASC)

| Field | Value |
|-------|-------|
| Subscription Group Name | Chi Daily Premium |
| Monthly Product ID | `com.aniccafactory.chidaily.monthly` |
| Monthly Price | $4.99 USD (Tier 5) |
| Annual Product ID | `com.aniccafactory.chidaily.annual` |
| Annual Price | $34.99 USD (Tier 35) |
| Free Trial | 7 days |
| Reference Name | Chi Daily Monthly / Chi Daily Annual |

---

## 6. Pre-Submission Checklist (7 Gates)

| # | Gate | Command / Action | Pass Criteria |
|---|------|-----------------|--------------|
| 1 | **Greenlight preflight** | `greenlight preflight ChiDailyios/` | CRITICAL = 0 |
| 2 | **PrivacyInfo.xcprivacy** | File exists in Xcode target | NSPrivacyAccessedAPICategoryUserDefaults declared |
| 3 | **No RevenueCatUI** | `grep -r 'import RevenueCatUI' --include='*.swift' .` | 0 results |
| 4 | **No Mock** | `grep -r 'Mock' --include='*.swift' . | grep -v Tests | wc -l` | 0 |
| 5 | **No tracking SDK** | Greenlight scan | No Mixpanel, Firebase, Amplitude |
| 6 | **Build validates** | `asc validate` | Errors = 0 |
| 7 | **Localization** | Manual: launch in Japanese simulator | No English strings in JA locale |

---

## 7. Build + Upload Process

```bash
# Source secrets
source ~/.config/mobileapp-builder/.env
security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db

# Set ASC env
export ASC_BYPASS_KEYCHAIN=true

# Full release
cd ChiDailyios && fastlane full_release
# OR step-by-step:
fastlane build       # Archive + IPA
fastlane upload      # Upload to ASC
fastlane submit_review  # Submit for App Store Review
```

---

## 8. TestFlight Distribution

```bash
export ASC_BYPASS_KEYCHAIN=true

# Get build info
asc builds list --app $APP_ID --limit 3

# Create TestFlight group
asc testflight groups create --app $APP_ID --name "Internal Testers"

# Distribute build
asc testflight builds distribute --app $APP_ID --build $BUILD_ID --group "Internal Testers"

# Get TestFlight link
TESTFLIGHT_URL=$(asc testflight builds get-link --app $APP_ID --build $BUILD_ID)
```

---

## 9. Review Information

```bash
export ASC_BYPASS_KEYCHAIN=true

# Set review details
asc review-details set --app $APP_ID \
  --demo-account-required false \
  --notes "Chi Daily is a TCM wellness check-in app. Core feature: answer 5 questions, receive on-device AI recommendations. No login required. RevenueCat subscription: 7-day trial then $4.99/month. 'Maybe Later' button always visible on paywall."
```

**Age Rating:** All 22 items = None / No.

---

## 10. Post-Launch Monitoring

| Metric | Tool | Check frequency |
|--------|------|----------------|
| Crash rate | Xcode Organizer | Daily (first week) |
| App Store reviews | ASC | Daily (first week) |
| Trial conversion | RevenueCat Dashboard | Daily |
| MRR | RevenueCat Dashboard | Weekly |

---

## 11. Launch Marketing Strategy

### Pre-Launch (Week -1)
- Create short-form TikTok: "I built an app for the Chinese Baddie TCM trend 🌿"
- Post on X: Build-in-public thread

### Launch Day
- Post TikTok demo (screen recording of check-in → result)
- Submit to: indie dev communities, wellness communities
- Price-point announcement: "7-day free trial, then $4.99/month"

### Post-Launch
- Respond to all App Store reviews within 24h
- Collect top 3 feature requests for v1.1
- Target: 500 installs in first 30 days

---

## 12. Success Metrics

| Metric | 30-Day Target |
|--------|--------------|
| Total installs | 500+ |
| Day-1 retention | 40%+ |
| Trial start rate | 15%+ |
| Trial-to-paid conversion | 30%+ |
| MRR | $200+ |
| App Store rating | 4.5+ (after 10+ reviews) |
