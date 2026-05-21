# API Backend Architecture (v1.6.2)

## 概要
Node.js + Express API。Railway上でStaging/Production運用。

## ディレクトリ構成
- `src/server.js` — エントリーポイント
- `src/routes/` — エンドポイント定義
- `src/services/` — ビジネスロジック
- `src/jobs/` — Cronジョブ
- `src/agents/` — LLMエージェント (Commander)
- `src/middleware/` — 認証・バリデーション
- `src/modules/` — 機能モジュール
- `prisma/` — DBスキーマ・マイグレーション

## 主要エンドポイント
### Mobile API (/api/mobile)
- GET/POST /profile — ユーザープロフィール
- GET /entitlement — サブスク状態(RevenueCat)
- GET /nudge/today — 日次LLM Nudge
- POST /nudge/feedback — Nudgeフィードバック
- POST /auth/apple — Apple認証

### Agent API (/api/agent — OpenClaw用)
- POST /nudge — 外部プラットフォーム用Nudge生成
- GET /wisdom — Wisdomコンテンツ
- POST /content — プラットフォーム別コンテンツ生成
- GET /posts — エージェント投稿一覧

### Admin API (/api/admin — 内部用)
- GET /tiktok/pending — TikTok投稿キュー
- POST /tiktok/sync-metrics — メトリクス同期
- GET /hook-candidates — Hook一覧

## Prisma テーブル (25テーブル)
### 認証・ユーザー
tokens, refresh_tokens, profiles, user_settings, mobile_profiles, user_subscriptions, subscription_events, monthly_vc_grants

### ユーザーインサイト
user_traits, user_type_estimates, type_stats

### Nudge・行動
nudge_events, nudge_outcomes, feeling_sessions, bandit_models, notification_schedules

### コンテンツ・Hook
hook_candidates, wisdom_patterns, tiktok_posts, x_posts, agent_posts, agent_audit_logs

## Cronジョブ
- generateNudges.js — 毎日05:00 JST、Commander agentでNudge生成
- monthlyCredits.js — 月初、月額クレジット付与
- aggregateTypeStats.js — タップ率集計

## Railway構成
| 環境 | APIサービス | Cronサービス | デプロイトリガー |
|------|-----------|-------------|----------------|
| Staging | API | nudge-cron | dev push |
| Production | API | nudge-cronp | main push |

## 主要サービス
- Commander Agent — OpenAI構造化出力でNudgeスケジュール決定
- HookSelector — Thompson SamplingでHook選択
- UserTypeService — T1-T4ユーザー分類
- SubscriptionStore — RevenueCatエンタイトルメントキャッシュ

## 認証方式
- Bearer JWT (HS256) — モバイルAPI
- Agent Token — OpenClaw API
- Internal API Token — Admin API
- RevenueCat Webhook — サブスクイベント

## 必須環境変数
DATABASE_URL, OPENAI_API_KEY, PROXY_AUTH_JWT_SECRET, PROXY_GUEST_JWT_SECRET, ANICCA_AGENT_TOKEN, INTERNAL_API_TOKEN