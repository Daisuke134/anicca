---
name: anicca-warmup-flip
description: "Daily 06:30 JST cron. Scans state/postiz-integrations.json for warmup_phase=warmup accounts. Sets warmup_started_at=today if missing. Flips warmup_phase to 'live' after 7 days. Slack pings on each flip."
metadata:
  tags: warmup, postiz, newsletter, growth
  requires:
    bins: [python3]
    env: [SLACK_BOT_TOKEN]
---

# Anicca Warmup Auto-Flip

For new TikTok/IG/YT accounts: 7-day soft-launch (post_mode=draft + auto-music)
then auto-flip to direct_post live mode. Per Spec Part L.

## Usage

`bash ~/.openclaw/skills/anicca-warmup-flip/scripts/run.sh`

## Mutation

postiz-integrations.json: warmup_started_at (= today if missing) +
warmup_phase (= 'live' after 7d).

Post scripts must read warmup_phase to decide DRAFT vs DIRECT_POST.
