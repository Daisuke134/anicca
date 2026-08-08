# Life Manager iOS Task 1 Report

## Scope

- Worktree: `feat/lm-ios-product`
- Product path: `apps/life-manager-ios/`
- Toolchain: Xcode 26.6 (`17F113`), iOS 26.5 simulator runtime, XcodeGen 2.44.1
- Test target: `LifeManagerTests`

## RED

Command from `apps/life-manager-ios/`:

```text
bundle exec fastlane test
```

Observed result: exit 1 before Fastlane could run. The shell selected macOS system Ruby 2.6 (`/usr/bin/ruby`), while `Gemfile.lock` requires Bundler 4.0.3:

```text
Could not find 'bundler' (4.0.3) required by .../Gemfile.lock.
```

This was a toolchain-path failure, not a Swift test assertion failure.

## GREEN

The same smoke lane was rerun with the installed Homebrew Ruby 4.0.1 and Bundler 4.0.3 explicitly first in PATH:

```text
PATH="/opt/homebrew/opt/ruby/bin:$PATH" bundle exec fastlane test
```

Observed result: exit 0 on the iOS 26.5 simulator.

```text
LifeManagerSmokeTests
✓ testLaunchesLifeManagerInTestEnvironment (19.003 seconds)
Executed 1 test, with 0 failures (0 unexpected)
Test Succeeded
```

The lane builds the app from the generated XcodeGen project and launches `LifeManagerApp` with `-uiTesting` and `LIFEMANAGER_TESTING=1`.

## Task 1 closeout verification

All Task 1 verification commands passed after the GREEN run:

```text
xcodegen generate                         exit 0
PATH="/opt/homebrew/opt/ruby/bin:$PATH" bundle install  exit 0
PATH="/opt/homebrew/opt/ruby/bin:$PATH" bundle exec fastlane build_for_simulator  exit 0
PATH="/opt/homebrew/opt/ruby/bin:$PATH" bundle exec fastlane test  exit 0 (1 test, 0 failures)
git diff --check                          exit 0
```

Generated `.xcodeproj`, DerivedData, and Fastlane reports remain ignored.

## Gate 4 integration follow-up: sync and APNs boundary

The iOS-owned integration slice was verified with the installed Xcode 26.6 and
iOS 26.5 simulator runtime after the Task 1 closeout:

```text
xcodebuild -scheme LifeManager -project LifeManager.xcodeproj \
  -derivedDataPath build/DerivedData \
  -destination 'platform=iOS Simulator,id=32CBF714-48D7-45DC-B3E3-6941C5210F2D' \
  -parallel-testing-enabled NO test
```

Observed result: exit 0, UI 2/2 and unit 54/54, for 56/56 tests with zero
failures. The unit count includes the six AppDelegate permission/token/router
tests and three device/payload tests. The parallel test runner was also
observed to stop in the existing coalescing harness once; the serial command
above is the reproducible green gate.

## Gate 4 signing and TestFlight configuration slice

### RED

The new `SigningConfigurationTests` were run before adding the iOS signing
configuration and TestFlight lanes:

```text
SigningConfigurationTests: 2 tests, 7 failures
```

The failures were the missing Debug/Release APNs entitlement files, missing
iphoneos signing configuration, and missing credential-gated TestFlight lanes.

### GREEN

The slice now has explicit environment-specific entitlements and keeps
simulator/debug builds unsigned while requiring signing for Release iphoneos:

```text
Release + iphoneos:
CODE_SIGNING_ALLOWED = YES
CODE_SIGNING_REQUIRED = YES
CODE_SIGN_ENTITLEMENTS = LifeManager/Config/Release.entitlements

Release + iphonesimulator:
CODE_SIGNING_ALLOWED = NO
CODE_SIGNING_REQUIRED = NO

Debug + iphoneos:
CODE_SIGNING_ALLOWED = YES
CODE_SIGNING_REQUIRED = YES
CODE_SIGN_ENTITLEMENTS = LifeManager/Config/Debug.entitlements

Debug + iphonesimulator:
CODE_SIGNING_ALLOWED = NO
CODE_SIGNING_REQUIRED = NO
```

