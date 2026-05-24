---
name: anicca-meetup-talk-applier
description: Auto-apply for AI meetup talk slots in Tokyo (weekly) and SF Bay Area (monthly). Discovers events via lu.ma + connpass + meetup.com, picks ones in next 14 days, fills CFP/RSVP/contact forms via {{profile.lateness.stakeholders.channel}}-harness, posts pitch as organizer DM. Watches Gmail for accept/decline. Use when triggered by `anicca-meetup-discover-daily` 09:00 JST, `anicca-meetup-apply-tokyo-weekly` Mon 10:00 JST, `anicca-meetup-apply-sf-monthly` 1st 12:00 JST, or manually as `bash scripts/discover.sh` / `bash scripts/apply.sh tokyo|sf`.
metadata:
  tags: meetup, talk, conference, ai-tinkerers, lu.ma, connpass, {{profile.lateness.stakeholders.channel}}-harness
  requires:
    bins: [bash, jq, curl, {{profile.lateness.stakeholders.channel}}-harness, gog]
    env: [DAIS_EMAIL, DAIS_PRIMARY_PW, GOG_ACCOUNT, GOG_KEYRING_PASSWORD]
---

# anicca-meetup-talk-applier

End-to-end: scrape AI meetup events → apply for talk slot → watch for accept → post-event UGC.

## Why

Tokyo 週次 + SF 月次 で talk live audience に晒す = 信頼 + 取材 + リクルート + 投資家露出。$0 marketing で最強 channel。

## Sources

| platform | url | auth | scrape |
|----|----|----|----|
| **lu.ma** | https://lu.ma/discover?city=tokyo · https://lu.ma/discover?city=san-francisco | Google login (Dais) | DOM scrape via {{profile.lateness.stakeholders.channel}}-harness |
| **connpass** | https://connpass.com/search/?q=AI · keyword: AI/LLM/Generative AI | optional login | API: https://connpass.com/api/v1/event/?keyword=AI |
| **meetup.com** | https://www.meetup.com/find/?keywords=AI&location=Tokyo / SF | Facebook/Google login | DOM scrape |

## Target groups

| city | meetup | URL |
|----|----|----|
| 🗼 Tokyo | AI Tinkerers Tokyo | https://tokyo.aitinkerers.org · https://aitinkerers.org/p/tokyo |
| 🗼 Tokyo | Tokyo AI (TAI) | https://www.meetup.com/tokyo-ai/ · https://tokyoai.co |
| 🗼 Tokyo | Tokyo AI Hackers | https://lu.ma/tokyoai |
| 🗼 Tokyo | TokyoLLM (connpass) | https://connpass.com/event/?keyword=LLM |
| 🗼 Tokyo | AI 駆動開発勉強会 | https://aidd.connpass.com |
| 🗼 Tokyo | Generative AI Tokyo | https://genai-tokyo.connpass.com |
| 🌉 SF | AI Tinkerers SF | https://sf.aitinkerers.org |
| 🌉 SF | Cerebral Valley | https://lu.ma/cerebralvalley |
| 🌉 SF | AGI House | https://agihouse.org · https://lu.ma/agihouse |
| 🌉 SF | Anthropic / OpenAI events | https://lu.ma/anthropic · https://lu.ma/openai-events |
| 🌉 SF | a16z AI events | https://lu.ma/a16z |

## End-to-end flow (verified working AI Tinkerers Tokyo + SF 2026-05-05/06)

