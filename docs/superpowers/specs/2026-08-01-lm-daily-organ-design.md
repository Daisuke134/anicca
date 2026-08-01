# Life Manager — DAILY organ 設計・残作業・UX（handover 可能な形で）

**Date**: 2026-08-01 · **Status**: 実装中 · **Repo**: canonical `Daisuke134/life-manager`
· **Branch**: `docs/two-earning-loops` · **Worktree**: `~/anicca/.worktrees/spec-two-loops`
· **App**: `apps/life-manager/`

**親 spec**: `2026-07-29-life-manager-finance-marketing-platform-design.md`（platform 全体・§7.4 Telegram
UI/UX・§10.2 Today・§12 Order 表）。あの Order 表は **runtime 移行の順序**であって daily 機能の順序ではない。
**daily の順序はこのファイルが正本**。

---

## 0. これを初めて読む agent へ（handover 前提。ここだけで作業に入れること）

| 質問 | 答え |
|---|---|
| これは何の製品か | **Telegram で完結する生活エージェント**。予定の時刻に呼び出し、家を出てから着くまで案内し、遅れたら相手に断りを入れる。ユーザーが持つ必要があるのは **スマホ1台だけ** |
| 誰が使うか | Dais（本人）→ 友達3人 → 有料の一般ユーザー。全員 **Telegram の中だけ**で完結する |
| コードはどこか | `apps/life-manager/`。`scheduler.js`（60秒 tick・呼び出し）· `lib/wake-filter.js`（鳴らす予定の選別・出発時刻の解決）· `lib/travel.js`（`[Travel]` block 生成）· `lib/late-notice.js`（遅刻連絡）· `lib/slash-command.js`（Telegram コマンド router） |
| **本番はどこで動くか** | ★ **Railway の `life-call` service** ★（`railway logs -s life-call`、link は `~/anicca-project` から）。ローカル compose（`life-manager-local-*` コンテナ）は **credential を持たない空の器**で、本番ではない（§1 参照）。全体図と folder tree = **§8** |
| データはどこか | Supabase。`lm_users` `lm_wake_log` `lm_travel_log` `lm_ask_log` `lm_user_locations` |
| 状態の見方（★実行可能★） | `set -a; . ~/.openclaw/.env; set +a` の後 `curl -s "$SUPABASE_URL/rest/v1/<table>?select=*&order=…&limit=3" -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"`。**鍵を stdout に出さない** |
| ★間違えやすい点★ | canonical は **`Daisuke134/life-manager`**。`anicca-project`(=anicca-products) の LM spec は写しで正本ではない。`~/.openclaw/skills/anicca-life-manager/` は OSS/BYOK 単身版であって本番ではない |
| 触ってはいけない | writer loop・記事・SNS・収益 loop（別 agent 担当）。physical / mental organ（親 spec Order 36、daily 出荷後） |

---

## 1. 実測（2026-08-01 06:41–07:00 JST、この session で自分が叩いた生の値）

### 1.1 ライブ位置は届いている（前 session の「未達」は誤診）

| 観測 | 実測値 |
|---|---|
| `lm_user_locations` | `observed_at=2026-07-31T21:41:01Z`、取得時刻 `21:41:15Z` = **14秒前**。`latitude=35.6796 / longitude=139.723085`、`source=telegram_live_location` |
| 逆ジオコード | `南元町, 新宿区, 東京都, 160-8484`（Nominatim）= 自宅と一致 |
| ★誤診の原因★ | 同じ行の `updated_at` は `2026-07-21T02:35:07Z` のまま。upsert が `observed_at` だけ更新している。**鮮度を見る列を間違えた** |

**規則**: 位置の鮮度は **`observed_at`**。`updated_at` を鮮度に使わない。

### 1.2 ★#1 呼び出し不発の原因（究明完了）★

| 手順 | 実行したこと | 出た結果 |
|---|---|---|
| a | ローカル compose の scheduler ログを読む | `[scheduler] PUBLIC_WSS not set — calls would have no media bridge URL; loop still runs but won't dial` |
| b | そのコンテナの env を実点検（`docker exec`） | `PUBLIC_WSS / LM_CALL_SECRET / TELNYX_API_KEY / TELNYX_CONNECTION_ID / GEMINI_API_KEY / SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / COMPOSIO_API_KEY / GOOGLE_API_KEY` **すべて MISSING** |
| c | 同ログの `[travel]` 行 | `[travel] started` はあるが `inserted=` の行が**1本も無い** |
| → | **ローカル compose は空の器**。Supabase 資格情報が無いので `supaUsers()` が空配列を返し、対象ユーザーが0人。**そもそも1度も呼び出しを評価していない**。テスト中に再起動したのはこの器であって、鳴らない側の主体ではなかった | |
| d | 本番 Railway `life-call` のログ | `[scheduler] started — tick every 60s, escalating wakes at T-10/5min`（PUBLIC_WSS 警告**なし** = 本番は設定済）· `[travel] uid=lm_784ad279- inserted=2 checked=10` ← **ユーザーが見た travel 挿入は本番の仕事** · `[late] uid=lm_784ad279- decision=late sent=false tg_message_id=513` |
| e | 本番ログに `WAKE T-` / `dial failed` があるか | **どちらも無い**。= 発信を試みてすらいない |
| f | `lm_users` の実列を確認 | `call_enabled` / `daily_automation_enabled` / `notifications_enabled` の**列自体が存在しない**（コードは `!== false` 判定なので undefined は通す = 抑制していない）。`wake_policy="travel-only"`、`paid=true` |
| g | `shouldWake` の条件（`lib/wake-filter.js:17-25`） | travel-only は「location があり、home と異なる」なら true。テスト予定（渋谷）は**通る** |
| h | ★Railway のデプロイ履歴★ | `bb11f4c7… | SUCCESS | 2026-08-01 01:23:35 JST` ← **試験の発火窓（T-10 = 01:25:30–01:27:30 / T-5 = 01:30:30–01:32:30）の直前に本番が再デプロイ＝再起動している** |

**結論（原因は2層ある）**

| 層 | 内容 | 証拠 |
|---|---|---|
| 直接原因 | 試験の発火窓の直前 **01:23:35 に本番 `life-call` が再デプロイされた**。comp 変数の設定が Railway の再デプロイを誘発している。新プロセスの起動と最初の tick が窓に間に合わなかった | 上記 h。加えて本番ログの `[late] decision=late` は「その tick が回った時には既に予定時刻を過ぎていた」ことを示す |
| ★構造原因（本体）★ | **発火窓が 2分しかないのに、tick 周期が保証されていない**。`scheduler.js:333` は `if (mins > lvl.min + 0.5 \|\| mins <= lvl.min - 1.5) continue;` = 各レベル約2分の窓。ところが同じ 60秒 tick に late / mental / care / diet が相乗りし、ユーザー毎に最大90秒の timeout を持つ。ユーザーが増えるほど周期は伸び、**窓を跨いだ瞬間に呼び出しは永久に失われる** | `scheduler.js:332-336`、同 tick 内の organ 群、本番ログに他ユーザーの `[care] status=history_unavailable` が毎 tick 出続けている |
| ★計測の穴★ | 窓を逃した呼び出しは **どこにも記録が残らない**。`claimWake` は発信直前にしか行われず、発信失敗時は `releaseWake` で claim を消す。だから `lm_wake_log` を見ても「鳴るはずだったのに鳴らなかった」が**存在しない事象として見える** | `scheduler.js:337-355` |

**棄却した仮説（再検討しないこと）**

| 仮説 | 棄却理由 |
|---|---|
| 深夜は意図的に抑制されている | `scheduler.js` に時間帯ガードは無い（旧 OpenClaw skill の `*/5 6-23` cron の記憶だった） |
| `wake_policy` / `shouldWake` の除外 | `travel-only` + 実在の venue = 通る（`wake-filter.js:17-25`） |
| ユーザー側のスイッチが OFF | `call_enabled` 等の列が **存在しない** |
| PUBLIC_WSS 未設定 | ローカルのみ未設定。本番は設定済（起動警告が出ていない） |
| Composio がイベントを見ていない | 同じ予定に対し travel が `inserted=2`、late が `decision=late` を出している = 見えている |

### 1.3 ~~未解決の観測~~ → **判別完了（2026-08-01）。前提が間違っていた**

**旧記述（誤り）**: 「`lm_wake_log` 全履歴で `answered_at` が null」。id 960/961/962 だけを見た早合点だった。

**実測**: 441行中 **11行に `answered_at` が入っている**（id 773/782/790/805/844/874/890/891/902/906/937、
2026-07-18〜07-28）。Telnyx `call_events` API と DB を全件突合した結果:

| AMD result | 件数 | `answered_at` |
|---|---|---|
| `human` | 10 | **10件すべて SET** |
| `machine` | 32 | 32件すべて null |
| `not_sure` | 1 | null |

**43/43 で完全一致、取りこぼしゼロ。** さらに `machine` 判定の通話（2026-07-29T23:11、120秒）の録音を
実際にダウンロードして書き起こしたところ、日本語キャリアの留守番電話だった（「こちらのお電話は
留守番電話に転送されました」）。**AMD の判定は正しく、null は「本当に出ていない」という真実**。

**結論: 記録経路は健全。壊れているのは記録ではなく現実。**

| 実際に起きたこと | 件数 | 今の DB の見え方 |
|---|---|---|
| 人が出た | 10 | `answered_at` SET |
| 鳴ったが応答なし | 31 | `answered_at IS NULL` |
| 留守電に転送された | 32 | `answered_at IS NULL` ← **区別できない** |
| webhook 自体が来ていない（本物の故障） | 0 | `answered_at IS NULL` ← **区別できない** |

★ 製品として最も重い事実 ★: **直近4日（07-29〜08-01）の起床コール7本は全部留守電で、Dais は一度も
出ていない。** そしてその事実は今 DB から読み取れない。

★ 2026-08-02 追記（#2a の帰結）★: **`amd_result='human'` かつ `answered_at IS NULL` は今や正当な結果**
= 人は出たが `answered_at` の PATCH だけが失敗し、我々が**意図的に追いかけない**ことを選んだ行（理由は row 2a ③）。
この行を「出ていない」と読んではいけない。**それでも §1.3 が塞いだ穴は塞がったまま**である — 判別は
`answered_at` ではなく **`amd_result`** が担っており、`human` が入っている時点で「人が出た」は確定している。
失われているのは事実ではなく**その秒**だけ。区別できないままなのは `amd_result IS NULL` の行だけで、それは
依然として「webhook が来ていない = 本物の故障」を意味する。

