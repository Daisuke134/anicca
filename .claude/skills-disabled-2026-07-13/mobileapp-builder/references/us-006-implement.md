# US-006: iOS Implementation (TDD)

## Skill

**Read first:** `.claude/skills/tdd-feature/SKILL.md` — Canon TDD 5-step cycle, iOS patterns, Fastlane commands

## Fastfile 必須レーン（MANDATORY）

Fastfile に以下3レーンを必ず含める。US-007 Maestro E2E の前提条件。

```ruby
lane :test do
  run_tests(scheme: "<AppName>", device: "iPhone 17 Pro")
end

lane :build_for_simulator do
  xcodebuild(
    scheme: "<AppName>",
    configuration: "Debug",
    sdk: "iphonesimulator",
    derivedDataPath: "build/DerivedData",
    xcargs: "-destination 'platform=iOS Simulator,name=iPhone 17 Pro'"
  )
end

lane :build_for_release do
  build_app(scheme: "<AppName>", export_method: "app-store")
end
```

## xcconfig は configFiles で設定（MANDATORY）

project.yml で xcconfig を設定する時は `configFiles:` セクションを使う。
`XCCONFIG_FILE` build setting は xcodegen が無視する。

❌ `settings: XCCONFIG_FILE: Config/Debug.local.xcconfig`
✅
```yaml
configFiles:
  Debug: Config/Debug.local.xcconfig
  Release: Config/Release.local.xcconfig
```

### xcconfig ファイル順序ルール（CRITICAL）
Source: dev.to/donniejp — 「secrets xcconfig must never be committed/pushed to git」
Source: moinulhassan.medium.com — 「make sure that config file does not reach the server」

構造（この順序を厳守）:
```
# Debug.xcconfig（gitにコミットされる）
RC_API_KEY = placeholder_replace_in_local    ← 1. placeholder定義（先）
MIXPANEL_TOKEN = placeholder
// ... other non-secret settings ...
#include? "Debug.local.xcconfig"              ← 2. ローカル上書き（最後）
```

APIキー（RC_API_KEY, MIXPANEL_TOKEN等）は `*.local.xcconfig` にのみ記載。
Debug.xcconfig / Release.xcconfig にはplaceholderのみ。

.gitignore に追加:
```
*.local.xcconfig
```

❌ `#include?` を先に書く → ローカル値がplaceholderで上書きされる
❌ Debug.xcconfig / Release.xcconfig に実APIキーを記載 → gitコミット = セキュリティインシデント
✅ `#include?` を最後に書く → ローカル値が有効になる

## SubscriptionService isConfigured guard（MANDATORY）

Purchases.configure() が呼ばれる前に Purchases.shared にアクセスすると
assertionFailure でクラッシュする。未設定時は空を返す guard を必須にする。

```swift
private var isConfigured = false

func configure(apiKey: String) {
    guard !apiKey.isEmpty else { return }
    // ... Purchases.configure(...) ...
    isConfigured = true
}

func purchase(...) async throws -> Bool {
    guard isConfigured else { return false }
    // ...
}

func loadOfferings() async {
    guard isConfigured else { return }
    // ...
}
```

## Variables

```bash
APP_NAME="<AppName>"          # e.g. DeskStretch
APP_SCHEME="<AppName>"        # Xcode scheme name
APP_DIR="$PWD"                # App root directory
BUNDLE_ID="com.aniccafactory.<appname>"
UDID=$(xcrun simctl list devices available | grep "iPhone 16" | head -1 | grep -oE '[A-F0-9-]{36}')
```

## Quality Gate 0 (US-005b 成果物検証)

```bash
source ~/.config/mobileapp-builder/.env
export ASC_BYPASS_KEYCHAIN=1  # tmux/cron環境でKeychainハング防止。irisセッションも正常動作確認済み。
grep -q "RevenueCat" ${APP_NAME}ios/project.yml || { echo "GATE FAIL: no RevenueCat in project.yml"; exit 1; }
asc subscriptions groups list --app $APP_ID | grep -q "group" || { echo "GATE FAIL: no IAP groups"; exit 1; }
```

## Execution Order (4 sub-sessions: 006a → 006b → 006c → 006d)

Source: tdd-feature SKILL.md — "TDD Execution Order: Models → Services → ViewModels → Integration"

### 006a: Data Layer
1. xcconfig template for API Key (tdd-feature: "xcconfig Template Pattern")
2. SubscriptionService Protocol + Implementation (tdd-feature: "Protocol-Based DI")
3. StretchLibraryService error handling
4. Models with accessibilityIdentifier constants
5. ProgressService input validation

### 006b: Onboarding + Monetization
1. AppState → MVVM split (ViewModels)
2. Onboarding flow (notification permission step)
3. Onboarding hook (UX_SPEC compliant — see ios-ux-design references/onboarding.md)

