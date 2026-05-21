# Release Specification: FrostDip

## 1. Pre-Submission Checklist

Source: [Apple App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
Source: CLAUDE.md CRITICAL Rules

| Gate | Command | Pass Criteria |
|------|---------|---------------|
| 1. Unit tests pass | `cd FrostDipios && fastlane test` | All tests GREEN |
| 2. Build succeeds | `cd FrostDipios && fastlane build` | BUILD SUCCEEDED |
| 3. Greenlight preflight | `greenlight preflight FrostDipios/` | CRITICAL = 0 |
| 4. No analytics SDK (Rule 17) | `grep -rE "Mixpanel\|Analytics\|Firebase" FrostDip/ --include="*.swift" \| grep -v Tests/ \| wc -l` | 0 |
| 5. No RevenueCatUI (Rule 20) | `grep -r "RevenueCatUI" FrostDip/ --include="*.swift" \| wc -l` | 0 |
| 6. No ATT (Rule 20b) | `grep -rE "ATTrackingManager\|AppTrackingTransparency" FrostDip/ --include="*.swift" \| wc -l` | 0 |
| 7. No AI APIs (Rule 21) | `grep -rE "OpenAI\|Anthropic\|GoogleGenerativeAI\|FoundationModels" FrostDip/ --include="*.swift" \| wc -l` | 0 |
| 8. PrivacyInfo.xcprivacy exists | `test -f FrostDipios/FrostDip/Resources/PrivacyInfo.xcprivacy && echo PASS` | PASS |
| 9. Maestro E2E smoke tests | `maestro test maestro/ --tags smokeTest` | All PASS |

---

## 2. App Store Metadata

Source: PRD.md §14 (SSOT)

### en-US

| Field | Value |
|-------|-------|
| app_name | Cold Plunge Timer - FrostDip |
| subtitle | Ice Bath Tracker & Streaks |
| keywords | cold plunge,ice bath,cold exposure,plunge timer,cold therapy,ice bath tracker,wim hof,contrast therapy,cold water,streak |
| promotional_text | Track your cold plunge sessions with precision timing, heart rate monitoring, and progressive protocols. Join thousands of cold plungers building consistency. |
| description | FrostDip is the ultimate cold plunge and ice bath tracking app designed for serious cold exposure enthusiasts.\n\nTIMER WITH PRECISION\n- Second-level countdown timer (not just minutes)\n- Breathing preparation phase before each plunge\n- Haptic alerts at custom intervals\n- Background mode support\n\nTRACK YOUR PROGRESS\n- Log every session: duration, water temperature, notes\n- View your complete session history\n- Track daily streaks and longest streaks\n- Progress dashboard with charts\n\nHEART RATE MONITORING\n- Live heart rate from HealthKit during sessions\n- Average and max HR saved per session\n- Track your HR adaptation over time\n\nPROGRESSIVE PROTOCOLS\n- Start with beginner protocols\n- Create custom protocols with rounds and rest periods\n- Contrast therapy mode (hot/cold alternating)\n\nPRIVACY FIRST\n- All data stored on your device\n- No account required\n- No tracking or analytics\n\nFree: Basic timer + 7-day history\nPremium: Unlimited history, HealthKit HR, custom protocols, streaks, progress dashboard, contrast therapy\n\nSubscription pricing:\n- Monthly: $6.99/month\n- Annual: $29.99/year (save 64%)\n\nPayment will be charged to your Apple ID account at confirmation of purchase. Subscription automatically renews unless canceled at least 24 hours before the end of the current period. |

### ja

| Field | Value |
|-------|-------|
| app_name | Cold Plunge Timer - FrostDip |
| subtitle | アイスバストラッカー＆ストリーク |
| keywords | コールドプランジ,アイスバス,冷水浴,プランジタイマー,冷水療法,冷水シャワー,ヴィムホフ,コントラストセラピー,冷水,ストリーク |
| promotional_text | 精密なタイミング、心拍数モニタリング、プログレッシブプロトコルで冷水浴セッションを記録。一貫性を築く数千人のコールドプランジャーに参加しよう。 |
| description | FrostDipは、本格的な冷水浴愛好家のために設計された究極のコールドプランジ＆アイスバストラッキングアプリです。\n\n精密タイマー\n- 秒単位のカウントダウンタイマー\n- プランジ前の呼吸準備フェーズ\n- カスタム間隔での触覚アラート\n- バックグラウンドモード対応\n\n進捗を記録\n- 全セッションを記録：時間、水温、メモ\n- 完全なセッション履歴を表示\n- デイリーストリークと最長ストリークを追跡\n- チャート付きプログレスダッシュボード\n\n心拍数モニタリング\n- HealthKitからのリアルタイム心拍数\n- セッションごとの平均・最大HRを保存\n- HR適応の変化を追跡\n\nプログレッシブプロトコル\n- 初心者プロトコルからスタート\n- ラウンドと休憩時間のカスタムプロトコル作成\n- コントラストセラピーモード（温冷交互）\n\nプライバシーファースト\n- 全データはデバイスに保存\n- アカウント不要\n- トラッキングやアナリティクスなし\n\n無料：基本タイマー＋7日間の履歴\nプレミアム：無制限の履歴、HealthKit HR、カスタムプロトコル、ストリーク、プログレスダッシュボード、コントラストセラピー\n\nサブスクリプション価格：\n- 月額：$6.99/月\n- 年額：$29.99/年（64%お得）\n\nお支払いは購入確認時にApple IDアカウントに請求されます。サブスクリプションは、現在の期間終了の24時間前までにキャンセルしない限り自動的に更新されます。 |

---

## 3. Screenshots

Source: [Apple App Store Screenshot Specifications](https://developer.apple.com/help/app-store-connect/reference/screenshot-specifications/)

### Device Requirements

| Device Type | Display Size | Resolution | ASC Device Type |
|-------------|-------------|-----------|-----------------|
| iPhone 15 Pro Max | 6.7" | 1290 x 2796 | IPHONE_67 |
| iPhone 15 Pro | 6.1" | 1179 x 2556 | IPHONE_61 |
| iPhone SE (3rd gen) | 4.7" | 750 x 1334 | IPHONE_47 |

### Screenshot Plan (per locale)

| # | Screen | Caption (en-US) | Caption (ja) | Key Element |
|---|--------|----------------|-------------|-------------|
| 1 | TimerView (active) | Precision Cold Plunge Timer | 精密コールドプランジタイマー | Circular timer at 2:00, breathing prep visible |
| 2 | SessionSummaryView | Track Every Session | 全セッションを記録 | Duration, temp, HR stats displayed |
| 3 | ProgressDashboardView | See Your Progress | 進捗を確認 | Duration chart trending up, streak calendar |
| 4 | BreathingPrepView | Guided Breathing Prep | ガイド付き呼吸準備 | Breathing circle animation, phase label |
| 5 | PaywallView | Unlock Full Potential | フルポテンシャルを解放 | Benefits list, pricing cards |

### Capture Commands

```bash
# Capture screenshots per locale
asc screenshots capture --bundle-id com.aniccafactory.frostdip --udid $DEVICE_UDID --output-dir screenshots/en-US --output json
asc screenshots capture --bundle-id com.aniccafactory.frostdip --udid $DEVICE_UDID --output-dir screenshots/ja --output json

# Frame with Koubou
asc screenshots frame --input-dir screenshots/en-US --output-dir screenshots/framed/en-US --device-type IPHONE_67
asc screenshots frame --input-dir screenshots/ja --output-dir screenshots/framed/ja --device-type IPHONE_67

# Upload
asc screenshots upload --version-localization $EN_LOC_ID --path screenshots/framed/en-US --device-type IPHONE_67
asc screenshots upload --version-localization $JA_LOC_ID --path screenshots/framed/ja --device-type IPHONE_67
```

### Locale Verification

```bash
# Verify en-US and ja screenshots are different (localized content)
md5 screenshots/framed/en-US/01.png
md5 screenshots/framed/ja/01.png
# MD5 values MUST differ
```

---

## 4. Privacy

Source: ARCHITECTURE.md §11, PRD.md §10

### PrivacyInfo.xcprivacy

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
    <key>NSPrivacyTracking</key>
    <false/>
    <key>NSPrivacyTrackingDomains</key>
    <array/>
</dict>
</plist>
```

### App Privacy Questionnaire (ASC Web)

| Question | Answer |
|----------|--------|
| Does your app collect data? | No — all data is stored on-device only |
| Does your app use tracking? | No |
| Third-party SDKs that collect data? | RevenueCat — handles its own privacy manifest |
| HealthKit data collected? | Read-only (heart rate), never transmitted off-device |

---

## 5. Build & Archive

Source: IMPLEMENTATION_GUIDE.md §8

### Build Pipeline

```bash
# 1. Source secrets
source ~/.config/mobileapp-builder/.env
security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db

# 2. Run tests
cd FrostDipios && fastlane test

# 3. Build archive
cd FrostDipios && fastlane release

# 4. Verify upload
asc builds list --app $APP_ID --sort -uploadedDate --limit 1
# Expected: processingState = VALID
```

### Version & Build Numbers

| Field | Format | Example |
|-------|--------|---------|
| CFBundleShortVersionString | MAJOR.MINOR.PATCH | 1.0.0 |
| CFBundleVersion | Sequential integer | 1 |

---

## 6. TestFlight

Source: [Apple TestFlight](https://developer.apple.com/testflight/)

### Beta Test Plan

| Phase | Testers | Duration | Focus |
|-------|---------|----------|-------|
| Internal | Developer (self) | 1 day | Smoke test all features |
| External (if needed) | Up to 10 invites | 3 days | Paywall flow, HealthKit, timer accuracy |

### TestFlight Setup Commands

```bash
# Get latest build
BUILD_ID=$(asc builds list --app $APP_ID --sort -uploadedDate --limit 1 --output json | jq -r '.[0].id')

# Add build to beta group
asc builds add-groups --build $BUILD_ID --group $BETA_GROUP_ID

# Add tester
asc testflight beta-testers add --app $APP_ID --email $TESTER_EMAIL --group $BETA_GROUP_ID

# Invite tester
asc testflight beta-testers invite --app $APP_ID --email $TESTER_EMAIL
```

---

## 7. Submission

Source: [Apple App Review](https://developer.apple.com/app-store/review/)

### Review Information

| Field | Value |
|-------|-------|
| Contact First Name | (from .env: $CONTACT_FIRST_NAME) |
| Contact Last Name | (from .env: $CONTACT_LAST_NAME) |
| Contact Email | (from .env: $CONTACT_EMAIL) |
| Contact Phone | (from .env: $CONTACT_PHONE) |
| Demo Account Required | NO |
| Notes for Reviewer | "FrostDip is a cold plunge timer app. No login required. To test premium features, use the sandbox account. The app uses HealthKit to read heart rate during active timer sessions. All data is stored locally on-device." |

### Compliance Questions

| Question | Answer | Rationale |
|----------|--------|-----------|
| Export Compliance (Encryption) | NO — does not use non-exempt encryption | App uses HTTPS (system framework) only |
| Content Rights | DOES_NOT_USE_THIRD_PARTY_CONTENT | All content is original |
| Advertising Identifier (IDFA) | NO | No ads, no tracking (Rule 20b) |

### Submission Commands

```bash
# Create review submission
asc review submissions-create --app $APP_ID

# Add version to submission
asc review items-add --submission $SUBMISSION_ID --version $VERSION_ID

# Submit for review
asc review submissions-submit --submission $SUBMISSION_ID
# Expected: status = WAITING_FOR_REVIEW
```

---

## 8. Review Notes

| Topic | Note for Reviewer |
|-------|-------------------|
| AI Usage | This app does not use any AI models, APIs, or machine learning features. All logic is deterministic (timers, counters, streaks). |
| Subscription | FrostDip offers monthly ($6.99) and annual ($29.99) auto-renewable subscriptions managed via RevenueCat SDK. Free tier includes basic timer and 7-day history. |
| HealthKit | The app reads heart rate data from HealthKit during active cold plunge sessions. Data is displayed in real-time and saved locally. No health data leaves the device. |
| Offline | The app works fully offline. No internet connection required except for initial subscription verification. |
| Privacy | No analytics, no tracking, no IDFA, no ATT. PrivacyInfo.xcprivacy declares UserDefaults (CA92.1) only. |

---

## 9. Age Rating

Source: [Apple Age Rating Guide](https://developer.apple.com/help/app-store-connect/reference/age-ratings/)

| Category | Value |
|----------|-------|
| Cartoon or Fantasy Violence | None |
| Realistic Violence | None |
| Prolonged Graphic or Sadistic Realistic Violence | None |
| Profanity or Crude Humor | None |
| Mature/Suggestive Themes | None |
| Horror/Fear Themes | None |
| Medical/Treatment Information | None |
| Alcohol, Tobacco, or Drug Use or References | None |
| Simulated Gambling | None |
| Sexual Content or Nudity | None |
| Graphic Sexual Content and Nudity | None |
| Unrestricted Web Access | None |
| Gambling with Real Currency | None |
| Contests | None |
| Age Rating Result | 4+ |

All 22 categories: **NONE**. Result: **4+**

---

## 10. Hotfix Protocol

| Step | Action | Command |
|------|--------|---------|
| 1 | Create hotfix branch | `git checkout -b hotfix/x.x.x main` |
| 2 | Fix bug | Edit source files |
| 3 | Bump patch version | Update CFBundleShortVersionString (e.g. 1.0.0 → 1.0.1) |
| 4 | Increment build number | Update CFBundleVersion |
| 5 | Run tests | `cd FrostDipios && fastlane test` |
| 6 | Greenlight | `greenlight preflight FrostDipios/` |
| 7 | Build + upload | `cd FrostDipios && fastlane release` |
| 8 | Submit | `asc review submissions-create --app $APP_ID` → `items-add` → `submissions-submit` |
| 9 | Merge back | `git checkout main && git merge hotfix/x.x.x && git checkout dev && git cherry-pick <commit>` |
| 10 | Clean up | `git branch -d hotfix/x.x.x` |

---

## 11. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | TBD | Initial release: Cold plunge timer, breathing prep, session logging, HealthKit HR, streaks, progress dashboard, contrast therapy, RevenueCat subscriptions ($6.99/mo, $29.99/yr) |
