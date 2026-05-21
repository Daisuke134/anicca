# 2026-02-17 APNs Problem Notifications + Subscription Sync + Cron Cleanup (SSOT)

## TL;DR
- **APNs Problem通知（1.6.3 spec）は prod/staging ともにコード反映済み**。
- **prodで通知が止まっていた原因はデータ不整合（mobile_profiles.user_idの紐付け）**で、prod DBはバックフィルで修復済み。
- **“通常状態ユーザー（= サインインしてないユーザー、実質ほぼ全員）”の課金が server側でfree扱いになるバグが残っている可能性が高い**
  - 原因: iOSがRevenueCat→Backend同期を **`.signedIn` のときだけ**実行しているため。
- **LLM生成（generateNudges.js）は今も動き得る**: Railwayの `nudge-cronp` は `CRON_MODE=nudges` + `OPENAI_API_KEY` で実行される構成。

## 今日のTODO（忘れない用 / 優先順）
1) **iOS: `SubscriptionManager.syncNow()` の `signedIn` ガード撤去（匿名ユーザーでもBackend同期）**
   - いまの実装は `guard case .signedIn(...) = AppState.shared.authStatus else { return }` で終了している。
   - 結果: **匿名課金ユーザー（= 実質ほぼ全員）**は RevenueCat の購読状態をBackendへ同期しない。
2) **Backend: “RevenueCatの app_user_id” と “Aniccaの profile_id(UUID)” を紐付けてSSOT化**
   - APNs送信ジョブは `push_tokens.profile_id(UUID)` 単位でfree/proを判定して送信量を決める。
   - なので `user_subscriptions` は最終的に **profile_id(UUID)** をキーに揃えるのが安全。
3) **RevenueCat webhook: 到達確認 + `subscription_events` への監査ログ保存を実装**
   - 現状 `subscription_events` は 0件でも webhook未到達とは断定できない（そもそもinsertしていない可能性がある）。
4) **LLM生成の停止（staging/prod）**
   - Railwayの cron サービス（`nudge-cron` / `nudge-cronp`）は **停止（スケール0 / スケジュール停止）**。
   - `OPENAI_API_KEY` を cron サービスから外す（最終安全策）。
   - さらに **手動起動経路も止める**: `/api/admin/trigger-nudges` と `.github/workflows/trigger-commander.yml`。
5) **DBテーブル整理は“削除”ではなく“段階的廃止”でやる（即drop禁止）**
   - まず「参照元コード/ジョブ/ルート」を洗い出してから deprecate → migrate → drop の順。

---

## 用語（このドキュメントの言葉を固定する）
### “通常状態ユーザー”
- ユーザーがアプリをインストールしてオンボードし、そのまま使っている状態。
- **Sign in with Apple をしていない**（`AppState.authStatus != .signedIn`）。
- Aniccaの現実の運用では、**これがほぼ全ユーザー**。

### “signedIn”
- iOS側で Sign in with Apple を完了して `AppState.authStatus == .signedIn(...)` になっている状態。
- ここは「RevenueCatの匿名/非匿名」とは別軸。Aniccaアプリ内部のログイン状態の話。

以後、「匿名」という言葉は誤解を招くので使わない。**“通常状態ユーザー（= 実質全員）”**で統一する。

## 1. 何が起きたか（Incident）

### 症状
- 1.6.3（TestFlight/提出ビルド）で、ユーザーがアプリを開かないと通知が途切れる/届かない。

### 根因（prod）
- APNs送信ジョブは `push_tokens.profile_id(UUID)` を軸に、`mobile_profiles` から `struggles` を集める。
- ところが一部で `mobile_profiles.user_id` が UUID ではなく **device_id文字列**のまま残り、
  `profileId -> mobile_profiles(userId)` の参照が外れて `struggles` が空扱いになり送信スキップ。

### 実際の修復（prod）
- `push_tokens.device_id` と一致する `mobile_profiles.device_id` をjoinし、`mobile_profiles.user_id` を `push_tokens.profile_id` に同期（バックフィル）。

---

## 2. 1.6.3 APNs Problem通知の実装SSOT

### Backend（送信）
- `apps/api/src/jobs/problemNudgeApnsSenderJob.js`
  - `push_tokens`（env別）を読む
  - `user_settings` で timezone/lang を読む
  - `mobile_profiles.profile.struggles`（fallbackで `profile.problems`）を読む
  - free/pro を **server-side**で判定し、
    - free: 1日3枠
    - pro: 選択problemの全スロット
  - `nudge_deliveries` と `nudge_delivery_sends` にログを残し、APNsへ送る

### iOS（token登録）
- `aniccaios/aniccaios/Services/PushTokenService.swift`
  - `/api/mobile/push/token` に token を登録
  - serverが `remoteProblemNudgesEnabled=true` を返した時だけローカルProblem通知を止める

