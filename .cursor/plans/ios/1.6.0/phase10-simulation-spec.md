# Phase 10: シミュレーション基盤

> **バージョン**: 1.6.0
>
> **最終更新**: 2026-01-26
>
> **前提**: 1.5.0（クロスユーザー学習 + TikTok投稿）完了後
>
> **状態**: レビュー中

---

## 開発環境

| 項目 | 値 |
|------|-----|
| **ワークツリーパス** | `/Users/cbns03/Downloads/anicca-project`（メインリポジトリ） |
| **ブランチ** | `dev` |
| **ベースブランチ** | `dev` |
| **作業状態** | Spec作成中 |

| 注記 | 内容 |
|------|------|
| 並列作業時 | 必要に応じてWorktreeを作成（例: `/Users/cbns03/Downloads/anicca-phase10`） |

---

## 1. 概要

### 1.1 What（何をするか）

| 項目 | 内容 |
|------|------|
| 概要 | シミュレーション基盤を構築し、ペルソナベースのNudge効果予測とTikTokマーケティングデータの自動収集を実現する |

### 1.2 Why（なぜ必要か）

| 課題 | 解決策 |
|------|--------|
| Nudge効果の事前検証ができない | ペルソナ×Nudgeのシミュレーションで事前予測 |
| TikTokデータの手動収集は非効率 | Marketing API連携で日次自動収集 |
| ユーザーセグメントの理解が曖昧 | 5-8個のコアペルソナで明確化 |

---

## 2. スコープ

### 2.1 1.6.0でやること

| 機能 | 詳細 |
|------|------|
| DBスキーマ作成 | ペルソナ、シミュ結果、TikTokメトリクス用テーブル |
| ペルソナ生成 | 8個のコアペルソナをDBに登録 |
| EDSLシミュレーション | ペルソナ×Nudge候補のシミュレーション実行 |
| TikTokデータ自動収集 | Marketing APIで日次メトリクス取得 |
| Appフィードバック集計 | 日次でnudge_feedbackを集計 |

### 2.2 1.6.0でやらないこと（境界）

| 機能 | 理由 | 予定バージョン |
|------|------|---------------|
| 校正ループ | シミュ予測 vs 実データ比較は基盤完成後 | 1.7.0 |
| Wisdom抽出 | LLMでの自然言語抽出は次フェーズ | 1.7.0 |
| Wisdom適用 | Nudge生成時の参照は次フェーズ | 1.7.0 |
| admin/jobs IP制限 | Cloudflare Access設定は運用整備後 | 1.7.0 |
| admin/jobs レート制限 | 基本認証で1.6.0は十分 | 1.7.0 |
| admin/jobs 認証失敗アラート | 運用監視整備後 | 1.7.0 |
| job_runs詳細履歴 | 再実行回数・履歴は次フェーズ | 1.7.0 |

| 注記 | 内容 |
|------|------|
| Wisdomテーブル | 1.6.0でスキーマ作成（マイグレーション実施）、機能実装は1.7.0。1.7.0での追加マイグレーション不要 |

### 2.3 触るファイル

| パス | 変更種別 |
|------|---------|
| `apps/api/supabase/migrations/` | 新規追加 |
| `apps/api/src/seeds/personas.ts` | 新規追加 |
| `apps/api/src/services/tiktokDataCollector.ts` | 新規追加 |
| `apps/api/src/simulation/edsl_runner.py` | 新規追加 |
| `apps/api/src/jobs/simulationJob.ts` | 新規追加 |
| `apps/api/src/jobs/scheduled.ts` | 修正（Cronジョブ追加、単一実行保証） |
| `apps/api/src/simulation/nudge_candidates.json` | 新規追加 |
| `apps/api/src/services/notificationService.ts` | 修正（Slack通知追加） |
| `apps/api/src/routes/admin/jobs.ts` | 新規追加（手動再実行API） |
| `apps/api/src/__tests__/fixtures/tiktok/` | 新規追加（モック） |
| `apps/api/src/__tests__/fixtures/edsl/` | 新規追加（モック） |
| `apps/api/Dockerfile` | 修正（Python追加） |
| `apps/api/requirements.txt` | 新規追加 |

### 2.4 触らないファイル

| パス | 理由 |
|------|------|
| `aniccaios/` | iOS側の変更なし |
| `apps/api/src/routes/mobile/` | 既存APIに変更なし |
| `apps/landing/` | ランディングページに変更なし |

---

## 3. 後方互換性

### 3.1 既存APIへの影響

| 項目 | 影響 |
|------|------|
| 既存エンドポイント | **変更なし** |
| 既存レスポンス形式 | **変更なし** |
| 既存必須パラメータ | **変更なし** |
| 既存テーブル | **変更なし**（新規テーブル追加のみ） |

### 3.2 マイグレーション方針

| 方針 | 詳細 |
|------|------|
| 追加のみ | 新規テーブル・インデックスの追加 |
| 削除なし | 既存テーブル・カラムの削除なし |
| 変更なし | 既存カラムの型変更なし |

### 3.3 古いバージョンのアプリへの影響

| 項目 | 影響 |
|------|------|
| iOSアプリとの通信 | **変更なし** |
| 理由 | バックエンド内部の機能追加のみ |

---

## 4. As-Is（現状）

### 4.1 現在のデータ収集

| データ | 収集方法 | 問題 |
|--------|---------|------|
| TikTokメトリクス | 手動でAds Managerから確認 | 非効率、漏れあり |
| Nudgeフィードバック | `nudge_feedback`テーブルに保存 | 集計・分析なし |
| ユーザーセグメント | ProblemTypeで分類 | 詳細なペルソナなし |

### 4.2 現在のNudge効果検証

| 項目 | 状況 |
|------|------|
| 事前検証 | なし（本番でA/Bテストのみ） |
| 効果予測 | 経験則のみ |
| データドリブン | 不十分 |

---

## 5. To-Be（変更後）

### 5.1 DBスキーマ

#### UUID生成方式（共通）

| 項目 | 内容 |
|------|------|
| 生成方式 | `gen_random_uuid()` |
| 拡張機能 | `pgcrypto`（Supabaseでデフォルト有効） |
| DEFAULT設定 | 全UUID PKに`DEFAULT gen_random_uuid()`を設定 |
| INSERT時 | UUIDを省略可能（自動生成される） |

| マイグレーション方針 | 内容 |
|-------------------|------|
| 拡張確認 | `CREATE EXTENSION IF NOT EXISTS pgcrypto;` をマイグレーション冒頭に追加 |
| Supabase対応 | Supabaseではデフォルト有効のため追加は冪等 |

#### simulated_personas テーブル

| カラム | 型 | 説明 | 制約 |
|--------|-----|------|------|
| id | UUID | 主キー | PRIMARY KEY, DEFAULT gen_random_uuid() |
| name | TEXT | ペルソナ名 | NOT NULL |
| problem_types | TEXT[] | 関連するProblemType配列 | NOT NULL |
| attributes | JSONB | 年齢、ライフスタイル、活動時間 | |
| psychological_profile | JSONB | コアペイン、防衛機制等 | |
| behavior_hypotheses | JSONB | 好みのトーン、効果的なHook等 | |
| created_at | TIMESTAMPTZ | 作成日時 | DEFAULT NOW() |

#### simulation_runs テーブル

| カラム | 型 | 説明 | 制約 |
|--------|-----|------|------|
| id | UUID | 主キー | PRIMARY KEY, DEFAULT gen_random_uuid() |
| job_run_id | UUID | ジョブ実行FK | NOT NULL, REFERENCES job_runs(id) ON DELETE CASCADE |
| persona_id | UUID | ペルソナFK | NOT NULL, REFERENCES simulated_personas(id) ON DELETE RESTRICT |
| nudge_config_hash | TEXT | Nudge設定のハッシュ（重複判定用） | NOT NULL |
| nudge_config | JSONB | Nudge設定（hook, content, tone等） | NOT NULL |
| predictions | JSONB | 予測結果（下記JSON構造参照） | NOT NULL |
| created_at | TIMESTAMPTZ | 作成日時 | DEFAULT NOW() |
| - | - | **一意制約** | **UNIQUE(job_run_id, persona_id, nudge_config_hash)** |

| simulation_runs再開性設計 | 内容 |
|--------------------------|------|
| 目的 | 週次シミュレーション中断時の再開、重複実行防止 |
| 識別方法 | job_run_id + persona_id + nudge_config_hash で一意識別 |
| 再開条件 | 同一job_run_idで未処理のペルソナ×Nudge組み合わせから再開 |
| 重複防止 | UNIQUE制約によりINSERT時に重複をブロック |

| nudge_config_hash仕様 | 内容 |
|---------------------|------|
| 計算箇所 | **Node.js側のみ**（SimulationJob内で計算） |
| ハッシュ関数 | SHA-256、先頭16文字（64bit） |
| 計算対象 | nudge_config JSONの正規化文字列 |

