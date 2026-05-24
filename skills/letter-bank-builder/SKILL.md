---
name: letter-bank-builder
description: "On-demand skill that generates N short Anicca letters (EN/JP) in batches via gpt-5.4-mini. Each letter is a one-page meditation on impermanence (~150-200 words). Output appended to bank_letter_<lang>.jsonl."
metadata:
  tags: letters, content-generation, batch, gpt-5.4-mini
  requires:
    bins: [python3]
    env: [OPENAI_API_KEY]
---

# Letter Bank Builder — How to use

This skill runs **on-demand**, not on cron. You invoke it manually to seed the daily letter bank.

## How to invoke

```bash
bash ~/.openclaw/skills/letter-bank-builder/scripts/run.sh <lang> <count> [start_id]
```

Examples:
```bash
# Generate 14 EN letters starting from id 1
bash ~/.openclaw/skills/letter-bank-builder/scripts/run.sh en 14 1

# Generate 30 JP letters starting from id 15
bash ~/.openclaw/skills/letter-bank-builder/scripts/run.sh jp 30 15
```

## Output

Appends to `~/anicca-monk-factory/scripts/bank_letter_<lang>.jsonl`. Each line:
```json
{
  "id": "letter-en-001",
  "lang": "en",
  "subject": "...≤80 chars",
  "preheader": "...≤90 chars",
  "html": "<full {{profile.lateness.stakeholders.channel}} HTML>",
  "tags": ["..."],
  "created_at": "ISO ts"
}
```

## Cost
- gpt-5.4-mini: ~$0.005 per letter (~150-200 words + HTML wrap)
- 365 letters × 2 langs = 730 letters × $0.005 = ~$3.65 one-time
- Recommended: seed 14 immediately, generate rest in background or weekly

## Themes covered (49 anchor topics from the ebook + variations)
anicca / dukkha / anatta / 90-second emotion / breath / suffering's expiration / reactivity / sankhara / vedana / impermanence of joy / impermanence of pain / loss / change / aging / death / the self illusion / mindfulness / non-attachment / meditation basics / loving-kindness / equanimity / etc.
