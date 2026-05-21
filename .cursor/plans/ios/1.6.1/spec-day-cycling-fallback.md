# Day-Cycling Fallback 仕様書

## 概要

ルールベースNudgeのfallback時に、Thompson Samplingではなく**Day-Cycling**を使用して、バリアントを順番に回す。これにより、同じメッセージが連日来ることを防ぎ、全バリアントを均等に使用する。

---

## 問題（As-Is）

### 現在の動作

| Day | 優先度1 | 優先度2 |
|-----|---------|---------|
| Day 1 | 決定論的割り当て (`slotIndex % variantCount`) | - |
| Day 2+ | LLMキャッシュ | Thompson Sampling (fallback) |

### Thompson Samplingの問題

- **同じバリアントが選ばれがち**: パフォーマンスの良いバリアントを優先するため
- **翌日に同じメッセージ**: 永続化なし、運任せ
- **2週間サイクル保証なし**: 14バリアントあっても順番に回らない

### 影響

| 問題 | 結果 |
|------|------|
| Day 3で「またこのメッセージ？」 | ユーザー離脱、通知オフ |
| 飽き → 解約 | LTV低下 |

---

## 解決策（To-Be）

### Day-Cyclingアルゴリズム

```
variantIndex = (dayIndex * slotsPerDay + slotIndex) % variantCount
```

| 変数 | 説明 |
|------|------|
| `dayIndex` | オンボーディング完了日からの経過日数（0-indexed） |
| `slotsPerDay` | その問題タイプの1日あたりのスロット数 |
| `slotIndex` | 当日内のスロット順序（0-indexed） |
| `variantCount` | バリアント総数（14 or 21） |

### 新しい動作

| Day | 優先度1 | 優先度2 |
|-----|---------|---------|
| Day 1 | 決定論的割り当て (既存) | - |
| Day 2+ | LLMキャッシュ | **Day-Cycling** (fallback) |

### サイクル日数

| ProblemType | バリアント数 | スロット/日 | サイクル日数 | 繰り返し開始 |
|-------------|-------------|------------|-------------|--------------|
| staying_up_late | 21 | 5 | **21日** | Day 22 = Day 1 |
| 他12種類 | 14 | 3 | **14日** | Day 15 = Day 1 |

**計算式**: `サイクル日数 = variantCount / GCD(variantCount, slotsPerDay)`

- porn_addiction: 14 / GCD(14, 3) = 14 / 1 = **14日**
- staying_up_late: 21 / GCD(21, 5) = 21 / 1 = **21日**

---

## 実装変更

### 1. NudgeStatsManager.swift に追加

**ファイル**: `aniccaios/aniccaios/Services/NudgeStatsManager.swift`

```diff
+    // MARK: - Day-Cycling Support
+    
+    private let onboardingDateKey = "com.anicca.onboardingDate"
+    
+    /// オンボーディング完了日からの経過日数を取得
+    /// - Returns: 経過日数（0 = 今日がオンボーディング日）
+    func getDaysSinceOnboarding(for problemType: String) -> Int {
+        let key = "\(onboardingDateKey)_\(problemType)"
+        let defaults = UserDefaults.standard
+        
+        guard let startDate = defaults.object(forKey: key) as? Date else {
+            // 初回: 今日を記録してDay 0を返す
+            defaults.set(Date(), forKey: key)
+            logger.info("Day-Cycling: First day for \(problemType), recording onboarding date")
+            return 0
+        }
+        
+        let calendar = Calendar.current
+        let days = calendar.dateComponents([.day], from: calendar.startOfDay(for: startDate), to: calendar.startOfDay(for: Date())).day ?? 0
+        return max(0, days)
+    }
+    
+    #if DEBUG
+    /// DEBUG用: オンボーディング日をリセット
+    func resetOnboardingDate(for problemType: String) {
+        let key = "\(onboardingDateKey)_\(problemType)"
+        UserDefaults.standard.removeObject(forKey: key)
+        logger.info("DEBUG: Reset onboarding date for \(problemType)")
+    }
+    
+    /// DEBUG用: オンボーディング日を過去に設定
+    func setOnboardingDate(for problemType: String, daysAgo: Int) {
+        let key = "\(onboardingDateKey)_\(problemType)"
+        let pastDate = Calendar.current.date(byAdding: .day, value: -daysAgo, to: Date()) ?? Date()
+        UserDefaults.standard.set(pastDate, forKey: key)
+        logger.info("DEBUG: Set onboarding date for \(problemType) to \(daysAgo) days ago")
+    }
+    #endif
```

