---
name: maestro-ui-testing
description: Use this skill when writing, debugging, or maintaining Maestro E2E UI tests. Enforces best practices for flakiness-free, CI-stable mobile UI tests.
---

# Maestro UI Testing Best Practices

This skill ensures all Maestro E2E tests follow best practices for reliability, especially in CI/CD environments like GitHub Actions.

## When to Activate

- Writing new Maestro E2E tests
- Debugging flaky tests in CI/CD
- Refactoring existing tests
- Setting up Maestro test structure
- Fixing "Assertion is false" errors

## Core Principles

### 1. One Flow = One User Scenario
**NEVER** test your entire app in a single long Flow.

| DO | DON'T |
|-----|-------|
| `01-onboarding.yaml` (single scenario) | `full-app-test.yaml` (entire app) |
| `02-paywall.yaml` (single feature) | All scenarios in one file |

**Why**: 
- If any command fails, the entire test halts
- Can't run tests in parallel
- Hard to identify which scenario failed

### 2. Use accessibilityIdentifier, NOT Text or Point Selectors

| Priority | Selector Type | Reliability | Example |
|----------|--------------|-------------|---------|
| 1st (Best) | `id:` (accessibilityIdentifier) | Stable | `id: "onboarding-welcome-cta"` |
| 2nd | `text:` (fallback) | Localization-dependent | `text: "許可\|Allow"` |
| 3rd (Avoid) | `point:` | **EXTREMELY FLAKY** | `point: "28,78"` |

**SwiftUI Implementation**:
```swift
Button("Get Started") {
    action()
}
.accessibilityIdentifier("onboarding-welcome-cta")
```

**Maestro Usage**:
```yaml
- tapOn:
    id: "onboarding-welcome-cta"
```

### 3. Never Use Static Waits

| DO | DON'T |
|-----|-------|
| `extendedWaitUntil` with visibility | `- wait: 5000` (sleep) |
| `assertVisible` for short waits | Fixed delays |

```yaml
# GOOD - Wait for element to appear
- extendedWaitUntil:
    visible:
      id: "onboarding-welcome-cta"
    timeout: 30000

# BAD - Fixed sleep
- wait: 5000
```

### 4. Handle System Dialogs Properly

System dialogs (permissions, alerts) are non-deterministic. Always use `optional: true`.

```yaml
# Permission dialog - may or may not appear
- tapOn:
    text: "許可|Allow"
    optional: true

# iOS system notification permission
- tapOn:
    id: "com.apple.springboard:Allow"
    optional: true
```

**Multi-language Support** (Japanese/English):
```yaml
- tapOn:
    text: "許可|Allow"
    optional: true
```

### 5. CI/CD Environment Alignment

| Issue | Solution |
|-------|----------|
| Slower CI machines | Increase timeouts (15s → 30s) |
| Different screen sizes | Use `id:` selectors, not `point:` |
| State inconsistency | Always `clearState` + `clearKeychain` |
| Simulator not ready | Add initial `extendedWaitUntil` |

## Flow Structure Template

```yaml
# Feature: [Description]
# Tests: [scenario description]
# Dependencies: [what state is required]

appId: com.example.app
name: Descriptive flow name
tags:
  - smokeTest      # Fast critical path tests for PR
  - featureName    # Feature-specific tag
  - phase6         # Version/phase tag

---
# ALWAYS start with clean state
- clearState
- clearKeychain
- launchApp

# Wait for app to fully load (critical for CI)
- extendedWaitUntil:
    visible: true
    timeout: 15000

# Step 1: [Description]
- extendedWaitUntil:
    visible:
      id: "element-id"
    timeout: 30000

- tapOn:
    id: "element-id"

# Handle optional system dialogs
- tapOn:
    text: "許可|Allow"
    optional: true

# Final verification
- assertVisible:
    id: "expected-result-element"

# Take screenshot for debugging
- takeScreenshot: "flow-complete"
```

## Tag Strategy for CI/CD

| Tag | Purpose | When to Run |
|-----|---------|-------------|
| `smokeTest` | Critical path, fast | Every PR |
| `regression` | Full test suite | Nightly |
| `phase6` | Phase-specific tests | Phase release |
| `util` | Helper flows (exclude) | Never standalone |

**config.yaml**:
```yaml
flows:
  - "*/*"
excludeTags:
  - util
```

**GitHub Actions**:
```yaml
# PR - Smoke tests only
maestro test maestro/ --include-tags smokeTest

# Nightly - Full suite
maestro test maestro/
```

