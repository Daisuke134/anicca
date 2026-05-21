# Test Specification: VagusReset

Source: [Apple XCTest Documentation](https://developer.apple.com/documentation/xctest) — 「Write tests that verify your code works correctly and stays correct as you iterate」
Source: [Google Testing Blog — Test Pyramid](https://testing.googleblog.com/2015/04/just-say-no-to-more-end-to-end-tests.html) — 「Unit: 70%, Integration: 20%, E2E: 10%」
Source: [Maestro Documentation](https://maestro.mobile.dev) — 「Write mobile UI tests with id: selectors for reliability」

---

## 1. Test Strategy

```
                    E2E Tests (Maestro)
                    ─────────────────
                       10%  6 flows

               Integration Tests (XCTest)
               ──────────────────────────
                    20%  8 test cases

        Unit Tests (XCTest + MockServiceProtocol)
        ─────────────────────────────────────────
                 70%  30+ test cases
```

| Layer | Tool | Target | Pass Criteria |
|-------|------|--------|---------------|
| Unit | XCTest | Models, Services, ViewModels | `fastlane test` → 0 failures |
| Integration | XCTest | Service 間連携 | `fastlane test` → 0 failures |
| E2E | Maestro | 全主要フロー | `maestro test maestro/` → all PASS |

---

## 2. Unit Tests

**最低30テスト、全 Service + Model をカバー**

### StreakServiceTests（8テスト）

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `testInitialStreakIsZero` | `StreakService` | 初期値 streak = 0 |
| `testRecordFirstSession` | `StreakService.recordSessionCompletion` | 初回記録 → streak = 1 |
| `testConsecutiveDays` | `StreakService.recordSessionCompletion` | 連続2日記録 → streak = 2 |
| `testNonConsecutiveDayResetsStreak` | `StreakService.recordSessionCompletion` | 1日空けると streak = 1（リセット）|
| `testSameDay` | `StreakService.recordSessionCompletion` | 同日2回記録 → streak 変わらず（1のまま）|
| `testGetCompletedDates` | `StreakService.getCompletedDates` | 記録した日付が正確に返る |
| `testLastSessionDate` | `StreakService.getLastSessionDate` | 最終記録日が正確 |
| `testClearAllResets` | `StreakService（UserDefaults clear）` | UserDefaults クリアで初期化 |

### SessionViewModelTests（6テスト）

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `testTimerStartsCorrectly` | `SessionViewModel.start()` | `isRunning = true`、`timeRemaining = durationSeconds` |
| `testTimerDecrements` | `SessionViewModel` + `Timer` | 1秒後に `timeRemaining` が 1 減る |
| `testTimerPause` | `SessionViewModel.pause()` | `isRunning = false`、時間は止まる |
| `testTimerResume` | `SessionViewModel.resume()` | `isRunning = true`、残り時間から再開 |
| `testTimerCompletion` | `SessionViewModel` | 0秒到達 → `isComplete = true` |
| `testBackgroundRestoration` | `SessionViewModel.restoreFromBackground()` | バックグラウンド経過時間を正確に補正 |

### ExerciseRepositoryTests（5テスト）

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `testLoadAllExercises` | `ExerciseRepository.loadAll()` | 20件以上のエクササイズが返る |
| `testFreeExercisesCount` | `ExerciseRepository.loadFree()` | 正確に5件返る |
| `testPremiumExercisesCount` | `ExerciseRepository.loadPremium()` | `isPremium == true` のみ返る |
| `testExerciseDecodable` | `Exercise.init(from:)` | JSON から `Exercise` に正しくデコード |
| `testExerciseCategories` | `Exercise.category` | 5カテゴリ（humming/gargling/cold/diaphragm/laughter）が全て存在 |

### SubscriptionServiceTests（6テスト — MockSubscriptionService 使用）

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `testIsPremiumFalseByDefault` | `MockSubscriptionService.isPremium` | 初期値 false |
| `testPurchaseSuccessSetsPremium` | `MockSubscriptionService.purchase` | 購入成功 → `isPremium = true` |
| `testPurchaseFailureThrows` | `MockSubscriptionService.purchase` | エラー時に `throw` |
| `testRestoreSuccessSetsPremium` | `MockSubscriptionService.restorePurchases` | 復元成功 → `isPremium = true` |
| `testFetchOfferingsReturnsPackages` | `MockSubscriptionService.fetchOfferings` | 月額 + 年額の2パッケージ返る |
| `testProtocolConformance` | `SubscriptionService: SubscriptionServiceProtocol` | 実装クラスがプロトコルに準拠 |

### NotificationServiceTests（5テスト）

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `testScheduleDaily` | `NotificationService.scheduleDaily` | リクエストが `UNUserNotificationCenter` に登録される |
| `testCancelAllRemovesRequests` | `NotificationService.cancelAll` | 全保留通知が削除される |
| `testPermissionDenied` | `NotificationService.requestPermission` | 拒否時に `false` が返る |
| `testDailyTriggerIsCalendar` | スケジュール済みリクエスト | トリガーが `UNCalendarNotificationTrigger` |
| `testNotificationBody` | 通知コンテンツ | body に「迷走神経」または "vagus" を含む |

---

## 3. Integration Tests

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `testHomeViewModelLoadsExercises` | `HomeViewModel` + `ExerciseRepository` | ViewModel が Repository からエクササイズを取得して `@Published exercises` に反映 |
| `testHomeViewModelPremiumFiltering` | `HomeViewModel` + `MockSubscriptionService` | 非プレミアム時に free 5件のみ表示 |
| `testSessionCompletionUpdatesStreak` | `SessionViewModel` + `StreakService` | セッション完了 → `StreakService.recordSessionCompletion` が呼ばれる |
| `testOnboardingFlowComplete` | `OnboardingViewModel` + `UserDefaults` | [Maybe Later] タップ → `onboarding.complete = true` |
| `testSettingsViewModelLoadsPremiumState` | `SettingsViewModel` + `MockSubscriptionService` | プレミアム時に Upgrade ボタン非表示 |
| `testNotificationScheduledAfterPermission` | `OnboardingStep2` + `NotificationService` | 許可後に `scheduleDaily` が呼ばれる |
| `testPaywallPurchaseUpdatesHomeView` | `PaywallView` + `HomeViewModel` | 購入成功後 HomeView が全エクササイズを表示 |
| `testStreakResetAfterMissedDay` | `HomeViewModel` + `StreakService` | 前日セッションなし → streak 通知トリガー |

---

## 4. E2E Tests (Maestro)

Source: [Maestro Documentation](https://maestro.mobile.dev) — 「Use id: selectors — they are stable across layout changes」
Source: UX_SPEC.md §7 — accessibilityIdentifier 一覧（ID は UX_SPEC と一致必須）

| File | Scenario | Key Assertions | Tag |
|------|----------|---------------|-----|
| `maestro/onboarding.yaml` | オンボーディング完全フロー + [Maybe Later] | `onboarding_step1_next_button` 表示 → `paywall_maybe_later_button` タップ → ホーム到達 | `smokeTest` |
| `maestro/timer.yaml` | エクササイズ選択 → セッション開始 → 完了 | `home_exercise_card_humming-01` タップ → `session_start_button` → 完了画面 | `smokeTest` |
| `maestro/settings.yaml` | 設定タブ → Upgrade → Paywall 遷移 | `settings_upgrade_button` タップ → `paywall_cta_button` 表示 | — |
| `maestro/payment_monthly.yaml` | 月額購入フロー（sandbox） | `paywall_monthly_plan_card` 選択 → `paywall_cta_button` → 購入完了 | — |
| `maestro/payment_annual.yaml` | 年額購入フロー（sandbox） | `paywall_annual_plan_card` 選択 → `paywall_cta_button` → 購入完了 | — |
| `maestro/payment_failure.yaml` | 購入失敗 → エラーメッセージ表示 | Sandbox Declined カード → エラーアラート表示 | — |

**全フロー共通ルール:**

| ルール | 実装 |
|--------|------|
| `clearState: true` | 各フロー冒頭で状態クリア |
| `takeScreenshot` | 主要ステップ後にスクリーンショット |
| `id:` セレクターのみ | `point:` セレクター禁止 |
| `smokeTest` タグ | onboarding + timer（2フロー）に付与 |

---

## 5. Greenlight Checks

Source: CLAUDE.md CRITICAL Rules — Rule 17 / 20 / 20b / 21

```bash
# Rule 17: tracking / data-collection SDK 禁止
# 検出パターン: 分析・トラッキング系 SDK の import (Swift ファイルのみ)
# 対象 SDK: MixP-SDK / FB-SDK / AmpSeg-SDK 等
grep -rE "^import (MixP|FB|Amplitude|Segment|Braze)" --include="*.swift" . && echo "FAIL: Rule 17 violation" || echo "PASS: Rule 17"

# Rule 20: RC-UI-package 禁止（自前 PaywallView 必須）
# 検出パターン: RC-UI-package の import (Swift ファイルのみ)
grep -rE "^import RC-UI-package" --include="*.swift" . && echo "FAIL: Rule 20 violation" || echo "PASS: Rule 20"

# Rule 20b: ATT 禁止
# 検出パターン: AppTrackingTransparency / ATTManager の使用 (Swift ファイルのみ)
grep -rE "^import AppTrackingTransparency|ATTManager" --include="*.swift" . && echo "FAIL: Rule 20b violation" || echo "PASS: Rule 20b"

# Rule 21: AI API / AI モデル / 外部 AI サービス完全禁止（月額収益 $29 vs API コスト $300+）
# 検出パターン: 外部 AI SDK の import (OA-SDK / GGA-SDK / FM-iOS26 等) (Swift ファイルのみ)
grep -rE "^import (OA-SDK|GGA-SDK|FM-iOS26)" --include="*.swift" . && echo "FAIL: Rule 21 violation" || echo "PASS: Rule 21"

# Mock が本番コードに混入していないか
grep -rw "class Mock" --include="*.swift" . | grep -v "Tests/" && echo "FAIL: Mock in production" || echo "PASS: no Mock leak"

# PrivacyInfo.xcprivacy が存在するか
test -f VagusResetios/Resources/PrivacyInfo.xcprivacy && echo "PASS: PrivacyInfo exists" || echo "FAIL: PrivacyInfo missing"
```

---

## 6. Performance Targets

| Metric | Target | Measurement Tool |
|--------|--------|-----------------|
| 起動時間（cold start） | < 2.0s | Xcode Instruments（Time Profiler） |
| セッション画面到達 | < 0.3s（タップから） | Xcode Instruments |
| メモリ使用量（通常操作） | < 80 MB | Xcode Memory Gauge |
| タイマー精度 | ± 0.1s 以内 | XCTest `measure()` |
| JSON 読み込み（loadAll） | < 50ms | `XCTestExpectation.fulfill()` |
| UI フレームレート | 60fps（タイマーアニメーション） | Xcode Instruments（Core Animation） |
| クラッシュフリー率 | 99.5%+ | Xcode Organizer |

---

## 7. Test Commands

| Task | Command |
|------|---------|
| Unit + Integration テスト実行 | `cd VagusResetios && fastlane test` |
| E2E テスト全実行 | `maestro test maestro/` |
| smokeTest のみ実行 | `maestro test --tags smokeTest maestro/` |
| 特定フロー実行 | `maestro test maestro/onboarding.yaml` |
| Greenlight チェック | `greenlight preflight VagusResetios/` |
| カバレッジレポート生成 | `fastlane test` → Xcode の Coverage タブ確認 |
