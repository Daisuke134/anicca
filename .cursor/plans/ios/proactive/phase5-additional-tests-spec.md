# Phase 5 追加テスト Spec

> **バージョン**: 1.1.0
>
> **最終更新**: 2026年1月23日
>
> **目的**: Phase 5 で漏れていたタイミング最適化（時刻シフト）のテストを追加

---

## 概要

### 問題

Phase 5 の実装で「2日連続無視 → 30分シフト」と「最大シフト120分」のテストが漏れていた。

### 解決

1. `ProblemNotificationScheduler` にテスト可能なメソッドを抽出
2. 不足しているテストを追加し、全 To-Be がカバーされている状態にする

---

## To-Be チェックリスト

| # | To-Be | テスト | 状態 |
|---|-------|--------|------|
| 1 | Thompson Sampling でバリアント選択 | `test_selectByThompsonSampling_favors_high_alpha()` | ✅ 済 |
| 2 | 時刻固定バリアント（0時→3、1時→4） | `test_selectVariant_returns_time_specific_variant()` | ✅ 済 |
| 3 | 7日連続無反応 → 未試行バリアント優先 | `test_isCompletelyUnresponsive_returns_true()` | ✅ 済 |
| 4 | 連続 ignored 日数取得（バリアント横断で最大値） | `test_getConsecutiveIgnoredDays_returns_max_across_variants()` | ⬜ 追加 |
| 5 | **2日連続無視で +30分シフト** | `test_calculateNewShift_adds_30_when_consecutive_2_or_more()` | ⬜ 追加 |
| 6 | **最大シフト120分** | `test_calculateNewShift_respects_max_120_minutes()` | ⬜ 追加 |
| 7 | **consecutive < 2 ならシフトなし** | `test_calculateNewShift_no_shift_when_consecutive_less_than_2()` | ⬜ 追加 |
| 8 | タップで連続無視日数リセット | `test_recordTapped_resets_consecutive_ignored()` | ✅ 済 |

---

## As-Is

### 現在の実装（ProblemNotificationScheduler.swift:62-64）

```swift
if consecutiveIgnored >= 2 && currentShift < maxShiftMinutes {
    let newShift = min(currentShift + 30, maxShiftMinutes)
    // ...
}
```

### 問題

1. シフト計算ロジックが `scheduleNotifications()` async メソッドに埋め込まれている
2. 単体テストが困難
3. テストが存在しない

---

## To-Be

### 変更 1: テスト可能なメソッドを抽出

**ファイル**: `aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift`

```swift
// MARK: - Phase 5: Shift Calculation (Testable)

/// シフト量を計算（純粋関数、テスト可能）
/// - Parameters:
///   - currentShift: 現在のシフト量（分）
///   - consecutiveIgnored: 連続無視日数
/// - Returns: 新しいシフト量（分）、最大 maxShiftMinutes まで
func calculateNewShift(currentShift: Int, consecutiveIgnored: Int) -> Int {
    guard consecutiveIgnored >= 2 else { return currentShift }
    return min(currentShift + 30, maxShiftMinutes)
}
```

**既存コードの変更**: `scheduleNotifications()` 内で新メソッドを使用

```swift
// Before:
if consecutiveIgnored >= 2 && currentShift < maxShiftMinutes {
    let newShift = min(currentShift + 30, maxShiftMinutes)
    // ...
}

// After:
let newShift = calculateNewShift(currentShift: currentShift, consecutiveIgnored: consecutiveIgnored)
if newShift > currentShift {
    // ...
}
```

---

### 変更 2: テスト追加

**ファイル**: `aniccaios/aniccaiosTests/ProblemNotificationSchedulerTests.swift`（新規作成）

```swift
import XCTest
@testable import aniccaios

final class ProblemNotificationSchedulerTests: XCTestCase {

    var scheduler: ProblemNotificationScheduler!

    override func setUp() {
        super.setUp()
        scheduler = ProblemNotificationScheduler.shared
    }

    // MARK: - calculateNewShift Tests

    /// consecutive < 2 ならシフトなし
    func test_calculateNewShift_no_shift_when_consecutive_less_than_2() {
        // consecutive = 0
        XCTAssertEqual(scheduler.calculateNewShift(currentShift: 0, consecutiveIgnored: 0), 0)

        // consecutive = 1
        XCTAssertEqual(scheduler.calculateNewShift(currentShift: 0, consecutiveIgnored: 1), 0)

        // currentShift があっても consecutive < 2 なら変わらない
        XCTAssertEqual(scheduler.calculateNewShift(currentShift: 30, consecutiveIgnored: 1), 30)
    }

    /// consecutive >= 2 で +30分シフト
    func test_calculateNewShift_adds_30_when_consecutive_2_or_more() {
        // consecutive = 2, currentShift = 0 → 30
        XCTAssertEqual(scheduler.calculateNewShift(currentShift: 0, consecutiveIgnored: 2), 30)

        // consecutive = 3, currentShift = 30 → 60
        XCTAssertEqual(scheduler.calculateNewShift(currentShift: 30, consecutiveIgnored: 3), 60)

        // consecutive = 5, currentShift = 60 → 90
        XCTAssertEqual(scheduler.calculateNewShift(currentShift: 60, consecutiveIgnored: 5), 90)
    }

    /// 最大シフトは 120分
    func test_calculateNewShift_respects_max_120_minutes() {
        // currentShift = 90, consecutive = 10 → 120 (capped)
        XCTAssertEqual(scheduler.calculateNewShift(currentShift: 90, consecutiveIgnored: 10), 120)

        // currentShift = 100, consecutive = 5 → 120 (capped, not 130)
        XCTAssertEqual(scheduler.calculateNewShift(currentShift: 100, consecutiveIgnored: 5), 120)

        // currentShift = 120 (already max), consecutive = 10 → 120 (stays at max)
        XCTAssertEqual(scheduler.calculateNewShift(currentShift: 120, consecutiveIgnored: 10), 120)
    }
}
```

