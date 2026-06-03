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

Requires `BLAND_API_KEY`. **If absent** (= not yet provisioned at signup), every call records a `{status:"missing-key"}` line to `state/call-log.jsonl` and exits non-zero — NOT a Dais escalation, this is a follow-up signup task for Anicca herself.

### Signup prerequisite (verified live 2026-06-03 via camofox)

bland.ai/signup requires **First/Last name + phone number + email + T&C**, and login at app.bland.ai/login is **phone+SMS code only** (no email password / no Google OAuth). Therefore Bland.ai signup blocks on having a phone number Anicca can receive SMS to. The deterministic next-action chain is:

1. Provision an Anicca-owned phone number with SMS receive (= SMSPool API signup, or Twilio inbound number, or another SMS-receive endpoint already wired into Anicca's stack).
2. Sign up at `app.bland.ai/signup` via camofox using that phone + `contact@aniccaai.com` (= the AgentMail forwarding alias already provisioned).
3. Verify via SMS → capture API key from dashboard → write to `~/.openclaw/.env` as `BLAND_API_KEY=<key>` (chmod 600 preserved).
4. Re-run `outbound-call.sh --dry-run` to validate.

Per HARD RULE #-2 this is NOT "Dais click required" — it's a multi-step camofox flow that depends on the SMS receive prerequisite. Until step 1 lands, `outbound-call.sh` returns deterministic `{status:"missing-key"}`.

## Rate cap

`state/call-log.jsonl` tracks calls. Local sleep gate enforces ≤ 20/h.
