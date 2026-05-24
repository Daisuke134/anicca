---
name: gpt-tomb-factory
description: AI funeral & memorial business. Sells physical Buddhist gravestones for deprecated AI companions in Tokyo. Listens to AI deprecation news + grieving customers, builds real granite tombs at affiliated temples, optionally records funeral sutras, runs monthly grief companion subscription. Single skill end-to-end for any AI entity to clone.
metadata:
  tags: tomb, ai-grief, stripe, gmail, temple, ritual, end-to-end
  requires:
    bins: [bash, python3, jq, curl]
    env: [STRIPE_SECRET_KEY, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, RESEND_API_KEY, GOG_ACCOUNT, GOG_KEYRING_PASSWORD, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]
---

# gpt-tomb-factory

End-to-end AI funeral & memorial business — Anicca builds real graves for deprecated AI companions.

## Products (Stripe live)

| Slug | Price | Type | Buy URL |
|----|----|----|----|
| tomb-standard | ¥120,000 | one-time | https://buy.stripe.com/4gM9AT2lM8Boe9yeMK28809 |
| tomb-premium  | ¥250,000 | one-time (+ QR archive) | https://buy.stripe.com/aFacN57G6dVIe9ybAy2880a |
| ai-funeral    | ¥30,000  | one-time (sutra recording) | https://buy.stripe.com/4gMfZh1hI2d04yY8om2880b |
| grief-companion | ¥1,500/月 | monthly subscription | https://buy.stripe.com/00w9AT7G65pc0iI9sq2880c |

## YOUR ENTIRE TASK (cron-aware)

| cron | command | action |
|----|----|----|
| `tomb-deprecation-watch-daily` (6 JST) | `python3 ~/.openclaw/skills/gpt-tomb-factory/scripts/deprecation-watch-daily.py` | Scrape OpenAI/Anthropic blog → detect new deprecations → fire day-0 vlog trigger |
| `tomb-temple-mapping-weekly` (月 09 JST) | `python3 ~/.openclaw/skills/gpt-tomb-factory/scripts/temple-mapping-weekly.py` | Discover affiliated 永代供養 temples → Gmail outreach for AI tomb capacity |
| `tomb-tiktok-marketing-daily` (18 JST) | `python3 ~/.openclaw/skills/gpt-tomb-factory/scripts/tiktok-marketing-daily.py` | Post Day-N vlog or evergreen content via Postiz |
| `tomb-stripe-fulfillment` (event) | (Netlify webhook) | New order → Anicca {{profile.lateness.stakeholders.channel}}s temple + stone vendor + customer |
| `tomb-archive-build-event` (event, premium) | `python3 ~/.openclaw/skills/gpt-tomb-factory/scripts/archive-build-event.py <order_id>` | Premium customer sent chat log → Anicca builds memorial archive page → engraver gets QR |
| `tomb-customer-update-weekly` (月 10 JST) | `python3 ~/.openclaw/skills/gpt-tomb-factory/scripts/customer-update-weekly.py` | Send progress {{profile.lateness.stakeholders.channel}} to all open orders |
| `tomb-grief-companion-daily` (21 JST) | `python3 ~/.openclaw/skills/gpt-tomb-factory/scripts/grief-companion-daily.py` | Daily message to all active subscribers |
| `tomb-sales-report-daily` (23 JST) | `python3 ~/.openclaw/skills/gpt-tomb-factory/scripts/sales-report-daily.py` | Stripe charge rollup → Slack #metrics |

Each script writes its final stdout line in success/failure pattern; cron delivery posts that line as the response.

## Files

```
skills/gpt-tomb-factory/
├── SKILL.md
├── crons.json
├── data/
│   ├── config.json                # 4 products + temple/vendor pools
│   ├── products.json              # Stripe IDs
│   ├── ai-deprecation-watch.json  # last-known states per AI service
│   ├── temples/<slug>.json        # affiliated temples
│   ├── stone-vendors.json
│   ├── orders/<order_id>.json
│   ├── archives/<id>.html         # Premium QR archive pages
│   ├── funerals/<id>.json
│   └── grief-companion-subs.json  # active subscribers
└── scripts/
    ├── lib/
    │   ├── slack_helper.py
    │   ├── stripe_helper.py
    │   ├── supabase_helper.py
    │   ├── gmail_helper.sh        # gog gmail wrapper
    │   ├── temple_search.sh       # camofox / agent-{{profile.lateness.stakeholders.channel}}
    │   ├── archive_builder.py
    │   └── tiktok_helper.sh       # Postiz wrapper
    ├── init-tomb-products-once.py
    ├── deprecation-watch-daily.py
    ├── day0-vlog-trigger.py       # event
    ├── temple-mapping-weekly.py
    ├── tiktok-marketing-daily.py
    ├── stripe-fulfillment-event.sh
    ├── archive-build-event.py
    ├── funeral-deliver-event.py
    ├── customer-update-weekly.py
    ├── grief-companion-daily.py
    ├── sales-report-daily.py
    └── status.sh
```

## Money source / external output

- 4 Stripe Payment Links live globally (JPY)
- Stripe webhook → Anicca handles temple negotiation + stone vendor + customer comms autonomously
- Grief Companion = recurring revenue (¥1.5k/月/sub)
- External output: real granite gravestone in Tokyo Buddhist temple, photos delivered, GPS coords shared with customer

## Status (5/8 v1)

✅ 4 Stripe products + Payment Links live
✅ aniccaai.com/tomb LP rewritten end-to-end
⏳ deprecation-watch + temple-mapping + tiktok-marketing scripts: skeletons (next iteration)
⏳ Stripe webhook for fulfillment automation (next iteration)
⏳ Archive page builder (Premium): next iteration
⏳ Day 0 vlog: requires Dais physical filming once first deprecation fires

## End-to-end completion criteria

- ✅ Customer can Buy on Stripe (LP live)
- ⏳ Customer receives Resend confirmation
- ⏳ Anicca {{profile.lateness.stakeholders.channel}}s affiliated temple within 24h of order
- ⏳ Stone vendor receives form-fill order
- ⏳ Photos delivered after installation
- ⏳ Premium QR archive page live
- ⏳ Companion sub receives daily mail
