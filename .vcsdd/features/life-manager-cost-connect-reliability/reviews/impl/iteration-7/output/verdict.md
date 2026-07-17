# C1 Implementation Review — iteration-7 (round 2, post FIND-001-critical fix) — OVERALL: FAIL

Reviewed the C1 fix on branch `feature/lm-cost-connect-reliability` (files: `apps/life-call/server.js`,
`apps/life-call/lib/call-bridge.cjs`, `apps/life-call/lib/call-bridge.test.js`) against
`specs/behavioral-spec.md` §C1 + §4, and against iteration-6's blocking finding. Fresh context, disk-only,
no builder context.

**Reviewer execution capability disclosure**: the review brief states "You HAVE a Bash tool — USE IT to run
`node --test`". This session's actual toolset was Read/Write/Edit/Grep/Glob only — **no Bash tool was
provisioned**, despite the instruction. Per this project's own HONESTY RULES (Rule 4: no test/build success
claims without an actual run this session) I am disclosing this rather than fabricating pass/fail counts.
**I did NOT run `node --check` or `node --test` in this session.** All findings below are from careful
static disk review (Read/Grep/Glob) plus a manual hand-trace of the event-ordering logic. This gap is
itself folded into FIND-002.

## Dimension verdicts

| Dimension | Verdict | Findings |
|---|---|---|
| Spec Fidelity | PASS | — |
| Edge Case Coverage | FAIL | FIND-001 |
| Implementation Correctness | PASS | — |
| Structural Integrity | PASS | — |
| Verification Readiness | FAIL | FIND-002 |

## FIND-001 (iteration-6, critical) — genuinely FIXED, verified by hand-trace

`server.js:420-423`:
```js
let ended = false;
const onGeminiEnd = (reason) => {
  if (ended) return;
  ended = true;
  ...
};
gemini.on("error", (e) => onGeminiEnd(`err ${e.message}`));
gemini.on("close", () => onGeminiEnd("closed"));
```
`ended` is declared **inside** `openGeminiLive()` (server.js:396), so **every invocation — including the
recursive reconnect call at server.js:433 — gets its own fresh closure binding**. Traced sequence for the
FIRST real pre-audio failure:
1. `error` fires on socket #1 → `onGeminiEnd('err ...')` → `ended`(#1) false→true → `decideGeminiEnd({gotAudio:false, reconnects:0, carrierOpen:true})` → `"reconnect"` → `geminiReconnects` 0→1, `gemini=null`, `openGeminiLive()` called **recursively and synchronously** → socket #2 created with its **own** fresh `ended`(#2)=false and its own 4 listeners bound directly to the socket #2 instance (via `gemini.on(...)` evaluated at that point, not re-resolved later). Control returns, outer `onGeminiEnd`(#1) hits `return;`.
2. The paired `close` for socket #1 (same underlying failure) fires → its handler closure still references `ended`(#1), which is now `true` → `if (ended) return;` → **no-op**. `carrierWs.close()` is NOT called. This is the exact fix for iteration-6's critical bug.

Verified the other 3 required scenarios by the same trace method:
- **Scenario 2 (2nd pre-audio failure on the reconnect socket)**: socket #2's own `error`/`close` → `ended`(#2) guards double-fire → `decideGeminiEnd({gotAudio:false, reconnects:1, carrierOpen:true})` → `reconnects(1) < maxReconnects(1)` is false → `"close"` → `carrierWs.close()`. **No infinite loop**: `geminiReconnects` is call-scoped (`server.js:388`), never reset mid-call, so exactly one reconnect total is possible regardless of interleaving.
- **Scenario 3 (drop after audio, `gotAudio=true`)**: `decideGeminiEnd` short-circuits on `!gotAudio` being false → always `"close"`, regardless of `reconnects`/`carrierOpen`. Correctly never reconnects post-audio.
- **Scenario 4 (`carrierOpen=false`)**: `"close"` → `carrierWs.close()` on an already-closed socket, caught by the `try/catch` → harmless no-op.

`decideGeminiEnd` (`lib/call-bridge.cjs:149-152`) is pure and matches C1's EDGE/ERROR clause exactly; its
default `maxReconnects=1` matches "attempt ONE reconnect."

## What else is correct (positive evidence)

- Gemini Live confirmed DEFAULT: `server.js:455` `if (!gemini) openGeminiLive();` on the Telnyx `start`
  frame; zero grep hits repo-wide in `apps/life-call` for `playWakeClip`/`synthWakeClip`/`buildWakeLine`/
  `planVoice`/`voice-cheap`/`voice-synth`/`compositional-voice`/`compositional-live`/`voice-turn`.