The TestFlight lanes require `LIFEMANAGER_BUILD_NUMBER` and external
App Store Connect credentials (`ASC_KEY_ID`, `ASC_ISSUER_ID`,
`ASC_API_KEY_PATH`); no credential or archive is committed.

Verification from `apps/life-manager-ios/`:

```text
PATH="/opt/homebrew/opt/ruby/bin:$PATH" bundle exec fastlane build_for_simulator
Build Succeeded

PATH="/opt/homebrew/opt/ruby/bin:$PATH" bundle exec fastlane test
UI tests: 2/2 passed
Unit tests: 60/60 passed
Number of tests: 62
Number of failures: 0
Test Succeeded
```

## APNs deferred-tap follow-up

### RED

The targeted regression test reproduced the lost deep link when a notification
arrived during the initial chat fetch:

```text
xcodebuild ... test \
  -only-testing:LifeManagerUnitTests/ChatViewModelTests/testPushDuringInitialSyncIsRetriedAndAnchorsStableMessage

Executed 1 test, with 3 failures
fetch cursors: [nil] (expected [nil, "cursor-1"])
scroll anchor: nil (expected "message-2")
messages: ["message-1"] (expected ["message-1", "message-2"])
```

### GREEN

`ChatViewModel` now retains the latest push target while a fetch is active,
then drains it through the same cursor coordinator after the active fetch
finishes. If the target is already present, it anchors without a duplicate
fetch.

```text
Targeted regression: 1/1 passed
Full serial xcodebuild: UI 2/2, unit 61/61, total 63/63, failures 0
```

The coalescing test harness now waits until both actor callers have entered
the coordinator before releasing its blocked fetch. This removes the
scheduler-dependent Fastlane stop while preserving the one-fetch assertion.
The final Fastlane verification also exited 0 with 63 tests and 0 failures.

## Fresh review round 1 — API environment and signed Debug configuration

### RED

The built-project inspection reproduced the review finding before the fix:

```text
xcodebuild -project LifeManager.xcodeproj -scheme LifeManager \
  -configuration Debug -sdk iphonesimulator -showBuildSettings
LIFEMANAGER_API_BASE_URL = https:
```

The first regression run was executed after adding the contract tests but before
changing production configuration:

```text
xcodebuild ... test -only-testing:LifeManagerUnitTests/SigningConfigurationTests
Executed 5 tests, with 7 failures (0 unexpected)
```

The failures covered the truncated built URL, missing real staging/production
URLs, missing Debug iphoneos signing, and missing simulator signing overrides.

### GREEN

The app now uses the Railway domains discovered from the read-only project
status, with the mobile v1 prefix required by the frozen API contract:

```text
Debug:   https://life-call-staging-staging.up.railway.app/api/mobile/v1
Release: https://life-call-production.up.railway.app/api/mobile/v1
```

The xcconfig values use `https:/$()/...` so Xcode does not treat `//` as a
comment; the built Info.plist resolves the complete URL. Debug device builds
require the development APNs entitlement and signing, while simulator builds
remain unsigned. The callback scheme is also resolved from the same build
setting in the built Info.plist.

```text
xcodebuild -configuration Debug -sdk iphoneos -showBuildSettings
CODE_SIGNING_ALLOWED = YES
CODE_SIGNING_REQUIRED = YES
CODE_SIGN_ENTITLEMENTS = LifeManager/Config/Debug.entitlements

xcodebuild -configuration Debug -sdk iphonesimulator -showBuildSettings
CODE_SIGNING_ALLOWED = NO
CODE_SIGNING_REQUIRED = NO

xcodebuild ... test -only-testing:LifeManagerUnitTests/SigningConfigurationTests
Executed 5 tests, with 0 failures (0 unexpected)
```

## Fresh review round 1 — URL cursor and canonical mobile-v1 fixtures

### RED

The cursor regression and fixture contract tests were run before the URL/model
changes were complete:

```text
xcodebuild ... test \
  -only-testing:LifeManagerUnitTests/APIClientTests \
  -only-testing:LifeManagerUnitTests/ServiceProtocolTests \
  -only-testing:LifeManagerUnitTests/ContractFixtureDecodingTests
Executed 15 tests, with 6 failures (0 unexpected)
```

The real URL assertion observed the cursor appended to the path, with no
`URLComponents.queryItems`; the chat service emitted percent-escaped cursor
text; and the existing fixture lookup decoded the stale bootstrap shape. The
typed fixture test also initially failed to compile until the canonical nullable
route fields and all frozen response models were represented.

### GREEN

`APIClient` now merges endpoint path and query through `URLComponents`, and
`ChatService.fetch` creates a `cursor` query item without path encoding. The
same checkout packages all 20 canonical `mobile-v1` fixtures from the Gate 3
contract commit. Swift models now decode the canonical `user.productLocale` /
`timezone`, all terminal analysis statuses, `analysis` and `call_status`
message kinds, nullable route facts/times, APNs/call/deletion/session/error/
contract receipts, and the canonical operation IDs.

```text
APIClientTests:               4/4 passed
ServiceProtocolTests:         5/5 passed
ContractFixtureDecodingTests: 7/7 passed
Combined targeted tests:     16/16 passed, 0 failures
```

## Fresh review round 1 — confirmed product locale propagation

### RED

The locale regression tests were added before the app wiring existed:

```text
xcodebuild ... test \
  -only-testing:LifeManagerUnitTests/ChatViewModelTests/testLocaleChangeResetsProjectionAndFetchesFromBeginning \
  -only-testing:LifeManagerUnitTests/AppDelegatePushTests/testLocaleChangeReregistersExistingTokenWithUpdatedLocale \
  -only-testing:LifeManagerUnitTests/SettingsViewModelTests/testSavedProductLocaleNotifiesTheAppAfterServerConfirmation \
  -only-testing:LifeManagerUnitTests/SettingsViewModelTests/testProductLocaleMapsToSwiftUILocaleIdentifier
```

The first run failed at compile time because `ChatViewModel` had no projection
reset, `LifeManagerAppDelegate` could not re-register a token with a new
locale, Settings had no server-confirmed profile callback, and the model had
no SwiftUI locale mapping.

### GREEN

The confirmed server `productLocale` now drives `.environment(\.locale, ...)`.
Settings notifies `AppViewModel` only after the profile mutation returns, the
chat coordinator clears its cursor and projection before refetching, and APNs
re-registers the existing token with the updated locale/timezone.

```text
AppDelegate locale test:   1/1 passed
Chat locale reset test:    1/1 passed
Settings callback + map:   2/2 passed
Combined targeted tests:   4/4 passed, 0 failures
```

## Fresh review round 1 — restore/bootstrap, chat state, and soft paywall receipt

### RED

The restore and receipt tests were added before `AppViewModel` fetched server
state or retained the analysis response:

```text
xcodebuild ... test \
  -only-testing:LifeManagerUnitTests/AppViewModelTests/testRestoreFetchesBootstrapAndChatProjectionBeforeChoosingChat \
  -only-testing:LifeManagerUnitTests/AppViewModelTests/testRestoreValidatesRequiredServerProfileBeforeChat \
  -only-testing:LifeManagerUnitTests/AppViewModelTests/testUsefulAnalysisReceiptIsRetainedAndSoftPaywallAppearsOnlyOnce
```

The RED build exposed the missing terminal bootstrap status representation,
missing receipt property, and the old restore path that stopped after reading
Keychain session state. It did not fetch `/bootstrap` or the initial `/chat`
projection, and it had no required-profile validation.

### GREEN

Restore now requires an authenticated session, fetches bootstrap, applies the
server calendar/profile/phone/analysis state, validates calendar/name/home
before entering chat, and loads the server chat projection when the account is
ready. `AnalysisResult` is retained as `lastAnalysisReceipt`; the soft paywall
is one-shot after the first useful result and `Continue free` preserves chat.

```text
Restore/chat projection test:  1/1 passed
Required profile test:         1/1 passed
Receipt/paywall test:          1/1 passed
Combined targeted tests:       3/3 passed, 0 failures
```

