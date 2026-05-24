---
name: anicca-retreat-slideshow
description: Daily content-first TikTok slideshow factory for Anicca Retreats. Posts USEFUL DHARMA INSIGHT (suffering-reduction) — retreat is the soft CTA underneath, not the hero. 6 slides per day, typography-only (no fal.ai cost), 7 theme rotation by day-of-week (anxiety / comparison / over-stimulation / anger / insomnia / grief / scattered mind). Drafts to TikTok via Postiz integration cmlrv8jq000hun60yy57eaptx (@anicca.jpx) until anicca.retreat warmup account exists. Triggered by cron at 11:30 JST daily.
metadata:
  tags: retreat, slideshow, tiktok, postiz, dharma, content-first, marketing, draft
  requires:
    bins: [bash, python3, postiz]
    env: [POSTIZ_API_KEY, POSTIZ_TIKTOK_INTEGRATION_ID, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID]
---

# anicca-retreat-slideshow

Daily content-first dharma slideshow → TikTok @anicca.jpx draft. Useful insight first. Retreat is the soft CTA underneath, not the hero.

## YOUR ENTIRE TASK

```bash
bash ~/.openclaw/skills/anicca-retreat-slideshow/scripts/00-run-daily.sh
```

That bash script:
1. Picks today's theme from `data/themes.json` rotation (DOW 1=anxiety, 2=comparison, 3=over-stimulation, 4=anger, 5=insomnia, 6=grief, 7=scattered). Override via `THEME=<slug>` env.
2. Composes 6 slides (1080x1920 9:16) with Pillow typography (no AI image gen — saves cost, stays on-brand):
   - Slide 1: Hook (universal pain — "you can't sleep")
   - Slide 2: Diagnosis (Buddhist insight, no marketing)
   - Slide 3: Remedy (one practical technique)
   - Slide 4: 3-step practice instruction (numbered)
   - Slide 5: Bridge ("for ten days, you can practice this in silence" — soft, no logo, no price)
   - Slide 6: Small CTA (`aniccaai.com/retreat`, mono micro-type)
3. Uploads slides to Postiz CDN.
4. POSTs to `/public/v1/posts` with TikTok integration `cmlrv8jq000hun60yy57eaptx` (@anicca.jpx) in drafts mode.
5. Posts Slack #metrics summary.

Final stdout line:
```
✅ retreat slideshow drafted: <theme> | postiz post=<id> | slides=6 | slack ts=<ts>
```

## Content philosophy

Per Dais (2026-05-09): "We shouldn't be promoting the product so much. We should just really try to be useful to people, and then the retreat is going to be the product, the CTA."

Same model as Anicca iOS app marketing: don't say "download the app" — say "here's how to reduce your suffering" and put the app at the bottom. Same for retreats: provide dharma insight + practice; the 10-day silent retreat is the natural conclusion, not the pitch.

## Output structure

```
output/<DATE>_<THEME>_<SLOT>/
├── slides/
│   └── slide_01..06.png
├── caption.txt
└── postiz-receipt.json
```

## Cron

`anicca-retreat-slideshow-daily` 30 11 * * * Asia/Tokyo (registered via openclaw cron add)

## Notes

- Drafts mode (`SELF_ONLY` + `UPLOAD`) → lands in TikTok app Inbox; Dais (or warmup factory) reviews before posting.
- Once SNS warmup factory provisions `@anicca.retreat` (or `@nature.retreat`), swap `POSTIZ_TIKTOK_INTEGRATION_ID` to that integration's id in `data/config.json`.
- Zero AI image cost. Pure Pillow typography on cream + terracotta + ink palette (matches `/retreat` LP DNA).
- 7-day theme rotation prevents repetition.
- Retreat URL CTA always on slide 6 only — never in caption-shouting style.
