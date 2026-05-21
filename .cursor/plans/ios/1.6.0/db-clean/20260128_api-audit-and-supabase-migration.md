# API監査 & Supabase移行調査レポート

**調査日**: 2026年1月28日
**対象**: `apps/api/` + プロジェクト全体構造
**現在Phase**: 7-8（LLM判断 + 根本原因深掘り）

---

## Part 1: 現状の真実（何を実際に使っているか）

### データベース

| 項目 | 実態 |
|------|------|
| **DB** | PostgreSQL（Railway上） |
| **接続** | `DATABASE_URL` 環境変数 → `pg` ドライバ（pool: max 5） |
| **ORM** | Prisma v6.0.0 |
| **接続ファイル** | `apps/api/src/lib/db.js` |
| **スキーマ** | `apps/api/prisma/schema.prisma`（20モデル） |

**結論: メインDBはRailway PostgreSQL。Supabaseは「DBとして」は使っていない。**

### Supabaseの実際の使われ方

Supabaseは**DBではなく、補助サービスとして**一部使われている:

| 用途 | ファイル | 状態 |
|------|---------|------|
| Slackトークン保存 | `src/services/tokens/slackTokens.supabase.js` | ACTIVE（5ファイルが依存） |
| Worker Memory保存 | `src/services/storage/workerMemory.js` | ACTIVE（agent記憶用） |
| Google OAuth | `src/api/auth/google/*.js`（3ファイル） | ACTIVE |
| Entitlement確認 | `src/api/auth/entitlement.js` | ACTIVE |
| Preview App | `src/api/static/preview-app.js` | ACTIVE |
| ParentAgent | `src/services/parallel-sdk/core/ParentAgent.js` | ACTIVE |

**合計: 18ファイルでSupabase SDKをインポート**

### iOSアプリが使うAPIルート

| ルート | 用途 | 状態 |
|--------|------|------|
| `/api/mobile/nudge/*` | Nudge配信・フィードバック | ACTIVE |
| `/api/mobile/feeling/*` | 感情チェックイン | ACTIVE |
| `/api/mobile/behavior/summary` | 日次サマリー | ACTIVE |
| `/api/mobile/profile` | ユーザープロファイル | ACTIVE |
| `/api/mobile/entitlement` | サブスク状態 | ACTIVE |
| `/api/mobile/account` | アカウント削除 | ACTIVE |
| `/api/mobile/daily_metrics` | ヘルスデータ | ACTIVE |
| `/api/mobile/sensors` | HealthKit権限 | ACTIVE |

### iOSが使わないルート（Desktop/Web/Agent用）

| ルート | 用途 | iOS使用 |
|--------|------|---------|
| `/api/realtime/desktop` | Desktopリアルタイムセッション | NO |
| `/api/realtime/web` | Webリアルタイム | NO |
| `/api/tools/*` | News/Search/Claude Code/Playwright/Slack | NO |
| `/api/proxy/claude` | Claude APIプロキシ | NO |
| `/api/mcp/gcal` | Googleカレンダー | NO |
| `/api/billing/*` | Stripe決済 | NO（RevenueCat経由） |

---

## Part 2: Dead Code / 削除候補

### Prismaモデル（完全未使用）

| モデル | 状態 | 理由 |
|--------|------|------|
| `HabitLog` | DEAD | ProblemTypeベースに置換済み |
| `MobileAlarmSchedule` | DEAD | ルールベースNudgeに置換済み |
| `SensorAccessState` | DORMANT | 定義のみ、読み書きゼロ |

### Desktop残骸

| ディレクトリ/ファイル | 内容 | 最終更新 |
|----------------------|------|---------|
| `apps/desktop/` | Electron + Quasar UIアプリ | 2024/11/17 |
| `apps/api/src/api/proxy/realtime/desktopSession.js` | Desktopリアルタイム | ACTIVE |
| `apps/api/src/api/proxy/realtime/desktopStop.js` | Desktop停止 | ACTIVE |
| `docs/electron.md` | Electronアーキ設計 | 古い |
| `docs/desktop-auth-and-mcp-token-architecture.md` | Desktop認証設計 | 古い |
| `docs/desktop-billing-subscription-plan.md` | Desktop課金設計 | 古い |
| `release/` | Desktop DMGバイナリ | 2024/08 |
| `.worktrees/feature-nitwork3-desktop-improvement` | Desktop改善ワークツリー | 古い |

### その他Dead Code

| ディレクトリ | 内容 | 状態 |
|-------------|------|------|
| `apps/web/` | Next.js Webアプリ | DORMANT（2021年以降ほぼ活動なし） |
| `examples/` | 45個のサンプルプロジェクト | DEAD |
| `plantuml/` | PlantUMLツールクローン | DEAD |
| `apps/workspace-mcp/` | Google Workspace MCP | TOOL（開発補助） |
| `supabase/migrations/` | 旧Supabaseマイグレーション3件 | DEAD（Prisma移行済み） |

### パッケージ（削除候補）

| パッケージ | 理由 |
|-----------|------|
| `@supabase/supabase-js` | 移行後に削除（移行前は残す） |
| `@anthropic-ai/claude-code` | Parent Agent用（iOS非依存） |
| `@composio/core`, `@composio/openai` | Agent用（iOS非依存） |
| `@google-cloud/text-to-speech` | 音声機能削除済みなら不要 |
| `mem0ai` | Agent記憶用（iOS非依存） |