| nudge_config正規化ルール | 内容 |
|-----------------------|------|
| キー順 | **辞書順（alphabetical）**でソート |
| 配列順 | **元の順序を維持**（ソートしない） |
| 数値型 | 数値のまま（文字列化しない） |
| 文字列型 | 文字列のまま |
| null値 | JSON nullとして含める |
| undefined | キーごと除外 |
| 空文字列 | `""`として含める |

| 正規化実装例（Node.js） | 内容 |
|---------------------|------|
| ライブラリ | `json-stable-stringify`（キー順ソート済みJSON生成） |
| コード例 | `const hash = crypto.createHash('sha256').update(stableStringify(nudgeConfig)).digest('hex').slice(0, 16)` |

| ハッシュ一貫性テスト | 内容 |
|-------------------|------|
| テスト名 | `test_nudge_config_hash_deterministic` |
| 検証内容 | 同一入力→同一ハッシュ、キー順入れ替え→同一ハッシュ |

| UPSERT方針 | 内容 |
|-----------|------|
| INSERT | 通常は INSERT（新規シミュレーション結果） |
| 重複時 | ON CONFLICT DO NOTHING（既存結果を上書きしない） |
| 再実行時 | **同一job_run_idを再利用**（下記参照） |

| 再実行時の動作 | 内容 |
|--------------|------|
| job_runs | 既存レコードをUPDATE（status=running）、**job_run_idは変わらない** |
| simulation_runs | 同一(job_run_id, persona_id, nudge_config_hash)は ON CONFLICT DO NOTHING でスキップ |
| 効果 | 中断後の再実行で、完了済みシミュレーションを再処理せず未処理分のみ実行（再開性） |

| predictions JSON構造 | 型 | 説明 |
|---------------------|-----|------|
| tap_rate | number | タップ率予測（0-1） |
| thumbs_up_rate | number | 👍率予測（0-1） |
| thumbs_down_rate | number | 👎率予測（0-1） |
| confidence | number | 予測信頼度（0-1） |
| reasoning | string | EDSLの推論説明（LLM出力） |
| model_version | string | 使用LLMモデル名（例: "gpt-4o-mini"） |

| predictions JSON例 | 値 |
|-------------------|-----|
| tap_rate | 0.35 |
| thumbs_up_rate | 0.72 |
| thumbs_down_rate | 0.08 |
| confidence | 0.85 |
| reasoning | "このペルソナは夜更かし傾向があり、gentleトーンに好反応する傾向..." |
| model_version | "gpt-4o-mini" |

#### tiktok_ad_metrics テーブル

| カラム | 型 | 説明 | 制約 |
|--------|-----|------|------|
| id | UUID | 主キー | PRIMARY KEY, DEFAULT gen_random_uuid() |
| ad_id | TEXT | TikTok広告ID | NOT NULL |
| impressions | INT | インプレッション数 | |
| clicks | INT | クリック数 | |
| ctr | DECIMAL(5,4) | クリック率 | |
| spend | DECIMAL(10,2) | 消費金額 | |
| video_views | INT | 動画視聴数 | |
| engagement_rate | DECIMAL(5,4) | エンゲージメント率 | |
| date | DATE | 日付 | NOT NULL |
| created_at | TIMESTAMPTZ | 作成日時 | DEFAULT NOW() |
| - | - | **一意制約** | **UNIQUE(ad_id, date)** |

#### ad_persona_mapping テーブル

| カラム | 型 | 説明 | 制約 |
|--------|-----|------|------|
| id | UUID | 主キー | PRIMARY KEY, DEFAULT gen_random_uuid() |
| ad_id | TEXT | TikTok広告ID | NOT NULL |
| persona_id | UUID | ペルソナFK | NOT NULL, REFERENCES simulated_personas(id) ON DELETE RESTRICT |
| hook | TEXT | 広告で使ったHook | |
| content | TEXT | 広告で使ったContent | |
| tone | TEXT | 広告のトーン | |
| created_at | TIMESTAMPTZ | 作成日時 | DEFAULT NOW() |

#### wisdom テーブル（1.7.0で使用）

| カラム | 型 | 説明 | 制約 |
|--------|-----|------|------|
| id | UUID | 主キー | PRIMARY KEY, DEFAULT gen_random_uuid() |
| persona_id | UUID | ペルソナFK | NOT NULL, REFERENCES simulated_personas(id) ON DELETE CASCADE |
| category | TEXT | tone/timing/content/hook | NOT NULL, CHECK (category IN ('tone', 'timing', 'content', 'hook')) |
| principle | TEXT | 抽出された原則 | NOT NULL |
| confidence | DECIMAL(3,2) | 信頼度（0-1） | DEFAULT 0.50 |
| evidence_count | INT | エビデンス件数 | DEFAULT 0 |
| created_at | TIMESTAMPTZ | 作成日時 | DEFAULT NOW() |
| - | - | **一意制約** | **UNIQUE(persona_id, category, principle)** |

#### daily_feedback_summary テーブル

| カラム | 型 | 説明 | 制約 |
|--------|-----|------|------|
| id | UUID | 主キー | PRIMARY KEY, DEFAULT gen_random_uuid() |
| date | DATE | 集計日 | NOT NULL |
| problem_type | TEXT | 問題タイプ | NOT NULL |
| total_delivered | INT | 配信数 | DEFAULT 0 |
| total_opened | INT | 開封数 | DEFAULT 0 |
| thumbs_up_count | INT | 👍数 | DEFAULT 0 |
| thumbs_down_count | INT | 👎数 | DEFAULT 0 |
| created_at | TIMESTAMPTZ | 作成日時 | DEFAULT NOW() |
| - | - | **一意制約** | **UNIQUE(date, problem_type)** |

| 注記 | 内容 |
|------|------|
| 集計元 | 既存の`nudge_feedback`テーブルを日次集計 |
| 実行ジョブ | `daily_feedback_aggregate`が毎日06:30 UTCに実行 |

| UPSERT方針 | 内容 |
|-----------|------|
| 通常実行 | INSERT（新規集計レコード） |
| 再実行時 | ON CONFLICT (date, problem_type) DO UPDATE |
| UPDATE対象 | total_delivered, total_opened, thumbs_up_count, thumbs_down_count |
| 理由 | 手動再実行時は最新の集計結果で上書き（データ修正対応） |

| UPSERT SQL例 | 内容 |
|-------------|------|
| クエリ | `INSERT INTO daily_feedback_summary (id, date, problem_type, total_delivered, total_opened, thumbs_up_count, thumbs_down_count) VALUES (...) ON CONFLICT (date, problem_type) DO UPDATE SET total_delivered = EXCLUDED.total_delivered, total_opened = EXCLUDED.total_opened, thumbs_up_count = EXCLUDED.thumbs_up_count, thumbs_down_count = EXCLUDED.thumbs_down_count` |

| 集計ロジック | 内容 |
|-------------|------|
| 集計対象期間 | 前日00:00:00 UTC 〜 23:59:59 UTC |
| タイムゾーン | UTC（DBもAPIもUTC統一） |

| 集計カラムマッピング | nudge_feedbackカラム | 集計方法 |
|--------------------|---------------------|---------|
| total_delivered | id (COUNT) | WHERE created_at >= :start AND created_at < :end AND problem_type = :type |
| total_opened | opened_at IS NOT NULL | COUNT WHERE opened_at IS NOT NULL |
| thumbs_up_count | feedback = 'thumbs_up' | COUNT |
| thumbs_down_count | feedback = 'thumbs_down' | COUNT |

| nudge_feedback参照カラム | 説明 |
|-----------------------|------|
| created_at | 集計期間の判定に使用（TIMESTAMPTZ） |
| problem_type | グループ化キー（TEXT） |
| opened_at | 開封判定（TIMESTAMPTZ、NULLなら未開封） |
| feedback | thumbs_up/thumbs_down/null |

| 集計SQL例 | 内容 |
|----------|------|
| クエリ | `SELECT problem_type, COUNT(*) as delivered, COUNT(opened_at) as opened, SUM(CASE WHEN feedback='thumbs_up' THEN 1 ELSE 0 END) as thumbs_up, SUM(CASE WHEN feedback='thumbs_down' THEN 1 ELSE 0 END) as thumbs_down FROM nudge_feedback WHERE created_at >= :start AND created_at < :end GROUP BY problem_type` |

#### job_runs テーブル

