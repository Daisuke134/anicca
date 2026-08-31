# Mr.bot iOS Sync, APNs, Maestro, and TestFlight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the same durable chat works through launch, foreground, refresh, and production APNs; automate both locale journeys in staging; and close the real TestFlight product and cost receipts.

**Architecture:** Every wake path calls the same cursor sync function. APNs contains only a stable message ID and cursor hint, then the client fetches the authenticated outbox and scrolls to that message. The backend sends production/sandbox APNs based on registered environment and removes invalid tokens. Maestro obtains a one-use staging callback code through an operator CLI and exercises the real staging API without a product test bypass. Real Google OAuth, production APNs, provider routing, calls, and deletion are verified on TestFlight.

**Tech Stack:** SwiftUI scene phase, UserNotifications, APNs HTTP/2 JWT, Node.js, Supabase, XCTest, `node:test`, Maestro, Fastlane, TestFlight, provider dashboards.

## Global Constraints

- TestFlight uses production APNs. Xcode device builds never point at the production API.
- Notification receipt never directly creates a chat message; the durable outbox is authoritative.
- Device registration uses bearer auth and idempotency. APNs token is never accepted as user identity.
- Google consent/account chooser is excluded from Maestro and verified manually on TestFlight.
- Maestro uses the real staging API and a pre-authorized tenant; production app code has no test login or fake route.
- Production TestFlight enrollment remains blocked until DAILY Gate 0 is deployed and verified.

## File Structure

| File | Change |
|---|---|
| `apps/mr-bot-ios/MrBot/App/AppDelegate.swift` | APNs registration callbacks and notification tap forwarding |
| `apps/mr-bot-ios/MrBot/Services/DeviceService.swift` | Authenticated APNs PUT/DELETE |
| `apps/mr-bot-ios/MrBot/Services/ChatSyncCoordinator.swift` | One launch/foreground/manual/push sync path |
| `apps/mr-bot-ios/MrBot/Models/NotificationDestination.swift` | Stable message/cursor payload decoder |
| `apps/mr-bot-ios/MrBotTests/ServiceTests/*Push*Tests.swift` | Token, payload, dedupe, deep-link tests |
| `apps/mr-bot/lib/apns-client.js` | JWT/HTTP2 sender with production/sandbox host |
| `apps/mr-bot/lib/mobile-push.js` | Outbox-message notification orchestration |
| `apps/mr-bot/test/mobile-apns-contract.test.js` | Device auth, payload, invalid-token cleanup |
| `apps/mr-bot/scripts/create-staging-mobile-session.js` | Operator-only one-use callback code for Maestro |
| `apps/mr-bot-ios/maestro/config.yaml` | Fail-fast flow configuration |
| `apps/mr-bot-ios/maestro/english-onboarding-route.yaml` | Required English real-staging journey |
| `apps/mr-bot-ios/maestro/japanese-onboarding-route.yaml` | Required Japanese real-staging journey |
| `apps/mr-bot-ios/maestro/push-deep-link.yaml` | Stable-message push journey |
| `apps/mr-bot-ios/fastlane/Fastfile` | TestFlight archive/upload lanes |

### Task 1: Unify Launch, Foreground, and Manual Sync

**Interface:**

```swift
actor ChatSyncCoordinator {
    func sync(reason: SyncReason, targetMessageID: String? = nil) async
}
enum SyncReason { case launch, foreground, manual, push }
```

- [ ] Write tests showing all four reasons call `ChatServicing.fetch(after:)`, concurrent triggers coalesce, cursors advance monotonically, stable IDs dedupe, and errors remain visible without cursor loss.
- [ ] Record RED, then move launch/manual behavior into one coordinator and connect `scenePhase == .active`.
- [ ] Preserve chat scroll unless a push supplies a target stable message ID.
- [ ] Run sync/view-model tests and commit/push.

### Task 2: Register Devices and Deliver the Stable Outbox Message

- [ ] Add Swift tests for permission state, 32-byte token to 64-hex conversion, authenticated PUT/DELETE, locale/timezone/environment metadata, token replacement, and logout cleanup.
- [ ] Add Node tests for 64-hex validation, server-derived tenant, idempotency, sandbox/production host, collapse ID, APNs ID/reason logging, and invalid-token removal.
- [ ] Define payload `{ "type":"chat_message", "messageId":"<stable>", "cursor":"<opaque>" }`; reject UID, route details, Calendar content, and access tokens in payload.
- [ ] Record RED in Swift and Node suites.
- [ ] Register only after notification permission, send device state through `DeviceService`, and wire app delegate callbacks into the sync coordinator.
- [ ] Send APNs only after the semantic outbox row commits. A tap syncs the outbox and scrolls to `messageId`; refetch cannot duplicate it.
- [ ] Re-run suites, test local notification routing in simulator, and commit/push.

