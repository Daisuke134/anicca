# Phase 5 Fix Spec - 残タスク仕様書

**作成日**: 2026年1月21日  
**目的**: Phase 5 の残りのタスク（ignored 閾値修正、Unit Tests、CI/CD、E2E、リリース）の詳細仕様

---

## 📋 タスク一覧

| # | タスク | 優先度 | 状態 |
|---|--------|--------|------|
| 1 | ~~CLAUDE.md にテストルールを追加~~ | 🟢 | ✅ 完了 |
| 2 | ~~ignored 閾値を 15分に修正~~ | 🔴 重大 | ✅ 完了 |
| 3 | ~~Unit Tests を書く~~ | 🔴 重大 | ✅ 完了 (14 tests) |
| 4 | ~~iOS 用 GitHub Actions を追加~~ | 🟡 中 | ✅ 完了 |
| 5 | ~~Maestro E2E を書く~~ | 🟡 中 | ✅ 完了 |
| 6 | ~~全テスト PASS 確認~~ | 🔴 重大 | ✅ 完了 |
| 7 | release/1.2.0 ブランチ作成 | 🟢 低 | ⬜ 未着手 |
| 8 | TestFlight ビルド | 🟢 低 | ⬜ 未着手 |
| 9 | UI 確認（ユーザー） | 🟢 低 | ⬜ 未着手 |
| 10 | App Store 提出 | 🟢 低 | ⬜ 未着手 |

---

## タスク 2: ignored 閾値を 15分に修正

### 現状

**ファイル**: `aniccaios/aniccaios/Services/NudgeStatsManager.swift`

**現在の実装**:
```swift
private static let ignoredThresholdMinutes = 24 * 60 // 24時間 = 1440分
```

### 問題点

- Phase 5 仕様書では **15分** で ignored 判定すると定義されている
- 現在は **24時間（1440分）** になっている

### 修正内容

```swift
// 修正前
private static let ignoredThresholdMinutes: Int = 1440  // 24時間

// 修正後
#if DEBUG
private static let ignoredThresholdMinutes: Int = 1   // デバッグ: 1分（テスト用）
#else
private static let ignoredThresholdMinutes: Int = 15  // 本番: 15分
#endif
```

**理由**: デバッグビルドでは 1分で ignored 判定することで、テストが高速になる。

### 検証方法

1. アプリを起動
2. 通知をスケジュール
3. 15分以上待つ（または時刻を進める）
4. アプリを再起動
5. `DEBUG: Recorded ignored for xxx` のログが出ることを確認

---

## タスク 3: Unit Tests を書く

### 必要なテストファイル

| ファイル | テスト対象 | 優先度 |
|---------|-----------|--------|
| `BetaDistributionTests.swift` | `BetaDistribution.sample()` | 🔴 必須 |
| `NudgeContentSelectorTests.swift` | `selectVariant()`, Thompson Sampling | 🔴 必須 |
| `NudgeStatsManagerTests.swift` | `isCompletelyUnresponsive()`, `selectUntriedVariant()` | 🔴 必須 |
| `ProblemNotificationSchedulerTests.swift` | タイミングシフト、最大シフト制限 | 🟡 推奨 |

### テストケース詳細

#### 3.1 BetaDistributionTests.swift

```swift
import XCTest
@testable import aniccaios

final class BetaDistributionTests: XCTestCase {
    
    // MARK: - sample() のテスト
    
    /// sample() は 0〜1 の範囲の値を返すこと
    func test_sample_returns_value_between_0_and_1() {
        let distribution = BetaDistribution(alpha: 1.0, beta: 1.0)
        
        for _ in 0..<1000 {
            let sample = distribution.sample()
            XCTAssertGreaterThanOrEqual(sample, 0.0)
            XCTAssertLessThanOrEqual(sample, 1.0)
        }
    }
    
    /// alpha が高いと sample の平均値が高くなること
    func test_sample_higher_alpha_produces_higher_mean() {
        let lowAlpha = BetaDistribution(alpha: 1.0, beta: 10.0)
        let highAlpha = BetaDistribution(alpha: 10.0, beta: 1.0)
        
        let lowSamples = (0..<1000).map { _ in lowAlpha.sample() }
        let highSamples = (0..<1000).map { _ in highAlpha.sample() }
        
        let lowMean = lowSamples.reduce(0, +) / Double(lowSamples.count)
        let highMean = highSamples.reduce(0, +) / Double(highSamples.count)
        
        XCTAssertLessThan(lowMean, 0.2, "Low alpha mean should be < 0.2")
        XCTAssertGreaterThan(highMean, 0.8, "High alpha mean should be > 0.8")
    }
    
    /// alpha=1, beta=1 は一様分布（平均 0.5 付近）
    func test_sample_uniform_distribution_has_mean_around_05() {
        let distribution = BetaDistribution(alpha: 1.0, beta: 1.0)
        
        let samples = (0..<10000).map { _ in distribution.sample() }
        let mean = samples.reduce(0, +) / Double(samples.count)
        
        XCTAssertGreaterThan(mean, 0.45)
        XCTAssertLessThan(mean, 0.55)
    }
}
```

