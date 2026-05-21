# Anicca 1.6.2 — Review Reflection Spec（P0〜P2 修正計画）

## 概要（What & Why）

Agent Teams による3視点並列レビュー（アーキテクチャ・パフォーマンス・UX）で検出された P0〜P2 の全問題に対する修正計画。
70件以上の指摘から優先度の高い19件を体系的に修正し、アプリの品質・パフォーマンス・UX を底上げする。

**Why:**
- AppState God Object（934行）が全機能の変更リスクとテスト不能の根本原因
- Cron ジョブの逐次処理がユーザー増加でタイムアウトする時限爆弾
- URLSession リークがメモリ使用量を単調増加させる
- Paywall 拒否直後のレビュー依頼がネガティブレビューを誘発
- 罪悪感を煽る通知文言がペルソナの自己嫌悪ループを強化

---

## P0（即時対応）— 6件

### P0-1: AppState God Object 分割

**重要度:** CRITICAL（architect + performance 全員一致）

**As-Is:**
```swift
// aniccaios/aniccaios/AppState.swift (934行)
@MainActor
class AppState: ObservableObject {
    // 認証
    @Published var authStatus: AuthStatus = .unknown
    @Published var signedInUser: User? = nil

    // プロファイル
    @Published var userProfile: UserProfile = .empty
    @Published var struggles: [String] = []

    // サブスクリプション
    @Published var isEntitled: Bool = false
    @Published var subscriptionStatus: SubscriptionStatus = .unknown

    // Nudge
    @Published var currentNudgeCard: NudgeCard? = nil
    @Published var showNudgeCard: Bool = false

    // その他
    @Published var dailyRefreshTrigger: UUID = UUID()
    @Published var monthlyUsageCount: Int = 0
    @Published var hasRequestedReview: Bool = false
    // ... 合計16個の @Published
}
```

**問題:**
- 任意の `@Published` 変更で、`@EnvironmentObject` で監視する**全View**が再評価される
- 934行に認証・プロファイル・サブスク・通知・分析・マイグレーションの全責任が混在
- テスト時にモック注入が不可能

**To-Be:**
```swift
// aniccaios/aniccaios/State/AuthState.swift
@MainActor @Observable
class AuthState {
    var authStatus: AuthStatus = .unknown
    var signedInUser: User? = nil
}

// aniccaios/aniccaios/State/SubscriptionState.swift
@MainActor @Observable
class SubscriptionState {
    var isEntitled: Bool = false
    var subscriptionStatus: SubscriptionStatus = .unknown
    var monthlyUsageCount: Int = 0
}

// aniccaios/aniccaios/State/NudgeState.swift
@MainActor @Observable
class NudgeState {
    var currentNudgeCard: NudgeCard? = nil
    var showNudgeCard: Bool = false
    var dailyRefreshTrigger: UUID = UUID()
}

// aniccaios/aniccaios/State/ProfileState.swift
@MainActor @Observable
class ProfileState {
    var userProfile: UserProfile = .empty
    var struggles: [String] = []
    var hasRequestedReview: Bool = false
}

// aniccaios/aniccaios/State/AppState.swift (ファサード、100行以下)
@MainActor @Observable
class AppState {
    let auth = AuthState()
    let subscription = SubscriptionState()
    let nudge = NudgeState()
    let profile = ProfileState()
}
```

**修正手順:**

| # | ステップ | ファイル |
|---|---------|---------|
| 1 | `State/` ディレクトリ作成 | 新規 |
| 2 | AuthState 切り出し | `State/AuthState.swift` |
| 3 | SubscriptionState 切り出し | `State/SubscriptionState.swift` |
| 4 | NudgeState 切り出し | `State/NudgeState.swift` |
| 5 | ProfileState 切り出し | `State/ProfileState.swift` |
| 6 | AppState をファサードに変更 | `AppState.swift` |
| 7 | 全Viewの参照を更新 | `appState.authStatus` → `appState.auth.authStatus` |
| 8 | `@EnvironmentObject` → `@Environment` に移行（@Observable 対応） | 全View |

