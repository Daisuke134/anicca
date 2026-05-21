# Phase 5: Thompson Sampling 実装仕様書

> **目的**: 固定ルールベースのバリアント選択を Thompson Sampling に置き換える
>
> **バージョン**: 1.2.0
>
> **最終更新**: 2026-01-21

---

## 1. 概要

### 1.1 背景

Phase 4 で実装した固定ルールベースの選択（80%活用/20%探索）には以下の問題がある：

| 問題 | 説明 |
|------|------|
| 固定比率 | データ量に関係なく同じ探索率（20%） |
| 非効率な探索 | 明らかに効果が低いバリアントにも20%の確率で選ばれる |
| 確信度無視 | データが少ないバリアントと多いバリアントを同等に扱う |

### 1.2 解決策

**Thompson Sampling** を採用する。

- 各バリアントの tapped/ignored 履歴から Beta 分布を構築
- 各バリアントからサンプリングし、最大値のバリアントを選択
- データ量に応じて探索/活用比率が自動調整される

### 1.3 なぜ Thompson Sampling か

| 選択肢 | 不採用理由 |
|--------|----------|
| Duolingo RDSA | Sleeping Arms 問題がない、大量データ前提、複雑すぎる |
| ε-greedy | 固定探索率で現状と同じ問題 |
| UCB1 | 計算が複雑、直感的でない |
| **Thompson Sampling** | シンプル、少データでも動く、確信度ベース |

---

## 2. ファイル一覧

### 2.1 新規作成

| ファイル | 内容 |
|---------|------|
| `aniccaios/Services/BetaDistribution.swift` | Beta 分布サンプリング実装 |

### 2.2 変更

| ファイル | 変更内容 |
|---------|---------|
| `aniccaios/Services/NudgeContentSelector.swift` | 固定ルール → Thompson Sampling |

### 2.3 変更なし

| ファイル | 理由 |
|---------|------|
| `NudgeStatsManager.swift` | 既存の tappedCount/ignoredCount をそのまま使用 |

---

## 3. 新規ファイル: BetaDistribution.swift

### 3.1 仕様

Beta 分布からのサンプリングを行う構造体。

**アルゴリズム**: Gamma 分布経由（Marsaglia and Tsang's method）

```
X ~ Gamma(alpha, 1)
Y ~ Gamma(beta, 1)
Beta(alpha, beta) = X / (X + Y)
```

### 3.2 コード

```swift
// ファイル: aniccaios/aniccaios/Services/BetaDistribution.swift

import Foundation

/// Beta分布からのサンプリング
struct BetaDistribution {
    let alpha: Double
    let beta: Double
    
    /// Beta分布からサンプリング（0〜1の値を返す）
    func sample() -> Double {
        let x = gammaSample(shape: alpha)
        let y = gammaSample(shape: beta)
        guard x + y > 0 else { return 0.5 }
        return x / (x + y)
    }
    
    /// Gamma分布からのサンプリング（Marsaglia and Tsang's method）
    private func gammaSample(shape: Double) -> Double {
        // shape < 1 の場合は変換
        if shape < 1 {
            let u = Double.random(in: Double.leastNonzeroMagnitude..<1)
            return gammaSample(shape: shape + 1) * pow(u, 1.0 / shape)
        }
        
        let d = shape - 1.0 / 3.0
        let c = 1.0 / sqrt(9.0 * d)
        
        while true {
            var x: Double
            var v: Double
            
            repeat {
                x = gaussianSample()
                v = 1.0 + c * x
            } while v <= 0
            
            v = v * v * v
            let u = Double.random(in: 0..<1)
            
            if u < 1.0 - 0.0331 * (x * x) * (x * x) {
                return d * v
            }
            
            if log(u) < 0.5 * x * x + d * (1.0 - v + log(v)) {
                return d * v
            }
        }
    }
    
    /// 標準正規分布からのサンプリング（Box-Muller法）
    private func gaussianSample() -> Double {
        let u1 = Double.random(in: Double.leastNonzeroMagnitude..<1)
        let u2 = Double.random(in: 0..<1)
        return sqrt(-2.0 * log(u1)) * cos(2.0 * .pi * u2)
    }
}
```

---

## 4. 変更: NudgeContentSelector.swift

### 4.1 As-Is（現状）

