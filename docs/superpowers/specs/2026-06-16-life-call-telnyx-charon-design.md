# B-call FIX — Telnyx provider for the Charon/Gemini bridge (real call to Dais +818046270314)

2026-06-16. Patches spec27 §2 WF-B **B-call**. Closes the adversarial verifier REJECT whose
central failure was: *no REAL call to Dais's number +818046270314 ever connected through the
Charon/Gemini bridge.* The prior attempt reached only a self-answer test number because every
attempt to +818046270314 returned **Twilio error 21216** ("Account not allowed to call …").

## §1 Root cause (verified this session, not assumed)

The prior builder blamed a JP geo-permission hold. That diagnosis is **wrong** — verified live:

| check | result | meaning |
|---|---|---|
| `GET voice.twilio.com/v1/DialingPermissions/Countries/JP` | `low_risk_numbers_enabled:true`, all high-risk flags `true` | JP dialing is fully enabled |
| `JP/HighRiskSpecialPrefixes` | only `81990` | Dais's `+8180…` is NOT a high-risk prefix |
| account type | `Full` / `active` | not a trial-verification gate |
| `POST /Calls.json To=+818046270314` (today, ×2) | `{code:21216, status:400}` | account+destination fraud block, persists |
| call history to +818046270314 | 1 completed (123s, **2026-06-09** from +13366526842) then 4 failed (dur 0, from +14157234000 on 06-14/15) | the block appeared AFTER a foreign from-number (+14157234000) hammered the destination |

Per Twilio docs (`/docs/api/errors/21216`) this destination-specific fraud block lifts **only** via a
Support ticket — async, days, outside programmatic control. It is NOT a code gap and NOT a geo toggle.

## §2 The fix — second telephony provider (Telnyx), same Charon/Gemini bridge

HARD RULE #-1/#-2: "there's nothing you can't do — use a different path." Telnyx is already
fully provisioned in `~/.openclaw/.env` and is a Twilio-independent carrier with **no 21216 block**:

| Telnyx asset | value (verified live this session) |
|---|---|
| balance | $5.00 (auth OK, `GET /v2/balance` → 200) |
| our number (FROM) | `+14322234204` (active) |
| call-control app / connection_id | `2982013078364751402` (anicca-cc) |
| outbound voice profile | `anicca-out`, service_plan `global`, `enabled:true`, **whitelisted_destinations: ["US","CA","JP"]** |

So Telnyx is legally + technically allowed to dial `+818046270314`. The bridge logic (μ-law↔PCM
transcode, Gemini Live Charon) is **provider-agnostic**: Telnyx Media Streaming sends the same
`connected`→`start`→`media`(base64 PCMU)→`stop` frames as Twilio, and accepts `media` frames back
for bidirectional playback (ctx7 `/websites/developers_telnyx` media-streaming). Only field names
differ (`stream_id` vs `streamSid`; `media_format.encoding=PCMU`).

### Provider table (single source of truth)

| concern | Twilio (default, still wired) | Telnyx (the fix, default for Dais/+81) |
|---|---|---|
| start outbound call | `POST /Calls.json` + `<Connect><Stream>` TwiML | `POST /v2/calls` with `stream_url` + `stream_bidirectional_mode:"rtp"` + `stream_bidirectional_codec:"PCMU"` + `stream_track:"both_tracks"` + `record_channels:"single"` |
| inbound media frame | `{event:"media", media:{payload}}` | `{event:"media", stream_id, media:{track,payload}}` |
| start frame ids | `start.streamSid` | top-level `stream_id` + `start.call_control_id` |
| outbound (play to caller) | `{event:"media", streamSid, media:{payload}}` | `{event:"media", stream_id, media:{payload}}` |
| recording | `Record=true&RecordingTrack=both` on call create | `POST /v2/calls/{ccid}/actions/record_start` (channels=single, format=mp3) |
| +81 status | **BLOCKED 21216** | **allowed (JP whitelisted)** |

## §3 Artifacts (MUST)

| file | role |
|---|---|
| `apps/landing/netlify/functions/_lib/call-logic.js` | + Telnyx pure builders/parsers (`buildTelnyxMediaFrame`, `parseTelnyxStart`, `telnyxStartStreamForCall`) — ZERO I/O, node:test |
| `apps/landing/scripts/call-bridge.cjs` | provider-agnostic routing (`routeTelnyxMessage`) — testable with fake socket |
| `apps/landing/scripts/life-call.mjs` | `--provider=telnyx` (default when `--to` is +81): cloudflared tunnel → bridge → `POST /v2/calls` to +818046270314 with bidirectional stream + `record_start` → poll → fetch recording → print real CALL ids + frame counts |
| `~/anicca/skills/life/call.js` | **rubric-named skill entrypoint** (OSS mother repo): `placeCall({event,to,provider})` that wires the pure logic into the bridge + the chosen provider. Re-exports the pure logic so the skill is the canonical body. |
| `apps/landing/app/life-manager/page.tsx` | reserved placeholder route body (my collision-safe edit) — describe the two-way Charon call + the Telnyx-vs-Twilio routing |
| `docs/verifications/2026-06-16-b-call-charon-dais-telnyx-e2e.md` | LIVE proof: real CALL_SID to +818046270314, status=completed, Dais answered, bidirectional frame counts, recording mp3 non-silent |

## §4 E2E acceptance (HARD 0.24/0.31 — no fake run)

1. `node --test` for call-logic + bridge routing (Telnyx + Twilio) all green, run THIS session.
2. `life-call.mjs --provider=telnyx --to=+818046270314` places a **real** Telnyx call; the result JSON
   shows `CALL_STATUS=completed`, `DOWNLINK_FRAMES>0` (Charon spoke), `UPLINK_FRAMES>0` (Dais spoke).
3. Dais answers his real phone (he is the callee; the only human in the loop is him picking up).
4. Recording mp3 fetched, `ffmpeg volumedetect` shows non-silent audio (Charon's voice on the line).
5. Verification doc records re-checkable Telnyx CALL ids + recording id.
6. Products PR merged to main; Netlify deploy green; `/life-manager` 200 live on aniccaai.com.
7. `~/anicca/skills/life/call.js` pushed to the anicca OSS repo main.

## §5 Non-goals / boundaries (collision rule)

- Do NOT edit shared files (install.sh / landing nav / skills/registry.json). Only ADD new files and
  replace the body of the reserved `app/life-manager/page.tsx`.
- Twilio path stays wired (default for non-+81); Telnyx is added, not a replacement.
- No new npm deps beyond `ws` (already used by the bridge) — Telnyx is plain `fetch` + the same `ws`.
