import XCTest
@testable import aniccaios

@MainActor
final class NudgeContentSelectorTests: XCTestCase {

    // NudgeContentSelector はシングルトンなので shared を使用
    private var selector: NudgeContentSelector!

    // MARK: - Test Helpers

    private var decoder: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }

    /// テスト用ヘルパー: LLMGeneratedNudgeを作成
    private func makeTestNudge(
        id: String = "llm-123",
        problemType: ProblemType = .cantWakeUp,
        scheduledHour: Int = 7
    ) throws -> LLMGeneratedNudge {
        let json = """
        {
            "id": "\(id)",
            "problemType": "\(problemType.rawValue)",
            "scheduledHour": \(scheduledHour),
            "hook": "LLM生成",
            "content": "LLMコンテンツ",
            "tone": "strict",
            "reasoning": "test",
            "createdAt": "2026-01-24T05:00:00Z"
        }
        """.data(using: .utf8)!
        return try decoder.decode(LLMGeneratedNudge.self, from: json)
    }

    override func setUp() {
        super.setUp()
        selector = NudgeContentSelector.shared
        NudgeStatsManager.shared.resetAllStats()
        LLMNudgeCache.shared.clear()
    }

    override func tearDown() {
        NudgeStatsManager.shared.resetAllStats()
        LLMNudgeCache.shared.clear()
        super.tearDown()
    }

    // MARK: - v1.5.0: LLM Priority Tests (交互ロジック削除後)

    /// LLMキャッシュがあれば常にLLMが選択される（AC2: LLM優先）
    func test_selectVariant_prefersLLM_whenCached() throws {
        let llmNudge = try makeTestNudge()
        LLMNudgeCache.shared.setNudges([llmNudge])

        let result = selector.selectVariant(for: .cantWakeUp, scheduledHour: 7)

        XCTAssertTrue(result.isAIGenerated)
        XCTAssertEqual(result.variantIndex, -1)
        XCTAssertNotNil(result.content)
        XCTAssertEqual(result.content?.id, "llm-123")
    }

    /// LLMキャッシュがあれば複数回呼んでも常にLLM（交互ではない）
    func test_selectVariant_alwaysLLM_whenCached() throws {
        let llmNudge = try makeTestNudge()
        LLMNudgeCache.shared.setNudges([llmNudge])

        // 連続で呼んでも常にLLM
        for _ in 0..<5 {
            let result = selector.selectVariant(for: .cantWakeUp, scheduledHour: 7)
            XCTAssertTrue(result.isAIGenerated, "Should always select LLM when cached")
        }
    }

    /// LLMキャッシュが空の場合、ルールベースにフォールバック（AC2フォールバック）
    func test_selectVariant_fallsBackToRuleBased() {
        LLMNudgeCache.shared.clear()

        let result = selector.selectVariant(for: .cantWakeUp, scheduledHour: 7)

        XCTAssertFalse(result.isAIGenerated)
        XCTAssertGreaterThanOrEqual(result.variantIndex, 0)
        XCTAssertNil(result.content)
    }

    /// 問題タイプと時刻の組み合わせが一致しない場合はルールベースにフォールバック
    func test_selectVariant_llmCacheMismatch() throws {
        let llmNudge = try makeTestNudge(problemType: .cantWakeUp, scheduledHour: 7)
        LLMNudgeCache.shared.setNudges([llmNudge])

        // 異なる時刻で取得 → ルールベース
        let result = selector.selectVariant(for: .cantWakeUp, scheduledHour: 8)
        XCTAssertFalse(result.isAIGenerated)

        // 異なる問題タイプで取得 → ルールベース
        let result2 = selector.selectVariant(for: .stayingUpLate, scheduledHour: 7)
        XCTAssertFalse(result2.isAIGenerated)
    }

    // MARK: - Existing Variant Selection Tests

    /// 初回呼び出しで有効なバリアントを返すこと (stayingUpLate)
    /// v1.6.1: stayingUpLate は21バリアント
    func test_selectVariant_returns_valid_variant_for_stayingUpLate() {
        // 乱数を高めに設定して既存ロジックを使用
        selector.randomProvider = { 0.9 }

        let result = selector.selectVariant(for: .stayingUpLate, scheduledHour: 22)

        // v1.6.1: stayingUpLate は21バリアント (0-20)
        XCTAssertTrue((0..<21).contains(result.variantIndex), "Variant \(result.variantIndex) should be in 0-20")
        XCTAssertFalse(result.isAIGenerated)
    }

    /// 他の問題タイプでは 0〜13 のバリアントを返すこと
    /// v1.6.1: 他の問題タイプは14バリアント
    func test_selectVariant_returns_valid_variant_for_other_problems() {
        // 乱数を高めに設定して既存ロジックを使用
        selector.randomProvider = { 0.9 }

        let problems: [ProblemType] = [.cantWakeUp, .selfLoathing, .procrastination, .anxiety]

        for problem in problems {
            let result = selector.selectVariant(for: problem, scheduledHour: 9)
            XCTAssertGreaterThanOrEqual(result.variantIndex, 0)
            XCTAssertLessThanOrEqual(result.variantIndex, 13) // v1.6.1: 14バリアント (0-13)
            XCTAssertFalse(result.isAIGenerated)
        }
    }

    /// v1.6.1: 全21バリアントが汎用（stayingUpLate）
    func test_selectVariant_stayingUpLate_allVariantsAreGeneric() {
        selector.randomProvider = { 0.9 }

        // 0時でも汎用バリアント (0-20) から Thompson Sampling で選択
        let result0 = selector.selectVariant(for: .stayingUpLate, scheduledHour: 0)
        XCTAssertTrue((0..<21).contains(result0.variantIndex), "At 00:00, should select from all 21 variants")

        // 1時も同様
        let result1 = selector.selectVariant(for: .stayingUpLate, scheduledHour: 1)
        XCTAssertTrue((0..<21).contains(result1.variantIndex), "At 01:00, should select from all 21 variants")

        // 22時も同様（全21バリアントが候補）
        let result22 = selector.selectVariant(for: .stayingUpLate, scheduledHour: 22)
        XCTAssertTrue((0..<21).contains(result22.variantIndex), "At 22:00, should select from all 21 variants")
    }

    // MARK: - Thompson Sampling Tests

    /// tapped が多いバリアントが選ばれやすいこと
    func test_selectVariant_favors_high_tapped_variants() {
        // 乱数を高めに設定して既存ロジック（Thompson Sampling）を使用
        selector.randomProvider = { 0.9 }

        // バリアント 0 に多くの tapped を記録
        for _ in 0..<20 {
            NudgeStatsManager.shared.recordTapped(
                problemType: "procrastination",
                variantIndex: 0,
                scheduledHour: 10
            )
        }

        // バリアント 1 に多くの ignored を記録
        NudgeStatsManager.shared.debugRecordIgnored(
            problemType: "procrastination",
            variantIndex: 1,
            scheduledHour: 10,
            count: 20
        )

        // 100回選択して、バリアント 0 が多く選ばれることを確認
        var variant0Count = 0
        for _ in 0..<100 {
            let result = selector.selectVariant(for: .procrastination, scheduledHour: 10)
            if result.variantIndex == 0 {
                variant0Count += 1
            }
        }

        XCTAssertGreaterThan(variant0Count, 60, "High-tapped variant should be selected > 60% of the time")
    }

    // MARK: - v1.5.0: 100% LLM Distribution Test

    /// LLMキャッシュがあれば100%LLMが選択される（交互ロジック削除後）
    func test_selectVariant_100percent_LLM_distribution() throws {
        let llmNudge = try makeTestNudge()
        LLMNudgeCache.shared.setNudges([llmNudge])

        var llmCount = 0
        let iterations = 100

        for _ in 0..<iterations {
            let result = selector.selectVariant(for: .cantWakeUp, scheduledHour: 7)
            if result.isAIGenerated {
                llmCount += 1
            }
        }

        // 交互ロジック削除後、LLMキャッシュがあれば100% LLM
        XCTAssertEqual(llmCount, iterations, "LLM should be selected 100% of the time when cached")
    }
}
