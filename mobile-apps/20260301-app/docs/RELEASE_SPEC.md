# Release Specification: AffirmFlow

**Version:** 1.0.0
**Date:** 2026-03-01
**Status:** APPROVED

---

## 1. App Store Metadata

### 1.1 Basic Information

| Field | Value |
|-------|-------|
| **App Name** | AffirmFlow |
| **Subtitle** | AI Affirmations Widget |
| **Bundle ID** | com.anicca.affirmflow |
| **Primary Category** | Health & Fitness |
| **Secondary Category** | Lifestyle |
| **Content Rating** | 4+ |
| **Price** | Free (with IAP) |

### 1.2 Keywords (100 characters max)

```
affirmation,widget,AI,daily,positive,mindset,motivation,wellness,self-care,mental,health,gratitude
```

**Character count:** 98

### 1.3 Description

```
Start every day with AI-powered affirmations personalized just for you.

AffirmFlow uses Apple's on-device AI to generate unique, meaningful affirmations based on your personal focus areas. Unlike other apps, your thoughts never leave your phone — 100% private, 100% personal.

WHY AFFIRMFLOW?

AI-Powered Personalization
Unlike generic quote apps, AffirmFlow generates fresh affirmations tailored to your goals. Each one is unique to you.

Widget-First Design
Your daily affirmation lives right on your home screen. No need to open an app — just glance and feel inspired.

100% On-Device Privacy
Your affirmations are generated entirely on your device. No cloud, no servers, no data sharing. Your thoughts stay yours.

FEATURES

- AI-generated affirmations using Apple Intelligence
- Home screen and lock screen widgets
- 5 focus areas: Confidence, Gratitude, Calm, Motivation, Self-Love
- Save your favorite affirmations
- Beautiful themes (Premium)
- Unlimited refreshes (Premium)

HOW IT WORKS

1. Choose up to 3 focus areas that matter to you
2. Add the widget to your home screen
3. Wake up to a new, personalized affirmation every day
4. Tap to refresh for a new affirmation anytime

PREMIUM

Free users get 3 affirmations per day. Upgrade to Premium for:
- Unlimited affirmations
- Lock screen widget
- 5 beautiful themes
- All focus areas

Start your day with positivity. Download AffirmFlow now.

Terms of Service: https://affirmflow.app/terms
Privacy Policy: https://affirmflow.app/privacy
```

### 1.4 Promotional Text (170 characters)

```
AI-powered affirmations, 100% on your device. Start your day with personalized positivity.
```

### 1.5 What's New (v1.0.0)

```
Welcome to AffirmFlow!

- AI-generated affirmations using Apple Intelligence
- Home screen and lock screen widgets
- 5 focus areas to personalize your experience
- Save your favorite affirmations
- Premium themes and unlimited refreshes

Your journey to daily positivity starts now.
```

---

## 2. App Store Assets

### 2.1 App Icon

| Requirement | Specification |
|-------------|---------------|
| Size | 1024x1024px |
| Format | PNG (no alpha) |
| Corners | Square (iOS rounds automatically) |
| Design | Gradient purple-pink, meditation/sparkle icon |

### 2.2 Screenshots

#### iPhone 6.7" (iPhone 15 Pro Max)

| # | Content | Caption |
|---|---------|---------|
| 1 | Widget on home screen | AI affirmations on your home screen |
| 2 | Focus area selection | Choose what matters to you |
| 3 | Home view with affirmation | Personalized just for you |
| 4 | Favorites list | Save your favorites |
| 5 | Lock screen widget | Start your day right |

**Dimensions:** 1290 x 2796px (or 1284 x 2778px)

#### iPhone 6.5" (iPhone 11 Pro Max)

| # | Content | Caption |
|---|---------|---------|
| 1-5 | Same as 6.7" | Same captions |

**Dimensions:** 1242 x 2688px

#### iPad 12.9" (if supporting iPad)

| # | Content | Caption |
|---|---------|---------|
| 1-5 | Same content, tablet layout | Same captions |

**Dimensions:** 2048 x 2732px

### 2.3 App Preview Video (Optional)

| Specification | Value |
|---------------|-------|
| Duration | 15-30 seconds |
| Resolution | 1080p minimum |
| Format | H.264, AAC audio |
| Content | Widget setup → refresh → favorite |

**Storyboard:**
1. (0-5s) Home screen with widget
2. (5-15s) Open app, show affirmation
3. (15-25s) Refresh, save to favorites
4. (25-30s) App icon with tagline

---

## 3. Privacy & Compliance

### 3.1 Privacy Manifest (PrivacyInfo.xcprivacy)

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
    <array>
        <dict>
            <key>NSPrivacyCollectedDataType</key>
            <string>NSPrivacyCollectedDataTypePurchaseHistory</string>
            <key>NSPrivacyCollectedDataTypeLinked</key>
            <false/>
            <key>NSPrivacyCollectedDataTypeTracking</key>
            <false/>
            <key>NSPrivacyCollectedDataTypePurposes</key>
            <array>
                <string>NSPrivacyCollectedDataTypePurposeAppFunctionality</string>
            </array>
        </dict>
    </array>
    <key>NSPrivacyTracking</key>
    <false/>
