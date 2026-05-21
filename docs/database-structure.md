# Anicca Database Structure

> **最終更新**: 2026-01-30
> **Production**: Railway PostgreSQL (`tramway.proxy.rlwy.net:32477`)
> **Staging**: Railway PostgreSQL (`ballast.proxy.rlwy.net:51992`)

## Staging vs Production 差分

| 差分 | テーブル | 状態 |
|------|---------|------|
| Production のみ | `mobile_alarm_schedules` | Legacy（削除候補） |
| Production のみ | `mobile_voip_tokens` | Legacy（削除候補） |

**それ以外は同一構成（27テーブル Production / 25テーブル Staging）。**

---

## テーブル一覧: アクティブ vs Legacy

### アクティブ（iOS から実際に使用中）

| テーブル | 行数(Prod) | 用途 | 書き込み元 |
|---------|-----------|------|-----------|
| `mobile_profiles` | 177 | デバイスごとのプロフィール（struggles, language等） | iOS アプリ → `/api/mobile/profile` |
| `nudge_events` | 8,240 | 全 Nudge 送信履歴（ルールベース + LLM） | Cron `generateNudges.js` |
| `user_subscriptions` | 53 | サブスクリプション状態（RevenueCat 連携） | RevenueCat Webhook |
| `user_settings` | 41 | ユーザー設定（言語、タイムゾーン、通知ON/OFF） | iOS アプリ → API |
| `bandit_models` | 1 | Thompson Sampling モデル重み | Cron / LinTS algorithm |
| `tiktok_posts` | 3 | TikTok 投稿記録 | GitHub Actions TikTok エージェント |
| `_prisma_migrations` | 5 | Prisma マイグレーション履歴 | `prisma migrate deploy` |
| `schema_migrations` | 6 | 手動マイグレーション履歴 | 手動 SQL |

### API はあるが iOS 未連携（孤立テーブル）

| テーブル | 行数(Prod) | 用途 | 実態 |
|---------|-----------|------|------|
| `daily_metrics` | 46 | 日次メトリクス（睡眠、歩数、SNS使用等） | **API エンドポイント存在するが iOS が一度も呼んでいない。HealthKit 連携未実装。** |
| `feeling_sessions` | 111 | DeepDive / Tell Anicca セッション | **API（`/feeling/start`, `/feeling/end`）存在するが iOS の DeepDive/TellAnicca はローカル保存のみ。API 未連携。** |
| `sensor_access_state` | 10 | センサーアクセス許可状態 | **API 存在するが ScreenTime Extension は v1.5.0 で削除済み。iOS から呼ばれていない可能性大。** |
| `type_stats` | 0 | ProblemType 別の集計統計 | **Cron が毎日書き込むはずだが 0行。読み取るコードもない。完全に死んでいる。** |

### Legacy（Sign in with Apple 時代 — 現在新規ユーザーは使わない）

| テーブル | 行数(Prod) | 用途 | 状態 |
|---------|-----------|------|------|
| `profiles` | 48 | Sign in with Apple ユーザー（UUID = Apple User ID） | **Legacy**: 新規匿名ユーザーは作成されない。既存ユーザーの FK 参照先として残存 |
| `refresh_tokens` | 339 | JWT リフレッシュトークン | **Legacy**: Sign in with Apple 認証フロー用 |
| `tokens` | 0 | OAuth トークン（Slack/Google 等） | **Legacy**: 0行。使っていない |
| `user_traits` | 18 | ユーザー特性（struggles, ideals, big5） | **Legacy**: `mobile_profiles.profile` に移行済み。FK で `profiles` に依存 |
| `user_type_estimates` | 2 | ユーザータイプ推定（UserTypeService） | **Legacy**: `profiles` に依存。匿名ユーザーでは profiles が存在しないため warning が出る |

### Legacy（完全未使用 — 削除候補）

