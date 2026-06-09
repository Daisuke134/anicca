---
name: anicca-life-manager
description: |
  Push-type AI phone agent. Reads your Google Calendar + live location, computes your real depart-by time per event, and calls you when it's time to leave — capped at 3 attempts, never endless. If you run late it can notify the right person, only after you confirm. Runs locally on your own always-on machine with YOUR OWN keys (BYOK); your location, calendar, and contacts never leave your device.
metadata:
  tags: [voice, calendar, reminder, twilio, pipecat, gemini-live, telegram, byok]
  type: life-manager
  requires:
    bins: [python3, gog, curl, jq]
    env: [TELEGRAM_BOT_TOKEN, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, GEMINI_API_KEY, GOOGLE_API_KEY, GOG_ACCOUNT]
---

# anicca-life-manager

Calendar-driven phone agent. Every few minutes it reads your next Google Calendar event + your live location, computes the real time you must leave (travel ETA + per-event buffer), and calls you when it's time. If you're late, it can notify the right person — only with your confirmation.

## Architecture

```
[Google Calendar] -- poll every 5 min --> [gcal_departures.py] travel-time + per-event buffer
        |                                          |
[Telegram Live Location] ----------------> [lateness_check.py] decision engine
        |   depart_by <= now+lead & at home -> call
        v
[Twilio + Gemini Live (Pipecat)] capped reminder call (max 3, 60-120s apart)
[renraku.py] late-notice email -- confirm-gated (off by default)
```

## PREREQUISITES (you set this up — not the package's job)

Anicca runs on YOUR always-on machine. The download installs the skill bundle; you bring the infrastructure:
1. An always-on machine (Mac mini, home server, VPS) with an agent runtime (Claude Code / Codex / OpenClaw).
2. A Telegram bot (BotFather -> /newbot) — drives Telegram Live Location (the location source).
3. Your own API keys in a local .env (see env list) — BYOK.
4. install.sh registers the local daemons (Telegram-location bridge, Pipecat phone) + the 5-min calendar poll. login/OAuth/2FA are done by you.

## Capafy Disclosure (R1/R2/R3 — Download, all data local)

| # | Item | Detail |
|---|---|---|
| (1) Data accessed | GPS/velocity (via your Telegram Live Location), calendar events (Google Calendar), your phone number / home address / stakeholder contacts (local config). All stored locally; nothing sent to us. |
| (2) External services | Telegram (Live Location), Twilio (calls), Gemini Live (voice), Google Directions (travel time), Google Calendar (read), Gmail/gog (late-notice email). |
| (3) Credentials (BYOK — you supply) | TELEGRAM_BOT_TOKEN, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, GEMINI_API_KEY, GOOGLE_API_KEY, GOG_ACCOUNT. |
| (4) When calls/email fire | Call: when depart_by <= now + lead and you're still at home. Email: only when an event has passed and you haven't arrived. |
| (5) Max retry / rate limit | Calls capped at 3 attempts (LATE_RELENTLESS_MAX, default 3), 60-120s apart — never endless. Email: 1 per event. |
| (6) Pause / stop | Set lifeManager.enabled=false in your profile to stop everything (enforced in code: life_manager_enabled()). Quiet hours (23:30-05:30 default) suppress routine calls. |
| (7) Third-party contact consent | Late-notice email is OFF by default; sent only if you opt in (lateness.autoSendMail=true). Otherwise a draft is shown for your confirmation (enforced: auto_send_allowed()). |

No Supabase. No OwnTracks. Location is Telegram Live Location only.

## Inputs (local config)

- profile config: alarm.wakeTime, alarm.eventStyles[type].buffer, lateness.stakeholders[], lateness.autoSendMail, lifeManager.enabled, location.homeLat/homeLon
- .env: the BYOK keys above

## Run

```bash
bash scripts/run.sh          # 5-min heartbeat: gcal departBy x Telegram location -> call if late-risk
```

## Failure modes
- Twilio/Gemini dialout fail -> retry max 3 -> stop.
- Telegram location silent -> use last known + flag stale.
- Google Directions quota -> haversine fallback x1.5.

## Limits enforced in code
- RELENTLESS_MAX_DEFAULT = 3 (lateness_check.py)
- life_manager_enabled(profile) — lifeManager.enabled=false halts the run
- auto_send_allowed(profile) — third-party email requires lateness.autoSendMail=true, else draft-only
</content>
