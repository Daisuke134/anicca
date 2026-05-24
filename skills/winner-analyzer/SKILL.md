---
name: winner-analyzer
description: "Weekly skill that scrapes top-performing TikTok posts per persona, extracts winning hook patterns, and appends 14 new bank entries per language. The bank evolves toward proven viral structures (Darwinian selection)."
metadata:
  tags: tiktok, apify, gpt-5.4-mini, bank-evolution, weekly
  requires:
    bins: [curl, python3, ffmpeg, ffprobe, whisper]
    env: [APIFY_TOKEN, OPENAI_API_KEY]
---

# Winner Analyzer — How to run

You are a cron-fired agent. Your only job is to run one bash command and exit.

## Trigger
- OpenClaw cron: weekly Mon 04:00 JST
- Cron message: `bash ~/.openclaw/skills/winner-analyzer/scripts/run-detached.sh weekly`

## What it does (informational)

1. Reads `~/anicca-monk-factory/personas.json`
2. For each persona: Apify `clockworks~tiktok-scraper` → last 7 days → top 3 by views
3. For each top post: download MP4 + Whisper transcript + 3 thumbnail frames
4. gpt-5.4-mini extracts: hook pattern / structure / emphasis_words / why-it-worked
5. gpt-5.4-mini generates 14 new bank entries matching the winning patterns
6. Appends to `~/anicca-monk-factory/scripts/bank_<lang>.jsonl`
7. Writes weekly report to `~/anicca-monk-factory/state/winner_report_<YYYYWW>.md`
8. Slack notify (if SLACK_WEBHOOK_URL set), else log to file

## Where output goes

```
~/anicca-monk-factory/state/winner_report_<YYYYWW>.md   ← human-readable report
~/anicca-monk-factory/state/winners_<YYYYWW>.json       ← machine-readable
~/anicca-monk-factory/scripts/bank_en.jsonl             ← +14 entries
~/anicca-monk-factory/scripts/bank_jp.jsonl             ← +14 entries
```

## Failure handling

- If Apify returns nothing for a persona (account too new, < 7 days posts): skip with note
- If gpt-5.4-mini fails: fall back to rotating last week's bank (no new entries)
- On any error, the cron delivery system reports to Slack. Do not retry inside the same run.