## Debugging Flaky Tests

### Step 1: Identify the Flakiness Pattern

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| "Element not found" | Timing issue | Increase `extendedWaitUntil` timeout |
| "Assertion is false: X is visible" | Element not loaded yet | Add `extendedWaitUntil` before assertion |
| Works locally, fails in CI | Environment difference | Use `id:` selectors, increase timeouts |
| Random failures | Point selectors | Replace `point:` with `id:` |

### Step 2: Debug Commands

```bash
# Run with debug output
maestro test --debug maestro/01-onboarding.yaml

# View hierarchy to find elements
maestro hierarchy

# Interactive testing with Maestro Studio
maestro studio
```

### Step 3: Common Fixes

**Problem**: `Assertion is false: "true" is visible`
```yaml
# BEFORE - Broken (checking literal "true")
- extendedWaitUntil:
    visible: true
    timeout: 15000

# AFTER - Fixed (checking for actual element)
- extendedWaitUntil:
    visible:
      id: "main-screen-element"
    timeout: 15000
```

**Problem**: Button not found after navigation
```yaml
# Add wait after navigation
- tapOn:
    id: "navigate-button"

- extendedWaitUntil:
    visible:
      id: "destination-element"
    timeout: 10000

- tapOn:
    id: "destination-element"
```

## iOS-Specific Best Practices

### SwiftUI accessibilityIdentifier Naming

```swift
// Use semantic, hierarchical naming
.accessibilityIdentifier("onboarding-welcome-cta")
.accessibilityIdentifier("onboarding-struggles-next")
.accessibilityIdentifier("nudge-card-primary-button")

// For dynamic elements, include the identifier
ForEach(problems) { problem in
    Button(problem.name) { ... }
        .accessibilityIdentifier("onboarding-struggle-\(problem.id)")
}
```

### Handling iOS Permission Dialogs

```yaml
# Notification permission (Japanese/English)
- tapOn:
    text: "許可|Allow"
    optional: true

# ATT permission
- tapOn:
    text: "許可|Allow Tracking"
    optional: true

# Location permission
- tapOn:
    text: "Appの使用中は許可|Allow While Using App"
    optional: true
```

### RevenueCat Test Store (Payment E2E)

