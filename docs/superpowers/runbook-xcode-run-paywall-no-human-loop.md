# Runbook: Xcode で paywall/購入を no-human-in-loop で実行・検証する

**目的**: aniccaios の paywall（実価格・サインイン無し・購入→解錠）を Dais の手を借りず、自分で起動・検証する。

## 核心の学び（なぜ simctl ではダメか）
- ★ paywall の実挙動（サインインダイアログ無し・StoreKit Testing 価格・購入→解錠）は **Xcode Run でしか再現できない** ★。
  - `xcrun simctl launch` は **scheme の StoreKit config を無視する** → 起動時の `refreshOfferings()`(StoreKit products fetch) が実 App Store を叩き「Apple Account にサインイン」ダイアログが出る。
  - `xcodebuild test`（scheme直）も config を test 実行に伝播しない。UI テストの被テスト app には config が確実適用されない。
- ★ Xcode の **Run action（LaunchAction）の StoreKitConfigurationFileReference** を Xcode が直接 app に適用する → これだけがサインイン無しで動く ★。

## 1. StoreKit config の path（RevenueCat 公式サンプルで確定）
- scheme の identifier = **`../../<源フォルダ名>/<file>.storekit`**（`RevenueCat-Samples/storekit-views-demo-app` と同形式）。
- 本プロジェクト = `aniccaios/aniccaios.xcodeproj` + `aniccaios/aniccaios/Anicca.storekit` → identifier = **`../../aniccaios/Anicca.storekit`**。
- UI テスト用は `.xctestplan` の `defaultOptions.storeKitConfigurationFileReference.identifier = "Anicca.storekit"`（.xctestplan と同フォルダ基準）。
- storefront 切替で paywall が変わる: `Anicca.storekit` の `settings._storefront` = "JPN"→ ¥+3プラン(lifetime)、"USA"→ $+2プラン。lifetime カードは `storefrontCountry=="JPN"` 条件。

## 2. webrtc.xcframework が空 → ビルド失敗の対処（恒久注意）
SPM のバイナリ artifact `stasel/WebRTC 141.0.0` が derivedData から消える/DL失敗することがある。
```bash
WC="<derivedData>/SourcePackages/artifacts/webrtc/WebRTC"
curl -sSL -o /tmp/w.zip "https://github.com/stasel/WebRTC/releases/download/141.0.0/WebRTC-M141.xcframework.zip"
rm -rf "$WC/WebRTC.xcframework"; mkdir -p "$WC"; unzip -q -o /tmp/w.zip -d "$WC/"; rm /tmp/w.zip
```
Xcode の dd は `~/Library/Developer/Xcode/DerivedData/aniccaios-*`、CLI は任意の `-derivedDataPath`。Xcode Run の前に**両方**確認。

## 3. cua-driver で Xcode を駆動（権限必須）
- 権限: System Settings → プライバシーとセキュリティ → **アクセシビリティ + 画面収録の両方で CuaDriver.app を ON**（`~/.local/bin/cua-driver doctor` で ✅✅ を確認）。
- ★ Mac Mini は headless で `list_windows` が空でも、**`hotkey` は pid 直送（CGEvent.postToPid）なので効く** ★。
- 手順:
```bash
# Xcode を AppKit-active に（menu shortcut ⌘R のルーティングに必要）
osascript -e 'tell application "Xcode" to activate'
# ⌘R を Xcode の pid に直送 → ビルド+Run
~/.local/bin/cua-driver call hotkey '{"keys":["cmd","r"],"pid":<XcodePID>}'
```
- iPhone 17 sim を destination に: 事前に `xcrun simctl create "iPhone 17" <iPhone-17 type> <iOS runtime>` + `boot`。Xcode は booted sim を destination に拾う。
- 検証: アプリが起動した sim を `xcrun simctl io <UDID> screenshot` で撮る（cua-driver の screen capture は headless で不可なことがあるため simctl が確実）。booted sim 群を `xcrun simctl spawn <UDID> launchctl list | grep ai.anicca.app.ios` でアプリ起動を検出。

## まとめ（1サイクル）
1. scheme: LaunchAction に `../../aniccaios/Anicca.storekit`、storefront を目的(JPN/USA)に設定
2. iPhone 17 sim 作成+boot、Xcode dd の webrtc 復元
3. `osascript activate Xcode` → cua-driver `hotkey ⌘R` (pid)
4. booted sim を `simctl io screenshot` で検証（サインイン無し・¥/$価格・プラン数）

これで完全に no-human-in-loop で paywall/購入を実機検証できる。

## 追記: sim の言語が優先される（言語切替の確実な方法）
scheme の `language="en"` 属性や `-AppleLanguages` 引数より、**sim のシステム言語が優先される**ことがある（新規 sim は Mac の locale=ja_JP を継承し ja-JP になる）。確実な言語切替:
```bash
xcrun simctl spawn <UDID> defaults write -g AppleLanguages -array en   # or ja
xcrun simctl spawn <UDID> defaults write -g AppleLocale -string en_US  # or ja_JP
xcrun simctl uninstall <UDID> ai.anicca.app.ios   # fresh
# → cua-driver ⌘R
```
EN/JA を切り替える時は ① sim language ② Anicca.storekit `_storefront`(USA/JPN) + 価格 の**両方**を合わせる。
