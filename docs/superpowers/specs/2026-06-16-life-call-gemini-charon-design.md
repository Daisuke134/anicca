# 2026-06-16 — life-call (B-call): Gemini Charon bidirectional phone bridge — design

> Subsystem **life-call** (track B) of the spec27 launch workflow. Builds **B-call**:
> Anicca calls Dais's real number 15 min before each calendar event and speaks
> two-way using **Gemini Live (voice = Charon, male)** bridged over **Twilio Media
> Streams**. Mirrors the telemetry pipeline template (spec/plan → TDD → PR → main → live).

## Dev environment
| key | value |
|---|---|
| worktree | `.claude/worktrees/wf_ce4a22b3-607-8` |
| branch | `feature/life-call-gemini-charon` (off `main`) |
| files I OWN (new only) | `apps/landing/netlify/functions/_lib/call-logic.js` + `__tests__/call-logic.test.js`; `~/anicca/skills/life/call/call.js`; my one-line registry slot flip (`life/call` only) |
| files I MUST NOT edit | `install.sh`, landing nav (`components/site/LaunchNav.tsx`), `app/life-manager/page.tsx` (travel builder's reserved body), `app/me/*` (earn builder's), any other registry slot |

## §1 Goal & success criterion
- **Goal**: a deterministic, TDD-covered bridge so one outbound Twilio call carries
  two-way audio between the human (μ-law 8 kHz PSTN) and Gemini Live (PCM 16 kHz in /
  24 kHz out, voice Charon), narrating "next event, leave-by time, directions" and
  answering follow-ups.
- **Launch gate for B-call (spec27 §2 / spec26 §0)**: a real outbound call to
  `+818046270314` connects, Charon speaks the event briefing, Dais can reply, the
  verifier (separate context) confirms by recording. **fake/mock = FAIL** (HARD 0.24/0.31).
  The verifier owns the real-dial E2E; this builder ships the deterministic core + skill so
  the dial is a single `node call.js --to <num> --event <json>` away.

## §2 Architecture — what is pure (TDD) vs what is I/O
The hard, bug-prone part is the **audio transcoding** + **wire-message shapes**. Those are
pure functions with zero I/O → unit-tested with `node:test` (same runner as telemetry/travel).
The websocket bridge + Twilio REST dial are thin I/O wrappers in the skill entrypoint.

```
 PSTN (Dais phone)                                   Gemini Live (Charon)
        │  μ-law 8kHz                                        ▲  PCM 24kHz
        ▼                                                    │
 ┌───────────────┐  decode b64 → μ-law→PCM16 → up 8→16k  ┌──────────────┐
 │ Twilio Media  │ ────────────────────────────────────▶ │ realtimeInput│
 │ Streams WS    │                                        │  audio (b64) │
 │ (media frames)│ ◀──────────────────────────────────── │ serverContent│
 └───────────────┘  PCM16→μ-law ← down 24→8k ← decode b64 │  audio (b64) │
        ▲                                                   └──────────────┘
   buildTwilioMediaFrame()                  buildGeminiSetup() / buildGeminiAudioInput()
```

### Pure functions (`call-logic.js`) — the unit under test
| fn | responsibility | source-of-truth |
|---|---|---|
| `muLawDecodeSample(u8)` / `muLawEncodeSample(int16)` | one G.711 μ-law sample ↔ 16-bit PCM | ITU-T G.711 μ-law standard table |
| `muLawBufToPcm16(buf)` / `pcm16BufToMuLaw(buf)` | whole-buffer transcode | wraps the per-sample fns |
| `resamplePcm16(buf, inRate, outRate)` | linear-interp resample (8k↔16k, 24k↔8k, mono LE int16) | nearest/linear resample |
| `twilioMuLawToGeminiPcm16(b64)` | Twilio media payload → Gemini-ready base64 (decode→μ-law→PCM16→up 8→16k→b64) | Twilio media msg + Gemini realtimeInput (ctx7) |
| `geminiPcm24ToTwilioMuLaw(b64)` | Gemini audio out → Twilio-ready base64 (decode→down 24→8k→PCM16→μ-law→b64) | Gemini output 24kHz + Twilio play 8kHz |
| `buildGeminiSetup({model,voiceName,systemInstruction})` | `BidiGenerateContentSetup` (Charon voice, AUDIO modality) | ctx7 Gemini Live setup + speechConfig |
| `buildGeminiAudioInput(b64Pcm16)` | `realtimeInput.audio` message (mime `audio/pcm;rate=16000`) | ctx7 Gemini realtimeInput |
| `buildTwilioMediaFrame(streamSid, b64MuLaw)` | outbound Twilio `media` frame | Twilio websocket-messages |
| `buildCallPrompt(event)` | system-instruction text Charon speaks ("Next is X at HH:MM, leave now…") | spec27 §2 B-call |
| `buildConnectStreamTwiml(wsUrl)` | `<Response><Connect><Stream url=…/></Connect></Response>` | Twilio Programmable Voice TwiML |