| カラム | 型 | 説明 | 制約 |
|--------|-----|------|------|
| id | UUID | 主キー | PRIMARY KEY, DEFAULT gen_random_uuid() |
| job_name | TEXT | ジョブ名 | NOT NULL |
| scheduled_date | DATE | 実行予定日 | NOT NULL |
| status | TEXT | 状態 | NOT NULL, CHECK (status IN ('running', 'completed', 'failed')) |
| started_at | TIMESTAMPTZ | 開始時刻 | |
| completed_at | TIMESTAMPTZ | 完了時刻 | |
| error_message | TEXT | エラーメッセージ | |
| created_at | TIMESTAMPTZ | 作成日時 | DEFAULT NOW() |
| - | - | **一意制約** | **UNIQUE(job_name, scheduled_date)** |

| 注記 | 内容 |
|------|------|
| 目的 | Cronジョブの単一実行保証（冪等性） |
| ジョブ名例 | daily_tiktok_collect, daily_feedback_aggregate, weekly_simulation |

| scheduled_date定義 | ジョブ名 | 意味 | 例（2026-01-27 06:00 UTC実行時） |
|-------------------|---------|------|--------------------------------|
| daily_tiktok_collect | 対象データ日（前日UTC） | 2026-01-26 |
| daily_feedback_aggregate | 対象データ日（前日UTC） | 2026-01-26 |
| weekly_simulation | 実行日（当日UTC） | 2026-01-27 |

| scheduled_date運用ルール | 内容 |
|------------------------|------|
| 日次ジョブ | 取得するデータの日付（前日UTC）を指定 |
| 週次ジョブ | 実行日（当日UTC）を指定 |
| 手動再実行 | 同じscheduled_dateを指定して再実行 |
| 冪等性 | 同一(job_name, scheduled_date)は1回のみ正常実行 |

#### system_settings テーブル

| カラム | 型 | 説明 | 制約 |
|--------|-----|------|------|
| key | TEXT | 設定キー | PRIMARY KEY |
| value | JSONB | 設定値 | NOT NULL |
| updated_at | TIMESTAMPTZ | 更新日時 | DEFAULT NOW() |

| 初期データ | key | value | 説明 |
|-----------|-----|-------|------|
| Cron停止フラグ | tiktok_cron_disabled | `false` | boolean型、true=停止 |
| 401連続回数 | tiktok_401_count | `0` | 数値型、3以上で停止 |

| 初期データ投入方法 | 内容 |
|------------------|------|
| 方式 | マイグレーションファイル内でINSERT |
| タイミング | テーブル作成と同一マイグレーション |
| 冪等性 | ON CONFLICT DO NOTHINGで重複回避 |

| 初期データSQL | 内容 |
|--------------|------|
| INSERT INTO system_settings (key, value) | VALUES ('tiktok_cron_disabled', 'false'::jsonb) ON CONFLICT DO NOTHING |
| INSERT INTO system_settings (key, value) | VALUES ('tiktok_401_count', '0'::jsonb) ON CONFLICT DO NOTHING |

#### インデックス

| テーブル | インデックス | 目的 |
|---------|-------------|------|
| simulation_runs | idx_simulation_runs_job_run | ジョブ実行別検索（再開処理用） |
| simulation_runs | idx_simulation_runs_persona | ペルソナ別検索 |
| tiktok_ad_metrics | idx_tiktok_metrics_date | 日付別検索 |
| tiktok_ad_metrics | idx_tiktok_metrics_ad_date | upsert用 |
| ad_persona_mapping | idx_ad_persona_mapping_ad_id | 広告ID別検索 |
| ad_persona_mapping | idx_ad_persona_mapping_persona | ペルソナ別検索 |
| wisdom | idx_wisdom_persona | ペルソナ別検索 |
| wisdom | idx_wisdom_confidence | 信頼度順検索 |
| daily_feedback_summary | idx_daily_feedback_date | 日付別検索 |
| daily_feedback_summary | idx_daily_feedback_problem | 問題タイプ別検索 |
| job_runs | idx_job_runs_name_date | ジョブ名＋日付検索 |
| job_runs | idx_job_runs_status | 状態別検索 |

### 5.2 サービス設計

#### TikTokDataCollector

| 項目 | 内容 |
|------|------|
| 責務 | TikTok Marketing APIからメトリクスを取得しDBに保存 |
| 入力 | 環境変数（TIKTOK_ACCESS_TOKEN等） |
| 出力 | tiktok_ad_metricsテーブルへのupsert |
| エラー処理 | API失敗時はSlack通知、exponential backoff（max 3回） |
| レート制限 | 10リクエスト/秒、1日10,000リクエスト（TikTok公式仕様） |
| upsert条件 | ON CONFLICT (ad_id, date) DO UPDATE |

#### TikTok API仕様（詳細）

| 項目 | 内容 |
|------|------|
| エンドポイント | `GET /report/integrated/get/` (Reporting API v1.3) |
| ベースURL | `https://business-api.tiktok.com/open_api/v1.3` |
| 認証 | `Access-Token: ${TIKTOK_ACCESS_TOKEN}` ヘッダー |

| リクエストパラメータ | 型 | 値 |
|--------------------|-----|-----|
| advertiser_id | string | `${TIKTOK_ADVERTISER_ID}` |
| report_type | string | `BASIC` |
| dimensions | string[] | `["ad_id"]` |
| data_level | string | `AUCTION_AD` |
| start_date | string | 前日UTC（例: "2026-01-25"） |
| end_date | string | 前日UTC（例: "2026-01-25"） |
| metrics | string[] | `["impressions", "clicks", "spend", "video_views_p100", "engagement_rate"]` |
| page_size | int | 100 |

| 取得対象日 | 内容 |
|-----------|------|
| 日次取得 | 前日UTC 00:00:00 〜 23:59:59 のデータ |
| 算出方法 | `dayjs().utc().subtract(1, 'day').format('YYYY-MM-DD')` |
| 理由 | TikTok APIは当日データが不完全なため前日を取得 |

| ad_id取得方法 | 内容 |
|--------------|------|
| 方式 | **メトリクスがある広告のみ対象**（Reporting APIは配信実績0の広告を返さない） |
| スコープ | 指定期間内にimpressions > 0 の広告のみ取得 |
| 理由 | report/integratedは配信実績がある広告のみ返すため、全広告取得は不要 |
| ad_persona_mapping | 後からマッピング（新広告は自動でメトリクス取得される） |

| ページングパラメータ | 型 | 説明 |
|-------------------|-----|------|
| page | int | ページ番号（1始まり） |
| page_size | int | 1ページあたり件数（最大100） |

| ページング処理フロー | 内容 |
|-------------------|------|
| 初回リクエスト | page=1, page_size=100 |
| レスポンス確認 | `response.data.page_info.total_page` で総ページ数取得 |
| 次ページ | page < total_page の間、page++でループ |
| 終了条件 | page >= total_page または data.list が空 |

| ページングレスポンス例 | 内容 |
|---------------------|------|
| page_info.page | 現在ページ（1始まり） |
| page_info.page_size | ページサイズ |
| page_info.total_number | 総レコード数 |
| page_info.total_page | 総ページ数 |

| レスポンス→DBマッピング | APIフィールド | DBカラム | 算出方法 |
|------------------------|--------------|---------|---------|
| ad_id | ad_id | ad_id | そのまま |
| impressions | impressions | impressions | そのまま |
| clicks | clicks | clicks | そのまま |
| - | - | ctr | clicks / impressions（APIで返らない場合） |
| spend | spend | spend | そのまま（小数点2桁） |
| video_views_p100 | video_views_p100 | video_views | そのまま（100%視聴数） |
| engagement_rate | engagement_rate | engagement_rate | APIから取得、なければ (clicks + video_views) / impressions |

| ctr算出式 | 内容 |
|----------|------|
| 定義 | `ctr = clicks / impressions` |
| 条件 | impressions = 0 の場合は ctr = 0 |
| 精度 | DECIMAL(5,4)、例: 0.0312 = 3.12% |

| engagement_rate算出式 | 内容 |
|---------------------|------|
| 定義 | `engagement_rate = (clicks + video_views) / impressions` |
| 条件 | impressions = 0 の場合は engagement_rate = 0 |
| 精度 | DECIMAL(5,4)、例: 0.0856 = 8.56% |
| 補足 | TikTok APIがengagement_rateを返す場合はAPI値を使用 |

| 通貨運用方針 | 内容 |
|------------|------|
| 運用通貨 | **JPY固定**（単一通貨運用） |
| 理由 | アカウント通貨=JPY、複数通貨の予定なし |
| spend解釈 | 全てJPY（円）として扱う |
| 将来対応 | 複数通貨が必要になった場合は1.7.0以降でcurrencyカラム追加を検討 |

| テストフィクスチャ | 内容 |
|-----------------|------|
| 保存場所 | `apps/api/src/__tests__/fixtures/tiktok/report_response.json` |
| 内容 | 上記レスポンス形式のモックデータ（3件の広告メトリクス） |

#### SimulationJob