#### 3.2 NudgeContentSelectorTests.swift

```swift
import XCTest
@testable import aniccaios

@MainActor
final class NudgeContentSelectorTests: XCTestCase {

    // NudgeContentSelector はシングルトンなので shared を使用

    override func setUp() {
        super.setUp()
        // テスト前に統計をリセット
        NudgeStatsManager.shared.resetAllStats()
    }

    override func tearDown() {
        NudgeStatsManager.shared.resetAllStats()
        super.tearDown()
    }

    // MARK: - selectVariant() のテスト

    /// 初回呼び出しで有効なバリアントを返すこと (stayingUpLate)
    func test_selectVariant_returns_valid_variant_for_stayingUpLate() {
        let variant = NudgeContentSelector.shared.selectVariant(for: .stayingUpLate, scheduledHour: 22)

        // stayingUpLate の汎用バリアントは [0, 1, 2, 5, 6, 7, 8, 9]
        let validVariants = [0, 1, 2, 5, 6, 7, 8, 9]
        XCTAssertTrue(validVariants.contains(variant), "Variant \(variant) should be in \(validVariants)")
    }

    /// 他の問題タイプでは 0〜7 のバリアントを返すこと
    func test_selectVariant_returns_valid_variant_for_other_problems() {
        let problems: [ProblemType] = [.cantWakeUp, .selfLoathing, .procrastination, .anxiety]

        for problem in problems {
            let variant = NudgeContentSelector.shared.selectVariant(for: problem, scheduledHour: 9)
            XCTAssertGreaterThanOrEqual(variant, 0)
            XCTAssertLessThanOrEqual(variant, 7)
        }
    }

    /// 時刻固定バリアントが正しく選択されること（0時と1時）
    func test_selectVariant_returns_time_specific_variant_at_correct_hour() {
        // 0時（深夜0時）は stayingUpLate の時刻固定バリアント 3
        let variant0 = NudgeContentSelector.shared.selectVariant(for: .stayingUpLate, scheduledHour: 0)
        XCTAssertEqual(variant0, 3, "At 00:00, should select variant 3 (midnight)")

        // 1時（深夜1時）は stayingUpLate の時刻固定バリアント 4
        let variant1 = NudgeContentSelector.shared.selectVariant(for: .stayingUpLate, scheduledHour: 1)
        XCTAssertEqual(variant1, 4, "At 01:00, should select variant 4 (1 AM)")
    }

    /// 22時などの通常時間帯では汎用バリアントから選択されること
    func test_selectVariant_does_not_return_time_specific_variant_at_other_hours() {
        let variant22 = NudgeContentSelector.shared.selectVariant(for: .stayingUpLate, scheduledHour: 22)

        // 22時は時刻固定が発動しないので、Thompson Sampling が汎用バリアント [0,1,2,5,6,7,8,9] から選択
        // Note: 3, 4 は genericVariants に含まれないため、絶対に返らない
        let validVariants = [0, 1, 2, 5, 6, 7, 8, 9]
        XCTAssertTrue(validVariants.contains(variant22), "At 22:00, should select a generic variant")
    }
    
    // MARK: - Thompson Sampling のテスト

    /// tapped が多いバリアントが選ばれやすいこと
    func test_selectVariant_favors_high_tapped_variants() {
        // バリアント 0 に多くの tapped を記録
        for _ in 0..<20 {
            NudgeStatsManager.shared.recordTapped(
                problemType: "procrastination",
                variantIndex: 0,
                scheduledHour: 10
            )
        }

        // バリアント 1 に多くの ignored を記録（debugRecordIgnored を使用）
        NudgeStatsManager.shared.debugRecordIgnored(
            problemType: "procrastination",
            variantIndex: 1,
            scheduledHour: 10,
            count: 20
        )

        // 100回選択して、バリアント 0 が多く選ばれることを確認
        var variant0Count = 0
        for _ in 0..<100 {
            let variant = NudgeContentSelector.shared.selectVariant(for: .procrastination, scheduledHour: 10)
            if variant == 0 {
                variant0Count += 1
            }
        }

        XCTAssertGreaterThan(variant0Count, 60, "High-tapped variant should be selected > 60% of the time")
    }
}
```