### iOS（ローカル通知）
- `aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift`
  - entitled かつ remote enabled の場合はローカル通知をスキップ
  - free はローカルFree枠を維持

---

## 3. 2026-02-17 に入れた修正（コード）

### (A) APNs送信ジョブの耐障害化
- `apps/api/src/jobs/problemNudgeApnsSenderJob.js`
  - `mobile_profiles` の取得を `userId(profileId)` だけでなく `deviceId(in tokens)` でも拾う
  - `user_traits.struggles` を fallback として使用

### (B) token登録時のデータ整合（再発防止）
- `apps/api/src/routes/mobile/push.js`
  - `/api/mobile/push/token` で `mobile_profiles.user_id` を `profile_id(UUID)` に同期

### (C) profile保存時のUUID正規化
- `apps/api/src/services/mobile/profileService.js`
  - `resolveProfileId(userId)` が取れればUUIDに正規化
  - 取れなければ `ensureDeviceProfileId(deviceId)` でUUIDを作る

### デプロイ状況
- **production**: `main` 自動デプロイ（コミット: APNs修正）
- **staging**: `dev` 自動デプロイ（同コミットが staging にも反映済み）

---

## 4. 重要: 購読（RevenueCat）同期のバグ可能性

### 現状（iOS）
- `aniccaios/aniccaios/Services/SubscriptionManager.swift` の `syncNow()` に以下がある:
  - `guard case .signedIn(let credentials) = AppState.shared.authStatus else { return }`

意味:
- **通常状態ユーザー（= 実質ほぼ全員）**は、RevenueCatの購入状態をBackendに同期しない（ここで `return` する）。
- iOS UI上はRevenueCat SDKでPro表示できても、**Backendの `user_subscriptions` が更新されない**。

### なぜ 1.6.2 は大丈夫で、1.6.3 で問題化する？
- **1.6.2**: ローカル通知中心なので、Pro/Free判定は端末内RevenueCat SDKだけで完結しやすい。
- **1.6.3**: APNsの送信量をserverが決めるため、server側でPro/Free判定が必要。
  - そのSSOTが `user_subscriptions`。
  - 匿名ユーザーがsyncしないと `user_subscriptions` がfreeのままになり得る。

### Backend 側の同期エンドポイント
- `POST /api/billing/revenuecat/sync`
  - `apps/api/src/api/billing/revenuecatSync.js`
  - `user-id` ヘッダ（または auth.sub）を RevenueCat の `app_user_id` として問い合わせる。

重要:
- この設計のままだと、匿名ユーザーの正しい `app_user_id`（RevenueCatのanonymous ID）を Backend に送る必要がある。
- さらに、APNs送信ジョブは `profileId(UUID)` 単位で動くので、
  `user_subscriptions.user_id` は **UUID(profileId)** をSSOTにするのが自然。
  - つまり `app_user_id(text)` と `profile_id(uuid)` のマッピングが必要。

### 実施すべき修正（決定）
1) iOS: `syncNow()` の signedInガード撤去
- **通常状態ユーザーでも** `POST /billing/revenuecat/sync` を叩く（= 全ユーザーで同期する）
- `user-id` は `Purchases.shared.appUserID` を使う（通常状態でも必ずある）
- `device-id` は従来通り `AppState.shared.resolveDeviceId()` を送る
- 目的: **サーバが `user_subscriptions` を最新化できるようにして、APNs送信量（free/pro）を正しく決める**

2) Backend: `revenuecat/sync` で取得した entitlement を、
- その `app_user_id` のまま `user_subscriptions.user_id` に保存しない
- **対応する profileId(UUID) を解決して、UUID側に保存**する
  - 例: `revenuecat_app_user_id_map` のようなテーブルを新設し、
    `app_user_id -> profile_id` を保持

### 重要（この修正が入った後のUX）
- 通常状態のProユーザー: サーバがpro判定できるようになり、**APNs送信量がPro枠**になる
- 通常状態のFreeユーザー: サーバがfree判定でき、**APNs送信量がFree枠**のまま
- ユーザーの体験としては「通知タップしなくても毎日届く」が安定する

---

## 5. `subscription_events` が0件の意味
### 事実（2026-02-17 時点のDB）
- prod: `subscription_events` は 0件
- staging: `subscription_events` は 0件

### 解釈
- **`subscription_events` が0件 = RevenueCat webhookが来ていない、とは断定できない**。
  - 理由: そもそも webhook handler が `subscription_events` に insert していない実装の可能性があるため。

推奨:
- webhook到達確認のために、
  - `subscription_events` に必ず1行insertする
  - もしくは別の監査ログ（ops_events等）に記録

---

## 6. LLM生成 cron（generateNudges.js）を止めるべきか

