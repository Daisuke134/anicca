# Railway PostgreSQL vs Supabase 移行調査

**調査日時**: 2026年1月28日
**調査対象**: Railway PostgreSQL から Supabase への移行可否
**プロジェクト**: Anicca iOS App (Phase 7-8)

---

## 📊 調査結果サマリー

```
決定: YES - Supabase へ移行すべき
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
タイミング: 今すぐ (Phase 7-8)
移行方法: 段階的アプローチ (5フェーズ)
リスク: 低〜中 (早期ステージのため)
ROI: 高 (開発時間削減 + コスト削減)
```

---

## 1. プラットフォーム比較

### Railway PostgreSQL

| 項目 | 詳細 |
|------|------|
| **タイプ** | 汎用コンテナホスティング + PostgreSQL |
| **特徴** | フル柔軟性、任意のサービスをデプロイ可能 |
| **料金** | 従量課金 (予測可能)、Managed PostgreSQL: $92.50/月 (2 vCPU, 4GB RAM, 50GB) |
| **利点** | - インフラのフルコントロール<br>- ベンダーロックインなし<br>- 接続プーリング、メモリ制限、ログへの直接アクセス可能 |
| **欠点** | - Auth、Realtime、Storage、APIは自前実装が必要<br>- DevOps負荷が高い (小規模チームには重い)<br>- セットアップに時間がかかる |

### Supabase

| 項目 | 詳細 |
|------|------|
| **タイプ** | Backend-as-a-Service (BaaS) on PostgreSQL |
| **特徴** | PostgreSQL + 統合サービス群 |
| **料金** | Free: $0 (50K MAUs, 500MB DB)<br>Pro: $25/月 ($10クレジット込み、実質$15/月)<br>Managed PostgreSQL: $60/月 (2 vCPU, 4GB RAM, 8GB) |
| **利点** | - **即座にプロダクション対応** (同日セットアップ可能)<br>- **Built-in Realtime** (WebSocket via PostgreSQL CDC)<br>- **Built-in Auth** (OAuth, Magic Link, JWT, Row Level Security)<br>- **Built-in Storage** (S3互換)<br>- **Edge Functions** (Deno/TypeScript、グローバル分散)<br>- **Auto-generated REST/GraphQL APIs**<br>- バックアップ、スケーリング、監視を自動管理<br>- オープンソース (Docker self-host可能) |
| **欠点** | - Supabase エコシステムへのロックイン<br>- Railway ほど細かい制御はできない<br>- 学習コストがある |

---

## 2. コスト比較 (2026年現在)

| 項目 | Railway | Supabase | 勝者 |
|------|---------|----------|------|
| **スタートアップ** | Free tier (小規模アプリ向け) | Free tier (50K MAUs, 500MB) | 🟢 Supabase (より寛大) |
| **Production (小規模)** | 従量課金 (~$92.50/月) | Pro: $25/月 (Micro compute込み) | 🟢 Supabase |
| **Managed PostgreSQL** | $92.50/月 (2 vCPU, 4GB, 50GB) | $60/月 (2 vCPU, 4GB, 8GB) | 🟢 Supabase |
| **Storage (1TB)** | $15/月 | $21/月 (1TB + 250GB R/W) | 🟢 Railway |
| **予測可能性** | 🟢 高い (従量課金だが明確) | 🟢 高い (固定料金 + compute) | 🟡 引き分け |

**Anicca の現状 (早期ユーザー段階) では Supabase の方がコスト効率が良い。**

---

## 3. 機能比較 (Plain PostgreSQL vs Supabase)

| 機能 | Plain PostgreSQL (Railway) | Supabase | インパクト |
|------|---------------------------|----------|-----------|
| **Realtime** | 要カスタム実装 (Logical Replication + WebSocket サーバー) | ✅ Built-in (WebSocket via CDC) | 🔴 **必須** (将来のロードマップ) |
| **Authentication** | 要カスタム実装 (JWT、OAuth、Row Level Security) | ✅ Built-in (全て統合済み) | 🟢 開発時間削減 |
| **Storage** | 要外部連携 (S3等) | ✅ Built-in (S3互換) | 🟡 便利だが必須ではない |
| **APIs** | 要手動実装 (PostgREST等) | ✅ Auto-generated (REST + GraphQL) | 🟢 開発速度向上 |
| **Edge Functions** | 要カスタム実装 | ✅ Built-in (Deno/TypeScript、global) | 🟡 今後必要になる可能性 |
| **Management** | 手動 (tuning、monitoring、backups) | ✅ Fully Managed | 🟢 DevOps負荷削減 |

---

## 4. 将来のロードマップとの適合性

