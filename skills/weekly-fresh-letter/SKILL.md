---
name: weekly-fresh-letter
description: "Weekly skill that writes ONE fresh letter on this week's news × impermanence and inserts it as the next 'alive slot' in bank_letter_<lang>.jsonl. Mimics Daily Stoic's 'meditation + weekly fresh op-ed' pattern."
metadata:
  tags: newsletter, fresh-content, gpt-5.4-mini, weekly
  requires:
    bins: [python3]
    env: [OPENAI_API_KEY]
---

# Weekly Fresh Letter — How to run

You are a cron-fired agent. Your job is to run one bash command and exit.

## Trigger
- OpenClaw cron: weekly Sun 08:13 JST
- Cron message: `bash ~/.openclaw/skills/weekly-fresh-letter/scripts/run-detached.sh weekly`

## What it does

1. gpt-5.4-mini generates 1 fresh letter for each lang (EN + JP) tying this week's general news/cultural moment to impermanence
2. The letter is a one-page meditation, not a hot-take — the news is just the entry door
3. Append to `~/anicca-monk-factory/scripts/bank_letter_<lang>.jsonl` with a flag `"fresh": true`
4. The daily-letter-sender will rotate it into the cycle as a "fresh slot" (every 7 days the cycle advances 1 fresh slot ahead of the bank)

## Output
- 2 entries (en + jp) appended to bank_letter_<lang>.jsonl
- `~/anicca-monk-factory/state/weekly_fresh_<YYYYWW>.log`
- Slack notification if SLACK_WEBHOOK_URL set

## Failure handling
- If gpt-5.4-mini fails: log + skip that lang, the cron continues for the other lang
- Letters are append-only; daily-letter-sender's bank index handles cycle automatically