**挿入位置**: Line 287 (`resetVariantStats` の後、`// MARK: - Storage` の前)

---

### 2. NudgeContentSelector.swift の変更

**ファイル**: `aniccaios/aniccaios/Services/NudgeContentSelector.swift`

#### 2a. Day-Cyclingメソッド追加

```diff
+    // MARK: - Day-Cycling (v1.6.1)
+    
+    /// Day-Cycling: バリアントを順番に回す
+    /// - 毎日同じスロットで異なるバリアントを表示
+    /// - variantCount ÷ slotsPerDay 日後に一巡
+    /// - Parameters:
+    ///   - problem: 問題タイプ
+    ///   - slotIndex: 当日内のスロット順序（0-indexed）
+    /// - Returns: バリアントインデックス
+    func dayCyclingVariant(for problem: ProblemType, slotIndex: Int) -> Int {
+        let dayIndex = NudgeStatsManager.shared.getDaysSinceOnboarding(for: problem.rawValue)
+        let variantCount = problem.notificationVariantCount
+        let slotsPerDay = problem.notificationSchedule.count
+        
+        // (dayIndex * slotsPerDay + slotIndex) % variantCount
+        let variant = (dayIndex * slotsPerDay + slotIndex) % variantCount
+        
+        logger.info("🔄 Day-Cycling: day=\(dayIndex) slot=\(slotIndex) → variant=\(variant) for \(problem.rawValue)")
+        return variant
+    }
```

**挿入位置**: Line 121 (`day1VariantIndex` の閉じブレースの後)

---

#### 2b. selectVariant のfallbackロジック変更

```diff
     /// v1.5.1: usedVariants重複排除 + Day1決定論的割り当て対応版
     func selectVariant(
         for problem: ProblemType,
         scheduledHour: Int,
         slotIndex: Int,
         usedVariants: Set<Int>,
         isDay1: Bool
     ) -> (variantIndex: Int, isAIGenerated: Bool, content: LLMGeneratedNudge?) {
         // Day 1: 決定論的割り当てを最優先（LLMより先に判定）
         // Day1ではThompson Samplingデータもないため、研究ベースの固定マッピングを使用
         if isDay1 {
             let variant = day1VariantIndex(for: problem, slotIndex: slotIndex)
             logger.info("📋 Day1 deterministic variant \(variant) for \(problem.rawValue) slot \(slotIndex)")
             return (variantIndex: variant, isAIGenerated: false, content: nil)
         }

         // Day 2+: LLMキャッシュがあれば優先
         if let llmNudge = LLMNudgeCache.shared.getNudge(for: problem, hour: scheduledHour) {
             logger.info("🤖 Selected LLM-generated nudge for \(problem.rawValue) at hour \(scheduledHour)")
             return (variantIndex: -1, isAIGenerated: true, content: llmNudge)
         }

-        // Day 2+: Thompson Sampling with usedVariants重複排除
-        let selectedVariant = selectExistingVariant(for: problem, scheduledHour: scheduledHour, usedVariants: usedVariants)
-        logger.info("📋 Selected rule-based variant \(selectedVariant) for \(problem.rawValue) at hour \(scheduledHour)")
+        // Day 2+: Day-Cycling fallback（v1.6.1: Thompson Sampling → Day-Cycling に変更）
+        // NOTE: usedVariants パラメータはAPI互換性のため残すが、Day-Cyclingでは使用しない
+        let selectedVariant = dayCyclingVariant(for: problem, slotIndex: slotIndex)
+        logger.info("🔄 Day-Cycling fallback variant \(selectedVariant) for \(problem.rawValue) at hour \(scheduledHour)")
         return (variantIndex: selectedVariant, isAIGenerated: false, content: nil)
     }
```

**変更箇所**: Line 44-47

---

#### 2c. selectVariantForDebug の変更（一貫性確保）

```diff
     #if DEBUG
     /// デバッグ用: 時刻を無視してLLMを取得（v1.5.0: LLM優先）
     func selectVariantForDebug(for problem: ProblemType) -> (variantIndex: Int, isAIGenerated: Bool, content: LLMGeneratedNudge?) {
         // LLMキャッシュにあれば常にLLM
         if let llmNudge = LLMNudgeCache.shared.getNudgeAnyHour(for: problem) {
             logger.info("🤖 [Debug] Selected LLM nudge for \(problem.rawValue)")
             return (variantIndex: -1, isAIGenerated: true, content: llmNudge)
         }

         // LLMキャッシュがなければルールベースにフォールバック
         logger.info("⚠️ [Debug] No LLM cache for \(problem.rawValue), using rule-based")
-        let selectedVariant = selectExistingVariant(for: problem, scheduledHour: 21)
-        logger.info("📋 [Debug] Selected rule-based variant \(selectedVariant) for \(problem.rawValue)")
+        // v1.6.1: Day-Cycling を使用（本番と同じ挙動）
+        let selectedVariant = dayCyclingVariant(for: problem, slotIndex: 0)
+        logger.info("🔄 [Debug] Day-Cycling variant \(selectedVariant) for \(problem.rawValue)")
         return (variantIndex: selectedVariant, isAIGenerated: false, content: nil)
     }
     #endif
```

