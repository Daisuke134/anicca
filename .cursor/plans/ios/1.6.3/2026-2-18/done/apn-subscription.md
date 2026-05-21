# 2026-02-17/18 APNs Problem Notifications + Subscription Sync + Cron Cleanup (SSOT)

## TL;DR
- **Problem通知は 1.6.3 から「サーバ送信(APNs)」がSSOT**（ローカルProblem通知は remote enabled 時は停止）。
- **prod/staging ともに反映済み**（Railwayの自動デプロイで API が更新される）。
- **Pro/Free判定はサーバ側がSSOT**。iOS側でPro表示でも、サーバ側で購読同期されていないと配信量がfree扱いになり得る問題は修正済み。
- **過去スロットのバックフィル送信は禁止**（HH:MM一致のみ送信）。
- **全配信停止の根因だった advisory lock を撤去**（Prisma接続プールと相性が悪く、ロックが残留して“今日0件”を起こすため）。
- LLM生成（generateNudges）は Problem通知とは別経路。止めるなら「cron停止 + 手動経路停止 + OPENAI_API_KEY除去」が安全。

## 状態（2026-02-18 時点）
- **production / API** と **staging / API** は再デプロイ済みで起動確認済み（起動ログ: Database initialized / API Server running）。
- prod で発生していた「Another worker holds advisory lock; skipping this tick」は、API再デプロイで解消。

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
- 1.6.3（TestFlight/提出ビルド）で、**Problem通知が届かない日が出る**（昨日来たのに今日は0件、など）。
- 一部端末で `BadDeviceToken` が出て、以後その token が無効化され配信できない。

### 根因（prod）
- APNs送信ジョブは `push_tokens.profile_id(UUID)` を軸に、`mobile_profiles` から `struggles` を集める。
- ところが一部で `mobile_profiles.user_id` が UUID ではなく **device_id文字列**のまま残り、
  `profileId -> mobile_profiles(userId)` の参照が外れて `struggles` が空扱いになり送信スキップ。

### 根因（prod 停止: advisory lock）
- APNs送信ジョブが `pg_try_advisory_lock` ベースで「他worker排他」をしていた。
- Prisma の接続プール環境では **lock/unlock が同一DBセッションで実行される保証がなく**、ロックが残留し得る。
- ロック残留中は毎分ジョブが `skipping this tick` になり、**全ユーザーに対して送信が止まる**。

### 根因（BadDeviceToken）
- **Xcodeで入れた開発ビルド**は APNs development token になり得る。
- それを prod（production APNs）宛に送ると Apple が `BadDeviceToken` を返す。
- サーバ側が token を無効化（disabled_at）すると、その端末は再登録まで届かない。

### 実際の修復（prod）
- `push_tokens.device_id` と一致する `mobile_profiles.device_id` をjoinし、`mobile_profiles.user_id` を `push_tokens.profile_id` に同期（バックフィル）。
- advisory lock が残留していた場合は「握っている接続」を terminate して即時復旧（緊急対応）。

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

## 3. 入れた修正（コード/運用）

### (A) APNs送信ジョブの耐障害化
- `apps/api/src/jobs/problemNudgeApnsSenderJob.js`
  - `mobile_profiles` の取得を `userId(profileId)` だけでなく `deviceId(in tokens)` でも拾う
  - `user_traits.struggles` を fallback として使用
  - **過去スロットのバックフィル禁止**（送信判定は HH:MM 一致のみ）
  - **advisory lock を撤去**（Prisma接続プールで残留し得て全停止を起こすため）

### (B) token登録時のデータ整合（再発防止）
- `apps/api/src/routes/mobile/push.js`
  - `/api/mobile/push/token` で `mobile_profiles.user_id` を `profile_id(UUID)` に同期

### (C) profile保存時のUUID正規化
- `apps/api/src/services/mobile/profileService.js`
  - `resolveProfileId(userId)` が取れればUUIDに正規化
  - 取れなければ `ensureDeviceProfileId(deviceId)` でUUIDを作る

### (D) 購読同期（RevenueCat）のSSOT化
- iOSは「通常状態ユーザーでも」購読同期を叩く（signedIn限定を撤去）。
- Backendは RevenueCat の `app_user_id` で entitlement を取得しつつ、DB保存は **profile_id(UUID)** 側へ寄せる（APNs送信ジョブの軸に合わせる）。
- Webhookは監査ログとして `subscription_events` を残せるようにする（到達/監査/デバッグ用途）。