---

### P0-2: Cron ジョブ逐次処理のバッチ化

**重要度:** CRITICAL（performance）

**As-Is:**
```javascript
// apps/api/src/jobs/generateNudges.js:340
for (const user of users) {
    // 各ユーザーに対して 5-10 クエリを逐次実行
    const userType = await getUserTypeForNudge(user.id);     // 2 queries
    const shouldUse = await shouldUseLLM(user.id);           // 1 query
    const grounding = await collectAllGrounding(user.id);    // 3+ queries
    const feedback = await getUserFeedback(user.id);         // 1 query
    const result = await runCommanderAgent(user, grounding); // LLM API call
    // INSERT nudges 1件ずつ
    for (const nudge of result.schedule) {
        await query('INSERT INTO nudge_events ...', [nudge]); // 5-6 queries
    }
}
// 10ユーザー × 10クエリ = 100+ クエリが直列実行
```

**To-Be:**
```javascript
// apps/api/src/jobs/generateNudges.js
import pLimit from 'p-limit';

const limit = pLimit(5); // LLM API 同時呼び出し上限

// 1. 事前に全ユーザーのデータを一括取得
const allUserTypes = await batchGetUserTypes(userIds);
const allFeedback = await batchGetUserFeedback(userIds);

// 2. ユーザー処理を並列化（5並列）
const results = await Promise.allSettled(
    users.map(user => limit(async () => {
        const userType = allUserTypes.get(user.id);
        const feedback = allFeedback.get(user.id);
        const grounding = await collectAllGrounding(user.id);
        return runCommanderAgent(user, { userType, feedback, grounding });
    }))
);

// 3. Nudge をバッチ INSERT
const allNudges = results
    .filter(r => r.status === 'fulfilled')
    .flatMap(r => r.value.schedule);

await batchInsertNudges(allNudges);

// バッチ INSERT ヘルパー
async function batchInsertNudges(nudges) {
    if (nudges.length === 0) return;
    const values = nudges.map((n, i) => {
        const offset = i * 5;
        return `($${offset+1}, $${offset+2}, $${offset+3}, $${offset+4}, $${offset+5})`;
    }).join(', ');
    const params = nudges.flatMap(n => [n.userId, n.problemType, n.content, n.scheduledAt, n.state]);
    await query(`INSERT INTO nudge_events (user_id, problem_type, content, scheduled_at, state) VALUES ${values}`, params);
}
```

**修正手順:**

| # | ステップ | ファイル |
|---|---------|---------|
| 1 | `p-limit` パッケージ追加 | `apps/api/package.json` |
| 2 | バッチクエリ関数作成 | `apps/api/src/jobs/batchQueries.js`（新規） |
| 3 | generateNudges.js を並列化 | `apps/api/src/jobs/generateNudges.js` |
| 4 | バッチ INSERT 関数作成 | 同上 |
| 5 | コネクションプール二重作成を解消（独自Pool削除） | `generateNudges.js:42-46` |

---

### P0-3: NetworkSessionManager URLSession リーク修正

**重要度:** CRITICAL（architect 追加レポート）

**As-Is:**
```swift
// aniccaios/aniccaios/Services/NetworkSessionManager.swift:23-25
var session: URLSession {
    // computed property → アクセスするたびに新しい URLSession を生成
    URLSession(configuration: config)
}
```

**To-Be:**
```swift
// aniccaios/aniccaios/Services/NetworkSessionManager.swift
lazy var session: URLSession = {
    URLSession(configuration: config)
}()
```

**修正手順:**

| # | ステップ | ファイル |
|---|---------|---------|
| 1 | `var session` → `lazy var session` に変更 | `NetworkSessionManager.swift:23-25` |

---

### P0-4: Paywall 拒否直後のレビュー依頼を削除

**重要度:** HIGH（ux-reviewer）