## Fresh review round 1 — operation-scoped idempotency and OAuth session propagation

### RED

The mutation/session regression lane was added before retry state and the
authenticated API session bridge existed:

```text
xcodebuild ... test \
  -only-testing:LifeManagerUnitTests/APIClientTests/testExplicitSessionPropagationUpdatesCachedSessionForLogout \
  -only-testing:LifeManagerUnitTests/ServiceProtocolTests/testOAuthExchangePropagatesSessionToAuthenticatedAPI \
  -only-testing:LifeManagerUnitTests/ChatViewModelTests/testAmbiguousReplyRetainsTextAndIdempotencyKeyForRetry \
  -only-testing:LifeManagerUnitTests/SettingsViewModelTests/testAmbiguousCallReusesOperationKeyUntilSuccess \
  -only-testing:LifeManagerUnitTests/SettingsViewModelTests/testAmbiguousProfileUpdateReusesDraftAndOperationKey \
  -only-testing:LifeManagerUnitTests/SettingsViewModelTests/testAmbiguousDeletionReusesOperationKeyUntilReceipt \
  -only-testing:LifeManagerUnitTests/SettingsViewModelTests/testSignOutNotifiesRootAfterSessionRevocationAttempt
```

RED failed at the missing retry-store/session-propagation APIs. The prior
implementation generated a fresh UUID on every call, cleared reply text before
an ambiguous error, and did not notify the root after local logout cleanup.

### GREEN

`UserDefaultsOperationRetryStore` persists operation-scoped UUIDs plus profile
draft/reply text. Ambiguous transport/5xx/409 failures retain the operation;
successful or definitive 4xx responses clear it. Calls, replies, profile
updates, and deletion all use the same key on retry. OAuth exchange and refresh
now propagate the new session into authenticated `APIClient`; sign-out clears
both caches and notifies the root to render welcome.

```text
APIClient session test:       1/1 passed
OAuth propagation test:      1/1 passed
Reply retry test:            1/1 passed
Call/profile/delete retry:   3/3 passed
Logout root callback:        1/1 passed
Retry policy test:            1/1 passed
Combined mutation lane:      7/7 passed, 0 failures
```

## Fresh review round 1 — masked phone display boundary and call-language default

### RED

The regression tests were added before separating the server's masked phone
display value from the replacement input:

```text
xcodebuild ... test \
  -only-testing:LifeManagerUnitTests/SettingsViewModelTests/testMaskedPhoneStaysDisplayOnlyAndIsOmittedFromUnchangedPayload \
  -only-testing:LifeManagerUnitTests/SettingsViewModelTests/testCallLanguageDefaultsToConfirmedProductLocaleWhenServerOmitsIt

Build failed: SettingsViewModel has no member 'phoneDisplay'
```

### GREEN

Settings now keeps the server-confirmed masked value in `phoneDisplay` and
starts the editable replacement field empty. An unchanged profile mutation
therefore omits `phone` instead of sending the masked display value. When the
server omits `callLanguage`, the confirmed `productLocale` is used as the
default. The settings UI labels the current masked value separately from the
replacement field.

```text
Targeted tests: 2/2 passed, 0 failures
```

## Fresh review round 1 — honest route timing, source, and unsupported facts

### RED

The route regression tests were added before the presentation exposed server
freshness/source facts and before either route view rendered the required
semantic honesty labels:

```text
xcodebuild ... test \
  -only-testing:LifeManagerUnitTests/RoutePresentationTests/testCollapsedRouteCardProjectsActionableFieldsAndOrderedLegSummary \
  -only-testing:LifeManagerUnitTests/RoutePresentationTests/testRouteViewsExposeSemanticTimingSourceFreshnessAndHonestyLabels

Build failed: RouteCardPresentation has no members computedAt, provider, or isUnofficialSource
```

After the presentation fields compiled, the source contract failed with 12
missing card/detail labels for leave, arrival, buffer reason, source,
freshness, non-official warning, live-location honesty, and unsupported-field
honesty.

### GREEN