| 機能 | 必要性 | Railway | Supabase | 評価 |
|------|--------|---------|----------|------|
| **Realtime Features** | 🔴 必須 (Phase 8+) | 要カスタム実装 (数週間) | ✅ Built-in | 🟢 Supabase 圧勝 |
| **User Simulation (RLVR)** | 🟡 必要 | データベース非依存 (compute層) | データベース非依存 (compute層) | 🟡 引き分け |
| **Reinforcement Learning** | 🟡 必要 | データベース非依存 | データベース非依存 | 🟡 引き分け |
| **Knowledge Graphs** | 🟡 検討中 | PostgreSQL拡張 (Apache AGE等) | PostgreSQL拡張 (Apache AGE等) | 🟡 引き分け |

**結論**: Realtime が決定的な差別化要因。RLVR/ML/知識グラフはコンピュート層の問題でデータベース選択に影響しない。

---

## 5. 移行のベストプラクティス

### 推奨移行手順 (Minimal Downtime)

| フェーズ | タスク | 期間 | リスク |
|---------|--------|------|--------|
| **Phase 1: 準備** | - Supabase プロジェクト作成<br>- スキーマ設計レビュー<br>- 環境変数セットアップ | 1日 | 低 |
| **Phase 2: スキーマ移行** | - `pg_dump` でスキーマをエクスポート<br>- Supabase にインポート<br>- 拡張機能の有効化 (pgvector等) | 1日 | 低 |
| **Phase 3: データ移行** | - Logical Replication または `pg_dump -j` でデータ転送<br>- データ検証 | 1-2日 | 中 |
| **Phase 4: API更新** | - Supabase Client SDK 導入<br>- API コードを Supabase SDK に切り替え<br>- ローカル/ステージングでテスト | 2-3日 | 中 |
| **Phase 5: デプロイ** | - Staging 環境でフル検証<br>- Production デプロイ<br>- モニタリング強化 | 1日 | 中 |

**合計期間**: 5-7日 (ソロ開発者)

### 移行リスク

| リスク | 影響 | 対策 |
|--------|------|------|
| ダウンタイム | 中 | Logical Replication でゼロダウンタイム移行 |
| データ損失 | 高 | 移行前に Railway の完全バックアップ取得 |
| API破損 | 中 | Staging で完全テスト、段階的ロールアウト |
| パフォーマンス劣化 | 低 | Supabase は同等以上のパフォーマンス |
| ベンダーロックイン | 中 | Supabase はオープンソース (self-host 可能) |

---

## 6. 決定根拠

### ✅ Supabase 移行を推奨する理由

| # | 理由 | 重要度 |
|---|------|--------|
| 1 | **Realtime が将来必須** - Railway で自前実装するより遥かに速い | 🔴 Critical |
| 2 | **Solo Developer** - DevOps 負荷削減 = 機能開発に集中可能 | 🔴 Critical |
| 3 | **コスト効率** - Pro プラン $25/月 vs Railway $92.50/月 | 🟢 High |
| 4 | **早期ステージ** - ユーザー数が少ない今が移行の最適タイミング | 🟢 High |
| 5 | **Supabase 残存コード** - 過去に検討済み、部分的統合が既に存在 | 🟡 Medium |
| 6 | **Auto-generated APIs** - 開発速度 2-3倍向上 | 🟡 Medium |
| 7 | **Built-in Auth** - RevenueCat と併用で完璧な認証フロー | 🟡 Medium |

### ❌ 移行しない場合のデメリット

| # | デメリット | インパクト |
|---|-----------|-----------|
| 1 | Realtime 機能を自前実装 (2-4週間の開発時間) | 🔴 Critical |
| 2 | DevOps 負荷が継続 (バックアップ、監視、スケーリング) | 🟢 High |
| 3 | Auth/Storage/API の統合コスト | 🟡 Medium |
| 4 | コストが高い ($92.50/月 vs $25/月) | 🟡 Medium |

---

## 7. 最終決定

### 🎯 決定: YES - Supabase へ移行する

**理由**:
1. **Realtime は Phase 8+ で必須機能** → Railway で自前実装するより Supabase の方が遥かに速い
2. **Solo Developer の時間が最も貴重** → DevOps 削減 = 機能開発に集中
3. **コスト削減** → $92.50/月 → $25/月 (約70%削減)
4. **早期ステージ** → 今が移行の最適タイミング (ユーザー数が少ない)
5. **既に Supabase 検討歴あり** → コードベースに残存、学習コスト低減

### 📅 移行タイミング: 今すぐ (Phase 7-8)

**なぜ今?**
- ユーザー数が少ない (移行リスクが低い)
- Phase 8 で Realtime が必要になる前に準備完了
- Revenue ステージだが、まだスケールしていない (最適なタイミング)

### 🔧 移行方法: 5フェーズ段階的アプローチ

```
Phase 1: Supabase セットアップ (1日)
    ↓
Phase 2: スキーマ移行 (1日)
    ↓
Phase 3: データ移行 + 検証 (1-2日)
    ↓
Phase 4: API 更新 + テスト (2-3日)
    ↓
Phase 5: Production デプロイ + モニタリング (1日)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
合計: 5-7日 (ソロ開発者ペース)
```