**As-Is:**
```swift
// aniccaios/aniccaios/Views/Onboarding/OnboardingFlowView.swift:151-159
// Paywall を閉じた直後に実行
if appState.isEntitled == false {
    // Free Plan に進む
    SKStoreReviewController.requestReview()  // ← Paywall拒否直後にレビュー依頼
}
```

**To-Be:**
```swift
// レビュー依頼は以下の条件を全て満たす場合のみ
// 1. アプリ使用7日以上
// 2. Nudge に3回以上ポジティブ反応
// 3. Paywall表示から24時間以上経過

// OnboardingFlowView からは完全削除
if appState.isEntitled == false {
    // Free Plan に進む（レビュー依頼なし）
}

// 代わりに ReviewRequestManager で条件管理
// aniccaios/aniccaios/Services/ReviewRequestManager.swift（新規）
@MainActor @Observable
class ReviewRequestManager {
    func requestReviewIfEligible() {
        guard daysSinceInstall >= 7 else { return }
        guard positiveNudgeReactions >= 3 else { return }
        guard hoursSinceLastPaywallShow >= 24 else { return }
        SKStoreReviewController.requestReview()
    }
}
```

**修正手順:**

| # | ステップ | ファイル |
|---|---------|---------|
| 1 | OnboardingFlowView からレビュー依頼を削除 | `OnboardingFlowView.swift:151-159` |
| 2 | ReviewRequestManager 作成 | `Services/ReviewRequestManager.swift`（新規） |
| 3 | 適切なタイミングで呼び出し（NudgeCard ポジティブ反応後等） | `NudgeCardView.swift` |

---

### P0-5: ContentView ローカライズバグ修正

**重要度:** HIGH（ux-reviewer）— 実バグ

**As-Is:**
```swift
// aniccaios/aniccaios/ContentView.swift:40
Text("common_signing_in")  // ← ローカライズキーがそのまま表示される
```

**To-Be:**
```swift
Text(String(localized: "common_signing_in"))
```

**修正手順:**

| # | ステップ | ファイル |
|---|---------|---------|
| 1 | `Text("common_signing_in")` → `Text(String(localized: "common_signing_in"))` | `ContentView.swift:40` |

---

### P0-6: 罪悪感を煽る通知文言の差し替え

**重要度:** HIGH（ux-reviewer）

**As-Is → To-Be:**

| キー | As-Is（現在） | To-Be（修正後） | 理由 |
|------|-------------|----------------|------|
| staying_up_late variant | "Put down your phone. Now." | "Your pillow is waiting for you." | 命令形 → 優しい誘い |
| staying_up_late variant | "Tomorrow's you will regret this." | "Tomorrow's you will thank tonight's you." | 罪悪感 → ポジティブ転換 |
| staying_up_late variant | "How many years have you lost to 'just 5 more minutes'?" | "What if tonight is the night you try something different?" | 過去の失敗攻撃 → 可能性の提示 |
| staying_up_late negative (ja) | "傷つける" | 完全削除（非表示だが残存） | 自傷連想リスク |

**修正手順:**

| # | ステップ | ファイル |
|---|---------|---------|
| 1 | 英語文言差し替え | `Localizable.strings (en)` |
| 2 | 日本語文言差し替え + 「傷つける」削除 | `Localizable.strings (ja)` |

---

## P1（短期）— 6件

### P1-1: データアクセス二重経路の統一

**重要度:** HIGH（architect）

**As-Is:**
```javascript
// 経路1: apps/api/src/lib/db.js — 生の PgPool
const { Pool } = require('pg');
const pool = new Pool({ max: 5 });
module.exports = { query: (text, params) => pool.query(text, params) };

// 経路2: apps/api/src/lib/prisma.js — Prisma ORM
const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

// 同じテーブルに対して両方が混在
// nudge.js → db.query('SELECT * FROM nudge_events ...')
// profileService.js → prisma.nudgeEvent.findMany(...)
```