### Task 3: Build Deterministic Real-Staging Maestro Flows

- [ ] Add `config.yaml` with fail-fast flows and exact file names from the approved spec.
- [ ] Add stable leaf accessibility IDs to every assertion target; use `extendedWaitUntil` for real API phases and optional handling only for OS-owned dialogs.
- [ ] Implement an operator CLI that uses staging service credentials to create a one-use callback code for a pre-authorized staging tenant. It prints no bearer/refresh token and has no HTTP route in production.
- [ ] English flow: clear state/Keychain → one-use callback → name/home → skip phone → analysis → route card → detail → soft paywall → continue free → settings; capture milestone screenshots.
- [ ] Japanese flow: repeat with `product_locale=ja`; assert the Japanese landmarks and absence of English product labels.
- [ ] Push flow: seed a real semantic outbox message, deliver a local/sandbox notification payload, open the stable message, then refresh and assert one copy.
- [ ] Run the flows with Maestro's interactive integration locally and CLI in CI; store videos/screenshots as CI artifacts outside Git.
- [ ] Commit/push flow definitions and accessibility-only fixes.

### Task 4: Produce a Signed TestFlight Build

- [ ] Add app-local Fastlane `build_for_testflight` and `upload_testflight` lanes with App Store Connect API-key authentication, explicit project/scheme/bundle, export method, build-number increment, and processing timeout handling.
- [ ] Add the aps-environment entitlement only in the signed configuration and verify it resolves to production for TestFlight.
- [ ] Run `bundle exec fastlane test`, `build_for_simulator`, then `build_for_testflight`.
- [ ] Inspect archive signing, bundle ID, minimum OS, privacy manifest, URL scheme, encryption flag, and embedded entitlements.
- [ ] Upload to TestFlight, wait until the build is `VALID`, attach tester notes, and install it on the real device.
- [ ] Record build/version/ASC identifiers and commit/push only configuration/metadata, never credentials or archives.

### Task 5: Close the Real TestFlight Matrix

- [ ] Verify DAILY row #5 deployment receipt before adding the tester to the production build.
- [ ] Real Google OAuth: connect one account, complete callback, relaunch, and confirm session restoration.
- [ ] Real Calendar: save name/home, skip phone, keep `paid=false`, analyze a controlled physical event, and verify an event-anchored English route with provider attribution/freshness.
- [ ] Verify collapsed card, same-data detail sheet, soft paywall free path, manual refresh, foreground refresh, and zero duplicate messages.
- [ ] Switch to Japanese and verify complete re-projection of product text and historical semantic messages while Calendar-authored content stays unchanged.
- [ ] Register production APNs, append one new semantic message, receive the push, tap it, open the stable chat message, and verify subsequent fetch does not duplicate it.
- [ ] Add a valid phone, explicitly enable calls, confirm one test call, and inspect durable cooldown/global cap plus Telnyx CDR/ledger receipt.
- [ ] Delete the account, inspect provider disconnect and backend deletion receipt, and prove revoked tokens cannot bootstrap.
- [ ] Inspect Google, Transit, Composio, Gemini, Telnyx, Resend, Railway, and Supabase cost rows; separate measured, estimated, fixed, and unknown.
- [ ] Update Gate 7–9 receipts in the approved spec with device/build/provider evidence, commit, and push.

### Task 6: Integrated Review and Regression

- [ ] Run every mobile backend contract, provider-cost suite, Swift XCTest, and three Maestro flows.
- [ ] Run the full backend suite against its clean installed baseline.
- [ ] Give one fresh Sol reviewer the integrated diff, spec, test evidence, and cost evidence; request only correctness/safety findings.
- [ ] Fix each in-scope finding, repeat affected tests and real receipts, then close review.
- [ ] Merge without rolling back newer main commits and verify Railway production commit/build identity.

## Verification Commands

```bash
cd apps/mr-bot
node --test test/mobile-apns-contract.test.js test/mobile-chat-cursor.test.js test/mobile-v1-surface-contract.test.js

cd ../mr-bot-ios
bundle exec fastlane test
maestro test maestro/english-onboarding-route.yaml
maestro test maestro/japanese-onboarding-route.yaml
maestro test maestro/push-deep-link.yaml
bundle exec fastlane build_for_testflight
git diff --check
```

All local/staging commands pass before upload. The TestFlight lane produces a signed archive; production APNs and real OAuth are separate real-device receipts and cannot be replaced by simulator success.
