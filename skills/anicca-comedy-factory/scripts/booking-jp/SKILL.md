---
name: comedy-booking-jp
description: Tokyo の open mic / 賞レースに毎週 1 本エントリー ({{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}} ピン 漫談)。 entity-agnostic — install.sh で任意ユーザー設定。HARD RULE #4: 9-17 work block, <training-school>書かない。
parent: anicca-comedy-factory
---

# comedy-booking-jp (sub-skill of anicca-comedy-factory)

毎週月曜 8 JST cron で発火し、来週の Tokyo open mic 1 枠を取る。デフォルトは U&C パワーオブフリー、満員なら下北 GRIP / 小猿ライブ / K-PRO Gereron に fallback。

## Install — auto-add cron

```bash
bash ~/.openclaw/skills/anicca-comedy-factory/scripts/booking-jp/install.sh \
  --account "{{profile.contact.personalEmail}}" \
  --{{profile.lateness.stakeholders.senderType}}-name "{{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}" \
  --{{profile.lateness.stakeholders.senderType}}-name "<your-name>" \
  --phone "08046270314" \
  --neta-type "漫談" \
  --neta-length "3min" \
  --persona-type "pin" \
  --budget-per-show "2500" \
  --frequency "weekly"
```

## Recipe — exact way

### Step 1: スケジュール discover (4 source)

| source | URL | 確認方法 |
|--------|-----|---------|
| U&C パワーオブフリー | http://uandcenterprise.jp/schedule.php?genre=newcomer | firecrawl scrape |
| 下北 GRIP / DASH | https://shimokita-grip.stores.jp/reserve/shimokita-grip/booking_pages | camofox |
| たか7 小猿/肉食 | https://ameblo.jp/odakarat/ | firecrawl |
| K-PRO Gereron | https://kpro-web.com/gereron/ | firecrawl |

note 一覧 (broader): https://note.com/toffee101/n/n3f48144ac982

### Step 2: 来週の空き枠 filter

- next 7 days (cron が月曜なので火-日)
- gcal で他予定と被らない (9-17 work block, AI meetup, 他 live)
- 入り時間: 平日は 18:00 以降、土日は 10:00-18:00 OK
- 料金 <= budget-per-show

### Step 3: 一番条件良いとこに entry

優先順:
1. U&C パワーオブフリー (mail 1 通で完結) — `live_entry@yahoo.co.jp`
2. 下北 GRIP (stores.jp camofox) — DASH の方は初回無料
3. たか7 / K-PRO は X DM or {{profile.lateness.stakeholders.channel}} (詳細は noteリンク先)

U&C 送信テンプレ:
```
希望月日・曜日◆ YYYY/MM/DD(曜)
ライブ名◆ パワーオブフリー(Ｓ) vol.千XX
ユニット名◆ {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}
人数◆ ピン
ネタ形態◆ 漫談
代表者名◆ <your-name>
電話番号◆ 080-4627-0314
```

### Step 4: gcal [TENTATIVE] 追加

返信受信後 mail-auto-reply 経由で [CONFIRMED] 化。

### Step 5: Slack 報告

## HARD RULE #4 strict

- <training-school> / <your-school> / 1年目 / 芸歴 **絶対書かない**
- {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}} 名義のみ。本名は「代表者名」項目のみ
- 9-17 平日本業 NG
- キャンセル可否を必ず gcal description に記録

## Frequency

| frequency | cron expr (JST) |
|----------|---|
| **weekly** (default) | `0 8 * * 1` (月曜 8時) |
| biweekly | `0 8 * * 1/2` |
| monthly | `0 8 1 * *` |

## Reference instance — Dais

- 既存 cron: `anicca-comedy-weekly-book`
- 2026-05-14 vol.千20 なかの芸能小劇場 にエントリー済 (確認待ち)
