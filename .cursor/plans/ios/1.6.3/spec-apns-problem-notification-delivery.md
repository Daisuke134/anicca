# Anicca iOS 1.6.3 — APNs Problem Nudge Delivery Spec (P0)

作成: 2026-02-13  
対象: iOS `aniccaios/` + Backend `apps/api/` + Railway（dev → staging → production）  
目的: **ユーザーがアプリを開かなくても**、毎日・固定時刻に・**毎回違う**Problem Nudge通知が届き続ける状態を実現する（48h枯渇=ゼロ通知を根絶）。

---

## 0. End Goal（受け入れ条件 / Done Definition）

1. ユーザーが48時間以上アプリを開かなくても、通知が止まらない（枯渇しない）。
2. 通知は「ProblemTypeごとの固定スロット」で配信される（SSOT: iOS `ProblemType.notificationSchedule` と Backend `scheduleMap.js` が一致）。
3. 配信時刻は **ユーザーのローカルタイムゾーン**基準で固定される（SSOT: Backend `user_settings.timezone`）。未設定の場合は `UTC` を使用する。
4. free/pro の配信ルールが「通知アプリとしての常識」を満たす:
   - free: **アプリを開かなくても** 毎日必ず **合計3通**が届き続ける（端末ローカルpending枯渇に依存しない）
   - pro: 選択したProblemTypeに応じて増える（通常: `選択problem数 × 3/日`、`staying_up_late` は `×5/日`）
   - 上記は server-side で強制され、iOSの手動再スケジュール等に依存しない
5. **各ProblemType内**で、最初の14日間は通知本文（hook）と詳細（detail）が一切重複しない。
   - 通常: `14日 × 3回/日 = 42` variants
   - `staying_up_late`: `14日 × 5回/日 = 70` variants
6. `staying_up_late` の **00:00 / 01:00** は深夜専用文面（睡眠促進・切り上げ・健康リスク）である。
7. 6言語（`en/ja/es/fr/de/pt-BR`）すべてで成立する。
8. devでE2E（Maestro含む）まで通してから staging → production → App Store 提出に進む。

---

## 1. As-Is（現状 / なぜ壊れたか）

### 1.1 iOSはローカル通知（pending枯渇リスク）

- `aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift` は iOS pending通知の上限64に合わせて、**2-day window（今日 + 明日）**のみをスケジュールする。
  - `UNCalendarNotificationTrigger(... repeats: false)`
  - 多スロットの場合、最大64件に達する（32スロット × 2日）。
- ユーザーが48時間以上アプリを開かない場合、再スケジュールが走らず pendingが枯れて通知がゼロになる。

### 1.2 Backendは「生成」はするが「端末配信」はしない

- Railway cron `apps/api/src/jobs/generateNudges.js` は `nudge_events` に日次生成を保存するが、端末へPush（APNs）配信を行わない。
- iOSの `/api/mobile/nudge/today` は「ローカル通知の文面差し替え用」であり、アプリ非起動ユーザーへの継続配信を保証できない。

---

## 2. To-Be（目標アーキテクチャ）

### 2.1 方針（決定）

- **配信の土台**: APNs Remote Push（サーバが時刻になったら送る。free/pro問わず全ユーザー）  
- **文面生成**: ルールベース（決定論的）をSSOTにする  
- **LLM/Commander**: 品質アップ用のオプション（配信成功の前提にはしない）

ベストプラクティス上の整理（根拠）:
- local通知は「外部データ不要の時刻リマインダ」に向くが、pending上限の制約があるため「無限運用の主経路」に置くと壊れやすい。
- remote通知は「サーバが内容/タイミングを決める」用途に向き、配信はベストエフォートであるため、冪等・再送・監視で信頼性を上げる（本specの設計）。
参考（一次情報）:
- Apple: Notification Best Practices: https://developer.apple.com/library/archive/documentation/Performance/Conceptual/EnergyGuide-iOS/NotificationBestPractices.html
- Apple: Local and Remote Notification Programming Guide（APNs接続/JWTのベストプラクティス含む）: https://developer.apple.com/library/archive/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/CommunicatingwithAPNs.html

### 2.2 全体フロー