### 事実
- `apps/api/src/jobs/generateNudges.js` は `OPENAI_API_KEY` 必須で実行され、LLM参照あり。
- `apps/api/railway.toml` の `startCommand`:
  - `CRON_MODE == nudges` のとき `node src/jobs/generateNudges.js`

### Railway サービス（production）
- `nudge-cronp`:
  - `CRON_MODE=nudges`
  - `OPENAI_API_KEY` 設定あり
  - => **LLM生成が走る構成**

- `nudge-cron`:
  - `CRON_MODE=true`（nudges ではない）
  - => `generateNudges.js` は起動しない（少なくともその条件分岐では）

### 手動起動経路
- `POST /api/admin/trigger-nudges` が存在（`apps/api/src/routes/admin/triggerNudges.js`）
- GitHub Actions で `workflow_dispatch` から叩ける（`.github/workflows/trigger-commander.yml`）

### 結論（決定）
- 「モバイル通知はAPNs+ルールベースでいく」方針なら、
  - **`nudge-cronp` を停止**（cron/サービス削除/スケール0 など）
  - **手動トリガー経路（/api/admin/trigger-nudges, trigger-commander.yml）も停止**

理由:
- cron停止だけだと、手動トリガーでLLM生成が起動できる状態が残る。

補足:
- **`generateNudges.js` のファイル自体は、いきなり削除しない（他からimport/参照されてる可能性がある）。**
- まずは「起動経路を遮断」→「LLMを物理的に呼べない（OPENAIキー無し）」→ それでも不要なら参照調査後に削除、の順。

---

## 7. DBテーブル: 何を使っていて、何を使っていないか

### 7.1 1.6.3 APNs Problem通知 + 課金判定で必須（使っている）
- `profiles`
- `mobile_profiles`
- `user_settings`
- `push_tokens`
- `nudge_deliveries`
- `nudge_delivery_sends`
- `user_subscriptions`
- `user_traits`（fallback）

### 7.2 使っていない/未実装に近い（ただし「即削除」は禁止）
- `subscription_events`（現状0件、書き込み実装なし）

注意:
- DBには他にも多数のテーブルがあるが、それらは Ops / 投稿 / 研究 / 解析 / 過去機能のSSOT。
- **削除は“混乱解消”ではなく“本番破壊”になり得る**ため、別途「削除計画（参照調査→移行→drop）」として切り出す。

### 7.3 DB全テーブルの現状（2026-02-17）
prod（44 tables）:
- `_prisma_migrations`, `agent_audit_logs`, `agent_posts`, `bandit_models`, `daily_metrics`, `feeling_sessions`, `habit_logs`, `hook_candidates`, `initiatives`, `memory_items`, `mobile_alarm_schedules`, `mobile_profiles`, `mobile_voip_tokens`, `monthly_vc_grants`, `notification_schedules`, `nudge_deliveries`, `nudge_delivery_sends`, `nudge_events`, `nudge_outcomes`, `ops_events`, `ops_mission_steps`, `ops_missions`, `ops_policy`, `ops_proposals`, `ops_reactions`, `ops_trigger_rules`, `profiles`, `push_tokens`, `realtime_usage_daily`, `refresh_tokens`, `research_items`, `schema_migrations`, `sensor_access_state`, `subscription_events`, `tiktok_posts`, `tokens`, `type_stats`, `usage_sessions`, `user_settings`, `user_subscriptions`, `user_traits`, `user_type_estimates`, `wisdom_patterns`, `x_posts`

staging（42 tables）:
- `_prisma_migrations`, `agent_audit_logs`, `agent_posts`, `bandit_models`, `daily_metrics`, `feeling_sessions`, `habit_logs`, `hook_candidates`, `initiatives`, `memory_items`, `mobile_profiles`, `monthly_vc_grants`, `notification_schedules`, `nudge_deliveries`, `nudge_delivery_sends`, `nudge_events`, `nudge_outcomes`, `ops_events`, `ops_mission_steps`, `ops_missions`, `ops_policy`, `ops_proposals`, `ops_reactions`, `ops_trigger_rules`, `profiles`, `push_tokens`, `realtime_usage_daily`, `refresh_tokens`, `research_items`, `schema_migrations`, `sensor_access_state`, `subscription_events`, `tiktok_posts`, `tokens`, `type_stats`, `usage_sessions`, `user_settings`, `user_subscriptions`, `user_traits`, `user_type_estimates`, `wisdom_patterns`, `x_posts`

### 7.4 「使ってないから消す」は今やらない（やるなら手順固定）
1) `apps/api/` と `aniccaios/` と OpenClaw 側の参照（SQL/ORM/生クエリ）を全検索
2) “参照ゼロ” を確認
3) 本番で「1リリース以上」未使用を観測（ログ/メトリクス）
4) 移行スクリプト or viewで互換性確保
5) その後に drop（migrationで管理）
