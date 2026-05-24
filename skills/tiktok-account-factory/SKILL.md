---
name: tiktok-account-factory
description: "Phase 4 account creation for TikTok. Playwright + SadCaptcha + SMSPool + Slack OTP relay. Per-persona triplet output. NEEDS Dais hardware (iPhone 8 + Mint SIM + Apple gift card $30 + Surfshark Dedicated IP)."
metadata:
  tags: phase4, account, tiktok, semi-automated
  status: SCAFFOLDED — needs Dais hardware before run
  spawn_pattern: per-persona-on-demand
  hardware_required:
    - iPhone 8/X/11 (factory reset, region=US, timezone=NY/LA, location_services=OFF)
    - Mint Mobile or Lycamobile US SIM (presence only, no data plan needed)
    - Apple ID with US billing (Apple gift card $30 from Amazon US)
    - Surfshark or NordVPN Dedicated IP (NOT shared NY/LA)
  external_services:
    - SMSPool (US phone number for OTP, ~$0.50 per number)
    - SadCaptcha (TikTok captcha solver)
    - Slack OTP relay channel (manual fallback when SMSPool fails)
  requires:
    bins: [playwright, python3, curl, jq]
    env: [SMSPOOL_API_KEY, SADCAPTCHA_API_KEY, SLACK_WEBHOOK_URL, TIKTOK_PROXY_URL]
---

# tiktok-account-factory

Semi-automated TikTok account creation, one persona at a time. Built on:
- l-portet/tiktok-warmup-bot (649⭐ on GitHub) — automation patterns
- Shalev L1 playbook (locked in MASTER_PLAN.md → SHALEV PLAYBOOK section)

## Run

\`\`\`
bash ~/.openclaw/skills/tiktok-account-factory/scripts/run.sh <persona-slug> <bio-url>
\`\`\`

Example:
\`\`\`
bash ~/.openclaw/skills/tiktok-account-factory/scripts/run.sh anicca-stoic aniccaai.com/monk
\`\`\`

## 8-step pipeline (per persona)

| # | Action | Auto / Manual | Notes |
|---|---|---|---|
| 1 | Pre-flight: iPhone reset + region + timezone + location off | **Manual** (Dais once per device) | iOS Settings checklist below |
| 2 | Fresh Apple ID with US billing | **Manual** (Dais, ~10min) | Apple gift card $30 to fund |
| 3 | Buy US phone number from SMSPool | Auto | scripts/smspool-buy.sh |
| 4 | TikTok signup via phone-number SMS code | Auto (Playwright + SadCaptcha) | scripts/signup.sh |
| 5 | OTP relay: SMSPool fails → Slack DM Dais → he types code | Auto (with manual fallback) | scripts/otp-relay.sh |
| 6 | Settings to default "naked" profile (no PFP/bio/link for 48-72h) | Auto | scripts/ghost-mode.sh |
| 7 | Hand off to warmup-tiktok skill | Auto | invokes warmup-tiktok |
| 8 | After warmup: set PFP + bio + bio link | **Manual** (Dais reviews assets first) | scripts/finalize.sh |

## Manual prerequisites (Dais once per device)

iPhone iOS Settings:
- Settings → General → Language & Region → United States
- Settings → General → Date & Time → Set Automatically OFF, timezone = New York
- Settings → Privacy & Security → Location Services → OFF (entirely, never re-enable)
- Settings → VPN: Surfshark or NordVPN configured with Dedicated IP add-on
- IP city must match Apple ID city (Manhattan ↔ NY-IP, LA ↔ LA-IP)

## Output

Per persona triplet (TT/IG/YT), state stored at:
\`\`\`
~/anicca-monk-factory/accounts/<persona-slug>/
  ├── tiktok.json    {handle, password, phone_number, sms_pool_order_id, created_at, status}
  ├── apple_id.json  {{{profile.lateness.stakeholders.channel}}, password, phone, billing_address, region}
  ├── proxy.json     {provider, ip_city, dedicated_ip, expires_at}
  └── _next_step.md  human-readable handoff note for warmup-tiktok
\`\`\`

## Status

**SCAFFOLDED** — script stubs in place. Each step marked TODO until Dais procures hardware (M6 + M7 in MASTER_PLAN.md Phase 4). When hardware ready, run end-to-end on persona #1 to validate, then iterate.

## Reference: Shalev's account creation evidence

- Yang Mun: 5M followers, $500K/6mo, 7 AI characters across 30+ accounts
- Julian Ivaldy / THE QUEST: 500M views verified using identical playbook
- Both confirmed: iPhone (NOT Android — Android leaks GPS deeper), Dedicated IP (NOT shared), phone-number signup (NOT {{profile.lateness.stakeholders.channel}}), 2-day pacing between account creations

## Why "semi-automated" (not full-auto)

2026 TikTok detection stack defeats most {{profile.lateness.stakeholders.channel}} automation:
- Device fingerprinting + canvas/WebGL/touch event checks
- Phone OTP (catchable but slow)
- Captcha (SadCaptcha solves ~80%)
- IP-trust scoring (residential proxy required, datacenter banned)

Realistic estimate: 30-60min human-in-loop per persona triplet, mostly OTP entry and the first 30min manual FYP curation per platform. Worth it because each persona × N platforms × N langs unlocks Postiz fan-out at our content scale.
