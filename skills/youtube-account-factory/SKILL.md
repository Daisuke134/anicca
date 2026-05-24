---
name: youtube-account-factory
description: "Phase 4 YouTube account creation. Gmail manual SIM signup → 5 Gmail accounts × 6 Brand Account each = 30 channels. Per-persona on-demand."
metadata:
  tags: phase4, account, youtube, gmail, semi-automated
  status: SCAFFOLDED — needs Dais hardware + manual SIM step
  hardware_required:
    - Same iPhone + Apple ID + US SIM as TT/IG persona
    - Real US phone number for Gmail signup (Mint Mobile is fine — but YT/Gmail is STRICTER on number reuse than TT/IG, so try fresh per persona if possible)
  external_services:
    - Google Cloud Platform (GCP) project per Brand Account family
    - Google OAuth verification (1-2 day delay if YT API access wanted)
    - Postiz YouTube integration
  requires:
    bins: [playwright, python3, gcloud (optional), curl, jq]
    env: [SLACK_WEBHOOK_URL, GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET]
---

# youtube-account-factory

YouTube channel scaling via Gmail Brand Accounts. **Lighter warmup than TT/IG**
(YouTube algorithm is interest-graph driven, less paranoid).

## Architecture: 5 Gmail × 6 Brand Account = 30 channels

Each Gmail can host up to 6 Brand Accounts → effectively 30 distinct YouTube
channels per Apple ID. Per Shalev L1 + Anicca scaling target.

## Run

\`\`\`
bash ~/.openclaw/skills/youtube-account-factory/scripts/run.sh <persona-slug>
\`\`\`

## Pipeline

| # | Action | Auto / Manual | Notes |
|---|---|---|---|
| 1 | Pre-flight: TT/IG account exists | Auto | reads accounts/<persona>/apple_id.json |
| 2 | Gmail signup with REAL SIM (NOT VOIP, NOT Google Voice — these get banned) | **Manual + Auto hybrid** | scripts/gmail-signup.sh — Dais enters OTP from real phone |
| 3 | Brand Account create (under that Gmail) — first persona only | Auto (Playwright) | scripts/brand-account-create.sh |
| 4 | YouTube channel customize (channel name = "@<persona-slug>", banner, description) | Auto | scripts/channel-customize.sh |
| 5 | Postiz YouTube integration (per Brand Account) | **Manual** | Dais authorizes via Postiz UI |
| 6 | (Optional) GCP project + YouTube Data API access | **Manual + delayed verify** | scripts/gcp-project.sh — 1-2 day Google verify wait |

## Output

\`\`\`
~/anicca-monk-factory/accounts/<persona-slug>/youtube.json
  {
    "gmail_account": "anicca.<n>@gmail.com",  // shared across personas (1 Gmail / 6 personas)
    "brand_account_id": "...",
    "channel_id": "UC...",
    "channel_handle": "@<persona-slug>",
    "type": "brand_account",
    "created_at": "...",
    "status": "ready" | "warming_up"
  }
\`\`\`

## Why 5 Gmail × 6 Brand?

- 1 Gmail = legitimate {{profile.lateness.stakeholders.channel}} tied to real SIM = trust signal
- 6 Brand Accounts per Gmail = Google's documented soft limit before flagging
- 5 Gmail accounts = enough capacity for 30 personas without saturating any single Gmail

Reference: Google official Brand Account docs + Shalev's verified 7-character / 30-account farm pattern.

## Status: SCAFFOLDED

Skeleton in place. Manual SIM step (#2) is unavoidable — Google's bot detection
on Gmail signup is the strictest of all 3 platforms. Even 100% Playwright
automation gets caught at the OTP step. Plan: Dais creates 1 Gmail per week,
spawns 6 personas under it as needed.

## Reference

- Google Brand Account docs: https://support.google.com/accounts/answer/7001996
- Postiz YT integration: requires OAuth, 5-min Dais flow per Brand Account
- YouTube Data API: optional for stats; Postiz handles posting without it
