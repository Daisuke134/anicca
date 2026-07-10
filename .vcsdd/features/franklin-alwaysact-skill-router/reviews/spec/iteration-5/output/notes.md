# Non-blocking observations — iteration 5 (FINAL, PASS)

Per the anti-leniency rule, these are recorded because they are genuinely minor/deferrable defects
found during a full, independent pass — not because a real defect is being softened into a note. No
blocking findings were filed this iteration; the file `output/findings/` is intentionally empty.

1. **The §2.5 transition matrix's own "exhaustive"/"no other combination reachable" claim is
   technically imprecise, though the underlying requirements are not.**
   `behavioral-spec.md:701-727`'s table is introduced as "the AUTHORITATIVE, exhaustive enumeration
   of every attempt-1 outcome × attempt-2 outcome combination" and its closing paragraph
   (`behavioral-spec.md:722-727`) states "No other attempt-1×attempt-2 combination is reachable."
   Independently enumerating the full outcome-class product (attempt-1 ∈ {no-tool-call,
   fabricated/off-menu, valid-but-no-op} × attempt-2 ∈ {valid-exec, no-tool-call, fabricated/off-menu,
   valid-but-no-op}) yields 12 reachable cells; the 9 named rows cover 8 of them explicitly. Four
   reachable cells have no dedicated row: attempt-1 = fabricated/off-menu-slot (REQ-513's own "on the
   very FIRST think() call" scenario, row 8's precursor) followed at attempt-2 by (a) another
   fabricated/off-menu slot, (b) no tool call, or (c) a valid pick that also no-ops; and attempt-1 =
   no-tool-call followed at attempt-2 by... — wait, that specific one (no-tool-call→no-tool-call) IS
   row 4, so the fourth missing cell is genuinely just those three off row-8's precursor plus none
   from the no-tool-call precursor (rows 2/3/4/9 already cover all four of its attempt-2 outcomes).
   These three missing cells (fabricated→fabricated, fabricated→no-tool-call, fabricated→no-op) are
   real and reachable (a model can fabricate `slot:'sleep'` on the very first `think()` call, get
   reprompted per REQ-513's baseline-attempt branch, and then do almost anything on the reprompt).
   They are NOT left ambiguous by the actual requirements, though: REQ-505's EARS text is written
   generically for "a given think() attempt" (not scoped to baseline/reprompt/reroute), REQ-513's
   branch rule is written generically for "attemptsUsed===1 ALREADY... by a PRIOR REQ-505 reprompt, a
   PRIOR REQ-506 reroute, or by this being itself the reroute attempt", and REQ-506's edge case is
   written generically for "the slot that just produced earnLine===null was itself picked and
   executed on a REQ-505 REPROMPT attempt" — all three correctly and unambiguously resolve every one
   of the three missing cells to ESCALATE via `attemptsUsed===1`, independent of the §2.5 table's own
   row count. The table's closing paragraph gestures at this ("once attemptsUsed===1, EVERY invalid
   outcome (of any type) terminates in ... ESCALATE") but its OWN worked example one sentence earlier
   ("Row 8's attempt-2 outcome, if instead a fabricated slot or a no-op result, is covered by rows
   3/4/9's ... pattern") omits "or no tool call again" as a third alternate for row 8, which is itself
   a small inconsistency in an artifact whose entire purpose is precision. Recommend (non-blocking,
   Phase 2a/2b polish): either add the 3 missing rows literally, or replace the "no other combination
   is reachable" sentence with something like "every other reachable combination collapses into the
   same ESCALATE pattern below, since attempt-2's outcome, once attemptsUsed=1, determines EXECUTE
   vs. ESCALATE independent of which failure type produced attemptsUsed=1 — see REQ-505/506/513's own
   generic wording." Verified this gap has ZERO effect on actual Phase 5 test coverage: PROP-511a
   (`verification-architecture.md:207`) is described as exploring "ALL orderings ... up to a bounded
   exploration depth," which is a property-test sweep that structurally includes all 12 cells, not
   just the 9 named rows; and `verification-architecture.md:300`'s Phase 5 harness-plan directive to
   "exercise EVERY row of ... §2.5's exhaustive 9-row transition matrix" is stated as a floor ("not
   merely the PROP-labeled subset"), not a ceiling, so PROP-511a's broader sweep is not excluded.

2. **REQ-510's ledger field "the number of reprompt/reroute attempts consumed (0, 1, or 2)"
   (`behavioral-spec.md:498-501`) uses a different numeric domain than REQ-511's `attemptsUsed ∈
   {0, 1}` state variable, and the spec never states which of the two domains this ledger field
   actually records.** Read literally, "attempts consumed" sounds like it should mirror
   `attemptsUsed` (whose entire domain, per REQ-511, is `{0, 1}`), but `{0, 1, 2}` only makes sense as
   "total `think()` calls made this wake" (0 in REQ-502's empty-menu terminal case, which spends zero
   `think()` calls at all; 1 in the ordinary immediate-accept case or REQ-506's empty-reroute-target
   terminal case; 2 in every reprompt/reroute/escalation case). Both readings are internally
   consistent with the rest of the spec taken in isolation, but the spec never says explicitly which
   one an implementer should ledger, and REQ-510's own acceptance criteria (`behavioral-spec.md:505-
   507`) only assert that "the new ledger fields appear on both ... paths" — never pin a specific
   numeric value for any fixture scenario, so neither reading is actually falsifiable by the stated
   AC. This is an audit/observability field, not a decision-path requirement (the router's actual
   branch logic is unaffected either way, and REQ-511's `attemptsUsed` domain itself is unambiguous
   and unaffected by this note), so it is non-blocking. Recommend (Phase 2a/2b polish): rename the
   field or add one clarifying sentence to REQ-510 stating explicitly whether it ledgers
   `attemptsUsed` (`{0,1}`) or total `think()` call count (`{0,1,2}`), and add one literal AC pinning
   the value for at least the REQ-502-empty-menu (0 `think()` calls) and REQ-506-empty-reroute-target
   (1 `think()` call) terminal cases specifically, since those are the two cases where the two
   candidate readings could plausibly diverge from naive assumption.

3. **FIND-301 is genuinely, verifiably resolved in this revision** — independently re-derived this
   iteration by reading REQ-505/506/511/513 and the new §2.5 matrix in full, not merely re-reading
   iteration-4's own notes. See `verdict.json.iteration4FindingsVerifiedResolved` for the full,
   line-cited derivation. No text anywhere in either spec file selects a retry/reroute/escalation
   branch by `currentOfferedSlots`/`ctx.alwaysActMenu` array identity or tool-schema shape;
   `attemptsUsed` is consistently and exclusively the arbiter throughout REQ-505, REQ-506, REQ-511,
   and REQ-513, and the exact FIND-301 regression scenario (a fabricated slot arriving on the
   REQ-505 reprompt attempt) is now explicitly named, tested (PROP-513e), and its REQ-506 symmetric
   counterpart is separately tested (PROP-506g).

4. **The 2-total `think()`-call ceiling (REQ-511, PROP-511a) is unviolatable in every path checked
   this iteration.** Traced every terminal path in §2.5's table plus the 4 cells noted in observation
   #1 above by hand: every path either (a) resolves in 1 `think()` call (row 1, or REQ-506/REQ-502's
   zero/one-call terminal edge cases), or (b) resolves in exactly 2 `think()` calls, with the second
   attempt's outcome unconditionally deciding EXECUTE-or-ESCALATE and never triggering a third call
   regardless of what that second outcome is. No path produces a 3rd `think()` call under any
   ordering of {no-tool-call, fabricated/off-menu-slot, no-realized-action} across up to 2 attempts.

5. **Ground-truth spot-check performed independently this iteration** (12 real files/citations
   checked against the actual repo at the current HEAD, not merely re-trusting iteration-4's own
   notes): `runtime/loop/index.mjs` (targeted reads: 170-190, 370-470), `runtime/loop/brain.mjs`
   (full read), `runtime/loop/prompt.mjs` (targeted read: 1-220), `runtime/loop/context.mjs` (full
   read), `runtime/loop/earn-slot.mjs` (full read), `runtime/loop/earn-detect.mjs` (full read),
   `runtime/loop/catalog-gate.mjs` (full read), `runtime/loop/parse-tool-call.mjs` (full read),
   `skills/registry.json` (full read, all slot entries), `skills/earn/sol-trade/run.sh` (full read),
   `skills/self/earning-health.py` (targeted read: 1-40). All cited line ranges/quotes verified as
   described in `verdict.json.groundTruthSpotChecks`; zero citation drift found this iteration
   (including the `index.mjs:183` avoidSlot quote iteration-4 had flagged as drifted to line 187 —
   re-verified against the current HEAD, it is back at line 183 exactly as the spec's own iteration-4
   changelog entry claims).
