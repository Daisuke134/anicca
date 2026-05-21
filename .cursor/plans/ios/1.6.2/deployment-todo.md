# 1.6.2 デプロイ & 実践 TODO（Runbook）

> VoxYZ + Oliver Henry + x-research-skill の学びを Anicca に適用するタスクリスト

## Phase 1: ループを回す（今週）

| # | タスク | ステータス | 依存 | 詳細 |
|---|--------|-----------|------|------|
| P1-1 | x-research-skill を Claude Code にインストール | ✅ | - | `.claude/skills/x-research` にクローン |
| P1-2 | x-research-skill を OpenClaw VPS にインストール | ⬜ | P1-1 | `/home/anicca/.openclaw/skills/x-research` + X_BEARER_TOKEN |
| P1-3 | feature/closed-loop-ops → dev マージ | ✅ | P1-1,P1-2 | 408テスト PASS → dev マージ完了 |
| P1-4 | Railway Staging デプロイ確認 | ✅ | P1-3 | dev push → 自動デプロイ → /health OK |
| P1-5 | DB Migration 実行（Staging） | ✅ | P1-4 | Prisma migrate deploy → 7テーブル作成 + seed |
| P1-6 | VPS Heartbeat Cron 追加 | ✅ | P1-5 | `*/5 * * * *` crontab → heartbeat OK |
| P1-7 | X API 実接続（post_x Executor） | ✅ | P1-5 | Blotato API (account 11852) → X投稿成功 |
| P1-8 | 手動テスト: Proposal → Mission → X投稿 | ✅ | P1-6,P1-7 | 3ステップ全成功: draft→verify→post_x |
| P1-9 | fetch_metrics Executor 実接続 | ✅ | P1-7 | Blotato解決→X API v2→DB更新→analyze_engagement |
| P1-10 | 48h Trigger テスト | ✅ | P1-8,P1-9 | 24h後自動発火→fetch_metrics→analyze→Thompson更新 |

### Phase 1 ゴール
> X投稿 → 効果測定 → Thompson Sampling 学習 の1サイクルが自動で回ること

---

## Phase 2: 頭脳を増やす（VoxYZ パターン、2週間）

| # | タスク | ステータス | 依存 | 詳細 |
|---|--------|-----------|------|------|
| P2-1 | OpenClaw マルチエージェント設計 | ✅ | P1-10 | anicca(共感), hunter(発見), growth(分析) の3エージェント |
| P2-2 | openclaw.json agents[] 追加 | ✅ | P2-1 | VPS `openclaw.json` に `anicca/hunter/growth` 追加 |
| P2-3 | Roundtable 会話スキル作成 | ✅ | P2-2 | API側で standup/debate/watercooler 実装 |
| P2-4 | 朝スタンドアップ Cron 追加 | ✅ | P2-3 | OpenClaw cron `09:00 JST` → `/api/admin/roundtable/standup` |
| P2-5 | 構造化 Memory テーブル追加 | ✅ | P2-1 | `memory_items`（scope/category/key/value/confidence/source/expires_at） |
| P2-6 | 会話ログ → Memory 自動抽出 | ✅ | P2-4,P2-5 | OpenClaw cron `08:55 JST` → `/api/admin/roundtable/memory-extract` |
| P2-7 | Initiative システム | ✅ | P2-6 | OpenClaw cron `09:05 JST` → `/api/admin/roundtable/initiative-generate` |
| P2-8 | x-research を Trend-Hunter に統合 | ✅ | P1-2 | 最小統合: `research_items` + admin API + roundtable から参照 |
| P2-9 | Reaction Matrix 設定 | ✅ | P2-2 | 数値固定 + テスト |
| P2-10 | Day-0 自律運用レディネス | ⬜ | P2-1〜P2-9 | `autonomy-check pass=true` を1回出せば完了（以降は日次運用） |

### Phase 2 ゴール
> 3エージェントが毎日会話し、自発的に Proposal を生成し、学習すること

---

## Phase 3: 放置で回る（Oliver Henry レベル、1ヶ月）

| # | タスク | ステータス | 依存 | 詳細 |
|---|--------|-----------|------|------|
| P3-1 | TikTok API 実接続（post_tiktok Executor） | ⬜ | P2-10 | TikTok API v2 |
| P3-2 | オンボーディング最適化ループ | ⬜ | P2-10 | ファネル測定 → A/Bテスト自動生成 → 勝者適用 |
| P3-3 | 広告最適化ループ | ⬜ | P2-10 | TikTok Ads / ASA → CPI測定 → クリエイティブ改善 |
| P3-4 | Voice Evolution（個性の進化） | ⬜ | P2-6 | VoxYZ パターン: memory 分布から個性を動的生成 |
| P3-5 | Dynamic Affinity（関係性） | ⬜ | P2-4 | エージェント間の好感度が会話で変動 |
| P3-6 | オンボ→Paywall→Trial 最適化 | ⬜ | P3-2 | 42.8% → 60%、1.1% → 5% を目標 |
| P3-7 | 完全自律運用（2週間テスト） | ⬜ | P3-1〜P3-6 | あなたの操作: 20分/日以下 |

### Phase 3 ゴール
> あなたが1週間旅行に行っても DL が増え続けること

---

## 参照

| ソース | URL/パス | 学び |
|--------|----------|------|
| VoxYZ 記事 | @Voxyz_ai | 閉ループ、Roundtable、Memory、Affinity、Initiative |
| Oliver Henry | @oliverhenry | 完全自律マーケティング、オンボ最適化 |
| x-research-skill | github.com/rohunvora/x-research-skill | X API リサーチ CLI |
| Closed-Loop Ops Spec | `.cursor/plans/ios/1.6.2/implementation/closed-loop-ops/` | 14ファイル |
| Trend-Hunter Spec | `.cursor/plans/ios/1.6.2/implementation/trend-hunter/` | 11ファイル |

---

最終更新: 2026-02-09