| テーブル | 行数(Prod) | 用途 | 削除判断 |
|---------|-----------|------|---------|
| `habit_logs` | 0 | 旧 Habit トラッキング | **削除 OK**: 0行、HabitType は完全廃止済み |
| `hook_candidates` | 0 (Prod) | Hook テキスト候補 DB | **削除検討**: Staging に20行あり。Phase 7+8 で使う予定だったがプロンプト内蔵に変更 |
| `mobile_alarm_schedules` | 8 | 旧アラームスケジュール | **削除 OK**: ProblemType ベースに移行済み |
| `mobile_voip_tokens` | 0 | VoIP プッシュトークン | **削除 OK**: 音声機能は廃止済み |
| `monthly_vc_grants` | 71 | 月次 Voice Credit 付与 | **削除 OK**: Voice Credit 機能は廃止済み |
| `nudge_outcomes` | 1 | Nudge 結果（報酬値） | **削除検討**: bandit_models と連携予定だったが 1行のみ |
| `realtime_usage_daily` | 0 | リアルタイム使用量カウント | **削除 OK**: 0行、機能未使用 |
| `subscription_events` | 0 | RevenueCat イベント生ログ | **削除検討**: Webhook 受信用だが 0行 |
| `usage_sessions` | 368 | Voice セッション使用量 | **削除 OK**: Voice 機能は廃止済み |
| `wisdom_patterns` | 0 | Wisdom パターン（クロスアプリ学習） | **削除検討**: Phase 7+8 で使う予定だったが 0行 |

---

## アクティブテーブル詳細スキーマ

### `mobile_profiles`（最重要）

全ユーザーのマスターテーブル。デバイス ID がプライマリキー。

| カラム | 型 | 説明 |
|--------|-----|------|
| `device_id` | text PK | iOS IDFV（デバイス識別子） |
| `user_id` | text | = device_id（匿名ユーザー）or Apple User ID |
| `profile` | jsonb | struggles, language, nudgeIntensity 等 |
| `language` | text | 'ja' or 'en' |
| `created_at` | timestamptz | 作成日 |
| `updated_at` | timestamptz | 更新日 |

`profile` JSON の中身:
```json
{
  "struggles": ["staying_up_late", "anxiety", ...],
  "preferredLanguage": "ja",
  "nudgeIntensity": "normal",
  "stickyMode": true,
  "gender": "", "ageRange": "", "displayName": "",
  "ideals": [], "keywords": [],
  "wakeRoutines": [], "sleepRoutines": [],
  "trainingGoal": "", "trainingFocus": [],
  "wakeLocation": "", "sleepLocation": "",
  "acquisitionSource": "", "summary": ""
}
```

### `nudge_events`（最重要）

全 Nudge 送信の記録。LLM / ルールベース両方。

| カラム | 型 | 説明 |
|--------|-----|------|
| `id` | uuid PK | |
| `user_id` | uuid | device_id を UUID 化したもの |
| `domain` | text | 常に `'problem_nudge'` |
| `subtype` | text | ProblemType（例: `staying_up_late`） |
| `decision_point` | text | スケジュール時刻（例: `07:00`） |
| `state` | jsonb | hook, content, tone, reasoning 等 |
| `action_template` | text | Nudge アクションテンプレート |
| `channel` | text | `'push'` |
| `sent` | boolean | 送信済みフラグ |
| `created_at` | timestamptz | |

### `user_subscriptions`

| カラム | 型 | 説明 |
|--------|-----|------|
| `user_id` | text PK | device_id |
| `plan` | text | `'free'` or `'premium'` |
| `status` | text | `'free'`, `'trial'`, `'active'`, `'expired'` |
| `entitlement_source` | text | `'revenuecat'` |
| `current_period_end` | timestamptz | 課金期限 |
| `trial_end` | timestamptz | トライアル期限 |

### `user_settings`

| カラム | 型 | 説明 |
|--------|-----|------|
| `user_id` | uuid PK | profiles.id への FK |
| `language` | text | `'ja'` or `'en'` |
| `timezone` | text | `'Asia/Tokyo'` |
| `notifications_enabled` | boolean | 通知 ON/OFF |
| `preferences` | jsonb | その他設定 |

