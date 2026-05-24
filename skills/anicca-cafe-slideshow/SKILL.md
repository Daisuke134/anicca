---
name: anicca-cafe-slideshow
description: Daily AI slideshow factory for Anicca fashion (Tee/Hoodie/Cap). Generates 2 AI model images (male+female) wearing the day's product via fal.ai, composes 6 slides with impermanence narrative, drafts to TikTok @anicca.jpx via Postiz. Single bash command end-to-end. Triggered by cron at 10 JST. Drafts mode (privacy_level=SELF_ONLY, content_posting_method=UPLOAD) — Dais reviews in TikTok app inbox before posting.
metadata:
  tags: fashion, slideshow, tiktok, postiz, fal.ai, marketing, draft
  requires:
    bins: [bash, python3, postiz]
    env: [FAL_API_KEY, POSTIZ_API_KEY, POSTIZ_TIKTOK_INTEGRATION_ID, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID]
---

# anicca-cafe-slideshow

Daily AI slideshow → TikTok @anicca.jpx draft for fashion products.

## YOUR ENTIRE TASK

```bash
bash ~/.openclaw/skills/anicca-cafe-slideshow/scripts/00-run-daily.sh
```

That bash script:
1. Picks today's product from `data/products.json` rotation (DOW 1=Tee, 2=Hoodie, 3=Cap, 4=Tee, 5=Hoodie, 6=Cap, 7=Tee). Override via `PRODUCT=<slug>` env.
2. Generates 2 AI model images (male + female wearing product) via fal.ai flux/dev.
3. Composes 6 slides (1080x1920 9:16) with Pillow:
   - Slide 1: "Everything fades." hook on cream
   - Slide 2: Male model with name + price overlay
   - Slide 3: Female model with "anicca = impermanence" + price
   - Slide 4: Message ("Most things you wear / will outlast / what you believed.")
   - Slide 5: "anicca / impermanence" on ink
   - Slide 6: CTA "aniccaai.com/fashion"
4. Uploads slides to Postiz CDN.
5. NO posting: cafe has no account (canonical 2026-05-19). `scripts/postiz-draft.py` skips the POST (guarded `TIKTOK_INT = None`); stale id `cmlrv8jq…` purged. Re-enable only when a real account exists.
6. Posts Slack #metrics summary.

Final stdout line is what cron passes to Slack:

```
✅ slideshow drafted: <slug> | postiz post=<id> | slides=6 | slack ts=<ts>
```

## Output structure

```
output/<DATE>_<PRODUCT>_<SLOT>/
├── images/
│   ├── model-male.jpg
│   └── model-female.jpg
├── slides/
│   └── slide_01..06.png
├── caption.txt
└── postiz-receipt.json
```

## Cron

`anicca-cafe-slideshow-daily` 0 10 * * * Asia/Tokyo

## Notes

- Drafts mode (`SELF_ONLY` + `UPLOAD`) means it lands in TikTok app Inbox; Dais must tap Post manually until SNS warmup factory completes.
- Once warmup factory provisions `@anicca.fashion` etc, swap `POSTIZ_TIKTOK_INTEGRATION_ID` to that integration.
- fal.ai flux/dev = ~$0.025/image × 2 images = ~$0.05/day for AI models. Slides themselves are pure Pillow (no API cost).