```swift
// 行 87-136: selectByDataLevel メソッド

/// データ量に応じた選択戦略
private func selectByDataLevel(variants: [Int], problem: ProblemType, hour: Int) -> Int {
    // 各バリアントのサンプル数を取得
    let variantSamples = variants.map { variantIndex -> (Int, Int) in
        let stats = NudgeStatsManager.shared.getStats(
            problemType: problem.rawValue,
            variantIndex: variantIndex,
            hour: hour
        )
        let samples = stats?.totalSamples ?? 0
        return (variantIndex, samples)
    }

    let minSamples = variantSamples.map { $0.1 }.min() ?? 0
    let totalSamples = variantSamples.map { $0.1 }.reduce(0, +)

    // Phase A: 全バリアントが最低3回ずつ試されるまで
    // → 最もサンプル数が少ないバリアントを優先
    if minSamples < 3 {
        let leastTested = variantSamples.filter { $0.1 == minSamples }
        if let selected = leastTested.randomElement() {
            logger.info("Phase A (exploration): selected least tested variant \(selected.0)")
            return selected.0
        }
    }

    // Phase B: 全バリアントが3回以上 & 合計15回未満
    // → 50%活用 / 50%探索
    if totalSamples < 15 {
        if Double.random(in: 0...1) < 0.5 {
            logger.info("Phase B (50/50): exploitation")
            return selectByTapRate(variants: variants, problem: problem, hour: hour)
        } else {
            logger.info("Phase B (50/50): exploration")
            return variants.randomElement() ?? variants[0]
        }
    }

    // Phase C: 合計15回以上
    // → 80%活用 / 20%探索
    if Double.random(in: 0...1) < 0.8 {
        logger.info("Phase C (80/20): exploitation")
        return selectByTapRate(variants: variants, problem: problem, hour: hour)
    } else {
        logger.info("Phase C (80/20): exploration")
        return variants.randomElement() ?? variants[0]
    }
}

/// tap率ベースで選択
private func selectByTapRate(variants: [Int], problem: ProblemType, hour: Int) -> Int {
    let variantRates = variants.map { variantIndex -> (Int, Double) in
        let stats = NudgeStatsManager.shared.getStats(
            problemType: problem.rawValue,
            variantIndex: variantIndex,
            hour: hour
        )
        let tapRate = stats?.tapRate ?? 0.5
        return (variantIndex, tapRate)
    }

    // 最高tap率のバリアントを選択
    if let best = variantRates.max(by: { $0.1 < $1.1 }) {
        return best.0
    }

    return variants[0]
}
```

### 4.2 To-Be（変更後）

```swift
// 行 87-136 を以下に置き換え

/// Thompson Sampling でバリアント選択
private func selectByThompsonSampling(variants: [Int], problem: ProblemType, hour: Int) -> Int {
    // 各バリアントから Beta 分布でサンプリング
    let samples = variants.map { variantIndex -> (variantIndex: Int, sample: Double) in
        let stats = NudgeStatsManager.shared.getStats(
            problemType: problem.rawValue,
            variantIndex: variantIndex,
            hour: hour
        )
        
        // alpha = tapped + 1, beta = ignored + 1 (事前分布として Beta(1,1) を使用)
        let alpha = Double(stats?.tappedCount ?? 0) + 1.0
        let beta = Double(stats?.ignoredCount ?? 0) + 1.0
        
        let distribution = BetaDistribution(alpha: alpha, beta: beta)
        let sample = distribution.sample()
        
        logger.debug("Variant \(variantIndex): alpha=\(alpha), beta=\(beta), sample=\(sample)")
        
        return (variantIndex, sample)
    }
    
    // 最高サンプル値のバリアントを選択
    if let best = samples.max(by: { $0.sample < $1.sample }) {
        logger.info("Thompson Sampling: selected variant \(best.variantIndex) with sample \(best.sample)")
        return best.variantIndex
    }
    
    return variants[0]
}

// selectByTapRate は削除（Thompson Sampling に統合）
```

### 4.3 呼び出し元の変更

```swift
// 行 27-32: selectVariant メソッド内

// As-Is
let selectedVariant = selectByDataLevel(
    variants: genericVariants,
    problem: problem,
    hour: scheduledHour
)

// To-Be
let selectedVariant = selectByThompsonSampling(
    variants: genericVariants,
    problem: problem,
    hour: scheduledHour
)
```

### 4.4 削除するメソッド

| メソッド | 理由 |
|---------|------|
| `selectByDataLevel` | Thompson Sampling に置き換え |
| `selectByTapRate` | Thompson Sampling に統合 |

### 4.5 残すメソッド

| メソッド | 理由 |
|---------|------|
| `selectVariant` | エントリーポイント |
| `getTimeSpecificVariant` | 時刻固定バリアント（深夜0時/1時） |
| `getGenericVariantIndices` | バリアント一覧取得 |
| `selectContentVariant` | 将来の拡張用 |
| `selectByCompositeScore` | 将来の拡張用（👍率考慮） |

---

## 5. 完全なパッチ

### 5.1 BetaDistribution.swift（新規）