### `bandit_models`

| カラム | 型 | 説明 |
|--------|-----|------|
| `id` | uuid PK | |
| `domain` | text | `'nudge_tone'` 等 |
| `version` | int | モデルバージョン |
| `weights` | jsonb | Thompson Sampling の重み |
| `covariance` | jsonb | 共分散行列 |

### `type_stats`

| カラム | 型 | 説明 |
|--------|-----|------|
| `type_id` | varchar PK | ProblemType |
| `tone` | varchar PK | NudgeTone |
| `tapped_count` | bigint | タップ数 |
| `ignored_count` | bigint | 無視数 |
| `thumbs_up_count` | bigint | 👍 数 |
| `thumbs_down_count` | bigint | 👎 数 |
| `tap_rate` | numeric | タップ率 |
| `thumbs_up_rate` | numeric | 👍 率 |

---

## データフロー

```
iOS アプリ
  ├─ POST /api/mobile/profile → mobile_profiles（upsert）
  ├─ POST /api/mobile/nudge/feedback → nudge_events（feedback 更新）
  ├─ GET /api/mobile/nudge/today → LLM Nudge 取得
  └─ RevenueCat Webhook → user_subscriptions

Cron (JST 5:00)
  ├─ generateNudges.js → nudge_events（INSERT）
  │   ├─ shouldUseLLM() → nudge_events をチェック（Day 1 vs Day 2+）
  │   ├─ mobile_profiles から struggles 取得
  │   └─ profiles → user_type_estimates → UserTypeService（Legacy 依存）
  └─ aggregateTypeStats → type_stats, bandit_models

GitHub Actions (daily)
  ├─ TikTok Agent → tiktok_posts
  └─ Daily Metrics → Slack（DB 不使用）
```

---

## 既知の問題

| # | 問題 | 影響 | 対処 |
|---|------|------|------|
| 1 | `profiles` が匿名ユーザーで作成されない | UserTypeService が warning を出す | `mobile_profiles` を唯一のユーザーマスターにリファクタ |
| 2 | `user_traits` が `profiles` に FK 依存 | 匿名ユーザーで user_traits が保存できない | `mobile_profiles.profile` に移行済みなので不要 |
| 3 | Legacy テーブルが 10+ ある | DB が見づらい、混乱の原因 | 段階的に削除（下記推奨順序） |

## 推奨クリーンアップ順序

| 順位 | テーブル | 理由 | リスク |
|------|---------|------|--------|
| 1 | `habit_logs` | 0行、機能廃止済み | なし |
| 2 | `mobile_voip_tokens` | 0行、音声機能廃止済み | なし |
| 3 | `realtime_usage_daily` | 0行、未使用 | なし |
| 4 | `mobile_alarm_schedules` | 8行のみ、旧アラーム | なし |
| 5 | `monthly_vc_grants` | Voice Credit 廃止済み | なし |
| 6 | `usage_sessions` | Voice セッション廃止済み | なし |
| 7 | `tokens` | 0行、OAuth 未使用 | なし |
| 8 | `subscription_events` | 0行 | Webhook 再実装時に再作成可能 |
| 9 | `wisdom_patterns` | 0行、Phase 7+8 未使用 | 将来使う可能性あり |
| 10 | `hook_candidates` | Staging に20行 | 将来使う可能性あり |

**削除手順:**
```sql
-- 1. バックアップ（念のため）
pg_dump -t <table_name> > backup_<table_name>.sql

-- 2. 依存関係チェック
SELECT conname, conrelid::regclass, confrelid::regclass
FROM pg_constraint WHERE confrelid = '<table_name>'::regclass;

-- 3. 削除
DROP TABLE <table_name>;

-- 4. Prisma スキーマから削除
-- prisma/schema.prisma から model を削除
```
