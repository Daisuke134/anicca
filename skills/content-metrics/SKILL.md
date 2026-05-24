---
name: content-metrics
description: Cross-account, cross-platform content analytics. One skill, three modes (daily / zero_view / rollup) dispatched via MODE env. Pulls Postiz analytics for every integration in ~/.openclaw/state/postiz-integrations.json, posts a daily Slack digest, flags 3-day zero-view streaks, and writes a 7-day top-performers.json that larry-strategy-updater consumes.
metadata:
  tags: content, analytics, postiz, cross-account, slack, larry, reelclaw, build-in-public
  requires:
    bins: [bash, curl, jq, python3]
    env: [POSTIZ_API_KEY]
    files:
      - ~/.openclaw/state/postiz-integrations.json
---

# content-metrics — three modes, one skill

Dispatch is via `MODE`:

```
MODE=daily    bash ~/.openclaw/skills/content-metrics/scripts/run.sh
MODE=zero_view bash ~/.openclaw/skills/content-metrics/scripts/run.sh
MODE=rollup   bash ~/.openclaw/skills/content-metrics/scripts/run.sh
```

`CONTENT_METRICS_DRY_RUN=true` flips every mode to print-only. Daily prints the digest it would send; zero_view prints flags it would alert; rollup writes `top-performers.json` with `dry_run: true`.

## Mode 1 — daily (`0 6 * * *` Asia/Tokyo)

Reads each `active: true` integration from the portfolio. For each:

1. `GET https://api.postiz.com/public/v1/posts?startDate=$YESTERDAY&endDate=$NOW` — list posts in the last 24 h.
2. Filter posts where `post.integration.id === <integration.id>`.
3. For each matched post id: `GET https://api.postiz.com/public/v1/analytics/post/<post_id>`.
4. Persist raw analytics to `~/.openclaw/workspace/content-metrics/<YYYY-MM-DD>/<platform>-<handle>.json`.
5. Aggregate per integration: `posts(24h)`, `total_views`, `total_likes`, `engagement_rate = (likes/views) * 100`.
6. Compose Slack digest table → `#metrics` (`{{profile.channels.reportChannel}}`). DRY_RUN: print the formatted table to stdout, do NOT post.

## Mode 2 — zero_view (`15 6 * * *` Asia/Tokyo, runs after daily)

Reads the last N days of `~/.openclaw/workspace/content-metrics/<date>/...` files. For each integration:

- Compute `streak`: number of consecutive most-recent days where total views < 100.
- If `streak >= 3` → flag account as **dying**.
- Persist streak state to `~/.openclaw/state/content-metrics/zero-view-streaks.json`.
- For flagged accounts, the Slack alert MUST include three actions (buttons or text):
  - 🔥 **launch warmup new account** — kick the new-account warmup flow for the same persona.
  - 🩹 **try last-resort hook reset** — force a hookPool refresh for the slot.
  - 💀 **sentence to death** — same protocol as Shalev's `account-burn-detector`: append to `~/anicca-monk-factory/accounts/burn/burned.jsonl`.
- DRY_RUN: print the flag list and the actions, do NOT post and do NOT mutate `burned.jsonl`.

## Mode 3 — rollup (`0 7 * * 1` Asia/Tokyo — Monday 07:00)

Runs after the daily ran for the Sun→Mon overnight transition.

1. Read the last 7 day-folders under `~/.openclaw/workspace/content-metrics/`.
2. For each integration, sum 7-day views, likes, post count.
3. Compute top-5 / bottom-5 across **all integrations** (not within a single skill).
4. Write `~/.openclaw/state/content-metrics/top-performers.json` with `top5`, `bottom5`, `period_start`, `period_end`, `dry_run` flag.
5. Post a Slack digest leaderboard. DRY_RUN: write file (with `dry_run: true`) and print the leaderboard, no Slack post.

## Relationship to `account-burn-detector`

| | `content-metrics-daily` | `account-burn-detector` |
|---|---|---|
| schedule | daily 06:00 JST | weekly Mon 04:25 JST |
| signal | Postiz analytics (views, likes, engagement) per integration | Apify TikTok scrape, avg playCount of first 10 videos (Shalev rule) |
| write path | `~/.openclaw/workspace/content-metrics/<date>/...` and `~/.openclaw/state/content-metrics/...` | `~/anicca-monk-factory/state/burn_check_<YYYYMMDD>.json` and `~/anicca-monk-factory/accounts/burn/burned.jsonl` |
| triggers death | NO — only suggests `💀 sentence to death` action | YES — auto-appends to `burned.jsonl` |
| coexistence | Fast daily signal across all platforms | Deep weekly signal, TikTok-only, Apify-grounded |

No path collision. `content-metrics` recommends sentencing; `account-burn-detector` actually does it. The two share the same `burned.jsonl` as the kill switch.

## How larry-strategy-updater consumes the rollup

`larry-strategy-updater` reads `top-performers.json` (if present) at step 2.5 of its prompt. Cross-account top-5 winners that match a hook in the larry hookPool become additional **SCALE** candidates, on top of the larry-only `hook-performance.json` rule. If the file is missing (rollup hasn't run yet, or was cleaned), step 2.5 is a no-op.

## Flipping out of DRY_RUN

For each cron, edit `~/.openclaw/cron/jobs.json` and set `CONTENT_METRICS_DRY_RUN=false` in the payload's exported env block (or remove the line). Or use jq:

```
jq '(.jobs[] | select(.name=="content-metrics-daily").payload.message) |= sub("CONTENT_METRICS_DRY_RUN=true";"CONTENT_METRICS_DRY_RUN=false")' \
  ~/.openclaw/cron/jobs.json > /tmp/jobs.json && mv /tmp/jobs.json ~/.openclaw/cron/jobs.json
```

Repeat for `content-zero-view-watcher` and `content-7day-rollup`.