### ⚠️ 重要な注意点

1. **Railway を即座に削除しない** → 1-2週間並行運用してバックアップとして保持
2. **Staging 環境で完全テスト** → Production デプロイ前に全 API を検証
3. **ユーザーに通知** → メンテナンス予定をアナウンス (数時間のダウンタイム可能性)
4. **Rollback Plan** → 問題発生時は Railway に即座に戻せるように準備

---

## 8. 情報源

### プラットフォーム比較
- [PostgreSQL vs Supabase Comparison 2025](https://pgbench.com/comparisons/postgres-vs-supabase/) - 機能比較、ユースケース
- [Railway vs Supabase Backend Platforms](https://uibakery.io/blog/railway-vs-supabase) - 詳細比較 (2025年7月)
- [Railway vs Supabase Comparison](https://getdeploying.com/railway-vs-supabase) - 料金比較

### 移行ベストプラクティス
- [Migrate from Postgres to Supabase](https://supabase.com/docs/guides/platform/migrating-to-supabase/postgres) - 公式移行ガイド (2026年1月更新)
- [Seamless PostgreSQL Migration to Supabase](https://chat2db.ai/resources/blog/migrate-postgresql-database-to-supabase) - 詳細移行手順 (2025年7月)
- [Managing Database Migrations](https://dev.to/parth24072001/supabase-managing-database-migrations-across-multiple-environments-local-staging-production-4emg) - 環境別移行ワークフロー

### Supabase 機能詳細
- [Supabase Features Overview](https://supabase.com/features) - Realtime, Auth, Storage, Edge Functions
- [6 Best Managed PostgreSQL 2026](https://sqlflash.ai/article/20260114_aws-azure-gcp-supabase-postgresql-2026/) - 2026年マネージド PostgreSQL 比較
- [Supabase Realtime Documentation](https://github.com/supabase/realtime) - WebSocket/CDC 実装詳細

### コスト比較
- [Supabase Pricing 2026](https://supabase.com/pricing) - 最新料金 (2026年1月確認)
- [Railway vs Supabase Cost Comparison](https://getdeploying.com/railway-vs-supabase) - 詳細料金比較

### RLVR/機械学習
- [RLVR for SQL Reasoning](https://www.databricks.com/blog/power-rlvr-training-leading-sql-reasoning-model-databricks) - RLVR は LLM トレーニング技術 (データベース非依存)
- [RLVR-World Training](https://github.com/thuml/RLVR-World) - 強化学習アプリケーション (コンピュート層)

---

## 9. 次のアクション (実装計画)

### 📋 実装前の準備

| # | タスク | 担当 | 期限 |
|---|--------|------|------|
| 1 | Supabase アカウント作成 | ユーザー | 即座 |
| 2 | Railway データベースの完全バックアップ取得 | エージェント | Phase 1 開始前 |
| 3 | 現在のスキーマをドキュメント化 | エージェント | Phase 1 |
| 4 | 移行計画をユーザーに共有、承認取得 | エージェント | Phase 1 開始前 |

### 📝 Phase 1: セットアップ (Day 1)

```bash
# Supabase CLI インストール
brew install supabase/tap/supabase

# Supabase プロジェクト作成 (Web UI)
# https://app.supabase.com

# ローカル開発環境セットアップ
supabase init
supabase start
```

### 📝 Phase 2: スキーマ移行 (Day 1-2)

```bash
# Railway から スキーマ export
pg_dump $RAILWAY_DB_URL --schema-only > schema.sql

# Supabase にインポート
psql $SUPABASE_DB_URL < schema.sql

# 拡張機能の有効化 (必要に応じて)
# pgvector, pg_stat_statements 等
```

### 📝 Phase 3: データ移行 (Day 2-3)

```bash
# Option 1: pg_dump/restore (シンプル、小規模向け)
pg_dump $RAILWAY_DB_URL --data-only --jobs=4 > data.sql
psql $SUPABASE_DB_URL < data.sql

# Option 2: Logical Replication (ゼロダウンタイム、中規模向け)
# Supabase 公式ドキュメント参照
```

### 📝 Phase 4: API更新 (Day 3-5)

```typescript
// Supabase Client SDK インストール
npm install @supabase/supabase-js

// API コード更新例
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_ANON_KEY
)

// 既存の SQL クエリを Supabase クライアントに置き換え
```

### 📝 Phase 5: デプロイ (Day 6-7)

```bash
# Staging 環境でテスト
# - 全 API エンドポイント検証
# - iOS アプリとの統合テスト
# - パフォーマンステスト

# Production デプロイ
# - 環境変数更新
# - Railway → Supabase 切り替え
# - モニタリング強化 (Supabase Dashboard)

# Railway を 1-2週間バックアップとして保持
```

---

**調査完了日**: 2026年1月28日
**次回レビュー**: 移行 Phase 1 完了後
