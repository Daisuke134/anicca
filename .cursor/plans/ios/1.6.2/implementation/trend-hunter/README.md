# trend-hunter 設計書 — サブフォルダ構成

> **元ファイル**: `../trendposter.md`（1836行）を論理グループに分割
> **最終更新**: 2026-02-08

---

## ファイル一覧

| # | ファイル | 内容 | 行数 |
|---|---------|------|------|
| 1 | `01-overview-prerequisites.md` | ユーザー事前作業（BLOCKING） + 改訂の背景 | ~80 |
| 2 | `02-skill-queries.md` | SKILL.md改訂案 + データソース選定 + 13 ProblemTypeクエリ辞書 | ~120 |
| 3 | `03-processing-flow.md` | Step 1-4 全コード例（TikTok/Reddit/X/GitHub + LLMフィルタ + hook生成 + 重複チェック&保存） | ~360 |
| 4 | `04-config-integration.md` | Required Tools + Error Handling + Cron設定 + 環境変数 + コスト見積もり + ClawHub流用 + x-poster連携 | ~110 |
| 5 | `05-examples-research.md` | 共感系 vs 問題解決系の具体例 + ClawHubスキル精査 + X/TikTokデータ取得調査結果 | ~110 |
| 6 | `06-test-matrix.md` | テスト可能なコード境界（14モジュール定義） + テストマトリックス（#1〜#40） | ~170 |
| 7 | `07-mock-data-validation.md` | モックAPIレスポンス（5ソース） + LLM出力バリデーション（JSON Schema） + 重複判定アルゴリズム（Jaccard） + 未解決項目 | ~390 |
| 8 | `08-acceptance-boundaries.md` | 受け入れ条件（AC-1〜AC-10） + 境界（B-1〜B-10） + E2E判定（不要） | ~70 |
| 9 | `09-skill-deploy.md` | スキルファイル構成（SKILL.mdのみ） + デプロイ手順 + テスト手順 | ~80 |
| 10 | `10-thompson-sampling.md` | Thompson Sampling v2（Beta分布 + ウォームスタート + 月次減衰） + テスト #41〜#49 | ~145 |
| 11 | `11-dlq-checklist.md` | DLQリトライロジック（指数バックオフ+ジッター） + テスト #50〜#63 + Spec完了チェックリスト | ~245 |

**合計テスト数**: 63（Pure 33 + 統合 7 + TS 9 + DLQ 14）

---

## 読む順序

### パターン A: 全体概要（初見エージェント向け）

| 順番 | ファイル | 読む範囲 | 所要時間 |
|------|---------|---------|---------|
| 1 | `01-overview-prerequisites.md` | 全体 | 2分 |
| 2 | `02-skill-queries.md` | データソーステーブル + クエリ辞書 | 3分 |
| 3 | `08-acceptance-boundaries.md` | 受け入れ条件 + 境界 | 2分 |
| 4 | `11-dlq-checklist.md` | Spec完了チェックリスト（末尾） | 1分 |

### パターン B: 特定コンポーネント実装

| やりたいこと | 読むファイル |
|-------------|------------|
| スキル実装を始める | `01` → `09-skill-deploy.md`（デプロイ手順） |
| 検索クエリを調整 | `02-skill-queries.md`（クエリ辞書セクション） |
| API呼び出しコードを書く | `03-processing-flow.md`（Step 1a-1d） |
| LLMプロンプトを調整 | `03-processing-flow.md`（Step 2-3） |
| Cron設定・環境変数 | `04-config-integration.md` |
| テストを書く | `06-test-matrix.md` → `07-mock-data-validation.md`（モックデータ） |
| Thompson Sampling実装 | `10-thompson-sampling.md` |
| DLQ実装 | `11-dlq-checklist.md` |

### パターン C: TDDで実装

| ステップ | 参照先 |
|---------|-------|
| 1. テストマトリックス確認 | `06-test-matrix.md`（#1〜#40） |
| 2. モックデータ準備 | `07-mock-data-validation.md`（5ソース分のJSON） |
| 3. RED: テスト作成 | テスト名・入力・期待出力がマトリックスに記載済み |
| 4. GREEN: 実装 | `03-processing-flow.md` のコード例を参考に |
| 5. 追加テスト（TS + DLQ） | `10-thompson-sampling.md`（#41-49）+ `11-dlq-checklist.md`（#50-63） |
| 6. 受け入れ条件確認 | `08-acceptance-boundaries.md`（AC-1〜AC-10） |

---

## 関係図

```
01-overview-prerequisites ──(BLOCKING)──→ 実装開始
                                            │
                                            ▼
02-skill-queries ──→ 03-processing-flow ──→ 04-config-integration
 (何を検索するか)     (どう処理するか)       (どう動かすか)
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
    05-examples    10-thompson    11-dlq-checklist
    (参考例)       (v2学習)       (エラー回復)
                          │
                          ▼
              09-skill-deploy ←── 08-acceptance-boundaries
              (デプロイ)          (完了基準)
                          │
                          ▼
              06-test-matrix ←── 07-mock-data-validation
              (テスト設計)       (テストデータ)
```

---

## 元ファイルとの関係

`../trendposter.md` は分割元のマスターファイルとして残す（アーカイブ）。
実装時はこのサブフォルダ内のファイルを参照する。

## 他ドキュメントとの関係

| ドキュメント | trend-hunter との関係 |
|-------------|---------------------|
| `../closed-loop-ops/` | trend-hunterの出力が `ops_events` → トリガー → 他スキル起動 |
| `../1.6.2-ultimate-spec.md` | Phase 3 (3.2) で trend-hunter が定義。hookSelector (Thompson Sampling) との連携 |
| `../1.6.2-ultimate-spec2.md` | trend-hunter の概要のみ。**このフォルダが完全版** |