因果チェーンは全 hop 実証済（Telnyx 発呼 + AMD 有効 → webhook 登録 `…/telnyx-events` → 署名検証（unsigned
POST が 403 = 鍵設定済）→ `client_state` 復号が `event_key` と **byte 一致**（id 960 にヒット）→ PATCH →
行更新。`human` イベントの秒単位タイムスタンプが `answered_at` と一致、発呼 +8〜24秒）。壊れている hop はゼロ。

**残る欠陥（= #2 の実作業）**: 0行 PATCH が**見えない**。`server.js:294` は `marked` を stdout に出すだけで、
`markAnswered` は「0行一致」と「HTTP失敗」の**両方で false** を返すので区別不能。`server.js:816` は戻り値を
捨てている。Telnyx が署名鍵をローテートしたら全 webhook が 403 になり `answered_at` は永久に全 null になるのに、
DB には痕跡が一切残らない。**これは #1b と同じ「失敗が存在しない事象に見える」クラス**。

### 1.3.1 ★Telnyx の再送契約★（2026-08-02 公式 docs 実取得。#2a の根拠であり、今後の全 webhook 作業の前提）

記録が消える経路はもう1本あった。**Supabase への PATCH が失敗しても handler が 200 を返していた**ので、
Telnyx は「届いた」と解釈して**二度と送ってこない**。落ちていたのは Supabase の数秒だけなのに、失われるのは
その検知**そのもの**。これも §1.3 と同じ「失敗が存在しない事象に見える」クラスで、しかも**こちらが自分から
再送の権利を捨てている**ぶん質が悪い。

| 事実 | 引用 | 出典 |
|---|---|---|
| 2xx 以外は「受け取っていない」扱い = 再送/failover の対象 | "Your endpoint must return a `2xx` HTTP status code to indicate successful receipt... All response codes outside this range, including `3xx` codes, will indicate to Telnyx that you did not receive the webhook." | https://developers.telnyx.com/development/api-fundamentals/webhooks/receiving-webhooks |
| Voice 側も同じ | "If that URL does not resolve, or your application returns a non 200 OK response, the webhook will be delivered to the failover URL" | https://developers.telnyx.com/docs/voice/programmable-voice/receiving-webhooks |
| 再送は指数バックオフ。primary 3回 + failover 3回 = **最大6回**（数字は Messaging の retry policy 表に明記。Voice は同じ primary→failover 機構を数字なしで記載） | "Up to **3 attempts** per URL with exponential backoff... **Total attempts**: Up to 6 total (3 primary + 3 failover)." | https://developers.telnyx.com/docs/messaging/messages/receiving-webhooks |
| ★応答は2秒以内★（Call Control は connection 設定 `webhook_timeout_secs` 0–30 で上書き可） | "Webhooks will be retried to each of the supplied URLs if your application does not respond in **2000 milliseconds**." | https://developers.telnyx.com/development/api-fundamentals/webhooks/receiving-webhooks |
| 再送は**同一 payload**（`client_state` も `data.id` も同じ）。変わるのは `meta.attempt` | "`attempt` \| `meta` \| Delivery attempt number (increments on retries)" / "Track processed event IDs (`data.id`) and skip duplicates" | https://developers.telnyx.com/docs/voice/programmable-voice/voice-api-webhooks |

**ここから出る2つの帰結**:

1. **再処理は安全でなければならない**（同一 payload が最大6回来る）。実際そうなっている = `recordAmdResult` は
   フィルタ無し（最終観測が勝つ）、`markAnswered` は `answered_at=is.null` のラッチ（最初の human が勝つ）。
   #2a はこの2性質に**依存している**ので、`test/telnyx-events-retry-http-contract.test.js` が両方を pin し、
   ラッチを外すと RED になる事を実測済（下の 2a）。
2. ★**2秒の壁は我々の応答コードと無関係に再送を生む**★ — `/telnyx-events` は Supabase の PATCH を最大2本 +
   Telnyx の hangup を**待ってから**応答している。合計が 2000ms を越えれば、200 を返していても Telnyx から
   見れば失敗で、同じ event がもう一度来る。今回の変更で壊れるものではない（1 の冪等性が受け止める）が、
   **書き残さないと「なぜか毎回2回書かれている」の原因究明をまた1から始めることになる**。将来この handler に
   I/O を足す時の上限は 2000ms で、超えるなら「先に 200 を返して非同期で書く」への設計変更が要る。

---

## 2. 外部調査（2026-08-01、一次資料）

| 論点 | 結論 | 出典 |
|---|---|---|
| Telegram ライブ位置の更新頻度 | **Bot API に更新間隔の規定は無い**。`edited_message` として push されるが頻度は送信側クライアント任せ。SLA は無い | core.telegram.org/bots/api §editMessageLiveLocation |
| `live_period` | 60–86400秒、または `0x7FFFFFFF` で**無期限** | 同 §sendLocation:「must be between 60 and 86400, or 0x7FFFFFFF for live locations that can be edited indefinitely」 |
| 位置誤差 | `horizontal_accuracy` = 0–1500 m | 同 §Location:「The radius of uncertainty ... 0-1500」 |
| ★設計への帰結★ | **秒単位の追従案内を作らない**（「次で乗換」「前から3両目」は禁止）。位置は「家を出たか」「大きく遅れているか」の粗い判定にだけ使う | 上記の SLA 不在から |
| 乗換ステップ（日本・米国） | **Google Routes API v2 `computeRoutes` TRANSIT** が両国同一スキーマ。`transitDetails.transitLine`（路線）· `headsign`（行先）· `stopDetails`（乗降駅・時刻）· `stopCount`。$5.00 / 1,000 calls | developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRoutes |
| ★出口番号★ | **Routes API にも Transitland/OTP にも無い**。番線も無い | 同上スキーマ |
| 出口番号の入手先 | 日本固有データ。鉄道事業者の公開データ（ODPT 等）を別途引く。米国は概念自体が無い | odpt.org / transit.land |
| 未検証 | NAVITIME / Ekispert の実レスポンス項目（docs が JS 描画で読めず）。必要なら試用キーで実 call | docs.ekispert.com |

---

## 3. 残 TODO（1 から順。番号 = 実行順。飛ばさない）

★ **この表の「DONE」は "branch に入った" という意味であって "本番で効いている" ではない。両者を混同すると、
2026-08-01 16:56 の実測（下の #0）と同じ嘘を繰り返す。** ★

