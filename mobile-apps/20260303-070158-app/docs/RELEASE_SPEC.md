# MindSnap — Release Specification

**App:** MindSnap: AI Daily Check-in
**Bundle ID:** com.anicca.mindsnap
**Initial Version:** 1.0.0
**Target:** App Store (iOS 18+)

---

## App Store Connect Setup

| Item | Value |
|------|-------|
| App Name | MindSnap: AI Daily Check-in |
| Bundle ID | com.anicca.mindsnap |
| SKU | mindsnap-001 |
| Primary Language | English (U.S.) |
| Category | Health & Fitness |
| Secondary Category | Lifestyle |

---

## Subscription Products

| Product ID | Display Name | Price | Duration |
|------------|--------------|-------|----------|
| `mindsnap_monthly_499` | MindSnap Monthly | $4.99 | 1 month |
| `mindsnap_annual_2999` | MindSnap Annual | $29.99 | 1 year |

**Subscription Group:** MindSnap Premium
**Free Trial:** Both products: 7-day free trial

---

## RevenueCat Configuration

| Item | Value |
|------|-------|
| Offering ID | `default` |
| Monthly package | `$rc_monthly` → `mindsnap_monthly_499` |
| Annual package | `$rc_annual` → `mindsnap_annual_2999` |
| Entitlement | `premium` |

---

## Age Rating

All 22 items: None/Infrequent (age rating: 4+)

---

## Compliance

| Item | Answer |
|------|--------|
| Encryption | NO — no encryption used |
| Content Rights | DOES_NOT_USE_THIRD_PARTY_CONTENT |
| App Privacy | No data collected |
| ATT | Not used |

---

## Pre-Submission Checklist

| Gate | Command | Pass Criteria |
|------|---------|---------------|
| Greenlight preflight | `greenlight preflight MindSnapios/` | CRITICAL=0 |
| PrivacyInfo | Inspect MindSnapios/PrivacyInfo.xcprivacy | UserDefaults + CA92.1 |
| Build | `fastlane build` | IPA created |
| ASC validate | `asc validate` | Errors=0 |
| Subscription state | `asc subscriptions list` | state≠MISSING_METADATA |
| No Mixpanel | `grep -r Mixpanel --include='*.swift' .` | 0 results |

---

## Build & Submit

```bash
# 1. Archive + Upload
source ~/.config/mobileapp-builder/.env
security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db
cd MindSnapios && fastlane release

# 2. Submit for review
fastlane submit_review
```