#### 3.3 NudgeStatsManagerTests.swift

**注意**: `recordIgnored` は private メソッドなので、テストでは `debugRecordIgnored` を使用する。
また、`isCompletelyUnresponsive` は `consecutiveIgnoredDays >= 7`（全バリアント）をチェックする。

```swift
import XCTest
@testable import aniccaios

@MainActor
final class NudgeStatsManagerTests: XCTestCase {

    override func setUp() {
        super.setUp()
        NudgeStatsManager.shared.resetAllStats()
    }

    override func tearDown() {
        NudgeStatsManager.shared.resetAllStats()
        super.tearDown()
    }

    // MARK: - isCompletelyUnresponsive() のテスト
    // 実装: 全バリアントが 7日以上連続 ignored なら true

    /// 連続 ignored が 7日未満では false を返すこと
    func test_isCompletelyUnresponsive_returns_false_when_consecutive_less_than_7() {
        // 6日連続 ignored を記録（7日未満）
        NudgeStatsManager.shared.debugRecordIgnored(
            problemType: "staying_up_late",
            variantIndex: 0,
            scheduledHour: 22,
            count: 6
        )

        let result = NudgeStatsManager.shared.isCompletelyUnresponsive(
            for: "staying_up_late",
            hour: 22
        )

        XCTAssertFalse(result, "Should return false when consecutiveIgnoredDays < 7")
    }

    /// 全バリアントが 7日以上連続 ignored なら true を返すこと
    func test_isCompletelyUnresponsive_returns_true_when_all_variants_7_consecutive_ignored() {
        // 全バリアント（0-7）に 7日連続 ignored を記録
        for variant in 0..<8 {
            NudgeStatsManager.shared.debugRecordIgnored(
                problemType: "staying_up_late",
                variantIndex: variant,
                scheduledHour: 22,
                count: 7
            )
        }

        let result = NudgeStatsManager.shared.isCompletelyUnresponsive(
            for: "staying_up_late",
            hour: 22
        )

        XCTAssertTrue(result, "Should return true when all variants have 7+ consecutive ignored days")
    }

    /// tapped が記録されると連続 ignored がリセットされること
    func test_recordTapped_resets_consecutive_ignored() {
        // 5日連続 ignored を記録
        NudgeStatsManager.shared.debugRecordIgnored(
            problemType: "staying_up_late",
            variantIndex: 0,
            scheduledHour: 22,
            count: 5
        )

        // tapped を記録（連続 ignored がリセットされる）
        NudgeStatsManager.shared.recordTapped(
            problemType: "staying_up_late",
            variantIndex: 0,
            scheduledHour: 22
        )

        let consecutive = NudgeStatsManager.shared.getConsecutiveIgnoredDays(
            problemType: "staying_up_late",
            hour: 22
        )

        XCTAssertEqual(consecutive, 0, "Consecutive ignored days should reset to 0 after tap")
    }

    // MARK: - selectUntriedVariant() のテスト

    /// まだ試されていないバリアントを返すこと
    func test_selectUntriedVariant_returns_untried_variant() {
        // バリアント 0, 1, 2 を試したことにする
        for variant in 0..<3 {
            NudgeStatsManager.shared.debugRecordIgnored(
                problemType: "anxiety",
                variantIndex: variant,
                scheduledHour: 9,
                count: 1
            )
        }

        let availableVariants = [0, 1, 2, 3, 4, 5, 6, 7]
        let untried = NudgeStatsManager.shared.selectUntriedVariant(
            for: "anxiety",
            hour: 9,
            availableVariants: availableVariants
        )

        XCTAssertNotNil(untried)
        XCTAssertTrue([3, 4, 5, 6, 7].contains(untried!), "Should return an untried variant")
    }

    /// 全バリアントが試されていたらサンプル数最小のバリアントを返すこと
    func test_selectUntriedVariant_returns_least_tested_when_all_tried() {
        // 全バリアントを試す（バリアント 0 は 1回、他は 3回）
        NudgeStatsManager.shared.debugRecordIgnored(
            problemType: "anxiety",
            variantIndex: 0,
            scheduledHour: 9,
            count: 1
        )
        for variant in 1..<8 {
            NudgeStatsManager.shared.debugRecordIgnored(
                problemType: "anxiety",
                variantIndex: variant,
                scheduledHour: 9,
                count: 3
            )
        }

        let availableVariants = [0, 1, 2, 3, 4, 5, 6, 7]
        let selected = NudgeStatsManager.shared.selectUntriedVariant(
            for: "anxiety",
            hour: 9,
            availableVariants: availableVariants
        )

        // サンプル数最小のバリアント 0 が選ばれるはず
        XCTAssertEqual(selected, 0, "Should return the least tested variant")
    }

    // MARK: - consecutiveIgnoredDays のテスト

    /// 連続 ignored 日数が正しくカウントされること
    func test_getConsecutiveIgnoredDays_increments_correctly() {
        // 初期状態は 0
        let initial = NudgeStatsManager.shared.getConsecutiveIgnoredDays(
            problemType: "rumination",
            hour: 20
        )
        XCTAssertEqual(initial, 0)

        // 3回 ignored を記録
        NudgeStatsManager.shared.debugRecordIgnored(
            problemType: "rumination",
            variantIndex: 0,
            scheduledHour: 20,
            count: 3
        )

        let afterThree = NudgeStatsManager.shared.getConsecutiveIgnoredDays(
            problemType: "rumination",
            hour: 20
        )
        XCTAssertEqual(afterThree, 3)
    }
}
```