### (E) LLM生成の誤起動防止
- cronサービス停止だけでなく、**手動起動経路も止める**（/api/admin/trigger-nudges と trigger-commander.yml）。
- OPENAIキーを cron サービスから外す（物理的に起動不能にする）。

### デプロイ状況
- **production**: `main` 自動デプロイ（コミット: APNs修正）
- **staging**: `dev` 自動デプロイ（同コミットが staging にも反映済み）

---

## 4. 重要: 購読（RevenueCat）同期のバグ（解決済み）

### 何が問題だったか
- iOS UIは RevenueCat SDK で Pro 表示できても、Backend が `user_subscriptions` を最新化できないと、APNs送信量が free 扱いに落ちる。
- 原因は「iOSが購読同期を signedIn 限定で return していた」ことと、「RevenueCatのIDとAniccaのprofile UUIDの軸ズレ」。

### なぜ 1.6.2 は大丈夫で、1.6.3 で問題化する？
- **1.6.2**: ローカル通知中心なので、Pro/Free判定は端末内RevenueCat SDKだけで完結しやすい。
- **1.6.3**: APNsの送信量をserverが決めるため、server側でPro/Free判定が必要。
  - そのSSOTが `user_subscriptions`。
  - 通常状態ユーザーがsyncしないと `user_subscriptions` がfreeのままになり得る。

### Backend 側の同期エンドポイント
- `POST /api/billing/revenuecat/sync`
  - `apps/api/src/api/billing/revenuecatSync.js`
  - `user-id` ヘッダ（または auth.sub）を RevenueCat の `app_user_id` として問い合わせる。

### 解決方針（SSOTとして固定）
- iOSは常に `Purchases.shared.appUserID` を `user-id` として送る（通常状態ユーザーでも）。
- Backendは `device-id -> profile_id(UUID)` を解決し、保存は UUID 側に寄せる。
- これで「Proなのにfree配信」事故を防ぐ。

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

## 7. DBテーブル: 今回のAPNs Problem通知で使う最小セット（SSOT）
この章は「削除対象」を決めるためではなく、まず **“今回の通知配信に関係するSSOT”** を固定する。

- `push_tokens`: device_id / APNs token / profile_id(UUID) / disabled_at
- `user_settings`: timezone / language / notifications_enabled
- `mobile_profiles`: device_id / user_id(profile_id) / struggles(=ProblemType選択)
- `profiles`: プロフィール本体（mobile_profilesが参照）
- `user_subscriptions`: profile_id(UUID)単位の plan/status/expires（サーバがPro/Free判定）
- `nudge_deliveries`: “送るべきだった通知”のレコード（idempotency/監査）
- `nudge_delivery_sends`: 実際のAPNs送信の成否ログ（sent/failed と error）

## 8. 再発防止 Runbook（最短で原因特定する）
### 8.1 「今日届かない」を見たら最初に疑うもの
1) **全停止**（APNs sender job が回ってない）
   - APIログに `Another worker holds advisory lock` が出ていないか
   - `nudge_delivery_sends` が今日0件になっていないか
2) **token死**（BadDeviceToken等で disabled）
   - `push_tokens.disabled_at` / `last_error`
3) **購読同期ズレ**
   - `user_subscriptions` が profile_id(UUID) で active/pro か
4) **struggles空**
   - `mobile_profiles.user_id` が profile_id(UUID) に正規化されているか

### 8.2 検証マトリクス（事故を起こさない）
- prod検証: **TestFlight / App Store ビルドのみ**
- staging検証: **Xcode実機ビルドのみ（staging API向き）**
- 禁止: Xcodeビルドをprod APIに向ける（BadDeviceTokenで token を殺す）

## 9. 学び（次回の行動規範）
- Gitの状態より **Railway deploy commit hash とログ**が真実
- Prisma接続プールでの advisory lock は地雷（全停止クラス）
- APNsは「ビルド種別」と「環境」の整合が全て（TestFlight/App Store = prod, Xcode = staging）
- 時刻仕様（バックフィル禁止/連投禁止）はUXそのもの。仕様としてコードに固定する

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
