# VCSDD Adversary Verdict — life-manager-cost-connect-reliability, spec review round 5 (iteration-3 doc, "iteration-16" review dir)

**Reviewer**: fresh-context adversary, disk-only, zero builder context
**Reviewed**: `.vcsdd/features/life-manager-cost-connect-reliability/specs/behavioral-spec.md` (iteration-3, dated 2026-07-04)
**Disk read**: `apps/life-call/server.js`, `apps/life-call/lib/call-bridge.cjs`, `apps/life-call/lib/voice-synth.test.js`, `apps/life-call/lib/voice-synth.cjs`, `apps/life-call/lib/voice-cheap.js`, `apps/life-call/nixpacks.toml`, `apps/life-call/lib/call-logic.js` (`buildCallPrompt`), `apps/life-call/scheduler.js`, `apps/life-call/lib/ask.js`, `apps/life-call/lib/travel.js`

## Overall verdict: **PASS — CONVERGED, ready to implement**

## Round-4 finding re-verification (all against live disk)

| Finding | Spec fix location | Disk verification | Status |
|---|---|---|---|
| r4-FIND-001 (voice-synth.test.js not on delete-list) | `specs/behavioral-spec.md:62` C1 step 3: "...voice-synth.cjs, AND voice-synth.test.js (FIND-001 r4: voice-synth.test.js:7 `require("./voice-synth.cjs")` → leaving it after deleting voice-synth.cjs HARD-CRASHES `node --test`)" | `apps/life-call/lib/voice-synth.test.js:7` — confirmed `const { chunkMuLawToFrames, voiceForLang } = require("./voice-synth.cjs");` — file exists on disk today, requires voice-synth.cjs exactly as spec states | **FIXED** — delete-list now includes it, §4(d) grep also lists it |
| r4-FIND-002 (nixpacks.toml ffmpeg/edge-tts not cleaned) | `specs/behavioral-spec.md:63` C1 step 4: "CLEAN nixpacks (FIND-002 r4): ... revert `nixPkgs` to `["..."]`" + §4 RED (f) | `apps/life-call/nixpacks.toml:7` — confirmed `nixPkgs = ["...", "ffmpeg", "python313Packages.edge-tts"]` exists today exactly as spec describes | **FIXED** — cleanup step + RED grep both present |
| r4-FIND-003 (Gemini path has no paced local loop; barge-in must be clear-only) | `specs/behavioral-spec.md:61` C1 step 2 | `apps/life-call/lib/call-bridge.cjs:109-124` `routeGeminiMessage` — confirmed: handles only `setupComplete` + `parseGeminiAudio` chunks, each frame forwarded immediately via `providerSend(buildFrame(...))` in a `for` loop with **no setTimeout/pacing** — there genuinely is nothing local to "stop". Spec's step 2 language now says exactly this ("there is NO paced local loop, so there is nothing local to 'stop'") and specifies the mechanism as `routeGeminiMessage` returning `{kind:"interrupted"}` → `server.js` calling `carrierSend({event:"clear"})`, with explicit "NO assertion about 'stopping a loop'" in §4(c) | **FIXED** — matches disk exactly, mechanism is accurately scoped |
| r4-FIND-004/005 (§4 RED must assert clear-only, include voice-synth.test.js in delete grep, cover Gemini-drop reconnect) | `specs/behavioral-spec.md:111` §4 RED (c)(d)(e) | grep for `interrupted`/`"clear"` across `apps/life-call/**` → **0 hits**, confirming barge-in is genuinely absent today and the RED test in §4(c) will go RED as claimed. §4(d) delete-grep list includes `voice-synth.test.js`. §4(e) specifies the Gemini-drop reconnect edge (ONE reconnect, then clean close, no throw/silence/clip-fallback) | **FIXED** — all three sub-items present and consistent with disk |

## Additional disk cross-checks (spot-verification beyond the r4 scope, since this is the final round)

