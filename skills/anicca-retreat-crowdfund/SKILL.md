---
name: anicca-retreat-crowdfund
description: Anicca Retreats crowdfunding tracker + content factory. Daily reports fundraising progress (Stripe direct on aniccaai.com/retreat/build + Camp Fire JP project 951165) to Slack #metrics, posts weekly progress slideshow to TikTok @anicca.jpx draft, and follows up donors via Resend. Recipe-style — uses gog gmail / camofox / Stripe API exactly as run manually 2026-05-11.
metadata:
  tags: crowdfund, retreat, anicca, stripe, camofox, gog, daily-report, weekly-slideshow
  requires:
    bins: [bash, curl, jq, /opt/homebrew/bin/gog]
    env: [STRIPE_SECRET_KEY, GOG_KEYRING_PASSWORD, SLACK_BOT_TOKEN, CAMPFIRE_EMAIL, CAMPFIRE_PASSWORD]
---

# anicca-retreat-crowdfund

Daily Stripe donation aggregation + Camp Fire status check + Slack report. Weekly TikTok progress slideshow.

## How this skill was built (recipe — exact tools used 2026-05-11)

### Camp Fire JP account creation (camofox-{{profile.lateness.stakeholders.channel}}, NOT playwright)

1. **camofox tab open** — `curl -X POST http://localhost:9377/tabs -H 'Content-Type: application/json' -d '{"url":"https://camp-fire.jp/signup","userId":"anicca-retreat","sessionKey":"crowdfund"}'`
2. **type {{profile.lateness.stakeholders.channel}}** — `curl -X POST http://localhost:9377/tabs/$TAB_ID/type -d '{"ref":"e35","text":"your-email-user+anicca-retreat@gmail.com",...}'`
3. **click 確認メールを送信** — `curl -X POST http://localhost:9377/tabs/$TAB_ID/click -d '{"ref":"e37",...}'`
4. **read confirmation {{profile.lateness.stakeholders.channel}} via gog** (NOT IMAP, NOT smtplib):
   ```bash
   gog gmail search "from:campfire newer_than:1h" -a {{profile.contact.personalEmail}} --max 5 -j --results-only
   gog gmail thread get $MSG_ID -a {{profile.contact.personalEmail}} -j --results-only > /tmp/{{profile.lateness.stakeholders.channel}}.json
   ```
5. **extract URL from base64 body** via Python json + base64.urlsafe_b64decode
6. **navigate camofox to confirmation URL** (full URL, not truncated)
7. **fill registration form** — username/password/confirm via type ref + click 登録
8. **save credentials** to `~/.openclaw/.env`

⚠️ Google OAuth path: 2FA blocks, fallback to {{profile.lateness.stakeholders.channel}} signup.

### Stripe Checkout direct (no Stripe MCP, raw fetch curl)

`apps/landing/netlify/functions/retreat-build-checkout.js` uses `fetch()` to `https://api.stripe.com/v1/checkout/sessions` with form-urlencoded params. metadata.product=`retreat-build-fund`. submit_type=`donate`.

## Daily run

```bash
bash ~/.openclaw/skills/anicca-retreat-crowdfund/scripts/00-daily-report.sh
```

What it does:
1. Stripe API: list checkout sessions with `metadata.product=retreat-build-fund` since last run → aggregate amount + donor count
2. Camp Fire status: camofox visit `/mypage/projects/951165` → snapshot 進捗
3. Update `data/progress.json`
4. Slack #metrics report (only if delta > 0 or weekly summary)
5. Update `dashboard.json` `mrr.by_product.retreat-build-fund` (if Anicca dashboard skill is integrated)

## Cron

`anicca-retreat-crowdfund-daily` `0 19 * * *` JST (registered via openclaw cron add)

## Files

```
~/.openclaw/skills/anicca-retreat-crowdfund/
├── SKILL.md (this file)
├── data/
│   ├── progress.json (running totals: stripe_donations_jpy, donor_count, last_session_id)
│   └── crowdfund-state.json (Camp Fire draft id, credentials, status)
└── scripts/
    ├── 00-daily-report.sh (entry — Stripe poll + Camp Fire check + Slack)
    ├── lib/
    │   ├── stripe-poll.sh (Stripe API list sessions filtered by metadata.product)
    │   ├── campfire-status.sh (camofox visit /mypage/projects/951165)
    │   ├── slack.sh (chat.postMessage)
    │   └── state.sh (read/write progress.json)
    └── status.sh (one-off status print)
```
