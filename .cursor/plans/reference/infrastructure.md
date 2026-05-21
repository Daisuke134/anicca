# インフラストラクチャ（Cron / Railway / GHA）

## Cron ジョブ アーキテクチャ

### 現在の構成

| ジョブ | 実行環境 | スケジュール | 仕組み |
|--------|---------|-------------|--------|
| Nudge生成 | Railway Cron | `0 20 * * *` (5:00 JST) | `CRON_MODE=nudges` → `generateNudges.js` 直接実行 |
| Type Stats集計 | Railway Cron | `0 21 * * *` (6:00 JST) | `CRON_MODE=aggregate_type_stats` → 直接実行 |
| TikTok投稿 | GitHub Actions | `0 0 * * *` (9:00 JST) | Python エージェント |
| TikTokメトリクス | GitHub Actions | `0 1 * * *` (10:00 JST) | Python スクリプト |
| **Daily Metrics Report** | GitHub Actions | `15 20 * * *` (5:15 JST) | Python: ASC + RevenueCat → Slack #agents |

### なぜ分離されているか

| 比較 | Railway Cron | GitHub Actions |
|------|-------------|----------------|
| 言語 | Node.js | Python |
| DB | 直接接続 | API経由 |
| コスト | Railwayプランに含む | 無料 |
| 用途 | ユーザー向け機能 | マーケティング自動化 |

**ベストプラクティス**: 言語・依存関係・責務が異なるものは分離する（Separation of Concerns）。

### スケーラビリティ

| ユーザー数 | Nudge生成時間 | 対応 |
|-----------|-------------|------|
| 10-50 | 2-12分 | 現状のfor-loopで十分 |
| 100+ | 25分+ | BullMQ + Redis に移行 |
| 500+ | 要改善 | On-Demand生成 + キャッシュ |

---

## 1.5.0 で学んだ教訓

### FK制約エラー（P2003）の防止

**Prisma upsert で FK 先のレコードが存在しない場合、P2003 エラーでクラッシュする。**

| ルール | 詳細 |
|--------|------|
| FK依存 upsert の前に存在チェック | `findUnique({ where: { id }, select: { id: true } })` |
| 存在しない場合 | warn ログを出して早期 return（throw しない） |
| 該当箇所 | `userTypeService.js:classifyAndSave()`, `profileService` 等 |

```javascript
// 必須パターン: FK依存 upsert の前
const exists = await prisma.targetTable.findUnique({ where: { id }, select: { id: true } });
if (!exists) {
  logger.warn(`Record not found, skipping FK-dependent operation`);
  return;
}
await prisma.dependentTable.upsert({ ... });
```

### 環境変数のフォールバック

**Railway 環境変数が未設定でコンテナがクラッシュするのを防ぐ。**

| ルール | 詳細 |
|--------|------|
| `PROXY_BASE_URL` | `RAILWAY_PUBLIC_DOMAIN` から自動生成可能 |
| throw 前にフォールバック | 自動復旧できるものは throw しない |
| 新しい必須変数追加時 | Railway Dashboard で設定 + コードにフォールバック |

### GitHub Actions デバッグ手順

| # | 手順 | コマンド |
|---|------|---------|
| 1 | Secret 一覧確認 | `gh secret list -R Daisuke134/anicca.ai` |
| 2 | **URL が正しいか確認** | `anicca-proxy-production`（`anicca-api-production` ではない） |
| 3 | 手動実行 | `gh workflow run "Name" --ref dev` |
| 4 | 結果確認 | `gh run list --workflow "Name" -L 3` |

### Prisma マイグレーション（既存DB）

| ステップ | コマンド |
|---------|---------|
| 1. baseline 適用 | `DATABASE_URL="..." npx prisma migrate resolve --applied <migration_name>` |
| 2. 残りを deploy | `DATABASE_URL="..." npx prisma migrate deploy` |
| 3. **main に push** | Railway は push で自動デプロイ。DB変更だけでは再デプロイされない |

### Railway 運用ルール

| ルール | 理由 |
|--------|------|
| main push = 自動デプロイ | DB変更後も push が必要 |
| env var 変更 = 自動再起動 | `railway variables --set` で即反映 |
| 内部URL vs Proxy URL | 内部は Railway 内のみ。外部アクセスは Proxy URL |
| DB資格情報は `.env.proxy` に保存 | 毎回ユーザーに聞かない |

---

## Railway サービス名・URL

### サービス名

| 環境 | API | Cron |
|------|-----|------|
| **Staging** | `API` | `nudge-cron` |
| **Production** | `API` | `nudge-cronp`（末尾に`p`） |

### 環境変数

| 変数 | API (Staging/Prod) | nudge-cron (Staging) | nudge-cronp (Prod) |
|------|-------------------|---------------------|-------------------|
| `CRON_MODE` | なし | `nudges` | `nudges` |
| `PROXY_BASE_URL` | あり | なし | なし |
| `DATABASE_URL` | あり | あり（internal） | あり（internal） |
| `OPENAI_API_KEY` | あり | あり | あり |
| `ANTHROPIC_API_KEY` | あり | なし | なし |

**`CRON_MODE`** は truthy チェック（`!!process.env.CRON_MODE`）。

### URL

| 環境 | URL |
|------|-----|
| Staging | `anicca-proxy-staging.up.railway.app` |
| Production | `anicca-proxy-production.up.railway.app` |

**注意:** `anicca-api-production` ではない。`anicca-proxy-production` が正しいURL。

### GHA + Railway 並行テストのフロー

```
1. dev でコード修正
2. dev → main マージ & push（Railway 自動デプロイ）
3. Railway デプロイ完了待ち（2-3分）
4. GHA workflow 手動実行で検証
5. 両方 SUCCESS で完了
```