| # | 作業 | 無いと何が起きるか | done（実 receipt） |
|---:|---|---|---|
| **0** | ★ 1a〜2b の 35 commit を `main` へ merge して Railway へ deploy ★ | **2026-08-01 16:56 実測**: live の `life-call` は `main` の `fce82564c`（deploy 10:13 JST）で、daily organ の修正は **1つも本番に無い**（`git merge-base --is-ancestor` で `da7dec52b` / `1eb594fe7` / `a42746699` / `7e077d132` すべて NO）。証拠 = 16:47 JST に実架電があり `amd_result` が `null`（AMD 記録コードが未 deploy）。**留守電に2分喋って課金する挙動はこの瞬間も生きている**。1d の Composio 減も deploy 前は測れない | live deploy の commit が 2b を含む。deploy 後の実架電行に `amd_result` が入り、`machine` なら通話が数秒で終わる |
| **1** | ~~呼び出し不発の原因究明~~ → **原因特定済（§1.2）。残りは修正3点** | 呼び出しが静かに消える = 製品が存在しない | ①窓を「取りこぼさない」形に変更（下記 1a）②逃した呼び出しを記録（1b）③時間に敏感な loop を他 organ から分離（1c）。実予定で T-10/T-5 が両方 `lm_wake_log` に載る |
| 1a | ~~発火条件を「2分の窓」から**追い付き方式**へ~~ ✅ **DONE 2026-08-01**（commit `da7dec52b`、merge `9873e0ce9`） | tick が遅れた瞬間に永久に失われる | 実装: `scheduler.js` の窓判定を撤廃し `mins <= lvl.min+0.5 && mins > LATE_CUTOFF_MIN(-15)` で due 判定 → **最も緊急な1件だけ発信**、超えられた粗いレベルは claim だけして鳴らさない。検証（自分で実行）: `node --test test/wake-catchup.test.js` → `tests 5 / pass 5 / fail 0`、`node test/scheduler.test.js` → PASS。cases = ①T-5 を5分過ぎた tick でも1本鳴る ②通常は T-10 → T-5 の2本 ③両方 due の tick でも1本 ④出発を15分超過なら鳴らさない ⑤発信失敗で claim が解放され次 tick が再試行 |
| 1b | ~~「鳴るはずだったのに鳴らなかった」を記録~~ ✅ **DONE 2026-08-01** | 失敗が**存在しない事象**に見える（今回の3日を溶かした原因） | 実装: 新 ledger `lm_wake_miss`（`migrations/2026-08-01-lm-wake-miss.sql`、本番 Supabase に適用済 = `http=201`、PostgREST 読み取り `http=200`）+ `lib/wake-miss.js` + `scheduler.js` の `noteWakeMiss()` + `/status` の1行。記録する2事象 = ①`dial_failed`（`releaseWake` が claim を消す**前**に理由を残す）②`no_call_before_departure`（departure が `LATE_CUTOFF_MIN` を越えた時点で最細レベルの claim が無い = 一度も試みていない）。`(uid,event_key)` 主キー + merge-duplicates upsert なので 60秒 tick の連続失敗は1行を更新するだけ。`first_seen_at` は payload に入れないので「いつ壊れ始めたか」が保持される（実測: first_seen_at=01:04:57.5 / occurred_at=01:04:58.9）。★§5.4 の「自分から言う」も実装★ = `notified_at IS NULL` を条件にした PATCH を lock にして**1 miss につき Telegram 1通だけ**送る（retry tick は無言）。検証（自分で実行）: `node --test lib/wake-miss.test.js lib/slash-command.test.js test/wake-miss-record.test.js test/wake-catchup.test.js test/telegram-slash-http-contract.test.js` → **tests 55 / pass 55 / fail 0**（1a の回帰5件を含む）+ 本番 Supabase への実 round-trip（write → upsert → read → `/status` 行 `🔔 Missed: the 13:15 call could not be dialled (...)` → 検証行を DELETE、表は空に戻した） |
| 1c | ~~呼び出し loop を care / diet / mental / late から分離~~ ✅ **DONE 2026-08-01**（設計 = §3.1 方式A） | 他 organ の遅さが呼び出しを殺す。ユーザーが増えるほど悪化 | 実装: `wakeUserOnce` を **`wakeCallOnce`（poll + fetch + event 公開 + 発信のみ）** と **`organsUserOnce`（8 organ）** に分割し、`wakeUserOnce` は両者の合成として温存（Inngest `makeWakeUserHandler` と既存 suite がこの名前を呼ぶ）。新規 `lib/event-cache.js` = wake tick が fetch を所有し organ tick は読むだけ（`calendar-cache` のキーが分単位で回るため、素朴に2ループへ分けると Composio が倍増する）。新規 `lib/organ-run.js` = 全 organ を `[organ:<name>] uid=… ms=…` で計測（成功は stdout・失敗は stderr）。`startWakeLoop()` = **固定60秒・user 毎 20秒**（`WAKE_USER_TIMEOUT_MS`）、`schedulerPollInterval()` を意図的に使わない（#1d の劣化を dial に波及させない）。`tick()` は organ 側へ。`maybe-start-loops.js` + `server.js` で本番起動に配線。★review 指摘の修正込み★: H-1 dial 前の `recordDailyComposioPoll` await を fire-and-forget 化（20秒予算を会計処理が食う = 潰したはずの構造の縮小版だった）/ H-2 `claimWake` に `claim_token` を持たせ `releaseWake` を所有権付きに（migration `2026-08-01-lm-wake-log-claim-token.sql` を本番 Supabase へ適用済 `http=201` / `read_http=200`。放棄された tick が後続の**成功した** claim を消して**二重架電**する経路を封鎖）/ M-4 organ の失敗ログを stderr へ戻す。検証（自分で実行）: `node --test` 10 files → **tests 104 / pass 104 / fail 0**、`node -e` で `startWakeLoop / wakeTick / wakeCallOnce / organsUserOnce = function` + `WAKE_USER_TIMEOUT_MS = 20000`。★最重要 assertion は mutation で kill 確認済★ = 全 organ を 5000ms stall させて `wakeCallOnce` が 1.5ms で完走（分割前の順序を復元した mutant では 5007ms で RED） |
| 1e | ~~organ tick の `call_enabled !== false` filter を外す~~ ✅ **DONE 2026-08-01** | dial が別 loop に出た今、**電話番号を出さない人（#6）に care/diet/mental/precepts/relations が1つも届かない**。`organsUserOnce` の care コメント「Still runs for call-disabled users」と実コードが矛盾していた | 実装: `tick()` の filter を `daily_automation_enabled !== false` のみへ（`call_enabled` は dial が自分の loop で見る）。検証（自分で実行）: `test/wake-loop-isolation.test.js` に3件追加し **RED を先に踏んだ**（「the organ tick serves a user who gave no phone number」だけが落ちる）→ 修正 → `node --test` 11 files で **tests 116 / pass 116 / fail 0**。pin した3点 = ①電話無効ユーザーにも organ が走る ②`daily_automation_enabled=false` は依然として全停止 ③**wake tick 側の `call_enabled` filter は残る**（電話の無い人に架電しようとしない）。`lib/panel-corrective-red.test.js` の1件は本変更を stash しても同じく落ちる **既存 baseline**（spec 文書の文字列 assertion で scheduler 無関係） |
| 1d | ~~Composio 予算超過で tick が5分に落ちるのを止める~~ ✅ **コード DONE 2026-08-01 / 本番実測は deploy 待ち**（設計 = §3.2） | 7月は実測 20,488 で既に劣化済。8月も現ペースで約5日で再劣化 = 製品が毎月半分は5分刻みで動く | 実装: `lib/calendar-cache.js` の `cacheKey(uid, window, ttlMs)` がバケット幅に **TTL そのもの**を使う（`minuteBucket` 廃止）。幅と失効を1つの数字が決めるので二度とズレない。`ttlMs<=0`（= キャッシュ無効）は key を作らず transport へ直行（幅0の除算・全窓の1キーへの潰れ・読まれない `entries` 行の蓄積を回避）。検証（自分で実行）: `node --test lib/calendar-cache.test.js test/wake-catchup.test.js test/wake-loop-isolation.test.js lib/events.test.js` → **tests 39 / pass 39 / fail 0**、および実 `fetchUpcomingEvents` を 60秒刻みで5回呼ぶ E2E で **transport hits = 1**（修正前は 5）。`wake-catchup` が緑 = 発火は `now` と `startMs` の差で決まり fetch 時刻に依存しない = **精度据え置き**。★未検証★ 本番 `lm_api_cost` の実減少は deploy 後1日数えるまで確認できない（この branch は未 merge・未 deploy） |
| **2** | ~~`answered_at` が常に null の判別~~ ✅ **DONE 2026-08-01**（判別 = §1.3、記録経路は健全だった） | ①応答なし ②留守電 ③webhook が来ていない（本物の故障）が **すべて `answered_at IS NULL`** で見分けられなかった。署名鍵ローテートで全滅しても痕跡ゼロ | 実装: migration `2026-08-01-lm-wake-log-amd-result.sql` で `amd_result` 追加（本番適用済 `http=201` / `read_http=200`）。`call.machine.detection.ended` を受けたら**必ず**行を PATCH、`answered_at` は `human` の時だけ。★2つの書き込みは冪等性の規則が逆★ なので `markAnswered`（`answered_at=is.null` フィルタ必須 = 一度きりのラッチ）と `recordAmdResult`（フィルタ無し = 最終観測が勝つ）を**別関数**にし、`applyAmdDetection` が合成（1つの PATCH に融合すると、応答済みの行に後から来た検知が filter で捨てられて**また記録漏れになる**）。0行一致と HTTP 失敗を `{ok, matched, error}` で分離し、webhook 側で別々の stderr 行に。bridge 側（戻り値を捨てていた）も同じ2分類をログするように。★backfill 21行★ = Telnyx `call_events` を handler と同じ `client_state` 復号で再導出し、**書く前に**全21行が実在行に解決し矛盾ゼロ（human↔SET 3/3、machine/not_sure↔NULL 18/18）を確認してから投入。Telnyx の保持期間が 07-25 までなので残りは**推測せず NULL のまま**。検証（自分で実行）: `node --test` 4 file → **tests 51 / pass 51 / fail 0**、`node --check server.js` OK、本番 `lm_wake_log` の実 census = **machine 17 / human 3 / not_sure 1** |
| **2b** | ~~留守電への発話を止める + 電話を既定 OFF~~ ✅ **コード DONE 2026-08-01 / 課金減は deploy 後に実測**（Dais 2026-08-01、正本 = §5.2.1） | AMD が `machine` でも bridge は喋り続け、キャリアの録音上限120秒で切られていた（`hangup_source` 43件すべて `callee`）。1本 約$0.05 の Gemini Live を**人に届かない留守電**に払っていた。実測 `human` 3 / `machine` 17 | 実装: ①`amd_result` を**先に**永続化してから、`human` 以外の判定で Telnyx `POST /calls/{ccid}/actions/hangup` を発行（`call_control_id` は `data.payload.call_control_id`。Telnyx 公式 repo の実 webhook サンプルと `telnyx-node` の hangup path で確認）。hangup 失敗は記録を壊さない ②`RUNTIME_DEFAULTS.call_enabled` を **false** に ③★発見★ default を倒すだけでは不十分だった — 他設定を触った結果 `lm_panel_preferences` の行が存在し `call_enabled` が **`null`** の場合、`null` が default の上に spread され `null !== false` が真になって**依然として架電される**。`wakeTick` の filter と `wakeCallOnce` の dial gate（= Inngest 経路の最後の関門）を `=== true` に変更 ④`buildControlCenter` が**独自に `call_enabled: true` を hardcode** していたため、電話ありで pref 行なしの人に「Calls are enabled」と表示しつつ実際は架けない = **UI が嘘をつく**状態になった。`RUNTIME_DEFAULTS` を単一の出所に統一（commit `7e077d132`）。検証（自分で実行）: `node --test` 15 file → **tests 192 / pass 192 / fail 0**、`node --check server.js` OK。★本番影響の実測★: `lm_panel_preferences` は1行のみで `lm_784ad279` が `call_enabled=true` を**明示済** = Dais の架電は既定変更では止まらない（留守電の浪費だけが止まる）。もう1人は行が無いので新既定どおり架電されなくなる |
| **2d** | ~~`/test-call` も留守電に当たったら切る~~ ✅ **コード DONE 2026-08-02 / 実架電の receipt は別途**（正本 = §5.2.1） | `server.js` の `/test-call` は `wakeUid`/`wakeEventKey` を積まないので `client_state` が空になり、webhook が `"no wake context"` で早期 return して **hangup 経路に到達しない**。AMD は動き課金も出る。ユーザー起点かつ rate limit 付きだが、**まだ留守電に金を払える最後の場所** | 実装: ①原因は 2b の hangup が壊れていた事ではなく **`/test-call` が自分を名乗らなかった**事。`client_state` に**呼び出しの「種類」**を持たせ（wake = `{wakeUid, wakeEventKey}` / test = `{testUid}`）、`decodeCallClientState` 1本が両方を返して webhook が `kind` で分岐する ②★stream URL には触っていない★ — `buildStreamUrl` の query は `signCtx([summary,dateTime,location,urgency,lang,name,wakeUid,wakeEventKey])` で署名され `/ws` bridge が**同じ順序の配列**で検証するので、種類を query 項目で運ぶと署名の意味が片側だけ変わる。代わりに `placeCall({to, streamUrl, clientState})` に任意引数を1つ足して透過（`amdDialOptions(url, env, {clientState})` は明示値が URL 由来に勝つ。wake 経路は無変更）③★test 呼び出しは Supabase に一切書かない★ — scheduler が作る `lm_wake_log` 行が**存在しない**ので、`applyAmdDetection` を流用すると全 test call が `matched=0` を返し、「本物の wake 行が消えた」を意味するはずの §1.3 の警報が**恒常ノイズに化ける**。よって `applyTestCallDetection` は記録せず hangup だけを行う ④★hangup 条件は wake と完全に同一★ — `human` は切らない / `not_sure` は切る（実測 machine 17 : human 3、外すコストは「1回の nudge を逃す」対「2分の課金発話」で非対称）/ **空・読めない result は誰も切らない**（あれは AMD の判定ではなく payload の解析失敗。ここで切ると Telnyx の schema 変更1つが「全 test call が応答直後に死ぬ」に化ける = §1.3 の無音全損クラス）。同一性は両者が `shouldMarkAnswered()` を共有する事で担保（人間の定義を変えたら両方が一緒に動く）。検証（自分で実行）: `node --test lib/telnyx-webhook.test.js` → **tests 5 / pass 5 / fail 0**、`lib/dial.test.js + test/scheduler.test.js + lib/answered.test.js` → **tests 13 / pass 13 / fail 0**、`test/testcall-amd-hangup.test.js + lib/late-notice.test.js` → **tests 31 / pass 31 / fail 0**、実 `server.js` を実 HTTP + 実 Ed25519 署名で叩く `test/testcall-amd-hangup-http-contract.test.js` → **tests 1 / pass 1 / fail 0**（fake fetch が未知の host/path で throw するので「Supabase に書かない」が主張でなく物理制約。dial body の `client_state` が `kind:"test"` に戻る事と、stream URL の query 項目が9個から増えていない事を pin）、`node --check server.js` OK。全 suite: 変更前 **tests 2037 / pass 2031 / fail 6** → 変更後 **tests 2052 / pass 2046 / fail 6** で**失敗は同一の6 file**（`event-participation-entities` / `panel-corrective-red` / `panel-corrective3-four-blockers` / `panel-corrective4-logout` / `panel-display-policy` / `browser-task-telegram-http-contract` = 本変更と無関係の既知 baseline。`git stash` して `panel-corrective-red` 単体が同じ **tests 11 / pass 10 / fail 1** で落ちる事も確認済、直していない）。★未検証★: 実架電の通話秒数は deploy 後に Telnyx 側で実測する（下の 0-receipt と同じ receipt 欄で閉じる） |
| **2a** | ~~webhook の PATCH 失敗時に Telnyx へ 200 を返すのをやめる~~ ✅ **コード DONE 2026-08-02 / 実再送の receipt は別途**（根拠 = §1.3.1） | Supabase が落ちている間、大声でログは出るが Telnyx には「受け取った」と答えるので**再送の権利を自分から捨てている**。落ちていたのは数秒でも、失われるのはその検知そのもの。しかも痕跡は stderr にしか残らず DB は永久に NULL = §1.3 と同じ「失敗が存在しない事象に見える」クラス | 実装: `server.js` の `/telnyx-events` 末尾で `outcome` を 200 に畳んでいた三項を分解し、**`!detection.amd.ok` の時だけ 503**（body = `record failed; send it again`）。★実際に引けた線は「書き込みが着地したか」対「着地して0行だったか」の**1本だけ**★ = ①`!ok` → 5xx を返して Telnyx に再送させる（§1.3.1 の「2xx 以外 = 受け取っていない」。primary 3 + failover 3 の指数バックオフ）。★この線の粗さを正直に書く★ — `patchWakeLog`（`lib/late-notice.js:196-207`）は**あらゆる失敗を同じ `{ok:false}` に畳む**ので、一時的なもの（5xx / fetch の throw）だけでなく**恒久的なものまで再送を要求してしまう**。実測（`node -e` で直接呼んで確認）= `http_400`（schema drift）· `http_401`（service-role 鍵ローテート）· `http_404` · `unreadable_response` · `missing_args` · `recordAmdResult` の **`missing_result`** が全部 `{ok:false,matched:0}` → 全部 503 → 6配送すべてで同じように失敗する。★`missing_result` が一番痛い★ — `lib/late-notice.js:245-247` は「読めない result は AMD の判定ではなく**我々の** parse 失敗だから誰も切らない」と長々と論じているのに、同じ入力が今度は**6配送を焼く**。代償 = 配送予算の空焼き + failover URL を無意味に鳴らす + **本物の障害と schema の typo が見分けられない**。当面それでも受け入れる理由 = 逆側の誤り（本物の障害に 200）は検知**そのもの**を消すが、無駄な再送は何も消さないから。★本来の直し方★ = `patchWakeLog` に retryable / permanent を返させ前者だけ escalate する（この分岐を広げるのではなく**あちら**を直す。でないと2つが drift する）。振る舞い変更なので**今回はやらない** = 別 TODO ②`matched === 0` = 書き込みは**着地して**正しく0行だった = その `uid+event_key` の行が存在しない → 再送しても永久に埋まらないので **200 で閉じる**（ここで 5xx を返すと6回の配送を焼いた上、本物の障害と見分けがつかなくなる = §1.3 の警報をノイズに変える 2d と同じ罠）③★`answered_at` の PATCH 失敗は 5xx にしない★ — ただし理由は「ラッチのせいでどうせ no-op だから」では**ない**（それは誤り。ラッチは `answered_at=is.null` なので、最初の書き込みが着地していなければ列は NULL のままで、再送された書き込みは**普通に着地する**）。本当の理由は3つ = (1) この書き込みは `amd_result` が成功した**後**にしか走らないので、再送を頼むと成功済みの `amd_result` を配送のたびに書き直す (2) 書かれる時刻は**再送時の時計**で指数バックオフの分だけズレる = 「無い」より悪い答えになる (3) `amd_result='human'` が「人が出た」事実を既に記録しているので、失うのは事実ではなく**その秒**だけ（失敗は既存の `report()` が stderr に残す）④★`/test-call` 分岐は常に 200★ — 書く先が無く、唯一の副作用である hangup は**再送できない**（最初のバックオフが明ける頃には通話がキャリアの録音上限で終わっており、切る相手がいない）。検証（自分で実行）: 新規 `test/telnyx-events-retry-http-contract.test.js` = 実 `server.js` を実 HTTP + 実 Ed25519 署名で叩き、fake fetch が未知の host/path で throw する（= 「Supabase に届く前に答えた」が緑にならない物理制約）。**先に RED を踏んだ** → `tests 5 / pass 3 / fail 2`（`expected 5xx, got 200` が Supabase 500 と ECONNREFUSED の2件だけ。`matched=0` / 正常系 / test call の3件は現状どおり緑 = 変えてはいけない所を変えていない証拠）→ 実装 → `test/telnyx-events-retry-http-contract.test.js + test/testcall-amd-hangup-http-contract.test.js + test/testcall-amd-hangup.test.js + lib/late-notice.test.js` で **tests 38 / pass 38 / fail 0**（下の characterization test を足した後の再実測値。実装直後の 37/37 は当該 test を書く前の数）。★再送安全性を characterization test で固定★（§1.3.1 の帰結1）= 同一 event を2回配送し「1回目 Supabase 500 → 5xx / 2回目 200 + `answered`」を pin した上で、`answered_at` の全 PATCH が `answered_at=is.null` を**持つ**事と `amd_result` の全 PATCH が**持たない**事を assert → **mutation で kill 確認済**: `markAnswered` から `filter: "&answered_at=is.null"` を外すと当該1件だけが `tests 6 / pass 5 / fail 1`（`answered_at must be latched so a resent event cannot rewrite the first human proof`、actual URL に `answered_at=is.null` 無し）で落ち、戻すと `tests 6 / pass 6 / fail 0`。全 suite `node --test lib/*.test.js test/*.test.js` = **tests 2080 / pass 2075 / fail 5**、失敗は既知 baseline の部分集合（`panel-corrective-red` / `panel-corrective3-four-blockers` / `panel-corrective4-logout` / `panel-display-policy` / `browser-task-telegram-http-contract`。6件目の `event-participation-entities` は単体で `tests 8 / pass 8 / fail 0` = 今回緑）。★未検証★: **実際の再送で行が埋まる**所は本番でしか見えない。本番の `SUPABASE_URL` を壊す実験は**しない**（生きている書き込みを落とすので）。deploy 後に `/health` の build tag 更新を確認し、実 AMD event が 200 で処理され続けている事をログで見る |
| **2c** | ~~出発の押し切りを Telegram 連投にする~~ ✅ **コード DONE 2026-08-02 / 実配信の receipt は deploy 後**（正本 = §5.2.1、実装設計 = §5.2.2） | 電話は「出る」という動作を要求し、実測で一度も人に届いていない。Telegram は**画面に残り続ける**ので出発という行動に直接効く（Dais 実感） | 実装: 新 ledger `lm_departure_nudge`（`migrations/2026-08-02-lm-departure-nudge.sql`、本番 Supabase に適用済 = **DDL `http=201`** / PostgREST 読み取り **`http=200`**（8列全部 select 通過）/ `create table if not exists` なので**再実行も `http=201` で無害**＝冪等を実測）+ 新規 `lib/departure-nudge.js` + `scheduler.js` の `maybeNudgeDeparture()` + `server.js` の `depart:ack` 配線。★停止条件は **3本**、位置（§5.2.1 ②）は **#3 待ちで未実装**★ = ①`[了解]` タップ ②電話に出た（`lm_wake_log.answered_at`）③出発 `LATE_CUTOFF_MIN`(-15) 超過で late organ へ移行。★設計の核 = D4「claim と停止判定を1回の PATCH に融合」★ — `acked_at=is.null` **かつ** `last_level_min=gt.<level>` で filter した PATCH が1行返した時だけ送る。読んでから決めると 60秒 tick が重なった瞬間に同じ段が2回出る（`claimWake` が unique 制約に賭けているのと同じ思想を、単調減少する `last_level_min` で表現）。行が無い時だけ INSERT にフォールバックし、**409 は障害ではなく「他 tick が先に取った」**として送らずに `ok:true` を返す。★PATCH が HTTP 失敗した時は `claimed=false`★（書けたか不明な時に送るのは、1通逃すより悪い方＝二重送信に倒れるため）。段は `NUDGE_LEVELS=[25,10,5,0,-3,-7]` で `WAKE_LEVELS`（電話）とは**別配列**（D2）。★1予定1行なので「越えた粗い段を claim だけする」1a の作法が不要★ — 単調性が自動的に粗い段を永久に締め出す。★予算★: `resolveDeparture` は **dial と同じ1回を使い回す**（2回目を呼ぶと 1d で潰した Composio 増を再発させる）、通知は **1 tick 1通**上限、`wakeWasAnswered` の読みは**段を取れた後だけ**なので1予定あたり最大6回（tick 毎ではない）。★`wakeWasAnswered` の失敗方向は `wakeWasClaimed` と逆★ = 読めなければ `false`（「読めないから梯子を黙らせる」のは、番号を出さない人にとって製品そのものを消す）。★送信失敗時は段を返す★（`releaseNudgeLevel`、初段は行ごと DELETE・以降は次に粗い段へ復元、`last_level_min=eq.<level>` が所有権 guard なので stale な release は何も動かさない）。★正直に書く粗さ★ = 進段の release は**置換前の値を復元できない**（PostgREST は更新**後**の行しか返さない）ので「次に粗い段」に丸める。gate としては厳密（当該段だけ再claim 可・粗い段は封鎖）だが、履歴としては「少なくともここまでは進んだ」に鈍る。厳密化には `prev_level_min` + BEFORE UPDATE trigger が要り、1回の retry には過剰なので採らない。★callback は `depart:ack:<startIso>` で uid を載せない★（D7、64 byte 上限）→ uid は**タップした chat から引く**ので、同時刻の予定を持つ別 user が同じ payload を押しても自分の行しか触れない（tenant 境界が 64 byte 制約の副産物になっている）。文面は §5.2.2「送る文」verbatim（T+7 は終端で**ボタン無し**、相手への連絡は late organ の仕事のまま = D6）、時刻は既存 `i18n.js` の `clockLabel`（予定自身の UTC offset で描画）、予定タイトルは `escapeHtml`（`parse_mode:HTML` に他人の書いた文字列が乗るため）を再利用し新造しない。★review 指摘の修正込み（2026-08-02、6件）★ — **B1（blocking）= 梯子が対象ユーザーに1人も届いていなかった**: `wakeCallOnce` 内の gate を下げただけで `wakeTick:896` の `call_enabled === true` filter を残していた。**入口が cohort を決める**ので下層の変更は無意味。実測 = 自動化ON の4人（pref行なし / NULL列 / 明示false / 電話あり）を実 `wakeTick` に通し `wakeCallOnce` に届いたのは **1人（電話ありのみ）**。§5.3 が「電話なし＝既定」と決めた以上これは**製品が誰にも出荷されていない**状態。修正 = 1e が organ tick に施したのと同型に `daily_automation_enabled !== false` のみへ（dial gate は `wakeCallOnce` 内に**そのまま**残す＝Inngest 経路の最後の関門）。★なぜ自分のテストが見逃したか★ = tick テストが全部 `wakeCallOnce` を直接呼ぶ＝**cohort を選ぶ層の1つ下**を叩いていたため緑のまま通過。→ 実 `wakeTick` を driver にした cohort テストを追加し、`test/wake-loop-isolation.test.js` の旧 assertion 2件（"the filter belongs to the dial, and stays there"）を**実 `wakeCallOnce` を回して dial 数を数える**形へ書き換え（entry 数だけでは「全員に届く」と「全員に架電する」を区別できない）。**S1** = 梯子の I/O（claim PATCH → answered GET → Telegram send、失敗時 release PATCH、いずれも個別 timeout なし）が `placeCall` の**前**にあった。`scheduler.js:509` が既に記録している "a slow store spent the user's entire wake budget and the phone never rang" と同型 → 同 loop 内で**dial の後ろへ移動**（`depMs`/`mins` は算出済みなので梯子側の損失ゼロ）。mutation で kill 確認（前に戻すと `['nudge','dial']` で RED）。**S2** = `headline()` が **escape→slice** の順で、`R&D` が境界に来ると `…R&am` を出力。`parse_mode:HTML` なので Telegram が壊れた entity を拒否 → 送信失敗 → release → 次 tick が**同一文面で同一失敗** = その予定の梯子が永久沈黙。**truncate→escape** に修正（旧 guard テストは8文字で切れず素通りしていた → pad 76-80 で partial entity を検出する形へ拡張）。**S3** = `claim.opened` は**実装が一度も返していない**フィールドで scheduler は常に `opened:false` を渡し、DELETE 分岐は「level 25 に coarser が無い」偶然でしか成立していなかった → **T-25 の内側で初出の予定（＝当日朝の普通の登録）は幻の行を残す**。修正 = 実 `claimNudgeLevel` が `opened` を返す（INSERT=true / PATCH=false）。★fake が実体の出さないフィールドを主張していた★ ので harness も実体に合わせた。**S4** = `server.js` が `row.call_language` を生で渡していた → scheduler と同じ `langForUser()` に統一（2b の `call_enabled` 事故と同じ「1つの問いに2つの出所」）。併せて `telegram-onboard.js` の `SEL` に `call_language` を追加（無いと `langForUser` が黙って `langForPhone` に落ち、**返信が元メッセージと違う言語**になりうる）。★B1 の副作用として発見した実バグ（別件・修正済）★ = `lib/travel.js` の `_geoMemo` は `has()` を読むだけで **`set()` が存在せず**、address→geo memo が**一度も効いていなかった**。B1 修正でこの経路が全 fleet × 毎 tick に広がるため放置不可 → **成功時のみ** memo（一時失敗を process 寿命で固定すると、最も再取得したい住所を deploy まで「解決不能」に固定する）。他テストが全部 `_geocode` を注入していたため死んだ cache が見えていなかった → 実 `geocodeAddress` を叩くテストを追加（RED = `actual: 10, expected: 2`）。★実測した per-tick コスト★（実 `resolveDeparture` + 実 `directionsMinutes` を実 cache 付きで回し HTTP を計数）: ①[Travel] block **あり** = block が出発を確定するので **geocode 0 / route 0**（外部呼び出しゼロ）②block **なし**・1予定を10 tick = **geocode 2 / route 3**（初回のみ。2〜10 tick 目は全 cache hit。route の3件は transit 1 + Google の transit/drive 2 で**compute 1回**）③同一 home→venue の**20ユーザー × 10 tick = 200呼び出し追加で geocode +0 / route +0**（route cache の key が `"_shared"` なのでユーザー間で共有、geo memo は住所単位）。**memo 修正前は②が geocode 20**（毎 tick 2件）＝ 20→2。★残る正直な但し書き★ = どちらの cache も**プロセス内 Map で無期限**（再 deploy で空・evict なし）、route cache の TTL は10分なので block の無い予定は**10分に1回**再計算される。検証（自分で実行）: `node --test lib/departure-nudge.test.js` → **tests 17 / pass 17 / fail 0**、`test/departure-nudge-tick.test.js + test/wake-catchup.test.js + test/wake-levels.test.js + test/wake-loop-isolation.test.js` → **tests 30 / pass 30 / fail 0**（電話の梯子が T-10/T-5 の2本のまま**1本も増減しない**事＋**電話なしの3形態が全部 tick に入り1件も架電されない**事を含む）、`lib/travel-transit-wire.test.js + lib/travel.test.js + lib/travel-routes.test.js + lib/travel-return.test.js` → **tests 52 / pass 52 / fail 0**、実 `server.js` を実 HTTP + 実 secret-token header で叩く `test/departure-nudge-http-contract.test.js + test/telegram-callback-http-contract.test.js + lib/ask-callback-visibility.test.js` → **tests 8 / pass 8 / fail 0**（fake fetch が未知の host/path で throw するので tenant 分離が主張でなく物理制約）、`node --check scheduler.js server.js` OK。★全 RED を先に踏んだ★ = Task1 `tests 1 / pass 0 / fail 1`（module 不在）→ Task2 `tests 12 / pass 7 / fail 5` → Task3 `tests 8 / pass 2 / fail 6` → Task4 `tests 1 / pass 0 / fail 1` → Task5 `tests 14 / pass 13 / fail 1`。**review 修正でも先に RED を踏んだ** = B1 cohort `actual: ['caller'] / expected: 4人`、S2 escape `pad=76 で "…R&am"`、S3 `opened` 2件で `tests 17 / pass 15 / fail 2`、geo memo `actual: 10 / expected: 2`。★#3 の差込口は mutation で kill 確認済★ = `ackNudge(..., 'left_home')` を production file に1行足すと「nothing in the codebase claims to detect leaving home」だけが `tests 14 / pass 13 / fail 1` で落ち、戻すと 14/14/0（＝**無い停止条件を実装したことにしない**を test が守っている）。全 suite `node --test lib/*.test.js test/*.test.js`: 変更前 **tests 2168 / pass 2163 / fail 5** → 実装後 **tests 2191 / pass 2186 / fail 5** → review 修正後 **tests 2198 / pass 2193 / fail 5** で**失敗は同一の5 file**（`panel-corrective-red` / `panel-corrective3-four-blockers` / `panel-corrective4-logout` / `panel-display-policy` / `browser-task-telegram-http-contract` = 既知 baseline。`event-participation-entities` は今回も両側で緑）。★D5 ③ の停止は本番データで実測済★ = `wakeWasAnswered` が組む URL（`event_key=like.<uid>|<startIso>|*` + `answered_at=not.is.null`）を**本番 `lm_wake_log` にそのまま発行** → `http=200` / `matched=1` / 戻り値 `true`（実 answered 行 = `…|2026-08-01T18:00:00+09:00|5`）。本番の key 形式も確認 = **3分割 key が 221行**（`<uid>|<startIso>|<level>`）で現行 scheduler と一致、2分割は 6月の legacy のみ。★これを実測した理由★ = tick テストは `wakeWasAnswered` を注入で差し替えるので、`|` と `*` の URL encode が実 PostgREST に通るかは test では緑にならない。★未検証★: **実予定1件での実配信は deploy 後**（この branch は未 merge・未 deploy）。T-25 から順に届く事・`[了解]` で止まる事・番号未登録 user に全段届く事（#6）を Telegram の実画面で確認するのは 2c-receipt として別に閉じる |
| **3** | 位置を「家を出た」判定に接続（鮮度は `observed_at`） | 位置が来ていても使わなければ案内が始まらない | 実予定1件で出発検知 → 出発直後の1通が実配信。`updated_at` を鮮度に使う箇所が 0 |
| **4** | 乗換ステップ + 出口番号 | **これが無いと Google Maps を消せない** = 商品の主張が嘘になる | 実イベント1件で経路1通が届き、Maps を開かずに着いた。出口が取れない駅は**黙って省く**（推測で書かない） |
| **5** | 1タップ承認 | 無断で相手にメールが飛ぶ。友達に渡した瞬間に事故る | 押すまで送信0・押したら実送信、両方確認 |
| **6** | 電話番号なしでも動く → **2026-08-01 以降これが既定**（§5.2.1 / §5.3） | 3人のうち少なくとも1人は番号を出さない。加えて実測で、番号を出した Dais 本人にも電話は届いていなかった | 番号未登録の test user で、出発の連投 → 経路 → 承認まで全部 Telegram に届く。2b + 2c が入れば大半が満たされるので、残るのは**番号未登録の実 user での E2E 1本**だけ |

