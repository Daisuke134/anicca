# Release Specification: EyeBreakIsland

**Version:** 1.0.0
**Date:** 2026-03-07
**SSOT:** docs/PRD.md
**Architecture:** docs/ARCHITECTURE.md
**Test Spec:** docs/TEST_SPEC.md

Source: [Apple: App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) — "Apps submitted for review must work on the current shipping version of iOS"
Source: [Apple: App Store Connect Help](https://developer.apple.com/help/app-store-connect/) — "Prepare metadata, screenshots, and pricing before submission"
Source: [asc CLI: ASC CLI Usage](https://github.com/nicklama/asc) — "Automate App Store Connect workflows"

---

## 1. Pre-Submission Checklist

| # | Gate | Command | Pass Criteria |
|---|------|---------|---------------|
| 1 | Unit tests pass | `cd EyeBreakIslandios && fastlane test` | 0 failures |
| 2 | E2E tests pass | `maestro test maestro/` | All 6 flows PASS |
| 3 | No analytics SDK (Rule 17) | `grep -rE "Mixpanel\|Analytics\|Firebase" EyeBreakIsland/ --include="*.swift" \| grep -v Tests/` | 0 matches |
| 4 | No RevenueCatUI (Rule 20) | `grep -r "RevenueCatUI" EyeBreakIsland/ --include="*.swift"` | 0 matches |
| 5 | No ATT (Rule 20b) | `grep -r "ATTrackingManager" EyeBreakIsland/ --include="*.swift"` | 0 matches |
| 6 | No AI API (Rule 21) | `grep -rE "OpenAI\|Anthropic\|GoogleGenerativeAI\|FoundationModels" EyeBreakIsland/ --include="*.swift"` | 0 matches |
| 7 | PrivacyInfo.xcprivacy exists | `test -f EyeBreakIsland/Resources/PrivacyInfo.xcprivacy` | File exists |
| 8 | Greenlight preflight | `greenlight preflight EyeBreakIslandios/` | CRITICAL=0 |
| 9 | Build succeeds | `cd EyeBreakIslandios && fastlane build` | BUILD SUCCEEDED |

---

## 2. App Store Metadata

### en-US

| Field | Value |
|-------|-------|
| App Name | Eye Break - EyeBreakIsland |
| Subtitle | 20-20-20 Rule, Dynamic Island |
| Keywords | eye strain,20 20 20 rule,eye break timer,digital eye strain,eye rest reminder,screen break,eye care,focus timer |
| Promotional Text | Protect your eyes. Dynamic Island keeps the countdown visible — always. |
| Description | Eye Break uses the proven 20-20-20 rule to protect your eyes from digital strain. Every 20 minutes, take a 20-second break and look 20 feet away. EyeBreakIsland keeps the countdown in your Dynamic Island — impossible to ignore, impossible to forget. No account required. Works in the background. Start your eye health habit today. |
| Privacy Policy URL | https://daisuke134.github.io/anicca-products/eyebreakisland/privacy-policy.html |
| Support URL | https://daisuke134.github.io/anicca-products/eyebreakisland/support.html |
| Marketing URL | https://daisuke134.github.io/anicca-products/eyebreakisland/ |

### ja

| Field | Value |
|-------|-------|
| App Name | Eye Break - EyeBreakIsland |
| Subtitle | 20-20-20ルール、ダイナミックアイランド |
| Keywords | 眼精疲労,目の疲れ,20-20-20ルール,目休み,デジタルアイストレイン,スクリーン休憩,視力ケア |
| Promotional Text | 目を守る。ダイナミックアイランドでカウントダウンを常時表示。無視できない、忘れない。 |
| Description | Eye Breakは実証済みの20-20-20ルールで目を保護します。20分ごとに20秒間、6メートル先を見てください。EyeBreakIslandはカウントダウンをダイナミックアイランドに常駐させます。アカウント不要。バックグラウンドで動作。今日から目の健康習慣を始めましょう。 |
| Privacy Policy URL | https://daisuke134.github.io/anicca-products/eyebreakisland/privacy-policy.html |
| Support URL | https://daisuke134.github.io/anicca-products/eyebreakisland/support.html |
| Marketing URL | https://daisuke134.github.io/anicca-products/eyebreakisland/ |

Source: PRD.md §14 App Store Metadata — exact copy for consistency

---

## 3. Screenshots

### Device Requirements

| Device Type | ASC Key | Resolution | Required |
|-------------|---------|-----------|----------|
| iPhone 6.7" | `IPHONE_67` | 1290 x 2796 | YES |
| iPhone 6.5" | `IPHONE_65` | 1284 x 2778 | YES (fallback) |

### Screenshot List (per locale)

| # | Screen | Content | Capture Steps |
|---|--------|---------|--------------|
| 1 | Timer (Idle) | Timer ring at 20:00, "Start Eye Break" button | Launch → skip onboarding → capture |
| 2 | Timer (Running) | Timer ring at 18:34, Dynamic Island visible | Start timer → wait 86 sec → capture |
| 3 | Break Overlay | Full-screen break countdown at 15 | Start timer → fast-forward → break → capture |
| 4 | Settings | Settings sheet with Pro features highlighted | Open settings → capture |
| 5 | Paywall | Subscription options with Annual selected | Open paywall → select annual → capture |

### Capture Commands

```bash
# Capture via AXe + asc
export ASC_BYPASS_KEYCHAIN=true

# en-US
asc screenshots capture \
    --bundle-id com.aniccafactory.eyebreakisland \
    --udid $SIMULATOR_UDID \
    --output-dir screenshots/en-US \
    --output json

# ja
asc screenshots capture \
    --bundle-id com.aniccafactory.eyebreakisland \
    --udid $SIMULATOR_UDID \
    --output-dir screenshots/ja \
    --output json
```

### Frame & Upload

```bash
# Frame with Koubou
asc screenshots frame \
    --input-dir screenshots/en-US \
    --output-dir screenshots/framed/en-US

asc screenshots frame \
    --input-dir screenshots/ja \
    --output-dir screenshots/framed/ja

# Upload
asc screenshots upload \
    --version-localization $EN_LOC_ID \
    --path screenshots/framed/en-US \
    --device-type IPHONE_67

asc screenshots upload \
    --version-localization $JA_LOC_ID \
    --path screenshots/framed/ja \
    --device-type IPHONE_67
```

---

## 4. Privacy

### PrivacyInfo.xcprivacy

| Key | Value |
|-----|-------|
| NSPrivacyTracking | false |
| NSPrivacyTrackingDomains | (empty) |
| NSPrivacyCollectedDataTypes | (empty) |
| NSPrivacyAccessedAPITypes | UserDefaults (CA92.1) |

### App Privacy Questionnaire (ASC Web)

| Question | Answer |
|----------|--------|
| Do you or your third-party partners collect data? | No |
| Data linked to user identity | None |
| Data used to track users | None |
| Data types collected | None |

### Privacy Policy Content

| Section | Content |
|---------|---------|
| Data Collection | "EyeBreakIsland does not collect, store, or transmit any personal data." |
| Analytics | "No analytics SDKs are used. No usage data is sent to any server." |
| Third-Party Services | "RevenueCat processes subscription transactions. See RevenueCat Privacy Policy." |
| Contact | support email from .env |

Source: [Apple: App Privacy Details](https://developer.apple.com/app-store/app-privacy-details/) — "All apps must declare their privacy practices"

---

## 5. Build & Archive

### Build Pipeline

```bash
# 1. Unlock keychain
source ~/.config/mobileapp-builder/.env
security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db

# 2. Run tests
cd EyeBreakIslandios && fastlane test

# 3. Build archive
cd EyeBreakIslandios && fastlane archive

# 4. Upload to App Store Connect
cd EyeBreakIslandios && fastlane beta
```

### Fastlane Fastfile Lanes

| Lane | Purpose | Command |
|------|---------|---------|
| `test` | Run all unit + integration tests | `scan(scheme: "EyeBreakIsland")` |
| `build` | Build for testing (no archive) | `build_app(scheme: "EyeBreakIsland", skip_archive: true)` |
| `archive` | Create .ipa for distribution | `build_app(scheme: "EyeBreakIsland", export_method: "app-store")` |
| `beta` | Upload to TestFlight | `upload_to_testflight` |

### Version & Build Numbers

| Field | Value | Update Rule |
|-------|-------|------------|
| CFBundleShortVersionString | 1.0.0 | Semver: major.minor.patch |
| CFBundleVersion | 1 | Increment on every upload |

---

## 6. TestFlight

### Beta Test Plan

| Phase | Duration | Testers | Goal |
|-------|----------|---------|------|
| Internal | 1 day | Development team | Verify build, crash-free |
| External | 3 days | Beta group | UX feedback, edge cases |

### TestFlight Setup

```bash
export ASC_BYPASS_KEYCHAIN=true

# Get latest build
asc builds list --app $APP_ID --sort -uploadedDate --limit 1

# Add build to beta group
asc builds add-groups --build $BUILD_ID --group $GROUP_ID

# Add tester
asc testflight beta-testers add --app $APP_ID --email tester@example.com --group $GROUP_ID

# Invite tester
asc testflight beta-testers invite --app $APP_ID --email tester@example.com
```

### Beta Test Checklist

| # | Test | Expected |
|---|------|----------|
| 1 | Fresh install → onboarding completes | 4 pages, paywall shows, dismiss works |
| 2 | Timer starts and runs in background | Notification received after 20 min |
| 3 | Dynamic Island shows countdown | Time updates every second |
| 4 | Break overlay appears and auto-dismisses | 20-sec countdown, then back to timer |
| 5 | Settings accessible | All rows display correctly |
| 6 | Paywall displays packages | Monthly + Annual with correct prices |
| 7 | Restore purchases works | No crash, shows result |
| 8 | Japanese locale | All strings localized |

---

## 7. Submission

### Review Information

| Field | Value |
|-------|-------|
| Contact First Name | (from .env: ASC_CONTACT_FIRST) |
| Contact Last Name | (from .env: ASC_CONTACT_LAST) |
| Contact Phone | (from .env: ASC_CONTACT_PHONE) |
| Contact Email | (from .env: ASC_CONTACT_EMAIL) |
| Demo Account Required | NO |
| Notes for Reviewer | "This app uses the 20-20-20 rule to remind users to rest their eyes. The Dynamic Island displays a countdown timer. The app does not require login, does not collect data, and works fully offline. Subscription features include custom timer intervals, schedule mode, and break statistics." |

### Compliance Answers

| Question | Answer | Rationale |
|----------|--------|-----------|
| Export Compliance (Encryption) | Uses encryption: NO | No custom crypto. HTTPS via RevenueCat SDK is exempt. |
| Content Rights | DOES_NOT_USE_THIRD_PARTY_CONTENT | All content is original |
| Advertising Identifier (IDFA) | NO | Rule 20b: No ATT |

### Submission Commands

```bash
export ASC_BYPASS_KEYCHAIN=true

# Create submission
asc review submissions-create --app $APP_ID

# Add items
asc review items-add --submission $SUBMISSION_ID --version $VERSION_ID

# Submit
asc review submissions-submit --submission $SUBMISSION_ID
```

---

## 8. Review Notes

| Topic | Note for Reviewer |
|-------|-------------------|
| AI Usage | "This app does not use any AI models, APIs, or machine learning. All logic is computed on-device." |
| Subscription | "Subscriptions managed via RevenueCat. Monthly ($4.99) and Annual ($29.99/yr with 7-day trial). Users can manage subscriptions via iOS Settings." |
| Offline | "The app works fully offline. No internet required for core functionality. RevenueCat SDK validates subscriptions when online." |
| Dynamic Island | "The app uses ActivityKit Live Activities to display a countdown in the Dynamic Island. On devices without Dynamic Island, the timer displays as a Lock Screen banner." |
| Data Privacy | "No data collected. No analytics. No tracking. UserDefaults stores only local preferences." |

---

## 9. Age Rating

| Category | Value |
|----------|-------|
| Cartoon or Fantasy Violence | NONE |
| Realistic Violence | NONE |
| Prolonged Graphic or Sadistic Realistic Violence | NONE |
| Profanity or Crude Humor | NONE |
| Mature/Suggestive Themes | NONE |
| Horror/Fear Themes | NONE |
| Medical/Treatment Information | NONE |
| Alcohol, Tobacco, or Drug Use or References | NONE |
| Simulated Gambling | NONE |
| Sexual Content or Nudity | NONE |
| Graphic Sexual Content and Nudity | NONE |
| Contests | NONE |
| Unrestricted Web Access | NONE |
| Gambling | NONE |
| Frequent/Intense - Cartoon or Fantasy Violence | NONE |
| Frequent/Intense - Realistic Violence | NONE |
| Frequent/Intense - Sexual Content or Nudity | NONE |
| Frequent/Intense - Profanity or Crude Humor | NONE |
| Frequent/Intense - Mature/Suggestive Themes | NONE |
| Frequent/Intense - Horror/Fear Themes | NONE |
| Frequent/Intense - Simulated Gambling | NONE |
| Frequent/Intense - Medical/Treatment Information | NONE |

**Result:** 4+ (No objectionable content)

---

## 10. Hotfix Protocol

| Step | Action | Command |
|------|--------|---------|
| 1 | Create hotfix branch | `git checkout -b hotfix/1.0.1 main` |
| 2 | Fix the issue | Edit code |
| 3 | Bump patch version | `1.0.0 → 1.0.1`, increment build number |
| 4 | Run tests | `fastlane test` |
| 5 | Run greenlight | `greenlight preflight EyeBreakIslandios/` |
| 6 | Archive + upload | `fastlane archive && fastlane beta` |
| 7 | Submit for expedited review | `asc review submissions-create --app $APP_ID` + request expedited |
| 8 | Merge back | `git checkout main && git merge hotfix/1.0.1` |
| 9 | Cherry-pick to dev | `git checkout dev && git cherry-pick <hash>` |

---

## 11. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-07 | Initial release. 20-20-20 timer, Dynamic Island, soft paywall, en-US + ja. |

---

**End of Release Specification**
