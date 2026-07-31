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
| これは何の製品か | **Telegram で動く通勤エージェント**。予定の時刻に呼び出し、家を出てから着くまで案内し、遅れたら相手に断りを入れる |
| 誰が使うか | Dais（本人）→ 友達3人 → 一般公開。全員 **Telegram だけ**で日常を完結させる。web パネルは設定と履歴だけ |
| コードはどこか | `apps/life-manager/`（branch `docs/two-earning-loops`）。`scheduler.js`（呼び出し loop）· `lib/wake-filter.js`（鳴らす予定の選別）· `lib/travel.js`（`[Travel]` block 生成）· `lib/late-notice.js`（遅刻連絡・ライブ位置削除）· `lib/slash-command.js`（Telegram コマンド router） |
| どこで動いているか | Railway（cloud、multi-tenant）。ローカル compose も同一コード |
| データはどこか | Supabase。`lm_users` `lm_wake_log` `lm_travel_log` `lm_ask_log` `lm_user_locations` |
| 状態の見方（★実行可能★） | `set -a; . ~/.openclaw/.env; set +a` の後、`curl -s "$SUPABASE_URL/rest/v1/<table>?select=*&order=…&limit=3" -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"`。**鍵を stdout に出さない** |
| ★間違えやすい点★ | canonical は **`Daisuke134/life-manager`**。`anicca-project`（= anicca-products）にある LM spec の写しは**正本ではない**。`~/.openclaw/skills/anicca-life-manager/` は OSS/BYOK 単身版であって本番ではない |
| 触ってはいけない | writer loop・記事・SNS・収益 loop（別 agent 担当）。physical / mental organ（platform Order 36、daily 出荷後） |

**daily 単体で商品になる**。physical / mental を待たずに出す。

---

## 1. 今日の実測（2026-08-01 06:41 JST、この session で自分が叩いた結果）

前 session の報告と**結論が変わった項目がある**。以下は自分で curl した生の値。

| 観測 | 実測値 | 意味 |
|---|---|---|
| ★ライブ位置は届いている★ | `lm_user_locations`: `observed_at=2026-07-31T21:41:01Z`、取得時刻 `21:41:15Z` = **14秒前**。`latitude=35.6796 / longitude=139.723085`、`source=telegram_live_location` | 「07-21 から止まっている」は**誤り**。今この瞬間に流れている |
| 逆ジオコード | `南元町, 新宿区, 東京都, 160-8484`（Nominatim） | 自宅と一致。位置は**使える精度で来ている** |
| ★誤診の原因（強い仮説）★ | 同じ行の `updated_at` は **`2026-07-21T02:35:07Z` のまま**。upsert が `observed_at` だけ更新し `updated_at` を触っていない | 前回「未達」と判定したのは、**鮮度を見る列を間違えた**可能性が高い。読む列は `observed_at` |
| 呼び出しは鳴っている | `lm_wake_log` 最新 = `id=962`, `called_at=2026-07-30T22:59:40Z`, `event_key=…|2026-07-31T08:40:00+09:00|5` | 朝の実予定に対する **T-5 は実発火している** |
| ★不発は深夜テストの側★ | 01:30 JST（=`16:30Z`）の試験に対応する行が**無い** | 「常に鳴らない」ではなく「**あの条件で鳴らない**」。原因究明の的が狭まった |
| ★未解決★ | `lm_wake_log` 全履歴で `answered_at` が null（id 960/961/962 も null） | 「出ていない」のか「記録漏れ」のか未判別。**鳴っているが機能していない**可能性が残る |

**教訓（一般化）**: 「動いていない」と判定する前に、**自分が見ている列/経路が正しいか**を先に疑う。
派生値（`updated_at`）ではなく、書き手が実際に更新する列（`observed_at`）を見る。

---

## 2. 外部調査（2026-08-01、一次資料）

| 論点 | 結論 | 出典 |
|---|---|---|
| Telegram ライブ位置の更新頻度 | **Bot API に更新間隔の規定は無い**。`edited_message` として push されるが、送信側クライアント（OS の背景位置制限込み）が頻度を決める。SLA は無い | core.telegram.org/bots/api §editMessageLiveLocation |
| `live_period` | 60–86400 秒、または `0x7FFFFFFF` で**無期限** | 同上 §sendLocation:「must be between 60 and 86400, or 0x7FFFFFFF for live locations that can be edited indefinitely」 |
| 位置の誤差 | `horizontal_accuracy` = 0–1500 m | 同上 §Location:「The radius of uncertainty for the location, measured in meters; 0-1500」 |
| ★設計への帰結★ | **秒単位の追従を前提にした案内を作らない**（「次で乗換」「前から3両目」等は禁止）。位置は「家を出たか / 大きく遅れているか」の**粗い判定にだけ使う** | 上記の SLA 不在から |
| 乗換ステップ（日本・米国） | **Google Routes API v2 `computeRoutes` TRANSIT** が両国で同一スキーマ。`transitDetails.transitLine`（路線名）· `headsign`（行先）· `stopDetails`（乗降駅・時刻）· `stopCount` を返す。$5.00 / 1,000 calls（Essentials） | developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRoutes、同 billing-and-pricing |
| ★出口番号★ | **Routes API にも Transitland/OTP にも出口番号のフィールドは無い**。番線（platform）も無い | 同上スキーマ確認 |
| 出口番号の入手先 | 日本固有データ。鉄道事業者の公開データ（ODPT 等）を**別途引く**必要がある。米国は GTFS に出口番号の概念が無い | odpt.org、Transitland documentation |
| 保留（未検証） | NAVITIME / Ekispert の実レスポンス項目は docs が JS 描画で読めず未確認。出口番号が要るなら**試用キーで実 call して確かめる**のが唯一の道 | docs.ekispert.com（MCP server 有り）· NAVITIME(RapidAPI) |