| 項目 | 内容 |
|------|------|
| 責務 | ペルソナ×Nudge候補のシミュレーション実行 |
| 入力 | simulated_personas、Nudge候補プール（下記参照） |
| 出力 | simulation_runsテーブルへの保存 |
| エラー処理 | EDSL失敗時はログ出力、該当ペルソナをスキップ |

#### Nudge候補プール定義

| 項目 | 内容 |
|------|------|
| データソース | `apps/api/src/simulation/nudge_candidates.json`（JSONファイル） |
| 候補数 | 50件（初期プール） |
| 選定根拠 | 13個のProblemType × 約4種類のHook/Content = 約52件、実用範囲で50件に調整 |
| 更新方法 | JSONファイルを手動更新、デプロイで反映 |
| バージョニング | Gitで管理、変更履歴を追跡可能 |

**Nudge候補JSONの構造:**

| フィールド | 型 | 説明 |
|-----------|-----|------|
| id | string | 候補ID |
| problem_type | string | 対象ProblemType |
| hook | string | 通知のフック文言 |
| content | string | 通知の本文 |
| default_tone | string | デフォルトトーン（gentle/direct/playful） |

| なぜJSONファイルか | 理由 |
|-------------------|------|
| 変更頻度 | DBに格納するほど頻繁に変更しない |
| レビュー | バージョン管理でレビュー可能 |
| 一貫性 | デプロイと同期するため一貫性が保たれる |

#### tone/timing派生ルール

| 項目 | 内容 |
|------|------|
| tone | シミュレーション時に3種類（gentle/direct/playful）を**全て試行** |
| timing | シミュレーション時に2種類（morning/evening）を**全て試行** |
| 派生方法 | SimulationJobがNudge候補をロード後、全tone/timing組み合わせを生成 |
| 保存先 | simulation_runs.nudge_configにtone/timingを含めて保存 |

| default_toneの用途 | 内容 |
|-------------------|------|
| シミュレーション | 使用しない（全tone試行） |
| 本番Nudge送信（1.7.0以降） | Wisdomがない場合のフォールバックとして使用予定 |
| 1.6.0での役割 | Nudge候補JSONに記録するのみ、シミュレーションには影響しない |

| シミュレーション入力例 | 値 |
|---------------------|-----|
| nudge_id | "nudge_001" |
| problem_type | "staying_up_late" |
| hook | "また夜更かし？" |
| content | "今日は早めに寝よう" |
| tone | "gentle" |
| timing | "evening" |

#### EDSLRunner（Python）

| 項目 | 内容 |
|------|------|
| 責務 | EDSLライブラリを使ってシミュレーション実行 |
| 依存 | Python 3.10+, edsl, httpx, pydantic |
| 並列度 | 最大5並列（LLM API制限考慮） |
| LLM API | OpenAI API（OPENAI_API_KEY環境変数） |

#### 週次シミュレーション実行方式

| 項目 | 設定 |
|------|------|
| 実行方式 | 常駐プロセス内スケジューラ（node-cron） |
| 実行環境 | Railway APIサービス内のNode.js → Python child_process |
| Cron実行主体 | `scheduled.ts`内のnode-cronスケジューラがトリガー |
| タイムアウト | 30分/バッチ、全体2時間 |
| リトライ | 失敗時最大3回、exponential backoff |
| 並列上限 | 5並列（LLM API制限） |
| チェックポイント | simulation_runsに途中結果保存（job_run_idで紐付け）、再開可能 |
| 中断時対応 | 同一job_run_idで未処理のペルソナ×Nudge組み合わせから再開 |
| 再開判定SQL | `SELECT DISTINCT persona_id, nudge_config_hash FROM simulation_runs WHERE job_run_id = :id` で処理済みを取得、未処理のみ実行 |
| リソース制限 | メモリ2GB上限 |

| Cronモデル詳細 | 内容 |
|---------------|------|
| ライブラリ | node-cron（APIプロセス常駐） |
| 起動タイミング | APIサーバー起動時にスケジューラ登録 |
| 実装ファイル | `apps/api/src/jobs/scheduled.ts` |
| 起動コマンド | なし（APIサーバー起動で自動有効化） |

| 単一実行保証 | 内容 |
|-------------|------|
| 方式 | job_runsテーブル（UNIQUE(job_name, scheduled_date)）で重複防止 |
| 冪等性 | 同日・同ジョブは1回のみ実行（自動Cron） |
| 複数インスタンス時 | 1.6.0は単一インスタンス前提、スケールアウト非対応 |
| 失敗時再実行 | manual_trigger APIで手動再実行可能（下記参照） |

| 手動再実行の挙動 | 内容 |
|----------------|------|
| 新規実行 | 新規レコードをINSERT（同日レコードなし） |
| completed/failed時 | 既存レコードのstatusを`running`にUPDATE、started_at=NOW()、completed_at/error_messageをNULLリセット |
| **running中** | **409 Conflict**を返す（実行中ジョブは上書き不可） |
| 履歴保持 | job_runsは最新状態のみ保持、詳細履歴は1.7.0で別テーブル検討 |

| 手動再実行の判定フロー | 内容 |
|---------------------|------|
| 1 | 既存レコード検索（job_name + scheduled_date） |
| 2 | レコードなし → 新規INSERT（status=running） |
| 3 | レコードあり＆status=running → 409 Conflict |
| 4 | レコードあり＆status=completed/failed → UPDATE（status=running） |

| ジョブ排他制御 | 内容 |
|--------------|------|
| ロック方式 | INSERT ON CONFLICT + statusチェック |
| 排他取得 | `INSERT INTO job_runs (job_name, scheduled_date, status) VALUES (?, ?, 'running') ON CONFLICT (job_name, scheduled_date) DO NOTHING RETURNING id` |
| 競合時 | RETURNING idがnull → 既存レコードのstatusを確認 → runningなら何もせずreturn |
| status遷移 | running → completed/failed（下記注記参照） |

| 1.6.0 status遷移図 | 内容 |
|------------------|------|
| 開始時 | INSERT with status=`running` |
| 正常終了 | UPDATE status=`completed` |
| 異常終了 | UPDATE status=`failed` |
| 409条件 | `running`のみチェック |
| API可用性への影響 | ジョブはasync実行、APIリクエスト処理をブロックしない |

| 同時実行防止SQL例 | 内容 |
|-----------------|------|
| 新規ジョブ開始 | `INSERT INTO job_runs (job_name, scheduled_date, status, started_at) VALUES (:job_name, :date, 'running', NOW()) ON CONFLICT (job_name, scheduled_date) DO NOTHING RETURNING id` |

| UUID生成注記 | 内容 |
|------------|------|
| id省略理由 | DEFAULT gen_random_uuid()により自動生成 |
| uuid-ossp | **使用しない**（uuid_generate_v4は非推奨） |
| 競合チェック | `SELECT status FROM job_runs WHERE job_name = :job_name AND scheduled_date = :date` |
| running中なら | スキップ（ログ出力のみ） |
| failed/completed中で手動再実行なら | `UPDATE job_runs SET status = 'running', started_at = NOW(), completed_at = NULL, error_message = NULL WHERE ...` |

| job_runsテーブル | 型 | 説明 |
|-----------------|-----|------|
| id | UUID | PRIMARY KEY |
| job_name | TEXT | ジョブ名（daily_tiktok_collect等） |
| scheduled_date | DATE | 実行予定日 |
| status | TEXT | running/completed/failed |
| started_at | TIMESTAMPTZ | 開始時刻 |
| completed_at | TIMESTAMPTZ | 完了時刻 |
| - | - | UNIQUE(job_name, scheduled_date) |

| デプロイ形態 | 内容 |
|-------------|------|
| サービス構成 | 単一APIサービス（ジョブはAPIプロセス内で実行） |
| プロセス分離 | Node.js → Python child_process（同コンテナ内） |
| 理由 | Railway無料枠での複雑さ回避、1.6.0では単純構成を優先 |
| 将来拡張 | 1.7.0以降で負荷増加時にWorkerサービス分離を検討 |

| API可用性への対策 | 方法 |
|------------------|------|
| 長時間処理 | 週次ジョブは日曜00:00 UTC実行（低トラフィック時間帯） |
| タイムアウト | 全体2時間でジョブ停止、部分結果はDBに保存済み |
| 障害分離 | child_processの失敗はAPIプロセスに影響しない（try-catch） |

### 5.3 1000パターンの計算ロジック

| 項目 | 数 | 計算 |
|------|-----|------|
| ペルソナ数 | 8 | 固定 |
| Nudge候補数 | 50 | 初期プール |
| トーンバリエーション | 3 | gentle/direct/playful |
| タイミングバリエーション | 2 | morning/evening |
| 合計パターン | **2400** | 8 × 50 × 3 × 2 |
| 受け入れ条件 | 1000パターン以上 | 2400パターンで十分に達成 |