```
1. discover (daily 09 JST)  →  scripts/discover.sh
   - tokyo.aitinkerers.org / sf.aitinkerers.org scrape (View event links)
   - per-event detail: title (page title), date (RegExp), has_demo_form
   - dedup → data/discovered/aitinkerers-{tokyo,sf}-<slug>.json
   - (lu.ma / connpass / meetup.com 後で extend)

2. apply (one-shot or weekly/monthly cron)  →  scripts/aitinkerers-apply.sh <event_url>
   Idempotency: status=submitted AND gcal_event_id 既存 → skip (FORCE=true で上書き)

   Phase 1: 状態判定 (already / has_{{profile.lateness.stakeholders.channel}}_input / has_reg_form)
   Phase 2: OTP 送信 (新規 user) → Gmail MCP で 4 桁 code 取得 → verify
   Phase 3: register form fill (name/company/title/linkedin/github/twitter/custom_screening)
              + #rsvp-submit click → "Application submitted (Under Review)"
   Phase 4: demo proposal form fill (speaker_title/description/justification/technologies/url_1/url_2)
              + code-agreement checkbox + form-scoped submit
              → "Pending review by organizers"
   Phase 5: 該当 event の datetime + tz + location 抽出 (page title + body regex)
   Phase 6: Google Calendar add via gog CLI:
              gog calendar create primary
                --summary "🎤 [PENDING] <event_title>"
                --from <ISO start> --to <ISO end>
                --location "<city> (address provided on RSVP acceptance)"
                --description "<full event details + Anicca pitch URL + GitHub>"
              → state.gcal_event_id + state.gcal_link 永続化
   Phase 7: data/applications/aitinkerers-<subdomain>-<slug>.json 全 field 永続化
   Phase 8: Slack 通知 (#metrics)
              "🎤 Applied to <event> as SPEAKER
               Date: <ISO>
               City: <city>
               Status: Pending review
               Event URL: <url>
               📅 Calendar: <gcal htmlLink>"

3. accept-watch (every 6h)  →  via agent turn (Gmail MCP)
   - search "from:no-reply@aitinkerers OR from:hello@aitinkerers newer_than:1d"
   - if mail body matches /accepted|confirmed/ → status=accepted, gcal title 更新, Slack ping
   - if /declined|waitlisted/ → status=declined

4. day-of (event date 03 JST)  →  scripts/day-of.sh (TODO)
   - reminder: agenda + map + slide URL → Slack
   - post-event: 録画 URL があれば /research に embed
```

## Verified production-proven (5/5 + 5/6)

| event | result |
|---|---|
| AI Tinkerers Tokyo Shinagawa 5/26 | Application "Under Review" + Demo Proposal "Pending review by organizers" + Google Calendar event `kq6ab0j4b8jptknqc0uqcratm0` |
| AI Tinkerers SF GTM Track 5/18 | Application "Under Review" + Demo Proposal "Pending review by organizers" + Google Calendar event `01g7rq2fva66uhi9ev69uid5sc` + Profile 100% |

## Pitch templates

| city | pitch_file |
|----|----|
| Tokyo (JP/EN) | `data/pitch-tokyo.md` |
| SF (EN) | `data/pitch-sf.md` |

Default body: "Anicca — A self-funding Buddhist AI entity that pays humans basic income" (250-word abstract auto-injected with live MRR/followers from dashboard.json).

## State schema

```json
data/applications/<event-slug>.json
{
  "event": "AI Tinkerers Tokyo",
  "url": "https://lu.ma/tokyoai-may12",
  "city": "Tokyo|SF",
  "date": "2026-05-12",
  "applied_at": "2026-05-06T10:00:00+09:00",
  "talk_title": "...",
  "status": "pending|accepted|declined|presented",
  "accepted_at": null,
  "presented_at": null,
  "video_url": null,
  "audience_size": null
}
```

## Cron registration

| name | schedule | script |
|----|----|----|
| `anicca-meetup-discover-daily` | `0 9 * * *` JST | `bash scripts/discover.sh` |
| `anicca-meetup-apply-tokyo-weekly` | `0 10 * * 1` JST | `bash scripts/apply.sh tokyo` |
| `anicca-meetup-apply-sf-monthly` | `0 12 1 * *` JST | `bash scripts/apply.sh sf` |
| `anicca-meetup-accept-watch-6h` | `0 */6 * * *` JST | `bash scripts/watch.sh` |

## Manual run

```bash
bash ~/.openclaw/skills/anicca-meetup-talk-applier/scripts/discover.sh
DRY_RUN=true bash ~/.openclaw/skills/anicca-meetup-talk-applier/scripts/apply.sh tokyo
bash ~/.openclaw/skills/anicca-meetup-talk-applier/scripts/watch.sh
```