**onboarding完了フラグのパターン（MANDATORY）:**
Source: stackoverflow.com/questions/74255552 — 「@AppStorage("show_onboarding") を各Viewに直接定義」
Source: medium.com/@jpmtech — 「add the same call to AppStorage with the same default value」

❌ onComplete?() → viewModel.complete() → isComplete → .onChange → hasCompleted （間接チェーン = 壊れやすい）
✅ @AppStorage("hasCompletedOnboarding") var hasCompletedOnboarding = false を PaywallView に直接定義。ボタンタップで直接 hasCompletedOnboarding = true。
理由: .onChange チェーンはSwiftUIのライフサイクルでタイミングが不安定。@AppStorage直接設定は確実。
4. PaywallView: offerings error display + DESIGN_SYSTEM tokens
5. PaywallView: remove false claims (Rule 21: AI禁止)
6. URL force-unwrap → optional binding

**PaywallView Implementation Best Practices:**
Source: https://blog.funnelfox.com/effective-paywall-screen-designs-mobile-apps/
Source: https://adapty.io/blog/how-to-design-ios-paywall/
Source: https://appagent.com/blog/mobile-app-onboarding-5-paywall-optimization-strategies/

**Mandatory Elements (all must be present):**
1. **Value headline**: Clear headline reflecting value (NOT feature list). Example: "Reach your goal 3× faster" (NOT "Premium features")
2. **Benefit bullets**: 3-5 specific, tangible benefits (NOT vague features). Example: "Track 10+ habits daily" (NOT "Advanced tracking")
3. **Pricing grid**: Display 3 plans (weekly + monthly + annual). Highlight "Best Value" plan with accent color
4. **Discount badge**: "Save X%" badge + strikethrough original price (Source: Adapty — +20-30% conversion)
5. **Benefit-driven CTA**: "Start my plan" / "Unlock full access" (NOT "Subscribe") (Source: Funnelfox — outperforms generic)
6. **FAQ section**: Inline FAQ (billing details, cancellation policy) to reduce friction
7. **Social proof**: Review count + average rating + 1-2 user testimonials
8. **Legal links**: Privacy Policy + Terms (bottom, small text)

**Layout Pattern (long-form):**
```
[Value Headline]
[Benefit bullets 1-5]
[Social proof: ⭐️ 4.9 (12,000 reviews)]
[Pricing grid: 3 cards with "Save 50%" badge]
[Benefit-driven CTA button]
[FAQ: 3-4 Q&A pairs]
[Privacy + Terms links]
```
Source: Appagent — "Long-form paywalls: up to 12× revenue"