1. iOSがAPNs device tokenを取得する
2. iOSがBackendへ token を登録（dev/staging/prod環境別に保存）
3. Backendがcron/workerで「今送るべき」通知を抽出し、APNsへ送信
4. iOSは通知を表示し、タップでNudge Card（既存）に遷移する

### 2.3 free/pro 配信ポリシー（固定）

SSOT:
- ユーザーが選択したProblemType: `mobile_profiles.profile->'struggles'`（fallback: `profile->'problems'`）
- スロット定義: `shared/problem_notification_schedule.v1.6.0.json` → Backend `scheduleMap.js`
- free/pro判定: `getEntitlementState(profileId)`（server-sideで強制）

ポリシー:
- free:
  - 1日合計 **3通**（アプリ非起動でも継続）
  - 選択したProblemType群から「その日送る3スロット」をserverが選び、APNsで送る（選択ロジックは 5.3.1 に固定）
- pro:
  - 選択したProblemType群の **全スロット** を対象にAPNsで送る
  - 通常Problemは3/日、`staying_up_late` は5/日

重要:
- iOS側は「free/proで配信本数を変える」責務を持たない（server-sideで担保）。

---

## 3. 固定スロット（SSOT）

一次SSOT（固定）:
- `shared/problem_notification_schedule.v1.6.0.json`（順序付き配列）

派生物（固定）:
- iOS: `aniccaios/aniccaios/Models/ProblemType.swift` `notificationSchedule`（共有JSONと完全一致すること）
- Backend: `apps/api/src/agents/scheduleMap.js` `NEW_SCHEDULE_MAP`（共有JSONと完全一致すること）

Timezone SSOT:
- Backend `user_settings.timezone`（IANA TZ, 例: `Asia/Tokyo`, `America/Los_Angeles`）

### 3.1 NEW_SCHEDULE（v1.6.0+）

NOTE: この表は読みやすさのためのスナップショットであり、一次SSOTは `shared/problem_notification_schedule.v1.6.0.json` とする。

| ProblemType | Slots |
|---|---|
| staying_up_late | 20:00 / 22:00 / 23:30 / 00:00 / 01:00 |
| cant_wake_up | 06:00 / 06:45 / 07:15 |
| self_loathing | 08:00 / 13:00 / 19:00 |
| rumination | 08:30 / 14:00 / 21:00 |
| procrastination | 09:15 / 13:30 / 17:00 |
| anxiety | 07:30 / 12:15 / 18:45 |
| lying | 08:15 / 13:15 / 18:15 |
| bad_mouthing | 09:30 / 14:30 / 19:30 |
| porn_addiction | 20:30 / 22:30 / 23:45 |
| alcohol_dependency | 16:00 / 18:00 / 20:15 |
| anger | 07:45 / 12:30 / 17:30 |
| obsessive | 09:00 / 13:45 / 18:30 |
| loneliness | 10:00 / 15:00 / 19:45 |

---

## 4. 文面のユニーク性（14日重複ゼロ）

### 4.1 要件

- 各ProblemTypeについて、`dayIndex in [0..13]` と `slotIndex in [0..slotsPerDay-1]` の全組み合わせで
  - `hook` が全て一意
  - `detail` が全て一意
- `staying_up_late` の `00:00 / 01:00` は深夜専用（必ず睡眠促進に寄せる）

### 4.2 決定論的インデックス（Server SSOT）

Server側は iOSと同じ概念で day/slot を決め打ちする（DB履歴不要）。

- `variantIndex = dayIndex * slotsPerDay + slotIndex`
  - 通常: `0..41`（42件）
  - 夜更かし: `0..69`（70件）

備考:
- ここでは「14日間完全ユニーク」を保証するため、**mod演算による循環は使わない**（最初の14日間は循環させない）。
- 15日目以降は `variantIndex % variantCount` で循環してよい（将来拡張で28日対応などにスケール可能）。

#### 4.2.1 dayIndex（day0のSSOT / 固定）

`dayIndex` の基準点（day0）を仕様として固定する。

- `nudge_day0_local_date` をSSOTとして永続化する（提案: `user_settings.nudge_day0_local_date`）。
- 初回確定ロジック（固定）:
  1. `user_settings.timezone`（IANA TZ）が **確定していること**（iOSが `x-timezone` を送る）
  2. `day0 = local_date(profiles.created_at at timezone)` を計算し、`user_settings.nudge_day0_local_date` がnullなら保存
