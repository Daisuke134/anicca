---
name: anicca-seo-rank-monitor
description: Daily SEO rank monitor via Brave Search API. Polls ~60 tracked keywords spanning all 7 Anicca products (iOS app, cafe, cemetery, fashion, retreat, mantra, iam) in EN + JA plus brand / SAO-category / competitor-alternative terms, records rank of aniccaai.com / App Store results, daily snapshot JSON with delta vs yesterday, Slack #metrics report. Triggered by cron daily 06:35 JST.
metadata:
  tags: seo, rank-monitor, brave-search, marketing, daily
  requires:
    bins: [bash, python3, jq, curl]
    env: [BRAVE_API_KEY]
---

# anicca-seo-rank-monitor — Single Command Skill

You are an LLM running once via cron. Your only job: execute the bash orchestrator + emit final stdout.

## YOUR ENTIRE TASK

```bash
bash ~/.openclaw/skills/anicca-seo-rank-monitor/scripts/run-daily.sh
```

That bash script:
1. Loads `~/.openclaw/.env` for `BRAVE_API_KEY`
2. Reads tracked keywords (hardcoded inside script):
   - anicca
   - anicca app
   - affirmation app
   - Calm alternative
   - Headspace alternative
   - ai grave
   - ai cafe
   - autonomous AI organization
   - BOND AI
3. For each keyword, GET `https://api.search.brave.com/res/v1/web/search?q=KEYWORD&count=20`
4. For each result, check if `aniccaai.com` or `apps.apple.com/.../anicca` appears → record rank (1-20, or `null` if >20)
5. Append today's snapshot to `state/ranks-YYYY-MM-DD.json`
6. Reports Slack #metrics with delta vs yesterday

## Reporting

Final stdout:
```
📊 SEO rank snapshot YYYY-MM-DD | aniccaai.com tracked: 9 kw | ranks: anicca=1, affirmation app=12, ai grave=NEW, ... | gains: +2 / losses: -1
```

## DO NOT

- Do not exceed 2000 queries/month (Brave free tier)
- Do not call Slack tools yourself

## Files

| File | Purpose |
|------|---------|
| `scripts/run-daily.sh` | Master orchestrator |
| `state/ranks-*.json` | Append-only snapshot per day |
| `prompts/` | (none — pure deterministic API call) |
