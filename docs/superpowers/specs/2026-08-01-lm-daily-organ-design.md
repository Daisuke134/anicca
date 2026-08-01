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

### 1.3 未解決の観測

`lm_wake_log` 全履歴で `answered_at` が null（id 960/961/962 すべて）。「出ていない」のか「記録漏れ」のか未判別。
**鳴っているが機能していない**可能性が残るので #2 で判別する。

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

| # | 作業 | 無いと何が起きるか | done（実 receipt） |
|---:|---|---|---|
| **1** | ~~呼び出し不発の原因究明~~ → **原因特定済（§1.2）。残りは修正3点** | 呼び出しが静かに消える = 製品が存在しない | ①窓を「取りこぼさない」形に変更（下記 1a）②逃した呼び出しを記録（1b）③時間に敏感な loop を他 organ から分離（1c）。実予定で T-10/T-5 が両方 `lm_wake_log` に載る |
| 1a | ~~発火条件を「2分の窓」から**追い付き方式**へ~~ ✅ **DONE 2026-08-01**（commit `da7dec52b`、merge `9873e0ce9`） | tick が遅れた瞬間に永久に失われる | 実装: `scheduler.js` の窓判定を撤廃し `mins <= lvl.min+0.5 && mins > LATE_CUTOFF_MIN(-15)` で due 判定 → **最も緊急な1件だけ発信**、超えられた粗いレベルは claim だけして鳴らさない。検証（自分で実行）: `node --test test/wake-catchup.test.js` → `tests 5 / pass 5 / fail 0`、`node test/scheduler.test.js` → PASS。cases = ①T-5 を5分過ぎた tick でも1本鳴る ②通常は T-10 → T-5 の2本 ③両方 due の tick でも1本 ④出発を15分超過なら鳴らさない ⑤発信失敗で claim が解放され次 tick が再試行 |
| 1b | ~~「鳴るはずだったのに鳴らなかった」を記録~~ ✅ **DONE 2026-08-01** | 失敗が**存在しない事象**に見える（今回の3日を溶かした原因） | 実装: 新 ledger `lm_wake_miss`（`migrations/2026-08-01-lm-wake-miss.sql`、本番 Supabase に適用済 = `http=201`、PostgREST 読み取り `http=200`）+ `lib/wake-miss.js` + `scheduler.js` の `noteWakeMiss()` + `/status` の1行。記録する2事象 = ①`dial_failed`（`releaseWake` が claim を消す**前**に理由を残す）②`no_call_before_departure`（departure が `LATE_CUTOFF_MIN` を越えた時点で最細レベルの claim が無い = 一度も試みていない）。`(uid,event_key)` 主キー + merge-duplicates upsert なので 60秒 tick の連続失敗は1行を更新するだけ。`first_seen_at` は payload に入れないので「いつ壊れ始めたか」が保持される（実測: first_seen_at=01:04:57.5 / occurred_at=01:04:58.9）。★§5.4 の「自分から言う」も実装★ = `notified_at IS NULL` を条件にした PATCH を lock にして**1 miss につき Telegram 1通だけ**送る（retry tick は無言）。検証（自分で実行）: `node --test lib/wake-miss.test.js lib/slash-command.test.js test/wake-miss-record.test.js test/wake-catchup.test.js test/telegram-slash-http-contract.test.js` → **tests 55 / pass 55 / fail 0**（1a の回帰5件を含む）+ 本番 Supabase への実 round-trip（write → upsert → read → `/status` 行 `🔔 Missed: the 13:15 call could not be dialled (...)` → 検証行を DELETE、表は空に戻した） |
| 1c | ~~呼び出し loop を care / diet / mental / late から分離~~ ✅ **DONE 2026-08-01**（設計 = §3.1 方式A） | 他 organ の遅さが呼び出しを殺す。ユーザーが増えるほど悪化 | 実装: `wakeUserOnce` を **`wakeCallOnce`（poll + fetch + event 公開 + 発信のみ）** と **`organsUserOnce`（8 organ）** に分割し、`wakeUserOnce` は両者の合成として温存（Inngest `makeWakeUserHandler` と既存 suite がこの名前を呼ぶ）。新規 `lib/event-cache.js` = wake tick が fetch を所有し organ tick は読むだけ（`calendar-cache` のキーが分単位で回るため、素朴に2ループへ分けると Composio が倍増する）。新規 `lib/organ-run.js` = 全 organ を `[organ:<name>] uid=… ms=…` で計測（成功は stdout・失敗は stderr）。`startWakeLoop()` = **固定60秒・user 毎 20秒**（`WAKE_USER_TIMEOUT_MS`）、`schedulerPollInterval()` を意図的に使わない（#1d の劣化を dial に波及させない）。`tick()` は organ 側へ。`maybe-start-loops.js` + `server.js` で本番起動に配線。★review 指摘の修正込み★: H-1 dial 前の `recordDailyComposioPoll` await を fire-and-forget 化（20秒予算を会計処理が食う = 潰したはずの構造の縮小版だった）/ H-2 `claimWake` に `claim_token` を持たせ `releaseWake` を所有権付きに（migration `2026-08-01-lm-wake-log-claim-token.sql` を本番 Supabase へ適用済 `http=201` / `read_http=200`。放棄された tick が後続の**成功した** claim を消して**二重架電**する経路を封鎖）/ M-4 organ の失敗ログを stderr へ戻す。検証（自分で実行）: `node --test` 10 files → **tests 104 / pass 104 / fail 0**、`node -e` で `startWakeLoop / wakeTick / wakeCallOnce / organsUserOnce = function` + `WAKE_USER_TIMEOUT_MS = 20000`。★最重要 assertion は mutation で kill 確認済★ = 全 organ を 5000ms stall させて `wakeCallOnce` が 1.5ms で完走（分割前の順序を復元した mutant では 5007ms で RED） |
| 1e | organ tick の `call_enabled !== false` filter を外す | dial が別 loop に出た今、**電話番号を出さない人（#6）に care/diet/mental/precepts/relations が1つも届かない**。`organsUserOnce` の care コメント「Still runs for call-disabled users」と実コードが矛盾 | 電話無効の test user で organ が走る。`tick()` の filter は `daily_automation_enabled` のみ |
| 1d | Composio 予算超過で tick が5分に落ち、**wake の精度自体が壊れる**のを止める（**設計 = §3.2**） | 7月は実測 20,488 で既に劣化済。8月も現ペースで約5日で再劣化 = 製品が毎月半分は5分刻みで動く | 月間 `composio_call` 実測が 20,000 未満（現ペース113,000から）。同一 uid の1秒差 二重 fetch が消える。`wake-catchup` の回帰が緑 = 発火精度据え置き |
| **2** | `answered_at` が常に null の判別 | 「鳴っているが誰も出ていない」= 核心が空洞、を検知できない | 実際に出た1回で入り、出なかった1回で入らないことを確認。入らないなら記録経路を直す |
| **3** | 位置を「家を出た」判定に接続（鮮度は `observed_at`） | 位置が来ていても使わなければ案内が始まらない | 実予定1件で出発検知 → 出発直後の1通が実配信。`updated_at` を鮮度に使う箇所が 0 |
| **4** | 乗換ステップ + 出口番号 | **これが無いと Google Maps を消せない** = 商品の主張が嘘になる | 実イベント1件で経路1通が届き、Maps を開かずに着いた。出口が取れない駅は**黙って省く**（推測で書かない） |
| **5** | 1タップ承認 | 無断で相手にメールが飛ぶ。友達に渡した瞬間に事故る | 押すまで送信0・押したら実送信、両方確認 |
| **6** | 電話番号なしでも動く | 3人のうち少なくとも1人は番号を出さない。今はその人に何も起きない | 番号未登録の test user で、出発通知 → 経路 → 承認まで全部 Telegram に届く |

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
   電話番号を登録した人は同時に📞（出るまで鳴る）
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

**予定1件につき最大3通。** これを超えたら設計の失敗（通知が多い製品は消される）。

### 5.3 電話番号を出さない人（#6）

```text
       電話あり                    電話なし
 07:40  📞 着信（出るまで鳴る）     🔔 通知（既読まで再送 3回）
 08:06  💬 経路1通                  💬 同じ経路1通
 09:02  💬 承認カード               💬 同じ承認カード
 ─────────────────────────────────────────────────
   判定エンジンは1つ。届け先が2つ。片方だけ動く実装にしない。
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
