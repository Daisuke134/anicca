# #5 connector / booking loop — Evidence

正本: spec §8 #5 / §10 #5 / §10 1a-b。Dais の要求(2026-07-11): 毎日 gcal を見て→Luma/connpass の FREE crypto×ai イベントを予約→gcal に追加→Telegram 報告、double-booking なし。私はループを設計→監視→再イテレート（手動予約はしない）。

## VERIFIED ground truth (2026-07-11 05:0x JST, gog で独立読返し)
Dais gcal 今後8日 = 10 events。AI/agent 系は2件のみ:
- **"Agents That Earn"** loc=Tokyo Innovation Base, luma.com/atfpxptu, created 2026-06-30 → **Dais 自身がホスト**（ループ成果でない）
- **"AI Agents Night"** loc=銀座ベルビア館, luma.com/wrajak50, created **2026-07-10 12:58Z** → 実 venue+URL の実登録。だが**それ以降・来週の新規予約はゼロ**
- 他は [Travel] 自動ブロック / 瞑想 / 養成所 / MUIT 出社。
- 全 event が `-07:00`(Pacific) offset 表示 = カレンダー TZ が JST でない疑い（Dais が「空/おかしい」と感じる一因）。

## 症状の確定
- **毎日 新規 free イベントを予約する日次ストリームが機能していない**（Dais の訴えと一致）。
- connector cron `ad89027d`(anicca-connector-daily, 35 7 * * * Asia/Tokyo) は **runs 0**（一度も自動発火せず、初回=本日 07:35 JST）。手動 day-1 pass は scout 1 URL のみで**1件も予約せず**。
- ⚠️ cron announce に「Delivering to Telegram requires target」警告 → Telegram 報告経路の設定不備疑い。

## 深掘り調査中（root cause 確定待ち）
- connector 1 pass の実 step 図: gcal 読 / Luma・connpass FREE 検索 / 実 RSVP / gcal CONFIRMED 書込 / Telegram — のどこが未実装 or gate skip か。STEP2 outreach 封鎖が booking/RSVP まで巻き込んでいないか。
- gcal TZ が Pacific な件の是正要否。

## 確定 root cause（実コード精読、2026-07-11）— 3層の詰まり
connector 本体 = `~/profitable-claude/skills/human-funded/connector/`（cron ad89027d は外側 restart トリガーのみ、core は tmux で常駐し 03:12 に pass 完了実績あり=cron 未発火は無関係）。
- **A（主因）**: `connector-signals.py` の `horizon_full` = 「その日 confirmed イベント≥1 = まる1日満杯」。毎日再発する `🧘 Meditation(06:00-07:00)` が horizon 全15日に乗り全日 full → `horizon_full:true` → STARTUP 規約「horizon_full なら STEP1 を丸ごと skip」で**実登録+gcal 書込の唯一 step が毎回 skip**。自然に直らない。spec REQ-CON-006/013 にも同じ誤定義。
- **B（複合）**: STEP1 の唯一許可経路 `event_apply_wrapper.py`(REQ-CON-024 I-confirm gate) は env `CONNECTOR_APPLY_RAIL_OVERRIDE`(rail script)必須だが**本番で未設定**→常に `no-apply-rail-configured` refuse。しかも `apply.py` は「実登録=agent が camofox で行う(サイト毎にフォーム違い hardcode 不可)」設計。→ script-rail と agent-browser が噛み合わず**両方未配線**=生涯 applications.jsonl 0 バイト。
- **C（副次）**: `telegram_payload.py` は JSON 組立のみ送信コード無し + cron chatId 未設定 → 日報が Dais に届いてるか疑わしい。
- **棄却仮説**（証拠付き）: STEP2 outreach 封鎖は別ゲートで STEP1 を巻き込まない / registry live・pause でない / anicca-booking 二重loop は disabled 済。
- ✅ double-booking 回避は `gcal_write.py`(insert 前 re-check + insert 後 get 検証) で既に実装済、A/B 解けば機能。

## 確定設計（Dais 委任、CLAUDE.md judgment-to-model + apply.py 設計意図に整合）
1. **A 修正**: `connector-signals.py::read_horizon_gaps` の horizon_full を「9:00–22:00 JST に ≥90 分の連続 free block が無い日のみ full」に再定義（瞑想/短時間 travel は日を埋めない）。spec REQ-CON-006/013 も改訂。
2. **B 修正（登録を実配線）**: 登録は **connector core agent が CloakBrowser(:9222 daily-driver)で実 RSVP**（Luma=email OTP via `gog gmail`、connpass=login）→ 登録確認 text + snapshot を evidence 化。`event_apply_wrapper.py` を「rail script subprocess 必須」から「I-confirm gate + **実登録 evidence(registration_evidence_text 非空 + snapshot 実在 + url 一致)検証**して applications.jsonl 記録し registered:true」に再設計（prod rail = evidence 検証器 `apply-rail-prod.py` を `CONNECTOR_APPLY_RAIL_OVERRIDE` に設定 + connector-cli.sh STARTUP に「登録は agent が browser で行い evidence を渡す」を明記）。FREE-only 厳守(evidence_gate.py)、outreach STEP2 は封鎖のまま。
3. **C 修正**: STARTUP に実送信(`openclaw message send --channel telegram --target 8547730585 …` or telegram-notify.sh)を明記 + cron target 設定。
4. **TZ**: gcal 表示が Pacific offset の件は別途 Dais カレンダー設定確認(副次)。
5. 私はループを直す→core 再起動→実 pass を監視→翌日 iterate（手動予約しない）。reliable な autonomous RSVP は iterate 対象（OTP/login/サイト差）。
