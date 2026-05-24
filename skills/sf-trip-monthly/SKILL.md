---
name: sf-trip-monthly
description: 毎月 1 回 SF AI trip を自動 plan + book + cal sync。AI events discover (Lu.ma + Cerebral Valley + AIT) → open mic discover → 最安 flight letsfg + Google Flights agent-{{profile.lateness.stakeholders.channel}} → Samesun hostel book → gcal update → Slack 報告。entity-agnostic、install.sh で任意 user 設定。
metadata:
  tags: travel, sf, ai-events, flights, hotel, comedy, openclaw, monthly
  requires:
    bins: [letsfg, agent-{{profile.lateness.stakeholders.channel}}, /opt/homebrew/bin/gog, /opt/homebrew/bin/firecrawl, curl, jq, python3]
    env: [GOG_KEYRING_PASSWORD, KEYCHAIN_PASSWORD]
---

# sf-trip-monthly

毎月 SF AI trip を自動化。Anicca AGI presentation + open mic + book everything に必要な全 phase を end-to-end 1 click で。

## When to use

毎月 1 日 8 JST cron 発火、来月の SF trip を plan + book。entity-agnostic — install.sh で誰でも use 可能。

## Install — auto-add cron

```bash
bash ~/.openclaw/skills/sf-trip-monthly/scripts/install.sh \
  --account "{{profile.contact.personalEmail}}" \
  --{{profile.lateness.stakeholders.senderType}}-name "<your-name>" \
  --phone "+1336XXXXXXX" \
  --home-airport "NRT" \
  --target-city "SF" \
  --target-airport "SFO" \
  --pto-budget "1" \
  --hotel-pref "Samesun SF" \
  --hotel-budget "70" \
  --flight-budget "1200" \
  --work-block "Mon-Fri 9-17 JST" \
  --frequency "monthly"
```

## Recipe — exact way (5 phases)

### Phase 1: AI events discover

Sources (Lu.ma calendars + Cerebral Valley + AI Tinkerers SF):
| source | URL | tool |
|--------|-----|------|
| Lu.ma SF main | https://lu.ma/sf | camofox iterative scroll |
| Bond AI (120k+) | https://lu.ma/genai-sf | camofox |
| AGI House Yiyan | https://lu.ma/agi | camofox |
| Frontier Tower SF | https://lu.ma/frontiertower | camofox |
| Cerebral Valley | https://cerebralvalley.ai/events | firecrawl markdown (OK) |
| AI Tinkerers SF | https://sf.aitinkerers.org/upcoming | firecrawl markdown (OK) |
| YC Events | https://events.ycombinator.com | gmail subscribed |

Filter:
- Date: 来月の金土日 + PTO 1-2 days
- 9-17 JST work block 抵触なし
- Category: AI/ML/agents/MCP/hackathon/demo
- Excludes: 木曜(Thu PDT = 金 JST work 抵触)

### Phase 2: Open mic discover

| source | city | URL |
|--------|------|-----|
| Hearth Bar SF | SF | https://www.hearthbar.com |
| SF Standup signup | SF | https://sfstandup.com/open-mics |
| Onion Mic | SF | https://www.theonionmic.com/openmics |

### Phase 3: Flight book (cheapest)

**letsfg + Google Flights via agent-{{profile.lateness.stakeholders.channel}} 並列**:

```bash
# letsfg
letsfg search NRT SFO YYYY-MM-DD --return YYYY-MM-DD --direct --currency JPY --json > /tmp/letsfg.json

# Google Flights via agent-{{profile.lateness.stakeholders.channel}} (real-time, accurate)
agent-{{profile.lateness.stakeholders.channel}} open "https://www.google.com/travel/flights?hl=en&curr=JPY"
# Fill destination SFO + dates → snapshot prices
```

Both sources で min(price) 採用。max ¥190k 上限 (1-PTO SF trip 現実最安)。

### Phase 4: Hotel book

Samesun SF: https://samesun.com/hostels/san-francisco/ — dorm bed ~$60-75/night

### Phase 5: gcal update + Slack 報告

