# apps/mr-bot

Telegram-based commute agent: it calls you when it is time to leave, sends the
route once you are out the door, and asks before telling anyone you are late.

## Read this before you change anything

| You are working on | Read |
|---|---|
| ★ daily organ — wake calls, travel blocks, live location, route, late notice ★ | `docs/superpowers/specs/2026-08-01-lm-daily-organ-design.md` — **the order of work lives there** |
| platform (finance, marketing, runtime migration, panel) | `docs/superpowers/specs/2026-07-29-mr-bot-finance-marketing-platform-design.md` |

This repository (`Daisuke134/life-manager`) is canonical. Copies of these specs
under `anicca-project` / `anicca-products` are pointers, not sources of truth.
Runtime state and the single-user BYOK build live under the portable state home
`${MR_BOT_STATE_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/mr-bot}`;
they are not production source.

## Where the daily behavior lives

| File | Role |
|---|---|
| `scheduler.js` | the 60s loop: escalating wakes at T-15/10/5, 6h horizon |
| `lib/wake-filter.js` | which events deserve a call at all |
| `lib/travel.js` | writes the `[Travel]` blocks into the calendar |
| `lib/late-notice.js` | late detection, attendee notice, live-location teardown |
| `lib/slash-command.js` | Telegram command router |

## Reading live state

Credentials come from `${MR_BOT_STATE_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/mr-bot}/.env` (`SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY`). Never echo them.

```bash
MR_BOT_STATE_HOME="${MR_BOT_STATE_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/mr-bot}"
set -a; . "$MR_BOT_STATE_HOME/.env"; set +a
curl -s "$SUPABASE_URL/rest/v1/lm_wake_log?select=*&order=id.desc&limit=3" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"
```

Tables: `lm_users`, `lm_wake_log`, `lm_travel_log`, `lm_ask_log`,
`lm_user_locations`.

**Location freshness is `lm_user_locations.observed_at`.** `updated_at` is not
maintained by the upsert, so reading it reports a live feed as dead.
