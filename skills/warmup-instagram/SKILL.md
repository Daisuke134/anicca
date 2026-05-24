---
name: warmup-instagram
description: "Phase 4 — 7-day Instagram warmup per Shalev L2. instagrapi-based (subzeroid/instagrapi)."
metadata:
  tags: phase4, warmup, instagram
  status: SCAFFOLDED
  duration_days: 7
  reference: subzeroid/instagrapi (actively maintained 2025+)
---

# warmup-instagram

7-day Personal-account warmup before Business switch. Mirrors warmup-tiktok in shape.

instagrapi is more API-friendly than mobile automation, so this is one of the easier warmups.

## Run

\`\`\`
bash ~/.openclaw/skills/warmup-instagram/scripts/run.sh <persona-slug>
\`\`\`

## Daily routine

| Day | Action |
|---|---|
| 1-2 | 5 explore-feed sessions × 10 min, watch reels, like ~5/session |
| 3-4 | Follow 2-3 niche accounts (only after watching their content) |
| 5-7 | Comment on 1-2 reels/day, save 2-3 reels |

NO PFP / bio / link / first post until day 8.

## Implementation status

instagrapi works headless via Python; no iOS device needed. Easier than TT
warmup. Real implementation lives in scripts/warmup_loop.py (TODO).
