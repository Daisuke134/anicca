import Foundation
import OSLog

/// Nudgeコンテンツ選択ロジック
@MainActor
final class NudgeContentSelector {
    static let shared = NudgeContentSelector()

    private let logger = Logger(subsystem: "com.anicca.ios", category: "NudgeContentSelector")

    // テスト用: 乱数生成を注入可能にする
    var randomProvider: () -> Double = { Double.random(in: 0...1) }

    private init() {}

    /// 問題タイプと時刻からベストなバリアントを選択（v1.5.0: LLM優先、交互ロジック削除）
    /// - Returns: (variantIndex: Int, isAIGenerated: Bool, content: LLMGeneratedNudge?)
    func selectVariant(for problem: ProblemType, scheduledHour: Int) -> (variantIndex: Int, isAIGenerated: Bool, content: LLMGeneratedNudge?) {
        return selectVariant(for: problem, scheduledHour: scheduledHour, slotIndex: 0, usedVariants: [], isDay1: false)
    }

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

        // Day 2+: Day-Cycling fallback（v1.6.1: Thompson Sampling → Day-Cycling に変更）
        // NOTE: usedVariants パラメータはAPI互換性のため残すが、Day-Cyclingでは使用しない
        let selectedVariant = dayCyclingVariant(for: problem, slotIndex: slotIndex)
        logger.info("🔄 Day-Cycling fallback variant \(selectedVariant) for \(problem.rawValue) at hour \(scheduledHour)")
        return (variantIndex: selectedVariant, isAIGenerated: false, content: nil)
    }

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
        // v1.6.1: Day-Cycling を使用（本番と同じ挙動）
        let selectedVariant = dayCyclingVariant(for: problem, slotIndex: 0)
        logger.info("🔄 [Debug] Day-Cycling variant \(selectedVariant) for \(problem.rawValue)")
        return (variantIndex: selectedVariant, isAIGenerated: false, content: nil)
    }
    #endif

    /// 既存のバリアント選択ロジック（Phase 5: Thompson Sampling）
    private func selectExistingVariant(for problem: ProblemType, scheduledHour: Int, usedVariants: Set<Int> = []) -> Int {
        // 0. 完全無反応ユーザーの場合、未試行バリアントを優先
        if NudgeStatsManager.shared.isCompletelyUnresponsive(for: problem.rawValue, hour: scheduledHour) {
            let allVariants = getGenericVariantIndices(for: problem)
            if let untriedVariant = NudgeStatsManager.shared.selectUntriedVariant(
                for: problem.rawValue,
                hour: scheduledHour,
                availableVariants: allVariants
            ) {
                logger.info("Unresponsive user: selected untried variant \(untriedVariant) for \(problem.rawValue)")
                return untriedVariant
            }
        }
        
        // 1. 汎用バリアントから選択（usedVariants除外）
        let allGeneric = getGenericVariantIndices(for: problem)
        let genericVariants = allGeneric.filter { !usedVariants.contains($0) }
        guard !genericVariants.isEmpty else {
            // All used → fallback to full set
            return selectByThompsonSampling(variants: allGeneric, problem: problem, hour: scheduledHour)
        }

        // 2. Thompson Samplingで選択
        let selectedVariant = selectByThompsonSampling(
            variants: genericVariants,
            problem: problem,
            hour: scheduledHour
        )

        logger.info("Selected variant \(selectedVariant) for \(problem.rawValue) at hour \(scheduledHour)")
        return selectedVariant
    }

    /// Day 1 決定論的バリアント割り当て
    /// - Parameters:
    ///   - problem: 問題タイプ
    ///   - slotIndex: スロットの順序インデックス（0-based）
    /// - Returns: 割り当てるバリアントインデックス
    func day1VariantIndex(for problem: ProblemType, slotIndex: Int) -> Int {
        let variantCount = problem.notificationVariantCount

        // staying_up_late exception: slots 3-5 use time-aware mapping (5,3,4)
        if problem == .stayingUpLate && slotIndex >= 3 {
            let timeAwareMapping = [5, 3, 4]
            let mappingIndex = slotIndex - 3
            guard mappingIndex < timeAwareMapping.count else {
                return slotIndex % variantCount
            }
            return timeAwareMapping[mappingIndex]
        }
        // Default: sequential assignment with bounds safety
        return slotIndex % variantCount
    }

    // MARK: - Day-Cycling (v1.6.1)

    /// Day-Cycling: バリアントを順番に回す
    /// - 毎日同じスロットで異なるバリアントを表示
    /// - 周期: variantCount / gcd(variantCount, slotsPerDay) 日（anxiety: 14日、stayingUpLate: 21日）
    /// - Parameters:
    ///   - problem: 問題タイプ
    ///   - slotIndex: 当日内のスロット順序（0-indexed）
    /// - Returns: バリアントインデックス
    func dayCyclingVariant(for problem: ProblemType, slotIndex: Int) -> Int {
        let dayIndex = NudgeStatsManager.shared.getDaysSinceOnboarding(for: problem.rawValue)
        let variantCount = problem.notificationVariantCount
        let slotsPerDay = problem.notificationSchedule.count

        // (dayIndex * slotsPerDay + slotIndex) % variantCount
        let variant = (dayIndex * slotsPerDay + slotIndex) % variantCount

        logger.info("🔄 Day-Cycling: day=\(dayIndex) slot=\(slotIndex) → variant=\(variant) for \(problem.rawValue)")
        return variant
    }

    /// テスト可能なバリアント選択（v1.6.1: Day-Cycling対応）
    func selectExistingVariantTestable(for problem: ProblemType, scheduledHour: Int, usedVariants: Set<Int> = [], slotIndex: Int = 0) -> Int {
        // v1.6.1: Day-Cycling を使用
        return dayCyclingVariant(for: problem, slotIndex: slotIndex)
    }

    /// 後方互換: 既存コード用のselectVariant（Intを返す）
    /// Phase 6移行期間中は使用可能だが、将来的に削除予定
    @available(*, deprecated, message: "Use selectVariant returning tuple instead")
    func selectVariantLegacy(for problem: ProblemType, scheduledHour: Int) -> Int {
        let result = selectVariant(for: problem, scheduledHour: scheduledHour)
        return result.variantIndex
    }

    /// 汎用バリアントのインデックス配列を返す
    private func getGenericVariantIndices(for problem: ProblemType) -> [Int] {
        Array(0..<problem.notificationVariantCount)
    }

    // MARK: - Thompson Sampling (Phase 5)

    /// Thompson Samplingによるバリアント選択
    func selectByThompsonSampling(variants: [Int], problem: ProblemType, hour: Int) -> Int {
        let samples = variants.map { variantIndex -> (variantIndex: Int, sample: Double, alpha: Double, beta: Double) in
            let stats = NudgeStatsManager.shared.getStats(
                problemType: problem.rawValue,
                variantIndex: variantIndex,
                hour: hour
            )
            // alpha = tapped + 1 (事前分布)
            // beta = ignored + 1 (事前分布)
            let alpha = Double(stats?.tappedCount ?? 0) + 1.0
            let beta = Double(stats?.ignoredCount ?? 0) + 1.0
            let distribution = BetaDistribution(alpha: alpha, beta: beta)
            let sample = distribution.sample()
            
            logger.debug("Variant \(variantIndex): alpha=\(alpha), beta=\(beta), sample=\(String(format: "%.3f", sample))")
            return (variantIndex, sample, alpha, beta)
        }
        
        // 最大サンプル値のバリアントを選択
        if let best = samples.max(by: { $0.sample < $1.sample }) {
            logger.info("Thompson Sampling: selected variant \(best.variantIndex) with sample \(String(format: "%.3f", best.sample))")
            
            // Mixpanelに送信
            AnalyticsManager.shared.track(.nudgeScheduled, properties: [
                "problem_type": problem.rawValue,
                "variant_index": best.variantIndex,
                "scheduled_hour": hour,
                "selection_method": "thompson_sampling",
                "alpha": best.alpha,
                "beta": best.beta,
                "sample_value": best.sample,
                "tap_rate_estimate": best.alpha / (best.alpha + best.beta)
            ])
            
            return best.variantIndex
        }
        
        return variants[0]
    }
    
    // MARK: - Legacy Selection (Deprecated)

    /// データ量に応じた選択戦略（Phase 4互換、非推奨）
    @available(*, deprecated, message: "Use selectByThompsonSampling instead")
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

    // MARK: - Content Selection (Task 8)

    /// 👍率ベースでdetailを選択（通知とペアなので同じvariantIndexを使用）
    /// Phase 4ではペアのまま運用。将来的に分離可能。
    func selectContentVariant(for problem: ProblemType, notificationVariant: Int) -> Int {
        // 現在はnotificationとdetailはペア
        return notificationVariant
    }

    /// 複合スコアで選択（tap率 70% + 👍率 30%）
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