### I/O (`call.js`, NOT unit-tested — exercised by the verifier's real dial)
- `dialOutbound({to, from, twimlUrl})` → Twilio REST `Calls.create` (env `TWILIO_ACCOUNT_SID/AUTH_TOKEN/PHONE_NUMBER`), via `fetch` Basic-auth (no twilio SDK).
- `bridge(twilioWs)` → opens Gemini Live WS (`wss://generativelanguage.googleapis.com/ws/...BidiGenerateContent?key=$GEMINI_API_KEY`),
  sends `buildGeminiSetup`, then per Twilio `media` frame `twilioMuLawToGeminiPcm16` → send;
  per Gemini audio chunk `geminiPcm24ToTwilioMuLaw` → `buildTwilioMediaFrame` → Twilio WS.
- CLI: `node call.js --to <num> --event '<json>'` dials; `node call.js --serve` runs the bridge ws server.

## §3 Config / env (read from `~/.openclaw/.env`, no hardcoded secrets)
| var | use | default |
|---|---|---|
| `GEMINI_API_KEY` | Gemini Live auth | (required) |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | Twilio REST | (required) |
| `TWILIO_PHONE_NUMBER` / `TWILIO_FROM` | caller id | (required) |
| `CALL_TO` | default callee | `+818046270314` (Dais) |
| `GEMINI_LIVE_MODEL` | model id | `gemini-2.0-flash-live-001` |
| `GEMINI_VOICE` | prebuilt voice | `Charon` |
| `CALL_PUBLIC_WS_URL` | public wss the `<Stream>` connects to | (required at serve time) |

## §4 Test matrix (node:test, all MUST pass)
| # | test | asserts |
|---|---|---|
| 1 | μ-law round-trip stable | `muLawEncodeSample(muLawDecodeSample(u))===u` for all 256 byte values |
| 2 | μ-law silence vectors | `0xFF`→0, `0x7F`→0 (G.711 sign split) |
| 3 | buffer transcode length | `muLawBufToPcm16(n)`=2n bytes; `pcm16BufToMuLaw(2n)`=n bytes |
| 4 | resample 8→16k doubles | output sample count ≈ 2× input |
| 5 | resample 24→8k thirds | output sample count ≈ input/3 |
| 6 | `twilioMuLawToGeminiPcm16` 4× growth | μ-law n → PCM16 2n → up2 → 4n bytes pre-b64 |
| 7 | `geminiPcm24ToTwilioMuLaw` ~1/6 | 24k PCM16 → 8k μ-law ≈ 1/6 bytes |
| 8 | `buildGeminiSetup` shape | `.setup.model`, `responseModalities=["AUDIO"]`, `voiceName="Charon"` |
| 9 | `buildGeminiAudioInput` shape | `.realtimeInput.audio.mimeType="audio/pcm;rate=16000"`, data passthrough |
| 10 | `buildTwilioMediaFrame` shape | `.event="media"`, `.streamSid`, `.media.payload` passthrough |
| 11 | `buildCallPrompt` content | contains title + start time + leave cue; null-safe on missing fields |
| 12 | `buildConnectStreamTwiml` | valid TwiML with `<Connect><Stream url="wss://…">`; XML-escapes the url |

**E2E (verifier, separate context, real dial — not this builder's unit run)**:
`node call.js --to +818046270314 --event '{...}'` → phone rings → Charon speaks briefing →
Dais replies → recording confirms. fake = FAIL.

## §5 Landing page
The `/life-manager` page (travel builder's reserved body) already lists B-call with
`status:'coming'`. **Collision rule: I do NOT edit that shared file.** Flipping the
**registry slot** `life/call.status` to `live` is mine (SLOT.md authorizes my own slot only)
and is the canonical machine-readable signal install.sh/dashboard read.

## §6 Self-review
- **No new deps**: call-logic.js uses only Buffer/built-ins; tests use node:test. call.js uses Node-built-in `WebSocket` (Node 22+ global) + Twilio REST via `fetch` — zero install.
- **Collision-safe**: only NEW files + my own registry slot flip. Shared files untouched.
- **Standards-cited**: μ-law per G.711, Gemini msg shapes per ctx7 `/websites/ai_google_dev_gemini-api`, Twilio media frame per ctx7 `/websites/twilio_voice`.
- **No fake run**: unit tests cover the deterministic core; the real dial is the verifier's job (HARD 0.24).