### 5.4 Cronジョブ設計

| ジョブ | 実行時間(UTC) | 処理内容 |
|--------|--------------|---------|
| daily_tiktok_collect | 06:00 | TikTokメトリクス取得 |
| daily_feedback_aggregate | 06:30 | Appフィードバック集計 |
| weekly_simulation | 日曜 00:00 | バッチシミュレーション |

---

## 6. To-Be チェックリスト

| # | To-Be項目 | 完了条件 |
|---|----------|---------|
| 1 | simulated_personasテーブル作成 | マイグレーション成功 |
| 2 | simulation_runsテーブル作成 | マイグレーション成功 |
| 3 | tiktok_ad_metricsテーブル作成 | マイグレーション成功 |
| 4 | ad_persona_mappingテーブル作成 | マイグレーション成功 |
| 5 | wisdomテーブル作成 | マイグレーション成功 |
| 6 | daily_feedback_summaryテーブル作成 | マイグレーション成功 |
| 7 | system_settingsテーブル作成 | マイグレーション成功 |
| 8 | job_runsテーブル作成 | マイグレーション成功 |
| 9 | system_settings初期データ投入 | マイグレーションで初期値挿入 |
| 10 | 8個のペルソナ初期データ投入 | seed実行成功 |
| 11 | Nudge候補プール作成 | nudge_candidates.json作成 |
| 12 | TikTokDataCollector実装 | Unit/Integrationテスト通過 |
| 13 | SimulationJob実装 | Unit/Integrationテスト通過 |
| 14 | EDSLRunner実装 | Integrationテスト通過 |
| 15 | daily_tiktok_collectジョブ | Cronテスト通過 |
| 16 | daily_feedback_aggregateジョブ | Cronテスト通過 |
| 17 | weekly_simulationジョブ | Cronテスト通過 |
| 18 | Cron停止フラグ実装 | DB設定テーブル方式 |
| 19 | Cron単一実行保証 | job_runsテーブル方式 |
| 20 | 外部APIモック実装 | nock/pytest-mockでテスト可能 |
| 21 | admin/jobs認可設計 | Bearer Token認証、ジョブ名許可リスト |
| 22 | admin/jobs監査ログ | 全リクエストをログ出力 |
| 23 | admin/jobs同日再実行（UPDATE方式） | 既存レコードをUPDATEして再実行 |
| 24 | 401連続カウンタ永続化 | system_settingsに保存、3回で停止 |
| 25 | simulation_runs再開性設計 | job_run_id + 一意制約 + UPSERT方針 |
| 26 | predictions JSON構造 | 必須キー定義（tap_rate, thumbs_up_rate等） |
| 27 | daily_feedback_summary UPSERT | 再実行時に集計結果を上書き |

---

## 7. ユーザーGUI作業

### 7.1 実装前（必須）

| # | タスク | URL/手順 | 取得するもの |
|---|--------|----------|-------------|
| 1 | TikTok For Businessアカウント作成 | https://ads.tiktok.com/ | アカウント |
| 2 | Developer登録 | Marketing API → Become a Developer | Developer ID |
| 3 | アプリ作成 | My Apps → Create New | App ID |
| 4 | スコープ申請 | Ads Management, Reporting | 承認（2-3日） |
| 5 | Access Token取得 | OAuth認証フロー実行 | Access Token |
| 6 | OpenAI API Key取得 | https://platform.openai.com/ → API Keys | OPENAI_API_KEY |
| 7 | Slack Incoming Webhook作成 | Slack App → Incoming Webhooks → Add | SLACK_WEBHOOK_URL |
| 8 | ADMIN_API_KEY生成（Staging用） | `openssl rand -base64 32` | ADMIN_API_KEY（Staging） |
| 9 | ADMIN_API_KEY生成（Production用） | `openssl rand -base64 32` | ADMIN_API_KEY（Production） |
| 10 | 環境変数設定（Staging） | Railway Staging → Variables | 設定完了 |
| 11 | 環境変数設定（Production） | Railway Production → Variables | 設定完了 |

| 環境別設定の注意 | 内容 |
|---------------|------|
| ADMIN_API_KEY | Staging/Productionで**必ず別の値**を使用 |
| TikTok関連 | 同じ値を共有（同一広告アカウント） |
| OPENAI_API_KEY | 同じ値を共有可（使用量は環境で分離しない） |
| SLACK_WEBHOOK_URL | 同じSlackチャンネルへ通知（環境タグで識別） |

| 取得した環境変数 | 説明 | 取得元 |
|-----------------|------|--------|
| TIKTOK_APP_ID | アプリID | TikTok Developer Portal |
| TIKTOK_APP_SECRET | アプリシークレット | TikTok Developer Portal |
| TIKTOK_ACCESS_TOKEN | アクセストークン | OAuth認証フロー |
| TIKTOK_ADVERTISER_ID | 広告主ID | TikTok Ads Manager |
| OPENAI_API_KEY | EDSLシミュレーション用 | OpenAI Platform |
| SLACK_WEBHOOK_URL | Slack通知用 | Slack App Incoming Webhooks |
| ADMIN_API_KEY | 管理API認証用（手動生成） | `openssl rand -base64 32` |

### 7.2 実装中（なし）

| 項目 | 内容 |
|------|------|
| 手動作業 | なし |
| 理由 | 全て自動化済み |

### 7.3 実装後（運用時）

| # | タスク | 頻度 | 詳細 |
|---|--------|------|------|
| 1 | 新規TikTok広告作成 | 新ペルソナ追加時 | Ads Managerで作成 |
| 2 | ad_persona_mapping登録 | 同上 | SQL/Admin UIで登録 |
| 3 | Access Token更新 | 60日ごと | OAuth再認証 |

---

## 8. セキュリティ

### 8.1 APIキー管理

| 項目 | 方針 |
|------|------|
| 保存場所 | Railway環境変数のみ |
| ログ出力 | シークレットは絶対に出力しない |
| コード内ハードコード | 禁止 |

| 管理対象キー | 用途 | ローテーション |
|-------------|------|---------------|
| TIKTOK_APP_ID | TikTok Marketing API | 固定 |
| TIKTOK_APP_SECRET | TikTok OAuth | 固定 |
| TIKTOK_ACCESS_TOKEN | TikTok API認証 | 60日ごと |
| TIKTOK_ADVERTISER_ID | TikTok広告主識別 | 固定 |
| OPENAI_API_KEY | EDSLシミュレーション用LLM | 必要に応じて |
| SLACK_WEBHOOK_URL | Slack通知（#anicca-alerts） | 固定 |
| ADMIN_API_KEY | 管理API認証（admin/jobs等） | 90日ごと |

### 8.2 TikTok Access Token

| 項目 | 詳細 |
|------|------|
| 有効期限 | 60日 |
| 更新方法 | OAuth再認証フロー |
| 失効時の対応 | Slack通知 + Cronジョブ停止 |
| 最小権限 | Ads Management (read-only), Reporting |

### 8.3 Cronジョブ停止方針

| 項目 | 詳細 |
|------|------|
| 停止条件 | TikTok Access Token失効（401エラー連続3回） |
| 停止方法 | `system_settings`テーブルのkey=`tiktok_cron_disabled`のvalueを`true`（boolean）に更新 |
| 実装 | ジョブ開始時にDBからフラグをチェック、`true`なら即return |
| 復旧手順 | Token更新後、DBのvalueを`false`に更新、失敗カウンタもリセット |
| 通知 | 停止時にSlack通知（#anicca-alerts） |

| 401連続回数の永続化 | 内容 |
|-------------------|------|
| 保存先 | system_settingsテーブル（key=`tiktok_401_count`） |
| 型 | JSONB（数値を格納、例: `0`, `1`, `2`, `3`） |
| 初期値 | `0` |
| インクリメント | 401エラー検出時にカウントアップ |
| リセット条件 | 成功時に`0`にリセット、またはToken更新後に手動リセット |
| 停止トリガー | count >= 3 で`tiktok_cron_disabled`を`true`に更新 |

| 期待値 | 状態 | system_settings.value |
|--------|------|----------------------|
| 初期 | 正常動作 | `false` |
| 停止時 | Cron停止 | `true` |
| 復旧後 | 正常動作 | `false` |

| 参照 | 内容 |
|------|------|
| テーブル定義 | 5.1 DBスキーマ → system_settings テーブル参照 |

### 8.4 ログ出力方針

| パターン | 可否 | 例 |
|---------|------|-----|
| シークレット出力 | ❌ 禁止 | `Token: ${process.env.TIKTOK_ACCESS_TOKEN}` |
| 処理結果出力 | ✅ OK | `[TikTok] Fetched ${metrics.length} ad metrics` |
| エラー詳細出力 | ⚠️ 注意 | APIレスポンスからシークレットを除外して出力 |

