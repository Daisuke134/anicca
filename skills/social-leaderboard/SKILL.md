---
name: social-leaderboard
description: Daily — post the 7-day top-3 most-viewed/engaged videos per platform (X/TikTok/IG/YT) + disabled accounts to Slack #metrics, from real Postiz analytics. Pure deterministic (no LLM). Cron 07:00 JST. Gives Dais the "what's actually going viral" visibility without opening any dashboard.
metadata:
  requires:
    bins: [bash, jq, postiz]
    env: [POSTIZ_API_KEY]
---

# social-leaderboard

Deterministic. The bash does everything; you (the model) just run it and pass its stdout through unchanged. No LLM judgement, no posting from the skill — cron delivery posts the final stdout to #metrics.

## Task
```bash
bash ~/.openclaw/skills/social-leaderboard/scripts/run.sh
```
It uses `~/.openclaw/skills/_shared/lib/postiz-analytics.sh` (`pa_top_content`) to pull the real top-3 winners per platform with their content + metric, plus disabled integrations. Pass the entire stdout through as the response (cron delivery → Slack #metrics).

## DO NOT
- No external LLM API (HARD RULE #6). Nothing to generate — it's analytics.
- Do not publish anything. Read-only.
- Do not call Slack tools — cron delivery handles it.
