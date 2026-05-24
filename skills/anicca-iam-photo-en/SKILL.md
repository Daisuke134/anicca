---
name: anicca-iam-photo-en
description: Daily Template A (photo + serif 5-line, EN) TikTok @anicca.jpx draft. 1:1 clone of @iam.affirmations photo template (DIht2HVR3VC). Single bash entry. Drafts mode (SELF_ONLY + UPLOAD).
metadata:
  tags: marketing, slideshow, tiktok, postiz, iam, en, affirmation, daily
  requires:
    bins: [bash, python3, postiz]
    env: [FAL_API_KEY, POSTIZ_API_KEY, POSTIZ_TIKTOK_INTEGRATION_ID, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID]
---

# anicca-iam-photo-en

Daily Template A (photo background + serif 5-line, English) → TikTok @anicca.jpx draft.

## Run

```bash
bash ~/.openclaw/skills/anicca-iam-photo-en/scripts/00-run-daily.sh
```

## Pipeline

1. Pick 5 EN affirmations from `data/quotes.json` (Louise Hay + Develop Good Habits, 100 verbatim) by day-of-year `(doy - 1) % 100`.
2. Generate 1080×1350 photo background via fal.ai flux/dev ($0.025).
3. Pillow compose: bg + dark gradient overlay + DM Serif Display header "Repeat with me:" + 5 affirmation lines + `aniccaai.com` watermark.
4. Upload PNG to Postiz CDN.
5. POST `/public/v1/posts` → TikTok integration `cmp93bkpu01uvoh0yd3aj560g` (iam EN slideshow, canonical 2026-05-19) as `SELF_ONLY` + `UPLOAD` (= drafts mode).
6. Slack `#metrics` summary.

## Output

```
output/<DATE>_<SLOT>/
├── picks.json             ← 5 affirmation objects from pool
├── images/bg.jpg          ← fal.ai photo
├── slides/slide_01.png    ← composed 1080×1350
├── caption.txt
└── postiz-receipt.json
```

## Final stdout line

```
✅ slideshow drafted: anicca-iam-photo-en | postiz=<id> | slides=1 | slack ts=<ts>
```

## Cron

`anicca-iam-photo-en-daily` `0 9 * * *` Asia/Tokyo

Source-of-truth spec: `docs/superpowers/plans/2026-05-12-iam-mantra-marketing.md`
