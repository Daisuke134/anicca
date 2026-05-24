---
name: hot-hooks-refresh
description: Daily — distil the last 7 days' winning post hooks (across X/TikTok/IG/YT, from real Postiz analytics) into ~/.openclaw/skills/_shared/state/hot-hooks.json so every content cron's STEP 1 reads what is actually working instead of guessing. Replaces the homegrown trend-hunter. Cron 06:00 JST (before content crons at 07:05+).
metadata:
  requires:
    bins: [bash, jq, postiz]
    env: [POSTIZ_API_KEY]
---

# hot-hooks-refresh

You are the LLM running this skill (HARD RULE #6: you do the pattern-extraction yourself — no external LLM API). The bash only pulls deterministic analytics.

## Task

1. Gather the real winners (deterministic):
```bash
bash ~/.openclaw/skills/hot-hooks-refresh/scripts/gather.sh /tmp/hot-hooks-raw.json
```
This writes top-5 posts per platform (x / tt / ig / yt) with their **actual content + metrics + score** from live Postiz analytics.

2. Read `/tmp/hot-hooks-raw.json`. For each platform, look at the highest-scoring posts' actual text. Extract WHY they beat the near-zero baseline: the hook shape, opening line pattern, angle (data / contrarian / story / question), length, presence of a concrete number or first-person claim. Ignore vanity — only posts that out-performed the platform's median.

3. Write `~/.openclaw/skills/_shared/state/hot-hooks.json`:
```json
{
  "generated_at": "<UTC ISO>",
  "by_platform": {
    "x":  { "winning_patterns": ["<short rule>", ...], "top_examples": ["<exact hook line>", ...], "avoid": ["<what flopped>"] },
    "tt": { ... }, "ig": { ... }, "yt": { ... }
  },
  "global_takeaways": ["<1-3 cross-platform rules to apply in STEP 2/3 today>"]
}
```
Keep each list ≤5 items, concrete, copy-usable. This file is read by every content skill's STEP 1 (x-marketing, 4.7-slideshow, sao, etc.) — it is the closed loop's memory.

4. Final stdout line (cron delivery → #metrics):
`✅ hot-hooks refreshed: x=<n> tt=<n> ig=<n> yt=<n> winners | top: <best hook 60 chars>`
where `<n>` = the number of winners gather.sh returned for that platform (the raw count, matches gather.sh's own "N winners" line). If a platform has zero positive signal (all score 0, e.g. TikTok on un-warmed accounts), append `(0 signal)` to its count — e.g. `tt=5(0 signal)` — so #metrics readers are not misled into thinking there are learnable winners.
or `❌ hot-hooks FAILED: <reason>`

## DO NOT
- No external LLM API — you extract the patterns (HARD RULE #6).
- Do not publish anything. Read-only analytics + one JSON write.
- Do not invent winners — only use what gather.sh returned from real Postiz data.
