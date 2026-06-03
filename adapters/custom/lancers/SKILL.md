---
name: adapter-lancers
description: Lancers.jp gig platform adapter for Anicca. Camofox-driven session persistence (Google OAuth), inbox read, and DM send (≤ 10/h rate cap). No public API — uses saved cookie session under ~/.camofox/profiles/anicca/lancers/. Read this skill whenever Anicca needs to apply to a Lancers gig, respond to a client message, or scan inbox for new threads.
metadata:
  type: custom-adapter
  spec: 12-CUSTOM-ADAPTERS.md
  parallel_safe: true
  invariants:
    rate_limit_dm_per_hour: 10
    rate_limit_bid_per_day: 3
    session_chmod: 600
  requires:
    bins: [bash, curl, jq, camofox]
    env: [GOOGLE_LOGIN_EMAIL, GOOGLE_LOGIN_PASSWORD]
    services: [camofox-browser:9377]
---

# adapter-lancers

JP gig platform adapter. Lancers has no public API — this adapter wraps camofox so Anicca can keep a long-lived session cookie under `~/.camofox/profiles/anicca/lancers/` and replay clicks against the inbox / thread DOM.

## Scripts

| Script | Use |
|---|---|
| `scripts/login.sh` | One-time + idempotent. Opens lancers.jp via camofox, Google OAuth with env creds, persists cookie. Writes `state/lancers-session.json` (chmod 600). |
| `scripts/send-dm.sh <thread_url> <body>` | Sends a DM in the given thread. Enforces ≤ 10 DM/h via local sleep gate. |
| `scripts/read-inbox.sh` | Returns JSON list of recent threads via camofox snapshot. |

## Session

camofox userId=`anicca`, sessionKey=`lancers`. Cookie/storage persist under `~/.camofox/profiles/anicca/lancers/`.

## Rate cap

`send-dm.sh` reads `state/dm-log.jsonl`, counts entries in last 3600s, and sleeps / refuses if ≥ 10. NO bot-burst behavior — per spec §5 anti-goals.

## CAPTCHA

Per HARD RULE #-1: if camofox snapshot reports a CAPTCHA element, the script logs the verbatim block and exits non-zero. No "ask Dais" — the loop owner retries on next cron with a fresh sessionKey.