---

## 3. 残 TODO（1 から順に。番号は実行順そのもの）

| # | 作業 | 無いと何が起きるか | done（実 receipt） |
|---:|---|---|---|
| **1** | 呼び出し不発の原因究明（深夜条件で鳴らない） | 鳴らなければ製品は存在しない。友達に配る前の最優先 | 深夜条件で鳴らなかった理由を**1つに特定**し、仕様（意図的な抑制）か欠陥かを判定。欠陥なら修正して同条件で `lm_wake_log` に新 id |
| **2** | `answered_at` が常に null の判別 | 「鳴っているが誰も出ていない」= 核心が空洞、を検知できない | 実際に出た1回で `answered_at` が入り、出なかった1回で入らないことを確認。入らないなら記録経路を直す |
| **3** | 位置を「家を出た」判定に接続（鮮度は `observed_at` で読む） | 位置が来ていても使っていなければ案内も遅刻検知も始まらない | 実予定1件で「出発検知 → 出発直後の1通」が実配信。`updated_at` を鮮度に使っている箇所が0 |
| **4** | 乗換ステップ + 出口番号 | **これが無いと Google Maps を消せない** = 商品の主張が嘘になる | 実イベント1件で「◯◯線・行先 → □□で乗換 → 到着 → **出口** → 徒歩N分」が Telegram に実配信され、Maps を開かずに着いた。出口番号が取れない駅は**黙って省く**（嘘を書かない） |
| **5** | 1タップ承認 | 無断で相手にメールが飛ぶ。友達に渡した瞬間に事故る | 遅刻1件で承認カードが届き、**押すまで送信0**・押したら実送信、両方を確認 |
| **6** | 電話番号なしでも動く | 3人のうち少なくとも1人は番号を出さない。今はその人に何も起きない | 番号未登録の test user で、出発通知 → 経路 → 承認まで全部 Telegram に届く |

**順序の理由**: 1→2 は「鳴る・出たか分かる」= 製品の心臓。3 は 4 の前提（出発を検知できないと案内を始められない）。
5 は他人に渡す前の安全弁。6 は3人目を拾う口。**番号は飛ばさない。**

### #1 の仮説（潰した物・残った物をここに追記していく）

| 仮説 | 見る場所 | 状態 |
|---|---|---|
| 深夜は意図的に抑制されている（旧実装は `*/5 6-23`） | `scheduler.js` の tick 条件、`WAKE_LEVELS`、時間帯ガード | **最有力・未検証** |
| `wake-filter` の除外に当たった（travel-only 既定 / `wake_policy` / routine 除外） | `lib/wake-filter.js` | 未検証 |
| 6h horizon の外だった／`[Travel]` block と event の突合 tolerance を外れた | `scheduler.js:290`（6h horizon）、`lib/wake-filter.js:27`（tolerance） | 未検証 |
| Composio がまだイベントを見ていなかった | calendar 取得の horizon とキャッシュ | 未検証 |
| 発信例外（Telnyx 側）が握り潰されている | 発信ログ、例外処理 | 未検証 |

---

## 4. 経路案内の実装方針（#4 の設計）

```
 予定（Google Calendar）
    │
    ▼
 Google Routes API v2  computeRoutes  travelMode=TRANSIT      ← 日本・米国 共通
    │   返る物: transitLine（路線名）/ headsign（行先）/ stopDetails（乗降駅・時刻）/ stopCount
    │   返らない物: ★番線★ ★出口番号★
    ▼
 出口番号の付与（日本のみ・別データ源）
    │   鉄道事業者の公開データ（ODPT 等）を駅+目的地方向で引く
    │   取れない駅 → ★書かない★（「N番出口」を推測で書くのは禁止）
    ▼
 Telegram に1通（下の 5.2）
```

| 国 | 経路 | 出口番号 |
|---|---|---|
| 日本 | Google Routes API v2 TRANSIT | 別データ源。取れた駅だけ表示 |
| 米国 | Google Routes API v2 TRANSIT | **存在しない概念**。表示しない（欠落ではなく仕様） |