**変更箇所**: Line 59-64

---

#### 2d. selectExistingVariantTestable の変更（テスト互換）

```diff
     /// テスト可能なバリアント選択（usedVariants対応）
-    func selectExistingVariantTestable(for problem: ProblemType, scheduledHour: Int, usedVariants: Set<Int> = []) -> Int {
-        let allVariants = getGenericVariantIndices(for: problem)
-        let available = allVariants.filter { !usedVariants.contains($0) }
-
-        // All variants used → reset and use full set
-        let candidates = available.isEmpty ? allVariants : available
-
-        guard !candidates.isEmpty else { return 0 }
-
-        // Thompson Sampling on available candidates
-        return selectByThompsonSampling(variants: candidates, problem: problem, hour: scheduledHour)
+    func selectExistingVariantTestable(for problem: ProblemType, scheduledHour: Int, usedVariants: Set<Int> = [], slotIndex: Int = 0) -> Int {
+        // v1.6.1: Day-Cycling を使用
+        return dayCyclingVariant(for: problem, slotIndex: slotIndex)
     }
```

**変更箇所**: Line 122-134

---

### 3. テスト追加

**ファイル**: `aniccaios/aniccaiosTests/DayCyclingTests.swift` (新規)

```swift
import XCTest
@testable import aniccaios

final class DayCyclingTests: XCTestCase {
    
    // MARK: - Day-Cycling Formula Tests
    
    func test_dayCycling_day0_slot0_returnsVariant0() {
        // (0 * 3 + 0) % 14 = 0
        let result = calculateDayCyclingVariant(dayIndex: 0, slotIndex: 0, slotsPerDay: 3, variantCount: 14)
        XCTAssertEqual(result, 0)
    }
    
    func test_dayCycling_day0_slot2_returnsVariant2() {
        // (0 * 3 + 2) % 14 = 2
        let result = calculateDayCyclingVariant(dayIndex: 0, slotIndex: 2, slotsPerDay: 3, variantCount: 14)
        XCTAssertEqual(result, 2)
    }
    
    func test_dayCycling_day1_slot0_returnsVariant3() {
        // (1 * 3 + 0) % 14 = 3
        let result = calculateDayCyclingVariant(dayIndex: 1, slotIndex: 0, slotsPerDay: 3, variantCount: 14)
        XCTAssertEqual(result, 3)
    }
    
    func test_dayCycling_day4_slot2_wrapsAround() {
        // (4 * 3 + 2) % 14 = 14 % 14 = 0
        let result = calculateDayCyclingVariant(dayIndex: 4, slotIndex: 2, slotsPerDay: 3, variantCount: 14)
        XCTAssertEqual(result, 0)
    }
    
    func test_dayCycling_stayingUpLate_day0() {
        // stayingUpLate: 5 slots, 21 variants
        // (0 * 5 + 0) % 21 = 0
        // (0 * 5 + 4) % 21 = 4
        XCTAssertEqual(calculateDayCyclingVariant(dayIndex: 0, slotIndex: 0, slotsPerDay: 5, variantCount: 21), 0)
        XCTAssertEqual(calculateDayCyclingVariant(dayIndex: 0, slotIndex: 4, slotsPerDay: 5, variantCount: 21), 4)
    }
    
    func test_dayCycling_stayingUpLate_day4_wrapsAround() {
        // (4 * 5 + 1) % 21 = 21 % 21 = 0
        let result = calculateDayCyclingVariant(dayIndex: 4, slotIndex: 1, slotsPerDay: 5, variantCount: 21)
        XCTAssertEqual(result, 0)
    }
    
    func test_dayCycling_noDuplicatesWithinDay() {
        // 1日内で重複がないことを確認
        for dayIndex in 0..<14 {
            var variants: Set<Int> = []
            for slotIndex in 0..<3 {
                let variant = calculateDayCyclingVariant(dayIndex: dayIndex, slotIndex: slotIndex, slotsPerDay: 3, variantCount: 14)
                XCTAssertFalse(variants.contains(variant), "Day \(dayIndex) has duplicate variant \(variant)")
                variants.insert(variant)
            }
        }
    }
    
    func test_dayCycling_14days_allVariantsUsed3Times() {
        // 14日間で各バリアントが3回ずつ使われることを確認
        var variantCounts: [Int: Int] = [:]
        
        for dayIndex in 0..<14 {
            for slotIndex in 0..<3 {
                let variant = calculateDayCyclingVariant(dayIndex: dayIndex, slotIndex: slotIndex, slotsPerDay: 3, variantCount: 14)
                variantCounts[variant, default: 0] += 1
            }
        }
        
        // 14日 × 3スロット = 42通知, 14バリアント → 各3回
        for variant in 0..<14 {
            XCTAssertEqual(variantCounts[variant], 3, "Variant \(variant) should appear exactly 3 times")
        }
    }
    
    // MARK: - Helper
    
    private func calculateDayCyclingVariant(dayIndex: Int, slotIndex: Int, slotsPerDay: Int, variantCount: Int) -> Int {
        return (dayIndex * slotsPerDay + slotIndex) % variantCount
    }
}
```

