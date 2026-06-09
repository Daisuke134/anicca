---
name: wake-me-up
description: Realtime phone wake-up. Calls a person on a real phone (Twilio) and holds a back-and-forth AI conversation (Gemini Live) that persuades them physically out of bed, then keeps re-calling at a fixed gap until they are provably awake. Use for the daily 7am wake-up cron, or any "call X until they wake up" request. Entity-agnostic: pass phone number + name.
metadata:
  tags: voice, twilio, gemini-live, wake-up, alarm, realtime, cron
  requires:
    bins: [bash, node, python3, curl, cloudflared]
    env: [TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, GEMINI_API_KEY, SLACK_WEBHOOK_AGENTS]
---

# wake-me-up

Calls a real phone and has Anicca **talk with** the person (full-duplex, not a recording)
until they are physically out of bed. Re-calls until provably awake.

```
cron 7:00 JST
   │
   ▼
ensure-bridge.sh ── imokenet relay+tunnel healthy? (launchd-managed, KeepAlive)
   │  reads state/public_url.txt
   ▼
wake_loop.py <phone> <name>
   │  place realtime call ─▶ Twilio ─▶ <Connect><Stream> ─▶ imokenet ⇄ Gemini Live
   │  poll Twilio outcome (status, duration)
   │  awake?  answered AND duration >= WAKE_AWAKE_MIN_SEC
   │   ├─ yes ─▶ ☀️ Slack success, stop
   │   └─ no  ─▶ wait WAKE_RETRY_GAP_SEC, call again (up to WAKE_MAX_ATTEMPTS)
   ▼
Slack #metrics report
```

## Architecture

| Piece | Path | Role |
|-------|------|------|
| Realtime bridge | `~/.openclaw/workspace/imokenet/` | Twilio Media Streams ⇄ Gemini Live (`server.js`, `geminiBridge.js`, `audio.js`) |
| Supervisor | `imokenet/run-bridge.sh` | runs relay + cloudflared tunnel, writes `state/public_url.txt` |
| Always-on service | `~/Library/LaunchAgents/ai.openclaw.imokenet.plist` | KeepAlive; restarts bridge on crash/reboot |
| Health/kick | `scripts/ensure-bridge.sh` | idempotent; recovers the bridge if down |
| Wake loop | `scripts/wake_loop.py` | call → judge awake → re-call until awake |

## Run (idempotent)

```bash
bash ~/.openclaw/skills/wake-me-up/scripts/ensure-bridge.sh
python3 ~/.openclaw/skills/wake-me-up/scripts/wake_loop.py {{profile.contact.phone}} {{profile.identity.preferredName}}
```

## Tunables (env)

| Var | Default | Meaning |
|-----|---------|---------|
| `WAKE_AWAKE_MIN_SEC` | 20 | answered + duration ≥ this ⇒ counts as awake |
| `WAKE_RETRY_GAP_SEC` | 60 | gap between re-calls |
| `WAKE_MAX_ATTEMPTS` | 12 | hard cap on calls |

## Awake judgment

v1 heuristic: a call that is **answered** and lasts **≥ WAKE_AWAKE_MIN_SEC** means a real
conversation happened ⇒ awake. `no-answer` / `busy` / very short calls ⇒ re-call.
The Gemini persona explicitly pushes the person to stand up, turn on the light, drink water.

Future hardening (task #4): have the bridge write a per-call "user confirmed standing"
signal (from Gemini `inputTranscription`) so awake is confirmed by what they SAID, not just
call duration.

## Notes

- Quick-tunnel URLs are ephemeral; `/twiml` derives the wss host from the request `Host`
  header, and `wake_loop.py` reads the live URL from `state/public_url.txt`, so a changed
  tunnel URL does not break calls.
- Real delivery only. No dry-run (HARD RULE #14). Test = one real call by Claude, loop logic
  unit-tested with mocked Twilio statuses.
