---
name: promote-fun-login
description: Create/verify a ZERO-human-credential promote.fun account (AI's own AgentMail email + random password — NEVER a human's Google OAuth/phone 2FA). Use before clip-promote's SELECT step needs a logged-in promote.fun tab.
metadata:
  tools:
    browser: "dedicated CloakBrowser instance, port 9224, profile ~/.cloak/profiles/promote-fun"
    email: "AgentMail API (the AI's own inbox, anicca-genesis@agentmail.to)"
  requires:
    env: [AGENTMAIL_API_KEY]
    bins: [python3, cdp.py (from ~/.claude/skills/ig-account-create/scripts)]
  tags: [promote-fun, clip-promote, zero-human-loop, agentmail, cloakbrowser]
disable-model-invocation: true
---

# promote-fun-login

Register (or confirm) a promote.fun account that an earning loop (`clip-promote`) can
operate autonomously forever — no human credential anywhere in the chain.

## Why this exists (Dais 2026-07-04, hard rule)

> When I say that it's no-human-loop, it means no using human credentials at all. It
> means no using human credential in any way, because that is what it means to be no
> human loop.

The FIRST attempt at this used promote.fun's "Sign up with Google" button with Dais's
personal `keiodaisuke@gmail.com`. Google demanded 2-factor approval — a push
notification to Dais's physical phone. That is a human-in-the-loop dependency baked
into the login method itself (every future re-auth/suspicious-login check would need
his phone again). **Never do that for an AI-operated earning account.** See
[[feedback_earn_accounts_use_ai_own_email_not_dais_google]] for the full postmortem.

## The zero-human-credential path (proven, 2026-07-04)

promote.fun's registration form supports plain Username + Email + Password (in
addition to Google OAuth). Use that:
- Username: any AI-chosen identifier
- Email: the AI's OWN mailbox (`anicca-genesis@agentmail.to`, AgentMail) — never a
  human's address, not even a `+alias` of one
- Password: freshly random, stored in `~/.openclaw/.env` under a service-specific var
- Email verification code: read via the AgentMail API (`GET https://api.agentmail.to/
  v0/inboxes/<inbox>/messages`) — the AI reads its own inbox, no human involved

## Usage

```bash
# 1. Launch (or confirm already running) the dedicated browser instance:
curl -s localhost:9224/json/list >/dev/null 2>&1 || \
  nohup /Users/anicca/.openclaw/skills/_shared/venv-cloak/bin/python3 \
    ~/.claude/skills/promote-fun-login/scripts/launch_promote_browser.py \
    > /tmp/promote-browser.log 2>&1 & disown

# 2. Register end-to-end (idempotent-ish: safe to inspect, will fail cleanly on a step
#    that's already been done rather than double-submit):
set -a; . ~/.openclaw/.env; set +a
/opt/homebrew/bin/python3 ~/.claude/skills/promote-fun-login/scripts/register_flow.py \
  --username anicca_clip_promote --email anicca-genesis@agentmail.to
```

Prints ONE JSON line: `{"ok":true/false,"username":...,"email":...,"password":...,
"logged_in":true/false,"step":"<where it stopped>"}`. `ok:true` means logged in and
ready — `password` is echoed back so the caller can persist it to `.env`
(`PROMOTE_FUN_PASSWORD`, `PROMOTE_FUN_USERNAME`, `PROMOTE_FUN_EMAIL`,
`CLIP_PROMOTE_CDP_PORT=9224`).

## Proven flow (what register_flow.py actually does, step by step)

1. `cdp.navigate(tid, "https://www.promote.fun/")`, wait ~4s for the SPA to render.
2. Dismiss the onboarding modal (best-effort click, harmless if absent).
3. `cdp.click_by_text(tid, "Register")` — the top-right nav button. **Use
   click_by_text, not click_xy with hardcoded coordinates** — raw mouse-event
   coordinates silently no-op'd on some SPA buttons during the original manual run
   (a Google passkey "try another way" link needed a JS `.click()` to actually fire).
4. Fill `input[placeholder="Enter your username/email/password"]` via
   `cdp.click_sel` + `cdp.insert_text` (Input.insertText — no per-character keydown
   loop needed, one call types the whole string).
5. Check the Terms-of-Service checkbox (`input[type="checkbox"]`, the only one on
   this form).
6. `cdp.click_by_text(tid, "Register")` again (the submit button — same text as the
   nav tab, but it's now inside the modal).
7. Poll AgentMail for a message containing "is your verification code" newer than
   the point Register was clicked; extract the 6-digit prefix.
8. Click the first OTP box, `insert_text` the whole 6-digit code (most OTP widgets
   auto-advance focus per input event).
9. `cdp.click_by_text(tid, "Verify Email")`.
10. Confirm login: `document.body.innerText` contains a `$` balance chip near the
    top and no longer shows "Sign up with Google" (i.e., we're past the auth gate).

## Known constraint

Google OAuth remains available as a UI option but MUST NOT be used for any
AI-operated earning account — only for genuinely acting-as-Dais tasks (see
[[identity_anicca_login_accounts]]). If a future platform offers ONLY Google OAuth
(no email+password alternative), that's a genuine constraint — flag it once, don't
silently fall back to a human's identity.