Source: [RevenueCat Test Store](https://www.revenuecat.com/docs/test-and-launch/sandbox/test-store)

RC Test Store replaces StoreKit Configuration for E2E tests. No Apple sandbox credentials needed.

**Prerequisites**:
- RC SDK >= 5.43.0
- Test Store API Key (`test_` prefix, Debug only)
- Products + Offerings in RC Dashboard
- **`uiPreviewMode: true` in SubscriptionService.configure() (DEBUG builds)**
  iOS 18.4+/26.x シミュレータでは StoreKit が products を返さない (GitHub #4954)。
  RC SDK の SimulatedStoreProductsManager は Web Billing API を使うが Test Store products 未対応。
  `uiPreviewMode` で mock products を生成して回避する。
  詳細: `us-005b-monetization.md` の「SubscriptionService.configure() パターン」

**Purchase dialog button labels** (RC SDK 5.60.0, `SimulatedStorePurchaseUI.swift`):
- Success: `"Test valid purchase"` (⚠️ NOT "Simulate Success")
- Failure: `"Test failed purchase"` (⚠️ NOT "Simulate Failure")
- Cancel: `"Cancel"`

```yaml
# Payment success test (monthly)
- tapOn:
    id: "paywall_plan_monthly"
- extendedWaitUntil:
    visible: "Test valid purchase"
    timeout: 10000
- tapOn: "Test valid purchase"
- extendedWaitUntil:
    visible:
      id: "timer_countdown"    # Post-purchase screen
    timeout: 10000

# Payment failure test
- tapOn:
    id: "paywall_plan_monthly"
- extendedWaitUntil:
    visible: "Test failed purchase"
    timeout: 10000
- tapOn: "Test failed purchase"
- extendedWaitUntil:
    visible:
      id: "paywall_plan_monthly"  # Returns to paywall
    timeout: 5000
```

### Paywall Dismissal

```yaml
# Soft paywall dismiss (Maybe Later)
- tapOn:
    id: "paywall_maybe_later"
    optional: true
```

## File Organization

```
maestro/
├── config.yaml              # Global configuration
├── README.md                # Documentation
├── 01-onboarding.yaml       # Core flow (numbered for order)
├── 02-paywall.yaml          # Core flow
├── phase6/                  # Feature-specific directory
│   ├── 01-llm-nudge.yaml
│   └── 02-feedback.yaml
└── common/                  # Shared utility flows
    └── login.yaml           # Tagged with 'util', excluded from standalone runs
```

## Checklist Before Merge

| Check | Description |
|-------|-------------|
| [ ] Uses `id:` selectors (not `point:`) | Reliability |
| [ ] Has appropriate timeouts (30s for CI) | CI stability |
| [ ] Uses `optional: true` for dialogs | Non-deterministic handling |
| [ ] Starts with `clearState` + `clearKeychain` | Clean state |
| [ ] Has correct tags (`smokeTest`, etc.) | CI filtering |
| [ ] Takes screenshots at key points | Debugging |
| [ ] Runs locally 3x without failure | Flakiness check |

## Quick Reference

### Common Commands

```yaml
# Wait for element
- extendedWaitUntil:
    visible:
      id: "element-id"
    timeout: 30000

# Tap by ID
- tapOn:
    id: "element-id"

# Tap by text (fallback)
- tapOn:
    text: "Button Text"

# Optional tap (for dialogs)
- tapOn:
    text: "Allow"
    optional: true

# Assert visibility
- assertVisible:
    id: "element-id"

# Input text
- inputText: "Hello World"

# Clear and type
- clearText
- inputText: "New Text"

# Scroll
- scroll

# Screenshot
- takeScreenshot: "filename"
```

### Timeout Guidelines

| Context | Timeout |
|---------|---------|
| App launch | 15000ms |
| Screen transition | 5000-10000ms |
| Element visibility | 30000ms (CI) |
| Animation completion | Use `waitForAnimationToEnd` |

---

## Troubleshooting: Simulator Build Issues

### 問題: 古いビルドがシミュレータに残っている

**症状**:
- 削除した画面（ATT等）がまだ表示される
- コード変更が反映されない
- `fastlane build_for_simulator` で「Could not find .app bundle」エラー

**原因**: fastlane がビルドしても `.app` がインストールされないことがある

**解決策**:
```bash
# 1. DerivedData をクリーン
rm -rf aniccaios/build/DerivedData

# 2. 再ビルド
cd aniccaios && fastlane build_for_simulator

# 3. 手動でインストール
xcrun simctl install "iPhone 16 Pro" "build/DerivedData/Build/Products/Debug-iphonesimulator/aniccaios.app"
```

### 問題: DEBUG ビルドで Paywall がスキップされる

**症状**: sandbox ユーザーでオンボーディング後に Paywall が表示されない

**原因**: sandbox の過去トライアルで `isEntitled=true` が残っている

**解決策**: DEBUG では entitlement に関係なく Paywall を強制表示
```swift
#if DEBUG
showPaywall = true
return
#endif
```

### 問題: Maestro で要素が見つからない

**症状**: `Element not found: Text matching regex: .*次へ.*`

**解決策**: 必ず `inspect_view_hierarchy` で実際のテキストを確認してからセレクターを決定

---

## Fix Loop (Automated Test Repair)

When a Maestro test fails, follow this closed-loop repair cycle:

```
maestro test maestro/<flow>.yaml:
  PASS → next flow
  FAIL → diagnose:
    YAML error (wrong id, selector mismatch):
      → Fix YAML → retry
    Swift error (missing a11y identifier, wrong label):
      → Fix Swift → fastlane build_for_simulator → retry
    上限なし。全フロー PASS するまで繰り返す。BLOCKED にしない。
```

### Diagnosis Commands

```bash
# Check actual view hierarchy
maestro hierarchy

# Interactive debugging
maestro studio

# Run single flow with debug output
maestro test --debug maestro/01-onboarding.yaml
```

### Common Fix Patterns

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| "Element not found: id: X" | a11y ID not set in Swift | Add `.accessibilityIdentifier("X")` + rebuild |
| "Element not found: text: X" | Text changed or localized | Use `id:` selector instead |
| Timeout on "Test valid purchase" | RC Test Store not configured or uiPreviewMode missing | Check API Key in Info.plist + SubscriptionService.configure() uiPreviewMode pattern |
| Flow passes locally, fails CI | Timing issue | Increase `extendedWaitUntil` timeout |

**Remember**: The goal is **zero flakiness**. Every test should pass 100% of the time in CI. If a test is flaky, fix the test, not the retry count.
