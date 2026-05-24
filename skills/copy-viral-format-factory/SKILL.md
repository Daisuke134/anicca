---
name: copy-viral-format-factory
description: "Meta-skill: discovers viral TikTok formats in a niche, downloads winners, reverse-engineers them frame-by-frame, generates a clone spec + 14-entry bank, and spawns a NEW factory skill ready to post. The factory that builds factories."
metadata:
  tags: meta-skill, virality, factory-generator, tiktok, gpt-5.4-mini, apify
  requires:
    bins: [curl, python3, ffmpeg, ffprobe, whisper, snaptik]
    env: [APIFY_TOKEN, OPENAI_API_KEY]
---

# Virality Copy Factory — How to run

You are a cron-fired agent. Your job is to run one bash command and exit.

This is the **factory that builds factories**. Given a niche keyword, it:
1. Discovers viral TikTok content in that niche
2. Downloads the winners
3. Reverse-engineers them frame-by-frame
4. Generates a clone spec + 14-entry script bank
5. Spawns a new factory skill (skeleton with placeholders)
6. Notifies Dais via Slack to provision the avatar

After Dais provides the avatar/voice IDs, the new factory cron starts posting daily on a warmed-up persona account.

## Trigger

### Weekly autonomous discovery
- Cron: weekly Mon 04:30 JST
- Message: `bash ~/.openclaw/skills/copy-viral-format-factory/scripts/run-detached.sh weekly`
- Picks rotating niche from `state/niches_queue.txt`

### On-demand
- `bash ~/.openclaw/skills/copy-viral-format-factory/scripts/run-detached.sh ondemand "<niche_kw>" "<lang>"`
- Example: `... ondemand "stoicism mindset" en`

## What it does (8 {{profile.lateness.stakeholders.senderType}}s)

| # | Stage | Output |
|---|---|---|
| 1 | DISCOVER | top 5 viral candidates in niche → `state/<run>/candidates.json` |
| 2 | DOWNLOAD | mp4 + Whisper transcript per candidate → `state/<run>/source_<id>.mp4` |
| 3 | ANALYZE | full-frame reverse-engineering + clone spec + 14-entry bank | 
| 4 | SPAWN | new skill at `~/.openclaw/skills/<niche-slug>-factory/` |
| 5 | SLACK | "🏭 new factory blueprint ready — please provision avatar/voice" |

Stages 6-8 (auto avatar provision, test render, auto cron schedule) are deferred to v2 — they currently require Dais's manual blessing of the avatar before the cron is scheduled.

## Output file structure

```
~/.openclaw/skills/copy-viral-format-factory/state/<run-tag>/
├── candidates.json              ← discover {{profile.lateness.stakeholders.senderType}} output
├── source_<id1>.mp4
├── source_<id1>.transcript.json
├── source_<id2>.mp4
├── source_<id2>.transcript.json
├── frames_<id>/                ← extracted frames per candidate
├── reverse_spec.md             ← human-readable clone spec
├── clone_spec.json             ← machine-readable
└── new_bank.jsonl              ← 14 generated bank entries

~/.openclaw/skills/<niche-slug>-factory/  ← spawned new skill
├── SKILL.md                    ← from template, niche-specific
├── CHARACTER_PROMPTS.md        ← from clone_spec.json
└── scripts/                    ← copied from template, ready to run
```

## Failure handling

- DISCOVER returns 0 candidates → abort, log, retry next week
- DOWNLOAD fails for a candidate → skip, continue with rest
- ANALYZE produces malformed JSON → fall back to existing seed factory clone
- SPAWN creates duplicate (skill already exists) → bump suffix `-v2`, `-v3`

## Cost per run
- Apify scraper: ~$0.10
- OpenAI gpt-5.4-mini calls (vision + text): ~$0.50-$1.50 depending on # candidates
- Total: ~$2/run, weekly ~$10/month for autonomous discovery
