# LM Gmail honest-OFF + Composio budget guard

## Measured baseline

- `mail-unipile.js` returns `[]`/`false` for missing credentials, network errors, and 401-shaped responses; it emits no warning.
- `ask.js` treats that empty inbox as legitimate and silently continues to Google Search.
- `telegram-onboard.js` still selects the Gmail stage and builds a fallback `gmail=connect` URL when Gmail is unavailable.
- `server.js` advertises `/gmail-connect`; failed hosted auth returns 503, while scheduler configuration checks only token presence, not validity.
- `context-graph.js` has no Gmail dependency. `scripts/e2e-ask.js` still describes the dormant Unipile path.
- Baseline `npm test`: exit 0, 0 failures (2026-07-21, fresh `origin/main` worktree).

## Required behavior

1. A cached (one-hour) provider probe plus `gmail_account_id` decides mail availability. Unavailable mail warns once per throttle window and never blocks Google Search.
2. Telegram onboarding auto-persists `gmail_skipped=true`, says Gmail is currently being prepared, and never renders an OAuth button while unavailable.
3. Every real Composio tool execution records `kind=composio_call` best-effort in `lm_api_cost`.
4. Monthly count `>=18000` sends one throttled admin alert; `>=19500` changes the wake polling interval from 60s to 300s. A new month/count below threshold restores 60s. Calls never hard-stop.

## Verification

- Unit tests cover Gmail probe cache/401, search skip, onboarding auto-skip, budget boundaries, 6h throttle, and recovery.
- Full `npm test`, staging deploy, staging smoke, PR to `dev`, then update consolidation spec §10 order 3 with evidence.
