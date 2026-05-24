---
name: anicca-iam-photo-ja
description: Daily Template A (photo + Noto Serif JP 5-line, JA) TikTok @anicca.jpx draft. 1:1 clone of @iam.affirmations photo template, Japanese pool. Drafts mode.
metadata:
  tags: marketing, slideshow, tiktok, postiz, iam, ja, affirmation, daily
  requires:
    bins: [bash, python3, postiz]
    env: [FAL_API_KEY, POSTIZ_API_KEY, POSTIZ_TIKTOK_INTEGRATION_ID, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID]
---

# anicca-iam-photo-ja

Run: `bash ~/.openclaw/skills/anicca-iam-photo-ja/scripts/00-run-daily.sh`

Pipeline same as `anicca-iam-photo-en` but Japanese affirmations (玉野湖太 + i.am app verified) + Noto Serif JP. Cron: `5 9 * * *` Asia/Tokyo.

Spec: `docs/superpowers/plans/2026-05-12-iam-mantra-marketing.md`