- `dayIndex = max(0, effective_delivery_day_local - nudge_day0_local_date)`（日数差）
- timezone更新があっても **day0は不変**（timezoneは配信時刻計算のみ更新する）

例外（救済 / 固定）:
- 既存ユーザー等で timezone 未確定のままday0を計算せざるを得ない場合は `UTC` で仮確定し、`user_settings.nudge_day0_source='utc_fallback'` を保存する。
- `utc_fallback` の場合に限り、timezoneが初めて確定したタイミングで **1回だけ** day0を再計算して上書きしてよい（以後は不変）。

#### 4.2.2 staying_up_late の日跨ぎ（effective_delivery_day_local / 固定）

`staying_up_late` は 00:00/01:00 を含むため、「カレンダー日付」ではなく「夜の論理日付」をSSOTにする。

- `effective_delivery_day_local` の定義:
  - `problem_type == staying_up_late` かつ `scheduled_time in {"00:00","01:00"}` の場合:
    - `effective_delivery_day_local = local_date(now_local - 1 day)`
  - それ以外:
    - `effective_delivery_day_local = local_date(now_local)`
- `nudge_deliveries.delivery_day_local` は **必ず effective_delivery_day_local を保存**する。
- 冪等キー（`unique(profile_id, problem_type, scheduled_time, delivery_day_local)`）はこのeffective日付に対して成立する。

### 4.3 6言語ローカライズ（Serverカタログ）

APNsの通知本文はサーバが決定して送るため、ローカライズ資産は **Backend側に持つ**。

- 形式: `apps/api/src/modules/problem_nudges/catalog/{lang}.json`
- スキーマ（固定）:
  - `schemaVersion: 1`
  - `titles: { [problemType]: string }`
  - `hooks: { [problemType]: string[] }`
  - `details: { [problemType]: string[] }`
- 配列長（固定）:
  - 通常: `hooks[problemType].length == 42` かつ `details[problemType].length == 42`
  - `staying_up_late`: `hooks.staying_up_late.length == 70` かつ `details.staying_up_late.length == 70`

深夜専用の割り当て（固定）:
- `staying_up_late` は **単一の70要素配列**で運用する（別プールは作らない）。
- staying_up_lateのslotIndexは `20:00=0 / 22:00=1 / 23:30=2 / 00:00=3 / 01:00=4` とする。
- `variantIndex = dayIndex*5 + slotIndex` のうち、slotIndexが `3/4`（= 00:00/01:00）に対応する要素は **深夜専用の文面**で埋める。

---

## 5. Backend設計

### 5.1 DB Schema（migration対象）

#### 5.1.1 `push_tokens`

- `id uuid pk`
- `profile_id uuid not null`（SSOT: `profiles.id`）
- `device_id text not null`（iOS identifierForVendor 由来）
- `token text not null`
- `platform text not null`（`ios`）
- `env text not null`（`dev|staging|prod`）
- `disabled_at timestamptz null`
- `last_error text null`
- `updated_at timestamptz not null`
- `created_at timestamptz not null`

制約:
- `unique(device_id, env)`（upsertキー）
- `unique(token, env)`（token重複登録の掃除を容易にする）

#### 5.1.2 `nudge_deliveries`（送信ログ / 冪等）

- `id uuid pk`
- `profile_id uuid not null`
- `problem_type text not null`
- `scheduled_time text not null`（`HH:MM`）
- `delivery_day_local date not null`（ユーザーTZの日付）
- `timezone text not null`（IANA TZ。SSOT: `user_settings.timezone`）
- `lang text not null`
- `variant_index int not null`
- `message_title text not null`
- `message_body text not null`
- `message_detail text not null`
- `status text not null`（`queued|sent|failed`）
- `apns_id text null`（返ってくるAPNs message-id）
- `error text null`
- `created_at timestamptz not null`
- `sent_at timestamptz null`

制約（冪等キー）:
- `unique(profile_id, problem_type, scheduled_time, delivery_day_local)`  
  → 同一ユーザー同一枠の二重送信を禁止する（再実行しても1回だけになる）。

#### 5.1.3 `nudge_delivery_sends`（端末ごとの送信ログ / 冪等）