---

### 変更 3: NudgeStatsManager テスト追加

**ファイル**: `aniccaios/aniccaiosTests/NudgeStatsManagerTests.swift`（既存に追加）

```swift
/// 連続 ignored 日数がバリアント横断で最大値を返すこと
func test_getConsecutiveIgnoredDays_returns_max_across_variants() {
    // Arrange
    NudgeStatsManager.shared.resetAllStats()

    // Act: variant 0 に 5日、variant 1 に 3日の ignored を記録
    NudgeStatsManager.shared.debugRecordIgnored(
        problemType: "staying_up_late",
        variantIndex: 0,
        scheduledHour: 22,
        count: 5
    )
    NudgeStatsManager.shared.debugRecordIgnored(
        problemType: "staying_up_late",
        variantIndex: 1,
        scheduledHour: 22,
        count: 3
    )

    // Assert: 最大値（5）が返る
    let consecutive = NudgeStatsManager.shared.getConsecutiveIgnoredDays(
        problemType: "staying_up_late",
        hour: 22
    )
    XCTAssertEqual(consecutive, 5, "Should return max consecutive ignored days across variants")
}
```

---

## テストマトリックス（更新後）

| # | To-Be | テスト名 | ファイル | 状態 |
|---|-------|----------|----------|------|
| 1 | Thompson Sampling | `test_selectByThompsonSampling_favors_high_alpha()` | NudgeContentSelectorTests | ✅ |
| 2 | 時刻固定バリアント | `test_selectVariant_returns_time_specific_variant()` | NudgeContentSelectorTests | ✅ |
| 3 | 7日連続無反応 | `test_isCompletelyUnresponsive_returns_true()` | NudgeStatsManagerTests | ✅ |
| 4 | 連続 ignored 日数（max） | `test_getConsecutiveIgnoredDays_returns_max_across_variants()` | NudgeStatsManagerTests | ⬜ 追加 |
| 5 | consecutive < 2 シフトなし | `test_calculateNewShift_no_shift_when_consecutive_less_than_2()` | ProblemNotificationSchedulerTests | ⬜ 追加 |
| 6 | consecutive >= 2 で +30分 | `test_calculateNewShift_adds_30_when_consecutive_2_or_more()` | ProblemNotificationSchedulerTests | ⬜ 追加 |
| 7 | 最大シフト 120分 | `test_calculateNewShift_respects_max_120_minutes()` | ProblemNotificationSchedulerTests | ⬜ 追加 |
| 8 | タップでリセット | `test_recordTapped_resets_consecutive_ignored()` | NudgeStatsManagerTests | ✅ |

---

## 実装手順

### Step 1: ProblemNotificationScheduler にメソッド追加

```bash
# 編集対象
aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift
```

1. `calculateNewShift(currentShift:consecutiveIgnored:)` メソッドを追加
2. `scheduleNotifications()` 内で新メソッドを使用するようリファクタリング

### Step 2: テストファイル作成

```bash
# 新規作成
aniccaios/aniccaiosTests/ProblemNotificationSchedulerTests.swift
```

### Step 3: 既存テストに追加

```bash
# 編集対象
aniccaios/aniccaiosTests/NudgeStatsManagerTests.swift
```

### Step 4: ビルド＆テスト

```bash
cd aniccaios && xcodebuild test \
  -project aniccaios.xcodeproj \
  -scheme aniccaios-staging \
  -destination 'platform=iOS Simulator,name=iPhone 16 Pro,OS=18.6' \
  -only-testing:aniccaiosTests \
  2>&1 | xcpretty
```

---

## レビューチェックリスト

- [x] 全 To-Be がテストマトリックスに含まれているか
- [x] 各 To-Be に対応するテストコードがあるか
- [x] テストは独立しているか（他のテストに依存しない）
- [x] テストが実際のロジックをテストしているか（フェイクでない）
- [x] Edge case がカバーされているか（0, 1, 2, max, over-max）
- [x] パッチは完全か（コピペで動くレベル）

---

**最終更新**: 2026年1月23日
