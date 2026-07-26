# DEMO-READY — the stranger funnel, swept and repaired the night before

Dais presents 2026-07-27 and 07-28. An Opus-driven sweep walked every surface a QR-scanning
stranger hits; five findings, all closed the same night, each with a production readback.

| finding | fix | readback |
|---|---|---|
| `?tg=` dropped across Google OAuth → Telegram never binds (one real victim row measured) | one line in anicca-products `lib/auth.ts`: redirect keeps `location.search` | new bundle `page-a96e1758….js` on aniccaai.com contains `location.search` |
| mandatory $20 wall mid-onboarding, no trial — unpaid users got zero calls | `LM_COMP_UNTIL` read-time comp window (PR #1153, 46/46, `paid` never written, Stripe stays single writer, self-expiring) | boot log `[comp] LM_COMP_UNTIL active until 2026-07-28T15:00:00.000Z` |
| Composio quota ≈2 users (8,849/20,000 used by one) | `LM_CAL_CACHE_TTL_MS=900000` (5→15 min) | var present on service |
| both admin alerts dead (incl. Telnyx low-balance; balance $20.86) | `LM_ADMIN_TELEGRAM_CHAT_ID=0000000000` | var present on service |
| onboarding nudges every 2 min mid-flow | 30-min per-uid cooldown + `notifications_enabled` join (PR #1153) | tick e2e in tests: sent=1 / +2min sent=0 / +31min sent=1 |

Swept clean without changes: QR decodes to `t.me/LifeManagerBotbot?start=lp`; webhook healthy,
fail-closed (401/405); Stripe link live; phone collected in onboarding; no hardcoded owner chat id
in runtime; no staging artifacts on the landing page.

Known risks accepted for the demo window: Telnyx balance covers ~2 days (alert now wired); comp
window expires 07-29 00:00 JST by itself; the in-memory nudge cooldown resets on deploy (costs at
most one extra message).
