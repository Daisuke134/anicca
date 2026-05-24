---
name: account-burn-detector
description: "Auto-detect shadowbanned / dead social accounts using anicca-socials snapshot. Auto-disables related cron jobs via openclaw cron disable, logs to ~/anicca-monk-factory/accounts/burn/burned.jsonl, and Slack-notifies with full verdict + disabled-cron list. Runs weekly Mon 04:25 JST. Replaces old Apify-based version (Apify rate-limited 2026-05)."
metadata:
  tags: account-management, shalev, anti-shadowban, kpi, auto-disable
  requires:
    bins: [python3, openclaw, curl]
    env: [SLACK_BOT_TOKEN, SLACK_CHANNEL_ID]
  data_source: ~/.openclaw/skills/anicca-socials/state/socials_latest.json

# Burn rule
# - views_7d < 10 AND posts_7d >= 5 → SHADOWBAN_BURN (auto-disable cron + log + Slack)
# - 10 <= views_7d < 100 AND posts_7d >= 5 → WATCH (Slack note only)
# - else → HEALTHY
---

# account-burn-detector — How to run

```
bash ~/.openclaw/skills/account-burn-detector/scripts/run.sh
```

Or via Python directly:

```
python3 ~/.openclaw/skills/account-burn-detector/scripts/run.py
```

Reads `~/anicca-monk-factory/personas.json` for active personas, Apify-scrapes each TT handle's posts, computes avg playCount of first 10, classifies, optionally moves dead personas to `accounts/burn/burned.jsonl`.

## Verdict logic (Shalev rule)

| avg first-10 plays | classification | action |
|---|---|---|
| ≤100 | 🔴 SHADOWBANNED | move to `burned.jsonl` + Slack critical alert + (manual) trigger account replacement |
| 100-199 | 🟡 watch | stay, re-test next week |
| ≥200 | 🟢 OK, algorithm testing | continue posting |

## Output

- per-persona verdict JSON: `~/anicca-monk-factory/state/burn_check_<YYYYMMDD>.json`
- Slack thread per persona + summary
- if 🔴 → `~/anicca-monk-factory/accounts/burn/burned.jsonl` appended

## Trigger
- weekly Mon 04:25 JST via `account-burn-detector-weekly` openclaw cron