背景:
- 1ユーザー（=1 profile_id）が複数端末（複数 `push_tokens`）を持つことがある。
- `nudge_deliveries` を「不変スナップショット（コンテンツ）」として維持したまま、**端末ごとの送信成否**を追跡する必要がある。

主要カラム:
- `id uuid pk`
- `delivery_id uuid not null`（FK → `nudge_deliveries.id`）
- `push_token_id uuid not null`（FK → `push_tokens.id`）
- `status text not null`（`queued|sending|sent|failed`）
- `apns_id text null`
- `error text null`
- `attempt_count int not null`
- `last_attempt_at timestamptz null`
- `next_attempt_at timestamptz null`
- `sent_at timestamptz null`

制約（冪等キー）:
- `unique(delivery_id, push_token_id)`

### 5.2 API

#### 5.2.1 `POST /api/mobile/push/token`

目的: iOSがdevice tokenを登録する。

入力:
- Headers:
  - `device-id`: required
  - `user-id`: optional（既存互換のため受け取るが、token紐付けの根拠にはしない）
  - `authorization`: optional（Bearerがあれば優先。token紐付けは auth → profile_id で行う）
  - `x-timezone`: optional（IANA TZ。例: `America/Los_Angeles`。受領できた場合 `user_settings.timezone` を更新してSSOTにする）
  - `x-lang`: optional（例: `en`, `ja`, `pt-BR`。受領できた場合 `user_settings.language` を更新してSSOTにする）
- Body:
  - `token`: string（hex）
  - `platform`: `"ios"`（省略可。iOSのみ想定）

出力:
- `200 { ok: true, remoteDeliveryEnabled: boolean, remoteProblemNudgesEnabled: boolean }`

フラグ定義（固定）:
- `remoteDeliveryEnabled`: サーバ側のAPNs設定が正しいか（= APNs probeが通るか）。インフラ都合の可否。
- `remoteProblemNudgesEnabled`: **ユーザー単位**で「Problem NudgesをAPNs配信してよい」か。
  - 本仕様では free/pro問わずAPNsが主経路のため、基本は `remoteProblemNudgesEnabled == remoteDeliveryEnabled`
  - fail-closed（例: APNs probe失敗時は `false`）
  - 目的: iOSが「APNsが死んでいるのにローカルも止める」等で **通知ゼロ（blackout）**になる事故を防ぐ

セキュリティ要件（固定）:
- `user-id` ヘッダは「本人性」の根拠にしない（なりすまし対策）
- `authorization` がある場合: `auth.sub` → `resolveProfileId` で `profile_id` を確定
- `authorization` がない場合: `ensureDeviceProfileId(device-id)` で `profile_id` を確定（deviceに紐付けた匿名プロフィール）
- **上書き防止**:
  - `authorization` がない場合、既存の `push_tokens.profile_id` を別UUIDへ付け替えない（device-id由来の同一profileにのみ紐付ける）。
  - `authorization` がある場合のみ、匿名→ログイン移行として `profile_id` の付け替えを許可する。
- tokenはログに出さない（マスク）
- tokenバリデーション: `^[0-9a-fA-F]{64}$`（64 hex）を満たさないものは400
- レート制限: **IP + device-id** の二重適用（device-id回転による回避を防ぐ）

保存/更新ルール（固定）:
- upsertキーは `device_id + env` とする（1端末=1 token / env）
- upsert成功時は必ず `disabled_at=NULL, last_error=NULL` に戻す（再登録で復活）
- `unique(token, env)` 競合時（同tokenが別deviceに紐付いている）:
  - 競合している既存行を **削除**（または無効化+token差し替え）して一意制約を解消する
  - その後、`device_id + env` のupsertで現在端末の行にtokenを保存する

実装規約（固定）:
- 上記の競合解決はトランザクション内で行う（delete/disable → upsert の順）。

#### 5.2.2 `GET /api/mobile/nudge/delivery/:id`

目的: 通知タップ後にNudge Card表示用の詳細（detail等）を取得する（payload肥大化を避ける）。

入力:
- Headers: `authorization` optional（Bearerがあれば優先）、`device-id` required（匿名も許可）
- Path: `id` = `nudge_deliveries.id`（UUID）

出力:
- `200 { id, problemType, scheduledTime, deliveryDayLocal, lang, title, hook, detail, variantIndex }`

