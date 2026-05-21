# API リファクタリング ゲームプラン v7

**日付**: 2026-01-29（2026-02-02 v7 — KEEP リスト全件監査、追加10件 DEAD 発見）
**対象**: `apps/api/src/` + `apps/landing/`
**ステータス**: 計画中（GATE 1 レビュー待ち）
**ブランチ**: dev → feature/backend-cleanup ワークツリーで実装

---

## 調査方法

サブエージェント計18並列（v4: 15 + v5: 3追加検証）+ v6 iOS Config.swift 完全監査で調査。

**v6 の追加監査方法**:
1. iOS `Config.swift` の全エンドポイント定義を抽出
2. `aniccaios/aniccaios/` + `aniccaios/AniccaNotificationService/` 全体を grep して実際の API 呼び出しを網羅
3. バックエンド `routes/index.js` → 各ルートファイル → 全55エンドポイントを列挙
4. iOS 呼び出しリスト × バックエンドルートリストをクロスリファレンス → iOS が呼ばないルートを特定

---

## 現状サマリー

| カテゴリ | ファイル数 | 状態 |
|---------|----------|------|
| iOS アクティブ（mobile/, auth/apple+refresh, billing/revenuecat等） | ~15 | ✅ KEEP |
| Admin/TikTok Agent（admin/tiktok, admin/hookCandidates, admin/xposts） | 3 | ✅ KEEP |
| Agents（commander, crossPlatformLearning, groundingCollectors等） | 6+5テスト | ✅ KEEP |
| Jobs アクティブ（generateNudges, monthlyCredits, aggregateTypeStats, syncCrossPlatform） | 5 | ✅ KEEP |
| Modules アクティブ（nudge, memory） | ~7 | ✅ KEEP |
| **Dead Mobile Routes（iOS Config.swift 監査で発覚）** | 3 | ❌ DELETE |
| **Dead Modules（behavior.js 連鎖で孤児化）** | 4 | ❌ DELETE |
| **Dead Auth/Nudge Routes（v7 KEEP 全件監査で発覚）** | 4 | ❌ DELETE |
| **Dead Bandit Policy（v7 import ゼロ確認）** | 3 | ❌ DELETE |
| **Dead Jobs/Services（v7 エントリポイントなし確認）** | 3 | ❌ DELETE |
| **Stripe Desktop 残骸** | 7+ | ❌ DELETE |
| **Google OAuth Desktop 残骸** | 4 | ❌ DELETE |
| **MCP GCal 孤児** | 6 | ❌ DELETE |
| **parallel-sdk 全体（Desktop Agent フレームワーク）** | 17 | ❌ DELETE |
| **Claude services（parallel-sdk 依存）** | 2 | ❌ DELETE |
| **tools/ 全エンドポイント（parallel-sdk Worker 専用）** | ~12 | ❌ DELETE |
| **mcp-clients（tools/ 依存）** | 4 | ❌ DELETE |
| **MCP HTTP server + config** | 2 | ❌ DELETE |
| **proxy/claude（Desktop Agent 専用）** | 2 | ❌ DELETE |
| **preview/app（Desktop Agent プレビュー）** | 3 | ❌ DELETE |
| **Slack 全コード（iOS 未使用）** | 4+ | ❌ DELETE |
| **OpenAI Realtime コード（iOS Voice 削除済み）** | 2 | ❌ DELETE |
| **Desktop/Web Realtime セッション** | 5 | ❌ DELETE |
| **workerMemory（parallel-sdk 専用）** | 1 | ❌ DELETE |
| **envelope crypto（gcal 削除で孤児化）** | 1 | ❌ DELETE |
| **Dead utils** | 3 | ❌ DELETE |
| **One-time scripts** | 2 | ❌ DELETE |
| **未使用 npm パッケージ** | 15+ | ❌ DELETE |
| Desktop 参照混在ファイル（config, subscriptionStore, server.js 等） | 3 | ⚠️ CLEAN |
| Landing Desktop 残骸 | 4修正 + 3削除 | ⚠️ CLEAN/DELETE |

**合計削除**: ~75ファイル以上 + ~8,000行以上

---

## 深層監査で判明した事実

### Stripe は完全に死んでいる（確定）

| 証拠 | 詳細 |
|------|------|
| 過去の削除コミット | `3eb0372f` で一度削除済み。マージ事故で復活 |
| iOS からの呼び出し | ゼロ。iOS は RevenueCat/Superwall |
| Stripe webhook トリガー | なし |

### parallel-sdk は全体として死んでいる（確定）

| 証拠 | 詳細 |
|------|------|
| 目的 | Desktop Agent システム（ParentAgent → Worker → BaseWorker → Claude services） |
| iOS/cron/routes からの import | ゼロ |
| 依存チェーン | parallel-sdk → claude services → tools/ → mcp-clients/ 全て連鎖的に死亡 |

### Slack は iOS で一切使われていない（確定）

