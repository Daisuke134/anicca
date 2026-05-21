# US-007: E2E Testing (Maestro)

**Unit/Integration tests are written in US-006 (TDD).** This US is E2E only.

## Skill

**Read first:** `.claude/skills/maestro-ui-testing/SKILL.md` — Best practices, Fix Loop, RC Test Store, a11y selectors

## Maestro + SwiftUI ベストプラクティス（MANDATORY — 全フロー作成前に読め）

Source: docs.maestro.dev/platform-support/ios-swiftui
核心の引用: 「assign accessibilityIdentifier or accessibilityLabel for UI element that needs to be accessed」

Source: birdeatsbug.com/blog/maestro-real-ios-device-support
核心の引用: 「Use Stable Element Identifiers: Leverage accessibility IDs, labels, or unique...」

### ルール1: コンテナに a11y ID を付けるな
NavigationStack, TabView, VStack, ScrollView に .accessibilityIdentifier() を
付けても Maestro が検出できない。末端の操作可能要素（Button, Text, TextField）に付けること。

❌ `NavigationStack { ... }.accessibilityIdentifier("timer_view")`
✅ `Button("Start") { }.accessibilityIdentifier("timer_start")`

### ルール2: 非選択タブはテキストでタップ
SwiftUI TabView は非選択タブのコンテンツを遅延ロードする。
a11y ID ではなくタブラベルのテキストでタップする。

❌ `- tapOn: { id: "tab_settings" }`
✅ `- tapOn: "Settings"`

### ルール3: アニメーション中の要素を検証するな
withAnimation / scaleEffect 中の Text は accessibility tree が不安定。
静的な要素（Skip ボタン等）で画面存在を検証する。

❌ `- assertVisible: { id: "breathing_phase_label" }`
✅ `- assertVisible: { id: "breathing_skip" }`

### ルール4: uiPreviewMode の購入テスト
Source: revenuecat.com/blog/engineering/testing-test-store/
核心の引用: 「The most important tests involve full purchase flows. These tests use Espresso to interact with Test Store's dialog」

uiPreviewMode: true では RC purchase dialog（"Test valid purchase"）は表示されない（自動完了）。
購入成功の検証は画面遷移で行う。

❌ `- tapOn: "Test valid purchase"`
✅ `- assertVisible: { id: "timer_start" }  # paywall 閉じた = 購入成功`

### ルール5: シミュレータ offerings フォールバック（MANDATORY）
Source: revenuecat.com/docs/test-and-launch/sandbox/apple-app-store — 「StoreKit Configuration file でテスト」

シミュレータでは RC offerings fetch が失敗する場合がある。
PaywallView に DEBUG 時フォールバックを必ず追加:

```swift
#if DEBUG
if packages.isEmpty {
    packages = Package.previewPackages(
        monthly: monthlyPrice, annual: annualPrice, weekly: weeklyPrice
    )
}
#endif
```

### ルール6: Scroll ルール（MANDATORY）
Source: docs.maestro.dev/api-reference/commands/scrolluntilvisible — 「scrollUntilVisible: element を使う」

PaywallView / 設定画面等の縦長画面では、画面下部のボタンをタップする前に scrollUntilVisible を使う:

```yaml
- scrollUntilVisible:
    element:
      id: "btn_maybe_later"
    direction: DOWN
    timeout: 10000
- tapOn:
    id: "btn_maybe_later"
```

❌ `- scroll` だけ → スクロール量が不定、要素がまだ見えない可能性
✅ `- scrollUntilVisible` → 要素が見えるまで自動スクロール

### ルール7: Timer/Workout E2E対応
WorkoutTimerView の Stop ボタンは常に WorkoutLogView に遷移する（elapsed=0 でも）。
elapsed=0 ガードで遷移を阻止しない。Maestro E2E で即 Stop しても画面遷移を検証できる必要がある。

## Variables

```bash
APP_NAME="<AppName>"
BUNDLE_ID="com.aniccafactory.<appname>"
UDID=$(xcrun simctl list devices available | grep "iPhone 17 Pro\|iPhone 16" | head -1 | grep -oE '[A-F0-9-]{36}')
```