**Animation (12-18% CVR boost — MANDATORY):**
- CTA button: subtle pulse animation (`.scaleEffect` with `.repeatForever`) — NOT just on tap
- Benefit bullets: `.onAppear` staggered fade-in
- Pricing cards: gentle entrance animation
Source: Adapty — "Animated vs static paywall: 2.9× higher"
Source: RevenueCat Blog — 5 Overlooked Paywall Improvements (https://www.revenuecat.com/blog/growth/paywall-conversion-boosters/)
Quote: 「When implemented correctly, animated elements typically increase conversion rates by 12-18% compared to static alternatives.」

**Copywriting Rule (Clarity > Creativity):**
- Paywall copy must state benefits directly in everyday language
- NO jargon, NO clever wordplay at the expense of comprehension
- Answer: "What benefit?" + "Why should I care?" + "How will this improve my life?"
Source: RevenueCat Blog (https://www.revenuecat.com/blog/growth/paywall-conversion-boosters/)
Quote: 「Users encountering a paywall aren't looking to be entertained — they're evaluating whether your product is worth their money.」

**Discount Prominence (MANDATORY):**
- Annual plan discount % must be large, visually distinct, above/near pricing
- Use contrasting color or badge. Frame as "Save X%" not technical terms
- Tie discount to a reason (first-time offer, launch special) — never naked discount
Source: RevenueCat Blog (https://www.revenuecat.com/blog/growth/paywall-conversion-boosters/)
Quote: 「When users can immediately quantify their savings, it creates urgency and provides a compelling reason to act now rather than later.」

**Day-1 Paywall (82% rule):**
- Paywall MUST appear during onboarding flow (not delayed to later sessions)
- 82% of trial starts happen on install day — missing day-1 = losing 82% of potential trials
Source: RevenueCat State of Subscription Apps 2025 (https://www.revenuecat.com/state-of-subscription-apps-2025/)
Quote: 「82% of trial starts occur the same day a user installs an app」

**Message Consistency:**
- Paywall headline must match onboarding final screen message
- Use same tone/visuals from onboarding
Source: Funnelfox — "Consistent messaging from ad to onboarding to paywall increases conversions"

### 006c: Core Screens
1. Timer: background timer support
2. Timer: zero-division guard (intervalMinutes=0)
3. Timer: StretchLibraryService dedup
4. Settings: Upgrade → PaywallView navigation
5. ProgressDashboard: DateFormatter optimization + weekday labels

**WorkoutTimerView 実装ルール:**
- Stop ボタンは常に WorkoutLogView に遷移する（elapsed=0 でも）
- 理由: Maestro E2E テストで即 Stop しても画面遷移を検証できる必要がある
- elapsed=0 のセッションは WorkoutLogView 内で「セッションなし」表示にする（ガードで遷移を阻止しない）

### 006d: Polish + Resources
1. DESIGN_SYSTEM tokens across all Views
2. All a11y IDs aligned to TEST_SPEC
3. PrivacyInfo.xcprivacy + ITSAppUsesNonExemptEncryption
4. Localization (.xcstrings)
5. PainAreaSelectionView: disabled button helper text

**a11y ID 配置ルール（CRITICAL — Maestro E2E 互換性）:**
Source: docs.maestro.dev/platform-support/ios-swiftui — 「assign accessibilityIdentifier for UI element that needs to be accessed」

❌ コンテナ（NavigationStack, TabView, VStack, ScrollView）に a11y ID を付ける → Maestroが検出不可
✅ 末端の操作可能要素（Button, Text, TextField, Toggle）に a11y ID を付ける
例:
❌ `NavigationStack { ... }.accessibilityIdentifier("screen_settings")`
✅ `Text("Settings").accessibilityIdentifier("label_settings_title")`

**Each sub-session follows Canon TDD:** Test List → RED → GREEN → REFACTOR → repeat

## Step: project.yml (before implementation)

```bash
cd ${APP_NAME}ios && xcodegen generate
```

project.yml template: see current file or docs/ARCHITECTURE.md. Key points:
- `deploymentTarget: iOS "17.0"` if @Observable, `"15.0"` if ObservableObject
- `packages: RevenueCat` (SPM mirror, from: 5.0.0). **RevenueCatUI 禁止**
- Test target: `GENERATE_INFOPLIST_FILE: YES`
- `.xcodeproj` in .gitignore

### iPhone-only + iPad Multitasking Opt-out（MANDATORY）
Source: Stack Overflow (https://stackoverflow.com/questions/32559724) — 543 upvotes
核心の引用: 「check the 'Requires Full Screen' checkbox under General > Targets」
Source: Apple (https://developer.apple.com/documentation/bundleresources/information_property_list/uisupportedinterfaceorientations)
核心の引用: 「you need to include all orientations to support iPad multitasking」

project.yml の info.properties に必ず追加:
```yaml
info:
  properties:
    UIRequiresFullScreen: true           # ← iPad multitasking opt-out
    UISupportedInterfaceOrientations:
      - UIInterfaceOrientationPortrait
```

settings.base に必ず追加:
```yaml
settings:
  base:
    TARGETED_DEVICE_FAMILY: "1"          # ← iPhone only（"1,2" = Universal, "2" = iPad only）
```

xcodegen 後の検証ゲート（MANDATORY — archive 前に実行）:
```bash
IPAD_LEAK=$(grep 'TARGETED_DEVICE_FAMILY = "1,2"' *.xcodeproj/project.pbxproj | grep -v "tests" || true)
if [ -n "$IPAD_LEAK" ]; then
  echo "❌ TARGETED_DEVICE_FAMILY '1,2' leaked into main target. Fix project.yml."
  exit 1
fi
echo "✅ All main targets are iPhone-only (TARGETED_DEVICE_FAMILY = 1)"
```

❌ `UIRequiresFullScreen` なし + `TARGETED_DEVICE_FAMILY: "1"` → xcodegen がReleaseで `1,2` を混入するリスク → ITMS-90474 拒否
✅ `UIRequiresFullScreen: true` + `TARGETED_DEVICE_FAMILY: "1"` + 検証ゲート → 確実にiPhone-only

## Step: PrivacyInfo.xcprivacy

```bash
cat > ${APP_NAME}ios/${APP_NAME}/PrivacyInfo.xcprivacy << 'PRIVEOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>NSPrivacyTracking</key><false/>
  <key>NSPrivacyTrackingDomains</key><array/>
  <key>NSPrivacyCollectedDataTypes</key><array/>
  <key>NSPrivacyAccessedAPITypes</key>
  <array>
    <dict>
      <key>NSPrivacyAccessedAPIType</key>
      <string>NSPrivacyAccessedAPICategoryUserDefaults</string>
      <key>NSPrivacyAccessedAPITypeReasons</key>
      <array><string>CA92.1</string></array>
    </dict>
  </array>
</dict>
</plist>
PRIVEOF
```

## Step: App Icon (1024x1024 single image, universal idiom) — Fix #7

Source: Apple HIG — App Icons
https://developer.apple.com/design/human-interface-guidelines/app-icons
核心の引用: 「Every app must have a beautiful, memorable icon... provide a single 1024×1024 px image」

```bash
# Generate with PIL, then place at:
# Resources/Assets.xcassets/AppIcon.appiconset/1024.png
# Contents.json: "idiom": "universal", "platform": "ios", "size": "1024x1024"
```

### App Icon Gate Check (MANDATORY — Fix #7)
```bash
# アプリアイコン存在チェック — ビルド前に必ず実行
ICON_SET=$(find . -name "AppIcon.appiconset" -not -path "*/build/*" | head -1)
ICON_FILE=$(find "$ICON_SET" -name "*.png" -size +10k 2>/dev/null | head -1)
if [ -z "$ICON_FILE" ]; then
  echo "❌ GATE FAIL: No app icon (1024x1024) found in $ICON_SET"
  echo "Generate a simple branded icon using Python/Pillow before proceeding"
  exit 1
fi
# サイズ検証
ICON_SIZE=$(python3 -c "from PIL import Image; img=Image.open('$ICON_FILE'); print(f'{img.width}x{img.height}')" 2>/dev/null || echo "unknown")
[ "$ICON_SIZE" = "1024x1024" ] || { echo "❌ GATE FAIL: App icon is $ICON_SIZE (must be 1024x1024)"; exit 1; }
echo "✅ App icon found: $ICON_FILE ($ICON_SIZE)"
```

## Step: PaywallView (自前 SwiftUI — RevenueCatUI 禁止)

Pattern: `Purchases.shared.offerings().current` → `ForEach(availablePackages)` → `purchase(package:)`

Required a11y IDs: `paywall_plan_monthly`, `paywall_plan_yearly`, `paywall_cta`, `paywall_maybe_later`, `paywall_restore`

Onboarding key: `hasCompletedOnboarding` (全アプリ統一 — US-008a スクショ依存)

### SubscriptionService 実装パターン（DEBUG uiPreviewMode 対応必須）

⚠️ **us-005b-monetization.md の「SubscriptionService.configure() パターン」を必ず実装すること。**

- `#if DEBUG` + `@_spi(Internal) import RevenueCat` + `DangerousSettings(uiPreviewMode: true)`
- `purchase()` で cancel(1) / simulatedFailure(42) のみ re-throw、それ以外は成功
- Release ビルドは通常の `entitlementVerificationMode: .informational`

これがないと US-007 の Payment E2E テストが全て FAIL する（シミュレータ StoreKit バグ）。

## Step: Greenlight Loop (実装完了後)

```bash
while true; do
  GL_OUTPUT=$(greenlight preflight "$(find . -name '*.xcodeproj' -maxdepth 2 | head -1 | xargs dirname)" --format json 2>&1)
  GL_CRITICAL=$(echo "$GL_OUTPUT" | jq '.summary.critical // 999')
  [ "$GL_CRITICAL" -eq 0 ] && echo "GREENLIT" && break
  echo "CRITICAL=$GL_CRITICAL — fixing..."
done
```

## PROHIBITED

- `import RevenueCatUI` / `RevenueCatUI.PaywallView`
- Mock/Placeholder code in production
- Mixpanel / Firebase Analytics / Amplitude (Greenlight CRITICAL)
- AppTrackingTransparency / NSUserTrackingUsageDescription
- AI API / external API (Rule 21: OpenAI, Anthropic, Gemini, FoundationModels)
- `xcodebuild` direct — use `fastlane test` / `fastlane build`

## Gate (ALL must pass)

```bash
# Build
fastlane build

# Tests
fastlane test

# Mock zero
MOCK_COUNT=$(grep -rw 'class Mock' --include='*.swift' . | grep -v 'Tests/' | grep -v '.build/' | wc -l)
[ "$MOCK_COUNT" -eq 0 ] || { echo "FAIL: $MOCK_COUNT Mock in production"; exit 1; }

# RevenueCat present, RevenueCatUI absent
grep -r 'import RevenueCat' --include='*.swift' . | grep -v 'RevenueCatUI' | wc -l  # > 0
grep -r 'import RevenueCatUI' --include='*.swift' . | wc -l  # = 0

# PrivacyInfo
grep -q "CA92.1" ${APP_NAME}ios/${APP_NAME}/PrivacyInfo.xcprivacy

# No AI APIs (Rule 21)
grep -rE 'import (OpenAI|GoogleGenerativeAI|Anthropic)' --include='*.swift' . | wc -l  # = 0

# Greenlight
greenlight preflight "$(find . -name '*.xcodeproj' -maxdepth 2 | head -1 | xargs dirname)" --format json | jq -e '.summary.critical == 0'

echo "US-006 PASS"
```
