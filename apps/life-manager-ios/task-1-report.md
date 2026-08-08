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
CODE_SIGNING_ALLOWED = NO
CODE_SIGNING_REQUIRED = NO
CODE_SIGN_ENTITLEMENTS = LifeManager/Config/Debug.entitlements
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