---

## タスク 4: iOS 用 GitHub Actions を追加

### ファイル

**作成**: `.github/workflows/ios-ci.yml`

### 内容

```yaml
name: iOS CI

on:
  push:
    branches: [dev, main]
    paths:
      - 'aniccaios/**'
      - '.github/workflows/ios-ci.yml'
  pull_request:
    branches: [dev, main]
    paths:
      - 'aniccaios/**'

jobs:
  unit-tests:
    name: Unit & Integration Tests
    runs-on: macos-14
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Xcode
        uses: maxim-lobanov/setup-xcode@v1
        with:
          xcode-version: '16.0'
      
      - name: Cache SPM
        uses: actions/cache@v4
        with:
          path: |
            ~/Library/Caches/org.swift.swiftpm
            ~/Library/Developer/Xcode/DerivedData
          key: ${{ runner.os }}-spm-${{ hashFiles('aniccaios/aniccaios.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved') }}
          restore-keys: |
            ${{ runner.os }}-spm-
      
      - name: Run Tests
        working-directory: aniccaios
        run: |
          set -o pipefail
          xcodebuild test \
            -project aniccaios.xcodeproj \
            -scheme aniccaios-staging \
            -destination 'platform=iOS Simulator,name=iPhone 15,OS=17.2' \
            -only-testing:aniccaiosTests \
            | xcpretty --color

  e2e-tests:
    name: E2E Tests (Maestro)
    runs-on: macos-14
    needs: unit-tests
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Xcode
        uses: maxim-lobanov/setup-xcode@v1
        with:
          xcode-version: '16.0'
      
      - name: Install Maestro
        run: |
          curl -Ls "https://get.maestro.mobile.dev" | bash
          echo "$HOME/.maestro/bin" >> $GITHUB_PATH
      
      - name: Boot Simulator
        run: |
          xcrun simctl boot "iPhone 15" || true
          xcrun simctl bootstatus "iPhone 15" -b
      
      - name: Build App
        working-directory: aniccaios
        run: |
          xcodebuild build \
            -project aniccaios.xcodeproj \
            -scheme aniccaios-staging \
            -destination 'platform=iOS Simulator,name=iPhone 15,OS=17.2' \
            -derivedDataPath ./build
      
      - name: Install App
        working-directory: aniccaios
        run: |
          xcrun simctl install booted ./build/Build/Products/Debug-iphonesimulator/aniccaios.app
      
      - name: Run Maestro Tests
        run: |
          maestro test maestro/
      
      - name: Upload Test Results
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: maestro-results
          path: ~/.maestro/tests/
```