```swift
// ファイル: aniccaios/aniccaios/Services/BetaDistribution.swift

import Foundation

/// Beta分布からのサンプリング
///
/// Thompson Sampling で使用。
/// アルゴリズム: Gamma分布経由（Marsaglia and Tsang's method）
struct BetaDistribution {
    let alpha: Double
    let beta: Double
    
    /// 初期化
    /// - Parameters:
    ///   - alpha: 成功回数 + 1（事前分布として1を加算済み想定）
    ///   - beta: 失敗回数 + 1（事前分布として1を加算済み想定）
    init(alpha: Double, beta: Double) {
        precondition(alpha > 0, "alpha must be positive")
        precondition(beta > 0, "beta must be positive")
        self.alpha = alpha
        self.beta = beta
    }
    
    /// Beta分布からサンプリング（0〜1の値を返す）
    func sample() -> Double {
        let x = gammaSample(shape: alpha)
        let y = gammaSample(shape: beta)
        guard x + y > 0 else { return 0.5 }
        return x / (x + y)
    }
    
    /// Gamma分布からのサンプリング（Marsaglia and Tsang's method）
    /// 参考: https://www.hongliangjie.com/2012/12/19/how-to-generate-gamma-random-variables/
    private func gammaSample(shape: Double) -> Double {
        // shape < 1 の場合は変換
        if shape < 1 {
            let u = Double.random(in: Double.leastNonzeroMagnitude..<1)
            return gammaSample(shape: shape + 1) * pow(u, 1.0 / shape)
        }
        
        let d = shape - 1.0 / 3.0
        let c = 1.0 / sqrt(9.0 * d)
        
        while true {
            var x: Double
            var v: Double
            
            repeat {
                x = gaussianSample()
                v = 1.0 + c * x
            } while v <= 0
            
            v = v * v * v
            let u = Double.random(in: 0..<1)
            
            if u < 1.0 - 0.0331 * (x * x) * (x * x) {
                return d * v
            }
            
            if log(u) < 0.5 * x * x + d * (1.0 - v + log(v)) {
                return d * v
            }
        }
    }
    
    /// 標準正規分布からのサンプリング（Box-Muller法）
    private func gaussianSample() -> Double {
        let u1 = Double.random(in: Double.leastNonzeroMagnitude..<1)
        let u2 = Double.random(in: 0..<1)
        return sqrt(-2.0 * log(u1)) * cos(2.0 * .pi * u2)
    }
}
```

### 5.2 NudgeContentSelector.swift（変更後の全体）

