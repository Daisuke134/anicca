# WS6j — Life Manager Telegram onboarding (parity with web /lm)

Date: 2026-06-19
Worktree / branch: `../anicca-lm-telegram` / `feature/lm-telegram-onboarding`

## Context

The Telegram bot the user currently talks to (`@AniccaLifeBot`, token in `~/.openclaw/.env`) is the
**OpenClaw personal Anicca (#1)** — NOT the Life Manager. Life Manager needs its OWN bot + onboarding,
at parity with the web `/lm` flow (Google Calendar + Gmail connect, phone, $20/mo, then the cloud
loops manage the user: wake calls, location asks, travel blocks, late-notices).

## The one human input (bot creation is the only non-autonomous step)

Telegram bot creation is ONLY possible via @BotFather from a Telegram **user** account — there is no
Bot-API method to create a bot, and we have no MTProto user session. So Dais creates the LM bot once
(@BotFather → `/newbot` → name `Anicca Life Manager`, username e.g. `AniccaLifeManagerBot`) and pastes
the token. Everything else is built + wired autonomously. Token stored as `LM_TELEGRAM_BOT_TOKEN`
(distinct from OpenClaw's `TELEGRAM_BOT_TOKEN`) in Railway (life-call) + Netlify env.

## Architecture

Telegram can't host Google OAuth or Stripe checkout in-app, so the bot is the **entry + notification +
reply channel**; the heavy onboarding (login, connect, phone, pay) happens on the existing web `/lm`,
deep-linked with the Telegram chat id. The always-on **life-call** Railway service (already public,
already runs the loops) hosts the bot webhook — one service, no new infra.

```
 user → @AniccaLifeManagerBot  /start
        │  life-call POST /telegram (webhook, secret-token gated)
        ▼
   reply: "Set up Life Manager →" button → https://aniccaai.com/lm?tg=<chat_id>
        │  web /lm: Google login → Composio gcal + Unipile gmail → phone → Stripe (SANDBOX for E2E)
        │  on ?tg=<chat_id>: save lm_users.telegram_chat_id (via a netlify fn)
        ▼
   cloud loops (life-call) act on the row AND, when telegram_chat_id is set, deliver via Telegram:
     - ask: "Where is <event>?" as a TG message; user's TG reply → agentMatchReply → patch calendar
     - notify (WS6g): late-notice via TG
     - wake: still a phone call (the core product); TG gets a heads-up message
```

## Data

`lm_users` add column: `telegram_chat_id text` (nullable). No other schema change.

## Slices (each: build → verify)

| # | Slice | Verify |
|---|---|---|
| 1 | `lm_users.telegram_chat_id` column (Supabase) | column present via REST select |
| 2 | life-call `POST /telegram` webhook: `/start`→deep-link button; secret-token header check; `lib/telegram.js` (sendMessage, setWebhook, answer) | unit: /start payload → correct deep-link reply JSON; live: setWebhook ok |
| 3 | web `/lm` captures `?tg=` → `lm-telegram-link` netlify fn saves `telegram_chat_id` (HMAC uid+sig gated) | row gets telegram_chat_id after a signed call |
| 4 | ask loop: when `telegram_chat_id` set, send the ask via Telegram + read TG replies (webhook → agentMatchReply → patch) | E2E: TG message asks; a TG reply fills the real calendar |
| 5 | notify (WS6g) via Telegram | late-notice arrives as a TG message |
| 6 | set webhook on the real LM bot + full E2E (/start → web onboard sandbox-pay → loop asks on TG → reply fills) | real bot conversation, no mock |

## Out of scope

OpenClaw's `@AniccaLifeBot` is untouched. Wake remains a phone call (Telegram is heads-up + asks/replies).

## Stripe (sandbox) for the pay leg

Use test mode: price `price_1TixctEeDsUAcaLSjxAamSc9` ($20/mo) + a test payment link, test card
4242 4242 4242 4242 — charges nobody. Web `/lm` uses `NEXT_PUBLIC_STRIPE_LM_URL` = the test link for E2E.
