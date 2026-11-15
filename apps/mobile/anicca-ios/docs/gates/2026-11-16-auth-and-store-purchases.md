# Apple authentication and store-origin purchase audit

Source changes on `codex/app-gates-2`; no push or deployment. This is a source audit, not App Review approval or a production receipt.

## Authentication

Settings exposes Apple's native, adaptive black/white SignInWithAppleButton at 50 points high. Authentication stays optional for anonymous use and purchases. The button remains mounted while the sheet is active; it does not replace its presenting view with the router's loading screen.

AuthCoordinator requests fullName/email and sends the existing SHA-256/base64 nonce contract, identity token, authorization code, Apple subject, first-grant profile fields and device-id to `POST auth/apple`. Only a successful response containing a backend user ID, access token and refresh token creates a local authenticated session. Backend IDs and Apple subjects are stored separately. No email-based account merge is attempted.

Credentials migrate from UserDefaults to Keychain. Existing records without an Apple subject lose their session tokens and require reauthorization, while keeping profile/name/email. Returning authorization preserves missing first-grant fields only for the same Apple subject; legacy metadata is reused only after the backend confirms the same account ID. First-grant data is saved before the network request, so a failed request does not discard Apple's one-time name/email. A verified different account clears the previous profile after secure credential persistence succeeds.

Launch, foreground and credential-revoked notifications query Apple. Authorized sessions continue. Revoked/notFound sessions clear credentials, refresh tokens, first-grant cache, shared user ID and the existing local profile/onboarding state. Transferred/unknown states require fresh authorization; no subject migration is invented locally. A failed state query is not treated as revocation. Sign-out invalidates outstanding sign-in work; token-refresh and profile-bootstrap responses cannot restore a signed-out account.

Settings also exposes the existing legacy `DELETE mobile/account` route. Authentication is required; only a 204 response for the current user triggers local wipe. The confirmation states that deleting an account does not cancel an App Store subscription. Actual server deletion and Apple token revocation are not verified here.

`apple_sign_in_started` and `apple_sign_in_result` count started/succeeded/cancelled/failed attempts without token or profile payloads. Cancellation is not displayed as an error.

## Purchases

RevenueCat 5.78.0 is pinned in the Xcode workspace. AppDelegate configures it at launch, explicitly with StoreKit 2 and `purchasesAreCompletedBy: .revenueCat`. SubscriptionManager retains its CustomerInfo stream independently of any paywall. There is no competing app-owned transaction finisher.

RevenueCat's TransactionPoster posts the receipt before finishing accepted subscription transactions. It does not finish offline-computed CustomerInfo; retryable receipt errors remain unfinished. Its callback can occur after finishing: durable RevenueCat entitlement delivery, rather than the timing of a SwiftUI redraw or the optional usage-sync endpoint, is the purchase authority. A backend/RevenueCat entitlement-product configuration audit is still necessary.

Foreground reconciliation runs from the SwiftUI scene, including return from an external code redemption or store offer. `syncPurchases()` results immediately update entitlements. CustomerInfo callbacks perform only backend usage sync, preventing recursive receipt sync. Usage responses merge usage fields into the current subscription instead of overwriting newer entitlement state.

RevenueCat identity changes are serialized. All entitlement application and synchronization require the RevenueCat identity to match the app session; signed-out sessions require an anonymous RevenueCat identity. Promoted purchase continuations survive identity failures in memory and retry on foreground/login/logout. Anonymous users can purchase without opening a paywall. Completion distinguishes cancellation, pending, failure, entitlement granted and no entitlement; only promoted callbacks are labeled `store_purchase_result`. CustomerInfo refreshes are not fabricated as new revenue events.

Channel decisions: App Store promoted IAP, externally redeemed codes, and store-presented offers use the SDK observer. StoreKit messages retain automatic presentation, including billing/price-consent messages. This patch does not add an in-app code redemption sheet, win-back paywall/link, eligibility-filtered message presentation, or a signed promotional-offer purchase API. Introductory offer selection remains in the existing paywall. No ASC offer configuration or paid tool was changed.

## Verification and unresolved gates