</dict>
</plist>
```

### 3.2 App Privacy Details (App Store Connect)

| Data Type | Collected | Linked to User | Used for Tracking |
|-----------|-----------|----------------|-------------------|
| **Purchase History** | Yes | No | No |
| **Device ID** | No | - | - |
| **Location** | No | - | - |
| **Contact Info** | No | - | - |
| **User Content** | No | - | - |

**Privacy Nutrition Label:**
- Data Used to Track You: None
- Data Linked to You: None
- Data Not Linked to You: Purchases

### 3.3 Required Disclosures

| Disclosure | Status | Notes |
|------------|--------|-------|
| Export Compliance (ECCN) | Standard encryption | Uses HTTPS for RevenueCat only |
| Third-Party Content | N/A | All AI content generated on-device |
| Made for Kids | No | General audience |
| Gambling | No | N/A |

---

## 4. In-App Purchases

### 4.1 Products

| Product ID | Type | Price | Description |
|------------|------|-------|-------------|
| `com.anicca.affirmflow.premium.weekly` | Auto-Renewable | $2.99/week | Weekly premium access |
| `com.anicca.affirmflow.premium.annual` | Auto-Renewable | $29.99/year | Annual premium access |

### 4.2 Subscription Group

| Field | Value |
|-------|-------|
| Group Name | AffirmFlow Premium |
| Group ID | (auto-generated) |
| Products | Weekly, Annual |

### 4.3 Subscription Metadata

**Display Name:** AffirmFlow Premium

**Description:**
```
Unlock unlimited AI affirmations, lock screen widget, beautiful themes, and all focus areas.
```

---

## 5. Pre-Submission Checklist

### 5.1 Development

| Task | Status |
|------|--------|
| All P0 features implemented | |
| All P1 features implemented | |
| Unit tests passing (80%+ coverage) | |
| UI tests passing | |
| No compiler warnings | |
| No SwiftLint errors | |

### 5.2 Testing

| Task | Status |
|------|--------|
| Tested on latest iOS 26 beta | |
| Tested on iPhone 15 Pro | |
| Tested on iPhone SE (if supporting) | |
| Widget tested on home screen | |
| Widget tested on lock screen | |
| TestFlight beta complete | |
| Crash-free rate > 99.5% | |

### 5.3 Privacy & Compliance

| Task | Status |
|------|--------|
| PrivacyInfo.xcprivacy added | |
| Privacy manifest reviewed | |
| App Privacy details ready | |
| Terms of Service URL active | |
| Privacy Policy URL active | |
| Export compliance answered | |

### 5.4 Assets

| Task | Status |
|------|--------|
| App icon 1024x1024 ready | |
| Screenshots 6.7" ready (5) | |
| Screenshots 6.5" ready (5) | |
| App preview video (optional) | |

### 5.5 Metadata

| Task | Status |
|------|--------|
| App name finalized | |
| Subtitle finalized | |
| Keywords optimized (100 chars) | |
| Description written | |
| What's New written | |
| Promotional text written | |

### 5.6 Subscriptions

| Task | Status |
|------|--------|
| Products created in ASC | |
| Subscription group created | |
| RevenueCat configured | |
| Test purchases verified | |
| Restore purchases works | |

---

## 6. Submission Process

### 6.1 Build & Archive

```bash
# Clean build
xcodebuild clean -scheme AffirmFlow

# Archive
xcodebuild archive \
  -scheme AffirmFlow \
  -archivePath ./build/AffirmFlow.xcarchive \
  -destination 'generic/platform=iOS'

# Export IPA
xcodebuild -exportArchive \
  -archivePath ./build/AffirmFlow.xcarchive \
  -exportPath ./build \
  -exportOptionsPlist ExportOptions.plist
```

### 6.2 Upload to App Store Connect

**Option 1: Xcode**
1. Xcode → Window → Organizer
2. Select archive → Distribute App
3. App Store Connect → Upload

**Option 2: altool**
```bash
xcrun altool --upload-app \
  --type ios \
  --file ./build/AffirmFlow.ipa \
  --username "your@email.com" \
  --password "@keychain:AC_PASSWORD"
```

### 6.3 App Store Connect Configuration

1. Log in to App Store Connect
2. Go to Apps → AffirmFlow
3. Create new version 1.0.0
4. Fill in all metadata
5. Upload screenshots
6. Select build
7. Answer App Privacy questions
8. Submit for Review

### 6.4 Review Notes

```
Thank you for reviewing AffirmFlow.

AffirmFlow is an AI-powered affirmation app that uses Apple's Foundation Models framework for on-device AI generation. All processing happens locally on the user's device.

TEST ACCOUNT: Not required (no login)

DEMO STEPS:
1. Complete onboarding by selecting focus areas
2. Add widget to home screen
3. View AI-generated affirmation
4. Tap refresh to generate new affirmation
5. Tap heart to save to favorites