---

## 2週間タイムテーブル

### porn_addiction（14バリアント × 3スロット/日）

計算式: `(dayIndex * 3 + slotIndex) % 14`

| Day | dayIndex | 20:30 (slot 0) | 22:30 (slot 1) | 23:45 (slot 2) | 同日重複 |
|-----|----------|----------------|----------------|----------------|----------|
| 1 | 0 | V0 | V1 | V2 | ✅ なし |
| 2 | 1 | V3 | V4 | V5 | ✅ なし |
| 3 | 2 | V6 | V7 | V8 | ✅ なし |
| 4 | 3 | V9 | V10 | V11 | ✅ なし |
| 5 | 4 | V12 | V13 | **V0** | ✅ なし |
| 6 | 5 | V1 | V2 | V3 | ✅ なし |
| 7 | 6 | V4 | V5 | V6 | ✅ なし |
| 8 | 7 | V7 | V8 | V9 | ✅ なし |
| 9 | 8 | V10 | V11 | V12 | ✅ なし |
| 10 | 9 | V13 | **V0** | V1 | ✅ なし |
| 11 | 10 | V2 | V3 | V4 | ✅ なし |
| 12 | 11 | V5 | V6 | V7 | ✅ なし |
| 13 | 12 | V8 | V9 | V10 | ✅ なし |
| 14 | 13 | V11 | V12 | V13 | ✅ なし |

**一巡**: Day 5 slot 2 で V0 が再登場（4.67日サイクル）

### staying_up_late（21バリアント × 5スロット/日）

計算式: `(dayIndex * 5 + slotIndex) % 21`

| Day | dayIndex | 20:00 | 22:00 | 23:30 | 00:00 | 01:00 | 同日重複 |
|-----|----------|-------|-------|-------|-------|-------|----------|
| 1 | 0 | V0 | V1 | V2 | V3 | V4 | ✅ なし |
| 2 | 1 | V5 | V6 | V7 | V8 | V9 | ✅ なし |
| 3 | 2 | V10 | V11 | V12 | V13 | V14 | ✅ なし |
| 4 | 3 | V15 | V16 | V17 | V18 | V19 | ✅ なし |
| 5 | 4 | V20 | **V0** | V1 | V2 | V3 | ✅ なし |
| 6 | 5 | V4 | V5 | V6 | V7 | V8 | ✅ なし |
| 7 | 6 | V9 | V10 | V11 | V12 | V13 | ✅ なし |

**一巡**: Day 5 slot 1 で V0 が再登場（4.2日サイクル）

---

## シナリオ別動作

### シナリオ1: LLM生成が完璧に動作

| Day | 動作 |
|-----|------|
| Day 1 | 決定論的割り当て (V0, V1, V2...) |
| Day 2+ | 🤖 LLM生成（毎回ユニーク） |

**重複**: なし

### シナリオ2: 特定スロットでLLMが失敗（部分fallback）

| Day | 20:30 | 22:30 | 23:45 (LLM失敗) |
|-----|-------|-------|-----------------|
| 1 | V0 (Day1) | V1 (Day1) | V2 (Day1) |
| 2 | 🤖 LLM | 🤖 LLM | V5 (Day-Cycling) |
| 3 | 🤖 LLM | 🤖 LLM | V8 (Day-Cycling) |
| 4 | 🤖 LLM | 🤖 LLM | V11 (Day-Cycling) |
| 5 | 🤖 LLM | 🤖 LLM | V0 (Day-Cycling) |