---

## Part 3: Supabase移行の判断

### 決定: YES — Supabaseに移行する

| # | 理由 | 重要度 |
|---|------|--------|
| 1 | **Realtimeが将来必須**（Phase 8+） — Railway自前実装 vs Supabase Built-in | CRITICAL |
| 2 | **Solo Developer** — DevOps削減 = 機能開発に集中 | CRITICAL |
| 3 | **コスト削減** — Railway $92.50/月 → Supabase Pro $25/月（約70%減） | HIGH |
| 4 | **早期ステージ** — ユーザーが少ない今が最適タイミング | HIGH |
| 5 | **既にSupabase検討歴** — コードに残存、学習コスト低 | MEDIUM |

### ただし注意: Railway APIサーバーは残す

**重要な区別:**
- **移行対象**: データベース（Railway PostgreSQL → Supabase PostgreSQL）
- **維持**: APIサーバー自体はRailway上で動き続ける（Node.js Express）
- **理由**: APIロジック（Nudge生成、cron job、LLM呼び出し等）はRailwayのコンテナで動くべき

```
現状:
  Railway Container (API) → Railway PostgreSQL

移行後:
  Railway Container (API) → Supabase PostgreSQL
  + Supabase Realtime / Auth / Storage を直接活用
```

### 移行フェーズ

| Phase | タスク | 期間 |
|-------|--------|------|
| 1 | Supabaseプロジェクト作成、環境変数セットアップ | 1日 |
| 2 | pg_dumpでスキーマ移行 | 1日 |
| 3 | データ移行 + 検証 | 1-2日 |
| 4 | API接続先変更（DATABASE_URL切替）+ テスト | 2-3日 |
| 5 | Production切替 + 監視 | 1日 |

---

## Part 4: リファクタリング計画（優先順）

### Phase A: 即座にやるべき（移行前のクリーンアップ）

| # | タスク | 影響ファイル数 | リスク |
|---|--------|-------------|--------|
| 1 | Dead Prismaモデル削除（HabitLog, MobileAlarmSchedule） | 1 | 低 |
| 2 | `supabase/migrations/` ディレクトリ削除 | 3ファイル | 低 |
| 3 | 古いワークツリー整理（`git worktree prune`） | 0（git管理） | 低 |

### Phase B: Supabase移行と同時にやる

| # | タスク | 影響 |
|---|--------|------|
| 1 | `slackTokens.supabase.js` → Supabase直接接続に統一 | 5ファイル |
| 2 | `workerMemory.js` → Supabase Storage統一 | 1ファイル |
| 3 | Google OAuth → Supabase Auth移行検討 | 3ファイル |

### Phase C: Desktop/Web決断後にやる

| # | タスク | 条件 |
|---|--------|------|
| 1 | `apps/desktop/` 削除 | Desktop廃止確定なら |
| 2 | Desktop API routes削除 | Desktop廃止確定なら |
| 3 | `apps/web/` 削除 | Web不要確定なら |
| 4 | Desktop関連docs削除 | Desktop廃止確定なら |
| 5 | `release/` バイナリ削除 | Desktop廃止確定なら |
| 6 | Desktop用パッケージ削除 | Desktop廃止確定なら |

### Phase D: 一般クリーンアップ

| # | タスク | リスク |
|---|--------|--------|
| 1 | `examples/` ディレクトリ削除 | 低 |
| 2 | `plantuml/` 削除 | 低 |
| 3 | package.json description更新（「AI Screen Narrator」→ 正しい説明） | 低 |
| 4 | CLAUDE.mdの「Supabase使ってる」誤記修正 | 低 |

---

## Part 5: プロジェクト構造の真実

```
anicca-project/
├── aniccaios/              ← iOS本体（PRIMARY、毎日更新）
├── apps/
│   ├── api/                ← Node.js API（Railway、毎日更新）
│   ├── desktop/            ← Electron（2024/11以降停止）← 廃止判断必要
│   ├── landing/            ← Next.js LP（Netlify、アクティブ）
│   ├── web/                ← Next.js Web（2021以降停止）← 削除候補
│   └── workspace-mcp/      ← Google Workspace MCP（開発ツール）
├── daily-apps/             ← Daily Dhamma RN App（アクティブ）
├── docs/                   ← ドキュメント（混在：アクティブ + アーカイブ）
├── examples/               ← サンプル（DEAD）← 削除候補
├── maestro/                ← E2Eテスト（アクティブ）
├── plantuml/               ← ツールクローン（DEAD）← 削除候補
├── release/                ← Desktopバイナリ（2024/08）← 削除候補
└── .cursor/plans/          ← Spec・計画（アクティブ）
```

---

## 情報源

| トピック | ソース |
|---------|--------|
| Railway vs Supabase比較 | [pgbench.com](https://pgbench.com/comparisons/postgres-vs-supabase/), [uibakery](https://uibakery.io/blog/railway-vs-supabase) |
| Supabase移行ガイド | [Supabase公式](https://supabase.com/docs/guides/platform/migrating-to-supabase/postgres) |
| コスト比較 | [getdeploying.com](https://getdeploying.com/railway-vs-supabase), [Supabase Pricing](https://supabase.com/pricing) |
| マネージドPostgreSQL 2026 | [sqlflash.ai](https://sqlflash.ai/article/20260114_aws-azure-gcp-supabase-postgresql-2026/) |