**To-Be:**
```javascript
// 方針: 新規コードは Prisma に統一。既存の db.query は段階的に移行。
// ただし generateNudges.js のバッチ INSERT など、
// Prisma では非効率な操作のみ db.query を許容する。

// apps/api/src/lib/db.js に明示的なコメント追加
/**
 * Raw SQL アクセス層
 * 使用条件: Prisma では非効率な操作のみ（バッチ INSERT、集計クエリ等）
 * 新規の CRUD 操作は必ず Prisma を使用すること
 */
```

**修正手順:**

| # | ステップ | ファイル |
|---|---------|---------|
| 1 | db.js に使用ガイドラインコメント追加 | `apps/api/src/lib/db.js` |
| 2 | nudge.js の単純クエリを Prisma に移行 | `apps/api/src/routes/mobile/nudge.js` |
| 3 | stateBuilder.js の集計クエリは db.query のまま（パフォーマンス上の理由） | 変更なし |

---

### P1-2: 認証 Middleware パターン統一

**重要度:** HIGH（architect）

**As-Is:**
```javascript
// パターン1: requireAuth.js — 関数呼び出し型（非標準）
// null 返却でレスポンス済みを示す
const userId = await requireAuth(req, res);
if (!userId) return;

// パターン2: requireInternalAuth.js — 標準 Express middleware
router.use(requireInternalAuth);

// パターン3: requireAgentAuth.js — 標準 Express middleware
router.use(requireAgentAuth);
```

**To-Be:**
```javascript
// 全て標準 Express middleware パターンに統一
// apps/api/src/middleware/auth.js（新規・統合）

function requireAuth(req, res, next) {
    const token = req.headers.authorization?.replace('Bearer ', '');
    if (!token) return res.status(401).json({ error: 'Unauthorized' });

    try {
        const userId = verifyToken(token);
        req.userId = userId;
        next();
    } catch (err) {
        return res.status(401).json({ error: 'Invalid token' });
    }
}

// ルートでの使用
router.get('/nudge/today', requireAuth, async (req, res) => {
    const userId = req.userId; // req から取得（null チェック不要）
});
```

**修正手順:**

| # | ステップ | ファイル |
|---|---------|---------|
| 1 | `middleware/auth.js` に統一版作成 | 新規 |
| 2 | requireAuth.js の呼び出し元を middleware パターンに移行 | 全 route ファイル |
| 3 | 旧ファイルを削除 | `requireAuth.js`, `extractUserId.js` |
| 4 | requireInternalAuth, requireAgentAuth は既に標準形のため変更なし | — |

---

### P1-3: コネクションプール二重作成の解消

**重要度:** HIGH（performance）

**As-Is:**
```javascript
// apps/api/src/jobs/generateNudges.js:42-46
const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    max: 5,
});
// db.js の pool とは別に独自 Pool を作成 → 接続数が倍消費
```

**To-Be:**
```javascript
// apps/api/src/jobs/generateNudges.js
const { query } = require('../lib/db');
// 共有プールを使用。独自 Pool は削除。
```

---

### P1-4: Nudge INSERT バッチ化

**重要度:** HIGH（performance）

P0-2 の修正に含まれる。`batchInsertNudges()` 関数で1クエリにまとめる。

---

### P1-5: 起動時 Task 一斉発火の段階化

**重要度:** HIGH（performance）

**As-Is:**
```swift
// aniccaios/aniccaios/AppState.swift:117-133
init() {
    // 4つの Task が同時に発火
    Task { await checkAndRecordIgnored() }
    Task { await sendIgnoredFeedbackForExpiredNudges() }
    Task { await bootstrapProfileFromServerIfAvailable() }
    Task { await fetchTodaysLLMNudges() }
}
```

