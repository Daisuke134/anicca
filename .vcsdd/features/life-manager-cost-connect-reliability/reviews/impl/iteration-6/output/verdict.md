# C1 Implementation Review — iteration-6 — OVERALL: FAIL

Reviewed commit 090b2109 (branch feature/lm-cost-connect-reliability), C1 (Voice: Gemini Live default +
barge-in) against `specs/behavioral-spec.md` §C1 + §4. Fresh context, disk-only, no builder context.

**Reviewer execution capability disclosure**: this session had NO Bash tool available. `node --test` /
`node --check` were NOT executed by me. All findings below are from static disk review (Read/Grep/Glob)
only. I did not find any evidence-log artifact on disk proving a green test run either (see FIND-006) —
so no party's "tests pass" claim can be confirmed from disk alone right now.

## Dimension verdicts

| Dimension | Verdict | Findings |
|---|---|---|
| Spec Fidelity | FAIL | FIND-005 |
| Edge Case Coverage | FAIL | FIND-002, FIND-003 |
| Implementation Correctness | FAIL | FIND-001 |
| Structural Integrity | FAIL | FIND-004 |
| Verification Readiness | FAIL | FIND-002, FIND-006 |

## What's correct (positive evidence, not a summary judgment)

- `server.js:442` — `openGeminiLive()` fires on the Telnyx `start` frame; this IS the default now (no
  `playWakeClip` anywhere). `liveWsOpened` increments on every `openGeminiLive()` call (server.js:396).
- `lib/call-bridge.cjs:109-121` — `routeGeminiMessage` checks `msg.serverContent.interrupted` BEFORE
  `parseGeminiAudio`, so an interrupted message cannot also forward an audio frame. Returns
  `{kind:"interrupted", frames:0}` correctly.
- `server.js:408` — `carrierSend({event:"clear"})` targets the CARRIER (Telnyx) socket, matching the
  Telnyx bidirectional-streaming protocol (`{"event":"clear"}` on the carrier ws, per
  `~/.claude/rules/building-voice-agents.md`), not the Gemini socket.
- Dead code cleanup is real and complete: `playWakeClip`/`synthWakeClip`/`buildWakeLine`/`planVoice` and
  the files `voice-cheap.{js,test.js}`, `voice-synth.cjs(.test.js)`, `compositional-{voice,live}.cjs`,
  `voice-turn.cjs` — 0 grep hits repo-wide in `apps/life-call`. `nixpacks.toml` no longer lists
  `edge-tts`/`ffmpeg` (reverted to `nixPkgs=["..."]`).
- Forbidden-to-touch surfaces look untouched in their CURRENT state: `/health`, `/telegram`,
  `/test-call`, `/inbound-email`, `/api/inngest`, `/api/stripe/webhook` all still registered
  (server.js:178-348); `ctxFromReq` (150), `MAX_CONCURRENT` (141,369), `startRecording` (437) all present
  and unchanged in shape; `apps/life-voice/` still exists on disk (shelved, not deleted, per spec).
- `lib/call-bridge.test.js` barge-in unit test is NOT vacuous: it asserts BOTH `{kind:"interrupted"}` AND
  `sent.length === 0` (no frame forwarded).

## Blocking findings

**FIND-001 (implementation_correctness, CRITICAL)** — `server.js:426-427` registers BOTH `gemini.on("error", ...)`
and `gemini.on("close", ...)` calling the SAME `onGeminiEnd`. A `ws` client emits `error` THEN `close` for
the SAME single connection failure (standard WebSocket-client semantics), so `onGeminiEnd` fires TWICE per
real failure. Traced sequence: event 1 (`error`) takes the reconnect branch (`geminiReconnects` 0→1, opens
a new Gemini socket asynchronously); event 2 (`close`, same underlying failure, fires immediately after)
sees `geminiReconnects < 1` now FALSE and calls `carrierWs.close()` — ending the call before the freshly
opened reconnect socket has any chance to complete its handshake or deliver audio. The C1 "attempt ONE
reconnect" safety net is therefore a no-op: a single real Gemini drop reliably hangs up the caller on the
first failure while silently burning and orphaning a second Gemini Live session.

**FIND-002 (edge_case_coverage + verification_readiness, CRITICAL)** — Spec §4 RED item (e) explicitly
requires a test that "simulate[s] the gemini ws emitting error/close before any audio → assert exactly ONE
reconnect attempt, then (on a second failure) a clean carrier close." No such test exists anywhere in the
repo. The entire reconnect state machine is inline inside `wss.on("connection", ...)` in `server.js` and is
not exported (`module.exports` at `server.js:473` exposes only `inngestServeAllowed`, `testCallAllowed`,
`TEST_CALL_COOLDOWN_MS`, `TEST_CALL_DAILY_MAX`). This is precisely why FIND-001 exists undetected.

**FIND-003 (edge_case_coverage, HIGH)** — Spec §4 RED item (c)'s second assertion — "(in a server-handler
test) that a `{"event":"clear"}` object is carrierSent" — is missing. Only the pure
`routeGeminiMessage` → `{kind:"interrupted"}` half is tested (`lib/call-bridge.test.js`). The actual wiring
`if (r.kind === "interrupted") carrierSend({event:"clear"})` (`server.js:408`) has zero test coverage; it
could regress silently.

**FIND-004 (structural_integrity, MEDIUM)** — The reconnect state machine (`server.js:356-455`) is embedded
inline in the network-I/O closure rather than extracted as a testable pure function, inconsistent with this
same feature's own established pattern (`routeTelnyxMessage`/`routeGeminiMessage` were deliberately pulled
into `lib/call-bridge.cjs` "testable with a fake socket" — `call-bridge.cjs:36`). This structural choice is
the direct enabler of FIND-001 + FIND-002.

**FIND-005 (spec_fidelity, HIGH)** — C1's invariant "no silent-call regression" is undercut by FIND-001:
since the one-way clip fallback is now fully deleted, a transient Gemini connect failure (that the old
one-retry design was meant to survive) now reliably ends the call outright — a regression relative to the
stated reliability goal, not merely an untested edge case.

**FIND-006 (verification_readiness, MEDIUM)** — No `evidence/` artifact exists anywhere under
`apps/life-call` or the feature directory proving `node --test` was actually run green after the deletes
(spec §4 RED item a). Per this project's own HARD RULE 0.12/0.31 convention, a green-run log should be
persisted before a sprint is claimed complete; none is present, and this reviewer had no Bash tool to
produce one independently.

## `node --test` result

**NOT RUN by this reviewer** — no Bash/execution tool was available in this review session. I did not
fabricate a pass count. Static grep confirms no orphaned `require()` of any deleted file (necessary but not
sufficient for a green run). This gap itself is folded into FIND-006.

## Ready for real-call E2E?

**NO.** FIND-001 is a real, high-confidence logic bug in the exact safety-net path the spec calls out by
name (pre-audio Gemini drop → one reconnect). Until it is fixed AND a regression test per spec §4 RED item
(e) is added (and, separately, item (c)'s server-handler clear-send assertion), a live E2E call that
happens to hit a transient Gemini connect hiccup will silently hang up instead of recovering — this is
exactly the failure mode Goal 1 / C1 was written to prevent. Fix → add the RED-e and RED-c(2) tests → re-run
`node --test` with a persisted evidence log → re-review, before any live-call E2E is attempted.