**禁止**: 位置に秒単位で追従する案内（「次で乗換」「前から3両目」）。§2 の通り Telegram のライブ位置に
更新頻度の保証が無いため、**遅れた情報で人を動かす**ことになる。出すのは **出発前 1通 + 出発直後 1通** が既定。

---

## 5. UX — 全員が触るのは Telegram（web は設定と履歴だけ）

### 5.1 登録（1回だけ）

```text
 /start
   ├─ 名前（チャットに直接入力）
   ├─ 予定をつなぐ         → ボタン → /lm?tg=<chat_id>（OAuth は web）
   ├─ メールをつなぐ       → ボタン
   ├─ 電話番号（任意）★#6★ → 未入力なら「Telegram だけで届けます」と明示
   ├─ ライブ位置を共有 ★#3★ 📎 → 位置情報 → ライブ位置情報（無期限 = live_period 0x7FFFFFFF）
   └─ 支払い               → ボタン → Stripe
        ▼
   🎉「明日の朝から始めます。何もしなくていいです」
```

### 5.2 いつもの1日（届くのは3通だけ）

```text
 07:40  出発前 ─────────────────────────────────────  #1
 ┌────────────────────────────────────────────┐
 │ ⏰ 9:00 打合せ / 渋谷スクランブルスクエア    │
 │ 8:05 に出て。あと 25分                     │
 │ [ 了解 ]        [ 15分ずらす ]             │
 └────────────────────────────────────────────┘
   電話番号を登録した人は同時に📞（出るまで鳴る）

 08:06  家を出た（位置で検知）───────────────────  #3 + #4
 ┌────────────────────────────────────────────┐
 │ 🚶 中目黒まで徒歩7分                        │
 │ 08:12 中目黒 日比谷線・北千住行             │
 │ 08:21 霞ケ関で乗換                          │
 │ 08:31 渋谷 着 → ★ B2出口 ★ → 徒歩3分        │
 │ 到着 08:44 / 予定 09:00（16分 余裕）        │
 └────────────────────────────────────────────┘
   ★これ1通で経路が完結する。以後は黙る★

 09:02  遅れ確定（到着予定 > 予定時刻）─────────  #5
 ┌────────────────────────────────────────────┐
 │ ⚠️ 5分ほど遅れます                          │
 │ 田中さん（tanaka@…）に送りますか?           │
 │「お世話になっております。交通事情により     │
 │  5分ほど遅れます。申し訳ございません。」    │
 │ [ 送る ]  [ 文面を直す ]  [ やめる ]        │
 └────────────────────────────────────────────┘
   押すまで1通も飛ばない。既定は送らない側
```

**1日の総通知数 = 予定1件につき最大3通**（出発前・出発直後・遅刻時のみ）。これを超えたら設計の失敗。

### 5.3 電話番号を出さない人（#6）

```text
       電話あり                    電話なし
 07:40  📞 着信（出るまで鳴る）     🔔 通知（既読まで再送 3回）
 08:06  💬 経路1通                  💬 同じ経路1通
 09:02  💬 承認カード               💬 同じ承認カード
 ─────────────────────────────────────────────────
   判定エンジンは1つ。届け先が2つ。片方だけ動く実装にしない。
```

### 5.4 コマンド（覚えなくていいが、ある）

| command | 何が起きる |
|---|---|
| `/status` | 次の予定・出発時刻・位置の最終受信（`observed_at` からの経過） |
| `/where` | 今どこにいると認識しているか。ずれていたら位置共有の張り直しを案内 |
| `/stop` | 今日の呼び出しを止める |
| `/panel` | web パネル（履歴と設定だけ） |

**出さないもの**: 実験ボタン・内部ジョブの実況・公開アーティファクトのページ（親 spec §12 Order 9 と同じ規律）。

---

## 6. 出荷までに起きること

| 段 | 条件 | 判定 |
|---:|---|---|
| 1 | #1 + #2 + #3 | 実予定で呼び出しが鳴り、出たかどうかが記録され、出発が検知される |
| 2 | #4 | ★ Dais が Google Maps を消す ★ = daily の合格判定。他の指標は見ない |
| 3 | #5 + #6 | 他人に渡しても事故らない（無断送信0・番号なしでも全部届く） |
| 4 | 友達3人に配る | 見るのは1つ:「Maps を消したか」。消さないなら理由を聞き、その1点だけ直す |
| 5 | 公開 | 3人中2人以上が1週間 Maps を消したまま過ごしたら出す。売り文句は「乗換案内アプリの代わり」ではなく **「もう調べなくていい」** |

physical / mental（親 spec Order 36）は段5 の後。

---

## 7. 更新規律

daily の TODO 状態が変わった瞬間にこのファイルを更新して commit する。
番号は**実行順**であり、消化しても振り直さない（済んだ行に done receipt を書く）。
`~/anicca-project` 側の同名ファイルは正本を指すポインタであり、**そこを編集しない**。
