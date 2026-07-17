# Capafy listing — Life Manager / "Leave-Time Planner" (ready-to-publish draft)

Sell a lite version of Life Manager as a Capafy agent skill. Per CAPAFY_PROFITABLE_PLAYBOOK: top sellers run
run_online + a 3-tier subscription + Sonnet 4.6 + an emoji-headed listing. Clone the WINNING structure WHOLE
(no blending). This file = the listing content; publish via the Capafy pipeline (init → configure --deep-scan
→ ship → web submit) when Dais is available (it's a marketplace publish on his account).

## Name
Leave-Time Planner

## Short description (pain/credibility-first)
Stop being late. It reads your day, blocks travel time before every event, and tells you the exact minute to leave — and pings you again 5 minutes before, sharper.

## Welcome message
👋 I'm your Leave-Time Planner. Tell me your day (or connect your calendar) and I'll work out when you actually have to walk out the door for each thing — not when it starts, when you must LEAVE. Try: "I have a 3pm dentist in Shibuya, when do I go?"

## Detailed description (emoji-headed)
✨ **What it does**
- Works backward from each event: leave time = start − travel − a buffer.
- Blocks the travel time so your calendar shows the real commitment.
- Tells you the leave minute and nudges again right before, more urgently.

🎯 **Best for**
People who are chronically a few minutes late, who read "10:00 meeting" and forget the 30-minute commute.

💡 **Why it's different**
Most reminders fire at the event time. This one fires at the LEAVE time and escalates — the moment that actually keeps you on time.

⚙️ **How it works**
| Step | What it does |
|---|---|
| 1 | Reads the events you give it (or your calendar) |
| 2 | Estimates travel to each location |
| 3 | Computes leave = start − travel − buffer |
| 4 | Tells you the leave time + a sharper second nudge |

## Pricing (3-tier subscription — COPY the winning ladder WHOLE, do not blend)
- Day: $1.99 / cap 10 messages
- Week: $4.99 / cap 35 messages
- Month: $9.90 / cap 120 messages
- 24h free trial.
(Model: Sonnet 4.6, run_online. Matches the top-seller pattern in CAPAFY_PROFITABLE_PLAYBOOK §2.)

## Publish checklist (Dais / when available — marketplace publish on the Capafy account)
- [ ] capafy init → confirm files (DESELECT workspace docs) on web
- [ ] capafy configure --deep-scan → confirm secrets on web
- [ ] capafy ship → web submit
- [ ] publish-refresh-url to re-mint the temp link
NOTE: this is the LITE/standalone planner (text in → leave-time out), NOT the full phone-calling product (that
is the $20/mo Telegram product at aniccaai.com/life-manager). The Capafy version is the funnel: it shows the
leave-time value; the CTA points to the full caller.