Route presentation now carries the server's `computedAt` and `provider` and
derives the non-official warning only for the Transit provider. The card and
read-only detail sheet show explicit leave/arrival labels, arrival-buffer
reason, provider source, freshness, and a localized non-official service
warning. The detail sheet also states that live location is off and that
unsupported entrance/exit/best-car/crowding facts are omitted. Existing
nullable fare, platform, geometry, and step locations remain omitted rather
than replaced with guesses.

```text
RoutePresentationTests:       4/4 passed
LocalizationConsistencyTests: 2/2 passed
Combined targeted tests:      6/6 passed, 0 failures
```

## Fresh review round 1 — clean test lane, fixture packaging, and Maestro locale picker

### RED

The test-lane and flow contract tests reproduced all three test-harness
findings before the fix:

```text
xcodebuild ... test -only-testing:LifeManagerUnitTests/MaestroFlowContractTests

Clean Fastlane lane: 2 failures (`clean: false`, `skip_build: true`)
Japanese locale flow: picker identifier missing (`profile.productLocale`)
Executed 4 tests, with 3 failures (0 unexpected)
```

### GREEN

The Fastlane test lane now cleans and builds the generated checkout project
before running the serial simulator suite. `project.yml` packages
`LifeManagerTests/TestFixtures/mobile-v1` into the unit-test bundle, and the
fixture loader checks that same-checkout directory first. Both English and
Japanese Maestro flows now tap `profile.productLocale` to open the Picker
before selecting their language.

```text
MaestroFlowContractTests: 4/4 passed, 0 failures
```

Clean Fastlane verification from `apps/life-manager-ios/`:

```text
PATH="/opt/homebrew/opt/ruby/bin:$PATH" bundle exec fastlane test
UI tests:   2/2 passed
Unit tests: 88/88 passed
Total:      90/90 passed, 0 failures
Test Succeeded
```

## TestFlight readiness follow-up — real AppIcon, Release signing, and ASC fail-closed lane

### RED

The fresh readiness tests were run before the signing and asset configuration:

```text
xcodebuild ... test \
  -only-testing:LifeManagerUnitTests/SigningConfigurationTests/testReleaseUsesAutomaticDistributionSigningTeamAndPreservesSimulatorDebugOverrides \
  -only-testing:LifeManagerUnitTests/SigningConfigurationTests/testAppIconAssetIsRealAndSelectedByTheApplicationTarget \
  -only-testing:LifeManagerUnitTests/SigningConfigurationTests/testFastlaneUsesASCBypassAndFailsClosedOnRequiredInputs

Executed 3 tests, with 7 failures (1 unexpected)
```

The failures were the absent AppIcon catalog, missing Release automatic team /
distribution identity settings, and missing ASC bypass / non-empty build-input
guards.

### GREEN

Release now uses automatic signing with team `S5U8UH3JLJ`, Apple Distribution
identity for iphoneos, and the existing production APNs entitlement; simulator
signing remains disabled and Debug remains development-APNs signed for devices.
The app target selects `AppIcon` from a real asset catalog. The 1024px source is
the tracked production Anicca umbrella-brand asset
`/Users/anicca/anicca-project/aniccaios/aniccaios/Assets.xcassets/AppIcon.appiconset/icon-1024.png`
(RGB 1024×1024), copied and resized into the iOS catalog without a placeholder.
Fastlane forces `ASC_BYPASS_KEYCHAIN=1`, rejects empty or missing ASC key
inputs, rejects non-positive `LIFEMANAGER_BUILD_NUMBER`, and verifies the IPA
exists before upload.

```text
SigningConfigurationTests: 8/8 passed, 0 failures
```

No Apple app record was created, and no archive, ASC mutation, or upload was
run.

Full serial verification after this readiness slice:

```text
xcodegen generate: exit 0
xcodebuild ... -parallel-testing-enabled NO test: exit 0
UI tests:   2/2 passed
Unit tests: 91/91 passed
Total:      93/93 passed, 0 failures
```

## Fresh final review — frozen mobile-v1 fixture synchronization

### RED