**To-Be:**
```swift
init() {
    Task {
        // Phase 1: 必須（プロファイル復元）
        await bootstrapProfileFromServerIfAvailable()

        // Phase 2: 高優先（今日のNudge取得）
        await fetchTodaysLLMNudges()

        // Phase 3: バックグラウンド（フィードバック送信）
        Task.detached(priority: .utility) {
            await self.checkAndRecordIgnored()
            await self.sendIgnoredFeedbackForExpiredNudges()
        }
    }
}
```

---

### P1-6: エラーメッセージのユーザーフレンドリー化

**重要度:** HIGH（ux-reviewer）

**As-Is:**
```swift
// aniccaios/aniccaios/Views/MyPathTabView.swift:103
.alert("Error", isPresented: $showError) {
    // ...
} message: {
    Text(error.localizedDescription) // "Server error: 500" が表示される
}
```

**To-Be:**
```swift
.alert(String(localized: "common_error_title"), isPresented: $showError) {
    Button(String(localized: "common_ok")) { }
} message: {
    Text(String(localized: "common_error_generic"))
    // "うまくいきませんでした。時間をおいてもう一度お試しください"
}
```

**Localizable.strings に追加:**
```
"common_error_title" = "問題が発生しました";
"common_error_generic" = "うまくいきませんでした。時間をおいてもう一度お試しください。";
```

---

## P2（中期）— 7件

### P2-1: シングルトン12個の DI 化

**重要度:** HIGH（architect）

**As-Is:**
```swift
// 12個のシングルトンが密結合
AppState.shared
  ├── LLMNudgeService.shared
  ├── LLMNudgeCache.shared
  ├── ProblemNotificationScheduler.shared
  ├── NudgeContentSelector.shared
  ├── NudgeStatsManager.shared
  ├── NudgeFeedbackService.shared
  ├── SubscriptionManager.shared
  ├── ProfileSyncService.shared
  ├── AnalyticsManager.shared
  ├── FreePlanService.shared
  ├── NetworkSessionManager.shared
  └── QuoteProvider.shared
```

**To-Be:**
```swift
// プロトコル抽象化 + DI Container
protocol NudgeServiceProtocol {
    func fetchTodaysNudges() async throws -> [Nudge]
}

protocol AnalyticsProtocol {
    func track(_ event: String, properties: [String: Any])
}

// DI Container
@MainActor
class DependencyContainer {
    lazy var nudgeService: NudgeServiceProtocol = LLMNudgeService(network: networkManager)
    lazy var analytics: AnalyticsProtocol = AnalyticsManager()
    lazy var networkManager: NetworkSessionManagerProtocol = NetworkSessionManager()
    // ...
}

// View での使用
struct MyPathTabView: View {
    @Environment(DependencyContainer.self) var container
}
```

**修正手順:**

| # | ステップ | ファイル |
|---|---------|---------|
| 1 | 各サービスのプロトコル定義 | `Protocols/` ディレクトリ（新規） |
| 2 | DependencyContainer 作成 | `DI/DependencyContainer.swift`（新規） |
| 3 | 各 `.shared` 参照を Container 経由に変更 | 全サービス・View |
| 4 | テスト用 MockContainer 作成 | `Tests/Mocks/MockDependencyContainer.swift` |

---

### P2-2: Commander.js 分割（789行）

**重要度:** HIGH（architect）

**As-Is:**
```
apps/api/src/agents/commander.js (789行)
├── プロンプト構築
├── バリデーション
├── 正規化
├── ガードレール
└── テスト用 export
```

**To-Be:**
```
apps/api/src/agents/
├── commander.js           (エントリポイント、100行以下)
├── promptBuilder.js       (プロンプト構築)
├── responseValidator.js   (バリデーション)
├── responseNormalizer.js  (正規化)
├── guardrails.js          (ガードレール)
└── __tests__/
    ├── promptBuilder.test.js
    ├── responseValidator.test.js
    └── guardrails.test.js
```

---

### P2-3: DB クエリ並列化（5箇所）

**重要度:** MEDIUM（performance）