---

## タスク 5: Maestro E2E を書く

### 必要なテストファイル

| ファイル | テスト内容 |
|---------|-----------|
| `maestro/05-phase5-thompson-sampling.yaml` | Thompson Sampling デバッグ UI |
| `maestro/06-phase5-unresponsive-simulation.yaml` | 無反応ユーザーシミュレーション |

**注意**: `appId` は実際のバンドルIDと一致させること。
- 本番: `com.anicca.ios`
- Staging: `com.anicca.ios.staging`（もし異なる場合）

### 5.1 maestro/05-phase5-thompson-sampling.yaml

```yaml
appId: com.anicca.ios
---
# Phase 5: Thompson Sampling テスト
- launchApp:
    clearState: true

# オンボーディングをスキップ（既存フローを使用）
- runFlow: 01-onboarding.yaml

# Profile タブに移動
- tapOn: "Profile"

# デバッグセクションまでスクロール
- scrollUntilVisible:
    element: "🎲 Phase 5: Thompson Sampling"
    direction: DOWN

# Thompson Sampling 統計セクションを確認
- tapOn: "🎲 Phase 5: Thompson Sampling"

# 統計が表示されることを確認（実際のUIに合わせる）
- assertVisible: "V0"
- assertVisible: "α:"
- assertVisible: "β:"

# 成功
- assertTrue: true
```

### 5.2 maestro/06-phase5-unresponsive-simulation.yaml

```yaml
appId: com.anicca.ios
---
# Phase 5: 無反応ユーザーシミュレーション テスト
- launchApp:
    clearState: false

# Profile タブに移動
- tapOn: "Profile"

# デバッグセクションまでスクロール
- scrollUntilVisible:
    element: "全バリアント無反応テスト"
    direction: DOWN

# シミュレーションボタンをタップ
- tapOn: "10回 x 8バリアント"

# 統計表示を確認
- scrollUntilVisible:
    element: "🎲 Phase 5: Thompson Sampling"
    direction: DOWN
- assertVisible: "V0"
- assertVisible: "α:"
```

---

## タスク 6: 全テスト PASS 確認

### 実行コマンド

**Note**: シミュレータは GitHub Actions（Task 4）と統一すること。

```bash
# 1. Unit Tests
cd aniccaios && xcodebuild test \
  -project aniccaios.xcodeproj \
  -scheme aniccaios-staging \
  -destination 'platform=iOS Simulator,name=iPhone 15,OS=17.2' \
  -only-testing:aniccaiosTests \
  2>&1 | xcpretty

# 2. E2E Tests
maestro test maestro/

# 3. ビルド確認
cd aniccaios && fastlane build_for_device
```

### 期待結果

```
✅ Unit Tests: XX tests passed
✅ E2E Tests: 6 flows passed
✅ Build: Successful
```

---

## タスク 7-10: リリースフロー

### 7. release/1.2.0 ブランチ作成

```bash
git checkout dev
git pull origin dev
git checkout -b release/1.2.0
git push origin release/1.2.0
```

### 8. TestFlight ビルド

```bash
cd aniccaios && fastlane build
fastlane upload
```

### 9. UI 確認（ユーザー）

TestFlight でアプリをインストールし、以下を確認：

1. オンボーディングが正常に完了するか
2. 通知が届くか
3. NudgeCard が表示されるか
4. Profile タブのデバッグセクションが**表示されない**こと（本番ビルド）

### 10. App Store 提出

```bash
cd aniccaios && fastlane full_release
```

---

## 付録: チェックリスト

### コードレビュー用チェックリスト

- [ ] ignored 閾値が 15分に設定されているか
- [ ] Unit Tests が全て PASS するか
- [ ] E2E Tests が全て PASS するか
- [ ] デバッグ UI が `#if DEBUG` で囲まれているか
- [ ] 本番ビルドでデバッグ UI が表示されないか
- [ ] GitHub Actions が正常に実行されるか

### リリース前チェックリスト

- [ ] TestFlight でテスト完了
- [ ] What's New を英語・日本語で記述
- [ ] バージョン番号を確認（1.2.0）
- [ ] main ブランチにはマージしない（承認後）

---

**最終更新**: 2026年1月21日（Task 6 シミュレータを iPhone 15,OS=17.2 に統一 - GitHub Actions との整合性確保）

