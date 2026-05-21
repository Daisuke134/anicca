fastlane documentation
----

# Installation

Make sure you have the latest version of the Xcode command line tools installed:

```sh
xcode-select --install
```

For _fastlane_ installation instructions, see [Installing _fastlane_](https://docs.fastlane.tools/#installing-fastlane)

# Available Actions

## iOS

### ios set_version

```sh
[bundle exec] fastlane ios set_version
```

Set app version

### ios test

```sh
[bundle exec] fastlane ios test
```

Run tests

### ios unlock_keychain_for_signing

```sh
[bundle exec] fastlane ios unlock_keychain_for_signing
```

Unlock keychain before signing

### ios build

```sh
[bundle exec] fastlane ios build
```

Build for App Store

### ios upload

```sh
[bundle exec] fastlane ios upload
```

Upload to App Store Connect

### ios release

```sh
[bundle exec] fastlane ios release
```

Build + Upload

### ios build_for_simulator

```sh
[bundle exec] fastlane ios build_for_simulator
```

Build for simulator

### ios build_for_device

```sh
[bundle exec] fastlane ios build_for_device
```

Build for device

----

This README.md is auto-generated and will be re-generated every time [_fastlane_](https://fastlane.tools) is run.

More information about _fastlane_ can be found on [fastlane.tools](https://fastlane.tools).

The documentation of _fastlane_ can be found on [docs.fastlane.tools](https://docs.fastlane.tools).
