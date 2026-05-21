# Release Specification: BreathStory

**Date:** 2026-03-04
**Version:** 1.0.0 (Build 1)

---

## Release Timeline

| Phase | Task | Depends On |
|-------|------|-----------|
| 1 | US-005: ASC + IAP + RevenueCat setup | US-004 |
| 2 | US-006: iOS implementation | US-005 |
| 3 | US-007: All tests pass | US-006 |
| 4 | US-008: Screenshots + metadata + build upload | US-007 |
| 5 | US-009: App Privacy + submit | US-008 |

---

## App Store Connect Configuration

### App Information

| Field | Value |
|-------|-------|
| App Name | BreathStory — Guided Breathing Stories |
| Bundle ID | com.anicca.breathstory |
| SKU | breathstory-001 |
| Primary Language | English (U.S.) |
| Category | Health & Fitness |
| Content Rights | Does Not Use Third-Party Content |
| Age Rating | 4+ (no objectionable content) |

### Version Information

| Field | Value |
|-------|-------|
| Version | 1.0.0 |
| Build | 1 |
| What's New | "First release of BreathStory — guided breathing stories." |

---

## Preflight Checklist (7 Gates)

All must pass before submission.

| # | Gate | Command/Check | Required |
|---|------|---------------|---------|
| 1 | Build compiles | `xcodebuild build` | PASS |
| 2 | All tests pass | `xcodebuild test` | PASS |
| 3 | No Mock code | `grep -r 'Mock' --include='*.swift' . \| grep -v Tests/ \| wc -l` = 0 | PASS |
| 4 | Greenlight scan | `greenlight preflight .` → CRITICAL=0 | PASS |
| 5 | PrivacyInfo.xcprivacy | UserDefaults CA92.1 declared | PASS |
| 6 | Info.plist encryption | `ITSAppUsesNonExemptEncryption = NO` | PASS |
| 7 | No ATT | No `NSUserTrackingUsageDescription` | PASS |

---

## Subscription Configuration

| Product ID | Display Name | Price | Duration |
|-----------|--------------|-------|----------|
| `com.anicca.breathstory.monthly` | BreathStory Monthly | $7.99 | 1 Month |
| `com.anicca.breathstory.annual` | BreathStory Annual | $49.99 | 1 Year |

Both products:
- Subscription Group: `BreathStory Premium`
- Free Trial: 7 days
- Entitlement: `premium`
- Territory: 175 territories

---

## Screenshots Required

| Device | Count |
|--------|-------|
| iPhone 6.7" (iPhone 15 Pro Max) | 3 minimum |
| iPhone 6.5" (iPhone 14 Plus) | 3 minimum |
| iPad Pro 12.9" (6th gen) | 3 minimum (optional for Phase 1) |

Locales: en-US (required), ja (required)

Screenshot content:
1. Home screen (story grid)
2. Player (breathing animation in progress)
3. Paywall (subscription offer)

Tool: Koubou (`asc screenshots frame`) — NOT screenshot-creator skill.

---

## Metadata Sync

| Locale | Field | Value |
|--------|-------|-------|
| en-US | Name | BreathStory — Guided Breathing Stories |
| en-US | Subtitle | Calm your stress with short audio tales |
| en-US | Keywords | breathing,breathwork,stress relief,calm,anxiety,relaxation,guided,stories,sleep,meditation |
| ja | Name | BreathStory — 呼吸ガイドストーリー |
| ja | Subtitle | 短い音声ストーリーでストレス解消 |
| ja | Keywords | 呼吸,リラックス,ストレス解消,瞑想,安眠,マインドフルネス,ガイド付き,睡眠,不安解消,呼吸法 |

---

## Age Rating

All 22 items: None / No (no violence, no adult content, no gambling, no drugs)

---

## Review Information

| Field | Value |
|-------|-------|
| Demo Account Required | No |
| Notes | "BreathStory is a breathing exercise app with narrative audio stories. Free tier: 3 stories. Premium: unlimited stories, $7.99/month or $49.99/year with 7-day trial. No login required." |
| Contact: First Name | (from .env: REVIEWER_FIRST_NAME) |
| Contact: Last Name | (from .env: REVIEWER_LAST_NAME) |
| Contact: Phone | (from .env: REVIEWER_PHONE) |
| Contact: Email | (from .env: REVIEWER_EMAIL) |

---

## Privacy Policy

URL: https://anicca.ai/privacy

**Data collected:**
- Purchase history (RevenueCat — subscription status only)
- No personal data, no analytics, no tracking

---

## Post-Submission Checklist

| # | Task |
|---|------|
| 1 | Slack #metrics: "BreathStory submitted — WAITING_FOR_REVIEW" |
| 2 | Monitor review status daily |
| 3 | If rejected: read rejection reason → fix → resubmit same day |
| 4 | On approval: Slack #metrics: "BreathStory APPROVED — live in X hours" |

---

## Build Upload Command

```bash
# Source env and unlock keychain
source ~/.config/mobileapp-builder/.env
security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db

# Build + upload via Fastlane
cd BreathStoryios && fastlane release
```

Evidence required: `asc builds list --app $APP_ID | head -5` → `processingState=VALID`
