# WS6k — Interactive Telegram onboarding (bot guides step-by-step, acknowledges each)

Date: 2026-06-19 | worktree `../anicca-lm-interactive` / `feature/lm-telegram-interactive`

## Why
Today /start dumps the user to the web app and everything happens there silently. Dais wants the BOT
to be conversational: guide one step at a time and acknowledge each ("✅ calendar connected, now Gmail
… ✅ phone saved, now subscribe … 🎉 all set, let's go").

## Design
Heavy OAuth/pay still happen on web `/lm` (Telegram can't host Google OAuth or Stripe), but the bot
ORCHESTRATES: it tracks the user's progress from their `lm_users` row (keyed by `telegram_chat_id`)
and, on each stage transition, sends the next single step + an acknowledgement.

Stage = pure function of the row:
| stage | condition | bot says |
|---|---|---|
| `calendar` | linked, `calendar_provider != composio_gcal` | "Let's connect your Google Calendar → [link]" |
| `gmail` | gcal done, no `gmail_account_id` | "✅ Calendar connected! Now Gmail → [link]" |
| `phone` | gmail done, no `phone` | "✅ Gmail connected! Add your phone → [link]" |
| `pay` | phone done, `paid != true` | "✅ Phone saved! Last step — subscribe \$20/mo → [link]" |
| `done` | `paid = true` | "🎉 All set! I'll start managing your schedule." |

Two triggers:
1. **Proactive nudge loop** (life-call, ~2 min): for every row with `telegram_chat_id`, compute stage;
   if it changed since `tg_onboard_stage`, send the new stage's message + persist `tg_onboard_stage`.
   This is what makes "✅ connected, now do X" appear automatically as they progress on web.
2. **On message** (/telegram webhook): `/start` → send the current stage message (or `calendar` if not
   yet linked). Any other text → if not `done`, reply with the current stage (guidance); if `done`,
   it's a location reply → existing resolveTelegramReply path.

All step links point to `/lm?tg=<chat_id>` (the page resumes at the right step). Dedup via the new
`lm_users.tg_onboard_stage` column so a stage is announced once.

## Slices (build → verify)
| # | slice | verify |
|---|---|---|
| 1 | `tg_onboard_stage` column | present (done) |
| 2 | `lib/telegram-onboard.js` — `computeStage(row)` + `stageMessage(stage,chat,base)` pure | unit test: each row shape → correct stage + message has the right link |
| 3 | webhook: /start + non-done text → stage guidance | simulated update → 200 + correct send |
| 4 | `startOnboardLoop` nudge in scheduler; persists tg_onboard_stage | live: flip a field on Dais's row → bot sends the matching step; idempotent (no resend) |
| 5 | full live: Dais /start → guided steps acknowledged | real bot conversation |

## Out of scope
Pre-link nudging (before the user ever opens /lm we don't know their uid) — handled by the /start reply.