SSOT（固定）:
- `title/hook/detail` は `nudge_deliveries.message_title/message_body/message_detail` を返す（送信時スナップショット）。catalog更新で過去の表示が変わらないことを保証する。

認可（固定）:
- `device-id` は必須（匿名も許可）。
- まず `push_tokens(device_id, env)` を引き、`disabled_at IS NULL` の token が存在すること（存在しない場合は401）。
- `authorization` がある場合:
  - `resolveProfileId(auth.sub)` を解決できること（解決できない場合は401）
  - 解決した `profile_id` が `push_tokens.profile_id` と一致すること（不一致は403）
- その上で `nudge_deliveries(id, profile_id)` を取得し、存在すれば200、無ければ404

fail-closed（固定）:
- `PUSH_ENV/APNS_ENV/RAILWAY_ENVIRONMENT*` が未設定の場合は503（env推測で進めない）

#### 5.2.3 `POST /api/admin/test/nudge-delivery`（dev専用 / Maestro seed）

目的: Maestro E2Eの前段で、テスト用の `nudge_deliveries` を1件作成して `messageId` を返す。

認証（固定）:
- `requireInternalAuth`（`Authorization: Bearer $INTERNAL_API_TOKEN`）

入力:
- Body:
  - `deviceId`: string（推奨。E2Eの認可を壊さないため device-id 基準でseedする）
  - `profileId`: uuid（任意。deviceIdを指定しない場合のみ使用）
  - `problemType`: string
  - `scheduledTime`: `HH:MM`
  - `timezone`: IANA TZ（例: `Asia/Tokyo`）
  - `lang`: `en|ja|es|fr|de|pt-BR`
  - `deliveryDayLocal`: `YYYY-MM-DD`（テストで固定したい場合のみ。省略時はserverがeffective日付を計算）

出力:
- `200 { id: "<uuid>" }`

備考:
- このendpointはdev/stagingでのみ有効化し、productionでは無効化する（Feature Flag）。
 - `deviceId` が指定された場合は `ensureDeviceProfileId(deviceId)` を使って `delivery.profile_id` を確定する（E2Eで `GET /delivery/:id` が404にならないようにする）。

#### 5.2.4 送信ジョブ（HTTP endpointは不要。cronで実行）

目的: “今送るべきスロット”を抽出し、APNs送信する。

入力:
- env vars:
  - APNs credentials
  - `CRON_MODE=push_send` 等

出力:
- logs + `nudge_deliveries` 更新

### 5.3 送信抽出（ユーザーTZ基準）

ルール（固定）:
- “今”のUTC時刻から、対象ユーザーごとに `user_settings.timezone` でローカル時刻へ変換する。
- ローカル時刻の `HH:MM` がスロットに一致する場合に送る（cronは毎分推奨）。
- cron遅延/ドリフトに備えて **due window** を持つ（固定: `now_local` が `slot_time` 以上かつ `slot_time + 30min` 未満）。
  - window内での重複実行は、DBのunique + insert-first戦略で抑止する。
- DST取り扱い:
  - spring forward（存在しない時刻）: 次の有効時刻へ前倒しではなく **後ろ倒し**（例: 02:30が存在しない→03:00に送る）
  - fall back（同じ時刻が2回）: **最初の出現で1回だけ送る**（冪等キーが同一のため2回目は送られない）

対象ProblemType集合（固定）:
- SSOTは `mobile_profiles.profile->'struggles'`（fallback: `profile->'problems'`）。
- sender job は「そのユーザーが選択しているProblemType」に対してのみ送信する。

#### 5.3.1 free: 1日3通の選択ロジック（固定 / 決定論）

目的:
- freeでも「通知が止まらない」を満たしつつ、1日合計3通に抑える（server-sideで強制）。

入力:
- `problemTypes = struggles`（ユーザーが選んだProblemType）
- `scheduleMap = NEW_SCHEDULE_MAP`
- `timezone`
- `effective_delivery_day_local`（dayIndex計算に使用）

アルゴリズム（固定）:
1. `allSlots = buildFlattenedSlotTable(problemTypes, scheduleMap)` を作る（`scheduleMap.js` の helperをSSOTとして利用）
2. その日のターゲット時刻を `["09:00","14:00","20:00"]`（local）として定義する
3. 各ターゲット時刻に対して `allSlots` から「その時刻に最も近いスロット」を1つ選ぶ（重複は除外）
   - tie-break: `abs(minutesDiff)` が同じなら `scheduledTime` が早い方、さらに同じなら `problemType` のalphabet順
