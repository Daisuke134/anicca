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

### ios test

```sh
[bundle exec] fastlane ios test
```

Unit/Integration テストを実行

### ios build_for_simulator

```sh
[bundle exec] fastlane ios build_for_simulator
```

シミュレータでビルド&起動

### ios build

```sh
[bundle exec] fastlane ios build
```

App Store 用 IPA をビルド

### ios upload

```sh
[bundle exec] fastlane ios upload
```

App Store Connect へアップロード

### ios preflight

```sh
[bundle exec] fastlane ios preflight
```

Greenlight でプリフライトチェック (CRITICAL=0 必須)

### ios submit_review

```sh
[bundle exec] fastlane ios submit_review
```

App Store 審査に提出

### ios safe_release

```sh
[bundle exec] fastlane ios safe_release
```

フルリリース: preflight → build → upload → submit

### ios set_version

```sh
[bundle exec] fastlane ios set_version
```

バージョン番号を更新

----

This README.md is auto-generated and will be re-generated every time [_fastlane_](https://fastlane.tools) is run.

More information about _fastlane_ can be found on [fastlane.tools](https://fastlane.tools).

The documentation of _fastlane_ can be found on [docs.fastlane.tools](https://docs.fastlane.tools).
