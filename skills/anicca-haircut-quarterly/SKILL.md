---
name: anicca-haircut-quarterly
description: 3 ヶ月毎 Dais の散髪を予約 (Rein 美容室、新宿区四谷1-4 綿半野原ビル1F、四ツ谷駅徒歩2分、reservia.jp 経由)。日曜 11:00 デフォルト、平日 9-17 本業避ける。
version: 0.1.0
---

# anicca-haircut-quarterly

## What

Rein (4.6+★ レベル、Dais 自宅から徒歩圏) で 3 ヶ月毎にカット予約。
カット ¥2900 30 分、シャンプー無し、平日 10-20 / 土日祝 10-19、月曜定休。

## Recipe — exact way (Reservia booking flow via camofox)

### Step 1: Cal 確認 + 候補スロット決定

- 日曜 11:00 デフォルト (歯科の土曜と分けて衝突回避)
- 4-6 週後の日曜
- gcal で AI meetup / 他予定と被ってないか

### Step 2: Reservia へ camofox で navigate

```bash
camofox new tab url=https://reservia.jp/shop/reserve/84ad9ba1c3 sessionKey=reservia
```

→ 自動的に `https://reservia.jp/reserve/staff/84ad9ba1c3?start_page=1&is_guest=1` に redirect

### Step 3: スタッフ → メニュー → 日時 → 確認

1. スタッフ Select: 【ご新規】男性のお客様 (初回) or 【2回目以降】男性のお客様
   - URL: `?staff_id=78811` (新規男性) / `78809` (リピ男性)
2. メニュー Select: カット (¥2900)
   - URL: `?menu_id=316739`
3. Date & Time: 月送り `start_date=YYYY-MM-DD` で navigation
4. 11:00 row の Sunday cell の ◎ をクリック
   - URL: `?datetime=YYYY-MM-DD+02:00:00` (11:00 JST = 02:00 UTC)
5. お客様情報フォーム fill (camofox eval で native value setter):
   - `input[name="Reservation[name]"]` ← <your-name>
   - `input[name="Reservation[{{profile.lateness.stakeholders.channel}}]"]` ← {{profile.contact.personalEmail}}
   - `input[name="Reservation[tel]"]` ← 08046270314
   - 初回 checkbox `input[name="Reservation[is_new_member]"]` チェック
6. Confirm Booking 押下

### 🔴 KNOWN GOTCHA (2026-05-11)

reservia form フィールドの順序が見た目と DOM 上で違う。
DOM 順は `Account[{{profile.lateness.stakeholders.channel}}]`, `Account[password]`, `Account[remember]`*2, **次に** `Reservation[name]`, `Reservation[{{profile.lateness.stakeholders.channel}}]`, `Reservation[tel]`。
全 `input[type=text]` を一気に取って [0]=name, [1]={{profile.lateness.stakeholders.channel}}, [2]=tel に入れると **ずれる**。

→ name 属性を必ず指定して fill:
```js
document.querySelector('[name="Reservation[name]"]').value="...";
document.querySelector('[name="Reservation[{{profile.lateness.stakeholders.channel}}]"]').value="...";
document.querySelector('[name="Reservation[tel]"]').value="...";
// native value setter + input/change event dispatch (HARD RULE memory)
```

### Step 4: 完了画面取得 → gcal [CONFIRMED] 追加

reservia は確定後に確認メール (`reservia.jp` ドメイン) を送ってくれる。
gcal に `cancellable=true (30 min 前まで)` で event 追加。

### Step 5: Slack 報告

## <training-school> 書かない (HARD RULE #4)

「予約メモ」欄等は使わない (※reservia は「※記入されても反映されません」と注意書きあり)。

## Cron

3 ヶ月毎 — 歯科 cron (Feb/May/Aug/Nov) と被らないよう +1.5 月オフセット
`cron 0 9 15 3,6,9,12 *` (Mar/Jun/Sep/Dec の 15 日)

## ガード

- 日曜 11:00 が標準、定休日 (月) avoid
- Cal で他予定 (SF trip 等) avoid
- 30 分前まではキャンセル可、それ以降は ¥1450 (50%) 料金