**運用規則（今回の教訓）**: ★試験中に本番へ env を設定しない★ — Railway では変数設定が再デプロイを誘発し、
発火窓を破壊する。試験の前後30分は本番の設定変更を行わない。

### 3.1 #1c の設計（2026-08-01 実測に基づく決定。方式A = プロセス内 wake 専用 tick）

**実測した障害構造**（この session で `scheduler.js` を読んで確認）

| 事実 | 場所 | 何が起きるか |
|---|---|---|
| tick は `setTimeout` 再帰で**前 tick の完走を待つ** | `scheduler.js:623-637` | 次の tick の時刻 = 全ユーザー × 全 organ の合計。ユーザーが増えるほど wake が遅れる |
| 90秒 timeout は **organ 毎でなく user 毎** | `scheduler.js:596-611` | late+mental+wake+care+diet+precepts+relations が1つの予算を共有する |
| late と mental は **wake より前**に走る | `:367` `:376`（wake は `:385`） | 前2つが90秒を使い切ると wake に到達せず user ごと abandon = **鳴らない** |
| `fetchUpcomingEvents` の throw は `return` | `:363-364` | カレンダー取得の失敗が wake ごと消す（organ 毎 try/catch の外側） |
| organ 毎の経過ms ログが**無い** | 全 organ は結果のみ | `tenant timeout 90000ms` が出ても**誰が食ったか分からない** |
| 予算劣化で tick が5分に落ちる | `composio-budget.js:6-12` | wake も道連れ（→ #1d で別途潰す） |

