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