- Barge-in: `routeGeminiMessage` (`call-bridge.cjs:119-121`) checks `msg.serverContent.interrupted`
  **before** `parseGeminiAudio` (line 122), so an interrupted message can never also forward an audio
  frame. `server.js:410-411` routes the result through the NEW `carrierActionForGeminiKind(r.kind)` pure
  helper and sends via `carrierSend` — the **carrier** (Telnyx) socket, not the Gemini socket. Both
  `carrierActionForGeminiKind` and `decideGeminiEnd` are tested in `lib/call-bridge.test.js` with
  meaningful (non-tautological) assertions: interrupted→`{event:'clear'}`, all other kinds→`null`;
  reconnects=0→reconnect, reconnects=1→close, gotAudio→close, carrier-closed→close (4 distinct cases,
  `call-bridge.test.js:35-44`). This resolves iteration-6 FIND-003 (untested `{event:"clear"}` wiring) —
  the decision half is now pure+tested, the wiring half is a trivial one-line `if (carrierAction)
  carrierSend(carrierAction)`.
- `apps/life-call/nixpacks.toml:5` still `nixPkgs = ["..."]`, no edge-tts/ffmpeg.
- Forbidden surfaces untouched: `/health`, `/telegram`, `/test-call`, `/inbound-email`, `/api/inngest`,
  `/api/stripe/webhook` all registered (`server.js:178-350`); `ctxFromReq` (152), `MAX_CONCURRENT`
  (143,371), `startRecording` (37,448-454) all present and unchanged in shape. `apps/life-voice/**` still
  on disk (shelved). `scheduler.js:12,43,281` still uses `calendarProviderFilter()` at both sites. All
  `require()`s in `server.js` resolve to files that exist (checked every `./lib/*` require against Glob) —
  no orphaned requires from the deleted-clip cleanup.

## Blocking findings

**FIND-001 (edge_case_coverage, HIGH)** — Spec §4 RED item (e) literally requires a test that "simulate[s]
the gemini ws emitting error/close before any audio." The iteration-6 critical bug was a bug in the EVENT
WIRING (the double-fire of `error`+`close` for one failure), not in a decision function — `decideGeminiEnd`
itself was already simple/correct; the bug was that it got invoked twice with a stale `geminiReconnects`
value in between. The fix extracts `decideGeminiEnd` as a pure tested function, which is good practice, but
this does **not** exercise the actual mechanism that caused the bug (the per-invocation `ended` flag /
`openGeminiLive` closure structure) — that code is still 100% inline inside `wss.on('connection', ...)` and
still not exported (`server.js:486` module.exports unchanged from iteration-6: only `inngestServeAllowed`,
`testCallAllowed`, `TEST_CALL_COOLDOWN_MS`, `TEST_CALL_DAILY_MAX`). My hand-trace above shows the fix is
CURRENTLY correct, but there is **zero automated regression protection** for the exact failure mode: a
future edit that hoists `ended` out of `openGeminiLive()`'s scope, or re-registers listeners against a
stale reference, reintroduces the iteration-6 hangup bug with a still-100%-green `node --test`
(`decideGeminiEnd`'s tests are untouched by such a regression). File: `apps/life-call/server.js:396-441`.

**FIND-002 (verification_readiness, MEDIUM)** — Carried over from iteration-6 FIND-006: no persisted
evidence artifact of a green `node --test` run exists anywhere under `apps/life-call/` or the feature
directory (Glob for `**/evidence/**` returns only pre-existing transit fixtures + unrelated research notes).
Compounding this: **this review session had no Bash tool available**, contradicting the review brief, so I
could not independently execute `node --check server.js`, `node --check lib/call-bridge.cjs`, or
`node --test` to confirm a green run either. Neither party's "tests pass" claim is currently confirmable
from disk-available evidence.

## `node --test` result

**NOT RUN by this reviewer** — no Bash tool was available in this session (disclosed above, not fabricated).
Static checks performed instead: every `require()` in `server.js` resolves to an existing file (Grep +
Glob cross-check); zero grep hits for any deleted clip-module name anywhere in `apps/life-call`;
`nixpacks.toml` clean. These are necessary-but-not-sufficient for "tests pass" and do not substitute for an
actual `node --test` transcript.

## Ready for real-call E2E?

**Conditionally — but per VCSDD gate rules, NOT YET.** The specific critical regression from iteration-6
(a transient pre-audio Gemini drop hanging up the call) is, on careful hand-trace, genuinely fixed and I
found no other correctness defect in the reviewed diff — `implementation_correctness` and `spec_fidelity`
both PASS with positive evidence above. However two findings remain open: (FIND-001) the exact bug-causing
mechanism has no regression test, only a proxy pure-function test, so a future edit could silently
reintroduce iteration-6's hangup bug with green CI; (FIND-002) no fresh, persisted `node --test` green-run
evidence exists from either the builder or this reviewer. Per VCSDD's "loop fix→re-review until ALL PASS"
and "no completion claim without fresh evidence" rules, close FIND-001 (add an event-level simulation test,
or export the wiring so it's directly testable) and FIND-002 (produce and persist an actual `node --test`
transcript, from a session that HAS Bash) before attempting the live-call E2E.
