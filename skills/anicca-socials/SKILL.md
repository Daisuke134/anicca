---
name: anicca-socials
description: Daily per-account social analytics from Postiz — pull last 7 days posts for every TT/IG/YT/X account, aggregate views/likes/comments per account, identify viral / dead accounts, post Slack report, and update dashboard.json with `socials` field for the aniccaai.com "Anicca Socials" card. Use when triggered by anicca-socials-daily cron, or told to "report views", "weekly account ranking", "アカウント別ビュー", "どのアカウントがバイラル".
metadata:
  tags: dashboard, postiz, analytics, accounts, socials, daily-report
  requires:
    bins: [bash, python3, jq, curl, git]
    env: [POSTIZ_API_KEY, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID]
---

# anicca-socials

Daily report on per-account social performance.

## What it does

1. Pull all 26 connected accounts from Postiz (`/integrations`)
2. Pull all posts from last 7 days (`/posts?startDate=...&endDate=...`)
3. For each post, hit `/analytics/post/{id}` and sum views / likes / comments
4. Group by account, rank by total views
5. Classify accounts:
   - **alive** — views > 0
   - **dead** — < 10 views with 2+ posts (shadowban / cold-start failure)
   - **viral** — avg views >= 1000
6. Write `state/socials_<date>.json` snapshot
7. Post Slack message to `SLACK_CHANNEL_ID` with the ranking + dead list + headlines
8. Write `state/socials_latest.json` for `aniccaai-dashboard` to read into `dashboard.json` `socials` field

## Run

```bash
bash ~/.openclaw/skills/anicca-socials/scripts/run.sh
```

## Cron

Daily 06:30 JST (`30 06 * * *`) — runs after `aniccaai-dashboard-refresh` 04:00 fire so dashboard.json picks up fresh socials data on next refresh.

## Output schema

`state/socials_latest.json`:

```json
{
  "updated_at": "2026-05-08T06:30:00Z",
  "window_start": "2026-05-01",
  "window_end": "2026-05-08",
  "totals": {
    "accounts": 26,
    "alive_accounts": 9,
    "dead_accounts": 10,
    "weekly_views": 35732,
    "weekly_likes": 179,
    "weekly_comments": 14,
    "weekly_posts": 380
  },
  "accounts": [
    {
      "platform": "youtube",
      "handle": "@anicca-jp",
      "name": "Anicca",
      "posts_7d": 24,
      "views_7d": 14467,
      "likes_7d": 24,
      "comments_7d": 5,
      "avg_views": 603,
      "engagement_rate": 0.18
    },
    ...
  ],
  "dead_handles": ["monk_anicca", "obou_anicca", "..."],
  "viral_handles": []
}
```

## Slack message format

⚠️ Cron runs must post to Slack with an explicit target. Use `channel:{{profile.channels.reportChannel}}` (or `SLACK_CHANNEL_ID`) every time. Never rely on the default recipient.
If using any helper or message wrapper, pass the target explicitly, never omit it.

```
*📊 Daily Anicca Socials report (last 7 days)*
_window: 2026-05-01 → 2026-05-08, 380 posts across 26 accounts_

*🟢 Alive accounts (views > 0):*
[ranked table]

*💀 DEAD accounts (< 10 views, 2+ posts) — recommend SHUTDOWN:*
[list]

*Headlines:*
• 🔥 best: <top account> ~Xk views/wk
• 💀 N accounts at 0 views (shadowban)
• ⚠️ <viral or notable insight>
```

## Why this exists

- Anicca runs N (currently 26) accounts across TT/IG/YT/X. Without per-account analytics, dead accounts silently waste posting budget for weeks.
- 2026-05-08 first run discovered: **all 10 TikTok accounts at 0 views (widespread shadowban)** while YT and IG are healthy. This insight is invisible in `kpi-dashboard` (which only aggregates totals).
- Triggers cascade decisions: 0-view accounts → `account-burn-detector` flags → Dais decides shutdown.

## Failure modes

| Symptom | Cause | Recovery |
|---|---|---|
| Slack post fails | `SLACK_BOT_TOKEN` invalid | refresh token in `~/.openclaw/.env` |
| `_err` in account row | per-post analytics call timed out | re-run; Postiz analytics is rate-limited |
| `posts_7d` = 0 for everyone | Postiz API returned no posts | check `POSTIZ_API_KEY` valid |
