---
name: instagram-account-factory
description: "Phase 4 IG account creation. Personal signup → 7d warmup → Business switch → FB Page link. Per-persona on-demand. NEEDS Dais hardware."
metadata:
  tags: phase4, account, instagram, semi-automated
  status: SCAFFOLDED — needs Dais hardware before run
  hardware_required:
    - Same iPhone as TikTok account (one device per persona)
    - Same Apple ID as TikTok account
    - Same US SIM as TikTok account
    - Same Surfshark Dedicated IP
  external_services:
    - SMSPool (US phone for OTP)
    - Slack OTP relay channel (manual fallback)
    - instagrapi (warmup library, subzeroid/instagrapi maintained)
  requires:
    bins: [playwright, python3, pip3 (instagrapi), curl, jq]
    env: [SMSPOOL_API_KEY, SLACK_WEBHOOK_URL, INSTAGRAM_APP_ID]
---

# instagram-account-factory

Semi-automated Instagram account creation, persona-by-persona. Same iPhone +
Apple ID + Mint SIM + Dedicated IP as the TikTok persona — one physical
device hosts BOTH TT and IG identities.

## Run

\`\`\`
bash ~/.openclaw/skills/instagram-account-factory/scripts/run.sh <persona-slug> <bio-url>
\`\`\`

## Pipeline (5 {{profile.lateness.stakeholders.senderType}}s)

| # | Action | Auto / Manual | Notes |
|---|---|---|---|
| 1 | Pre-flight: verify TT-account-factory ran first (shares device + Apple ID) | Auto | reads accounts/<persona>/apple_id.json |
| 2 | IG Personal signup via phone (SMS code, NOT {{profile.lateness.stakeholders.channel}}) | Auto (Playwright) | scripts/signup-personal.sh |
| 3 | 7-day warmup (handed off to warmup-instagram skill) | Auto (delayed) | warmup-instagram via instagrapi |
| 4 | Personal → Business switch | Auto | scripts/business-switch.sh |
| 5 | FB Page link (required for Postiz IG → IG Reels API) | **Manual** | Dais creates FB Page, pastes IDs |

## Output

\`\`\`
~/anicca-monk-factory/accounts/<persona-slug>/instagram.json
  {
    "handle": "anicca.stoic",
    "password": "...",
    "phone": "+1...",
    "type": "business",
    "fb_page_id": "...",
    "ig_business_account_id": "...",
    "created_at": "...",
    "status": "ready" | "warming_up" | "ghost_mode"
  }
\`\`\`

## Why "Personal first, Business after warmup"

Per Shalev L1 + Larry Portet docs:
- IG Business signups from fresh accounts = high ban rate
- Path: Personal (phone signup) → 7-day warmup → switch to Business → link FB Page → ready for posting

## Personal vs Business in Postiz

Postiz REQUIRES IG Business (not Personal) to post via Graph API. Personal accounts
can only post via Reels Display API which doesn't allow scheduling.

So the funnel is: warmup as Personal → confirmed not banned → upgrade to Business
→ FB Page link → Postiz integration ID → spawned factory cron starts posting.

## Status: SCAFFOLDED

Same as TikTok: stubs in place, hardware blocks the live run. M6/M7 from
MASTER_PLAN.md must complete before this skill validates.

## Reference docs

- instagrapi: https://github.com/subzeroid/instagrapi (actively maintained 2025+)
- Larry Portet IG Business switch flow: documented in his post-to-tiktok.js source patterns