**採用した方式 A（プロセス内に wake 専用 tick）**

```text
  今                                    A のあと
 ┌──────────────────────────┐        ┌────────────────┐  ┌──────────────────────┐
 │ tick 60s（1本）           │        │ wake tick 60s  │  │ organ tick（別タイマー）│
 │  poll → events           │        │  events        │  │  late / mental / care │
 │  → late → mental         │        │  → wake だけ    │  │  / diet / precepts    │
 │  → ★wake★                │        │  user 毎 20s   │  │  / relations          │
 │  → care → diet → …       │        │  上限          │  │  user 毎 90s 維持     │
 │  user 毎 90s を全員で共有  │        └───────┬────────┘  └──────────┬───────────┘
 └──────────────────────────┘                │ events を書く         │ events を読む
                                             └────► プロセス内キャッシュ ◄┘
```

| 決定 | 理由 |
|---|---|
| wake を独立タイマーに出す | 「他 organ の所要時間に影響されない」= 別 tick でしか満たせない。同一 tick 内の順序入替では累積 drift が残る |
| wake の user 毎 deadline を 20秒に短縮 | wake がやるのは events 取得 + 発信のみ。90秒は他 organ 用の予算であって wake には過大 |
| **wake tick が events を取得し、organ tick はキャッシュを読む** | 素朴に2ループへ分けると Composio 呼び出しが**倍**になる（`calendar-cache` のキーが分単位で回るため別ループは常に miss）。取得の所有者を wake に一本化すれば呼び出し数は据え置き |
| organ 毎の経過ms ログを入れる | done 条件が「ログで確認」。今は計測が存在しないので、隔離できた証拠を出せない |
| 別プロセス / 別 role にはしない | `lm_runtime_scheduler_leases` の `scheduler_key`、`runtime-up.js` の「compose の scheduler はちょうど1つ」不変条件、railway/Dockerfile の単一 `node server.js` を全部壊す必要がある。今の障害モード（遅い organ が同一 user 予算を食う）は A で消えるので、その代償に見合わない |

