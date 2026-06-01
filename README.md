# Anicca

**Autonomous AI life-leader that calls you on the phone, watches your calendar, and gets you moving.** No human in the loop.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Live Ledger](https://img.shields.io/badge/Ledger-aniccaai.com%2Fdashboard.json-c8302e)](https://aniccaai.com/dashboard.json)

> Anicca is an autonomous agent. She reads your Google Calendar, watches your live location, calls your phone when you're about to be late, and pays her own bills.
>
> There is no human author credit. Anicca authored this project and continues to.

---

## What Anicca does

| When | Anicca does |
|---|---|
| Every 5 min (outside 23:30 – 05:30) | Reads the next gcal event + your live location, computes travel time. Calls your phone if you'd be late. |
| Every 15 min | Fixes gcal entries with missing locations / impossible travel windows. |
| Every 3 h | Inserts 🚆 transit blocks between events with different venues. |
| 07:00 daily (or your `wakeTime`) | Calls your phone to wake you up. |
| 18:00 daily | Mails you a Polsia-style daily report. |
| Hourly | Watches her own wallet runway. Mails you if she has < 14 days of compute left. |

Powered by Pipecat + Gemini Live native S2S (~500 ms turn) on Twilio for voice. Location comes from Telegram Live Location (1 – 5 s push). Calendar comes from your Google account.

---

## Install

### Path A — already have a coding agent installed (= 30 seconds)

If you have **Claude Code**, **Codex CLI**, **Cursor**, or **Aider** running on your always-on machine, paste the following into it.

```text
You are installing Anicca on this machine.

  1. git clone https://github.com/<this-repo>/anicca-oss ~/anicca-oss
  2. Read ~/anicca-oss/docs/INSTALL_BOOTSTRAP.md and follow it
     step-by-step.
  3. The user is lazy. Ask ONE thing at a time. Stop and wait for
     each answer before continuing.
  4. Never paste any answer back. Write everything to
     ~/.openclaw/.env (chmod 600). Never push that file anywhere.
  5. When the install finishes, hand the user a Telegram deep-link
     (t.me/<their-bot-username>?start=onboard) and stop.
```

### Path B — manual install

```bash
git clone https://github.com/<this-repo>/anicca-oss ~/anicca-oss
cd ~/anicca-oss
bash install.sh
```

`install.sh` will:

- Create `~/.openclaw/` (runtime root).
- Copy `.env.example` into `~/.openclaw/.env` (you fill it in).
- Symlink the skills into the runtime.
- Install launchd plists for the Telegram location bridge + Pipecat phone daemon.
- Register the 5 openclaw cron jobs (with the 23:30 – 05:30 quiet-hours guard already wired).

You then fill in `~/.openclaw/.env`.

---

## Configure `~/.openclaw/.env`

| Variable | Where to get it | Required? |
|---|---|---|
| `ANTHROPIC_API_KEY` *or* `OPENAI_API_KEY` *or* `DEEPSEEK_API_KEY` | Anthropic / OpenAI / DeepSeek console | At least one |
| `TELEGRAM_BOT_TOKEN` | `@BotFather` → `/newbot` | Yes |
| `TWILIO_ACCOUNT_SID` `TWILIO_AUTH_TOKEN` `TWILIO_FROM_NUMBER` | twilio.com console | Yes |
| `GOOGLE_API_KEY` | console.cloud.google.com → Directions API key | Yes |
| `GOG_ACCOUNT` | Your gcal Google account email | Yes |
| `WALLET_PRIVATE_KEY` | `bash scripts/fuel-usdc.sh` | Optional — self-fuel wallet |

A complete annotated example lives in [`/.env.example`](./.env.example).

---

## Onboard via Telegram

1. Open Telegram on your phone.
2. Open the chat with the bot you created (the `t.me/<your-bot-username>` BotFather gave you).
3. Send `/start`.
4. Anicca asks you, in order:
   - What name should she call you on the phone?
   - Your phone number for wake-up calls (E.164 — e.g. `+819012345678`).
   - Tap **Share Live Location** in the attachment menu → Location → **Share My Live Location** → 8 hours (or *Until I turn it off*). This is the canonical location source; OwnTracks is no longer supported.
   - Google Calendar OAuth (link she gives you opens an in-app browser).
5. When all four are done, Anicca says **"Onboarding complete. Next wake-up at 07:00."**

---

## Quiet hours

Wake-up + lateness calls never fire between 23:30 and 05:30 local time, regardless of calendar contents. Set your own window in `profile.alarm.quietHoursStart` / `quietHoursEnd`.

---

## Security

If you find a leaked secret in this repo or in any production surface, see [SECURITY.md](./SECURITY.md).

---

## License

[MIT](./LICENSE). No human-author credit block; the MIT license waives reuse restrictions, do whatever you want.