| # | ファイル | As-Is | To-Be |
|---|---------|-------|-------|
| 1 | `groundingCollectors.js:28-48` | 3クエリ逐次 await | `Promise.all([query1, query2, query3])` |
| 2 | `nudge.js:106-158` | 6クエリ逐次 | resolveProfileId 後に残り4つを `Promise.all` |
| 3 | `stateBuilder.js:138-152` | Promise.all(3) + 逐次2 | Promise.all(5) に統合 |
| 4 | `ProfileSyncService.swift:35-36` | MainActor.run 2回分離 | 1回にまとめる |
| 5 | `NudgeFeedbackService.swift:73-89` | for ループ逐次送信 | TaskGroup で5並列 |

---

### P2-4: NudgeStatsManager saveToStorage デバウンス化

**重要度:** HIGH（performance）

**As-Is:**
```swift
// 毎回の recordTapped/recordIgnored/recordScheduled で即座に全データ書き込み
func recordTapped(...) {
    stats[key]?.tappedCount += 1
    saveToStorage()  // ← 毎回呼ばれる
}
```

**To-Be:**
```swift
private var saveWorkItem: DispatchWorkItem?

private func scheduleSave() {
    saveWorkItem?.cancel()
    saveWorkItem = DispatchWorkItem { [weak self] in
        self?.saveToStorage()
    }
    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5, execute: saveWorkItem!)
}

func recordTapped(...) {
    stats[key]?.tappedCount += 1
    scheduleSave()  // ← 0.5秒デバウンス
}
```

---

### P2-5: Dynamic Type 対応

**重要度:** HIGH（ux-reviewer）

**As-Is:**
```swift
// 18箇所で固定サイズフォント
.font(.system(size: 28, weight: .bold))
.font(.system(size: 16))
```

**To-Be:**
```swift
// システムフォントスタイルに統一
.font(.title)        // 28pt 相当
.font(.body)         // 16pt 相当
.font(.headline)     // セクションヘッダー

// カスタムサイズが必要な場合
@ScaledMetric(relativeTo: .title) private var titleSize: CGFloat = 28
.font(.system(size: titleSize, weight: .bold))
```

**修正対象:**

| 箇所 | 現在 | 修正後 |
|------|------|--------|
| WelcomeStepView タイトル | `.system(size: 28, weight: .bold)` | `.title.bold()` |
| WelcomeStepView サブタイトル | `.system(size: 16)` | `.body` |
| StrugglesStepView ラベル | `.system(size: 14)` | `.subheadline` |
| NudgeCardView コンテンツ | `.system(size: 16)` | `.body` |
| 他14箇所 | 各種固定サイズ | 対応するシステムスタイル |

---

### P2-6: VoiceOver ラベル追加

**重要度:** HIGH（ux-reviewer）

**As-Is:**
```swift
// accessibilityLabel が 0件
Button(action: { sendFeedback(.positive) }) {
    Image(systemName: "hand.thumbsup.fill")
}
```

**To-Be:**
```swift
Button(action: { sendFeedback(.positive) }) {
    Image(systemName: "hand.thumbsup.fill")
}
.accessibilityLabel(String(localized: "nudge_feedback_helpful"))
.accessibilityHint(String(localized: "nudge_feedback_helpful_hint"))
```

**最低限追加すべき要素:**

| 要素 | accessibilityLabel |
|------|-------------------|
| Nudge サムズアップ | "この通知は役に立った" |
| Nudge サムズダウン | "この通知は役に立たなかった" |
| 問題カード | "{問題名}の通知設定" |
| オンボーディング「はじめる」ボタン | "はじめる" |
| Paywall 閉じるボタン | "閉じる" |
| 設定ボタン | "設定を開く" |

---

### P2-7: Paywall 前の期待感ステップ追加

**重要度:** MEDIUM（ux-reviewer）

**As-Is:**
```
通知許可 → 即 Paywall
```

**To-Be:**
```
通知許可 → 「最初の通知は○○時に届きます」画面 → Paywall
```

