# VCSDD Adversary — Spec Review, iteration-12
Feature: `life-manager-cost-connect-reliability` — behavioral-spec.md iter-3 (voice REVERSAL: keep Gemini Live, shelve Pipecat/Kokoro)

## Overall verdict: FAIL

| Dimension | Verdict | Findings |
|---|---|---|
| Spec Fidelity | FAIL | FIND-001, FIND-002 |
| Edge Case Coverage | FAIL | FIND-005 |
| Implementation Correctness | FAIL | FIND-003, FIND-006 |
| Structural Integrity | FAIL | FIND-002 |
| Verification Readiness | FAIL | FIND-004 |

## Top findings

**FIND-001 (blocker, spec_fidelity)** — "Gemini Live already works / KEPT / current stack" contradicts the actual wired production entrypoint.
`specs/behavioral-spec.md:27,43,58` assert Gemini Live is TODAY's live path. `apps/life-call/server.js` (the sole entrypoint per `railway.toml:5` + `package.json:6-8`) wires `/ws` to `compositional-voice.cjs`'s `createConversation` (server.js:26-27,412) and literally says "NO Gemini Live socket is EVER opened" (server.js:381) / "NEVER open Gemini Live" (server.js:400). This feature's own `execution-notes.md:50-53` confirms the merged-to-main prod call is a **one-way** edge-tts clip, not Gemini Live. C1 is materially harder than framed — real re-wiring, not a pure deletion.

**FIND-002 (major, spec_fidelity + structural_integrity)** — C4's MIGRATION bullet (`specs/behavioral-spec.md:85`) claims `scheduler.js:42,280` still hardcode `eq.composio_gcal`. On disk both sites already call the shared `calendarProviderFilter()` (`scheduler.js:12,43,281`), and `apps/life-call/lib/user-selector.js:1-14` already implements the widened filter — its own header comment says this exact C4 fix is done. The spec's own governance line (`specs/behavioral-spec.md:8`, "re-verify against main before carrying a fact forward") wasn't applied here.

**FIND-003 (blocker, impl_correctness)** — C1 ("restore the Gemini Live /ws bridge", `specs/behavioral-spec.md:60-61`) never names the target file. `apps/life-call/lib/call-bridge.cjs` already contains a full, standalone Gemini Live bridge but is not required by `server.js` and is not the Railway entrypoint (`railway.toml:5`, `package.json:6-8` = `server.js` only). No merge strategy is specified, risking either duplicated logic or a broken merge that drops `server.js`'s other endpoints (`/telegram`, `/test-call`, inbound-reply).

**FIND-004 (major, verification_readiness)** — §4 RED check (c) "the Gemini Live path is intact (call-logic.js unchanged)" (`specs/behavioral-spec.md:106`) proves nothing: `call-logic.js` is already unchanged/dormant today, so it stays "unchanged" whether or not the cleanup actually rewires `server.js` to call it. A broken restore (files deleted, `/ws` left unwired) would still pass this RED check.

**FIND-005 (major, edge_case_coverage)** — C1 has no EDGE/ERROR bullet (unlike C2 at line 74) for a Gemini Live connect failure or mid-call drop. Separately, the DTMF bullet ("keep whatever the origin/main Gemini Live path already does", line 66) is unverifiable: the currently-wired cascade ignores DTMF outright (`server.js:436-437`) and the dormant bridge only classifies the event (`call-bridge.cjs:71,94`), with no forwarding logic — there is no provable "already does X" to keep.

**FIND-006 (major, impl_correctness)** — C3 and `route-cache.js`'s own comment (`route-cache.js:3-4`) claim production is Supabase-backed (`lm_route_cache`); the actual wired caller `apps/life-call/lib/travel.js:14` uses a volatile in-process `Map()`. Cache does not survive restarts/redeploys or scale across dynos — undermines the §1/Goal-3 "already fixed" cost claim.

## Files reviewed
- `specs/behavioral-spec.md` (full)
- `apps/life-call/server.js`, `apps/life-call/lib/call-logic.js`, `apps/life-call/lib/call-bridge.cjs`
- `apps/life-call/scheduler.js`, `apps/life-call/lib/user-selector.js`
- `apps/life-call/lib/ask.js`, `apps/life-call/lib/route-cache.js`, `apps/life-call/lib/travel.js`
- `apps/life-call/railway.toml`, `apps/life-call/package.json`
- `.vcsdd/features/life-manager-cost-connect-reliability/execution-notes.md`
- `.vcsdd/features/life-manager-cost-connect-reliability/reviews/spec/iteration-11/output/verdict.json` (prior-round context)
- `.vcsdd/features/life-manager-cost-connect-reliability/reviews/impl/iteration-5/output/findings/FIND-201.json`, `FIND-202.json` (corroborating C1 "never worked" characterization)

## Structural note (not a finding, positive evidence)
The iter-2→iter-3 REVERSAL text itself is internally coherent: whole-document grep for `live_ws_opened=0`, `SUPERSEDES`, `GEMINI LIVE FULLY REMOVED` = 0 hits; every Pipecat/Kokoro/Groq/Silero/SmartTurn/edge-tts mention (lines 4, 11, 37, 53, 58, 110, 115, 116) is correctly framed as shelved/historical, not live. The FAILs above are about disk-fact accuracy and underspecification of the cleanup mechanics, not textual leakage from iteration-2.