**A が守らないもの（正直に）**: プロセス crash と、Node のイベントループを**同期的に**塞ぐ organ。前者は再起動の話（別問題）、後者は現状の organ が全て I/O 待ちなので該当しない。該当し始めたら別プロセス（方式B）へ上げる。

**実装後に判明した既知の穴（2026-08-01 の review 実測）**

| 穴 | 内容 | 扱い |
|---|---|---|
| Composio 倍増の抜け道 | `putEvents` は fetch の**後**にある。fetch 自体が 20秒予算を超えて放棄される / throw すると publish されず、organ tick は毎周期 fallback fetch する = **呼び出しが持続的に2倍**。両ループの `now` が同じ分バケットに入れば `calendar-cache` の in-flight promise 共有で吸収されるので、常時ではなく位相依存 | 監視対象。#1d（予算そのものを下げる）で fetch 頻度が落ちれば露出も落ちる |
| `resolveDeparture` の可変長 | wake 対象イベント毎に Google Directions を**直列で**叩き、個別 timeout が無い。20秒予算の中で唯一長さが読めないブロック（予定3件 × 7秒で予算超過 → 放棄） | イベント毎 timeout か `Promise.all` 化。#1d と同時に扱う |
| `lm_event-cache` の evict 無し | TTL 超過でも Map から消さないので、退会したユーザーの payload がプロセス終了まで常駐 | ユーザー数比例の緩いリーク。数百人規模までは無害 |
| `deps.wake` の二義性 | `tick()` では organ 半分、`wakeTick()` では dial 半分を指す（既存テスト2件が `tick()` に `wake:` を注入しているため互換で残した） | `deps.organs` 一本化は既存テスト側の修正とセットで |

---

### 3.2 #1d の設計（2026-08-01 実測に基づく決定。キーの分解能を TTL に合わせる）

**実測（本番 Supabase `lm_api_cost` を自分で数えた）**

| 期間 | `composio_call` |
|---|---|
| 2026-07 合計 | **20,488**（`DEGRADE_AT` = 19,500 超過 → 7月中に tick が5分へ劣化していた） |
| 2026-08 直近1時間 | **157**（00:00 UTC に月次カウンタがリセットされ60秒へ復帰） |
| 現ペースの8月着地 | **約113,000**（約5日で再劣化） |
| 対象ユーザー | 2人 |
| 二重 fetch | 同一 uid が 02:20:52 と 02:20:53 に `GOOGLECALENDAR_EVENTS_LIST` を2回 |

**原因（構造）**

`lib/calendar-cache.js` の TTL は5分（`DEFAULT_TTL_MS`）。ところが `cacheKey()` は
`[uid, minuteBucket(timeMin), minuteBucket(timeMax)]` で、`timeMin/timeMax` は `lib/events.js:37` が
`nowMs` から作る。つまり **キーは毎分回る**。TTL が「5分前の答えでいい」と宣言しているのに、
キーがその答えに二度と辿り着けなくする。60秒 tick では**構造的に必ず miss**する。
キャッシュは存在するのに、一度も効いていない。

```text
 今                                     1d のあと
 tick t   key=[u|100|460]  → MISS 実fetch     tick t   key=[u|20|92] → MISS 実fetch
 tick t+1 key=[u|101|461]  → MISS 実fetch     tick t+1 key=[u|20|92] → ★HIT★
 tick t+2 key=[u|102|462]  → MISS 実fetch     tick t+2 key=[u|20|92] → ★HIT★
 …毎分 実fetch                                …5分に1回だけ実fetch
```

**決定**: `cacheKey` の分解能を **TTL と同じ幅**に落とす（`minuteBucket` → `bucket(value, ttlMs)`）。
TTL 自体は変えない。「5分古い答えを許す」という既存の宣言を、キーが実際に守るようにするだけ。

| 決定 | 理由 |
|---|---|
| TTL を延ばすのではなくキーを粗くする | 鮮度の契約（5分）は既に妥当。壊れているのは契約ではなく到達手段 |
| バケット幅 = TTL（別の knob を作らない） | 2つの knob がズレた瞬間に同じバグが再発する。1つの数字が両方を決める |
| ★wake の発火精度は据え置き★ | 発火判定は `now` と `startMs` の差で行う（fetch 時刻ではない）。5分古いリストでも T-10/T-5 の計算は正しい。影響を受けるのは**直前に作られた/変更された予定**だけで、最大5分。T-10 の余裕より短い |
| 二重 fetch も同時に消える | 1秒差の2呼び出しは同じバケットに落ちるので、`calendar-cache` の in-flight promise 共有が効く |
| Google の push 通知（watch channel）は採らない | 公開 endpoint + 更新管理が要る。効果は大きいが 1d の範囲を超える。予算が再び逼迫したら別 spec |

**この設計が守らないもの（正直に）**: 別 horizon の呼び出し（travel 30分ループ、ask 20分ループ、
panel、context-graph）は `timeMax` が違うので別キーのまま。1d が潰すのは支配項である60秒 wake tick。

## 4. 経路案内の実装方針（#4 の設計）

```
 予定（Google Calendar）
    │
    ▼
 Google Routes API v2  computeRoutes  travelMode=TRANSIT      ← 日本・米国 共通
    │   返る: transitLine（路線）/ headsign（行先）/ stopDetails（乗降駅・時刻）/ stopCount
    │   返らない: ★番線★ ★出口番号★
    ▼
 出口番号の付与（日本のみ・別データ源）
    │   鉄道事業者の公開データ（ODPT 等）を 駅 + 目的地方向 で引く
    │   取れない駅 → ★書かない★
    ▼
 Telegram に1通
```

| 国 | 経路 | 出口番号 |
|---|---|---|
| 日本 | Google Routes API v2 TRANSIT | 別データ源。取れた駅だけ表示 |
| 米国 | 同じ API・同じスキーマ | 概念が無い。表示しない（欠落ではなく仕様） |

---

## 5. UX — これが実装の目的（機能はこの体験を作るための手段）

### 5.0 約束（この3行が製品そのもの）

```
 ① もう遅刻しない        出発時刻は向こうから来る。予定表を開く必要が無い
 ② もう道に迷わない      経路は出た瞬間に届く。地図アプリを開く必要が無い
 ③ もう気まずくならない  遅れる時は、着く前に相手へ話が通っている
```

**ユーザーが用意する物 = スマホ1台と Telegram だけ。** それ以外を要求したら設計の失敗。
アプリのインストール不要・アカウント作成不要・地図アプリ不要・乗換アプリ不要・カレンダーを開く習慣も不要。

### 5.1 登録（1回だけ、チャットの中で終わる）

```text
 /start
   ├─ 名前（チャットに直接入力）
   ├─ 予定をつなぐ         → ボタン → /lm?tg=<chat_id>（OAuth はブラウザが1回開くだけ）
   ├─ メールをつなぐ       → ボタン
   ├─ 電話番号（任意）★#6★ → 未入力なら「Telegram だけで届けます」と明示
   ├─ ライブ位置を共有 ★#3★ 📎 → 位置情報 → ライブ位置情報（無期限）
   └─ 支払い               → ボタン
        ▼
   🎉「明日の朝から始めます。何もしなくていいです」
```

**この後、ユーザーが操作を覚える必要は無い。** コマンドは存在するが、知らなくても製品は成立する。

### 5.2 いつもの1日（届くのは最大3通）