```swift
// aniccaios/aniccaios/Views/Onboarding/NudgePreviewStepView.swift（新規）
struct NudgePreviewStepView: View {
    let selectedProblems: [ProblemType]

    var body: some View {
        VStack(spacing: 24) {
            Text(String(localized: "onboarding_nudge_preview_title"))
                .font(.title2.bold())

            Text(String(localized: "onboarding_nudge_preview_subtitle"))
                .font(.body)
                .foregroundStyle(.secondary)

            // 選択した問題に基づく通知プレビュー
            ForEach(selectedProblems.prefix(3), id: \.self) { problem in
                NudgePreviewCard(problem: problem)
            }

            Button(String(localized: "onboarding_continue")) {
                // → Paywall に遷移
            }
        }
    }
}
```

---

## テストマトリックス

| # | To-Be | テスト名 | 種類 |
|---|-------|----------|------|
| 1 | AppState 分割後、AuthState 変更で NudgeView が再レンダリングされない | `test_authStateChange_doesNotTriggerNudgeViewUpdate` | Unit |
| 2 | バッチ INSERT で全 nudge が正しく保存される | `test_batchInsertNudges_savesAllRecords` | Integration |
| 3 | URLSession が1インスタンスのみ生成される | `test_networkSession_isSingleton` | Unit |
| 4 | Paywall 拒否後にレビュー依頼が発動しない | `test_paywallDismiss_doesNotRequestReview` | Unit |
| 5 | ローカライズキーが正しく解決される | `test_signingInText_isLocalized` | Unit |
| 6 | 修正後の通知文言がペルソナガイドラインに準拠 | `test_nudgeContent_noGuiltTripping` | Unit |
| 7 | 認証 middleware が標準パターンで動作 | `test_requireAuth_setsReqUserId` | Integration |
| 8 | 起動時 Task が段階的に実行される | `test_appInit_phased_taskExecution` | Unit |
| 9 | エラーメッセージがユーザーフレンドリー | `test_errorAlert_showsFriendlyMessage` | Unit |
| 10 | DI Container からモック注入可能 | `test_dependencyContainer_mockInjection` | Unit |
| 11 | saveToStorage がデバウンスされる | `test_saveToStorage_debounced` | Unit |
| 12 | Dynamic Type でフォントサイズが変化する | `test_dynamicType_fontsScale` | UI |
| 13 | VoiceOver ラベルが存在する | `test_voiceOver_labelsExist` | UI |

---

## 境界（やらないこと）

| やらないこと | 理由 |
|-------------|------|
| API versioning（URL-based `/api/v2/`）導入 | P3。現状の410スタブで後方互換は維持できている |
| Prisma 完全移行（db.js 廃止） | 段階的に移行。集計クエリは raw SQL のまま |
| Free Plan の通知ロジック変更 | 別 Spec で対応（ビジネス判断が必要） |
| オンボーディングの抜本的リデザイン | 別 Spec。今回は文言修正とステップ追加のみ |
| `agent_raw_output` のテーブル分離 | P3。データ量がまだ少ない |

---

## E2E 判定

| 項目 | 値 |
|------|-----|
| UI変更 | あり（エラーメッセージ、通知文言、NudgePreviewStep、Dynamic Type） |
| 新画面 | あり（NudgePreviewStepView） |
| 結論 | Maestro E2E シナリオ: **必要**（オンボーディングフロー + エラー表示） |

---

## 実行手順

```bash
# iOS テスト
cd aniccaios && FASTLANE_SKIP_UPDATE_CHECK=1 fastlane test

# API テスト
cd apps/api && npm test

# E2E テスト（Maestro MCP 経由）
# mcp__maestro__run_flow_files で実行
```

---

## 開発環境

| 項目 | 値 |
|------|-----|
| **ワークツリーパス** | TBD（実装開始時に作成） |
| **ブランチ** | `feature/1.6.2-review-reflection` |
| **ベースブランチ** | `dev` |
| **作業状態** | Spec 作成完了 |
