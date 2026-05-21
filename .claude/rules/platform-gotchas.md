# iOS Platform Gotchas

プラットフォーム固有の問題と回避策。経験から学んだ教訓を記録。

Source: Kris Puckett (https://www.linkedin.com/posts/kris-puckett-0109041b_if-youre-building-an-ios-app-with-claude-activity-7393778932807852032-Pkuj)
核心の引用: 「Document platform gotchas immediately. Hit an iOS 26 API issue? Add it to CLAUDE.md that session. 'NO .background() before .glassEffect()' saved me from repeating that mistake 50+ times.」

## iOS 26 Specific

### SwiftUI Modifier Order

**問題**: `.background()` を `.glassEffect()` の前に付けるとクラッシュ
**回避策**: `.glassEffect()` → `.background()` の順序で適用

```swift
// ❌ NG
someView
    .background(.ultraThinMaterial)
    .glassEffect()

// ✅ OK
someView
    .glassEffect()
    .background(.ultraThinMaterial)
```

### Age Rating System

**問題**: iOS 26 で新しい age rating system に移行。古い rating key は無効
**回避策**: 新 rating system を使う（appledev CLI で自動対応）

Source: https://developer.apple.com/news/upcoming-requirements/
核心の引用: 「Ratings for all apps and games on the App Store have been automatically updated to align with our new age rating system and will be reflected on Apple devices running a minimum of iOS 26」

## iOS 15 Compatibility

### Locale API

**問題**: `Locale.current.language.languageCode` は iOS 16+。iOS 15 でクラッシュ
**回避策**: `Locale.current.languageCode` を使う

```swift
// ❌ NG (iOS 16+)
let code = Locale.current.language.languageCode

// ✅ OK (iOS 15+)
let code = Locale.current.languageCode
```

### scrollContentBackground

**問題**: `.scrollContentBackground(.hidden)` は iOS 16+
**回避策**: ZStack + Color で代替

```swift
// ❌ NG (iOS 16+)
List { ... }
    .scrollContentBackground(.hidden)

// ✅ OK (iOS 15+)
ZStack {
    Color.clear
    List { ... }
}
```

## General SwiftUI

### .pbxproj ファイル

**問題**: Claude Code が .pbxproj を編集するとプロジェクトが壊れる
**回避策**: 新規ファイルは Claude Code で作成 → Xcode で手動追加

Source: https://www.linkedin.com/posts/kris-puckett-0109041b_if-youre-building-an-ios-app-with-claude-activity-7393778932807852032-Pkuj
核心の引用: 「Never let AI modify .pbxproj files. Create files with Claude Code, add them to Xcode manually. One corrupted project file will waste hours.」

## RevenueCat

### PurchasesDelegate 名前衝突

**問題**: `PurchasesDelegate` を直接採用すると "Type 'X' does not conform to protocol 'PurchasesDelegate'" エラー
**回避策**: NSObject を継承した中間クラス経由で採用

```swift
// ❌ NG
class PaywallViewModel: ObservableObject, PurchasesDelegate { }

// ✅ OK
class RCPurchasesDelegate: NSObject, PurchasesDelegate { }
class PaywallViewModel: ObservableObject {
    private let delegate = RCPurchasesDelegate()
}
```

## Xcode Build

### Simulator Destination

**問題**: `-destination 'name=iPhone 15'` は曖昧でエラー
**回避策**: UDID で明示指定

```bash
# ❌ NG
xcodebuild test -destination 'name=iPhone 15'

# ✅ OK
UDID=$(xcrun simctl list devices | grep "iPhone 15" | head -1 | grep -o '[A-Z0-9-]\{36\}')
xcodebuild test -destination "id=$UDID"
```

## App Store Connect

### Availability Before Pricing

**問題**: pricing を先に設定すると Apple 500 エラー
**回避策**: availability → pricing の順序

```bash
# ❌ NG
asc iap pricing set ...
asc iap availability set ...

# ✅ OK
asc iap availability set ...
asc iap pricing set ...
```

### Demo Account Required Default

**問題**: `demoAccountRequired` のデフォルトは `true`。デモアカ未入力で提出ブロック
**回避策**: 明示的に `false` 指定

```bash
asc metadata update --demoAccountRequired false
```

---

**新しい gotcha を見つけたら即座にこのファイルに追記すること。**
