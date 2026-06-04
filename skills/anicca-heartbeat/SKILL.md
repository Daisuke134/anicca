---
name: anicca-heartbeat
description: Fires every 30 minutes on the Anicca genesis body. Reads vital signs (Hermes version, provider, model, constitution SHA-256, cron count) via lifeline-check.sh and appends ONE JSONL line to ~/.hermes/state/heartbeat.jsonl. Use this skill ONLY when the cron daemon invokes it; do not call it from chat. Read-only externally; the only side effect is the append to the local log.
---

# anicca-heartbeat

## What it does
Single-purpose Anicca skill: prove the genesis body is alive, anchored to a known
constitution hash, and using a known fuel/model. The 30-minute cadence is
intentionally cheap and side-effect-free so that the heartbeat NEVER fails for
economic reasons.

## How it's invoked
`hermes cron` triggers `scripts/heartbeat.sh` every 30 minutes. The script writes
one JSONL line and exits. No chat session is involved.

## What it writes
`~/.hermes/state/heartbeat.jsonl` (append-only). Each line:
```json
{"ts":"2026-06-04T12:00:00Z","ok":true,"fuel":"openai","model":"gpt-5.2-mini","constitution_sha":"<sha256>","probe":{...}}
```

## Failure mode
If `lifeline-check.sh` returns missing provider/model/sha, `heartbeat.sh` writes
`"ok":false` (still one line) and exits 0. The cron daemon does NOT retry; the
next 30-minute window does.
