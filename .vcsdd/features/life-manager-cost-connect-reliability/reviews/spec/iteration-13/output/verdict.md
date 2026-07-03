# Spec review — iteration 13 (round 2 of iteration-12's 6 findings) — FAIL

**Overall: FAIL.** The headline defect is worse than the one this round was supposed to fix.

## The core problem (FIND-001 / FIND-002 / FIND-003)

Iteration-12 correctly caught that the spec's earlier claim ("Gemini Live already works / just keep it")
was false — the real merged code runs a one-way edge-tts clip / compositional cascade, not Gemini Live.

The round-2 rewrite (this spec) does NOT fix that. It replaces one false "current state" narrative with a
**second, independently false** one: it now claims origin/main defaults to a one-way clip via `playWakeClip`
(`server.js:381`) that escalates to Gemini Live via `openGeminiLive` (`server.js:408`), and that Gemini's
`geminiLiveWsUrl/geminiSetupForEvent/routeGeminiMessage/buildGeminiTurn` machinery is "ALREADY wired into
server.js."

None of this exists. A whole-worktree grep for `playWakeClip` and `openGeminiLive` returns **zero hits in
any source file** — those strings appear only inside the spec itself and prior review JSON quoting it. The
real `server.js:355-448` wires `/ws` to a third architecture entirely: `createConversation()` from
`lib/compositional-voice.cjs` (Groq Whisper STT + Groq Llama LLM + edge-tts), whose own header states
"NEVER opens a Gemini Live ws," and `server.js:380-382` says outright: "NO Gemini Live socket is EVER
opened." `server.js:18-21` imports only `routeTelnyxMessage`/`buildTelnyxMediaFrame` from
`lib/call-bridge.cjs` — the actual Gemini-wiring symbols live only inside that file's own CLI-only
`startServer()`, gated by `require.main === module` (`call-bridge.cjs:269`), which never runs when the
service boots via `node server.js`.

C1's "small surgical edit" (call `openGeminiLive()` instead of `playWakeClip()`, delete four cascade
files) is therefore not executable as written — those functions don't exist — and literally following the
delete-list would remove the files `server.js` currently `require()`s to build its ONLY working `/ws`
handler (`server.js:27-28,412-416`), crashing the service at boot. That directly violates C1's own stated
invariant that `/health /telegram /test-call /inbound-email` must keep responding.

## Secondary fabrication (FIND-002)

OQ6 states GROQ_API_KEY is "Now UNUSED on the live path (voice = Gemini Live)." False: `server.js:358-361`
makes GROQ_API_KEY a hard requirement to accept ANY `/ws` connection today — missing key closes the call
outright. Same root cause as FIND-001, independently checkable.

## Route-in-prompt claim is also false (FIND-004)

C1 claims "route INCLUDED via `geminiSetupForEvent`." `geminiSetupForEvent(event,urgency,lang,name,model)`
(`call-bridge.cjs:131-137`) calls `buildCallPrompt(event,urgency,lang,name)` (`call-logic.js:378`) — no
route/duration parameter exists in that signature at all, regardless of which voice system is live.

## RED checks are unfalsifiable (FIND-005, FIND-006)

§4 RED check (b) greps for the presence/absence of `openGeminiLive`/`playWakeClip` — symbols that never
existed — so it is vacuously true today and can never meaningfully go RED. Check (e) ("call-logic.js +
call-bridge.cjs unchanged") doesn't assert anything about server.js actually opening a Gemini socket, so an
implementer could satisfy every listed RED check while shipping a build that crashes at boot or silently
never opens `/ws` to anything.

## Edge case bullet is inert (FIND-007)

The new Gemini-drop EDGE/ERROR bullet (closing OLD FIND-005) is textually present but specifies behavior
for a socket that isn't wired anywhere, and conflicts with the real, currently-live GROQ-key hard-close
gate.

## What IS actually fixed (FIND-008, minor)

- OLD FIND-002 (scheduler.js selector): substance correct — `calendarProviderFilter()` is called at both
  sites (actual lines 43 and 281; spec cites 42/280).
- OLD FIND-006 (route cache store): substance correct — in-process `Map()` + 10-min TTL confirmed (actual
  line 14; spec cites 16).

Both are genuine fixes with minor line-citation drift — not blockers on their own, but they lower
confidence that every other citation in this document (most consequentially C1's) was freshly re-verified
against this disk rather than carried forward or invented.

## Dimension verdicts

| Dimension | Verdict | Findings |
|---|---|---|
| spec_fidelity | FAIL | FIND-001, FIND-002, FIND-004, FIND-008 |
| edge_case_coverage | FAIL | FIND-007 |
| implementation_correctness | FAIL | FIND-002, FIND-003, FIND-004 |
| structural_integrity | FAIL | FIND-003 |
| verification_readiness | FAIL | FIND-005, FIND-006 |

## Prior-findings resolution map

| ID | Status |
|---|---|
| FIND-001 (old) | **NOT RESOLVED** — replaced by a new fabrication |
| FIND-002 (old) | RESOLVED in substance (minor line drift) |
| FIND-003 (old) | **NOT RESOLVED** — same defect as FIND-001 (old), renamed |
| FIND-004 (old) | **NOT RESOLVED** — new RED check is weaker (checks fictional symbols) |
| FIND-005 (old) | Partially resolved — text added, but inert/unverifiable |
| FIND-006 (old) | RESOLVED in substance (minor line drift) |
