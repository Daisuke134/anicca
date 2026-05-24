---
name: comedy-booking-en
description: SF / NYC / London 等の英語 open mic に毎月 1 本エントリー。entity-agnostic、install.sh で都市と budget 指定。
parent: anicca-comedy-factory
---

# comedy-booking-en (sub-skill of anicca-comedy-factory)

毎月 1 日 8 JST cron で発火、翌月の英語 open mic 1 枠を取る。default は SF (Dais が毎月行く)。NYC / London / LA も対応。

## Install — auto-add cron

```bash
bash ~/.openclaw/skills/anicca-comedy-factory/scripts/booking-en/install.sh \
  --account "{{profile.contact.personalEmail}}" \
  --{{profile.lateness.stakeholders.senderType}}-name "Anicca" \
  --{{profile.lateness.stakeholders.senderType}}-name "<your-name>" \
  --phone "+1336XXXXXXX" \
  --city "SF" \
  --neta-type "standup" \
  --neta-length "5min" \
  --budget-per-show "20" \
  --frequency "monthly"
```

## Recipe — exact way

### Step 1: 都市別 source

| city | source | note |
|------|--------|-----|
| SF | https://sfstandup.com/open-mics, http://www.sfcomedy.com/openmics.html, https://www.theonionmic.com/openmics | Hearth Bar / Onion Mic / SF Standup |
| NYC | https://nycstandup.com/open-mics | Standing Room Only / EastVille |
| London | https://comedymapsapp.com/london/, https://www.comedyclub.london/open-mics/ | Top Secret / Angel |
| Tokyo (EN) | https://www.tokyocomedybar.com (English shows), Hearth Tokyo | |
| LA | https://www.laughfactory.com/open-mics, https://www.improvla.com | |

### Step 2: 翌月の空き枠 filter

- 翌月 1-31 日 + 滞在日程 (gcal の `🛬 SF Trip` etc から自動推定)
- gcal で他予定と被らない
- 入り時間: 都市 TZ で適切に

### Step 3: 各都市の予約方法

| city | method |
|------|--------|
| SF | mostly walk-up but signup via Eventbrite / sfstandup.com signup form |
| NYC | NYC Standup form + Hot 97 mic signup |
| London | Top Secret signup form |
| Tokyo (EN) | Tokyo Comedy Bar Wix booking |

### Step 4: gcal [TENTATIVE] + Slack

英語 mic は walk-up が多いので「行く予定」だけ gcal に入れて当日 signup する case も。
[WALK-UP] flag を summary に入れる。

## Frequency

| frequency | cron expr (JST) |
|----------|---|
| **monthly** (default) | `0 8 1 * *` |
| biweekly | `0 8 1,15 * *` |
| weekly | `0 8 * * 1` |

## Reference instance — Dais

- city: SF (毎月 1 回 SF 渡航)
- 既に 5/17 Hearth Bar SF gcal にあり
- 次回 cron 発火: 6/1 8:00 JST → 6 月分エントリー
