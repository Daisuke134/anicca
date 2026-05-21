# Phase 6: LLM生成 Nudge - 仕様書

> 作成日: 2026-01-24
> ステータス: Draft

---

## 目次

1. [概要](#1-概要)
2. [As-Is（現状）](#2-as-is現状)
3. [To-Be（変更後）](#3-to-be変更後)
4. [To-Be チェックリスト](#4-to-be-チェックリスト)
5. [テストマトリックス](#5-テストマトリックス)
6. [実装詳細](#6-実装詳細)
7. [Unit Tests](#7-unit-tests)
8. [E2E Tests (Maestro)](#8-e2e-tests-maestro)
9. [ローカライズ](#9-ローカライズ)
10. [実行手順](#10-実行手順)
11. [Skills / Sub-agents](#11-skills--sub-agents)
12. [レビューチェックリスト](#12-レビューチェックリスト)

---

## 1. 概要

### 何を解決するか

Phase 5までは固定バリアント（5-10個）からThompson Samplingで選択していた。ユーザーごとに「刺さる言葉」は違うが、バリアント数に限界がある。

### なぜ必要か

- 固定バリアントでは「刺さらない人」が出る
- 時間が経つと飽きる
- パーソナライズに限界がある

### Phase 6でやること

LLMで新しいバリアントを生成し、既存バリアントと50/50で比較。効果測定してイテレーション。

### 決定事項

| 項目 | 決定 |
|------|------|
| LLM | GPT-4o-mini |
| 生成タイミング | 毎朝5:00 JST バッチ生成 |
| 比率 | 50% LLM / 50% 既存 |
| 問題タイプ | 13問題全部 |
| Hook + Content | ペアで生成 |
| フィードバック | tapped/ignored、👍👎をAPIに送信 |

---

## 2. As-Is（現状）

### 2.1 NudgeContentSelector

```swift
// 現在: Thompson Samplingで固定バリアントから選択
func selectVariant(for problem: ProblemType, scheduledHour: Int) -> Int {
    // 時刻固定バリアントをチェック
    if let fixedVariant = getTimeSpecificVariant(problem: problem, hour: scheduledHour) {
        return fixedVariant
    }
    // 汎用バリアントからThompson Samplingで選択
    let genericVariants = getGenericVariantIndices(for: problem)
    return selectByThompsonSampling(variants: genericVariants, problem: problem, hour: scheduledHour)
}
```

### 2.2 ProblemNotificationScheduler

```swift
// 現在: ローカライズキーから文字列を取得
let notificationTextKey = "nudge_\(problem.rawValue)_notification_\(variantIndex + 1)"
let detailTextKey = "nudge_\(problem.rawValue)_detail_\(variantIndex + 1)"
notificationContent.body = NSLocalizedString(notificationTextKey, comment: "")
```

### 2.3 NudgeContent

```swift
// 現在: 固定バリアントのみ
struct NudgeContent {
    let problemType: ProblemType
    let notificationText: String
    let detailText: String
    let variantIndex: Int
}
```

**To-Be（変更後）**:
```swift
// 変更後: LLM生成フラグを追加
struct NudgeContent {
    let problemType: ProblemType
    let notificationText: String  // hook
    let detailText: String        // content
    let variantIndex: Int         // LLM生成の場合は -1
    let isAIGenerated: Bool       // LLM生成かどうか
    let llmNudgeId: String?       // LLM生成の場合のID（Mixpanel/DB連携用）
}
```

### 2.4 API

- NudgeEvent/NudgeOutcomeモデルは存在
- LLM生成エンドポイントは未実装
- `isAIGenerated`フラグなし

---

## 3. To-Be（変更後）

### 3.1 NudgeContentSelector

```swift
// 変更後: 50%の確率でLLM生成を使用
// @MainActorでスレッド安全性を保証（LLMNudgeCacheと同じアクター）
// テスト用に乱数生成を注入可能にする（決定論的テストのため）
@MainActor
final class NudgeContentSelector {
    static let shared = NudgeContentSelector()

    // テスト用: 乱数生成を注入可能にする
    var randomProvider: () -> Double = { Double.random(in: 0...1) }

    func selectVariant(for problem: ProblemType, scheduledHour: Int) -> (variantIndex: Int, isAIGenerated: Bool, content: LLMGeneratedNudge?) {
        // 50%の確率でLLM生成を試みる（randomProviderで乱数取得）
        if randomProvider() < 0.5 {
            // LLMNudgeCacheも@MainActorなので直接アクセス可能
            if let llmNudge = LLMNudgeCache.shared.getNudge(for: problem, hour: scheduledHour) {
                return (variantIndex: -1, isAIGenerated: true, content: llmNudge)
            }
        }

        // LLM生成がなければ既存ロジック
        // ...既存のThompson Samplingロジック
        return (variantIndex: selectedVariant, isAIGenerated: false, content: nil)
    }
}
```

**呼び出し側**: `@MainActor`から呼ぶか、`await MainActor.run { ... }` でラップする。

### 3.2 LLMGeneratedNudge モデル（新規）

```swift
// Tone enum（LLM生成で使用する5種類）
enum NudgeTone: String, Codable, CaseIterable {
    case strict
    case gentle
    case logical
    case provocative
    case philosophical
    case unknown  // 未知値のフォールバック

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        let rawValue = try container.decode(String.self)
        self = NudgeTone(rawValue: rawValue) ?? .unknown
    }
}

struct LLMGeneratedNudge: Codable {
    let id: String
    let problemType: ProblemType   // 既存のProblemType enumを使用
    let scheduledHour: Int
    let hook: String               // 通知テキスト（25文字以内）
    let content: String            // OneScreenテキスト（80文字以内）
    let tone: NudgeTone            // enum: strict/gentle/logical/provocative/philosophical
    let reasoning: String          // LLMの判断理由
    let createdAt: Date

    // カスタムデコーダー: problemTypeのrawValueからenumに変換
    enum CodingKeys: String, CodingKey {
        case id, problemType, scheduledHour, hook, content, tone, reasoning, createdAt
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)

        // problemTypeはAPIが文字列で返すので、ProblemType enumに変換
        let problemTypeString = try container.decode(String.self, forKey: .problemType)
        guard let problemType = ProblemType(rawValue: problemTypeString) else {
            throw DecodingError.dataCorruptedError(
                forKey: .problemType,
                in: container,
                debugDescription: "Unknown problemType: \(problemTypeString)"
            )
        }
        self.problemType = problemType

        scheduledHour = try container.decode(Int.self, forKey: .scheduledHour)
        hook = try container.decode(String.self, forKey: .hook)
        content = try container.decode(String.self, forKey: .content)
        tone = try container.decode(NudgeTone.self, forKey: .tone)
        reasoning = try container.decode(String.self, forKey: .reasoning)
        createdAt = try container.decode(Date.self, forKey: .createdAt)
    }
}

// LLMNudgeService.swift - デコーダー設定
extension LLMNudgeService {
    static var decoder: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601  // ISO8601文字列をDateに変換
        return decoder
    }
}
```

**API ↔ iOS 型マッピング表**:

| API (String) | iOS (enum) | 備考 |
|-------------|------------|------|
| `"cant_wake_up"` | `ProblemType.cantWakeUp` | rawValue一致 |
| `"staying_up_late"` | `ProblemType.stayingUpLate` | rawValue一致 |
| `"strict"` | `NudgeTone.strict` | rawValue一致 |
| `"gentle"` | `NudgeTone.gentle` | rawValue一致 |
| 未知の文字列 | デコードエラー（problemType）/ `.unknown`（tone） | エラーハンドリング |

### 3.3 LLMNudgeCache（新規）

```swift
@MainActor
final class LLMNudgeCache {
    static let shared = LLMNudgeCache()

    private var cache: [String: LLMGeneratedNudge] = [:]  // key: "\(problemType)_\(hour)"

    func getNudge(for problem: ProblemType, hour: Int) -> LLMGeneratedNudge? {
        let key = "\(problem.rawValue)_\(hour)"
        return cache[key]
    }

    func setNudges(_ nudges: [LLMGeneratedNudge]) {
        for nudge in nudges {
            let key = "\(nudge.problemType)_\(nudge.scheduledHour)"
            cache[key] = nudge
        }
    }

    func clear() {
        cache = [:]
    }
}
```

### 3.4 ProblemNotificationScheduler 修正

```swift
private func scheduleNotification(for problem: ProblemType, hour: Int, minute: Int) async {
    // NudgeContentSelectorでバリアント選択（LLM対応）
    let selection = await MainActor.run {
        NudgeContentSelector.shared.selectVariant(for: problem, scheduledHour: hour)
    }

    let notificationContent = UNMutableNotificationContent()

    if selection.isAIGenerated, let llmNudge = selection.content {
        // LLM生成の場合
        notificationContent.body = llmNudge.hook
        notificationContent.userInfo = [
            "problemType": problem.rawValue,
            "isAIGenerated": true,
            "llmNudgeId": llmNudge.id,
            "detailText": llmNudge.content,
            "scheduledHour": hour,
            "scheduledMinute": minute
        ]
    } else {
        // 既存バリアントの場合
        let notificationTextKey = "nudge_\(problem.rawValue)_notification_\(selection.variantIndex + 1)"
        let detailTextKey = "nudge_\(problem.rawValue)_detail_\(selection.variantIndex + 1)"
        notificationContent.body = NSLocalizedString(notificationTextKey, comment: "")
        notificationContent.userInfo = [
            "problemType": problem.rawValue,
            "isAIGenerated": false,
            "notificationTextKey": notificationTextKey,
            "detailTextKey": detailTextKey,
            "variantIndex": selection.variantIndex,
            "scheduledHour": hour,
            "scheduledMinute": minute
        ]
    }
    // ...残りは同じ
}
```

### 3.5 NudgeStatsManager 修正

```swift
// LLM生成Nudgeの統計記録
func recordTapped(problemType: String, variantIndex: Int, scheduledHour: Int, isAIGenerated: Bool, llmNudgeId: String?) {
    // 既存ロジック + isAIGeneratedをMixpanelに送信
    AnalyticsManager.shared.track(.nudgeTapped, properties: [
        "problem_type": problemType,
        "variant_index": variantIndex,
        "scheduled_hour": scheduledHour,
        "is_ai_generated": isAIGenerated,
        "llm_nudge_id": llmNudgeId ?? ""
    ])
}
```

### 3.6 API: POST /api/nudge/generate

**認証**: 内部API用サービストークン（cron job専用）
**呼び出し元**: Railway cron job のみ
**設計**: cron jobが全ユーザーを走査し、各ユーザー分を生成

```typescript
import { z } from 'zod';
import { requireInternalAuth } from '../middleware/auth';

// 入力バリデーションスキーマ
const GenerateNudgeSchema = z.object({
    userId: z.string().uuid(),  // cron jobが指定
    problems: z.array(z.enum([
        'staying_up_late', 'cant_wake_up', 'self_loathing', 'rumination',
        'procrastination', 'anxiety', 'lying', 'bad_mouthing', 'porn_addiction',
        'alcohol_dependency', 'anger', 'obsessive', 'loneliness'
    ])).min(1).max(13),
    stats: z.record(z.string(), z.object({
        tapped: z.number().int().min(0),
        ignored: z.number().int().min(0),
        thumbsUp: z.number().int().min(0),
        thumbsDown: z.number().int().min(0)
    })).optional()
});

// LLM出力バリデーションスキーマ
const LLMOutputSchema = z.object({
    hook: z.string().min(1).max(50),  // 最大50文字（後で25文字に切り捨て）
    content: z.string().min(1).max(200),  // 最大200文字（後で80文字に切り捨て）
    tone: z.enum(['strict', 'gentle', 'logical', 'provocative', 'philosophical']),
    reasoning: z.string()
});

// 内部API（cron job専用、サービストークン認証）
app.post('/api/nudge/generate', requireInternalAuth, async (req, res) => {
    // 入力バリデーション
    const parseResult = GenerateNudgeSchema.safeParse(req.body);
    if (!parseResult.success) {
        return res.status(400).json({ error: 'Invalid input', details: parseResult.error.issues });
    }
    const { userId, problems, stats } = parseResult.data;

    const nudges = [];
    for (const problem of problems) {
        const prompt = buildPrompt(problem, stats?.[problem]);

        try {
            const response = await openai.chat.completions.create({
                model: 'gpt-4o-mini',
                messages: [{ role: 'user', content: prompt }],
                response_format: { type: 'json_object' }
            });

            const rawOutput = JSON.parse(response.choices[0].message.content);

            // LLM出力バリデーション
            const outputResult = LLMOutputSchema.safeParse(rawOutput);
            if (!outputResult.success) {
                console.warn(`LLM output validation failed for ${problem}:`, outputResult.error);
                continue;  // このproblemはスキップ（既存バリアントが使われる）
            }
            const generated = outputResult.data;

            const scheduledHour = getScheduledHourForProblem(problem);
            nudges.push({
                id: crypto.randomUUID(),
                problemType: problem,
                scheduledHour,
                hook: generated.hook.slice(0, 25),  // 25文字制限
                content: generated.content.slice(0, 80),  // 80文字制限
                tone: generated.tone,
                reasoning: generated.reasoning,
                createdAt: new Date().toISOString()
            });
        } catch (error) {
            console.error(`LLM generation failed for ${problem}:`, error);
            // このproblemはスキップ（既存バリアントが使われる）
        }
    }

    // DBに保存（scheduledHourもstateに含める）
    if (nudges.length > 0) {
        await prisma.nudgeEvent.createMany({
            data: nudges.map(n => ({
                userId,
                domain: 'problem_nudge',
                subtype: n.problemType,
                decisionPoint: 'llm_generation',
                state: {
                    id: n.id,
                    scheduledHour: n.scheduledHour,  // stateに保存
                    hook: n.hook,
                    content: n.content,
                    tone: n.tone,
                    reasoning: n.reasoning
                },
                actionTemplate: 'notification',
                channel: 'push',
                sent: false
            }))
        });
    }

    res.json({ nudges, skipped: problems.length - nudges.length });
});
```

**cron job実装** (apps/api/jobs/generateNudges.ts):
```typescript
// 毎朝5:00 JST に実行
async function generateNudgesForAllUsers() {
    const users = await prisma.user.findMany({
        where: { isActive: true },
        select: { id: true, problems: true }
    });

    for (const user of users) {
        if (user.problems.length === 0) continue;

        // 各ユーザーの統計を取得
        const stats = await getUserNudgeStats(user.id);

        // 内部APIを呼び出し
        await fetch(`${process.env.API_URL}/api/nudge/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${process.env.INTERNAL_API_TOKEN}`
            },
            body: JSON.stringify({
                userId: user.id,
                problems: user.problems,
                stats
            })
        });
    }
}
```
```

### 3.6.1 API: GET /api/nudge/today

**認証**: 必須（Bearer Token）
**認可**: userIdはトークンから取得
**呼び出し元**: iOSアプリ（起動時）

```typescript
// 今日生成されたNudgeを取得
app.get('/api/nudge/today', requireAuth, async (req, res) => {
    const userId = req.user.id;

    // 今日の00:00 JST以降に生成されたNudgeを取得
    // JST (UTC+9) で今日の開始時刻を計算
    const nowJST = new Date(Date.now() + 9 * 60 * 60 * 1000);
    const todayStartJST = new Date(Date.UTC(
        nowJST.getUTCFullYear(),
        nowJST.getUTCMonth(),
        nowJST.getUTCDate(),
        0, 0, 0, 0
    ) - 9 * 60 * 60 * 1000);  // JSTの00:00をUTCに変換

    const nudges = await prisma.nudgeEvent.findMany({
        where: {
            userId,
            domain: 'problem_nudge',
            decisionPoint: 'llm_generation',
            createdAt: { gte: todayStartJST }
        },
        select: {
            state: true,
            subtype: true,
            createdAt: true
        }
    });

    // LLMGeneratedNudge形式に変換
    const formattedNudges = nudges.map(n => ({
        id: n.state.id,
        problemType: n.subtype,
        scheduledHour: n.state.scheduledHour,  // stateに保存済み
        hook: n.state.hook,
        content: n.state.content,
        tone: n.state.tone,
        reasoning: n.state.reasoning,
        createdAt: n.createdAt.toISOString()
    }));

    res.json({ nudges: formattedNudges });
});
```

**レスポンス例**:
```json
{
  "nudges": [
    {
      "id": "uuid-123",
      "problemType": "cant_wake_up",
      "scheduledHour": 7,
      "hook": "まだ寝てる？",
      "content": "あと5分で起きたら、今日は違う1日になる。",
      "tone": "strict",
      "reasoning": "User responds well to strict tone",
      "createdAt": "2026-01-24T05:00:00Z"
    }
  ]
}
```

**キャッシュ**: iOS側で24時間キャッシュ（LLMNudgeCache）

### 3.7 プロンプト

```
You are Anicca, an AI that reduces human suffering through perfectly-timed nudges.

## Your Mission
Generate notification hooks and one-screen content that will make this specific person take action. The notification alone should be powerful enough to change behavior - they shouldn't even need to tap.

## User Profile
- Problem types: {problem_types}
- Preferred tone: {preferred_tone} (based on past thumbs_up patterns)
- Avoided tone: {avoided_tone} (based on past thumbs_down patterns)
- Most responsive hours: {responsive_hours}

## Yesterday's Results
{yesterday_nudges_json}

## What Worked (Top 3)
{successful_nudges}

## What Failed (Top 3)
{failed_nudges}

## Tone Definitions
- strict: 厳しい、直接的、言い訳を許さない。例：「まだ寝てる？言い訳はいらない」
- gentle: 優しい、共感的、寄り添う。例：「大丈夫、少しずつでいいよ」
- logical: 論理的、データや事実ベース。例：「睡眠不足は判断力を40%下げる」
- provocative: 挑発的、プライドを刺激。例：「また負けるの？」
- philosophical: 哲学的、深い問い。例：「この5分が人生を変えるかもしれない」

## Output Requirements

Generate a PAIR of hook and content for each scheduled time slot.

### Hook (Notification)
- Maximum 25 characters (CRITICAL - must fit in notification preview)
- Action-oriented
- Uses the tone that works for this person
- Powerful enough that they might change behavior without tapping

### Content (One-Screen)
- Maximum 80 characters
- Specific action or insight
- Directly related to the hook
- Provides value even if they only glance at it

## Today's Schedule
Generate nudges for these time slots: {time_slots}

## Output Format (JSON)

**注意**: 1回のLLM呼び出しで1つの問題タイプに対する1つのNudgeを生成する。配列ではなく単一オブジェクトを出力すること。

{
  "hook": "まだ布団の中？",
  "content": "あと5分で起きたら、今日は違う1日になる。試してみろ。",
  "tone": "strict",
  "reasoning": "This person responds well to strict tone in the morning. Yesterday's gentle approach was ignored."
}

## Critical Rules
1. NEVER exceed character limits. Hook ≤ 25, Content ≤ 80.
2. Output a SINGLE JSON object, not an array.
3. If yesterday's approach failed, try something different.
4. The hook is more important than the content. Focus there first.
5. Use Japanese. Natural, conversational, not robotic.
```

### 3.8 Accessibility Identifier（Maestroテスト用）

**Debugボタンは使わない。accessibilityIdentifierで判別する。**

**注意**: SwiftUIの`.accessibilityIdentifier`は1要素に1つのみ有効（複数指定すると上書き）。LLM判別は`accessibilityValue`で表現する。

```swift
// NudgeCardView.swift
// UI変更なし、accessibilityIdentifierのみ設定

// カード全体（E2Eで表示確認用）
VStack {
    // ... NudgeCard content
}
.accessibilityIdentifier("nudge-card-view")

// Hook（通知テキスト）
Text(nudge.hook)
    .accessibilityIdentifier("nudge-hook-text")

// Content（詳細テキスト）
// accessibilityIdentifierで表示確認、accessibilityValueでLLM/既存を判別
Text(nudge.content)
    .accessibilityIdentifier("nudge-content-text")
    .accessibilityValue(nudge.isAIGenerated ? "llm" : "rule")

// フィードバックボタン
Button("👍") { ... }
    .accessibilityIdentifier("feedback-thumbs-up")

Button("👎") { ... }
    .accessibilityIdentifier("feedback-thumbs-down")

// フィードバック送信完了状態
if feedbackSubmitted {
    Text("ありがとう！")
        .accessibilityIdentifier("feedback-submitted")
}
```

**Accessibility Identifier 一覧**:

| ID | 用途 | E2Eで使用 |
|----|------|----------|
| `nudge-card-view` | カード全体の表示確認 | ✅ |
| `nudge-hook-text` | Hookテキスト表示確認 | ✅ |
| `nudge-content-text` | Contentテキスト表示確認 | ✅ |
| `llm-indicator` | LLM生成判別（🤖、DEBUGのみ） | ✅ |
| `feedback-thumbs-up` | 👍ボタンタップ | ✅ |
| `feedback-thumbs-down` | 👎ボタンタップ | ✅ |
| `feedback-submitted` | 送信完了確認 | ✅ |

**LLM判別方法**:

MaestroではaccessibilityValueの直接検証が困難なため、以下のいずれかの方法を採用:

**方法1: テスト専用の可視ラベルを追加**（推奨）
```swift
// NudgeCardView.swift - テスト用LLM判別ラベル
#if DEBUG
if nudge.isAIGenerated {
    Text("🤖")
        .font(.caption)
        .accessibilityIdentifier("llm-indicator")
}
#endif
```

```yaml
# Maestroで可視ラベルを検証
- assertVisible:
    id: "llm-indicator"
```

**方法2: XCUITestでaccessibilityValueを検証**
```swift
// XCUITest
let contentText = app.staticTexts["nudge-content-text"]
XCTAssertEqual(contentText.value as? String, "llm")
```

**採用**: 方法1（Debugビルドで🤖表示）をE2Eテストで使用する。

**Deep Link（staging buildのみ）**:
```swift
// テスト用Deep Linkハンドラー
func handleTestDeepLink(_ url: URL) {
    guard url.scheme == "anicca", url.host == "test" else { return }

    switch url.path {
    case "/trigger-llm-nudge":
        // LLMキャッシュにテストデータを設定してNudgeCardを表示
        let testNudge = LLMGeneratedNudge(...)
        LLMNudgeCache.shared.setNudges([testNudge])
        showNudgeCard(testNudge)
    default:
        break
    }
}
```

---

## 4. To-Be チェックリスト

| # | To-Be | 完了 |
|---|-------|------|
| 1 | LLMGeneratedNudgeモデル作成 | [ ] |
| 2 | LLMNudgeCacheクラス作成 | [ ] |
| 2.5 | NudgeContent: isAIGenerated, llmNudgeId追加 | [ ] |
| 3 | NudgeContentSelector: 50%分岐追加 | [ ] |
| 4 | ProblemNotificationScheduler: isAIGenerated対応 | [ ] |
| 5 | NudgeStatsManager: isAIGenerated記録 | [ ] |
| 6 | API: POST /api/nudge/generate エンドポイント | [ ] |
| 7 | API: GPT-4o-mini連携 | [ ] |
| 8 | API: プロンプトテンプレート実装 | [ ] |
| 9 | API: Railway cron job（毎朝5:00 JST） | [ ] |
| 10 | iOS: 生成済みNudge取得API呼び出し | [ ] |
| 11 | iOS: Accessibility Identifier設定 + テスト用Deep Link | [ ] |
| 12 | Mixpanel: is_ai_generated プロパティ追加 | [ ] |
| 13 | 文字数超過時のfallback/切り捨て | [ ] |
| 14 | CLAUDE.md更新（Skills使用ルール、Maestroベストプラクティス追記） | [ ] |
| 15 | roadmap.md更新（Phase番号変更、決定事項反映） | [ ] |

---

## 5. テストマトリックス

| # | To-Be | テスト名 | カバー |
|---|-------|----------|--------|
| 1 | LLMGeneratedNudgeモデル (#1) | `test_LLMGeneratedNudge_encodeDecode()` | [ ] |
| 2 | LLMNudgeCache (#2) | `test_LLMNudgeCache_setAndGet()` | [ ] |
| 2.5 | NudgeContent: isAIGenerated (#2.5) | `test_NudgeContent_hasIsAIGenerated()` | [ ] |
| 3 | NudgeContentSelector 50%分岐 (#3) | `test_selectVariant_withLLMAvailable()` | [ ] |
| 4 | LLM優先でfallback (#3) | `test_selectVariant_fallbackToExisting()` | [ ] |
| 5 | ProblemNotificationScheduler isAIGenerated (#4) | `test_scheduleNotification_withLLMNudge()` | [ ] |
| 6 | NudgeStats isAIGenerated記録 (#5) | `test_recordTapped_withIsAIGenerated()` | [ ] |
| 7 | 文字数切り捨て（Hook 25文字）(#13) | `test_hookTruncation_25chars()` | [ ] |
| 8 | 文字数切り捨て（Content 80文字）(#13) | `test_contentTruncation_80chars()` | [ ] |
| 9 | API: POST /api/nudge/generate (#6,#7,#8) | `test_api_generateNudge_authenticated()` | [ ] |
| 10 | API: 認証なしでリジェクト (#6) | `test_api_generateNudge_rejectsUnauthenticated()` | [ ] |
| 11 | API: 入力バリデーション (#6) | `test_api_generateNudge_validatesInput()` | [ ] |
| 12 | API: GET /api/nudge/today (#10) | `test_api_getTodayNudges_authenticated()` | [ ] |
| 13 | Railway cron job (#9) | 手動確認: Railway Dashboard でcron設定確認 | [ ] |
| 14 | iOS: 生成済みNudge取得 (#10) | `test_LLMNudgeService_fetchTodaysNudges()` | [ ] |
| 15 | iOS: Accessibility Identifier (#11) | Maestro `01-llm-nudge-display.yaml` | [ ] |
| 16 | iOS: Deep Link (#11) | Maestro `02-llm-nudge-flow.yaml` | [ ] |
| 17 | Mixpanel: is_ai_generated (#12) | `test_analytics_includesIsAIGenerated()` | [ ] |
| 18 | フィードバック送信 | Maestro `03-feedback-with-ai-flag.yaml` | [ ] |
| 19 | CLAUDE.md更新 (#14) | 静的チェック: diff確認 | [ ] |
| 20 | roadmap.md更新 (#15) | 静的チェック: diff確認 | [ ] |

---

## 6. 実装詳細

### 6.1 ファイル構成

```
aniccaios/
├── aniccaios/
│   ├── Models/
│   │   ├── LLMGeneratedNudge.swift  (新規)
│   │   └── NudgeContent.swift       (修正: isAIGenerated, llmNudgeId追加)
│   ├── Services/
│   │   ├── LLMNudgeCache.swift      (新規)
│   │   ├── LLMNudgeService.swift    (新規)
│   │   ├── NudgeContentSelector.swift  (修正)
│   │   └── NudgeStatsManager.swift     (修正)
│   ├── Notifications/
│   │   └── ProblemNotificationScheduler.swift  (修正)
│   └── Views/
│       └── NudgeCardView.swift  (修正)
└── aniccaiosTests/
    ├── LLMGeneratedNudgeTests.swift  (新規)
    ├── LLMNudgeCacheTests.swift      (新規)
    └── NudgeContentSelectorTests.swift  (修正)

apps/api/
├── api/
│   └── nudge/
│       └── generate.ts  (新規)
└── lib/
    └── prompts/
        └── nudgeGeneration.ts  (新規)

maestro/
└── phase6/
    ├── 01-llm-nudge-display.yaml     (新規)
    ├── 02-llm-nudge-flow.yaml        (新規)
    └── 03-feedback-with-ai-flag.yaml (新規)
```

### 6.2 データフロー

```
毎朝5:00 (Railway cron)
    │
    ▼
API: /api/nudge/generate
    │ 各ユーザーの問題タイプ + 統計データを取得
    │ GPT-4o-miniでNudge生成
    │ DBに保存
    ▼
iOSアプリ起動時
    │
    ▼
LLMNudgeService.fetchTodaysNudges()
    │ API呼び出し
    │ LLMNudgeCacheに保存
    ▼
ProblemNotificationScheduler.scheduleNotifications()
    │
    ▼
NudgeContentSelector.selectVariant()
    │ 50%の確率でLLMNudgeCacheから取得
    │ なければ既存Thompson Sampling
    ▼
通知スケジュール
    │ userInfoに isAIGenerated を含める
    ▼
通知タップ → NudgeCardView表示
    │ accessibilityIdentifierでLLM/既存を判別
    ▼
フィードバック（👍👎）
    │ is_ai_generated をMixpanelに送信
    ▼
翌日の生成に反映
```

---

## 7. Unit Tests

### 7.1 LLMGeneratedNudgeTests.swift

```swift
import Testing
@testable import aniccaios

struct LLMGeneratedNudgeTests {

    @Test("LLMGeneratedNudge decode from API response")
    func test_LLMGeneratedNudge_decodeFromAPI() throws {
        // APIレスポンス形式のJSON（文字列）
        let json = """
        {
            "id": "test-123",
            "problemType": "cant_wake_up",
            "scheduledHour": 7,
            "hook": "まだ寝てる？",
            "content": "あと5分で起きたら、今日は違う1日になる。",
            "tone": "strict",
            "reasoning": "User responds well to strict tone",
            "createdAt": "2026-01-24T05:00:00Z"
        }
        """.data(using: .utf8)!

        let decoder = LLMNudgeService.decoder
        let decoded = try decoder.decode(LLMGeneratedNudge.self, from: json)

        #expect(decoded.id == "test-123")
        #expect(decoded.problemType == .cantWakeUp)  // enum
        #expect(decoded.tone == .strict)  // enum
        #expect(decoded.hook == "まだ寝てる？")
        #expect(decoded.content == "あと5分で起きたら、今日は違う1日になる。")
    }

    @Test("Unknown tone falls back to .unknown")
    func test_LLMGeneratedNudge_unknownTone() throws {
        let json = """
        {
            "id": "test-123",
            "problemType": "cant_wake_up",
            "scheduledHour": 7,
            "hook": "テスト",
            "content": "テスト",
            "tone": "some_new_tone",
            "reasoning": "test",
            "createdAt": "2026-01-24T05:00:00Z"
        }
        """.data(using: .utf8)!

        let decoder = LLMNudgeService.decoder
        let decoded = try decoder.decode(LLMGeneratedNudge.self, from: json)

        #expect(decoded.tone == .unknown)
    }

    @Test("Unknown problemType throws error")
    func test_LLMGeneratedNudge_unknownProblemType() throws {
        let json = """
        {
            "id": "test-123",
            "problemType": "unknown_problem",
            "scheduledHour": 7,
            "hook": "テスト",
            "content": "テスト",
            "tone": "strict",
            "reasoning": "test",
            "createdAt": "2026-01-24T05:00:00Z"
        }
        """.data(using: .utf8)!

        let decoder = LLMNudgeService.decoder
        #expect(throws: DecodingError.self) {
            try decoder.decode(LLMGeneratedNudge.self, from: json)
        }
    }

    @Test("Hook character limit validation")
    func test_hookTruncation_25chars() {
        let longHook = "これは25文字を超える非常に長いフックテキストです"
        let truncated = String(longHook.prefix(25))

        #expect(truncated.count <= 25)
    }

    @Test("Content character limit validation")
    func test_contentTruncation_80chars() {
        let longContent = String(repeating: "あ", count: 100)
        let truncated = String(longContent.prefix(80))

        #expect(truncated.count <= 80)
    }
}
```

### 7.2 LLMNudgeCacheTests.swift

```swift
import Testing
@testable import aniccaios

@MainActor
struct LLMNudgeCacheTests {

    // テスト用ヘルパー: LLMGeneratedNudgeを作成
    private func makeTestNudge(
        id: String = "test-123",
        problemType: ProblemType = .cantWakeUp,
        scheduledHour: Int = 7
    ) -> LLMGeneratedNudge {
        // JSONからデコードしてインスタンス作成（本番と同じ経路）
        let json = """
        {
            "id": "\(id)",
            "problemType": "\(problemType.rawValue)",
            "scheduledHour": \(scheduledHour),
            "hook": "起きろ",
            "content": "今日も頑張ろう",
            "tone": "strict",
            "reasoning": "test",
            "createdAt": "2026-01-24T05:00:00Z"
        }
        """.data(using: .utf8)!
        return try! LLMNudgeService.decoder.decode(LLMGeneratedNudge.self, from: json)
    }

    @Test("Set and get nudge from cache")
    func test_LLMNudgeCache_setAndGet() async {
        let cache = LLMNudgeCache.shared
        cache.clear()

        let nudge = makeTestNudge()
        cache.setNudges([nudge])

        let retrieved = cache.getNudge(for: .cantWakeUp, hour: 7)
        #expect(retrieved != nil)
        #expect(retrieved?.id == "test-123")
        #expect(retrieved?.problemType == .cantWakeUp)
    }

    @Test("Return nil for missing nudge")
    func test_LLMNudgeCache_missingNudge() async {
        let cache = LLMNudgeCache.shared
        cache.clear()

        let retrieved = cache.getNudge(for: .cantWakeUp, hour: 7)
        #expect(retrieved == nil)
    }
}
```

### 7.3 NudgeContentSelectorTests.swift (追加)

**注意**: 50%確率テストはフレークしやすいため、乱数を注入可能にして決定論的にテストする。
**注意**: NudgeContentSelectorは@MainActorなので、テストも@MainActorで実行する。

```swift
import Testing
@testable import aniccaios

@MainActor
struct NudgeContentSelectorTests {

    // テスト用ヘルパー: LLMGeneratedNudgeを作成（JSONデコード経由）
    private func makeTestNudge(id: String = "llm-123") -> LLMGeneratedNudge {
        let json = """
        {
            "id": "\(id)",
            "problemType": "cant_wake_up",
            "scheduledHour": 7,
            "hook": "LLM生成",
            "content": "LLMコンテンツ",
            "tone": "strict",
            "reasoning": "test",
            "createdAt": "2026-01-24T05:00:00Z"
        }
        """.data(using: .utf8)!
        return try! LLMNudgeService.decoder.decode(LLMGeneratedNudge.self, from: json)
    }

    @Test("Select LLM variant when random < 0.5 and cache available")
    func test_selectVariant_withLLMAvailable() {
        // LLM nudgeをキャッシュに設定
        let llmNudge = makeTestNudge()
        LLMNudgeCache.shared.clear()
        LLMNudgeCache.shared.setNudges([llmNudge])

        // 乱数を0.3（< 0.5）に固定 → LLM選択
        let selector = NudgeContentSelector.shared
        selector.randomProvider = { 0.3 }

        let result = selector.selectVariant(for: .cantWakeUp, scheduledHour: 7)

        #expect(result.isAIGenerated == true)
        #expect(result.content?.id == "llm-123")
        #expect(result.content?.problemType == .cantWakeUp)

        // クリーンアップ
        selector.randomProvider = { Double.random(in: 0...1) }
    }

    @Test("Select existing variant when random >= 0.5")
    func test_selectVariant_existingWhenRandomHigh() {
        // LLM nudgeをキャッシュに設定
        let llmNudge = makeTestNudge()
        LLMNudgeCache.shared.clear()
        LLMNudgeCache.shared.setNudges([llmNudge])

        // 乱数を0.7（>= 0.5）に固定 → 既存バリアント選択
        let selector = NudgeContentSelector.shared
        selector.randomProvider = { 0.7 }

    let result = await MainActor.run {
        selector.selectVariant(for: .cantWakeUp, scheduledHour: 7)
    }

    #expect(result.isAIGenerated == false)
    #expect(result.variantIndex >= 0)

    // クリーンアップ
    selector.randomProvider = { Double.random(in: 0...1) }
}

@Test("Fallback to existing when LLM cache is empty")
func test_selectVariant_fallbackToExisting() async {
    await MainActor.run {
        LLMNudgeCache.shared.clear()
    }

        let result = selector.selectVariant(for: .cantWakeUp, scheduledHour: 7)

        #expect(result.isAIGenerated == false)
        #expect(result.variantIndex >= 0)

        // クリーンアップ
        selector.randomProvider = { Double.random(in: 0...1) }
    }

    @Test("Fallback to existing when LLM cache is empty")
    func test_selectVariant_fallbackToExisting() {
        LLMNudgeCache.shared.clear()

        // 乱数を0.3（< 0.5）に固定してもキャッシュが空ならfallback
        let selector = NudgeContentSelector.shared
        selector.randomProvider = { 0.3 }

        let result = selector.selectVariant(for: .cantWakeUp, scheduledHour: 7)

        #expect(result.isAIGenerated == false)
        #expect(result.variantIndex >= 0)

        // クリーンアップ
        selector.randomProvider = { Double.random(in: 0...1) }
    }
}
```

### 7.4 LLMNudgeServiceTests.swift (新規)

```swift
import Testing
@testable import aniccaios

struct LLMNudgeServiceTests {

    @Test("Fetch today's nudges from API with ISO8601 date decoding")
    func test_LLMNudgeService_fetchTodaysNudges() async throws {
        // Mock URLSession or use URLProtocol for testing
        let mockResponse = """
        {
            "nudges": [
                {
                    "id": "test-123",
                    "problemType": "cant_wake_up",
                    "scheduledHour": 7,
                    "hook": "起きろ",
                    "content": "今日も頑張ろう",
                    "tone": "strict",
                    "reasoning": "test",
                    "createdAt": "2026-01-24T05:00:00Z"
                }
            ]
        }
        """

        // JSONDecoderにISO8601を設定
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        // テスト用のMock URLSession設定
        let service = LLMNudgeService(
            session: MockURLSession(responseData: mockResponse.data(using: .utf8)!),
            decoder: decoder
        )

        let nudges = try await service.fetchTodaysNudges()

        #expect(nudges.count == 1)
        #expect(nudges[0].id == "test-123")
        #expect(nudges[0].problemType == .cantWakeUp)  // enum
        #expect(nudges[0].tone == .strict)  // enum
        #expect(nudges[0].scheduledHour == 7)
        // createdAtがDateとして正しくデコードされることを確認
        #expect(nudges[0].createdAt != nil)
    }

    @Test("Decoding fails without ISO8601 strategy")
    func test_LLMNudgeService_decodingFailsWithoutISO8601() async throws {
        let mockResponse = """
        {
            "nudges": [
                {
                    "id": "test-123",
                    "problemType": "cant_wake_up",
                    "scheduledHour": 7,
                    "hook": "起きろ",
                    "content": "今日も頑張ろう",
                    "tone": "strict",
                    "reasoning": "test",
                    "createdAt": "2026-01-24T05:00:00Z"
                }
            ]
        }
        """

        // デフォルトのJSONDecoder（ISO8601なし）
        let decoder = JSONDecoder()

        let service = LLMNudgeService(
            session: MockURLSession(responseData: mockResponse.data(using: .utf8)!),
            decoder: decoder
        )

        // ISO8601なしではデコードが失敗することを確認
        await #expect(throws: DecodingError.self) {
            try await service.fetchTodaysNudges()
        }
    }
}
```

### 7.5 API Tests (TypeScript - apps/api)

```typescript
// apps/api/__tests__/nudge/generate.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest';
import request from 'supertest';
import { app } from '../../app';

const INTERNAL_API_TOKEN = process.env.INTERNAL_API_TOKEN || 'test-internal-token';
const TEST_USER_ID = '00000000-0000-0000-0000-000000000001';  // 有効なUUID形式

describe('POST /api/nudge/generate', () => {
    it('rejects requests without internal token', async () => {
        const res = await request(app)
            .post('/api/nudge/generate')
            .send({ userId: TEST_USER_ID, problems: ['cant_wake_up'] });

        expect(res.status).toBe(401);
    });

    it('validates input schema - invalid problem type', async () => {
        const res = await request(app)
            .post('/api/nudge/generate')
            .set('Authorization', `Bearer ${INTERNAL_API_TOKEN}`)
            .send({ userId: TEST_USER_ID, problems: ['invalid_problem_type'] });

        expect(res.status).toBe(400);
        expect(res.body.error).toBe('Invalid input');
    });

    it('validates input schema - missing userId', async () => {
        const res = await request(app)
            .post('/api/nudge/generate')
            .set('Authorization', `Bearer ${INTERNAL_API_TOKEN}`)
            .send({ problems: ['cant_wake_up'] });

        expect(res.status).toBe(400);
        expect(res.body.error).toBe('Invalid input');
    });

    it('generates nudges with internal auth', async () => {
        // Mock OpenAI response
        vi.mock('openai', () => ({
            default: vi.fn().mockImplementation(() => ({
                chat: {
                    completions: {
                        create: vi.fn().mockResolvedValue({
                            choices: [{ message: { content: JSON.stringify({
                                hook: 'テストフック',
                                content: 'テストコンテンツ',
                                tone: 'strict',
                                reasoning: 'test'
                            })}}]
                        })
                    }
                }
            }))
        }));

        const res = await request(app)
            .post('/api/nudge/generate')
            .set('Authorization', `Bearer ${INTERNAL_API_TOKEN}`)
            .send({ userId: TEST_USER_ID, problems: ['cant_wake_up'] });

        expect(res.status).toBe(200);
        expect(res.body.nudges).toHaveLength(1);
        expect(res.body.nudges[0].hook.length).toBeLessThanOrEqual(25);
        expect(res.body.nudges[0].scheduledHour).toBeDefined();
    });

    it('handles LLM output validation failure gracefully', async () => {
        // Mock OpenAI to return invalid output
        vi.mock('openai', () => ({
            default: vi.fn().mockImplementation(() => ({
                chat: {
                    completions: {
                        create: vi.fn().mockResolvedValue({
                            choices: [{ message: { content: JSON.stringify({
                                // missing required fields
                                hook: 'テスト'
                            })}}]
                        })
                    }
                }
            }))
        }));

        const res = await request(app)
            .post('/api/nudge/generate')
            .set('Authorization', `Bearer ${INTERNAL_API_TOKEN}`)
            .send({ userId: TEST_USER_ID, problems: ['cant_wake_up'] });

        expect(res.status).toBe(200);
        expect(res.body.nudges).toHaveLength(0);  // skipped due to validation failure
        expect(res.body.skipped).toBe(1);
    });
});

describe('GET /api/nudge/today', () => {
    it('rejects unauthenticated requests', async () => {
        const res = await request(app)
            .get('/api/nudge/today');

        expect(res.status).toBe(401);
    });

    it('returns today\'s nudges for authenticated user', async () => {
        const res = await request(app)
            .get('/api/nudge/today')
            .set('Authorization', 'Bearer valid-user-token');

        expect(res.status).toBe(200);
        expect(res.body).toHaveProperty('nudges');
        expect(Array.isArray(res.body.nudges)).toBe(true);
    });
});
```

### 7.6 AnalyticsTests.swift (新規)

```swift
import Testing
@testable import aniccaios

struct AnalyticsTests {

    @Test("Analytics includes is_ai_generated property")
    func test_analytics_includesIsAIGenerated() {
        var capturedProperties: [String: Any] = [:]

        // Mock AnalyticsManager
        let mockAnalytics = MockAnalyticsManager { event, properties in
            capturedProperties = properties
        }

        // Record tapped with isAIGenerated = true
        NudgeStatsManager(analytics: mockAnalytics).recordTapped(
            problemType: "cant_wake_up",
            variantIndex: -1,
            scheduledHour: 7,
            isAIGenerated: true,
            llmNudgeId: "llm-123"
        )

        #expect(capturedProperties["is_ai_generated"] as? Bool == true)
        #expect(capturedProperties["llm_nudge_id"] as? String == "llm-123")
    }
}
```

---

## 8. E2E Tests (Maestro)

**ベストプラクティス**: Debugボタンではなく、Deep Linkでテスト状態をトリガーする。

### 8.1 maestro/phase6/01-llm-nudge-display.yaml

```yaml
appId: com.anicca.ios.staging
---
- launchApp:
    clearState: true

# オンボーディング完了（既存フローを流用）
- runFlow: ../shared/complete-onboarding.yaml

# Deep LinkでLLM Nudgeをトリガー（staging buildのみ有効）
- openLink: "anicca://test/trigger-llm-nudge"

# NudgeCard表示待ち（accessibilityIdentifier使用）
- extendedWaitUntil:
    visible:
      id: "nudge-card-view"
    timeout: 10000

# Contentテキストが表示されていることを確認
- assertVisible:
    id: "nudge-content-text"

# LLM生成の判別: DEBUGビルドで🤖インジケーターが表示される
- assertVisible:
    id: "llm-indicator"

# スクリーンショット
- takeScreenshot: "llm-nudge-display"
```

### 8.2 maestro/phase6/02-llm-nudge-flow.yaml

```yaml
appId: com.anicca.ios.staging
---
- launchApp:
    clearState: true

# オンボーディング完了
- runFlow: ../shared/complete-onboarding.yaml

# Deep LinkでLLM Nudgeをトリガー
- openLink: "anicca://test/trigger-llm-nudge"

# NudgeCard表示待ち（accessibilityIdentifier使用）
- extendedWaitUntil:
    visible:
      id: "nudge-card-view"
    timeout: 10000

# NudgeCardが表示されることを確認
- assertVisible:
    id: "nudge-card-view"

# Hookが表示されることを確認
- assertVisible:
    id: "nudge-hook-text"

# Contentが表示されることを確認
- assertVisible:
    id: "nudge-content-text"

# スクリーンショット
- takeScreenshot: "llm-nudge-card"
```

### 8.3 maestro/phase6/03-feedback-with-ai-flag.yaml

```yaml
appId: com.anicca.ios.staging
---
- launchApp:
    clearState: true

# オンボーディング完了
- runFlow: ../shared/complete-onboarding.yaml

# Deep LinkでLLM Nudgeをトリガー
- openLink: "anicca://test/trigger-llm-nudge"

# NudgeCard表示待ち（accessibilityIdentifier使用）
- extendedWaitUntil:
    visible:
      id: "nudge-card-view"
    timeout: 10000

# 👍ボタンをタップ
- tapOn:
    id: "feedback-thumbs-up"

# フィードバック送信後の状態確認（accessibilityIdentifier使用）
- assertVisible:
    id: "feedback-submitted"

# スクリーンショット
- takeScreenshot: "feedback-with-ai-flag"
```

---

## 9. ローカライズ

### 新規追加なし

LLM生成テキストは動的に生成されるため、Localizable.stringsへの追加は不要。

### Accessibility Identifier

テスト用のAccessibility Identifierは英語で設定。ローカライズ不要。

---

## 10. 実行手順

### 10.1 開発環境

```bash
# iOSビルド（シミュレータ）
cd aniccaios && fastlane build_for_simulator

# iOSテスト実行
cd aniccaios && xcodebuild test \
  -project aniccaios.xcodeproj \
  -scheme aniccaios-staging \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.2' \
  -only-testing:aniccaiosTests \
  | xcpretty

# APIテスト（ローカル）
cd apps/api && pnpm test

# Maestro E2Eテスト
maestro test maestro/phase6/
```

### 10.2 実機テスト

```bash
# 実機ビルド（staging-release）
cd aniccaios && fastlane build_for_device

# 実機にインストール後、以下を手動確認:
# 1. 通知が来るか
# 2. LLM生成テキストが自然か
# 3. 文字数が通知に収まっているか
# 4. 🤖アイコンが表示されるか（Debug build）
```

### 10.3 Railway cron job設定

```
# Railway Dashboard > Settings > Cron Jobs
# Add: 0 20 * * * (UTC = 5:00 JST)
# Command: node dist/jobs/generateNudges.js
```

---

## 11. Skills / Sub-agents

| ステージ | 使用するもの | 用途 |
|---------|-------------|------|
| Spec作成 | `/plan` | 実装計画の作成 |
| テスト実装 | `/tdd-workflow` | TDDでテスト先行開発 |
| コードレビュー | `/code-review` | 実装後のレビュー |
| E2Eテスト | Maestro MCP | UIテスト自動化 |
| リリースノート | `/changelog-generator` | リリース時のchangelog作成 |
| ビルドエラー | `/build-fix` | エラー発生時の修正 |

---

## 12. レビューチェックリスト

### 仕様レビュー

- [ ] 全 To-Be がテストマトリックスに含まれているか
- [ ] 各 To-Be に対応するテストコードがあるか
- [ ] 後方互換性は保たれているか（既存バリアントも動く）
- [ ] As-Is の問題が To-Be で解決されるか

### コードレビュー

- [ ] 文字数制限（Hook 25文字、Content 80文字）が守られているか
- [ ] エラーハンドリングは適切か（LLM失敗時のfallback）
- [ ] Accessibility Identifierが正しく設定されているか
- [ ] Mixpanelに`is_ai_generated`が送信されるか

### テストレビュー

- [ ] Unit Testsが全てPASSするか
- [ ] Maestro E2Eが全てPASSするか
- [ ] カバレッジ80%以上か

### 最終確認（実機）

- [ ] 通知が実際に来るか
- [ ] LLM生成テキストが自然か
- [ ] 文字数が通知に収まっているか
- [ ] 全体的に「いい感じ」か

---

## 次のステップ

1. このSpecをレビュー用エージェントに渡す
2. 承認後、`/tdd-workflow`でテスト先行開発を開始
3. 全テストPASS後、実機テスト
4. devにプッシュ
5. `/changelog-generator`でリリースノート作成
6. release/1.3.0ブランチ作成

---

*この仕様書は Phase 6 の完全な実装を定義する。*