- Python source-boundary regressions: 10 passed. The original HEAD fails these regressions. These check wiring/invariants, not StoreKit or Apple server behavior.
- Existing settings sign-out tests: 1 passed, 1 skipped because Swift is absent.
- Six XCTest cases added and registered: first-grant preservation/update/account separation, legacy decode, Apple-subject round trip, actual Keychain update/delete. Not run: this Linux environment has neither Swift nor Xcode.
- `git diff --check`: passed.
- All three added localization keys exist in all six locales. Full localization parity fails on existing key drift, unchanged by this patch.
- Existing analytics contract script fails because onboarding lacks `onboardingStepCompleted`; the same missing call exists in HEAD and is outside this change.
- Independent review: migration data loss, stale RevenueCat identity application, and profile reset before secure persistence were found and corrected. Native compilation remains unverified.

The external Python gate scripts consume human-audited JSON, not Swift source. Checked-in JSON records source evidence conservatively; output files preserve failures rather than claiming an end-to-end pass.

| Checker | Fixture | Result |
|---|---|---|
| siwa-check | current source audit | FAIL 3: backend token flow, server verification, server-side revocation cleanup unverified |
| store-origin-check | current source audit | FAIL 5: ASC evidence, in-app win-back path, entitlement-filtered win-back presentation, in-app code entry, channel-specific outcome measurement |
| mgmt-check | supplied historical `anicca-source.json` | FAIL 8; subscription-management UI/dashboard gate, not a current-source purchase-observer test |

Historical SIWA fixture: FAIL 12. Its client omissions have been addressed; a passing source fixture would still not prove authentication against production.

The repository has no implementation of `auth/apple`, `auth/refresh`, or `DELETE mobile/account` to audit. Server work remains: validate Apple's signature/issuer/audience/expiry/nonce and authorization code, bind the validated subject to a stable backend account, securely retain Apple refresh tokens, retain first-grant data server-side, support subject transfer, invalidate sessions on revocation, and revoke tokens on account deletion. Client request fields alone do not prove those effects.

Before release, build/run XCTest on macOS and exercise fresh/repeated/cancelled sign-in, offline/revoked authorization, logout during requests, and deletion on a device. In StoreKit/sandbox, test a promoted purchase at cold launch without a paywall, offer-code redemption while backgrounded, pending approval, network failure/relaunch, and login/logout failure. Verify entitlement access and no unfinished accepted transaction afterward. Confirm ASC products map to the configured RevenueCat entitlement and obtain backend readbacks.

## Procedure and documentation discrepancies

The assigned origin is `https://github.com/Daisuke134/anicca.git`, root `/home/hatch/workspace/anicca-gates2-wt`, branch `codex/app-gates-2`; common Git directory is `/home/hatch/workspace/life-manager/.git`. The source-boundary script rejects this path under the inherited Life Manager rules. The explicit assignment overrides that mismatch and the dedicated-worktree/push procedure. This work stays on the assigned branch and is committed without push. Team documentation also asks for push; the assignment overrides it.

The referenced `~/.agents/skills/superpowers` path is absent. Later discovery found the installed Superpowers 7.0.1 copy under `~/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills`; using-superpowers and verification-before-completion were read there for final verification. pstack technical-writing was read for this record. No Astra Advisor tool is exposed. Existing Keychain, profile, RevenueCat and legacy deletion paths were reused rather than introducing another auth or purchase SDK.

The supplied subscription-management spec describes status summaries, billing retry and Customer Center configuration; it does not define store-originated purchase observation. The separate existing store-origin-check was therefore also run. No dashboard-management completion is claimed.

## Primary references

- [Apple: verifying a user](https://developer.apple.com/documentation/signinwithapple/verifying-a-user)
- [Apple: credential state](https://developer.apple.com/documentation/authenticationservices/asauthorizationappleidprovider/getcredentialstate%28foruserid%3Acompletion%3A%29)
- [RevenueCat 5.78.0 configuration](https://github.com/RevenueCat/purchases-ios/blob/5.78.0/Sources/Purchasing/Configuration.swift)
- [RevenueCat 5.78.0 receipt posting and finishing](https://github.com/RevenueCat/purchases-ios/blob/5.78.0/Sources/Purchasing/Purchases/TransactionPoster.swift)