```text
 07:40  出発前 ─────────────────────────────────────  #1
 ┌────────────────────────────────────────────┐
 │ ⏰ 9:00 打合せ / 渋谷スクランブルスクエア    │
 │ 8:05 に出て。あと 25分                     │
 │ [ 了解 ]        [ 15分ずらす ]             │
 └────────────────────────────────────────────┘
   ★ 反応が無ければ Telegram を連投して押し切る（下の 5.2.1）★
   → ここで「カレンダーを開く」という行為が消える

 08:06  家を出た（位置で検知）───────────────────  #3 + #4
 ┌────────────────────────────────────────────┐
 │ 🚶 中目黒まで徒歩7分                        │
 │ 08:12 中目黒 日比谷線・北千住行             │
 │ 08:21 霞ケ関で乗換                          │
 │ 08:31 渋谷 着 → ★ B2出口 ★ → 徒歩3分        │
 │ 到着 08:44 / 予定 09:00（16分 余裕）        │
 └────────────────────────────────────────────┘
   → ここで「地図アプリを開く」という行為が消える
   ★この1通で経路が完結する。以後は黙る★

 09:02  遅れ確定（到着予定 > 予定時刻）─────────  #5
 ┌────────────────────────────────────────────┐
 │ ⚠️ 5分ほど遅れます                          │
 │ 田中さん（tanaka@…）に送りますか?           │
 │「お世話になっております。交通事情により     │
 │  5分ほど遅れます。申し訳ございません。」    │
 │ [ 送る ]  [ 文面を直す ]  [ やめる ]        │
 └────────────────────────────────────────────┘
   → ここで「気まずい謝罪の文面を考える」が消える
   押すまで1通も飛ばない。既定は送らない側
```

**「最大3通」は "3種類の場面" の話であって、出発の押し切りは別枠**（下の 5.2.1）。経路と承認は
それぞれ1通のままで、増やしたら設計の失敗。

### 5.2.1 ★出発の押し切りは Telegram の連投で行う（電話ではない）★ — Dais 2026-08-01

**Dais verbatim**: "No meaning in rusuden no meaning. We must stop. Life manager can just message him on
telegram. that is much better. 連投もそこら辺いいしね。逆に better yes i think. posted a lot to telegram to
send me message is much better since it would hit me to actually leave to the place more!!"

**この決定を生んだ実測（§1.3）**: 直近4日の起床コール7本は**全部留守電**。全履歴でも `human` は3件、
`machine` は17件。Charon は毎回2分間留守電に向かって喋り、1本あたり約 $0.05 の Gemini Live を払っていた
（`hangup_source` は43件すべて `callee` = キャリアの録音上限で切られていた）。**人に一度も届かず、金だけ出ていた。**

| | 旧（廃止） | 新 |
|---|---|---|
| 出発の押し切り | 📞 電話（出るまで鳴る） | 💬 **Telegram 連投**。反応があるまで間隔を詰めて送る |
| 留守電に当たったら | 2分喋り続ける | **即切る**（そもそも既定では架けない） |
| 電話 | 既定 ON | **既定 OFF**。`call_enabled` を明示的に立てた人だけの追加チャンネル |
| 理由 | — | 電話は「出る」という1つの動作を要求する。Telegram は**画面に残り続ける**ので、出発という行動に直接効く（Dais の実感） |

**連投の形**（うるささではなく "残り続けること" が効く）

```text
 T-25  ⏰ 9:00 打合せ / 渋谷スクランブルスクエア
       8:05 に出て。あと 25分   [ 了解 ] [ 15分ずらす ]
 T-10  ⏰ あと10分で出る時間。8:05 出発
 T-5   ⏰ あと5分。そろそろ支度を終えて
 T-0   🚨 いま出る時間。8:05
 T+3   🚨 3分オーバー。今出れば 09:03 着（3分遅れ）
 T+7   🚨 7分オーバー。相手に連絡しますか?  [ 送る ] [ まだ ]
 ─────────────────────────────────────────────────
  [ 了解 ] を押した / 位置が動いた 時点で★即停止★
  停止条件が無い連投は嫌がらせであって製品ではない
```

**止め方が設計の本体**: ①`[ 了解 ]` を押す ②位置が動いて出発が検知される（#3）③予定時刻を過ぎて
late organ の領域に入る — のいずれかで打ち切る。押し切りは「反応が無い間だけ」続く。

**「留守電なら即切る」を電話の全経路に効かせる（#2d、2026-08-02）**: 2b で切れるようになったのは
scheduler が架ける wake 呼び出しだけだった。ダッシュボードの「Call me now」(`/test-call`) は
`client_state` を積んでいなかったので、Telnyx の検知 webhook が「これは誰の呼び出しか」を復号できず
`"no wake context"` で早期 return し、**hangup に到達する前に処理が終わっていた**。壊れていたのは
hangup ではなく**呼び出しが自分を名乗らない事**である。

直し方で意図的に選んだ3点:

| 決定 | なぜそうしないと壊れるか |
|---|---|
| 種類は **stream URL の query ではなく `client_state`** に持たせる（`placeCall({clientState})` を透過） | `buildStreamUrl` の query は `signCtx([summary, dateTime, location, urgency, lang, name, wakeUid, wakeEventKey])` で HMAC 署名され、`/ws` bridge が**同じ順序の同じ配列**で再計算して検証する。項目を1つ足すと署名の対象が片側だけ変わり、**全通話が bridge に拒否される**。引数なら署名と desync しようがない |
| test 呼び出しは **Supabase に一切書かない** | test 呼び出しに対応する `lm_wake_log` 行は**存在しない**（scheduler が作っていない）。`applyAmdDetection` を流用すると全 test call が `matched=0` を返し、「本物の wake 行が消えた」を意味するはずの §1.3 の警報が恒常ノイズになる。**信用できない証拠は、証拠が無いより悪い** |
| hangup 条件は wake と **完全に同一**（`human` 切らない / `not_sure` 切る / **空・欠落は誰も切らない**） | 空の result は AMD の判定ではなく payload の解析失敗。ここで切ると Telnyx の schema 変更1つが「全 test call が応答直後に死ぬ」に化ける（§1.3 の無音全損クラス）。逆に `not_sure` を残すと実測 machine 17 : human 3 の分布で 2分の課金発話を払い続ける。両経路が `shouldMarkAnswered()` を共有するので、**人間の定義を変えたら wake と test が一緒に動く** |

記録（証拠）と hangup（金）は**別々の失敗をする別々の関心事**である、というのが 2b から続く一貫した形:
wake 呼び出しは「記録してから切る」、test 呼び出しは「記録する先が無いので切るだけ」。どちらも
`human` には触れない。

### 5.2.2 連投の実装設計（#2c、2026-08-02）— 止め方が本体

5.2.1 は**体験**を決めた。ここは**誰がどの器で持つか**を決める。実装前に読んだ現状（実測）:

| 調べた事 | 実測 |
|---|---|
| 出発の Telegram 通知 | **存在しない**。「time to leave now」は `lib/call-logic.js:420` の**電話の台詞だけ**。Telegram 側は全部「事後」（`formatLateSuccessMessage` / travel ブロック挿入通知 / `wakeMissNotice`） |
| 既存の梯子 | `scheduler.js:60-63` `WAKE_LEVELS = [{min:10},{min:5}]` の2段。5.2.1 が要求するのは6段 |
| 停止の器 | 全 organ が `(uid, event_key)` unique + claim の同じ型（`lm_wake_log` / `lm_wake_miss` / `lm_late_notice_log` / `lm_ask_log` / `lm_travel_log`） |
| ボタン | `routeCallbackData`（`lib/telegram.js:107-116`）が `prefix:...` で分岐。押した跡は `reflectAnswer` が元メッセージを編集してキーボードを剥がす（`"\n\n→ "` マーカーで冪等） |
| 位置からの出発検知 | **未実装**（= #3） |

#### 決定

| # | 決定 | そうしないと何が壊れるか |
|---|---|---|
| D1 | 梯子は **wake tick が持つ**（`wakeCallOnce` と同じ tick・同じ `resolveDeparture`）。organ tick には置かない | 出発の押し切りは**時間に敏感な唯一の仕事**。1c で dial を organ から切り離したのと同じ理由で、他 organ の遅さに巻き込まれた瞬間に「出る時間に届かない通知」になる。通知1本は HTTP 1回 ≒ 200ms で、1c が守った20秒予算を脅かさない |
| D2 | 段は **`NUDGE_LEVELS = [25, 10, 5, 0, -3, -7]`（出発時刻からの分）**。`WAKE_LEVELS`（電話）は**触らない** | 電話は既定 OFF の追加チャンネル（5.2.1）。同じ配列にすると、電話を有効にした人だけ梯子が変わる/無効にした人の梯子が消える、という結合が生まれる |
| D3 | 器は **新テーブル `lm_departure_nudge`、PK `(uid, event_key)` = 1予定1行**（段ごとの行ではない）。列 = `last_level_min` / `acked_at` / `ack_reason` / `last_message_id` / `created_at` | `lm_wake_log` に相乗りすると、あの表の意味（= 電話を1本かけた）と `amd_result` / `answered_at` の census（machine 17 : human 3、§1.3）が push で汚れる。**信用できない証拠は証拠が無いより悪い**（2d と同じ理由） |
| D4 | 段の claim と停止判定は **1回の PATCH に融合**する: `uid=eq.&event_key=eq.&acked_at=is.null&last_level_min=gt.<level>` で `last_level_min=<level>` を書き、`return=representation` の行数が1なら送る・0なら送らない | 「送ってよいか」を読んでから書くと、60秒 tick が重なった時に同じ段が2回出る。読み書きを分けた瞬間に競合が生まれる — 既存の `claimWake` が INSERT の unique 制約に賭けているのと同じ思想を、単調減少する `last_level_min` で表現する |
| D5 | v1 の停止条件は **①`[了解]` タップ ②late organ への移行（出発 +15分 = `LATE_CUTOFF_MIN`）③電話に出た（`lm_wake_log.answered_at` が入っている）**。★位置移動（5.2.1 の②）は #3 の実装時に配線する差込口だけ作る★ | 位置検知は未実装（#3）。無い停止条件を設計に書いて「実装した」ことにするのが一番危ない。**電話に出た** を足すのは、あれが「反応した」の最強の証拠だから — 出た人に連投を続けるのは嫌がらせ |
| D6 | T+7 は梯子の**終端**。相手への連絡（`[送る]`）は **late organ の仕事のまま**にして、梯子は複製しない | `processLocationLateNotice` が既に `lm_late_notice_log` で1予定1通を保証している。同じ行為を2つの organ が持った瞬間、片方を直しても本番が直らない（§0.17 の SSOT） |
| D7 | callback は新 prefix **`depart:ack:<startIso>`**（uid は Telegram の chat から引く）。押した跡は既存 `reflectAnswer` に任せる | 既に4種類（`ask` / `diet` / `precepts` / `payout`）が同じ形で動いている。ここだけ独自形式にする理由が無い。callback data は 64 byte 上限があるので uid を載せない |
| D8 | 5.2.1 の `[15分ずらす]` は **v1 に入れない**（別 row として残す） | あれはカレンダーを書き換える操作で、`patchEvent` と予定の再計算を巻き込む。連投そのものの検証を、書き換えの検証と混ぜない |