### 8.5 手動再実行API（admin/jobs）認可設計

#### エンドポイント仕様

| 項目 | 内容 |
|------|------|
| パス | `POST /api/admin/jobs/:jobName/trigger` |
| 用途 | Cronジョブの手動再実行（Token更新後等） |

#### 認証・認可（1.6.0スコープ）

| 項目 | 方式 | 1.6.0 |
|------|------|-------|
| 認証方式 | Bearer Token（ADMIN_API_KEY環境変数） | ✅ |
| ヘッダー | `Authorization: Bearer ${ADMIN_API_KEY}` | ✅ |
| Railway環境 | Staging/Productionで別々のADMIN_API_KEY | ✅ |
| IP制限 | 社内VPN/Cloudflare Access | 1.7.0 |

| 1.6.0運用前提 | 内容 |
|--------------|------|
| エンドポイント公開範囲 | **非公開**（URLを知っている人のみ） |
| 外部ドキュメント | APIドキュメントに記載しない |
| 利用者 | 開発者のみ（cURL/Postmanで手動実行） |
| 防御方針 | ADMIN_API_KEY漏洩防止が最優先、漏洩時は即座にキーローテーション |

| 認可チェック | 内容 |
|-------------|------|
| ジョブ名許可リスト | `['daily_tiktok_collect', 'daily_feedback_aggregate', 'weekly_simulation']` |
| 不正なジョブ名 | 403 Forbidden |
| トークン不一致 | 401 Unauthorized |

#### リクエスト/レスポンス

| リクエスト | 型 | 説明 |
|-----------|-----|------|
| jobName (path) | string | 実行するジョブ名 |

| scheduled_date決定ルール | ジョブ名 | 算出方法 | 例（2026-01-27 10:00 UTC実行時） |
|------------------------|---------|---------|-------------------------------|
| daily系 | daily_tiktok_collect | **前日UTC**（NOW() - 1 day） | 2026-01-26 |
| daily系 | daily_feedback_aggregate | **前日UTC**（NOW() - 1 day） | 2026-01-26 |
| weekly系 | weekly_simulation | **当日UTC**（NOW()の日付） | 2026-01-27 |

| scheduled_date算出コード例 | 内容 |
|-------------------------|------|
| daily系 | `new Date(Date.now() - 86400000).toISOString().slice(0, 10)` |
| weekly系 | `new Date().toISOString().slice(0, 10)` |

| 注記 | 内容 |
|------|------|
| 同日再実行 | completed/failed時のみ許可（既存レコードをUPDATEして再実行） |
| running時 | **409 Conflict**（実行中ジョブは上書き不可） |
| 冪等性 | 同一(job_name, scheduled_date)に対する複数回呼び出しは、既存レコードのUPDATEとなり安全 |

| レスポンス | 型 | 説明 |
|-----------|-----|------|
| success | boolean | 成功/失敗 |
| job_run_id | UUID | job_runsレコードID |
| is_retry | boolean | true=既存レコードをUPDATEした再実行 |
| message | string | 結果メッセージ |

| ステータスコード | 条件 |
|----------------|------|
| 200 | 正常実行（新規/再実行両方） |
| 400 | 不正なリクエスト |
| 401 | 認証失敗 |
| 403 | 認可失敗（ジョブ名不正） |
| 409 | 実行中ジョブあり（running） |
| 500 | 内部エラー |

#### セキュリティ対策（1.6.0スコープ）

| 対策 | 内容 | 1.6.0 |
|------|------|-------|
| Bearer Token認証 | ADMIN_API_KEY必須 | ✅ |
| ジョブ名許可リスト | 3種類のみ許可 | ✅ |
| 監査ログ | 全リクエストを構造化ログ出力（下記参照） | ✅ |
| キーローテーション | 90日ごとにADMIN_API_KEYを更新 | ✅ |
| レート制限 | 1分あたり10リクエスト/IP | 1.7.0 |
| IP制限 | Cloudflare Access | 1.7.0 |
| 認証失敗アラート | 5回連続でSlack通知 | 1.7.0 |

| 1.6.0運用制限（レート制限なし期間） | 内容 |
|--------------------------------|------|
| 手動実行頻度 | 1日あたり各ジョブ最大3回まで（運用手順で制限） |
| 実行時間帯 | 業務時間内（9:00-18:00 JST）のみ |
| 実行者 | 開発者のみ（ADMIN_API_KEYを知る人） |
| 異常検知 | 監査ログを日次で目視確認、異常時はADMIN_API_KEY即時ローテーション |

#### 監査ログ仕様

| 項目 | 内容 |
|------|------|
| 出力先 | stdout（構造化JSON）→ Railway Logs |
| 保持期間 | Railway標準（7日）、1.7.0で外部ログサービス検討 |
| DB保存 | 1.6.0では不要（Railway Logsで十分） |

| 必須フィールド | 型 | 説明 |
|---------------|-----|------|
| timestamp | ISO8601 | リクエスト時刻 |
| event | string | `admin_job_trigger` |
| ip | string | クライアントIP |
| job_name | string | 実行ジョブ名 |
| result | string | success/auth_failed/forbidden/error |
| job_run_id | UUID/null | 成功時のjob_runsレコードID |
| is_retry | boolean | 同日再実行かどうか |
| error_message | string/null | エラー時のメッセージ |

| ログ除外フィールド（セキュリティ） | 理由 |
|-------------------------------|------|
| Authorization ヘッダー | ADMIN_API_KEY漏洩防止（絶対にログに出力しない） |
| Cookie ヘッダー | セッション情報漏洩防止 |
| リクエストボディ全文 | 将来的な機密データ混入防止 |

| ログ出力例（成功） | 値 |
|------------------|-----|
| timestamp | "2026-01-26T06:00:00Z" |
| event | "admin_job_trigger" |
| ip | "192.168.1.1" |
| job_name | "daily_tiktok_collect" |
| result | "success" |
| job_run_id | "uuid-xxxx" |
| is_retry | false |

| テスト検証方法 | 内容 |
|---------------|------|
| `test_admin_jobs_audit_log` | stdoutをキャプチャし、必須フィールドの存在とJSON形式を検証 |

| IP取得方法 | 内容 |
|-----------|------|
| Express設定 | `app.set('trust proxy', 1)` （1段のプロキシを信頼） |
| 取得優先順位 | `req.ip` → X-Forwarded-Forの最初のIPを返す |
| Railway環境 | Railway Load Balancerが1段のプロキシ |

| X-Forwarded-For信頼モデル | 内容 |
|-------------------------|------|
| 前提 | Railway Load Balancerが上流でX-Forwarded-Forを設定/上書き |
| trust proxy=1の意味 | Express は1段のプロキシ（Railway LB）からのX-Forwarded-Forを**信頼する** |
| req.ipの値 | Railway LBが設定したクライアントIPを返す |
| 偽装リスク | Railway LBより前のネットワーク層での偽装は Railway 側で制御されるため、アプリ層では考慮不要 |
| 監査ログの信頼性 | Railway インフラを前提とする限り、req.ip は実際のクライアントIP |
| 補足 | Railway以外にデプロイする場合はtrust proxy設定を見直すこと |

| IP取得コード例 | 内容 |
|--------------|------|
| 実装 | `const clientIp = req.ip \|\| req.socket.remoteAddress` |

| 環境変数（追加） | 説明 |
|----------------|------|
| ADMIN_API_KEY | 管理API認証用キー |

---

## 9. 実行環境

### 9.1 EDSL Python環境

| 項目 | 詳細 |
|------|------|
| Python | 3.10+ |
| 依存パッケージ | edsl, httpx, pydantic |
| 実行ホスト | Railway APIサービスのコンテナ内 |
| 呼び出し方法 | Node.js → Python child_process（同コンテナ） |
| 並列度 | 最大5（LLM API制限考慮） |
| 分離方針 | 5.2 週次シミュレーション実行方式 参照 |

### 9.2 Railway Python導入手順

| ステップ | 内容 |
|---------|------|
| 1 | Dockerfileに`python3`と`pip`をインストール |
| 2 | `requirements.txt`に依存パッケージを記載 |
| 3 | ビルド時に`pip install -r requirements.txt`を実行 |
| 4 | 環境変数`OPENAI_API_KEY`を設定（EDSL内部で使用） |

| Dockerfile追記 | 内容 |
|----------------|------|
| apt-get update | システムパッケージ更新 |
| python3, python3-pip | Python環境インストール |
| COPY requirements.txt | 依存ファイルコピー |
| pip3 install -r requirements.txt | Python依存インストール |

| requirements.txt | バージョン |
|-----------------|-----------|
| edsl | >=0.1.0 |
| httpx | >=0.25.0 |
| pydantic | >=2.0.0 |

### 9.3 LLM APIプロバイダ

