# VCSDD Adversary Verdict — life-manager-cost-connect-reliability, spec iteration-3, review round iteration-15

- **Reviewer**: vcsdd-adversary (fresh context, disk-only)
- **Spec reviewed**: `.vcsdd/features/life-manager-cost-connect-reliability/specs/behavioral-spec.md` (frontmatter says "iteration 3", round 4)
- **Timestamp**: 2026-07-04
- **overallVerdict**: **FAIL**

## Reconciliation check (mandatory pre-check)

CONFIRMED CLEAN AND ACCURATE. `apps/life-call/server.js` still shows the same simple `playWakeClip`(390)/`openGeminiLive`(409) pair as the DEFAULT/escalation split described in the spec — not any compositional-cascade. `compositional-voice.cjs`, `compositional-live.cjs`, `voice-turn.cjs` remain absent (Glob = 0 matches). Proceeding with full review.

## Dimension verdicts

| Dimension | Verdict | Findings |
|---|---|---|
| Spec Fidelity | **PASS** | none |
| Edge Case Coverage | **FAIL** | FIND-005 |
| Implementation Correctness | **FAIL** | FIND-003 |
| Structural Integrity | **FAIL** | FIND-001, FIND-002 |
| Verification Readiness | **FAIL** | FIND-004 |

## Round-3 (iteration-14) findings — explicitly re-verified against disk

| Prior finding | Status this round | Evidence |
|---|---|---|
| FIND-001 (geminiLiveWsUrl/buildGeminiTurn misattributed to call-bridge.cjs) | **RESOLVED** | `server.js:24-28` confirmed: these 3 symbols come from `./lib/call-logic.js`; spec:27,58 now cite `call-logic.js` correctly. |
| FIND-002 (voice-cheap.js falsely claimed "already gone") | **RESOLVED (narrowly)** | `server.js:29,391,430,444` confirmed LIVE exactly as now cited; C1 step 3 (spec:62) now lists `voice-cheap.js` + `voice-cheap.test.js` on the delete-list. **BUT** the identical defect class reappears one file over — see FIND-001 below (`voice-synth.test.js` now the orphan). |
| FIND-003 (barge-in absent, falsely called "existing behavior") | **PARTIALLY RESOLVED** | `call-bridge.cjs:109-124` + 0-hit grep for `interrupted`/`"clear"` confirmed; spec now honestly frames barge-in as newly-wired (Goal-1 line 43, C1 "OUT" line 65: "Barge-in is NEWLY WIRED here (step 2), NOT pre-existing"). **BUT** the wiring instruction itself is defective — see FIND-003 below. |
| FIND-004 (§4 RED omits any barge-in test) | **RESOLVED (structurally)** | §4 item (c) now specifies a RED-before/GREEN-after unit test feeding `{serverContent:{interrupted:true}}`. **BUT** the assertion it specifies is partly untestable — see FIND-004 below. |
| FIND-005 (RED item (c)'s file-list blind spot) | **RESOLVED for voice-cheap.js, RECURRED for voice-synth.test.js** | §4 item (d)'s grep list now includes `voice-cheap.js`/`voice-cheap.test.js` but still omits `voice-synth.test.js`. Same blind spot, different file. |

## New findings this round

### FIND-001 — structural_integrity / spec_gap — `voice-synth.test.js` omitted from C1's delete-list (HIGH)
`apps/life-call/lib/voice-synth.test.js` exists and `require("./voice-synth.cjs")` directly. C1 step 3 (spec:62) lists `voice-cheap.js` + `voice-cheap.test.js` + `voice-synth.cjs` for deletion but never mentions `voice-synth.test.js`. Post-C1, this file will `require` a module that no longer exists — a **hard crash** in the test suite (`Cannot find module './voice-synth.cjs'`), not merely dead code. This is the same defect class as round-3's FIND-002/FIND-005, recurring on a sibling file.

### FIND-002 — structural_integrity / spec_gap — `nixpacks.toml`'s ffmpeg/edge-tts build deps never addressed (MEDIUM)
`apps/life-call/nixpacks.toml:1-7` installs `ffmpeg` + `python313Packages.edge-tts` with a comment explicitly tied to `synthWakeClip`/the one-way clip. C1's delete-list and §4 never mention `nixpacks.toml`. After the flip this becomes dead build weight with a now-false comment, and nothing in the spec catches it.

### FIND-003 — implementation_correctness / requirement_mismatch — "stop the local outbound frame loop" describes a mechanism that won't exist post-flip (CRITICAL)
C1 step 2 requires, on `interrupted`: "(i) send Telnyx `{event:"clear"}`... and (ii) stop the local outbound frame loop." The only actual paced/loop construct in `server.js` is `playWakeClip`'s `for (const f of frames) {...setTimeout(20)}` loop (lines 394-399) — which C1 step 3 **deletes**. The Gemini-Live path that becomes the default (`openGeminiLive` → `gemini.on("message")` → `routeGeminiMessage`) sends each audio chunk synchronously as it arrives from Gemini's websocket message stream; there is no buffered/interval-driven send queue to "stop." Action (i) is well-defined; action (ii) has no referent in the post-flip architecture, forcing a builder to either invent unscoped new buffering machinery or silently no-op half the spec's own requirement.

### FIND-004 — verification_readiness / verification_tool_mismatch — §4 RED inherits both gaps above (HIGH)
RED item (c) asserts the barge-in test must prove it "stops the outbound loop" — untestable per FIND-003. RED item (d)'s grep file-list is copy-identical to C1's (incomplete, per FIND-001) delete-list, so it also never catches the surviving `voice-synth.test.js`.

### FIND-005 — edge_case_coverage / test_coverage — Gemini socket drop/reconnect logic has zero test coverage (MEDIUM)
C1's own EDGE/ERROR clause (spec:66) commits to "if it drops before any audio, attempt ONE reconnect, else end the call cleanly." None of §4 RED items (a)-(f) test any part of this. A builder could ship this entirely unimplemented and every listed automated check would still pass.

## Summary for the Builder
Round-3's five findings are NOT cleanly closed — three of five were resolved narrowly on the *exact* file/claim originally cited, but the same underlying process gap (incomplete "what must be deleted/tested" enumeration; wiring instructions copied from the wrong code path) reproduced itself in new places this round:
1. Add `voice-synth.test.js` to C1's delete-list and to §4 RED item (d)'s grep list (this one is urgent — as written it will crash the test suite, not just linger as dead code).
2. Add `nixpacks.toml`'s `ffmpeg`/`edge-tts` Nix packages to the cleanup scope (or explicitly justify keeping them).
3. Rewrite C1 step 2's barge-in instruction: drop or redefine "stop the local outbound frame loop" so it maps onto the ACTUAL post-flip code path (there is no loop to stop in `routeGeminiMessage`'s synchronous per-message forwarding) — likely the real requirement is just "do not forward any further audio chunks belonging to the interrupted turn," which needs its own concrete mechanism (e.g., a `state.interruptedAt` flag checked before each `providerSend`), not a reference to a construct that's being deleted.
4. Update §4 RED item (c) to assert only what is actually implementable, and widen item (d)'s file list.
5. Add a RED/GREEN test for the "reconnect once if dropped before any audio" edge case, or explicitly demote it out of C1's committed behavior if it is not going to be tested.
