# Q5 SN: server-truth decision — 2026-11-16

## Decision and evidence boundary

The decided path is RevenueCat receiving App Store Server Notifications V2 and
normalizing them, with the client re-reading authoritative CustomerInfo as the
app-side application mechanism. This is a design decision, not evidence that the
external configuration is deployed. The own-backend relay is NOT implemented by
this change; no working notification relay is evidenced in this checkout.
ASC / RevenueCat dashboard state is unverified from code.

The current client integration learns usage only from the own server and does
not overwrite entitlement state (plan/status): `syncUsageInfo` merges only monthly
usage fields. Preserve that separation. The own server is not an evidenced
notification-driven entitlement authority in this decision.

**Source/spec discrepancy:** the reference spec's blanket statement that the
server never learns entitlement state is stronger than the code supports.
`syncNow()` already POSTs to `billing/revenuecat/sync`; its comments say that the
backend re-fetches RevenueCat state for APNs limits. That request is not a
notification relay, and its implementation/deployment is unverified here. We do
not remove it or claim that the backend only stores usage globally. The
usage-only statement above describes what the app imports from the server.

## External follow-up (not completed)

Read back ASC Production and Sandbox notification URLs and version, RevenueCat
store-notification settings and webhook configuration. Record destination,
environment and successful test delivery without credentials. Keep Production
and Sandbox separated; a sandbox receipt is not production evidence. Both
coverage and environment/signature checks remain unverified.

Decide the own-backend relay and its owner after that readback. Any future
receiver must authenticate before trusting payloads, independently verify nested
Apple transaction/renewal JWS when applicable, validate app/environment, persist
before ack, deduplicate by event ID and apply an authoritative current-state
re-read rather than arrival order. Confirm the actual provider authentication
contract before implementation; this document adds no receiver or decoder.

Recovery to implement with the relay: Apple V2 production retries occur after
1, 12, 24, 48, 72 hours **after the preceding attempt**; Sandbox has no retries.
Use Get Notification History and periodic reconciliation against current
store/RevenueCat state for missed notifications after retries end. Define a
schedule, replay/dedup evidence and event ledger there. None runs in this change.
Verify Request a Test Notification end-to-end in both environments and cover
price-consent/offer transitions before claiming SN-3 completion.

## Client freshness and verification

`.informational` reports verification failures as information and does not block
access. This deliberate tradeoff is not enforcement. No timestamp here means
cryptographic verification succeeded.

`SubscriptionManager.lastCustomerInfoRequestAt` exposes the request date on the
last observed CustomerInfo. It is not the time a cached value was replayed.
`isEntitlementStale` is true when unknown, future-dated (clock skew), or at least
72 hours old. The value starts unknown each process launch; there is no separate
persisted freshness marker that could accidentally carry across users/relaunches.
Stream, delegate, explicit refresh and promoted-purchase observations update it.

Launch and foreground use the existing `.fetchCurrent` refresh. Failed refreshes
do not advance the date or change access. Staleness is an exposed diagnostic flag,
not an automatic access cutoff or extension: premium derivation remains the
existing CustomerInfo-based path. A device remaining offline can therefore still
show its previous access; the checker pass means bounded **staleness reporting
and revalidation**, not offline revocation enforcement.

Local subscription diagnostics include `customer_info_request_at` and
`entitlement_stale`. These are not a server event ledger or a measured divergence
rate. All three SN-5 fields remain false.

## Reproduction and limits

The adjacent `server-notifications-state-2026-11-16.json` records source-supported
state. Run the external `~/workspace/tools/server-notifications-check/server_notifications_check.py`
against it. Only SN-0 decision and the two SN-4 gaps change from the supplied
baseline: **17 → 14 FAIL**. External unknowns stay false. Existing lifecycle and
refund/revoke passes retain the spec's client-side-only interpretation.

Run `python3 apps/mobile/anicca-ios/scripts/tests/test_server_notifications_wiring.py`
for static wiring checks. They do not execute Swift or certify a deployed endpoint.
No Xcode build is possible on this VM. The referenced Superpowers skill directory
was absent; the assignment explicitly permits direct work. Starting checkout:
`codex/q5-server-notifications`, HEAD `a553a6e42`, origin `Daisuke134/anicca`.
The assignment mentions FS `8cdcfc07d`, but it is not an ancestor of the starting HEAD; this
change preserves the assigned branch and does not import another branch.

## Primary references

- [RevenueCat CustomerInfo](https://www.revenuecat.com/docs/customers/customer-info): request date is the server date of the fetch.
- [Trusted Entitlements](https://www.revenuecat.com/docs/customers/trusted-entitlements): informational verification and cached data limitations.
- [Apple retry handling](https://developer.apple.com/documentation/appstoreservernotifications/responding-to-app-store-server-notifications): retry ladder and recovery.
- [ASC notification URLs](https://developer.apple.com/help/app-store-connect/configure-in-app-purchase-settings/enter-server-urls-for-app-store-server-notifications/): environment configuration.

## Validation results

- New SN static wiring: 6/6 PASS (initial red: 3 failures + 2 missing-file errors;
  decoder-absence check already passed).
- Python discovery: 50 tests, 46 passed, 2 skipped, 2 pre-existing failures.
  `test_free_onboarding_completes_without_a_network_or_purchase_gate` rejects the
  existing refresh call; `test_primary_offer_and_alternatives_do_not_have_competing_scroll_regions`
  expects an absent `paywall-other-plans` identifier. Re-running all 23 paywall
  tests with source reads taken from starting HEAD reproduced exactly those two
  failures; the affected source/tests are unchanged here.
- Checker fixtures: compliant PASS/exit 0; anicca-source FAIL 17/exit 1;
  contrast-decode-only FAIL 20/exit 1. Post-change state: FAIL 14/exit 1.
- `git diff --check`: PASS. No Xcode build, native Swift tests, dashboard changes,
  test-notification delivery, push or merge performed.
