---
name: warmup-youtube
description: "Phase 4 — Light 1-2 day YouTube warmup. Watch niche videos from linked Gmail to seed interest graph."
metadata:
  tags: phase4, warmup, youtube
  status: SCAFFOLDED
  duration_days: 2
---

# warmup-youtube

YouTube is the LIGHTEST warmup of the 3 platforms. Algorithm is interest-graph
driven, less paranoid about new channels. 1-2 days suffices.

## Run

\`\`\`
bash ~/.openclaw/skills/warmup-youtube/scripts/run.sh <persona-slug>
\`\`\`

## Daily routine

| Day | Action |
|---|---|
| 1 | Watch 3-5 niche videos from the Gmail (NOT the Brand Account) — informs interest graph |
| 2 | Watch 3-5 more, like 1-2, subscribe to 1 niche channel |

Day 3+: ready for spawned factory cron uploads via Postiz YT integration.

## Implementation

YouTube Watch History API requires no automation — just open YT logged in as
the parent Gmail and watch a few videos manually. Or use YouTube's iframe API
in headless Chrome (Playwright) to "watch" videos programmatically.

Real script (TODO): scripts/watch_loop.py with Playwright YT iframe player.
