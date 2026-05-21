# Daily Metrics Report（自動化済み）

## 概要

ASC + RevenueCat のメトリクスを毎日自動取得し、Slack #agents に投稿する。

| 項目 | 値 |
|------|-----|
| **ワークフロー** | `.github/workflows/daily-metrics.yml` |
| **スクリプト** | `scripts/daily-metrics/` |
| **スケジュール** | 毎日 5:15 JST（`15 20 * * *` UTC） |
| **送信先** | Slack #agents チャンネル |
| **GitHub Secrets** | 全て設定済み（上記テーブル参照） |
| **手動実行** | `gh workflow run "Daily Metrics Report" --repo Daisuke134/anicca.ai` |

## 取得メトリクス

| ソース | メトリクス | 注意事項 |
|--------|-----------|---------|
| ASC Sales Reports | 新規DL数（7日間）、国別内訳 | **type 1のみ**（更新/IAPは除外）、**2日前データ**使用 |
| ASC Analytics Reports | Impressions, Page Views | ONGOINGレポート作成済み。初回は1-2日後からデータ取得可能 |
| RevenueCat v2 | MRR, Active Subs, Active Trials, Trial→Paid, Churn | `id`フィールドで取得（`name`ではない）、値はドル（セントではない） |

## ASC API Key 情報

| 項目 | 値 |
|------|-----|
| **使用するキー** | `D637C7RGFN`（Fastlane と同じキー） |
| **p8ファイル** | `~/Downloads/AuthKey_D637C7RGFN.p8` |
| **Issuer ID** | GitHub Secret `ASC_ISSUER_ID` に設定済み |
| **Vendor Number** | `93486075` |
| **バンドルID** | `ai.anicca.app.ios`（`com.anicca.ios` ではない） |
| **App ID** | `6755129214` |

## 重要な注意（過去のバグから学んだ教訓）

| 教訓 | 詳細 |
|------|------|
| **Sales Reports は gzip 圧縮** | `gzip.decompress(resp.content)` が必要 |
| **Product Type フィルター必須** | type `1` = 新規DL、`7` = アップデート、`3` = IAP。フィルターなしだとDL数が過大 |
| **ASCデータは2日遅れ** | `today - 2` を使う。昨日のデータは不完全 |
| **RevenueCat は `id` フィールド** | `name` ではない（例: `id: "mrr"`, `name: "MRR"`） |
| **RevenueCat MRR はドル単位** | 100で割らない |
| **p8キーは`D637C7RGFN`** | `646Y27MJ8C` は古い/無効なキー |
| **テスト時は `gh workflow run`** | ローカルにRC/Slack秘密鍵がないため、GitHub Actions経由で実行 |

## 目標KPI

| KPI | 目標 | 現状（2026/1/27時点） |
|-----|------|---------------------|
| **日次DL** | 10/日 | 1.7/日 |
| **CVR (Page View → DL)** | 3% | 0.3% |
| **MRR** | - | $17 |
| **Active Subs** | - | 2 |