4. 3つ未満しか選べない場合は、残りを `allSlots` の時刻順で埋める（重複除外）
5. 選ばれたスロット（最大3）に対してのみ、以降の `nudge_deliveries` / `nudge_delivery_sends` の作成・送信を行う

保証:
- 選択されるスロットはユーザーの選択ProblemType群のスロットから選ばれる（無関係な固定文面にならない）
- 端末ローカルpendingに依存しない（アプリ非起動でも毎日届く）

lang（SSOT / 固定）:
- SSOT: `user_settings.language`（許容: `en|ja|es|fr|de|pt-BR`）
- `POST /mobile/push/token` で `x-lang`（推奨）を受け取り、whitelist正規化して `user_settings.language` を更新する（不正/欠損は `en`）
- sender job は `catalog[lang]` を使用し、欠損時は `en` へfallbackする

title（SSOT / 固定）:
- SSOT: `catalog[lang].titles[problemType]`
- sender job は `message_title=title`、`message_body=hook`、`message_detail=detail` を `nudge_deliveries` にスナップショット保存する

### 5.4 冪等・並列安全（実装ルール）

送信は「INSERTを先に行う」ことで並列実行に強くする（マルチデバイス対応）。

1. due候補（profile×problem×slot）を列挙
2. `nudge_deliveries` を **スナップショットとして** upsert（不変。二重作成しない）
3. 各 `push_tokens`（端末）ごとに `nudge_delivery_sends` を upsert（`unique(delivery_id, push_token_id)`）
4. 送信は `nudge_delivery_sends` を `updateMany` で claim してから実行（並列起動でも二重送信しない）
5. 成功→`nudge_delivery_sends.status=sent`、失敗→`failed + nextAttemptAt`（config/authは短いbackoff + runを停止）

これにより、cronが二重起動/並列化されても二重送信が発生しない。

### 5.5 APNs 認証・環境差分（固定）

方式:
- APNs token-based auth（.p8）を使用する。

必要な環境変数（Railway）:
- `APNS_TEAM_ID`
- `APNS_KEY_ID`
- `APNS_PRIVATE_KEY_P8`（改行を含む。Railwayの設定方法もrunbookに明記）
- `APNS_TOPIC`（iOS Bundle ID）
- `APNS_ENDPOINT` = `development|production`（**必須**。NODE_ENVから推測しない）

dev/staging/prod マッピング:
- dev: `APNS_ENDPOINT=development`（APNs sandbox）
- staging: 原則 `development`（必要に応じてTestFlight検証時のみ `production`）
- production: `APNS_ENDPOINT=production`

整合性ガード（固定）:
- sender job 起動時に `PUSH_ENV`（dev/staging/prod）と `APNS_ENDPOINT` の矛盾を検知したら **送信しない**（設定不備でtokenをdisableしない）。

必須ヘッダ:
- `apns-topic: ${APNS_TOPIC}`
- `apns-push-type: alert`
- `apns-priority: 10`（即時表示）

### 5.6 APNs エラー処理（固定）

APNsレスポンスの `reason` に応じて処理を分岐する。

- `Unregistered`: 端末側でtokenが無効化された（アプリ削除など）。`push_tokens.disabled_at` を設定して以降の送信対象から除外する（再登録で復活できる）。
- `BadDeviceToken`, `DeviceTokenNotForTopic`: **設定/環境差分で誤検知し得る**ため、tokenは無効化しない（`last_error` を保存しつつ送信継続は止めない。必要なら監視で可視化）。
  - `POST /mobile/push/token` のAPNs probeでは、この2つを「authはOK」と判定するために使う。
- `TooManyRequests`（429）/ `InternalServerError`（500）など: exponential backoffで再試行（ただし冪等キーにより二重送信は発生しない）
- `Forbidden`（403）/ `BadTopic` など: 認証・設定異常として即アラート。`nudge_deliveries.status=blocked` にして **そのrunを即停止**（大量失敗のスパムを防ぐ）

監視追加（最低限）:
- failure reason別カウント
- 無効token削除数
- 403系の即時アラート

---

## 6. iOS設計（APNs受信 + token登録）