```swift
// ファイル: aniccaios/aniccaios/Services/NudgeContentSelector.swift

import Foundation
import OSLog

/// Nudgeコンテンツ選択ロジック
@MainActor
final class NudgeContentSelector {
    static let shared = NudgeContentSelector()

    private let logger = Logger(subsystem: "com.anicca.ios", category: "NudgeContentSelector")

    private init() {}

    /// 問題タイプと時刻からベストなバリアントを選択
    func selectVariant(for problem: ProblemType, scheduledHour: Int) -> Int {
        // 1. 時刻固定バリアントをチェック
        if let fixedVariant = getTimeSpecificVariant(problem: problem, hour: scheduledHour) {
            logger.info("Selected time-specific variant \(fixedVariant) for \(problem.rawValue) at hour \(scheduledHour)")
            return fixedVariant
        }

        // 2. 汎用バリアントから選択
        let genericVariants = getGenericVariantIndices(for: problem)
        guard !genericVariants.isEmpty else {
            return 0
        }

        // 3. Thompson Sampling でバリアント選択
        let selectedVariant = selectByThompsonSampling(
            variants: genericVariants,
            problem: problem,
            hour: scheduledHour
        )

        logger.info("Selected variant \(selectedVariant) for \(problem.rawValue) at hour \(scheduledHour)")
        return selectedVariant
    }

    // MARK: - Time-Specific Variants

    /// 時刻固定バリアントを返す（該当しない場合はnil）
    private func getTimeSpecificVariant(problem: ProblemType, hour: Int) -> Int? {
        switch problem {
        case .stayingUpLate:
            // 深夜0時 → variant_4（インデックス3）
            if hour == 0 { return 3 }
            // 深夜1時 → variant_5（インデックス4）
            if hour == 1 { return 4 }
            return nil
        default:
            return nil
        }
    }

    /// 汎用バリアントのインデックス配列を返す
    private func getGenericVariantIndices(for problem: ProblemType) -> [Int] {
        switch problem {
        case .stayingUpLate:
            return [0, 1, 2]
        case .cantWakeUp:
            return [0, 1, 2]
        case .selfLoathing:
            return [0, 1, 2]
        case .rumination:
            return [0, 1, 2]
        case .procrastination:
            return [0, 1, 2]
        case .anxiety:
            return [0, 1, 2]
        case .lying:
            return [0]
        case .badMouthing:
            return [0, 1]
        case .pornAddiction:
            return [0, 1]
        case .alcoholDependency:
            return [0, 1]
        case .anger:
            return [0, 1]
        case .obsessive:
            return [0, 1, 2]
        case .loneliness:
            return [0, 1]
        }
    }

    // MARK: - Thompson Sampling

    /// Thompson Sampling でバリアント選択
    ///
    /// 各バリアントの tapped/ignored 履歴から Beta 分布を構築し、
    /// サンプリングして最大値のバリアントを選択する。
    ///
    /// - Beta(alpha, beta) where:
    ///   - alpha = tappedCount + 1
    ///   - beta = ignoredCount + 1
    /// - 事前分布: Beta(1, 1) = 一様分布
    private func selectByThompsonSampling(variants: [Int], problem: ProblemType, hour: Int) -> Int {
        let samples = variants.map { variantIndex -> (variantIndex: Int, sample: Double) in
            let stats = NudgeStatsManager.shared.getStats(
                problemType: problem.rawValue,
                variantIndex: variantIndex,
                hour: hour
            )
            
            // alpha = tapped + 1, beta = ignored + 1
            let alpha = Double(stats?.tappedCount ?? 0) + 1.0
            let beta = Double(stats?.ignoredCount ?? 0) + 1.0
            
            let distribution = BetaDistribution(alpha: alpha, beta: beta)
            let sample = distribution.sample()
            
            logger.debug("Variant \(variantIndex): alpha=\(alpha), beta=\(beta), sample=\(String(format: "%.3f", sample))")
            
            return (variantIndex, sample)
        }
        
        if let best = samples.max(by: { $0.sample < $1.sample }) {
            logger.info("Thompson Sampling: selected variant \(best.variantIndex) with sample \(String(format: "%.3f", best.sample))")
            return best.variantIndex
        }
        
        return variants[0]
    }

    // MARK: - Content Selection

    /// 👍率ベースでdetailを選択（通知とペアなので同じvariantIndexを使用）
    func selectContentVariant(for problem: ProblemType, notificationVariant: Int) -> Int {
        return notificationVariant
    }

    /// 複合スコアで選択（tap率 70% + 👍率 30%）
    /// 将来の拡張用に残す
    func selectByCompositeScore(variants: [Int], problem: ProblemType, hour: Int) -> Int {
        let variantScores = variants.map { variantIndex -> (Int, Double) in
            let stats = NudgeStatsManager.shared.getStats(
                problemType: problem.rawValue,
                variantIndex: variantIndex,
                hour: hour
            )
            let tapRate = stats?.tapRate ?? 0.5
            let thumbsUpRate = stats?.thumbsUpRate ?? 0.5
            let score = tapRate * 0.7 + thumbsUpRate * 0.3
            return (variantIndex, score)
        }

        if let best = variantScores.max(by: { $0.1 < $1.1 }) {
            return best.0
        }

        return variants[0]
    }
}
```

---

## 6. テストケース

### 6.1 BetaDistribution

| テスト | 期待結果 |
|--------|---------|
| `BetaDistribution(alpha: 1, beta: 1).sample()` | 0〜1 の一様分布 |
| `BetaDistribution(alpha: 10, beta: 1).sample()` | 0.8〜1.0 付近 |
| `BetaDistribution(alpha: 1, beta: 10).sample()` | 0.0〜0.2 付近 |
| 100回サンプリング | クラッシュなし、全て 0〜1 の範囲内 |

### 6.2 Thompson Sampling 選択

| シナリオ | 期待結果 |
|---------|---------|
| 全バリアントがデータなし | ランダムに近い選択 |
| variant_0: 10 tapped, 2 ignored | variant_0 が高確率で選択される |
| variant_0: 2 tapped, 10 ignored | variant_0 が低確率で選択される |

### 6.3 時刻固定バリアント

| シナリオ | 期待結果 |
|---------|---------|
| stayingUpLate, hour=0 | 必ず variant 3 |
| stayingUpLate, hour=1 | 必ず variant 4 |
| stayingUpLate, hour=21 | Thompson Sampling で選択 |

---

## 7. 実装手順

1. `BetaDistribution.swift` を新規作成
2. `NudgeContentSelector.swift` の `selectByDataLevel` と `selectByTapRate` を削除
3. `selectByThompsonSampling` を追加
4. `selectVariant` の呼び出しを変更
5. ビルド確認
6. ユニットテスト追加（オプション）

---

## 8. 参考文献

- [Analysis of Thompson Sampling for the multi-armed bandit problem](https://arxiv.org/pdf/1111.1797v3) - Agrawal & Goyal, 2011
- [Marsaglia and Tsang's method for Gamma distribution](https://www.hongliangjie.com/2012/12/19/how-to-generate-gamma-random-variables/)
- [Duolingo KDD 2020 Paper](https://research.duolingo.com/papers/yancey.kdd20.pdf) - 不採用理由の参考

---

*この仕様書は Phase 5 の Thompson Sampling 実装を定義する。*


