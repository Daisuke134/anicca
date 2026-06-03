---
name: adapter-bland-ai
description: Bland.ai outbound voice call adapter for Anicca. Thin REST wrapper around POST https://api.bland.ai/v1/calls. Use when Anicca needs to phone a real person (wakeup call, meeting reminder, gig client follow-up, lead qual). Voice + script + phone are arguments; the call runs server-side at Bland and a webhook delivers the transcript.
metadata:
  type: custom-adapter
  spec: 12-CUSTOM-ADAPTERS.md
  parallel_safe: true
  invariants:
    rate_limit_calls_per_hour: 20
  requires:
    bins: [bash, curl, jq]
    env: [BLAND_API_KEY]
---

# adapter-bland-ai

Outbound voice call adapter. Bland.ai is REST-only — no browser dance needed. The single script wraps `POST /v1/calls`.

## Scripts

| Script | Use |
|---|---|
| `scripts/outbound-call.sh <phone> <script> [voice] [--dry-run]` | Trigger an outbound call. `--dry-run` includes `"should_call": false` in payload (Bland echoes config without dialing). |

## Env

Requires `BLAND_API_KEY`. **If absent** (= not yet provisioned at signup), every call records a `{status:"missing-key"}` line to `state/call-log.jsonl` and exits non-zero — NOT a Dais escalation, this is a round-2 signup task for Anicca herself.

## Rate cap

`state/call-log.jsonl` tracks calls. Local sleep gate enforces ≤ 20/h.