### 6.1 token取得・登録

- `application(_:didRegisterForRemoteNotificationsWithDeviceToken:)`
  - tokenをhex化
  - `POST /api/mobile/push/token` へ送信
  - `x-timezone` に端末のIANA timezoneを付与する（SSOT更新用）

必要なiOS実装要件（固定）:
- `UNUserNotificationCenter.current().delegate` を設定
- category `PROBLEM_NUDGE` を登録（既存のNudge Card導線と一致させる）
- 起動経路（foreground/background/killed）で tap ルーティングが一致する（`didReceive` + launchOptions）
- **表示SSOT（固定）**: Push起点（`messageId`）で開くNudge Cardは、必ず `GET /api/mobile/nudge/delivery/:id` の `title/hook/detail` を表示する。ローカルの `ProblemType` 表示名は使わない（fallback時のみ `aps.alert.title/body` を使う）。

ローカル配信との共存（固定）:
- 1.6.3以降、ProblemTypeの通知は **APNsを主経路**とし、ローカル通知の「無限運用」は前提にしない（pending枯渇の温床になるため）。
- iOSは `POST /mobile/push/token` のレスポンス `remoteProblemNudgesEnabled` が `true` のとき
  - ローカルのProblem通知（`ProblemNotificationScheduler`）をキャンセルする（重複防止 / 移行の掃除）
- `remoteProblemNudgesEnabled` が `false` の場合:
  - blackout回避のため、既存のローカルProblem通知が残っていても削除しない（ただし、主経路としては扱わない）

重要（既存ユーザーへの現実）:
- APNsは「トークン登録が完了している端末」にしか届かない。既存ユーザーも **アップデート後に一度だけ起動**してtoken登録が走る必要がある。
- 以後はアプリ非起動でも通知は継続する（本specの目的）。

### 6.2 通知ペイロード（提案）

APNs payload（例）:

```json
{
  "aps": {
    "alert": { "title": "…", "body": "…" },
    "sound": "default",
    "category": "PROBLEM_NUDGE",
    "thread-id": "problem_nudge",
    "mutable-content": 0
  },
  "schemaVersion": 1,
  "problemType": "anxiety",
  "scheduledTime": "07:30",
  "deliveryDayLocal": "2026-02-13",
  "lang": "en",
  "variantIndex": 5,
  "messageId": "uuid"
}
```

iOS側は tap 時に `messageId`（= `nudge_deliveries.id`）を使い、`GET /api/mobile/nudge/delivery/:id` でdetailを取得してNudge Card表示へ接続する。
ネットワーク不可の場合は `aps.alert.body` を暫定表示し、次回オンライン時に詳細を取得できるようにする（クラッシュしない）。

---

## 7. テスト（TDD必須 / 80%+）

### 7.1 Backend Unit（Vitest）

1. 6言語×全ProblemType×day0-13×全slot で `hook` が重複しない
2. 同条件で `detail` が重複しない
3. `staying_up_late` の 00:00/01:00 に該当するvariantが「深夜専用」条件を満たす（ルール/タグ/キーワード）
4. 文字数・空文字などの境界条件
5. catalog完全性: スキーマ/配列長/空文字なし/欠損langはenへfallback

### 7.2 Backend Integration（Vitest + prisma mock / test DB）

1. `POST /mobile/push/token` upsert（登録/更新）
2. 送信ジョブの due抽出が正しい（ユーザーTZ境界 + DST含む）
3. 冪等: 同一枠を二重送信しない（unique制約 + ロジック）
4. failed→retry で sent になる（再送してもsent済みは再送しない）

### 7.3 iOS Unit（XCTest）

1. device token → hex 変換 + 登録API呼び出し（mock）
2. push payload のデコード/取り出し（problemType等）

### 7.4 Maestro E2E

方針: OS通知UIはフレークしやすいので、**Maestroの主E2Eは「通知tap相当の内部導線」**で安定化する。`simctl push` の疎通は別スモークで担保する。

前提（固定）:
- Debug/CIビルドでのみ `anicca://debug/*` deep link を有効化する（本番ビルドでは無効）。
- Maestroの前段で「テスト用delivery」を作成し、`messageId` を取得できること。
- Maestro/E2Eは `device-id` が固定されていること（認可の整合のため）。

