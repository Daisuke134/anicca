# UUID移行計画（v0.3）: text `user_id` → `profiles.id` (uuid)

## 目的
v0.3 で新設するテーブル（`user_traits`, `daily_metrics`, `nudge_*`, `feeling_sessions` など）は UUID を前提に設計する。
一方、既存の `apps/api` では歴史的経緯により `user_id` が **TEXT** のテーブルが多い。
このギャップを事故なく埋めるため、v0.3 は「二重書き込み＋読み優先」方式で移行する。

## 現状（一次情報）
- `public.profiles.id`: UUID（`apps/api/supabase/migrations/20251106_create_profiles.sql`）
- `public.user_settings.user_id`: UUID（FK）
- `tokens.user_id`: TEXT（`apps/api/docs/migrations/001_create_tokens.sql`）
- `public.user_subscriptions.user_id`: TEXT（`apps/api/docs/migrations/006_init_billing_tables_on_railway.sql`）
- `mobile_profiles.user_id`: TEXT だが、`apps/api/docs/migrations/004_backfill_profile_user_ids.sql` により **Apple ID → UUID文字列** へ置換される設計

## v0.3 方針（段階的）

### フェーズA: 新規テーブルは UUID を「正」とする
- v0.3 新設テーブルは `user_id uuid` を基本。
- API層では、受け取った `user-id` ヘッダが UUID 文字列であることを前提に実装する（非UUIDなら 400/401 扱い）。

### フェーズB: 二重書き込み期間（v0.3〜）
- 既存の TEXT `user_id` テーブルに対しては、**UUID文字列**を書き続ける（互換のため TEXT をすぐに変えない）。
- 将来的に `profile_id uuid` カラムを追加する場合は「NULL許容＋緩いFK」で導入し、バックフィル後に強める。

### フェーズC: 読みの優先順位
- 新コードの読み取りは `profile_id(uuid)` を優先。
- `profile_id` が無い場合のみ `user_id(text)` をフォールバック。

### フェーズD: バックフィルと監視
- `profile_id IS NULL` 件数を継続監視し、再実行可能なバックフィル手段を用意。
- v0.3 のスコープでは「完全移行（text列削除）」はしない（v0.4 で実施）。

## 推奨チェック（手動）
1. DB上の型確認:
   - `\\d public.profiles`
   - `\\d public.user_settings`
   - `\\d public.user_subscriptions`
   - `\\d public.usage_sessions`
2. `mobile_profiles.user_id` が UUID文字列に変換済みか確認:
   - `SELECT user_id FROM mobile_profiles LIMIT 5;`

## 注意
- `mobile_alarm_schedules.id` は過去マイグレーションが UUID/TEXT で揺れているため、実DBの型を先に確認すること。
  v0.3 ではここを無理に直さず、v0.4 で整理するのが安全。










