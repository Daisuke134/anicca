# Pending Purchase gate — 2026-11-16

Code-side implementation only. No release, push, merge, Xcode build or Sandbox
Ask to Buy simulation (`simulatesAskToBuyInSandbox`) was performed.

## Decision and platform contract

Purchase results are **success / cancelled / failed / pending**. Pending is a
fourth outcome, not a failure, cancellation, successful purchase or revenue.
Causes include Ask to Buy (parent/guardian approval), SCA (bank authentication),
and cash payment methods such as convenience-store payment in Japan (payer
must complete payment). The SDK does not identify which cause applies; the six
localized messages describe conditional next steps rather than guessing.

A pending purchase cannot be cancelled in app code and can resolve days later,
including after 30 days. Do not expire a marker by age or encourage a duplicate
purchase. Access unlocks through the existing CustomerInfo entitlement path,
never through the pending marker.

Sources:
- [RevenueCat error handling](https://www.revenuecat.com/docs/test-and-launch/errors)
- [RevenueCat pending-state limitations](https://community.revenuecat.com/sdks-51/how-to-know-at-any-moment-if-the-purchase-of-a-product-is-deferred-1646)
- [RevenueCat pending error](https://community.revenuecat.com/sdks-51/understanding-payment-pending-error-2162)
- [CustomerInfo API](https://github.com/RevenueCat/purchases-ios/blob/main/api/revenuecat-api-ios.swiftinterface)
- [CustomerInfo updates](https://www.revenuecat.com/docs/customers/customer-info)

## Implementation and reuse

Reuse `PurchaseObservationLedger`'s UserDefaults persistence pattern and
`SubscriptionManager.refreshCustomerInfo()`'s `.fetchCurrent` mechanism.
No dependencies, new source targets, server ledger or parallel purchase owner.

Both PaywallVariantBView.purchase and RetentionOfferSheet.acceptOffer classify
`paymentPendingError` before cancelled/generic failure. They persist product ID,
start time, flow, original CustomerInfo user ID and the previous product purchase
date; show neutral inline information; and disable/guard the same product's CTA.
Neither pending branch calls a success callback or starts a retention offer.
Cancellation in the retention sheet no longer displays a raw error alert.

Each purchase obtains a fresh CustomerInfo baseline before calling purchase.
If that read fails, the attempt takes the existing failed path without submitting
a purchase. This adds a network prerequisite deliberately: old purchases must
not be mistaken for resolution. The provider purchase timestamp is compared
only to the provider baseline, not to the device clock. A different original
CustomerInfo user cannot clear the record. Markers remain device-local and block
the same product across app-account switches conservatively; reinstall, another
device, or a store-account switch is not a globally durable pending ledger.

Published markers restore at manager initialization. After SDK configuration,
after recording pending, and on scene activation, pending records trigger a
fresh CustomerInfo read. The delegate, stream and explicit refresh all reconcile
positive evidence: matching original user and a first/newer product purchase.
This also handles an already-expired completed purchase without granting access.
Persistence is updated before emitting `pending_purchase_resolved`, avoiding
ordinary delegate/stream double counting. Missing/failed reads retain markers.
A missing baseline cannot resolve speculatively. CustomerInfo continues to be
the sole entitlement authority.

Analytics: existing `purchase_started` remains the funnel denominator;
`purchase_result` now has `result=pending`. `pending_purchase_resolved` carries
`result=confirmed`, `product_id`, originating `flow_id`, and `pending_seconds`.
It is a client observation, not an extra sale or revenue event. Delivery is not
transactional with UserDefaults: process death between persistence and analytics
can lose an event. No claim of exactly-once server accounting. `/open` dashboard
columns are outside this code-side handoff and were not changed.

## Honest remaining boundary: PP-4 denial without callback

A fresh CustomerInfo without a purchase cannot distinguish denied Ask to Buy
from a request still waiting for approval/payment. Clearing on that evidence or
on a timeout would permit a duplicate while the original can still complete.
Therefore confirmation resolves and clears, but denial without callback remains
unknown and blocked. There is no fabricated refusal event, timeout cancellation,
or user-facing retry/reset. A verified platform/store recovery path is still
needed for denied requests; this implementation does not solve that boundary.
The state JSON deliberately sets `foreground_recheck_clears_or_resolves=false`
for the full denial-recovery gate, although positive foreground resolution is
wired. Remaining checker **FAIL 1**, not a full PP pass.

## Repository discrepancies and workflow

The assigned worktree origin is Daisuke134/anicca and branch is
codex/q5-pending-purchase. Root instructions name Life Manager; the explicit
assignment overrides that mismatch. Starting HEAD was a553a6e42, not SN
878a414ad. That SN commit exists as a Git object but is not an ancestor of this
branch; its gate files were read with `git show` as the documentation pattern.
No SN cherry-pick or merge was performed. PP supplies its own required launch
and scene recheck using existing mechanisms. Team docs describe a hard paywall,
whereas current app/test conventions include optional purchase flows; pricing
and access policy were not changed.

Astra Advisor is not exposed here. Applied installed Superpowers
using-superpowers, brainstorming (explicit no-question exception),
test-driven-development and verification-before-completion skill texts under
`/home/hatch/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills/`.
Initial wiring tests failed before implementation. Independent read-only review
identified device/server clock comparison and missing owner correlation; both
were fixed with a fresh provider baseline and owner match, then checked again. A subsequent review caught a storefront-check race introduced
by the baseline fetch; that fetch now precedes the existing storefront/package
validation, covered by another regression wiring test.

## Validation

- `python3 apps/mobile/anicca-ios/scripts/tests/test_pending_purchase_wiring.py`:
  8/8 PASS. Static wiring contracts only, not Swift execution.
- `python3 -m unittest discover -s apps/mobile/anicca-ios/scripts/tests -p 'test_*.py'`:
  52 tests: 48 PASS, 2 skipped (toolchain-dependent), 2 pre-existing failures below.
- App state checker: FAIL 1 (exit 1), PP-4 denial recovery as described above.
- `git diff --check`: PASS. Final independent read-only review: 0 findings;
  all three findings across review rounds fixed.
- Baseline paywall suite run using `git show HEAD:<path>` source reads: 23 tests,
  2 failures, both reproduced before this change:
  `test_free_onboarding_completes_without_a_network_or_purchase_gate` and
  `test_primary_offer_and_alternatives_do_not_have_competing_scroll_regions`.
  The old tests expect flows/UI absent from the starting tree; unrelated fixes
  were not folded into PP.
- Checker fixtures: compliant PASS (exit 0); anicca-source FAIL 13 (exit 1);
  contrast-grant-on-pending FAIL 13 (exit 1).
- Native compiler, Xcode, device UI, actual pending purchases, relaunch during
  approval, denial and delayed conversion delivery remain unverified.
