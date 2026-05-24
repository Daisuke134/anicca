---
name: barber-booking
description: 任意のユーザーの周辺で「レビュー高 × 価格安」の美容室/理容室を自動探索 → 予約 → gcal → Slack 報告。3 ヶ月毎の install 型 cron。Dais など特定ユーザーに依存しない entity-agnostic 設計。
version: 0.1.0
---

# barber-booking — universal recipe

任意の住所 + Gmail account を渡すと **Google Maps で評価 4.3+★ + サンプル 10件+ + 安い** 美容室を見つけて予約 + gcal + Slack する。Dais 専用じゃない。誰でも install すれば動く。

## Install — auto-add cron

```bash
bash ~/.openclaw/skills/barber-booking/scripts/install.sh \
  --account "{{profile.contact.personalEmail}}" \
  --address "東京都{{profile.identity.homeAddress}}" \
  --name "<your-name>" \
  --gender "male" \
  --phone "08046270314" \
  --price-max "5000" \
  --frequency "quarterly"
# → config 保存 + 3 ヶ月毎 cron (Mar/Jun/Sep/Dec 15 日 9 JST) を自動登録
```

`install.sh` がやること:
1. `data/config.json` に上記引数を保存
2. `openclaw cron add --name barber-booking-quarterly-${HOSTNAME} --cron "0 9 15 3,6,9,12 *" --tz Asia/Tokyo --agent anicca --model openai-codex/gpt-5.4-mini --to "channel:${SLACK_CHANNEL_ID}" ...` を実行
3. `openclaw gateway restart`

## Recipe — exact way

### Step 1: discover

camofox で Google Maps 検索:
```
https://www.google.com/maps/search/美容室+near+<URL-encoded address>
```
snapshot から `<address-or-station>` 周辺の salon を抽出。各 `article` 要素から:
- name
- rating (`X.X つ星`)
- review_count (`クチコミ N 件`)
- distance
- vicinity (住所)

filter:
- rating >= 4.3
- review_count >= 10
- 男性 OK (default), 性別指定があれば反映
- (price 確認は次 step)

### Step 2: rank + price check

トップ 5 候補それぞれを開いて:
- 料金: HotPepper / 自社サイト / reservia ページから「カット」「メンズカット」価格 scrape
- オンライン予約可否: reservia / minimo / HotPepper Beauty / 自社サイト
- 営業時間 + 定休日

最終 score = `rating × log10(review_count + 1) / (price / 1000)`

### Step 3: pick top + book

1 位の店で予約可能枠を探す:
- 平日 18:30 以降 (work block 9-17 避ける) OR 土日 10:00-18:00
- 4 週後を起点に近い空きスロット

予約方式 ↓ 優先順:

#### a) reservia.jp (一番確実)

```
URL pattern: https://reservia.jp/reserve/datetime/<shop_id>?staff_id=...&menu_id=...&start_date=YYYY-MM-DD
```

camofox flow:
1. navigate datetime page
2. JS で target datetime の `<a href="...datetime=YYYY-MM-DD+HH%3A00%3A00">` を find + click
3. confirm page で input fill **(name 属性必須、DOM 順は misleading)**:
   - `input[name="Reservation[name]"]` ← name
   - `input[name="Reservation[{{profile.lateness.stakeholders.channel}}]"]` ← {{profile.lateness.stakeholders.channel}}
   - `input[name="Reservation[tel]"]` ← phone
   - `input[name="Reservation[is_new_member]"]` checkbox
4. `e7 / Confirm Booking` 押下
5. URL が `/reserve/complete/<shop_id>/<booking_id>` に遷移 → ✅

#### b) HotPepper Beauty

HotPepper も同様の camofox flow (詳細は将来追記)

#### c) {{profile.lateness.stakeholders.channel}} backup

オンライン予約系不可なら、店の問い合わせメール (firecrawl で取得) に予約希望日 4 つ書いて送信。
team428 形式と同じテンプレ。

### Step 4: gcal event

```bash
gog -a "$ACCOUNT" calendar create primary \
  --summary "💇 [CONFIRMED] $SHOP_NAME 散髪" \
  --from "...T11:00:00+09:00" --to "...T11:30:00+09:00" \
  --location "$SHOP_ADDRESS" \
  --description "★ 確定 ★
予約URL: $COMPLETE_URL
変更URL: $DETAIL_URL
料金: ¥$PRICE
Maps レビュー: $RATING★ / $REVIEWS 件
cancellable=$CANCELLABLE"
```

### Step 5: Slack 報告

`channel:{{profile.channels.reportChannel}}` に header + fields blocks で投稿。

## Required env (`~/.openclaw/.env`)

```
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID={{profile.channels.reportChannel}}
```

gog account token + camofox は既存。

## Files

| Path | Purpose |
|------|---------|
| `scripts/install.sh` | config 保存 + cron add + gateway restart |
| `scripts/discover.sh` | Maps 検索 → 候補 list → rank |
| `scripts/book.sh` | reservia or HotPepper or {{profile.lateness.stakeholders.channel}} backup で予約完走 |
| `scripts/run.sh` | discover → book → gcal → slack (cron が呼ぶ) |
| `data/config.json` | install 引数を保存 |
| `data/runs/<ts>/` | 各 run の raw / candidate / booking 証跡 |

## Frequency presets

| frequency | cron expr (JST) |
|----------|---|
| monthly | `0 9 15 * *` |
| **quarterly** (default) | `0 9 15 3,6,9,12 *` |
| biannual | `0 9 15 3,9 *` |
| yearly | `0 9 15 6 *` |

## Reference instance — Dais

- 1st run 2026-06-21(日) 11:00 @ Rein (新宿区四谷1-4) ¥2900 5.0★ ← Confirmed manual
- Cron: `0 9 15 3,6,9,12 *` JST
- Skill instance: `anicca-haircut-quarterly` (Dais 専用 wrapper)

## ガード

- 9-17 平日本業ブロック (HARD RULE #4) 必ず避ける
- gcal で他予定と被らないか install 引数の `--account` で確認
- canceLOLble=true な店のみ予約 (キャンセル不可は信用リスク)
- <training-school>/所属 一切書かない (もし表現職の場合は HARD RULE #4 RULE C)