SUBSCRIPTION TESTING:
- Free tier: 3 affirmations per day
- Premium: Unlimited (use Sandbox account)

IN-APP PURCHASES:
- Weekly: $2.99/week
- Annual: $29.99/year

SPECIAL NOTES:
- Requires iOS 26 for Foundation Models framework
- Widget requires manual addition by user

Contact: support@affirmflow.app
```

---

## 7. Post-Submission

### 7.1 Monitor Review Status

| Status | Meaning | Action |
|--------|---------|--------|
| Waiting for Review | In queue | Wait |
| In Review | Being reviewed | Wait |
| Pending Developer Release | Approved, manual release | Release when ready |
| Ready for Sale | Live on App Store | Celebrate! |
| Rejected | Issues found | Fix and resubmit |

### 7.2 Common Rejection Reasons

| Issue | Solution |
|-------|----------|
| Crashes | Fix bugs, test thoroughly |
| Incomplete metadata | Fill all required fields |
| Misleading screenshots | Use accurate screenshots |
| Privacy policy missing | Add valid URL |
| IAP issues | Test subscription flow |

### 7.3 Appeal Process

If rejected unfairly:
1. Reply to rejection email
2. Explain your case clearly
3. Reference App Review Guidelines
4. Request phone call if needed

---

## 8. Launch Plan

### 8.1 Pre-Launch (Week -1)

| Task | Status |
|------|--------|
| Finalize landing page | |
| Prepare social media | |
| Write press kit | |
| Notify beta testers | |

### 8.2 Launch Day

| Task | Status |
|------|--------|
| Release app | |
| Post on Product Hunt | |
| Tweet announcement | |
| Post on Reddit | |
| Email beta testers | |
| Monitor crashes | |

### 8.3 Post-Launch (Week 1-2)

| Task | Status |
|------|--------|
| Respond to reviews | |
| Fix critical bugs | |
| Analyze analytics | |
| Plan v1.0.1 | |

---

## 9. Post-Launch Monitoring

### 9.1 Key Metrics

| Metric | Target | Tool |
|--------|--------|------|
| Crash-free rate | > 99.5% | Xcode Organizer |
| App Store rating | > 4.5 | App Store Connect |
| Downloads | 1000+ Month 1 | App Store Connect |
| Premium conversion | > 3% | RevenueCat |
| Widget adoption | > 50% | Custom analytics |

### 9.2 Review Response Templates

**Positive Review:**
```
Thank you so much for your kind words! We're thrilled AffirmFlow is helping you start your days positively. We'd love to hear any suggestions for future updates!
```

**Bug Report:**
```
Thank you for reporting this issue. We're sorry you experienced this problem. We're investigating and will fix it in the next update. Please contact support@affirmflow.app if you need immediate help.
```

**Feature Request:**
```
Thank you for your feedback! We love hearing your ideas. This is definitely something we're considering for a future update. Stay tuned!
```

---

## 10. Version Planning

### 10.1 v1.0.1 (Bug Fixes)

| Target | 1-2 weeks post-launch |
|--------|----------------------|
| Focus | Critical bug fixes |
| Features | None |

### 10.2 v1.1.0 (First Feature Update)

| Target | 4-6 weeks post-launch |
|--------|----------------------|
| Features | Daily notifications, more themes |

### 10.3 v2.0.0 (Major Update)

| Target | 3-6 months post-launch |
|--------|------------------------|
| Features | TBD based on user feedback |

---

## 11. Marketing Channels

### 11.1 App Store Optimization (ASO)

| Element | Strategy |
|---------|----------|
| Keywords | Focus on "affirmation widget", "AI", "privacy" |
| Screenshots | Show widget prominently |
| Description | Lead with AI + privacy differentiators |
| Reviews | Respond promptly, encourage happy users |

### 11.2 Social Media

| Platform | Strategy |
|----------|----------|
| Twitter/X | Daily affirmation posts, indie dev journey |
| Reddit | r/iOS, r/selfimprovement, r/widgets |
| TikTok | Widget demo videos, morning routine content |
| Product Hunt | Launch on Monday |

### 11.3 Press & Content

| Channel | Content |
|---------|---------|
| Blog | How AffirmFlow uses Foundation Models |
| Press release | Privacy-first AI app launch |
| Indie Hackers | Build in public updates |

---

## 12. Support

### 12.1 Contact Channels

| Channel | Response Time |
|---------|---------------|
| Email: support@affirmflow.app | < 24 hours |
| App Store reviews | < 48 hours |

### 12.2 FAQ

**Q: Why does AffirmFlow require iOS 26?**
A: AffirmFlow uses Apple's Foundation Models framework, which is only available on iOS 26 and later.

**Q: Is my data stored in the cloud?**
A: No. All affirmation generation happens on your device. Your data never leaves your phone.

**Q: How do I add the widget?**
A: Long press your home screen, tap +, search "AffirmFlow", and add the widget.

**Q: How do I restore my purchase?**
A: Go to Settings → Restore Purchases.

---

**Document End**
