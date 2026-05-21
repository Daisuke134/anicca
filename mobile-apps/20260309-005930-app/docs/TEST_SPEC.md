# Test Specification: LumaRed

Source: [Apple Developer: XCTest](https://developer.apple.com/documentation/xctest) — 「Write unit tests to verify the behavior of individual components in isolation.」
Source: [Maestro: E2E Testing](https://maestro.mobile.dev/) — 「Use accessibilityIdentifier for stable, maintainable selectors.」
Source: [Martin Fowler: Test Pyramid](https://martinfowler.com/bliki/TestPyramid.html) — 「Unit 70% / Integration 20% / E2E 10%」

---

## 1. Test Strategy

```
         ┌───────┐
         │  E2E  │  10%  — Maestro (6 flows)
         ├───────┤
         │ Integ │  20%  — XCTest + Protocol DI
         ├───────┤
         │ Unit  │  70%  — XCTest + Mock Services
         └───────┘
```

| 種別 | フレームワーク | 実行方法 |
|------|-------------|---------|
| Unit | XCTest | `fastlane test` |
| Integration | XCTest | `fastlane test` |
| E2E | Maestro | `maestro test maestro/` |

**Coverage 目標: 80%+**

---

## 2. Unit Tests

最低 30 テスト。全 Service + Model をカバー。

### SessionService (10 tests)

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `testSaveAndFetchSession` | SessionService | セッション保存 → 取得が同一オブジェクトを返す |
| `testFetchAllReturnsSorted` | SessionService | fetchAll() が日付降順で返す |
| `testFreeTierLimit7Days` | SessionService | Free ユーザーは直近7日分のみ取得できる |
| `testPremiumNoLimit` | SessionService | Premium ユーザーは全セッション取得 |
| `testCurrentStreakZeroOnNoSessions` | SessionService | セッションなし → streak = 0 |
| `testCurrentStreakConsecutiveDays` | SessionService | 連続3日 → streak = 3 |
| `testCurrentStreakBrokenOnGap` | SessionService | 2日空き → streak リセット |
| `testTotalDuration` | SessionService | 全セッション秒数の合計 |
| `testSaveEmptySessionList` | SessionService | 空配列保存 → fetchAll() が [] を返す |
| `testPersistenceAcrossInstances` | SessionService | 再初期化後も保存データ保持 |

### SubscriptionService (8 tests)

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `testIsPremiumFalseOnInit` | SubscriptionService | 未購入状態 → isPremium = false |
| `testIsPremiumTrueAfterPurchase` | MockSubscriptionService | 購入完了 → isPremium = true |
| `testPurchaseCallsRevenueCat` | SubscriptionService | purchase() が Purchases.shared.purchase を呼ぶ |
| `testRestorePurchasesUpdatesState` | SubscriptionService | restorePurchases() → isPremium 更新 |
| `testCheckEntitlementSetsState` | SubscriptionService | checkEntitlement() → isPremium 更新 |
| `testPurchaseCancellationSilent` | SubscriptionService | ユーザーキャンセル → エラーなし |
| `testPurchaseNetworkErrorThrows` | SubscriptionService | ネットワークエラー → throws |
| `testMockServiceDI` | Protocol DI | MockSubscriptionService をDI注入できる |

### TimerViewModel (7 tests)

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `testInitialStateIsIdle` | TimerViewModel | 初期状態 = .idle |
| `testStartTransitionsToRunning` | TimerViewModel | start() → .running |
| `testPauseTransitionsToPaused` | TimerViewModel | pause() → .paused |
| `testResumeTransitionsToRunning` | TimerViewModel | resume() → .running |
| `testStopTransitionsToIdle` | TimerViewModel | stop() → .idle |
| `testCountdownDecrements` | TimerViewModel | 1秒後に remainingSeconds が 1 減る |
| `testCompletionTriggeredAtZero` | TimerViewModel | remainingSeconds = 0 → isComplete = true |

### Data Models (5 tests)

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `testSessionEncodeDecode` | Session | Codable ラウンドトリップ |
| `testLightProtocolEncodeDecode` | LightProtocol | Codable ラウンドトリップ |
| `testBodyPartAllCases` | BodyPart | CaseIterable が 5 ケース |
| `testProtocolLibraryNotEmpty` | ProtocolLibrary | protocols.count >= 3 (Free tier) |
| `testProtocolLibraryHas5Protocols` | ProtocolLibrary | protocols.count == 5 |

### NotificationService (3 tests)

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `testRequestPermissionReturnsResult` | NotificationService | requestPermission() → Bool |
| `testScheduleSessionCompleteNotification` | NotificationService | UNTimeIntervalNotificationTrigger が登録される |
| `testCancelAllRemovesNotifications` | NotificationService | cancelAll() → pendingNotifications.count == 0 |

---

## 3. Integration Tests

### Service-ViewModel Integration

| Test Name | Services | What It Verifies |
|-----------|---------|-----------------|
| `testTimerCompletionSavesSession` | TimerViewModel + SessionService | タイマー完了 → Session が自動保存される |
| `testSubscriptionStateUpdatesDashboard` | SubscriptionService + DashboardViewModel | Premium 購入 → Dashboard の制限が解除される |
| `testProtocolLockBasedOnSubscription` | SubscriptionService + HomeViewModel | Free → Premium ロック状態の切り替え |
| `testSessionServiceFreeTierFiltering` | SessionService + DashboardViewModel | Free ユーザーの Dashboard に 7日制限が反映 |
| `testNotificationPermissionUpdatesSettings` | NotificationService + SettingsViewModel | 通知許可状態が設定画面に反映 |
| `testPaywallPurchaseEnablesLockedProtocols` | SubscriptionService + HomeViewModel | 購入後に Back & Spine / Full Body が解除 |

---

## 4. E2E Tests (Maestro)

Source: [Maestro Docs](https://maestro.mobile.dev/api-reference/commands) — 「Use id: selectors (accessibilityIdentifier). Never use point: coordinates.」

**全ファイル共通ルール:**
- `clearState: true` (アプリリセット)
- `takeScreenshot:` (各主要ステップ)
- `id:` セレクタのみ（point: 禁止）
- `smokeTest: true` が 2 ファイル以上に必要

| File | Scenario | Key Assertions | Tag |
|------|---------|---------------|-----|
| `onboarding.yaml` | 初回起動 → オンボーディング → Maybe Later | `welcome_get_started_button` 表示, `paywall_maybe_later_button` タップでMain App表示 | smokeTest |
| `timer.yaml` | プロトコル選択 → タイマー開始 → 完了 | `protocol_card_face` タップ, `timer_countdown_label` 表示, セッション保存 | smokeTest |
| `settings.yaml` | 設定画面 → 通知トグル → Upgrade表示 | `settings_notification_toggle` 操作, `settings_upgrade_button` → Paywall表示 | — |
| `payment-monthly.yaml` | Paywall → Monthly 選択 → 購入フロー | `paywall_monthly_card` タップ, `paywall_subscribe_button` タップ | — |
| `payment-annual.yaml` | Paywall → Annual 選択 → 購入フロー | `paywall_annual_card` タップ, `paywall_subscribe_button` タップ | — |
| `payment-failure.yaml` | Paywall → Cancel → Maybe Later | サブスク拒否後 `paywall_maybe_later_button` でアプリ継続 | — |

**accessibilityIdentifier → UX_SPEC.md §7 完全対応:**

全 E2E で使用する ID は UX_SPEC.md §7 の一覧と 1:1 対応。追加 ID は UX_SPEC.md に先に追記してから E2E に使用する。

---

## 5. Greenlight Checks

Source: [CLAUDE.md CRITICAL Rules]() — 必須チェック。CI/CDで自動実行。

**🔴 Rule 17: tracking-SDK 完全禁止（Greenlight が自動検出）**

```bash
# fastlane test — Greenlight が tracking-SDK を検出 = CRITICAL
# 対象: tracking-SDK, analytics-framework, third-party-analytics
# → greenlight preflight でゼロを確認
greenlight preflight ./LumaRedios 2>&1 | grep "CRITICAL" | grep -v "0 CRITICAL" && echo "FAIL: tracking-SDK detected" || echo "PASS: Rule 17"
```

**🔴 Rule 20: RC-UI-library 禁止**

```bash
# 許可: RevenueCat SDK のみ（purchases-ios）
# 禁止: RC-UI-library（purchases-ios の UI コンポーネント拡張）
# → greenlight が import 文を検出
greenlight preflight ./LumaRedios 2>&1 | grep "RC-UI\|CRITICAL" | grep -v "0 CRITICAL" && echo "FAIL: RC-UI-library found" || echo "PASS: Rule 20"
```

**🔴 Rule 20b: ATT 禁止（AppTracking 系 API 完全不使用）**

```bash
# 禁止: ATT 関連クラス、NSUserTrackingUsageDescription
# → PrivacyInfo.xcprivacy に tracking 記述なしであることを確認
# → greenlight が ATT 混入を検出
greenlight preflight ./LumaRedios 2>&1 | grep "ATT\|CRITICAL" | grep -v "0 CRITICAL" && echo "FAIL: ATT found" || echo "PASS: Rule 20b"
```

**🔴 Rule 21: AI API / 外部 AI サービス完全禁止**

```bash
# 禁止: third-party-AI-API, google-AI-SDK, apple-on-device-AI（iOS 26+ のみ）
# 月収 $29 vs API コスト $300+ のため一切禁止
# → greenlight が AI SDK import を検出
greenlight preflight ./LumaRedios 2>&1 | grep "AI\|CRITICAL" | grep -v "0 CRITICAL" && echo "FAIL: AI SDK found" || echo "PASS: Rule 21"
```

**🔴 Greenlight (外部ツール)**

```bash
# greenlight CLI — CRITICAL = 0 であることを確認
greenlight preflight ./LumaRedios 2>&1 | grep "CRITICAL" | grep -v "0 CRITICAL" && echo "FAIL: Greenlight CRITICAL" || echo "PASS: Greenlight"
```

---

## 6. Performance Targets

Source: [Apple Developer: Performance](https://developer.apple.com/documentation/xcode/improving-your-app-s-performance) — 「Target cold launch under 400ms on minimum deployment target device.」

| 指標 | 目標値 | 測定方法 |
|------|-------|---------|
| Cold Launch Time | < 2.0秒 | Xcode Instruments: Time Profiler |
| Memory (idle) | < 50 MB | Xcode Organizer |
| Memory (timer active) | < 80 MB | Xcode Instruments |
| Battery (1hr session) | < 5% | Xcode Energy Log |
| UI Frame Rate | 60 fps (99%ile) | Xcode Instruments: Core Animation |
| UserDefaults Write | < 10ms | XCTest measureMetrics |
| Session List Render (100 items) | < 16ms | SwiftUI List benchmark |

---

## 7. Test Commands

| タスク | コマンド |
|--------|---------|
| Unit + Integration 実行 | `fastlane test` |
| E2E 全フロー実行 | `maestro test maestro/` |
| E2E smoke テストのみ | `maestro test --tags smokeTest maestro/` |
| カバレッジレポート生成 | `fastlane test` → `coverage/report.html` |
| Greenlight チェック | `greenlight preflight ./LumaRedios` |
| Rule 17 チェック | `greenlight preflight ./LumaRedios` (tracking-SDK 検出) |
| Rule 20 チェック | `greenlight preflight ./LumaRedios` (RC-UI-library 検出) |
| Rule 20b チェック | `greenlight preflight ./LumaRedios` (ATT 系 API 検出) |
| Rule 21 チェック | `greenlight preflight ./LumaRedios` (third-party-AI-API 検出) |