| 証拠 | 詳細 |
|------|------|
| iOS の Slack エンドポイント呼び出し | ゼロ（`grep -r "slack" routes/mobile/` = 0件） |
| slackTokens.supabase.js の使用元 | api/tools/web/slack.js（削除対象）、api/tools/sdk/claude-code.js（削除対象）、api/auth/slack/*（Desktop OAuth）、server.js（init のみ） |
| TikTok Agent の Slack 使用 | ゼロ（hookSelector, wisdomExtractor に Slack 参照なし） |
| 結論 | Slack OAuth + トークン管理 + ツール全て Desktop Agent 専用。iOS は一切使わない |

### OpenAI Realtime API は iOS で削除済み（確定）

| 証拠 | 詳細 |
|------|------|
| VoiceSessionController.swift | コミット `9aaa5306`（2026-01-20）で 1,184行削除 |
| VoIP Background Mode | Info.plist から削除済み（コミット `d880a024`、2025-11-27） |
| Maestro E2E テスト | `03-session-start.yaml` + `04-session-completion.yaml` 削除済み（コミット `fe23706f`） |
| iOS Config.swift | URL 定義だけ孤児として残存（呼び出しコードなし） |
| 結論 | サーバー側 realtime コードは完全に孤児。iOS クライアントが存在しない |

### contextSnapshot.js は DEAD（v6 修正 — v5 ALIVE 判定を撤回）

| 証拠 | 詳細 |
|------|------|
| v5 時点の判定 | behavior.js L4 で import → ALIVE |
| v6 での発見 | **behavior.js 自体が DEAD**（iOS Config.swift に `/mobile/behavior/summary` なし） |
| consumer 一覧 | 1. behavior.js（DEAD）、2. realtime.js（DEAD） → consumer ゼロ |
| 結論 | **削除対象に変更**（A-18 で削除） |

### iOS Config.swift 完全監査（v6 新規）

iOS が実際に呼ぶエンドポイントを `Config.swift` + `aniccaios/` + `AniccaNotificationService/` 全体の grep で確定。

**iOS が呼ぶ10エンドポイント（確定）:**

| # | エンドポイント | iOS ファイル |
|---|--------------|-------------|
| 1 | POST `/auth/apple` | AuthCoordinator.swift |
| 2 | GET `/auth/apple/health` | AuthHealthCheck.swift |
| 3 | POST `/auth/refresh` | NetworkSessionManager.swift |
| 4 | GET/PUT `/mobile/profile` | AppState.swift / ProfileSyncService.swift |
| 5 | DELETE `/mobile/account` | MyPathTabView.swift |
| 6 | GET `/mobile/entitlement` | SubscriptionManager.swift |
| 7 | POST `/billing/revenuecat/sync` | SubscriptionManager.swift |
| 8 | POST `/mobile/nudge/trigger` | NudgeTriggerService.swift |
| 9 | POST `/mobile/nudge/feedback` | NudgeFeedbackService.swift |
| 10 | GET `/mobile/nudge/today` | LLMNudgeService.swift |

**+ Notification Service Extension が呼ぶ1エンドポイント:**

| # | エンドポイント | iOS ファイル |
|---|--------------|-------------|
| 11 | POST `/mobile/nudge/pre-reminder` | AniccaNotificationService/NotificationService.swift:86 |

**バックエンドに存在するが iOS が呼ばない mobile ルート（DEAD）:**

| ルート | ファイル | 理由 |
|--------|---------|------|
| GET `/mobile/behavior/summary` | behavior.js | Config.swift に不在。iOS コード 0件 |
| GET `/mobile/user-type` | userType.js | Config.swift に不在。iOS コード 0件 |
| GET `/mobile/realtime/session` + 5 endpoints | realtime.js | Config.swift に URL 定義あるが呼び出しコードなし（VoiceSessionController 削除済み） |

**Config.swift に定義あるが呼び出しなし（孤児 URL）:**

| URL | 状態 |
|-----|------|
| `realtimeSessionURL` | 呼び出しコードなし（VoiceSessionController 削除済み） |
| `realtimeSessionStopURL` | 同上 |
| `feelingStartURL` | 呼び出しコードなし、バックエンドにもハンドラなし |
| `feelingEndURL` | 同上 |

### openai npm パッケージは直接使われていないが KEEP（v5 修正）

| 証拠 | 詳細 |
|------|------|
| `from 'openai'` / `require('openai')` | grep 0件。直接 import なし |
| `@openai/agents` | commander.js 等で使用。peer dependency として `openai` が必要 |
| 結論 | `openai` は `@openai/agents` の peer dep として **残す** |

### Phase D feeling バグは存在しない（v5 修正）

| 証拠 | 詳細 |
|------|------|
| `routes/mobile/index.js` | grep "feeling" = 0件。feelingRouter 参照なし |
| 結論 | 過去のコミットで既に修正済み。Phase D 削除 |

### @composio/*, @vercel/mcp-adapter は全て未使用（確定）

import/require ゼロ。

### /mcp/gcal は完全に孤児（確定・ユーザー確認済み）

呼び出し元ゼロ。

---

## ⚠️ 重要: routes/index.js アトミック修正ルール

**Phase A の各削除ステップで、対応する `routes/index.js` の `app.use()` マウントを同時に削除すること。**

ファイル削除だけして routes/index.js を後回しにするとサーバーが起動時にクラッシュする。
各 A-X の「同時修正」セクションに routes/index.js の修正を明記。

---

## Phase A: Dead Code 完全削除

### A-1: Stripe 課金コード全削除

| # | ファイル | 理由 |
|---|---------|------|
| 1 | `src/api/billing/checkoutSession.js` | Stripe checkout — マージ事故で復活した死コード |
| 2 | `src/api/billing/portalSession.js` | Stripe portal — 呼び出し元ゼロ |
| 3 | `src/api/billing/webhookStripe.js` | Stripe webhook — トリガーなし |
| 4 | `src/routes/billing/checkout-session.js` | ルートマウント |
| 5 | `src/routes/billing/portal-session.js` | ルートマウント |
| 6 | `src/routes/billing/webhook/stripe.js` | ルートマウント |
| 7 | `src/services/stripe/` (全3ファイル: checkout.js, client.js, webhookHandler.js) | Stripe サービス層 |

**⚠️ A-1 は必ず1コミットで実施**（#7 stripe/ 削除と #9 subscriptionStore.js クリーンアップを分離すると ESM static import が解決できずサーバークラッシュ）

**同時修正（サーバークラッシュ防止）**:

| # | ファイル | 作業 |
|---|---------|------|
| 8 | `src/routes/billing/index.js` | checkout-session, portal-session, webhook/stripe の import/マウント削除。RC のみ残す |
| 9 | `src/services/subscriptionStore.js` | **Stripe 関連**: L2 `./stripe/client.js` import 削除、`ensureStripeCustomer()` / `recordStripeEvent()` / `updateSubscriptionFromStripe()` / `clearSubscription()` 削除、`ENTITLEMENT_SOURCE.STRIPE` 削除、L244 `getEntitlementState()` の fallback を `ENTITLEMENT_SOURCE.STRIPE` → `'revenuecat'` に変更（null entitlement_source の既存ユーザー保護）、`normalizeStatus()` の Stripe ブランチ（L102-113: trialing/past_due/incomplete 等）削除。**Realtime 関連**: `getTodayUsage()` / `startUsageSession()` / `finishUsageSessionAndBill()` / `canUseRealtime()` / `getMonthlyUsage()` / `resolveMonthlyLimit()` 削除、`getEntitlementState()` 内の usage 計算フィールド削除（Realtime 削除後は無意味） |
| 10 | `src/server.js` | Stripe webhook 参照削除（L70 `stripeWebhookPath` 定義、L72 `express.raw()` ミドルウェア、L78/L82 の条件分岐） |

### A-2: Google OAuth Desktop 残骸削除

| # | ファイル | 理由 |
|---|---------|------|
| 1 | `src/api/auth/google/oauth.js` | Desktop 専用 |
| 2 | `src/api/auth/google/callback.js` | Desktop 専用 |
| 3 | `src/api/auth/google/refresh.js` | Desktop 専用 |
| 4 | `src/routes/auth/google/index.js` | ルートマウント（ディレクトリごと削除） |

**同時修正**:

| # | ファイル | 作業 |
|---|---------|------|
| 5 | `src/routes/index.js` | auth/google マウント削除 |

### A-3: MCP GCal 孤児削除

| # | ファイル | 理由 |
|---|---------|------|
| 1 | `src/api/mcp/gcal/` (4ファイル: callback.js, disconnect.js, oauth-url.js, status.js) | 呼び出し元ゼロ |
| 2 | `src/routes/mcp/gcal/index.js` | ルートマウント |
| 3 | `src/services/googleTokens.js` | gcal 専用（自己参照のみ） |

**同時修正**:

| # | ファイル | 作業 |
|---|---------|------|
| 4 | `src/routes/index.js` | mcp/gcal マウント削除 |

### A-4: Slack 全コード削除（iOS 未使用）

| # | ファイル | 理由 |
|---|---------|------|
| 1 | `src/api/auth/slack/oauth-url.js` | Slack OAuth — iOS 未使用。Desktop Agent 専用 |
| 2 | `src/api/auth/slack/oauth-callback.js` | 同上 |
| 3 | `src/api/auth/slack/check-connection.js` | 同上 |
| 4 | `src/routes/auth/slack/index.js` | ルートマウント |
| 5 | `src/services/tokens/slackTokens.supabase.js` | Slack トークン管理 — tools/slack（削除）と auth/slack（削除）のみ使用 |

**同時修正**:

| # | ファイル | 作業 |
|---|---------|------|
| 6 | `src/server.js` | slackTokens import と `initDatabase()` 呼び出し削除 |
| 7 | `src/routes/index.js` | auth/slack マウント削除 |

### A-5: OpenAI Realtime コード削除（iOS Voice 機能削除済み）

| # | ファイル | 理由 |
|---|---------|------|
| 1 | `src/services/openaiRealtimeService.js` | iOS の VoiceSessionController は 2026-01-20 に削除。呼び出し元なし |
| 2 | `src/routes/mobile/realtime.js` | 6エンドポイント全て iOS から呼ばれない（Config.swift に URL だけ残存、呼び出しコードなし） |

**⚠️ contextSnapshot.js は A-18 で別途削除**: behavior.js 自体が DEAD と判明（v6）。consumer ゼロ。

**同時修正**:

| # | ファイル | 作業 |
|---|---------|------|
| 3 | `src/routes/mobile/index.js` | realtime ルートの import/マウント削除 |
| 4 | iOS: `aniccaios/Config.swift` | 孤児 URL 定義（realtimeSessionURL, realtimeSessionStopURL, feelingStartURL, feelingEndURL）削除 |

### A-6: Desktop/Web Realtime セッション削除

| # | ファイル | 理由 |
|---|---------|------|
| 1 | `src/routes/realtime/desktop.js` | Desktop リアルタイムセッション — iOS 未使用 |
| 2 | `src/routes/realtime/web.js` | Web リアルタイムセッション — iOS 未使用 |
| 3 | `src/api/proxy/realtime/desktopSession.js` | Desktop セッションプロキシ — iOS 未使用 |
| 4 | `src/api/proxy/realtime/desktopStop.js` | Desktop セッション停止 — iOS 未使用 |
| 5 | `src/api/proxy/realtime/webSession.js` | Web セッションプロキシ — iOS 未使用 |

**同時修正**:

| # | ファイル | 作業 |
|---|---------|------|
| 6 | `src/routes/index.js` | realtime/desktop, realtime/web マウント削除 |

**ディレクトリ確認**: `src/routes/realtime/` と `src/api/proxy/realtime/` が空になったらディレクトリごと削除。

### A-7: parallel-sdk 全削除（Desktop Agent フレームワーク）

| # | ファイル | 理由 |
|---|---------|------|
| 1-8 | `src/services/parallel-sdk/core/` (4ファイル: BaseWorker.js, Worker.js, ParentAgent.js, index.js) + `IPCProtocol.js` + `prompts/` (2ファイル) + `utils/PreviewManager.js` | Desktop Agent — import ゼロ |
| 9-18 | `src/services/parallel-sdk/config/instructions/` (5ファイル) + `config/profiles/` (5ファイル) | Worker 設定 |

**ディレクトリ全体を削除（18ファイル）**: `rm -rf src/services/parallel-sdk/`

### A-8: Claude services 削除（parallel-sdk 依存で死亡）

| # | ファイル | 理由 |
|---|---------|------|
| 1 | `src/services/claude/executorService.js` | parallel-sdk Worker からのみ呼ばれる |
| 2 | `src/services/claude/sessionManager.js` | 同上 |

**ディレクトリ全体を削除**: `rm -rf src/services/claude/`

### A-9: tools/ 全エンドポイント削除（Desktop Agent Worker 専用）

| # | ファイル | 理由 |
|---|---------|------|
| 1-6 | `src/routes/tools/` (6ファイル: news, search_exa, claude_code, slack, playwright, transcribe) | Worker のみ |
| 7-12 | `src/api/tools/` (web/news, web/search, web/browser, web/slack, sdk/claude-code, transcribe) | Worker のみ |

**同時修正**:

| # | ファイル | 作業 |
|---|---------|------|
| 13 | `src/routes/index.js` | tools/* マウント全削除 |

**ディレクトリ全体を削除**: `rm -rf src/routes/tools/ src/api/tools/`

### A-10: MCP clients + server 削除

| # | ファイル | 理由 |
|---|---------|------|
| 1-2 | `src/mcp/clients/` (exaClient, playwrightClient) | tools/ のみ使用 |
| 3-4 | `src/services/mcp-clients/` (exaClient, playwrightClient) | 同上（重複パス） |
| 5 | `src/mcp/servers/http/index.js` | Desktop Agent MCP サーバー |
| 6 | `src/api/mcp/config.js` | 空オブジェクト返すだけ |

**routes/index.js**: mcp マウントは `/mcp/gcal` のみ（A-3 で削除済み）。A-10 での routes/index.js 修正は不要。

**ディレクトリ確認**: gcal + clients + servers + config.js 削除で `src/mcp/` が空 → ディレクトリごと削除。

### A-11: proxy/claude 削除（Desktop Agent 専用）

| # | ファイル | 理由 |
|---|---------|------|
| 1 | `src/routes/proxy/claude.js` | Claude API プロキシ — Desktop のみ |
| 2 | `src/api/proxy/claude.js` | 同上 |

**同時修正**:

| # | ファイル | 作業 |
|---|---------|------|
| 3 | `src/routes/index.js` | proxy/claude マウント削除 |

**注意**: A-6 の realtime proxy 削除と合わせて `src/api/proxy/` と `src/routes/proxy/` が空になったらディレクトリごと削除。

### A-12: preview/app 削除（Desktop Agent プレビュー）

| # | ファイル | 理由 |
|---|---------|------|
| 1 | `src/routes/preview/app.js` | Desktop Agent のみ |
| 2 | `src/api/static/preview-app.js` | 同上 |
| 3 | `src/api/static/preview/[...path].js` | 同上 |

**同時修正**:

| # | ファイル | 作業 |
|---|---------|------|
| 4 | `src/routes/index.js` | preview/* マウント削除 |

**ディレクトリ全体を削除**: `rm -rf src/routes/preview/ src/api/static/`

### A-13: workerMemory 削除

| # | ファイル | 理由 |
|---|---------|------|
| 1 | `src/services/storage/workerMemory.js` | parallel-sdk 削除で孤児化 |

### A-14: envelope crypto 削除（gcal 削除で孤児化）

| # | ファイル | 理由 |
|---|---------|------|
| 1 | `src/lib/crypto/envelope.js` | googleTokens.js からのみ使用 → gcal 削除で孤児化 |

### A-15: Dead utils 削除

| # | ファイル | 理由 |
|---|---------|------|
| 1 | `src/utils/migrate-to-logger.js` | import ゼロ。CLI ワンタイムツール（既に実行済み） |
| 2 | `src/utils/errorHandler.js` | import ゼロ。ApiError クラスがあるが誰も使っていない |
| 3 | `src/utils/state.js` | gcal OAuth のみ使用 → A-3 削除で孤児化 |

### A-16: One-time scripts 削除

| # | ファイル | 理由 |
|---|---------|------|
| 1 | `src/scripts/backfill-user-types.js` | 実行済みマイグレーション |
| 2 | `src/scripts/initHookLibrary.js` | 実行済み初期データ投入 |

### A-17: 未使用 npm パッケージ削除

| # | パッケージ | 理由 | 確認 |
|---|-----------|------|------|
| 1 | `@composio/core` | import ゼロ | ✅ 確定 |
| 2 | `@composio/openai` | import ゼロ | ✅ 確定 |
| 3 | `@vercel/mcp-adapter` | import ゼロ | ✅ 確定 |
| 4 | `stripe` | Stripe 全コード削除 | ✅ 確定 |
| 5 | `@anthropic-ai/claude-code` | claude services + tools/claude_code 削除で不要 | ⚠️ grep |
| 6 | `@modelcontextprotocol/sdk` | mcp/ 全削除で不要 | ⚠️ grep |
| 7 | `@google-cloud/kms` | envelope.js のみ使用 → A-14 削除で不要 | ⚠️ grep |
| 8 | `exa-mcp-server` | mcp-clients/exaClient のみ使用 → A-10 削除で不要 | ⚠️ grep |
| 9 | `busboy` | tools/transcribe のみ使用 → A-9 削除で不要 | ⚠️ grep |
| 10 | `form-data` | tools/transcribe のみ使用 → A-9 削除で不要 | ⚠️ grep |
| 11 | `mime-types` | api/static/preview のみ使用 → A-12 削除で不要 | ⚠️ grep |
| 12 | `@slack/web-api` | Slack 全コード削除（A-4） | ⚠️ grep |
| 13 | `@google-cloud/text-to-speech` | tools/transcribe のみ使用 → A-9 削除で不要 | ⚠️ grep |
| 14 | `node-cron` | parallel-sdk/core/Worker.js のみ使用 → A-7 削除で不要 | ⚠️ grep |
| 15 | `axios` | api/auth/slack/oauth-callback.js のみ使用 → A-4 削除で不要 | ⚠️ grep |
| 16 | `uuid` | parallel-sdk + api/tools/sdk のみ使用 → A-7/A-9 削除で不要 | ⚠️ grep |
| 17 | `@js-temporal/polyfill` | import ゼロ。完全未使用 | ✅ 確定 |
| 18 | `vercel` (devDependencies) | Desktop-era デプロイ用。Railway 移行後は不要 | ⚠️ grep |

**KEEP（削除禁止）**:

| パッケージ | 理由 |
|-----------|------|
| `openai` | `@openai/agents` の peer dependency。直接 import はないが必要 |
| `@openai/agents` | agents/commander.js 等で使用（1.5.0 Cross-User Learning） |

**注意**: ⚠️ は実装時に grep 確認必須。

### A-18: Dead Mobile Routes & Modules 削除（v6 iOS Config.swift 監査で発覚）

iOS `Config.swift` + `aniccaios/` + `AniccaNotificationService/` 全体の grep でクロスリファレンスした結果、以下のルート/モジュールは iOS から一切呼ばれていないと確定。

#### Dead Routes

| # | ファイル | エンドポイント | DEAD 理由 |
|---|---------|-------------|----------|
| 1 | `src/routes/mobile/behavior.js` | GET `/mobile/behavior/summary` | iOS Config.swift に不在。iOS コード grep 0件 |
| 2 | `src/routes/mobile/userType.js` | GET `/mobile/user-type` | iOS Config.swift に不在。iOS コード grep 0件 |

**注意**: `services/userTypeService.js` は **削除しない**。`jobs/generateNudges.js` L17 で `classifyUserType()` を import（cron 使用）。ルートファイル（userType.js）のみ削除。

#### Dead Modules（behavior.js 連鎖で孤児化）

| # | ファイル | 唯一の consumer | consumer の状態 |
|---|---------|----------------|---------------|
| 3 | `src/modules/simulation/futureScenario.js` | behavior.js | DEAD |
| 4 | `src/modules/insights/generateTodayInsight.js` | behavior.js | DEAD |
| 5 | `src/modules/metrics/stateBuilder.js` | behavior.js | DEAD |
| 6 | `src/modules/realtime/contextSnapshot.js` | behavior.js + realtime.js | 両方 DEAD |

**同時修正**:

| # | ファイル | 作業 |
|---|---------|------|
| 7 | `src/routes/mobile/index.js` | behavior, userType ルートの import/マウント削除 |

**ディレクトリ確認**: `src/modules/simulation/` が空 → ディレクトリ削除。`src/modules/insights/` が空 → ディレクトリ削除。`src/modules/metrics/` から stateBuilder.js 削除後、nudge 用 stateBuilder（`modules/nudge/features/stateBuilder.js`）は別ファイルなので影響なし。`src/modules/realtime/` は contextSnapshot.js 削除で空 → ディレクトリ削除。

### A-19: Dead Auth/Nudge Routes 削除（v7 KEEP 全件監査で発覚）

| # | ファイル | エンドポイント | DEAD 理由 |
|---|---------|-------------|----------|
| 1 | `src/routes/auth/entitlement.js` | POST `/auth/entitlement` | iOS は `/mobile/entitlement` を使う。`/auth/entitlement` は呼ばれない |
| 2 | `src/api/auth/entitlement.js` | — (ハンドラ) | ↑ のルートが DEAD → ハンドラも DEAD |
| 3 | `src/routes/auth/logout.js` | POST `/auth/logout` | iOS は `Purchases.shared.logOut()`（RevenueCat ネイティブ）を使う。バックエンド logout は呼ばれない |
| 4 | `src/routes/nudge/generate.js` | POST `/nudge/generate` + GET `/nudge/today` | POST: Railway cron は `node src/jobs/generateNudges.js` を直接実行（HTTP 不要）。GET: iOS は `/mobile/nudge/today`（routes/mobile/nudge.js）を使用 |

**同時修正**:

| # | ファイル | 作業 |
|---|---------|------|
| 5 | `src/routes/index.js` | auth/entitlement, auth/logout, nudge/generate マウント削除 |

**注意**: `services/auth/refreshService.js` は routes/auth/logout.js 削除後も ALIVE（routes/auth/refresh.js と routes/mobile/account.js が使用）

### A-20: Dead Bandit Policy 削除（v7 import ゼロ確認）

| # | ファイル | DEAD 理由 |
|---|---------|----------|
| 1 | `src/modules/nudge/policy/mentalBandit.js` | import ゼロ。どこからも使われていない |
| 2 | `src/modules/nudge/policy/wakeBandit.js` | import ゼロ。どこからも使われていない |
| 3 | `src/modules/nudge/policy/linTS.js` | importer は mentalBandit.js と wakeBandit.js のみ → 両方 DEAD で連鎖的に孤児化 |

**ディレクトリ確認**: `src/modules/nudge/policy/` が空 → ディレクトリ削除

### A-21: Dead Jobs/Agents/Services 削除（v7 エントリポイントなし確認）

| # | ファイル | DEAD 理由 |
|---|---------|----------|
| 1 | `src/jobs/aggregateTypeStats.js` | エントリポイントなし。Railway cron にも server.js にも参照なし。完全孤児 |
| 2 | `src/agents/dayCycling.js` | import ゼロ確定。v5 では「要別途確認」だったが、v7 で DEAD 確定 |
| 3 | `src/services/guestSessions.js` | consumer: desktopSession.js（A-6 削除）+ api/auth/entitlement.js（A-19 削除）→ consumer ゼロ |

**agents/dayCycling テスト**: `src/agents/__tests__/dayCycling.test.js` も本体削除と同時に削除。

### A-Landing: Landing Page クリーンアップ

#### Desktop 参照修正

| # | ファイル | 現状 | 修正後 |
|---|---------|------|--------|
| 1 | `app/billing/success/page.tsx` | "Return to the desktop app" | **ページ削除**（到達不可能） |
| 2 | `app/faq/page.tsx:17` | "macOS 10.15+" | iOS 対応情報に更新 |
| 3 | `app/tokushoho/page.tsx:42` | "macOSデスクトップアプリ" | "iOSアプリ" |
| 4 | `app/tokushoho/page.tsx:46` | "Apple Silicon搭載macOS向け" | "iOS向け" |
| 5 | `app/tokushoho/page.tsx:72` | "Desktopアプリで即時反映" | "iOSアプリで即時反映" |
| 6 | `app/tokushoho/page.tsx:76` | "Apple Silicon搭載のmacOS" | "iOS 17以降" |
| 7 | `app/tokushoho/page.tsx:80` | "Desktopアプリ「Upgrade to Pro」" | RC/Superwall 解約手順 |
| 8 | `app/support/en/page.tsx:65` | "both iOS and desktop (Mac)" | "iOS devices" |

#### 未使用コンポーネント + npm 削除

| # | ファイル/パッケージ | 理由 |
|---|-------------------|------|
| 1 | `components/ui/badge.tsx` | import ゼロ |
| 2 | `components/ui/button.tsx` | import ゼロ |
| 3 | `components/ui/separator.tsx` | import ゼロ |
| 4 | `@radix-ui/react-separator` | separator 削除で不要 |

---

## Phase B: Desktop 参照クリーンアップ（残存ファイル内の掃除）

### B-1: config/environment.js 大規模クリーンアップ

| # | 対象 | 作業 |
|---|------|------|
| 1 | `DESKTOP_MODE` | フラグ定義削除 |
| 2 | `BILLING_CONFIG` Stripe フィールド | `STRIPE_SECRET_KEY`, `STRIPE_PRICE_PRO_MONTHLY`, `STRIPE_PRODUCT_PRO`, `STRIPE_WEBHOOK_SECRET`, `CHECKOUT_RETURN_URL`, `PORTAL_RETURN_URL` 削除 |
| 3 | `MODEL_CONFIG.CLAUDE_WORKER_DEFAULT_MODEL` | proxy/claude.js のみ → 削除 |
| 4 | `USE_PROXY` | claude/executorService.js のみ → 削除 |
| 5 | `DIRECTORIES.USER_DATA` | parallel-sdk のみ → 削除 |
| 6 | `API_KEYS.ANTHROPIC` | proxy/claude.js のみ → 削除 |
| 7 | `validateEnvironment()` | Stripe 関連警告削除 |
| 8 | `logEnvironment()` | Stripe/Desktop ログ行削除 |

### B-2: server.js 追加クリーンアップ

| # | 作業 |
|---|------|
| 1 | Desktop/Agent 関連の起動ロジックがあれば削除 |
| 2 | slackTokens/Stripe は Phase A で削除済み。残存がないか最終確認 |

### B-3: package.json 整理

| # | 作業 |
|---|------|
| 1 | 削除パッケージの残存参照確認 |
| 2 | scripts セクションの Desktop 関連コマンド削除（`dev`: `vercel dev`、`deploy`: `vercel --prod`） |
| 3 | `description` 更新（"Proxy server for ANICCA AI Screen Narrator" → iOS API 用に更新） |
| 4 | `keywords` 更新（"proxy", "gemini", "claude" 等 Desktop-era 用語削除） |

---

## Phase C: Prisma スキーマ精査

**スコープ**: schema.prisma 編集 + `prisma generate` のみ。本番 DB 変更なし。

### 削除候補

| # | モデル/フィールド | 状態 | 作業 |
|---|-----------------|------|------|
| 1 | `stripeCustomerId` (User) | Stripe 削除で不要 | raw SQL grep → 削除可否 |
| 2 | `stripeSubscriptionId` (User) | 同上 | 同上 |
| 3 | `MobileAlarmSchedule` | コード参照ゼロ（pre-v0.3 レガシー） | 削除 |
| 4 | `HabitLog` | コード参照ゼロ（NudgeEvent/NudgeOutcome に置換済み） | 削除 |
| 5 | `MobileVoipToken` | VoIP は iOS Info.plist から削除済み | 削除 |
| 6 | `RealtimeUsageDaily` | Realtime 機能削除で不要 | grep 確認 → 削除可否 |
| 7 | `UsageSession` | Desktop セッション tracking のみ | grep 確認 → 削除可否 |
| 8 | `SensorAccessState` | Profile.metadata.sensorAccess に JSON で保存しており、このモデルは未使用 | 削除 |

**絶対禁止**: `prisma migrate dev`, `prisma db push`, `prisma migrate deploy`

---

## 実行順序と受け入れ条件

| ステップ | 作業 | 受け入れ条件 |
|---------|------|-------------|
| 1 | Phase A-1〜A-16, A-18〜A-21（API Dead Code 大量削除 + routes/index.js 同時修正） | `npm test` 全 PASS。routes/index.js に削除対象マウントなし |
| 2 | A-17（npm パッケージ削除 — コード削除完了後に実施） | `npm install` 成功。`npm test` PASS |
| 3 | A-Landing（Landing クリーンアップ） | `cd apps/landing && npm run build` 成功 |
| 4 | Phase B（Desktop 参照除去） | `npm test` PASS。`grep -r "DESKTOP_MODE\|STRIPE_SECRET\|platform.*desktop" src/` = 0件 |
| 5 | Phase C（Prisma 精査） | `npx prisma generate` 成功。`npm test` PASS |
| 6 | レビュー | サブエージェント並列レビュー ok |
| 7 | push | — |

---

## 残すファイル一覧（全ファイル、理由付き）

### routes/

| ファイル | 何をしている | なぜ必要 |
|---------|------------|---------|
| `routes/index.js` | 全ルートのマウント | Express 起動に必須 |
| `routes/auth/apple.js` | Apple Sign-in 認証 | 旧ユーザーのログイン |
| `routes/auth/refresh.js` | JWT リフレッシュ | NetworkSessionManager.swift L53 で呼び出し確認済み |
| `routes/billing/index.js` | RevenueCat webhook + sync のマウント | iOS 課金 |
| `routes/billing/revenuecat-sync.js` | RC 手動同期 | 課金状態修正 |
| `routes/billing/webhook/revenuecat.js` | RC webhook | サブスク変更検知 |
| `routes/mobile/account.js` | アカウント削除 | GDPR 対応 |
| `routes/mobile/entitlement.js` | サブスク状態確認 | iOS 課金チェック |
| `routes/mobile/nudge.js` | Nudge trigger/feedback/today | iOS Nudge 通知コア |
| `routes/mobile/preReminder.js` | Notification Extension からの事前リマインダー | `AniccaNotificationService/NotificationService.swift:86` で呼び出し確認済み |
| `routes/mobile/profile.js` | プロフィール CRUD | iOS ユーザー設定 |
| `routes/mobile/index.js` | mobile ルートマウント | Express 構造 |
| `routes/admin/tiktok.js` | TikTok 投稿管理 | GitHub Actions TikTok Agent |
| `routes/admin/hookCandidates.js` | Hook 候補選定 | GitHub Actions |
| `routes/admin/xposts.js` | X（Twitter）投稿管理（/admin/x にマウント） | GitHub Actions |

### api/ ハンドラ層

| ファイル | 何をしている | なぜ必要 |
|---------|------------|---------|
| `api/billing/revenuecatSync.js` | RC sync ハンドラ | routes/billing から呼ばれる |
| `api/billing/webhookRevenueCat.js` | RC webhook ハンドラ | routes/billing から呼ばれる |

**注意**: `api/auth/apple/` ディレクトリは存在しない。Apple Sign-in ロジックは routes/auth/apple.js に直接実装されている。api/ 層の正確なファイル一覧は実装時に確認。

### agents/ （1.5.0 Cross-User Learning で追加）

| ファイル | 何をしている | なぜ必要 |
|---------|------------|---------|
| `agents/commander.js` | OpenAI Agents SDK で Nudge 生成を統括 | jobs/generateNudges.js から使用 |
| `agents/crossPlatformLearning.js` | TikTok ↔ iOS 間の学習データ同期 | jobs/syncCrossPlatform.js から使用 |
| `agents/groundingCollectors.js` | Nudge 生成用のグラウンディングデータ収集 | jobs/generateNudges.js から使用 |
| `agents/reasoningLogger.js` | Commander の決定ログ + Slack 通知 | jobs/generateNudges.js から使用 |
| `agents/scheduleMap.js` | Nudge スケジュール定義 + スロットテーブル | jobs/nudgeHelpers.js から使用 |
| `agents/__tests__/` (4ファイル) | commander, crossPlatformLearning, reasoningLogger, scheduleMap のテスト | テストスイート |

### services/

| ファイル | 何をしている | なぜ必要 |
|---------|------------|---------|
| `services/auth/appleService.js` | Apple ID トークン検証（JWKS） | 旧ユーザー認証 |
| `services/auth/refreshService.js` | リフレッシュトークン発行・ローテーション | JWT 認証基盤 |
| `services/auth/refreshStore.js` | リフレッシュトークン PostgreSQL 保存 | 認証基盤 |
| `services/mobile/userIdResolver.js` | UUID/apple_user_id → profiles.id マッピング | 全 mobile ルートで使用 |
| `services/mobile/profileService.js` | プロフィール保存・取得 | iOS プロフィール |
| `services/revenuecat/api.js` | RevenueCat API クライアント | iOS 課金 |
| `services/revenuecat/webhookHandler.js` | RC webhook 処理 | サブスク変更処理 |
| `services/revenuecat/virtualCurrency.js` | 仮想通貨（分単位）管理 | 月次クレジット付与 |
| `services/users/profileStore.js` | 外部ID → 内部UUID マッピング | Apple/Anonymous ユーザー作成 |
| `services/hookSelector.js` | Thompson Sampling で Hook A/B テスト | TikTok Agent |
| `services/wisdomExtractor.js` | 高パフォーマンス Hook パターン抽出 | TikTok Agent |
| `services/userTypeService.js` | ユーザータイプ分類（T1-T4） | iOS + Nudge 生成 |
| `services/subscriptionStore.js` | サブスク状態管理（Stripe + Realtime 関数は A-1 で除去） | iOS 課金確認 |

### modules/

| ファイル | 何をしている | なぜ必要 |
|---------|------------|---------|
| `modules/memory/mem0Client.js` | Mem0 AI メモリ管理 | nudge.js, preReminder.js で使用（iOS Nudge パーソナライズ） |
| `modules/nudge/features/stateBuilder.js` | Bandit モデル用特徴量エンコーディング | routes/mobile/nudge.js L10 で import |
| `modules/nudge/reward/rewardCalculator.js` | Nudge 報酬計算 | routes/mobile/nudge.js で import |

### jobs/

| ファイル | 何をしている | なぜ必要 |
|---------|------------|---------|
| `jobs/generateNudges.js` | 日次 LLM Nudge 生成 | Railway cron（CRON_MODE=nudges） |
| `jobs/monthlyCredits.js` | 月次仮想通貨付与 | server.js setInterval |
| `jobs/nudgeHelpers.js` | Nudge 生成ヘルパー | generateNudges から使用 |
| `jobs/syncCrossPlatform.js` | TikTok ↔ iOS 間の学習データ同期 | generateNudges.js L13 で import |

### middleware/

| ファイル | 何をしている | なぜ必要 |
|---------|------------|---------|
| `middleware/extractUserId.js` | Bearer JWT からユーザーID抽出 | 全 mobile ルートで使用 |
| `middleware/requireAuth.js` | JWT 署名検証（member + guest 対応） | 認証必須エンドポイント |
| `middleware/requireInternalAuth.js` | INTERNAL_API_TOKEN 検証（timing-safe） | admin ルート（tiktok, hookCandidates, xposts） |

### utils/

| ファイル | 何をしている | なぜ必要 |
|---------|------------|---------|
| `utils/logger.js` | 統一ログシステム（レベル、色、タイムスタンプ、コンテキスト） | 18+ファイルから使用 |
| `utils/timezone.js` | タイムゾーンユーティリティ（Intl.DateTimeFormat） | Nudge/メトリクス計算 |
| `utils/jwt.js` | JWT HS256 署名 | refreshService, apple, mobile/entitlement |

### lib/

| ファイル | 何をしている | なぜ必要 |
|---------|------------|---------|
| `lib/db.js` | PostgreSQL プール管理・クエリ実行 | 17ファイルから使用（DB 基盤） |
| `lib/prisma.js` | PrismaClient シングルトン | 7ファイルから使用 |
| `lib/migrate.js` | DB マイグレーション実行 | server.js 起動時 |

### config/

| ファイル | 何をしている | なぜ必要 |
|---------|------------|---------|
| `config/environment.js` | 環境変数一元管理（Phase B でクリーンアップ） | 全体基盤 |

### テスト

| ディレクトリ | ファイル数 | 内容 | なぜ必要 |
|------------|----------|------|---------|
| `agents/__tests__/` | 4 | commander, crossPlatformLearning, reasoningLogger, scheduleMap | agents/ テスト |
| `jobs/__tests__/` | 2 | generateNudges, nudgeHelpers | jobs/ テスト（syncCrossPlatform テスト有無は実装時確認） |
| `routes/admin/__tests__/` | 2 | tiktok, xposts | admin ルートテスト |
| `services/__tests__/` | 3 | hookSelector, userTypeService, wisdomExtractor | services/ テスト |

**注意**: `src/generated/prisma/` は `prisma generate` の自動生成ファイル（~30ファイル）。手動管理対象外。

### エントリポイント

| ファイル | 何をしている | なぜ必要 |
|---------|------------|---------|
| `server.js` | Express サーバーエントリポイント | 起動に必須 |
| `prisma/schema.prisma` | DB スキーマ定義 | Prisma 必須 |

---

## やらないこと（境界）

| 項目 | 理由 |
|------|------|
| 上記「残すファイル一覧」の変更（Phase B/C のクリーンアップ対象を除く） | 全て iOS/Admin/Cron アクティブ |
| `apps/landing/` の構造変更 | テキスト修正 + 未使用コンポーネント削除のみ |
| 本番 DB のテーブル/カラム削除 | schema.prisma 編集 + generate のみ |
| `services/userTypeService.js` の削除 | ルート（userType.js）は削除するがサービスは `generateNudges.js` cron が使用中 |

---

## 1.6.0-one-buddha との依存関係

| パッケージ | backend-cleanup | one-buddha | 衝突 |
|-----------|----------------|------------|------|
| `@openai/agents` | KEEP | ^0.4.4 | なし |
| `openai` | **KEEP**（peer dep） | ^6.17.0 | なし |
| `@composio/*` | 削除 | 不使用 | なし |
| `stripe` | 削除 | 不使用 | なし |

**マージ順序**: backend-cleanup → one-buddha。削除を先に。

---

## v6 → v7 変更点サマリー（KEEP リスト全件監査）

| # | 変更 | 理由 |
|---|------|------|
| 1 | `routes/auth/entitlement.js` + `api/auth/entitlement.js` を KEEP → A-19 削除に移動 | iOS は `/mobile/entitlement` を使う。`/auth/entitlement` は呼ばれない |
| 2 | `routes/auth/logout.js` を KEEP → A-19 削除に移動 | iOS は RevenueCat ネイティブ `logOut()` を使う |
| 3 | `routes/nudge/generate.js` を KEEP → A-19 削除に移動 | POST: cron は JS 直接実行。GET: iOS は `/mobile/nudge/today` を使用。両方 DEAD |
| 4 | `modules/nudge/policy/` 全3ファイル（linTS, mentalBandit, wakeBandit）を KEEP → A-20 削除に移動 | 全て import ゼロ。linTS は mentalBandit/wakeBandit のみが使用、両方 DEAD |
| 5 | `jobs/aggregateTypeStats.js` を KEEP → A-21 削除に移動 | エントリポイントなし。Railway cron にも server.js にも参照なし |
| 6 | `agents/dayCycling.js` + テスト を KEEP → A-21 削除に移動 | v5 「要別途確認」→ v7 で DEAD 確定（import ゼロ） |
| 7 | `services/guestSessions.js` を KEEP → A-21 削除に移動 | consumer: desktopSession（A-6 削除）+ auth/entitlement（A-19 削除）→ ゼロ |
| 8 | 合計削除量を ~80 → ~90 ファイル、~8,800 → ~11,000 行に更新 | A-19〜A-21 の追加分 |

---

## v5 → v6 変更点サマリー（iOS Config.swift 完全監査）

| # | 変更 | 理由 |
|---|------|------|
| 1 | contextSnapshot.js を ALIVE → DEAD に変更 | behavior.js（唯一の live consumer）が DEAD と判明。consumer ゼロ |
| 2 | `routes/mobile/behavior.js` を KEEP → A-18 削除に移動 | iOS Config.swift に `/mobile/behavior/summary` 不在。iOS コード grep 0件 |
| 3 | `routes/mobile/userType.js` を KEEP → A-18 削除に移動 | iOS Config.swift に `/mobile/user-type` 不在。iOS コード grep 0件。ただし `userTypeService.js` は cron が使用 → KEEP |
| 4 | `modules/simulation/futureScenario.js` を KEEP → A-18 削除に移動 | behavior.js 専用 → behavior.js DEAD で孤児化 |
| 5 | `modules/insights/generateTodayInsight.js` を KEEP → A-18 削除に移動 | 同上 |
| 6 | `modules/metrics/stateBuilder.js` を KEEP → A-18 削除に移動 | 同上 |
| 7 | `modules/realtime/contextSnapshot.js` を KEEP → A-18 削除に移動 | 同上 |
| 8 | preReminder.js の KEEP 根拠を強化 | `AniccaNotificationService/NotificationService.swift:86` で呼び出し確認 |
| 9 | iOS Config.swift 孤児 URL に feeling（start/end）を追加 | バックエンドにハンドラなし、iOS にも呼び出しなし |
| 10 | 合計削除量を ~75 → ~80 ファイル、~8,000 → ~8,800 行に更新 | A-18 の6ファイル追加分 |

---

## v4 → v5 変更点サマリー

| # | 変更 | 理由 |
|---|------|------|
| 1 | contextSnapshot.js を A-5 削除リストから除外 | behavior.js L4 で import。iOS Behavior タブで使用 |
| 2 | desktopStop.js を A-6 に追加 | 存在していたが v4 で漏れ |
| 3 | agents/ (6ソース+5テスト) を KEEP リストに追加 | 1.5.0 Cross-User Learning の新サブシステム |
| 4 | jobs/syncCrossPlatform.js を KEEP リストに追加 | generateNudges.js から import |
| 5 | routes/admin/xposts.js を KEEP リストに追加 | /admin/x にマウント済み |
| 6 | routes/index.js 修正を各 Phase A に統合 | ファイル削除と同時でないとサーバークラッシュ |
| 7 | server.js Stripe 参照（L70,72,78,82）を A-1 に追加 | stripeWebhookPath 定義が残存 |
| 8 | subscriptionStore.js Realtime 関数を A-1 に追加 | A-5/A-6 削除後に孤児化する4関数 |
| 9 | Phase D 削除 | feeling バグは存在しない（grep 0件） |
| 10 | openai npm を KEEP に変更 | @openai/agents の peer dependency |
| 11 | @slack/web-api を A-17 に追加 | Slack 全削除（A-4）で不要 |
| 12 | @google-cloud/text-to-speech を A-17 に追加 | tools/transcribe 削除で不要 |
| 13 | api/ ハンドラ層を KEEP リストに追加 | routes/ から呼ばれるハンドラ |
| 14 | テストディレクトリを KEEP リストに追加 | テストスイート |
| 15 | dayCycling.js を「削除禁止」に明記 | import ゼロだが新規追加、要別途確認 |

---

## 予想される削除量

| Phase | 削除ファイル数 | 削除行数（推定） |
|-------|-------------|----------------|
| A-1〜A-3 (Stripe/Google/GCal) | ~17 | ~2,000 |
| A-4 (Slack) | ~5 | ~400 |
| A-5〜A-6 (Realtime) | ~7 | ~1,200 |
| A-7〜A-12 (Desktop Agent 系) | ~40+ | ~3,500+ |
| A-13〜A-16 (Dead utils/scripts) | ~5 | ~400 |
| A-18 (Dead mobile routes/modules) | 6 | ~800 |
| A-19 (Dead auth/nudge routes) | 4 | ~600 |
| A-20 (Dead bandit policy) | 3 | ~500 |
| A-21 (Dead jobs/agents/services) | 3+1テスト | ~400 |
| A-17 (npm packages) | — | package.json |
| A-Landing | 4削除 + 3修正 | ~200 |
| Phase B | 2ファイル修正 | ~300 |
| Phase C (Prisma) | 8モデル/フィールド | ~100 |
| **合計** | **~90+ファイル削除 + ~6修正** | **~11,000+行** |

---

## リスク管理

| リスク | 対策 |
|--------|------|
| Stripe 削除でクラッシュ | subscriptionStore.js + billing/index.js + server.js を同時修正（A-1 で明記） |
| routes/index.js 不整合 | 各 Phase A で同時修正（アトミックルール適用） |
| Slack 削除で Worker 破壊 | parallel-sdk 自体が死コード。Worker は存在しない |
| Realtime 削除で iOS 破壊 | iOS VoiceSessionController は 2026-01-20 に削除済み。Config.swift の孤児 URL も同時削除 |
| behavior.js 削除で preReminder.js 破壊 | preReminder.js は behavior.js を import しない。独立（mem0Client のみ共有） |
| contextSnapshot.js 誤 KEEP | v6 で DEAD 確定。consumer（behavior.js + realtime.js）両方 DEAD |
| agents/ 誤削除 | generateNudges.js 等が使用確認済み。KEEP リストに明記 |
| openai 誤削除 | @openai/agents の peer dep。KEEP に明記 |
| npm パッケージ誤削除 | ⚠️ マークは実装時 grep 必須 |
| auth/logout 削除で refreshService 破壊 | refreshService は refresh.js + account.js も使用。logout 削除で孤児化しない |
| guestSessions 削除 | consumer 全て削除済み（desktopSession A-6, auth/entitlement A-19） |
| bandit policy 削除で nudge 破壊 | nudge.js は mentalBandit/wakeBandit を import しない。stateBuilder + rewardCalculator のみ使用 |
| nudge/generate.js 削除で LLM Nudge 破壊 | cron は jobs/generateNudges.js を直接実行。iOS は /mobile/nudge/today を使用。別系統 |
| Prisma モデル削除 | generate のみ。DB カラム残置 |

### ロールバック・監視

| 項目 | 方法 |
|------|------|
| ロールバック | `git revert` Phase 単位。Railway 自動再デプロイ |
| 監視: API 5xx | Railway ログ 30 分間 |
| 監視: iOS | `/mobile/*`, `/auth/apple/*`, `/billing/revenuecat/*` 正常応答確認 |
| 監視: Landing | Netlify 主要ページ 404 確認 |
| 判断基準 | 5xx 1% 超 → 即 revert |
