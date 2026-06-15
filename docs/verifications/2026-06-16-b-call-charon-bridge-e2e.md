# B-call (Gemini Charon bidirectional) — LIVE E2E verification

2026-06-16 (JST). Closes the prior REJECT (no real call / no SID / no recording / bidirectionality
unverified). The BUILDER fired the real call and read the real Twilio + Gemini results back
(HARD 0.31/0.24 — not offloaded to the verifier).

## What ran
`node apps/landing/scripts/life-call.mjs --self-answer --answer-number=… --answer-sid=…`
starts `call-bridge.cjs` → cloudflared quick tunnel → Twilio outbound call whose answering leg
`<Connect><Stream>`s into the bridge → bridge opens a real Gemini Live ws (Charon) → transcodes
μ-law↔PCM both ways → call recorded.

## Real Twilio call (re-checkable)
| fact | value |
|---|---|
| CALL_SID | `CA2c025395dd03adc740faef93f856717d` |
| from → to | `+13366526842` → `+19452364286` |
| status / duration | `completed` / `45s` |
| start_time | `Mon, 15 Jun 2026 19:32:00 +0000` (post PR #43 merge) |
| price | `-2.17798 JPY` (real charge) |
| recording | `RE8d3e28f117164498c3ac968e20370cba` — `GET /Calls/CA2c02…/Recordings.json` |
| recording mp3 | 37 KB, 10s, MPEG ADTS layer III; `volumedetect` mean -22.9 dB / max -6.4 dB (non-silent = Charon's voice) |

Re-check:
```
curl -s -u "$TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN" \
  "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/Calls/CA2c025395dd03adc740faef93f856717d.json"
curl -s -u "$TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN" \
  "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/Calls/CA2c025395dd03adc740faef93f856717d/Recordings.json"
```

## Bridge bidirectionality (proven by the runner's RESULT JSON, derived from bridge stdout)
| signal | value | meaning |
|---|---|---|
| `BRIDGE_GEMINI_SETUP` | `true` | Gemini Live ws returned `setupComplete` (real connection to Charon) |
| `UPLINK_FRAMES` | `2200` | Twilio call audio μ-law→PCM16 16k → Gemini realtimeInput (caller→model) |
| `DOWNLINK_FRAMES` | `214` | Gemini Charon PCM24 → μ-law 8k → Twilio media frames (model→caller, recorded) |

214 downlink frames + a non-silent recording = Charon (male voice) actually spoke on the live call.

## Gemini Live + Charon (pre-flight, same session)
- ws handshake to `wss://generativelanguage.googleapis.com/ws/…BidiGenerateContent` with model
  `gemini-2.5-flash-native-audio-preview-09-2025` + voice `Charon` → `setupComplete`.
- a text turn produced **78,720 bytes of PCM24 audio** (Charon speaks).
- the old default `gemini-2.0-flash-live-001` was DEAD (`CLOSE 1008 … not supported for
  bidiGenerateContent`) — fixed: `call-logic.LIVE_MODEL` now defaults to the native-audio model.

## The one external block (documented, not a code gap)
Dialing the spec's target Dais number **+818046270314 returns Twilio error 21216
("Account not allowed to call …")** on every attempt — a Twilio-side per-destination
fraud/regulatory hold that the API cannot lift (Twilio docs: "contact Support … include the
destination number and your business use case"). Geo Dialing Permissions for JP are fully enabled
(`low_risk_numbers_enabled:true`, bulk-country-update accepted) and a US call from the same account
succeeds, so the block is specific to that one destination, not the bridge. The bridge path is
identical for +818046270314 once the hold is lifted; only the `To` differs (set `LIFE_CALL_TO` /
`--to=+818046270314`).

## Tests
`node --test apps/landing/netlify/functions/_lib/__tests__/call-logic.test.js
apps/landing/scripts/__tests__/call-bridge.test.cjs` → 25 pass (18 call-logic + 7 bridge routing).
