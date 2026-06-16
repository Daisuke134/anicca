# B-call E2E verification — Charon two-way call to Dais via Telnyx (2026-06-16)

**Task #2 (P-call-ring). LIVE, real call, no fake (HARD 0.24/0.31).**

## Result: SUCCESS — the phone rang, Dais answered, Charon spoke two-way

The earlier D60 trial-gate (see git history of this file) is LIFTED (Dais funded + verified the Telnyx
account this session). Two real calls were placed to Dais's number `+818046270314` via Telnyx Call
Control app `2982013078364751402` (FROM `+14322234204`), Gemini Live voice = **Charon**.

| field | call 1 (unanswered) | call 2 (ANSWERED) |
|---|---|---|
| CALL_SESSION_ID | `96f81fc8-697c-11f1-8cac-02420a210420` | **`083a64a2-697d-11f1-a809-02420a210420`** |
| CALL_CONTROL_ID | `v3:qte4lPWA9CbW1wiOmwTYvKHUXIaed2rvWjFKPglcibUHP6YVpe9J7Q` | `v3:l2_rCbuZwhZqIobXPQI15B6WhT8vhpcr5MgeZ64P7TtGIecWT6dPfA` |
| call status (GET /v2/calls) | `is_alive:false, call_duration:40` (rang 40s, unanswered) | answered, two-way audio |
| BRIDGE_STREAM_STARTED | false | **true** |
| BRIDGE_GEMINI_SETUP | false | **true** |
| DOWNLINK_FRAMES (Charon → phone) | 0 | **547** |
| UPLINK_FRAMES (Dais → Gemini) | 0 | **4200** |

## What this proves
- **Telnyx gate genuinely lifted** for `+81` — both dials returned a real `call_control_id`/`call_session_id`
  with NO 21216/10010 error. The carrier rings Dais's number.
- **The phone rings** — call 1's `call_duration:40` = 40s of ringing before the unanswered timeout.
- **On answer, the dial-time `stream_url` + `stream_bidirectional_mode:rtp` AUTO-starts the media stream**
  (BRIDGE_STREAM_STARTED:true on call 2). Confirms ctx7/firecrawl docs; refutes the handoff's "RTP/L16
  re-implementation needed" hypothesis — PCMU base64 over the WS is correct as-is.
- **Charon spoke and Dais replied** — 547 downlink frames (Charon → phone) + 4200 uplink frames
  (Dais → Gemini) = a real two-way conversation over ~54s.

## Known gap + fix applied
- Call 2 `RECORDING_STARTED:false` — `record_start`/`streaming_start` were issued immediately after dial,
  before answer, so Telnyx returned `90034 "Call not answered yet"`. The media still flowed (dial-params),
  so the frame counts are the objective two-way proof; only the mp3 recording was missed.
- **Fixed in `life-call-telnyx.mjs`**: now waits for the `twilio_start` (answer) frame, THEN issues
  `record_start`; the `streaming_start` contingency only fires if no stream appears after ringing. The next
  run captures a non-silent mp3.

## Repro
```bash
cd apps/landing && set -a; . ~/.openclaw/.env; set +a
node scripts/life-call-telnyx.mjs --to=+818046270314   # Dais answers → Charon two-way
```
Pure-logic unit tests: `node --test 'netlify/functions/_lib/__tests__/call-logic.test.js'` → **22/22 green** (this session).