- `buildCallPrompt` (`apps/life-call/lib/call-logic.js:378`) confirmed to take `(event, urgency, lang, name)` — **no route argument**, matching spec's claim that the route informs call timing, not the spoken prompt (`specs/behavioral-spec.md:65`).
- `calendarProviderFilter()` confirmed used at **both** `scheduler.js:43` and `scheduler.js:281` (spec C4 claim, `specs/behavioral-spec.md:90`) — selector migration is accurate.
- `ask.js:8` confirmed verbatim "We NEVER read or send from the user's Gmail" comment — spec's Gmail-scope claim (`specs/behavioral-spec.md:89`) is accurate.
- `travel.js:14` confirmed `makeRouteCache({ store: new Map(), ttlMs: 10 * 60_000 })` — spec's C3 as-built claim (`specs/behavioral-spec.md:82`) is accurate.
- `voice-cheap.js`, `voice-cheap.test.js`, `voice-synth.cjs`, `voice-synth.test.js` all confirmed present on disk today (glob match); `compositional-voice.cjs`, `compositional-live.cjs`, `voice-turn.cjs` confirmed **absent** (glob no-match) — spec's claim that the compositional-cascade files were "already removed when the worktree was reconciled to origin/main" (`specs/behavioral-spec.md:62`) is accurate. This means the C1 delete-list is neither over- nor under-inclusive relative to current disk state.

## Dimension verdicts

### Spec Fidelity — PASS
Every disk-fact claim checked (C1's current-state description, C4 selector sites, C3 cache implementation, Gmail-scope claim, `buildCallPrompt` signature) matches the live repository exactly at the cited file:line. No remaining fabricated or stale disk-fact citations found in the sections re-reviewed this round.

### Edge Cases — PASS
C1's EDGE/ERROR block (`specs/behavioral-spec.md:67`) now covers: missing `GEMINI_API_KEY` (existing), mid-call socket `error`/`close` before any audio → ONE reconnect then clean close (new, §4(e) concretized this round), `MAX_CONCURRENT` reject, unauthenticated `/ws` reject, and barge-in via `{event:"clear"}`. The r4 gap (no reconnect-edge test) is now closed by §4(e)'s concrete assertion.

### Implementation Correctness — PASS
The barge-in mechanism specified (`routeGeminiMessage` returns `{kind:"interrupted"}` on `msg.serverContent.interrupted`; `server.js` handler calls `carrierSend({event:"clear"})`) is directly implementable against the existing `routeGeminiMessage` signature (`call-bridge.cjs:109`) without restructuring — it is a straightforward early-return branch plus one new `if (r.kind === "interrupted")` check in `server.js`'s gemini `message` handler (mirroring the existing `if (r.kind === "setupComplete")` pattern at `server.js:419`). No invented API surface; `serverContent.interrupted` matches the documented Gemini Live wire format referenced by the user's own voice-agent rules file.

### Structural Integrity — PASS
C1 explicitly scopes the change to `server.js` + one new branch in `call-bridge.cjs`'s existing `routeGeminiMessage` ("Do NOT extract a new file", `specs/behavioral-spec.md:64`), consistent with the file's existing pure-router/thin-shell split. The delete-list is exact and matches what's actually dead-after-flip on disk (verified above) — no leftover requires, no orphaned test files.

### Verification Readiness — PASS
§4 RED (a)-(h) gives eight concrete, disk-checkable assertions (boot, default-branch grep, barge-in unit test, delete-grep, Gemini-drop reconnect test, nixpacks grep, route-preservation grep, call-logic-unchanged grep) covering every clause of C1's INVARIANT. Goal-1's live-conversation and interrupt-and-be-heard conditions are explicitly deferred to the NO-MOCK E2E step (real call, Dais converses + interrupts) rather than falsely claimed as unit-testable — this is the correct split (unit-provable mechanism vs. real-world-provable UX), not a gap.

## Blocking findings
None. All four round-4 findings are resolved and independently re-verified against the current worktree disk state, not merely re-stated in the spec.

## Convergence
**CONVERGED.** C1 is implementable exactly as written: exact files (`server.js`, `lib/call-bridge.cjs`), exact barge-in mechanism (`{kind:"interrupted"}` → `{event:"clear"}`, no phantom "stop the loop"), exact delete-list (4 files + 2 already-gone files correctly not re-listed), exact nixpacks reversion. Every Goal-1 proof condition maps to either a concrete §4 RED check or the NO-MOCK E2E step. No cosmetic-vs-blocking ambiguity was found — the round-4 findings were genuine implementability blockers and are now closed against disk, not just against prose.
