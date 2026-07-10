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

## 次の設計方針（調査結果で確定させる）
1. booking/RSVP を outreach 封鎖から**分離**（登録は評判リスク低、封鎖対象は intro 送信のみ）。
2. 毎日: gcal horizon 空き算出 → FREE crypto×ai イベント検索 → 実登録 → gcal CONFIRMED(既存 event 突合で double-book 回避) → Telegram delivered:true。
3. 私はループを直す→07:35 自動 run を監視→翌日 iterate（手動予約しない）。
