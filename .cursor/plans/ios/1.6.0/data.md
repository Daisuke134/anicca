# Anicca DB テーブル使用状況（1.6.0 リファクタ用）

> **調査日**: 2026-01-30
> **調査方法**: コードベース全検索（API routes, iOS Swift, Cron jobs, Prisma schema）

## テーブル分類サマリ

| カテゴリ | テーブル数 | 内容 |
|---------|-----------|------|
| アクティブ（iOS連携済み） | 6 | mobile_profiles, nudge_events, user_subscriptions, user_settings, bandit_models, tiktok_posts |
| インフラ | 2 | _prisma_migrations, schema_migrations |
| API あるが iOS 未連携 | 4 | daily_metrics, feeling_sessions, sensor_access_state, type_stats |
| Legacy（Sign in with Apple） | 5 | profiles, refresh_tokens, tokens, user_traits, user_type_estimates |
| 削除候補（機能廃止/0行） | 10 | habit_logs, hook_candidates, mobile_alarm_schedules, mobile_voip_tokens, monthly_vc_grants, nudge_outcomes, realtime_usage_daily, subscription_events, usage_sessions, wisdom_patterns |

---

## アクティブテーブル（6テーブル — これだけが本当に使われている）

| テーブル | 行数 | 書込元 | 読取元 | 重要度 |
|---------|------|--------|--------|--------|
| `mobile_profiles` | 177 | iOS → API | API, Cron | **最重要** — 全ユーザーのマスター |
| `nudge_events` | 8,240 | Cron | API, iOS | **最重要** — 全通知履歴 |
| `user_subscriptions` | 53 | RevenueCat Webhook | API | **最重要** — 課金状態 |
| `user_settings` | 41 | iOS → API | API | 高 — 言語/TZ/通知設定 |
| `bandit_models` | 1 | LinTS algorithm | LinTS algorithm | 高 — Thompson Sampling 重み |
| `tiktok_posts` | 3 | GitHub Actions | Admin API | 中 — TikTok自動投稿 |

---

## API はあるが iOS 未連携（4テーブル — 1.6.0 で判断が必要）

### `daily_metrics`（46行）

| 項目 | 状態 |
|------|------|
| API エンドポイント | `POST /api/mobile/daily_metrics` — 存在する |
| 読み取り | `GET /api/mobile/behavior/summary`, `POST /api/mobile/nudge/pre-reminder` |
| iOS 連携 | **なし** — HealthKit/Screen Time 連携が未実装 |
| 判断 | 1.6.0 で HealthKit 連携するなら活用。しないなら削除候補。 |

### `feeling_sessions`（111行）

| 項目 | 状態 |
|------|------|
| API エンドポイント | `POST /api/mobile/feeling/start`, `POST /api/mobile/feeling/end` |
| 読み取り | `contextSnapshot.js`（リアルタイム機能用） |
| iOS 連携 | **なし** — DeepDive/TellAnicca は UI があるがローカル保存のみ。API を呼んでいない |
| 判断 | 1.6.0 で DeepDive を API 連携するなら活用。しないなら削除候補。 |

### `sensor_access_state`（10行）

| 項目 | 状態 |
|------|------|
| API エンドポイント | `PUT/GET /api/mobile/sensors/state` |
| iOS 連携 | **不明** — ScreenTime Extension は v1.5.0 で削除済み |
| 判断 | iOS コードを確認して、呼んでいないなら削除候補。 |

### `type_stats`（0行）

| 項目 | 状態 |
|------|------|
| 書き込み | `aggregateTypeStats.js` Cron（毎日 6:00 JST） |
| 読み取り | **なし** — 読み取るコードが存在しない |
| 判断 | **削除候補** — 書き込みはあるが読まれない。完全に死んでいる。 |

---

## Legacy テーブル（Sign in with Apple — 5テーブル）

| テーブル | 行数 | なぜ消せない | 1.6.0 アクション |
|---------|------|-------------|-----------------|
| `profiles` | 48 | `nudgeHelpers.js` が FK 参照。匿名ユーザーで warning | FK 依存をリファクタして `mobile_profiles` に一本化 |
| `refresh_tokens` | 339 | Sign in with Apple 認証用 | profiles リファクタ後に削除 |
| `user_traits` | 18 | `profiles` に FK 依存 | profiles リファクタ後に削除 |
| `user_type_estimates` | 2 | `profiles` に FK 依存 | profiles リファクタ後に削除 |
| `tokens` | 0 | 0行、FK なし | **即削除 OK** |

---

## 即削除 OK テーブル（10テーブル）

| 順位 | テーブル | 行数 | 理由 | リスク |
|------|---------|------|------|--------|
| 1 | `habit_logs` | 0 | HabitType 完全廃止 | なし |
| 2 | `mobile_voip_tokens` | 0 | 音声機能廃止 | なし |
| 3 | `realtime_usage_daily` | 0 | 未使用 | なし |
| 4 | `tokens` | 0 | OAuth 未使用 | なし |
| 5 | `mobile_alarm_schedules` | 8 | ProblemType 移行済み | なし |
| 6 | `monthly_vc_grants` | 71 | Voice Credit 廃止 | なし |
| 7 | `usage_sessions` | 368 | Voice Session 廃止 | なし |
| 8 | `subscription_events` | 0 | Webhook 未使用 | なし |
| 9 | `nudge_outcomes` | 1 | bandit 未連携 | なし |
| 10 | `wisdom_patterns` | 0 | Phase 7+8 未使用 | なし |

---

## 1.6.0 推奨アクション

| 優先度 | アクション | 影響テーブル |
|--------|-----------|-------------|
| P0 | 即削除（0行/機能廃止テーブル 10個） | 上記10テーブル |
| P1 | `profiles` FK 依存を `mobile_profiles` に移行 | profiles, user_traits, user_type_estimates, refresh_tokens |
| P2 | `daily_metrics` / `feeling_sessions` の iOS 連携判断 | daily_metrics, feeling_sessions |
| P3 | `type_stats` 削除 or 読み取りコード追加 | type_stats |

---

## 詳細スキーマ

詳細は `docs/database-structure.md` を参照。
