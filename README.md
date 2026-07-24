→ Daisuke134/life-manager へ移行済み

# Anicca — Behavior Change Agent + Wake-up SaaS

Proactive agent that helps people break harmful patterns and build better
habits. Two surfaces share one codebase:

| Surface | What | Status |
|---------|------|--------|
| **iOS app** | Onboarding → 13 problem types → scheduled nudges → 1-screen card UX | Live on App Store (1.9.x) |
| **Wake-up SaaS** | $9.99/mo — AI calls you every morning, escalates if you're running late | Live at <https://aniccaai.com/alarm> |

The wake-up SaaS uses a real voice agent ("Anicca") who talks back over PSTN,
not a recorded ringtone. She knows your calendar, your home location, and your
day-job start time — and if you're falling behind schedule she'll keep calling
plus optionally email a 報連相 (heads-up) to your manager.

---

## Repo layout

| Path | What |
|------|------|
| `aniccaios/` | iOS app (Swift / SwiftUI, iOS 15+) |
| `apps/api/` | Node.js mobile backend (Railway) |
| `apps/landing/` | Marketing site + checkout (Netlify, `aniccaai.com`) |
| `apps/alarm-backend/` | Wake-up SaaS (this is what we just open-sourced) |
| `apps/alarm-backend/bridge/` | Gemini Live ⇄ Twilio Media Streams WebSocket bridge (Node) |
| `apps/alarm-backend/scheduler/` | Per-minute alarm + 15-min lateness cron (Python, Railway worker) |
| `maestro/` | E2E test flows |

---

## How the Wake-up SaaS works

```
User signs up at aniccaai.com/alarm
        ↓ Stripe webhook
Supabase `subscriber_profiles` row created (phone, wake_time, tz, name)
        ↓
scheduler/alarm_scheduler.py  (every 60s, multi-tenant)
        ↓  it's wake_time in user's tz, and not fired today
scheduler/wake_loop.py        →  POST /dialout on bridge
        ↓
bridge/server.js              →  Twilio Calls API
        ↓
Twilio → user's phone → bridge WebSocket → Gemini Live (Charon voice)
        ↓
Real two-way conversation until user is verifiably awake.

Then, every 15min from 6:00-23:00 local:
scheduler/saas_lateness.py    →  reads gcal + OwnTracks location
        ↓  ETA - now < buffer
Calls again with lateness persona, optionally emails stakeholders.
```

---

## OwnTracks setup (required for lateness detection)

The lateness loop needs to know where the user is right now. We use
[OwnTracks](https://owntracks.org/) — open-source location publisher — because
it's privacy-respecting (you own the data) and battery-aware.

### One-time setup on the user's phone

1. **Install OwnTracks**
   - iOS: <https://apps.apple.com/app/owntracks/id692424691>
   - Android: <https://play.google.com/store/apps/details?id=org.owntracks.android>

2. **Configure HTTP publishing** (Settings → Preferences → Connection)
   - **Mode**: `HTTP`
   - **URL**: `https://<your-anicca-alarm-backend>.up.railway.app/ingest/owntracks?token=<USER_TOKEN>`
     - The token comes from `aniccaai.com/alarm/setup` after signup.
   - **Identification → DeviceID**: anything (e.g. `iphone`)
   - **Identification → TrackerID**: 2 chars (e.g. `DA`)

3. **CRITICAL: Set mode to _Move_, NOT _Significant_**
   - Open OwnTracks → ⓘ icon → Mode selector
   - Choose **Move**
   - Why: per [OwnTracks docs](https://owntracks.org/booklet/features/location/),
     _Significant_ mode publishes nothing while the device is stationary.
     If the user is asleep in bed, no location update is sent for hours —
     and Anicca then sees a stale fix and can't tell whether they left home.
     _Move_ publishes every 5 min OR 100 m of movement (whichever is sooner),
     which is what the lateness loop needs. Battery cost is roughly that of a
     navigation app, so we recommend the user enables Low Power Mode override.

4. **Grant always-on location permission** (iOS: "Always Allow")
   - Otherwise iOS will silently throttle background publishes.

5. **Verify it's working**
   - Go to `aniccaai.com/alarm/setup` → "Last seen" timestamp should refresh
     within 5 minutes of you walking around with the phone.

### Why HTTP and not MQTT

We support only the HTTP publisher (simpler ops, no broker to run). MQTT will
return.

### Why we don't use Apple Find My / Significant Location Changes

- Find My has no public API.
- iOS Significant Location Changes API only fires on 500m+ movement after 5 min
  — useless while someone is in bed.

---

## Self-hosting

This is the cheap path if you want to run your own wake-up agent for yourself
or a small group.

### Required services (free or near-free tiers)

| Service | What for | Free tier? |
|---------|----------|------------|
| Twilio | Phone number + outbound calls | $1/mo number + ~$0.015/min |
| Google AI Studio | Gemini Live API | yes (per-key quota) |
| Supabase | Subscriber DB | yes |
| Railway | bridge + scheduler hosting | $5/mo hobby |
| Stripe | Billing (skip if self-hosting for yourself) | — |

### Environment variables

Set these in Railway (`apps/alarm-backend/bridge` service) AND
(`apps/alarm-backend/scheduler` worker):

```bash
# Voice + LLM
GEMINI_API_KEY=...
GEMINI_LIVE_MODEL=gemini-2.5-flash-native-audio-preview-09-2025
GEMINI_VOICE=Charon

# Telephony
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...

# Subscriber DB
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...   # service role, not anon

# Stakeholder ETA (lateness loop only)
GOOGLE_API_KEY=...                  # Google Maps Directions API
GOG_ACCOUNT=you@example.com         # which Google account holds the user's calendar
GOG_KEYRING_PASSWORD=...

# Optional integrations
COMPOSIO_API_KEY=...                # 1-click calendar OAuth
SLACK_BOT_TOKEN=xoxb-...            # ops alerts
SLACK_CHANNEL_ID=C...

# Networking
PORT=8787
PUBLIC_BASE_URL=https://<railway-domain>
```

### Deploy

```bash
# bridge (Node)
cd apps/alarm-backend/bridge
railway link
railway up

# scheduler (Python worker — runs every minute via Procfile)
cd ../scheduler
railway link
railway up
```

Supabase schema and Stripe webhook are in the live aniccaai backend; if you're
self-hosting standalone we'll publish a minimal schema separately.

---

## Stack

- **iOS**: Swift, SwiftUI, RevenueCat, Mixpanel
- **Voice**: [Pipecat](https://github.com/pipecat-ai/pipecat) + [Gemini Live](https://ai.google.dev/gemini-api/docs/live) (native audio S2S)
- **Telephony**: Twilio Media Streams
- **Backend**: Node.js (bridge), Python (scheduler), Express, Railway, Supabase
- **Tests**: Maestro (E2E)

---

## Status

| Component | State |
|-----------|-------|
| iOS app | Live (1.9.x) |
| Alarm SaaS | Live, paid customers since 2026-05-23 |
| Lateness loop | Live, requires OwnTracks Move mode (see above) |
| Self-host docs | Minimal (this file) — improvements welcome via PR |

---

## License

The code is OSS so people can learn from it and self-host. Commercial use,
trademarks, and the "Anicca" name are reserved. See `LICENSE` once published.

## Contact

- Landing: <https://aniccaai.com>
- Issues: GitHub issues on this repo