| 項目 | 詳細 |
|------|------|
| プロバイダ | OpenAI |
| モデル | gpt-4o-mini（コスト効率重視） |
| 環境変数 | `OPENAI_API_KEY` |
| 料金目安 | 2400パターン × $0.001 ≈ $2.40/回 |

### 9.4 TikTok API

| 項目 | 詳細 |
|------|------|
| レート制限 | 10リクエスト/秒、1日10,000リクエスト |
| リトライ方針 | 429エラー時、exponential backoff（max 3回） |
| タイムゾーン | UTC（APIデフォルト） |
| ページング | page_size=100、必要に応じて自動ページング |

### 9.5 外部API依存テスト方針

| 項目 | 方針 |
|------|------|
| モック対象 | TikTok Marketing API、OpenAI API（EDSL経由）、**Slack Webhook** |
| ライブラリ | nock（Node.js）、pytest-mock + responses（Python） |
| CIでの実行 | 全てモックを使用、実APIへのリクエストなし |
| ローカル実行 | モック使用がデフォルト、`--live`フラグで実APIテスト可 |

| テストレイヤー | モック方針 | 理由 |
|---------------|-----------|------|
| Unit Tests | 全てモック | 高速化、外部依存排除 |
| Integration Tests | 外部APIはモック、DBは実接続 | DB連携を検証しつつ外部依存排除 |
| E2E（手動検証） | 実API使用 | 運用環境での動作確認 |

| モックデータ例 | 保存場所 |
|--------------|---------|
| TikTokレスポンス | `apps/api/src/__tests__/fixtures/tiktok/` |
| OpenAI/EDSLレスポンス | `apps/api/src/__tests__/fixtures/edsl/` |
| Slack Webhook | `apps/api/src/__tests__/fixtures/slack/` |

| Slackモック方針 | 内容 |
|---------------|------|
| モック方法 | nockでhooks.slack.comをインターセプト |
| 検証内容 | リクエストボディ（text, channel等）の検証 |
| テスト種別 | Unit Test（notificationServiceの単体テスト） |
| 実API呼び出し | CI/テストでは禁止、`--live`フラグ時のみ許可 |

| Slackモック例 | 内容 |
|-------------|------|
| nock設定 | `nock('https://hooks.slack.com').post(/\/services\/.*/).reply(200, 'ok')` |
| 検証方法 | `expect(scope.isDone()).toBe(true)` でリクエスト送信を確認 |

| CIパイプライン | 設定 |
|---------------|------|
| 環境変数 | `CI=true` でモック強制 |
| シークレット | 不要（モック使用のため） |
| タイムアウト | Integration Tests: 5分 |

---

## 10. 受け入れ条件

| # | 条件 | 測定方法 | 対応テスト |
|---|------|---------|----------|
| 1 | 8個のペルソナがDBに登録されている | `SELECT COUNT(*) FROM simulated_personas` = 8 | #8 `test_seed_personas_count` |
| 2 | 1000パターン以上のシミュが実行できる | 最新job_run_idでスコープ（下記SQL参照） | #27 `test_acceptance_simulation_count` |
| 3 | TikTok APIからデータが自動取得できる | tiktok_ad_metricsに日次データあり | #13 `test_tiktok_collector_fetch_success` |
| 4 | Appフィードバックが日次集計される | daily_feedback_summaryテーブルにデータあり | #28 `test_acceptance_feedback_aggregate` |
| 5 | Token失効時にCron停止フラグが有効になる | system_settingsにtiktok_cron_disabled=true | #34 `test_tiktok_token_expired_db_auto_disable` |
| 6 | Token失効→Cron停止時にSlack通知が送信される | Slack #anicca-alertsに通知到達 | #29 `test_token_expired_slack_notification` |
| 7 | admin/jobs認証がBearer Tokenで保護されている | 無効トークンで401 | #44 `test_admin_jobs_auth_failure` |
| 8 | Cron単一実行保証が機能する | INSERT失敗時スキップログ出力 | #37 `test_cron_single_execution_guarantee` |
| 9 | admin/jobs実行中409が返る | running状態で再トリガー→409 | #38 `test_cron_manual_trigger_api` |
| 10 | ジョブ再開性が機能する（resumable） | 中断後のリトライで続行 | #51 `test_simulation_runs_resume_from_incomplete` |
| 11 | 401カウンタがDBに永続化される | 再起動後もカウンタ維持 | #48 `test_tiktok_401_count_persistence` |
| 12 | 全テストが通過する | CI green | 全テスト |

**受け入れ条件#2の測定SQL:**

| 項目 | 内容 |
|------|------|
| クエリ | `SELECT COUNT(*) FROM simulation_runs WHERE job_run_id = (SELECT id FROM job_runs WHERE job_name = 'weekly_simulation' ORDER BY scheduled_date DESC LIMIT 1)` |
| 条件 | 結果 >= 1000 |
| 理由 | 過去の実行分と混在させず、直近の週次ジョブの結果のみを測定 |

---

## 11. テストマトリックス

| # | To-Be | テスト名 | 種別 | カバー |
|---|-------|----------|------|--------|
| 1 | simulated_personasテーブル | `test_migration_personas_table` | Integration | ⬜ |
| 2 | simulation_runsテーブル | `test_migration_simulation_runs_table` | Integration | ⬜ |
| 3 | tiktok_ad_metricsテーブル | `test_migration_tiktok_metrics_table` | Integration | ⬜ |
| 4 | ad_persona_mappingテーブル | `test_migration_ad_persona_mapping_table` | Integration | ⬜ |
| 5 | wisdomテーブル | `test_migration_wisdom_table` | Integration | ⬜ |
| 6 | daily_feedback_summaryテーブル | `test_migration_daily_feedback_summary_table` | Integration | ⬜ |
| 7 | system_settingsテーブル | `test_migration_system_settings_table` | Integration | ⬜ |
| 8 | ペルソナ初期データ投入 | `test_seed_personas_count` | Integration | ⬜ |
| 9 | Nudge候補プール読み込み | `test_nudge_candidates_load` | Unit | ⬜ |
| 10 | Nudge候補プールバリデーション | `test_nudge_candidates_validation` | Unit | ⬜ |
| 11 | ペルソナバリデーション | `test_persona_validation_valid` | Unit | ⬜ |
| 12 | ペルソナバリデーション失敗 | `test_persona_validation_invalid` | Unit | ⬜ |
| 13 | TikTokメトリクス取得 | `test_tiktok_collector_fetch_success` | Integration | ⬜ |
| 14 | TikTokメトリクス取得失敗 | `test_tiktok_collector_fetch_failure` | Integration | ⬜ |
| 15 | TikTokメトリクス保存 | `test_tiktok_collector_save_to_db` | Integration | ⬜ |
| 16 | TikTok重複データ処理 | `test_tiktok_collector_upsert_duplicate` | Integration | ⬜ |
| 17 | TikTokトークン失効 | `test_tiktok_collector_token_expired` | Integration | ⬜ |
| 18 | EDSLシミュレーション | `test_edsl_runner_batch_simulation` | Integration | ⬜ |
| 19 | EDSL失敗時スキップ | `test_edsl_runner_failure_skip` | Integration | ⬜ |
| 20 | SimulationJob実行 | `test_simulation_job_run_success` | Integration | ⬜ |
| 21 | SimulationJob保存 | `test_simulation_job_save_results` | Integration | ⬜ |
| 22 | SimulationJob失敗 | `test_simulation_job_failure_handling` | Integration | ⬜ |
| 23 | daily_tiktok_collectジョブ | `test_cron_tiktok_collect_executes` | Integration | ⬜ |
| 24 | daily_feedback_aggregateジョブ | `test_cron_feedback_aggregate_executes` | Integration | ⬜ |
| 25 | weekly_simulationジョブ | `test_cron_weekly_simulation_executes` | Integration | ⬜ |
| 26 | weekly_simulation失敗時 | `test_cron_weekly_simulation_failure` | Integration | ⬜ |
| 27 | 受け入れ条件#2検証 | `test_acceptance_simulation_count` | Integration | ⬜ |
| 28 | 受け入れ条件#4検証 | `test_acceptance_feedback_aggregate` | Integration | ⬜ |
| 29 | Token失効→停止時Slack通知 | `test_token_expired_slack_notification` | Integration | ⬜ |
| 30 | ad_persona_mapping登録 | `test_ad_persona_mapping_insert` | Integration | ⬜ |
| 31 | tiktok_ad_metrics一意制約 | `test_tiktok_metrics_unique_constraint` | Integration | ⬜ |
| 32 | daily_feedback_summary一意制約 | `test_daily_feedback_summary_unique_constraint` | Integration | ⬜ |
| 33 | DB Cron停止フラグ参照 | `test_cron_db_disable_flag_check` | Unit | ⬜ |
| 34 | Token失効時DB自動停止 | `test_tiktok_token_expired_db_auto_disable` | Integration | ⬜ |
| 35 | job_runsテーブル | `test_migration_job_runs_table` | Integration | ⬜ |
| 36 | system_settings初期データ | `test_system_settings_initial_data` | Integration | ⬜ |
| 37 | Cron単一実行保証（重複防止） | `test_cron_single_execution_guarantee` | Integration | ⬜ |
| 38 | Cron手動再実行API | `test_cron_manual_trigger_api` | Integration | ⬜ |
| 39 | TikTokAPIモック動作 | `test_tiktok_api_mock_response` | Unit | ⬜ |
| 40 | EDSLモック動作 | `test_edsl_mock_response` | Unit | ⬜ |
| 41 | tone派生ルール | `test_simulation_tone_variations` | Unit | ⬜ |
| 42 | timing派生ルール | `test_simulation_timing_variations` | Unit | ⬜ |
| 43 | admin/jobs認証成功 | `test_admin_jobs_auth_success` | Integration | ⬜ |
| 44 | admin/jobs認証失敗 | `test_admin_jobs_auth_failure` | Integration | ⬜ |
| 45 | admin/jobsジョブ名不正 | `test_admin_jobs_invalid_job_name` | Integration | ⬜ |
| 46 | admin/jobs同日再実行（UPDATE方式） | `test_admin_jobs_retry_update` | Integration | ⬜ |
| 47 | admin/jobs監査ログ | `test_admin_jobs_audit_log` | Integration | ⬜ |
| 48 | 401連続カウンタ永続化 | `test_tiktok_401_count_persistence` | Integration | ⬜ |
| 49 | 401カウンタ成功時リセット | `test_tiktok_401_count_reset_on_success` | Integration | ⬜ |
| 50 | simulation_runs一意制約 | `test_simulation_runs_unique_constraint` | Integration | ⬜ |
| 51 | simulation_runs再開（未処理から継続） | `test_simulation_runs_resume_from_incomplete` | Integration | ⬜ |
| 52 | simulation_runs重複防止 | `test_simulation_runs_duplicate_prevention` | Integration | ⬜ |
| 53 | predictions JSON構造バリデーション | `test_predictions_json_schema_validation` | Unit | ⬜ |
| 54 | daily_feedback_summary UPSERT | `test_daily_feedback_summary_upsert` | Integration | ⬜ |
| 55 | nudge_config_hash決定性 | `test_nudge_config_hash_deterministic` | Unit | ⬜ |
| 56 | TikTokページング | `test_tiktok_paging_multipage` | Integration | ⬜ |