### シナリオ3: 完全ルールベースfallback

上記タイムテーブル通り。Day-Cyclingで順番に回る。

---

## 影響範囲

| ファイル | 変更内容 | 行数 |
|---------|---------|------|
| `NudgeStatsManager.swift` | `getDaysSinceOnboarding` 追加 | +30行 |
| `NudgeContentSelector.swift` | `dayCyclingVariant` 追加 + fallback変更 | +25行, 変更3行 |
| `DayCyclingTests.swift` | 新規テスト | +80行 |

---

## テスト計画

### ユニットテスト

| テスト | 期待結果 |
|-------|---------|
| `test_dayCycling_day0_slot0_returnsVariant0` | 0 |
| `test_dayCycling_day4_slot2_wrapsAround` | 0 (一巡) |
| `test_dayCycling_noDuplicatesWithinDay` | 全日で重複なし |
| `test_dayCycling_14days_allVariantsUsed3Times` | 各バリアント3回 |

### 手動テスト

| テスト | 手順 | 期待結果 |
|-------|------|---------|
| Day 1動作確認 | オンボーディング直後 | V0, V1, V2... |
| Day 2 fallback確認 | LLMキャッシュなし | V3, V4, V5... |
| 一巡確認 | Day 5まで待機 | V0が再登場 |

---

## 既存テストの更新

### NotificationHotfixTests.swift

以下のテストはDay-Cyclingで動作が変わるため更新が必要:

```diff
-    // MARK: - P4: usedVariants 重複排除
-
-    func test_selectVariant_respectsUsedVariants() {
-        let selector = NudgeContentSelector.shared
-        // usedVariants に variant 0-12 を入れると、唯一残りの variant 13 が選ばれるはず
-        // v1.6.1: anxiety は14バリアント
-        let result1 = selector.selectExistingVariantTestable(for: .anxiety, scheduledHour: 10, usedVariants: Set(0..<13))
-        XCTAssertEqual(result1, 13, "With variants 0-12 used, should select 13")
-
-        // 全バリアント使用済み → usedVariants クリアしてフォールバック
-        // v1.6.1: anxiety は14バリアント
-        let result = selector.selectExistingVariantTestable(for: .anxiety, scheduledHour: 10, usedVariants: Set(0..<14))
-        XCTAssertNotNil(result)
-        XCTAssertTrue((0..<14).contains(result), "Should still return a valid variant index")
-    }
+    // MARK: - P4: Day-Cycling（v1.6.1: usedVariants → Day-Cycling に変更）
+
+    func test_selectVariant_dayCycling_usesDayAndSlot() {
+        let selector = NudgeContentSelector.shared
+        // Day-Cycling: usedVariantsは無視され、(dayIndex * slotsPerDay + slotIndex) % variantCount で決定
+        // Day 0, slot 0 → variant 0
+        let result = selector.selectExistingVariantTestable(for: .anxiety, scheduledHour: 10, usedVariants: [], slotIndex: 0)
+        // dayIndexは実行日により変動するため、0-13の範囲内であることを確認
+        XCTAssertTrue((0..<14).contains(result), "Day-Cycling should return a valid variant")
+    }
+
+    func test_selectVariant_dayCycling_differentSlots_differentVariants() {
+        let selector = NudgeContentSelector.shared
+        // 同日内で異なるスロットは異なるバリアントを返す
+        let result0 = selector.selectExistingVariantTestable(for: .anxiety, scheduledHour: 10, usedVariants: [], slotIndex: 0)
+        let result1 = selector.selectExistingVariantTestable(for: .anxiety, scheduledHour: 10, usedVariants: [], slotIndex: 1)
+        let result2 = selector.selectExistingVariantTestable(for: .anxiety, scheduledHour: 10, usedVariants: [], slotIndex: 2)
+        
+        // 3つとも異なるはず（同日内重複なし）
+        let uniqueVariants = Set([result0, result1, result2])
+        XCTAssertEqual(uniqueVariants.count, 3, "Same day, different slots should return different variants")
+    }
```

---

## デプロイ

1. **iOS変更あり** → App Store提出必要
2. **Backend変更なし**
3. **既存ユーザー影響**: オンボーディング日がない場合、アップデート日がDay 0になる

---

## 削除予定コード

Thompson Sampling関連のコードは残しておく（将来的にLLM学習に使用する可能性があるため）。
ただし、`selectExistingVariant` は内部でのみ使用し、fallbackでは使わない。

---

*Last updated: 2026-02-04*