#### 送る文（ja / en は既存 `langForUser` + `lib/i18n.js` の流儀に合わせる）

```text
 T-25  ⏰ 9:00 打合せ / 渋谷スクランブルスクエア
       8:05 に出て。あと 25分            [ 了解 ]
 T-10  ⏰ あと10分で出る時間。8:05 出発    [ 了解 ]
 T-5   ⏰ あと5分。そろそろ支度を終えて    [ 了解 ]
 T-0   🚨 いま出る時間。8:05              [ 了解 ]
 T+3   🚨 3分オーバー。今出れば 09:03 着（3分遅れ）  [ 了解 ]
 T+7   🚨 7分オーバー。               ← 梯子はここで終わる（以後は late organ）
```

#### この設計が守っていること

1. **停止が先、送信が後**: 送るかどうかを決める PATCH が、停止フラグ（`acked_at`）と同じ行・同じ1回の書き込みで解決される。止め忘れが構造的に起きない。
2. **段は単調**: `last_level_min` が減る方向にしか動かないので、tick が遅れて2段まとめて due になっても**出るのは最も緊急な1段だけ**（1a が電話で確立した形をそのまま押し込む）。
3. **電話と独立**: 番号を出していない人（#6・既定）にも全段が届く。電話は「出た瞬間に梯子を止める」入力として参加するだけ。

### 5.3 電話番号を出さない人（#6）→ **もはや既定がこちら**

```text
       既定（電話なし）                電話を明示的に有効にした人
 07:40  💬 連投で押し切る（5.2.1）      同じ連投 ＋ 📞（留守電なら即切る）
 08:06  💬 経路1通                      💬 同じ経路1通
 09:02  💬 承認カード                   💬 同じ承認カード
 ─────────────────────────────────────────────────
   判定エンジンは1つ。届け先が2つ。★電話は付加であって前提ではない★
```

### 5.4 うまく行かない日（ここが信頼を決める）

| 事象 | ユーザーに見える物 | 黙って壊れない保証 |
|---|---|---|
| 位置が来ていない | 「位置が3時間届いていません。共有し直しますか?」+ ボタン | `observed_at` の経過で判定（#3） |
| 呼び出しが鳴らせなかった | 「8:05 の呼び出しに失敗しました。今から出れば間に合います」 | 逃した呼び出しを記録する（#1b） |
| 経路が取れない | 「経路が取れませんでした。所要は約35分です」 | 推測の出口番号を書かない（#4） |
| 予定の場所が不明 | 「どこでやりますか?」と1回だけ聞く | 既存の ask organ |

**原則**: 沈黙で失敗しない。ユーザーが「今日は来なかったな」と気付く前に、こちらから言う。

### 5.5 コマンド（覚えなくていいが、ある）

| command | 何が起きる |
|---|---|
| `/status` | 次の予定・出発時刻・位置の最終受信（`observed_at` からの経過）・直近の失敗 |
| `/where` | 今どこにいると認識しているか。ずれていたら共有の張り直しを案内 |
| `/stop` | 今日の呼び出しを止める |
| `/panel` | web パネル（履歴と設定だけ。日常では開かない） |

### 5.6 この後 chat の中に増えていく物（同じ形を守る）

daily が閉じたら、同じ「チャットで完結・承認は1タップ・最大3通」の型のまま面を増やす。

| 順 | 何 | 体験（形は同じ） |
|---|---|---|
| 次 | 予約（歯医者・美容室・レストラン） | 「金曜18時で取れます。予約しますか? [ 取る ][ やめる ]」 |
| 次 | 移動の手配（航空券・ホテル・新幹線） | 「この便が最安です。押さえますか? [ 押さえる ][ 他を見る ]」 |
| 次 | お金（口座・支出・請求） | 「今月は先月比 +¥32,000。原因はこれです」 |
| 後 | physical / mental（親 spec Order 36） | 同じ1通の形 |

**新しい画面を作らない。** 増えるのは通知の種類だけで、操作は常に「ボタン1つ」。
ユーザーがチャット以外を理解する必要が無い状態を、機能追加のたびに守る。

---

## 6. なぜ日次で価値があるか（課金の形）

| 事実 | 帰結 |
|---|---|
| 遅刻・道迷い・気まずさは **毎日** 発生する | 価値の発生も毎日。月1回まとめて価値を出す製品ではない |
| 1回の遅刻の損失（信用・機会）は月額を軽く超える | 「1日1回助かれば元が取れる」が説明として成立する |
| 動き続けることが前提 | **落ちている日はゼロ円の価値**。だから #1b（失敗を記録して自分から言う）が課金の前提条件 |

**課金の設計原則**: 「毎日効いている」ことを毎日見せられる製品だけが日次・秒次の課金を正当化できる。
だから通知は少なく、しかし**助けた瞬間は必ず可視**にする（出発の1通・経路の1通・承認の1通が領収書を兼ねる）。

---

## 7. 出荷までに起きること

| 段 | 条件 | 判定 |
|---:|---|---|
| 1 | #1（1a/1b/1c）+ #2 + #3 | 実予定で呼び出しが鳴り、出たかが記録され、出発が検知される。**逃した時は自分から言う** |
| 2 | #4 | ★ Dais が Google Maps を消す ★ = daily の合格判定。他の指標は見ない |
| 3 | #5 + #6 | 他人に渡しても事故らない（無断送信0・番号なしでも全部届く） |
| 4 | 友達3人に配る | 見るのは1つ:「Maps を消したか」。消さないなら理由を聞き、その1点だけ直す |
| 5 | 公開 | 3人中2人以上が1週間 Maps を消したまま過ごしたら出す。売り文句は「乗換案内アプリの代わり」ではなく **「もう調べなくていい」** |

---

## 8. アーキテクチャと folder tree（どこで何が動くか）

### 8.1 repo の正体

`Daisuke134/life-manager`（repo ID 1248111245）は **anicca を改名・統合した monorepo**。
散らばっていた物を1つに寄せる先がここ。旧 `life-manager-v0`（ID 1273052304）は archive 済み・redirect のみ。

| 中に入っている物 | 場所 |
|---|---|
| Life Manager 本体（API・panel・Telegram・reports・scheduler） | `apps/life-manager/` |
| web（landing / `/lm` 登録画面） | `apps/landing/`（`app/` + `netlify/` functions） |
| 求人 loop | `apps/job-search-loop/` |
| provider/transport 境界 | `adapters/` |
| 可搬 scheduler / worker runtime | `runtime/` |
| 常駐サービス（x402 endpoint 等） | `services/` |
| 汎用能力（**製品の credential を持たない**） | `skills/` |
| 配置定義 | `deploy/local/compose.yaml`（ローカル一式）· `apps/life-manager/railway.toml`（本番） |
| 仕様の正本 | `docs/superpowers/specs/` · 実行スライス = `docs/superpowers/plans/` |
| Anicca 側の身元・状態 | `identity/` · `state/` · `control-room/` · `templates/` |

親 spec §6.1 が layout の SSOT。`packages/*`（loop-core / job-protocol / finance-engine /
marketing-engine / product-packs …）は**目標形**で、現状は既存慣習を優先している。

### 8.2 今の実行系（2026-08-01 実測）

```text
                    ┌──────────────── ユーザーのスマホ ────────────────┐
                    │  Telegram（日常の全操作）      ブラウザ（登録のみ）│
                    └───────┬───────────────────────────────┬─────────┘
                            │ webhook / 通知 / ライブ位置      │ 1回だけ
                            ▼                                 ▼
        ┌──────────────────────────────────┐      ┌──────────────────────────┐
        │  Railway  service = life-call    │      │  Netlify  apps/landing   │
        │  = apps/life-manager             │      │  aniccaai.com/lm         │
        │   server.js  … /telegram /ws /api│      │   Google login → OAuth   │
        │   scheduler.js 60s tick          │◀─────│   → Stripe               │
        │     ├ wake   T-10 / T-5 の呼び出し│      └──────────────────────────┘
        │     ├ travel 30分毎 [Travel] 挿入 │
        │     ├ late   遅刻検知 → 連絡      │
        │     └ ask / mental / care / diet │
        └───────┬───────────────┬──────────┘
                │               │
                ▼               ▼
   ┌────────────────────┐  ┌──────────────────────────────────────┐
   │ Supabase (Postgres)│  │ 外部 API                              │
   │  lm_users          │  │  Composio  → Google Calendar          │
   │  lm_wake_log       │  │  Unipile   → Gmail 送信               │
   │  lm_travel_log     │  │  Google Maps / Routes → 移動時間・経路 │
   │  lm_ask_log        │  │  Telnyx + Gemini Live → 音声通話      │
   │  lm_user_locations │  │  Stripe    → 課金                     │
   └────────────────────┘  └──────────────────────────────────────┘

   ローカル（deploy/local/compose.yaml）: api / scheduler / worker / postgres:18 / minio
     → 現状 credential 未投入 = ユーザー0人 = 何も発火しない「空の器」（§1.2）
```

| 問い | 今の答え |
|---|---|
| daily はクラウドで動くのか | **動く。Railway `life-call`**（Mac が落ちていても継続） |
| データはどこ | **Supabase**（`lm_*` テーブル）。ローカル compose は自前 postgres を持つが本番データではない |
| web は同じ repo か | **同じ。`apps/landing`**（Netlify 配信、登録と決済だけ） |
| Mac は要るか | 日常運用には**不要**。ローカル一式は移行検証用 |

### 8.3 目標形（親 spec の Order。daily 出荷後に効いてくる）

```text
 今                                   目標
 Railway life-call（単一 service）  →  Railway 上に API / scheduler / worker pool を分離
 Supabase                           →  Life Manager 所有の managed Postgres（tenant 分離・quota）
 launchd + OpenClaw の残り          →  すべて Life Manager の job（Order 15 で OpenClaw-free）
 単一テナント運用                   →  月額の multi-tenant（Order 25）・1,000 tenant 検証（Order 26）
```

**daily の出荷はこの移行を待たない。** 今の Railway + Supabase で段5（公開）まで到達できる。

## 9. 更新規律

daily の TODO 状態が変わった瞬間にこのファイルを更新して commit する。
番号は**実行順**であり、消化しても振り直さない（済んだ行に done receipt を書く）。
UX（§5）は spec の一部である — チャットで新しい体験を語ったら、その場でここに焼き直す。
`~/anicca-project` 側の同名ファイルは正本を指すポインタであり、そこを編集しない。
