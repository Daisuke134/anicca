# Unfinished transaction decision — 2026-11-16

RevenueCat is the sole finishing owner. Its default is now explicit at
SubscriptionManager.configure: purchasesAreCompletedBy = .revenueCat.
The builder requires a storeKitVersion argument; .default preserves the existing
SDK selection. Switching to .myApp is forbidden without an implementation that
verifies delivery before finishing, and a separate storeKitVersion decision.

The Xcode project's project.xcworkspace/xcshareddata/swiftpm/Package.resolved
pins purchases-ios 5.78.0, revision 629a56ecef190469914b8f0914bf0446363eb09f.
The repository-root mobile Package.resolved is for tooling, not the app SDK.
The pinned upstream [Configuration.swift](https://github.com/RevenueCat/purchases-ios/blob/629a56ecef190469914b8f0914bf0446363eb09f/Sources/Purchasing/Configuration.swift#L218-L232)
was read: lines 135–143 map .revenueCat to observerMode=false and record the
default; lines 225–231 implement the explicit builder API used here.
This proves configuration support, not production finishing.

Platform facts from the handoff spec: unfinished transactions stay queued and
are redelivered on every launch until finished. A crash between payment and
finish creates unfinished work. For a consumable, an unfinished transaction can
block repurchase of that product. For a subscription or non-consumable,
redelivery can re-fire delivery. Anicca currently offers subscriptions and a
lifetime non-consumable; consumables are a future-design constraint.

All current purchases use Purchases.shared.purchase; there is no direct StoreKit
purchase path. Delivery is idempotent: access is re-derived from CustomerInfo.
The delegate updates entitlement state and does not double count redelivery as a
new purchase/revenue event. No app transaction finish call is added.
The existing informational entitlement verification policy remains unchanged;
the app cannot establish verified-delivery-before-finish for RevenueCat here.

No vendored Pods/SPM SDK source or configure-time drain proof was found in this
checkout. The upstream configuration evidence above does not prove a drain.
Instead AppDelegate schedules an observation after analytics configuration on
launch and on applicationDidBecomeActive. SubscriptionManager scans
StoreKit.Transaction.unfinished, serializes overlapping scans, and emits
unfinished_transactions_observed through the existing AnalyticsManager.
UI testing/configuration-skipped runs do not scan.

The event contains reason, unfinished_count, oldest_dwell_seconds (nonnegative
age since purchaseDate, zero for an empty snapshot), unverified_count, and
finishing_owner. Age includes unverified metadata and is therefore untrusted
when unverified_count is nonzero. Purchase age is a dwell proxy, not a measured
time of entry into the queue. SDK finishing can race the snapshot. Overlapping
launch/foreground scans coalesce; neither blocks UI or grants access.
An unverified result is counted only, never treated as releasable or delivered.
No transaction IDs, product IDs, receipts, or verification errors are emitted.

This is observation, NOT a drain: both UF-3 booleans remain false. Finish failure
counts are unavailable from this integration; finishing_failures_status is
unobservable, never a fabricated zero. The event can be compared with the
existing purchase_started denominator, but no /open dashboard or provider
receipt was verified. Count/age instrumentation exists in source; actual
on-device values and analytics delivery have not been measured.

The adjacent JSON is an honest source-state input for unfinished_check.py.
Expected remaining FAIL count: 6 — UF-2 verified delivery/finishing and
unverified safety (2), UF-3 launch/foreground drain (2), UF-4 permanent-block
recovery (1), UF-5 finishing failures (1). The observer alone cannot clear them.
No on-device force-quit redelivery test was done. RevenueCat production
finishing is not verifiable from this repo. Xcode build and SDK execution were
not performed on this VM.

Validation uses scripts/tests/test_unfinished_transaction_wiring.py and the
external checker fixtures. Static contracts are not runtime proof.
The referenced Superpowers skill is absent and Astra Advisor is not exposed;
the assignment permits proceeding directly. Existing lifecycle/analytics and
Python wiring-test patterns were reused without dependencies. The Life Manager
source-boundary script rejects this Anicca checkout; the explicit assignment
overrides that stale repository identity. Team docs also describe a hard
paywall while the current app implements a soft paywall; neither is changed.

Recorded validation:
- New wiring tests: 4 passed (before implementation: 1 failure, 2 errors).
- Python unittest discovery: 48 run, 44 passed, 2 skipped, 2 failed.
  Existing paywall tests test_free_onboarding_completes_without_a_network_or_purchase_gate
  and test_primary_offer_and_alternatives_do_not_have_competing_scroll_regions
  also fail when reading unchanged HEAD sources (23 baseline paywall tests,
  the same 2 failures). Their assertions disagree with existing onboarding
  CustomerInfo refresh and paywall presentation; no related source was changed.
- Checker fixtures: compliant PASS/exit 0; anicca-source FAIL 12/exit 1;
  contrast-finish-first FAIL 15/exit 1.
- Adjacent app-state JSON: FAIL 6/exit 1, as enumerated above.
- git diff --check passed. No Xcode build, push, merge, or production mutation.