## Pre-test Setup（MANDATORY）

### 1. シミュレータ環境クリーンアップ（並列実行防止）
```bash
# テスト対象以外の全シミュレータをshutdown
xcrun simctl list devices booted | grep -oE '[A-F0-9-]{36}' | while read uid; do
  [ "$uid" != "$UDID" ] && xcrun simctl shutdown "$uid" 2>/dev/null
done
```

### 2. config.yaml 作成（sequential実行強制）
```bash
cat > maestro/config.yaml << 'EOF'
executionOrder:
  continueOnFailure: false
  flowsOrder:
    - 01-onboarding
    - 02-timer
    - 03-settings
    - 04-payment-monthly-success
    - 05-payment-annual-success
    - 06-payment-failure
EOF
```

### 3. テスト実行
```bash
~/.maestro/bin/maestro test --device "$UDID" maestro/
```

## Quality Gate 0 (US-006 成果物検証)

```bash
fastlane test  # Unit/Integration from 006 must still pass
fastlane build_for_simulator  # Simulator build for Maestro
```

## 6 Flows

| # | File | Content | Tags |
|---|------|---------|------|
| 1 | `maestro/01-onboarding.yaml` | Full onboarding flow | onboarding, smokeTest |
| 2 | `maestro/02-timer.yaml` | Timer start → stretch | timer |
| 3 | `maestro/03-settings.yaml` | Settings screen navigation | settings |
| 4 | `maestro/04-payment-monthly-success.yaml` | RC Test Store → Monthly → Simulate Success | payment, smokeTest |
| 5 | `maestro/05-payment-annual-success.yaml` | RC Test Store → Annual → Simulate Success | payment |
| 6 | `maestro/06-payment-failure.yaml` | RC Test Store → Simulate Failure | payment |

## Flow Template (all flows follow this structure)

```yaml
appId: com.aniccafactory.<appname>
tags:
  - <tag>
---
- clearState
- clearKeychain
- launchApp
- extendedWaitUntil:
    visible:
      id: "<first_element>"
    timeout: 30000
# ... flow steps using id: selectors ...
- takeScreenshot: "<flow_name>"
```

## Fix Loop (FAIL 時の自動修正)

See maestro-ui-testing SKILL.md "Fix Loop" section.

## PROHIBITED

- `flows/` directory (use `maestro/`)
- `xcodebuild test` (use `fastlane test`)
- StoreKit Configuration file (use RC Test Store + `uiPreviewMode`)
  ⚠️ RC Test Store (`test_` key) 単独ではシミュレータで offerings 取得不可。
  us-005b の `uiPreviewMode` パターンが必須。詳細: us-005b-monetization.md
- `point:` selectors (use `id:`)
- Static `wait:` commands (use `extendedWaitUntil`)
- Foundation Models references (Rule 21)
- `"Simulate Success"` / `"Simulate Failure"` テキスト（旧API。RC SDK 5.60.0 では `"Test valid purchase"` / `"Test failed purchase"`）

## Gate (ALL must pass)

```bash
# Simulator build
fastlane build_for_simulator

# All 6 Maestro flows
maestro test maestro/

# Verify flow count
FLOW_COUNT=$(ls maestro/*.yaml | wc -l)
[ "$FLOW_COUNT" -ge 6 ] || { echo "FAIL: need 6+ flows, got $FLOW_COUNT"; exit 1; }

# Verify clearState in all flows
for f in maestro/*.yaml; do
  grep -q 'clearState' "$f" || { echo "FAIL: $f missing clearState"; exit 1; }
done

# Verify takeScreenshot in all flows
for f in maestro/*.yaml; do
  grep -q 'takeScreenshot' "$f" || { echo "FAIL: $f missing takeScreenshot"; exit 1; }
done

# Verify smokeTest tag exists
grep -rl 'smokeTest' maestro/ | wc -l | grep -qv '^0$' || { echo "FAIL: no smokeTest tags"; exit 1; }

echo "US-007 PASS"
```
