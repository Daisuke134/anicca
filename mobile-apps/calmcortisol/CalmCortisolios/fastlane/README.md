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

### ios create_app

```sh
[bundle exec] fastlane ios create_app
```

Create app in ASC and Developer Portal

### ios test

```sh
[bundle exec] fastlane ios test
```

Run unit tests

### ios set_version

```sh
[bundle exec] fastlane ios set_version
```

Set marketing version

### ios build_for_simulator

```sh
[bundle exec] fastlane ios build_for_simulator
```

Build for simulator (screenshots)

### ios build_for_device

```sh
[bundle exec] fastlane ios build_for_device
```

Build for device

### ios release

```sh
[bundle exec] fastlane ios release
```

Build and upload to App Store Connect

### ios full_release

```sh
[bundle exec] fastlane ios full_release
```

Full release: build + upload

----

This README.md is auto-generated and will be re-generated every time [_fastlane_](https://fastlane.tools) is run.

More information about _fastlane_ can be found on [fastlane.tools](https://fastlane.tools).

The documentation of _fastlane_ can be found on [docs.fastlane.tools](https://docs.fastlane.tools).