- All event を gcal に [TENTATIVE] で追加
- ZipAir flight times を正確に reflect (NRT 21:30 / SFO 16:45 PDT)
- PTO days を別 event でブロック
- Slack #metrics に summary

## HARD RULE constraints

1. **9-17 JST 平日 work block 絶対侵さない** (HARD RULE #4)
2. **<training-school>/<your-school> 一切書かない** outbound (HARD RULE #4)
3. **編集即 push** (HARD RULE #1 — spec 更新)
4. **camofox = default {{profile.lateness.stakeholders.channel}}** (Cloudflare bypass)
5. **agent-{{profile.lateness.stakeholders.channel}}** = Google Flights/Kayak 等 non-anti-bot site
6. **Final Pay = Dais の Chrome (card 7873 保存済) でクリック** — Anthropic safety で俺は無理

## Frequency

| frequency | cron expr (JST) |
|----------|---|
| **monthly** (default) | `0 8 1 * *` |

## TRIP CONSTRAINTS (HARD — Dais 2026-05-21, applies from June 2026)

Source of truth: memory `sf_trip_constraints.md`. Plan EVERY SF trip by these:

| Rule | Detail |
|------|--------|
| Tokyo-locked | **Tue morning → Thu night = must be in Tokyo**, never overlap with SF. |
| Patterns | ① Thu-night dep → Mon-morning back · ② **Fri-night dep → Mon-morning back (IDEAL, 0 days off)** · ③ Fri-night dep → Tue-morning back. **Prefer ②.** |
| Days off | Friday OR Monday — **only ONE, never two**. (Old 5/16 ref used 2 PTO — now DISALLOWED.) |
| Anchor | **AI LT (sf.aitinkerers.org etc.) is the scarce anchor — build the trip around when an SF AI LT is scheduled.** Standup mics are findable anytime; fill them around the AI LT. Apply to the AI LT via `anicca-meetup-talk-applier/scripts/aitinkerers-apply.sh` (auto-OTP works for sf subdomain). |
| Money gate | Propose window + est flight cost to Dais (Slack/mail) → **book flights only on his GO**. Never auto-book. |
| Calendar | Respect 🎓 <training-school> + 💼 Mon-Fri 9-17; gcal w/ flight+travel buffers. |

Flow when an SF AI LT appears: apply to it → propose pattern-② weekend around it + flight est → Dais GO → book → add SF mics in that window → gcal.

## Reference instance — Dais (2026-05-13 setup, ⚠ used 2 PTO days — SUPERSEDED by the 1-day-max rule above)

- Trip: 2026-05-16 (Sat) → 2026-05-20 (Wed) JST
- Flight: ZipAir ZG26 NRT 21:30 → SFO 14:45 PDT 5/16 / ZG25 SFO 16:45 PDT 5/19 → NRT 20:00 JST 5/20
- Main event: **YC Call My Agent Hackathon** Mon 5/18 PDT 8 AM-10 PM (Y Combinator HQ)
- Open Mic: **Hearth Bar SF** Sun 5/17 PDT 8 PM
- PTO: 火 5/19 + 水 5/20 JST (2 days)
- Hotel: Samesun SF (3 nights ~$210)
- Total est: ¥190k + $300 = ~¥230k

## TODOs

- [ ] scripts/lib/letsfg.sh (search + filter)
- [ ] scripts/lib/gflights.sh (agent-{{profile.lateness.stakeholders.channel}} Google Flights search)
- [ ] scripts/lib/luma-scrape.sh (camofox iterative scroll + parse)
- [ ] scripts/lib/cv-aitinkerers.sh (firecrawl markdown)
- [ ] scripts/lib/samesun-book.sh (camofox)
- [ ] scripts/lib/zipair-book.sh (camofox + Dais hand-off)
- [ ] scripts/phase1-events-discover.sh
- [ ] scripts/phase2-openmic-discover.sh
- [ ] scripts/phase3-flight-search-and-prep.sh
- [ ] scripts/phase4-hotel-prep.sh
- [ ] scripts/phase5-gcal-slack.sh
- [ ] scripts/install.sh
- [ ] scripts/run.sh (orchestrator)