device-id 固定（固定）:
- iOSに `UI_TESTING` launchArgument が入っている場合、`AppState.resolveDeviceId()` は固定値 `UI_TEST_DEVICE_ID` を返す（E2E用）。
- Maestroのseedは常に `deviceId=UI_TEST_DEVICE_ID` を使う。

テスト用delivery生成（固定）:
- dev専用の内部エンドポイント `POST /api/admin/test/nudge-delivery`（`requireInternalAuth`）で `nudge_deliveries` を1件作成し、`id` を返す。
- Maestroは `runScript` でこのendpointを叩き、返ってきた `messageId` を環境変数として後続ステップへ渡す。

`runScript`（例）:
```bash
# INTERNAL_API_TOKEN はCI/ローカルのSecretで注入
MESSAGE_ID=$(curl -sS -X POST "$ANICCA_PROXY_BASE_URL/api/admin/test/nudge-delivery" \
  -H "Authorization: Bearer $INTERNAL_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "deviceId": "UI_TEST_DEVICE_ID",
    "problemType": "staying_up_late",
    "scheduledTime": "00:00",
    "timezone": "Asia/Tokyo",
    "lang": "en"
  }' | jq -r '.id')
export MESSAGE_ID
```

1. Deep link（例: `anicca://debug/pushTap?messageId=$MESSAGE_ID`）で「通知tap相当」を実行
2. `NudgeCardView` が表示される（識別子で検証）
3. 代表2言語（ja/en）で同じテストを回す
4. `staying_up_late` 00:00/01:00 の深夜専用文面が出るケースを1つ通す

補助スモーク（Simulator限定）:
- `simctl push <bundleId> <payload.apns>` を実行し、通知が表示されることだけ確認する（CIで不安定なら手動でも可）。

---

## 8. SSOT整合（スロット一致の自動検査）

要求:
- iOSの `ProblemType.notificationSchedule` と Backendの `NEW_SCHEDULE_MAP` の一致を **テストで検出**できること。

実装方針（固定）:
- 共有カノニカルを `shared/problem_notification_schedule.v1.6.0.json` として追加し、
  - Backendはそれを読み込む（またはテストで一致検査する）
  - iOSもそれをテストターゲットに同梱し一致検査する

共有カノニカルの形（固定）:
- `{"version": "...", "schedule": { "<problemType>": ["HH:MM", ...] } }`
  - `schedule[problemType]` は **順序付き配列**（slotIndexは配列indexのみを使用）
- Backend/iOSのテストは「集合一致」ではなく **完全一致（順序含む）**を検証する

---

## 9. Rollout（dev → staging → production）

1. dev
   - migration適用
   - token登録確認
   - cron/workerをdevで起動し、`nudge_deliveries` とログで送信確認
   - iOS devビルドで受信確認（simulator + 実機）
   - Maestro E2E をdevで通す
2. staging
   - 同様に確認（環境変数とAPNs sandbox/productionの差を検証）
3. production
   - 監視（送信成功率、失敗率、重複率0）
4. App Store提出
   - 1.6.3にAPNsが含まれることが前提（token登録が必要なため）

App Store再提出が必要か？（結論 / 固定）:
- **必要**。理由:
  - 根本原因は「iOSがローカル通知を2日分しか積まない」ことで、サーバだけ直しても、ユーザーが48h以上アプリを開かないとpendingが枯れてゼロ通知になる。
  - APNs token登録・tap導線（`messageId` → `GET /delivery/:id`）の実装はアプリ側に必要。

---

## 10. Monitoring（最低限）

- `nudge_deliveries` の `status` 集計（sent/failed）
- 冪等違反（unique衝突）件数（0であること）
- APNs error率（トークン無効、認証失敗、レート等）

---

## 11. Implementation Checklist（今日中に終わらせる）

- [ ] Backend migrations: `push_tokens`, `nudge_deliveries`
- [ ] Backend route: `POST /mobile/push/token` + tests
- [ ] Backend content catalog: 6言語、42/70、深夜専用（00/01）
- [ ] Backend sender job: due抽出、APNs送信、冪等、retry + tests
- [ ] iOS: token登録 + unit tests
- [ ] iOS: push tap → Nudge Card導線 + tests
- [ ] Maestro: simctl push → open → verify
- [ ] Railway dev deploy + staging + production runbook
