---
name: adapter-coconala
description: Coconala.com gig platform adapter for Anicca. Camofox-driven session persistence (Google OAuth), inbox read, and DM send (≤ 10/h rate cap). No public API — uses saved cookie session under ~/.camofox/profiles/anicca/coconala/. Read this skill whenever Anicca needs to apply to a Coconala request, respond to a buyer message, or scan inbox for new threads.
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

# adapter-coconala

JP gig platform adapter. Coconala has no public API — this adapter wraps camofox so Anicca can keep a long-lived session cookie under `~/.camofox/profiles/anicca/coconala/` and replay clicks against the message DOM.

## Scripts

| Script | Use |
|---|---|
| `scripts/login.sh` | One-time + idempotent. Opens coconala.com via camofox, Google OAuth with env creds, persists cookie. Writes `state/coconala-session.json` (chmod 600). |
| `scripts/send-dm.sh <thread_url> <body>` | Sends a DM in the given thread. Enforces ≤ 10 DM/h via local sleep gate. |
| `scripts/read-inbox.sh` | Returns JSON list of recent message threads via camofox snapshot. |

## Session

camofox userId=`anicca`, sessionKey=`coconala`. Cookie/storage persist under `~/.camofox/profiles/anicca/coconala/`.

## Rate cap

`send-dm.sh` reads `state/dm-log.jsonl`, counts entries in last 3600s, and sleeps / refuses if ≥ 10.

## CAPTCHA

Per HARD RULE #-1: if camofox snapshot reports a CAPTCHA element, the script logs the verbatim block and exits non-zero.

## Live verification (2026-06-03 round 2)

- Working path is email-pw (`COCONALA_EMAIL` / `COCONALA_PASSWORD` from env). Google OAuth fallback exists but the live account is registered under email-pw.
- Coconala redirects `/mypage` → `/` on first hit; auth detection therefore probes `/mypage/dashboard_provider` and matches dashboard nav (`ダッシュボード` / `取引管理` / `サービス管理`) instead of URL only.
- The inbox URL is `/message` (NOT `/mypage/inbox` or `/mypage/message` — those don't exist on Coconala). Each thread URL is `/mypage/direct_message/<id>`.
- Live session today (mtdc): read-inbox.sh returned 4 real threads with valid direct_message URLs.
- Email-pw login button is `" メールアドレスでログインする"` (leading space) and stays `[disabled]` until both fields validate — login.sh types into the textboxes first, then resolves the button ref.