The frozen backend contract hash gate was added against commit `78bcadf98`:

```text
xcodebuild ... test \
  -only-testing:LifeManagerUnitTests/ContractFixtureDecodingTests/testBundledFixturesMatchFrozenBackendContractHashes

Executed 1 test, with 9 failures (0 unexpected)
```

The failures identified stale local copies for route/analysis/chat/contract
and deletion fixtures. The old loader also searched an environment override,
the sibling backend path, and sibling worktrees, allowing stale fixtures to
win in a clean test lane.

### GREEN

All 20 bundled JSON fixtures now byte-match the frozen `78bcadf98`
`apps/life-manager/contracts/mobile-v1` files, including canonical cursors,
timezone/route text, and deletion capability fields. The loader prefers the
unit-test bundle and only falls back to the same checkout's fixture directory;
environment, backend-sibling, and sibling-worktree fallbacks are removed.

```text
ContractFixtureDecodingTests: 8/8 passed, 0 failures
Hash + loader regression pair: 2/2 passed, 0 failures
```

## Fresh final review — OAuth session propagation and revoke ordering

### RED

The new real-composition regression initially could not compile because
`AppComposition` had no injectable transport/store/callback authorizer, and the
OAuth relay had only one target. The test contract requires the exchange and
refresh session to reach both the unauthenticated session API and the
authenticated API before logout.

### GREEN

`SessionPropagationRelay` now fans out every exchange, refresh, and clear to
all attached API clients. `AppComposition` injects the same transport/store and
attaches both `sessionAPI` and `authenticatedAPI`; production construction
still uses Keychain, URLSession, and the web OAuth authorizer. The real
composition test pauses the server's `DELETE /session`, asserts the OAuth
Bearer header and server revoke while the root is not yet `.welcome`, then
releases the response and verifies the root transitions to `.welcome`.

```text
OAuth exchange + refresh + AppComposition logout: 3/3 passed, 0 failures
```

## Fresh final review — APIClient idempotency fail-closed guard

### RED

The regression test showed that a mutation called without a key silently
generated a UUID and reached the transport:

```text
testMutationWithoutIdempotencyKeyFailsClosedBeforeTransport: failed
expected caller-provided key; transport request count was 1
```

### GREEN

`APIClient` now throws `APIError.missingIdempotencyKey` before loading or
sending a required mutation, and request construction no longer has an
implicit UUID fallback. Callers must persist and pass their operation key.

```text
APIClient fail-closed + explicit-key regression: 2/2 passed, 0 failures
```

## Fresh final review — durable session mutation keys and bodies

### RED

The new session mutation tests first failed to compile because `AuthService`
had no durable operation store. After wiring the store, the exchange test
showed the second callback request generated a different key/body rather than
replaying the persisted request.

### GREEN

`RetryOperation` now includes session start/exchange/refresh/revoke. Auth
persists each mutation key before sending, retains the exact exchange/refresh
body through transport/invalid-response ambiguity, and clears only after a
successful response or definitive rejection. APIClient also keeps the current
session on an ambiguous refresh failure so the persisted refresh operation can
be retried; definitive refresh-family rejection still clears it.

```text
OAuth exchange + refresh + revoke durable retry: 3/3 passed, 0 failures
Ambiguous APIClient refresh retention + definitive rejection: 2/2 passed, 0 failures
```

## Fresh final review — analysis and APNs durable mutation coverage

### RED

The new analysis/APNs tests reproduced missing durable state: analysis used a
fresh UUID after an ambiguous failure, APNs registration had no persisted body
for restart, and Settings logout generated a separate APNs DELETE key from the
AppDelegate path.

### GREEN

Analysis now stores its operation key until the analysis receipt succeeds.
AppDelegate persists the APNs PUT body/key, restores the pending token and
server-confirmed locale/timezone after restart, and reuses the key through an
ambiguous response. APNs DELETE uses the same durable operation in AppDelegate
and Settings. Concurrent registration attempts are coalesced so one mutation
cannot clear another request's pending operation.

```text
Analysis + APNs durable regression set: 4/4 passed, 0 failures
```
