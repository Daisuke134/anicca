---
name: warmup-tiktok
description: "Phase 4 — 7-day TikTok ghost-mode warmup per Shalev L2. iOS Voice Control + l-portet/tiktok-warmup-bot patterns."
metadata:
  tags: phase4, warmup, tiktok, ios, voice-control
  status: SCAFFOLDED — needs Dais hardware (iPhone Voice Control)
  duration_days: 7
  hardware: iPhone with iOS Voice Control configured
  reference: l-portet/tiktok-warmup-bot (649⭐ on GitHub)
  requires:
    bins: [python3, scrcpy (optional, OTG mirroring), curl]
    env: [SLACK_WEBHOOK_URL]
---

# warmup-tiktok

Per Shalev L2: TikTok account must look like a "bored US human consumer"
for 48-72h MIN before posting any content. This skill orchestrates that.

## Run

\`\`\`
bash ~/.openclaw/skills/warmup-tiktok/scripts/run.sh <persona-slug>
\`\`\`

## What it does (7 days, automated)

| Day | Action |
|---|---|
| 1-2 | 5 sessions × 15 min FYP scroll, watch full videos, like ~5/session, comment on 1 |
| 3-4 | Add 2-3 niche follows (only after watching full content). Still no PFP/bio/link. |
| 5-7 | Bump session count to 6/day. Save 2-3 videos. Daily light comments. |

Daily Slack ping to Dais with progress + flagged anomalies (rate limits, captchas).

## Implementation notes

iOS Voice Control is the only stable 2026 method for true TikTok native-app
automation. Browser TikTok is too restricted.

l-portet/tiktok-warmup-bot pattern:
- Voice Control commands ("scroll up", "tap like", "swipe down") run via accessibility
- Mac sends commands via OTG cable + scrcpy mirror
- Each command triggered via Keyboard Maestro / AppleScript

## Status: SCAFFOLDED

Skill file + run.sh stub in place. Real Voice Control script lives in OTG +
scrcpy + macOS automation — Dais hardware required (iPhone tethered to Mac
Mini via OTG cable).

## Reference: Shalev's L5 burn-test

After 7 days warmup + 10 video posts:
- 🔴 < 100 views/video × 10 → BURN ACCOUNT (shadowbanned, save attempts futile)
- 🟢 200+ views/video → SAFE (algorithm testing, keep posting 3x/day)

The `account-burn-detector` skill (already live, weekly Mon 04:25 JST) automates this verdict.
