# Family Sharing decision — 2026-11-16 (Q5 / FS-0)

## Decision

Keep Family Sharing **OFF for now for each product below**. This is an explicit product decision, not an inference from a default configuration. Do not turn it on in App Store Connect as part of Q5.

**Irreversibility:** Apple states that once Family Sharing is turned ON for a product, it cannot be turned OFF again. This applies per product, including eligible non-consumables and auto-renewable subscriptions. Up to five additional family members can share a purchase.

| Product | Decision | Reason | ASC live state |
| --- | --- | --- | --- |
| `ai.anicca.app.ios.lifetime` | OFF for now | Preserve separate lifetime sales; one payment could otherwise fund ongoing access for up to six people without recurring revenue. | Unverified |
| `ai.anicca.app.ios.yearly.b` | OFF for now | Preserve annual revenue per paying member until retention and referral gains justify household consolidation. | Unverified |
| `ai.anicca.app.ios.monthly.b` | OFF for now | Preserve monthly revenue per paying member while household conversion and retention effects remain unknown. | Unverified |
| `ai.anicca.app.ios.weekly.b` | OFF for now | Preserve weekly revenue per paying member; there is no measured evidence that sharing offsets displaced purchases. | Unverified |

## Revenue tradeoff and estimate

Sharing can increase family engagement, retention, loyalty and word-of-mouth, but can reduce purchases per household and increase service usage per payment. We currently prioritize protecting household revenue because the offsetting gains have not been measured. This does not assert that OFF maximizes long-term revenue.

Illustrative gross-revenue sensitivity, not a forecast: if `n` household members would independently buy the same product at price `P`, OFF yields `n × P` and ON could yield `P`, a reduction of `(n − 1) × P`. Two otherwise-paying members imply a 50% reduction; six imply 83.3%. If only one member would pay anyway, direct displaced revenue is zero. Taxes, fees, churn, refunds, referrals and incremental service costs are excluded.

Using local StoreKit display prices only (not verified live prices), the two-paying-member case is: lifetime 199.98 → 99.99 once; yearly 79.98 → 39.99 per year; monthly 19.98 → 9.99 per month; weekly 15.98 → 7.99 per week, in configured price units. Actual household purchase propensity, net revenue and retention lift are unknown. Do not book these examples as revenue or losses.

Same-niche winner evidence (including I am) is **not verified in this task**. No competitor sharing policy is claimed or inferred. Before reconsidering ON, obtain dated product-level competitor observations, actual household economics, and retention/referral evidence sufficient to offset displaced revenue and service costs. Missing evidence supports deferring this irreversible change, not assuming competitors are OFF.

## Evidence boundary and remaining gate work

`aniccaios/Anicca.storekit` has `familyShareable: false` for all four products. It describes local test configuration only. **ASC live state is not verified from code.** This decision does not establish the current store setting and does not claim to turn an already-enabled product OFF. No ASC setting was changed. FS-0 remains incomplete until an authorized live readback records each product's setting, timestamp and evidence; if any is already ON, record the discrepancy and respect irreversibility.

The preserved Q5 implementation conditionally displays the localized callout from each Package's `isFamilyShareable`, maps purchased/shared ownership, exposes an identity-scoped education-needed flag with acknowledgement, and permits purchase analytics only for matching PURCHASED entitlements. Existing optional decoding preserves older subscription caches. The education flag is preparation: no consuming education screen was added here. Shared-cohort analytics, introductory-offer verification, actual grant/revoke behavior and real-family testing remain outside this bounded retry. Do not mark the whole FS gate passed from source wiring checks.

## Validation and provenance

- Reviewed the preserved diff on `codex/q5-family-sharing`, base `a553a6e42`; retained its implementation and six locales.
- `python3 apps/mobile/anicca-ios/scripts/tests/test_family_sharing_wiring.py`: 4 tests PASS. These are static source contracts, not Swift/RevenueCat runtime tests.
- External `family-check/family_check.py` fixtures: compliant PASS (exit 0), historical `anicca-source` FAIL 10 (exit 1), negative contrast FAIL 13 (exit 1). Fixtures were not modified; the historical fixture does not inspect current source.
- Adjacent checks: analytics-provider contract fails on missing `onboardingStepCompleted`; paywall-selection wiring has 21 passes / 2 failures (free-onboarding network gate and competing scroll regions). All three failures reproduce unchanged in an isolated archive of base `a553a6e42`; they are pre-existing and outside Q5. Temporary baseline files were removed.
- `git diff --check`: PASS.
- Xcode build and real-device/provider readback were not run on this VM.
- Read installed `superpowers:using-superpowers` and `superpowers:verification-before-completion`. The Life Manager source-boundary script rejects this assigned Anicca path; the explicit assignment overrides that repository/path restriction. Astra Advisor is not exposed by this harness; direct review and focused verification were used.

Basis: supplied `family-sharing-gate-spec-2026-11-15.md`, FS-0 and its cited [Apple guidance](https://developer.apple.com/help/app-store-connect/configure-in-app-purchase-settings/turn-on-family-sharing-for-in-app-purchases) and [RevenueCat guide](https://www-docs.revenuecat.com/blog/engineering/implement-apple-family-sharing/). External guidance was supplied in the specification; no fresh live-store verification is implied.