---

## 12. E2Eシナリオ

| 注記 | 内容 |
|------|------|
| Maestro E2E | 不要（バックエンド内部機能のため） |

### 12.1 手動検証シナリオ

| # | シナリオ | 確認項目 |
|---|---------|---------|
| 1 | Cronジョブ実行確認 | Railway logsでジョブ実行ログを確認 |
| 2 | TikTokデータ確認 | DBのtiktok_ad_metricsにデータあり |
| 3 | シミュレーション結果確認 | DBのsimulation_runsにデータあり |
| 4 | 日次集計確認 | DBのdaily_feedback_summaryにデータあり |
| 5 | Token失効→Cron停止 | 401エラー3回でtiktok_cron_disabled=true確認 |
| 6 | Slack通知確認 | #anicca-alertsに停止通知が届く |
| 7 | admin/jobs手動再実行 | cURLでPOST→200返却→ジョブ実行確認 |

| 自動テストのみで担保する項目 | 内容 |
|--------------------------|------|
| Token失効検知 | #17, #34 Integration Testsでモック検証 |
| Slack通知送信 | #29 Integration Testsでモック検証 |
| admin/jobs認証 | #43, #44 Integration Testsで検証 |

| 手動検証が必要な理由 | 内容 |
|-------------------|------|
| #5 Token失効→Cron停止 | 運用環境でのDB更新とCron停止の連携確認 |
| #6 Slack通知 | 実際のSlackチャンネルへの到達確認 |
| #7 admin/jobs | 運用環境でのAPI疎通とジョブ起動確認 |

---

## 13. Skills / Sub-agents

| ステージ | 使用するもの | 用途 |
|---------|-------------|------|
| Spec作成 | `/plan` | 実装計画の作成 |
| テスト実装 | `/tdd-workflow` | TDDでテスト先行開発 |
| コードレビュー | `/code-review` | 実装後のレビュー |
| ビルドエラー | `/build-fix` | エラー発生時の修正 |
| Spec/コードレビュー | `/codex-review` | 自動レビューゲート |

---

## 14. ローカライズ

| 注記 | 内容 |
|------|------|
| 追加テキスト | なし（バックエンド内部機能のため） |

| 言語 | 追加文字列 |
|------|-----------|
| 日本語 | なし |
| 英語 | なし |

---

## 15. 実行手順

| # | コマンド | 説明 |
|---|---------|------|
| 1 | `cd apps/api && npm run build` | ビルド |
| 2 | `cd apps/api && npm run test` | Unit + Integration Tests |
| 3 | `cd apps/api && npm run test -- --grep "tiktok"` | 特定テストのみ |
| 4 | `cd apps/api && npx supabase db push` | マイグレーション |
| 5 | `cd apps/api && npm run seed:personas` | ペルソナseed |
| 6 | `cd apps/api && railway up --environment staging` | Stagingデプロイ |

---

## 16. タスクリスト

| # | タスク | ファイル | 優先度 |
|---|--------|----------|--------|
| 1 | DBスキーマ作成（migration、system_settings、job_runs含む） | `apps/api/supabase/migrations/` | 高 |
| 2 | system_settings初期データ（マイグレーション内） | `apps/api/supabase/migrations/` | 高 |
| 3 | ペルソナ初期データ投入 | `apps/api/src/seeds/personas.ts` | 高 |
| 4 | Nudge候補プール作成 | `apps/api/src/simulation/nudge_candidates.json` | 高 |
| 5 | TikTokDataCollector実装 | `apps/api/src/services/tiktokDataCollector.ts` | 高 |
| 6 | EDSL Pythonスクリプト | `apps/api/src/simulation/edsl_runner.py` | 高 |
| 7 | SimulationJob実装（tone/timing派生含む） | `apps/api/src/jobs/simulationJob.ts` | 中 |
| 8 | 日次Cronジョブ設定 | `apps/api/src/jobs/scheduled.ts` | 中 |
| 9 | Cron単一実行保証（job_runs連携） | `apps/api/src/jobs/scheduled.ts` | 中 |
| 10 | Dockerfile更新（Python追加） | `apps/api/Dockerfile` | 中 |
| 11 | 外部APIモックfixture | `apps/api/src/__tests__/fixtures/` | 中 |
| 12 | エラー通知（Slack） | `apps/api/src/services/notificationService.ts` | 低 |
| 13 | Cron停止フラグ実装 | `apps/api/src/jobs/scheduled.ts` | 低 |
| 14 | 手動再実行API | `apps/api/src/routes/admin/jobs.ts` | 低 |

---

## 17. レビューチェックリスト

### 17.1 Specレビュー

| # | 項目 | 確認 |
|---|------|------|
| 1 | 全To-Beがテストマトリックスに含まれているか | ⬜ |
| 2 | 受け入れ条件がテスト可能な形式か | ⬜ |
| 3 | 設計（シグネチャ、データモデル）が明確か | ⬜ |
| 4 | 境界（やらないこと）が定義されているか | ⬜ |
| 5 | 後方互換性は保たれているか | ⬜ |
| 6 | セキュリティ（APIキー管理）が適切か | ⬜ |
| 7 | As-Isの問題がTo-Beで解決されるか | ⬜ |

### 17.2 実装レビュー

| # | 項目 | 確認 |
|---|------|------|
| 1 | テストが先に書かれているか（TDD） | ⬜ |
| 2 | 80%以上のテストカバレッジか | ⬜ |
| 3 | エラーハンドリングが適切か | ⬜ |
| 4 | ログ出力にシークレットが含まれていないか | ⬜ |
| 5 | 既存APIに影響がないか | ⬜ |

---

## 18. 参考

| 種別 | リンク |
|------|--------|
| EDSL公式 | https://github.com/expectedparrot/edsl |
| TikTok Marketing API | https://business-api.tiktok.com/portal/docs |

---

## 19. 次のステップ（1.7.0）

| # | 機能 | 詳細 |
|---|------|------|
| 1 | 週次校正ループ | シミュ予測 vs 実データ比較 |
| 2 | LLM Wisdom抽出 | 効果的なパターンを自然言語で抽出 |
| 3 | Wisdom適用 | Nudge生成時にWisdomを参照 |

---

*このSpecはCodex Review反復中。*
