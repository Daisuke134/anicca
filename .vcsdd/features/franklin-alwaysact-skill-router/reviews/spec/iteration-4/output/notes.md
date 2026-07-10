# Non-blocking observations — iteration 4

These are NOT blocking findings (per the anti-leniency rule, listed here only because they are
genuinely minor/deferrable, not because they are being softened). The one genuine defect found this
iteration (FIND-301) is filed separately as a blocking finding.

1. **`index.mjs:175-184`/`index.mjs:183` citation has drifted a few lines against the current main HEAD.**
   The spec's §1 ground-truth bullet on `avoidSlot`'s soft-nudge semantics cites `index.mjs:175-184` for
   the mechanism and `index.mjs:183` for the exact quote `"the agent's choice is never blocked, only the
   enforced pause after ignoring it grows"`. Independently re-read this iteration: `avoidSlot` is declared
   at line 177, and the quoted comment text is actually at line 187 (an escalating-cooldown-streak comment
   block — added by a later, unrelated commit — pushed the quote down ~4 lines within the same code
   region). The CONTENT of the citation is verbatim correct and still trivially locatable in the same
   ~15-line block; only the line number is stale. Every other line-number citation checked this iteration
   (brain.mjs:63/92, prompt.mjs:10-24/139-173/171, context.mjs:26-53, index.mjs:382-416/402-416/440-456/
   450/458-475, sol-trade/run.sh:21-24/28-41/45-48/54-66/68-76/105-158) is pixel-exact against this same
   commit, so this is an isolated transcription slip, not systemic staleness. Not blocking.

2. **`isMarketRiskFree`'s missing-`risk`-field fail-closed behavior is now explicitly documented (REQ-506
   edge case, behavioral-spec.md:313-318) but still has no PROP/acceptance-criterion that literally
   exercises a slot with `risk` field ABSENT (as opposed to explicitly `"capital"`).** PROP-506e/f
   (verification-architecture.md:154-155) test "a mix of risk:'safe'/risk:'capital' members" and "every
   remaining slot is risk:'capital'" respectively — neither's description names an `undefined`/missing-field
   fixture explicitly. The predicate's own definition (`riskTagOf(slot) === 'safe'`) is inherently
   fail-closed for `undefined` regardless of whether a test literally exercises it, so this is a coverage
   gap, not a behavioral gap. Recommend Phase 2a add one explicit fixture entry with no `risk` key to
   PROP-506e's property-test generator. Not blocking (carried over from iteration-3's own non-blocking
   note #1, still unresolved but still non-critical).

3. **FIND-201 is genuinely, verifiably resolved in this revision** — independently re-derived this
   iteration, not merely re-read (see `verdict.json.iteration3FindingsVerifiedResolved` for full citations):
   REQ-504 point 5 introduces `currentOfferedSlots` as the per-attempt local variable; REQ-506 sets it at
   the reroute-schema construction point; REQ-513's EARS/edge-cases/acceptance-criteria all validate against
   `currentOfferedSlots`, never the static `ctx.alwaysActMenu`, for a reroute attempt; the Purity Boundary
   Map, Proof Obligations table (PROP-513b/c/d), Verification Strategy, Phase 5 harness plan, and Changelog
   are all internally consistent with this fix.

4. **Ground-truth spot-check performed independently this iteration** (11 real files fully read, not
   merely re-trusting iteration-3's own notes): `runtime/loop/index.mjs` (full read, 653 lines),
   `runtime/loop/brain.mjs` (full read), `runtime/loop/prompt.mjs` (full read), `runtime/loop/context.mjs`
   (full read), `runtime/loop/earn-slot.mjs` (full read), `runtime/loop/earn-detect.mjs` (full read),
   `runtime/loop/catalog-gate.mjs` (full read), `runtime/loop/parse-tool-call.mjs` (full read),
   `skills/registry.json` (full read, all 21 slot entries), `skills/earn/sol-trade/run.sh` (full read),
   `skills/self/earning-health.py` (full read). All cited line ranges/quotes verified as described in
   `verdict.json.groundTruthSpotChecks`, with the two trivial, non-blocking overshoots noted above (#1, and
   the earning-health.py docstring citation overshooting by 2 lines into surrounding prose).

5. **FIND-301 (this iteration's blocking finding, filed separately) is the third instance of the same
   underlying failure mode this spec pair has now been caught on** (FIND-102: total-call-ceiling wording
   off-by-one; FIND-201: dispatch guard checking the wrong reference array; FIND-301: dispatch guard's own
   branch-selection rule, added to fix FIND-201, fails to unambiguously bound a THIRD, realistic compound
   scenario — a fabricated/off-menu slot arriving specifically on REQ-505's reprompt attempt, as opposed to
   REQ-506's reroute attempt). The recommended fix explicitly reuses the already-specified
   `nextRerouteState` state machine's attempt-budget tracking rather than introducing a new mechanism, to
   minimize the risk of a fourth iteration surfacing yet another instance of this same class of ambiguity.
