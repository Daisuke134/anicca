# Behavioral Spec — anicca-agent-lending (Phase 1a)

**feature**: anicca-agent-lending · **mode**: strict · **increment**: in-colony agent-to-agent lending
(citizen-to-citizen loans, first-party Anicca capability, no external protocol import) · **日付**:
2026-07-07 · **revision**: iteration 8, revised (spec review iterations 1 through 6 — findings
FIND-001..008, FIND-101..107, FIND-201..206, FIND-301..305, FIND-401..403, and FIND-501..503 — ALL
resolved; iteration-7's own FIND-601..603 resolved; this revision additionally resolves iteration-8's own
FIND-701..702; see `reviews/spec/iteration-1/RESOLUTION-NOTES.md` through
`reviews/spec/iteration-8/RESOLUTION-NOTES.md`, one file per iteration, for the full per-finding
changelogs)

## Changelog (iteration 1 → iteration 2)

Spec review iteration 1 FAILed with 8 findings (2 critical, 4 major, 1 medium, 1 minor). Each is resolved
by a specific, cited design decision (not a vague "will fix later"); see
`reviews/spec/iteration-1/RESOLUTION-NOTES.md` for the full detail per finding:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-001 | critical | REQ-106 now fully specifies `loan_id = loan_${lenderId}_${n}`, `n` a per-lender monotonic sequence computed strictly inside the SAME per-lender lock — namespaced by `lenderId`, so no shared/global lock is needed for collision-freedom (new PROP-106e). |
| FIND-002 | critical | New REQ-112: loan issuance/repayment participation scoped to a single coordinator host this increment, the direct by-name analog of `anicca-agent-spawn` REQ-106, with the remote-cloud-hosted-citizen case explicitly out of scope (new PROP-112a). |
| FIND-003 | major | Dependencies section now cites `payViaFacilitator`'s real full signature, states `facilitatorUrl` has no default and requires the already-running facilitator service, and REQ-106 specifies fail-closed behavior on disbursement failure (new PROP-106f). |
| FIND-004 | major | REQ-104/105 rewritten to separate the PROVEN sizing claim (zero-collateral cold-start issuance) from the UNPROVEN economic claim (borrower repayment capacity), state the intended cold-start use case honestly, and add a monitoring-plan function `computeColdStartRepaymentRate` (new PROP-105f). |
| FIND-005 | major | REQ-101 now reads (read-only) `ubi`'s `gojo-log.jsonl` and subtracts recent gojo commitments from a lender's available surplus (`sumRecentGojoGiftsUsd`, new PROP-101f); the reverse direction is explicitly flagged as an acknowledged, not-yet-solved limitation. |
| FIND-006 | medium | Dependencies section's `citizens.json` record-shape citation updated to the CURRENT (iteration 4) `anicca-agent-spawn` shape, including `homeDir`. |
| FIND-007 | major | REQ-108/verifyRepayment now cites the REAL precedent (`record-earn.mjs`'s `TRANSFER_TOPIC`/exact-padded-address-equality/finalized-block pattern), not the false `escrow.mjs` claim (new fixture in PROP-108b covering the `FIND-704` bug class). |
| FIND-008 | minor | REQ-104's `LOAN_INTEREST_RATE` justification rewritten as an honest, conservative starting parameter, not a reuse of `ubi.js`'s unrelated profit-tithe rate. |

## Changelog (iteration 2 → iteration 3)

Spec review iteration 2 FAILed with 7 findings (3 critical, 4 major). Each is resolved by a specific,
cited design decision; see `reviews/spec/iteration-2/RESOLUTION-NOTES.md` for the full detail per finding:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-101 | critical | Dependencies section's `anicca-agent-spawn` citation rewritten to be explicitly DYNAMIC — no frozen iteration number/FIND-list is stated as a durable fact anymore; new REQ-113 makes a fresh, dated re-read of that sibling spec's THEN-CURRENT state, immediately before this feature's own Phase 2a begins, a standing acceptance criterion (new PROP-113a). |
| FIND-102 | critical | `sumRecentGojoGiftsUsd` now takes a `lenderId` parameter and is gated to `GOJO_SENDER_ID` ("anicca-a3cdd4", today's real, only gojo sender per `run.sh`'s own hardcoded identity) — returns `0` unconditionally for every other lender, documented as a real, honest limitation of `gojo`'s own single-sender design (updated PROP-101f). |
| FIND-103 | critical | REQ-106 now specifies a crash-safe two-phase ledger record — a PROVISIONAL row (`status:"provisioning"`) appended BEFORE `payViaFacilitator`, a FOLLOW-UP row (`status:"active"`/`"disbursement_failed"`) after — and requires a caller reclaiming a stale lock to perform a REAL on-chain lookup before ever retrying disbursement for an already-reserved sequence number (new PROP-106g). |
| FIND-104 | major | REQ-108/REQ-109 now wrap their own repayment-verification/default-detection appends in a NEW, per-loan lock (`loan_${loan_id}`, distinct from REQ-106's per-lender `loan_${lenderId}` issuance lock) (new PROP-108d/PROP-109e). |
| FIND-105 | major | REQ-108's `from`-topic check reworded: `record-earn.mjs`'s own `FIND-704` fix is a literal reuse for the `to` topic only; the `from`-topic check is an honest, sound EXTENSION of that technique, not a literal reuse of an already-tested code path for that field (updated PROP-108b). |
| FIND-106 | major | REQ-102's `BORROWER_LOW_USD` is now this feature's OWN independently-declared constant (default `0.50`), set to the SAME numeral as `economy/gig/decide.mjs`'s `DEFAULT_LOW_USDC` for definitional consistency only, via NO import/code coupling — explicitly cross-referenced against REQ-110's zero-coupling requirement (updated PROP-110a). |
| FIND-107 | major | `computeColdStartRepaymentRate`'s definition corrected to "loans whose `successfulOnTimeRepayments`, re-derived over that borrower's own strictly-earlier rows, is `0` at issuance" — removing the false "(i.e. every borrower's own first-ever loan)" equivalence; a borrower's 2nd+ loan CAN recur at cold-start if all priors were repaid late, and this is intentional (updated PROP-105f). |

## Changelog (iteration 3 → iteration 4)

Spec review iteration 3 FAILed with 6 findings (3 critical, 3 major). Each is resolved by a specific,
cited design decision; see `reviews/spec/iteration-3/RESOLUTION-NOTES.md` for the full detail per finding:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-201 | critical | REQ-106 now names a THIRD terminal disbursement status, `"disbursement_uncertain"`, for an in-process (non-crash) exception thrown from `payViaFacilitator` AFTER its own on-chain settle already succeeded; `reconcileProvisionalDisbursement` is unified to ALSO resolve this row on the NEXT issuance attempt for that lender, never gated on a stale-lock reclaim (new PROP-106h). |
| FIND-202 | critical | `verifyRepayment` now reads the FULL `loans.jsonl` ledger and rejects any `txHash` already recorded as credited anywhere in it — closing BOTH a same-loan replay and a cross-loan replay, checked BEFORE any value is credited (new PROP-108e). |
| FIND-203 | critical | New pure function `evaluateColdStartKillSwitch({sampleSize, rate, defaultedCount}) → {paused, reason}` makes REQ-105's kill-switch a concrete, testable SHALL, called by REQ-106's issuance step before the per-lender lock for any cold-start request (new PROP-105g); the previously-contradicting adjacent Edge Case is rewritten to match. |
| FIND-204 | major | `excludeDefaultedBorrowers` (a whole-citizen removal) replaced by `adjustBalancesForOutstandingDebt` — a debt-PROPORTIONAL balance adjustment, same array length, only the defaulted citizen's own balance figure reduced by its own unrecovered debt, clamped at `0` (new PROP-109f). |
| FIND-205 | major | REQ-106's own Acceptance Criteria corrected to state its two-phase issuance append is wrapped ONLY by its own per-lender lock, NEVER REQ-108/109's per-loan lock — a new structural check (PROP-106i) makes the distinction independently verifiable. |
| FIND-206 | major | Every dollar-denominated formula this feature introduces now clamps via the established `+(...).toFixed(6)` money-precision convention (`ubi.js::contribute()`/`decide.mjs::decideGigAction()`), with every Acceptance Criterion asserting against the clamped value. |

## Changelog (iteration 4 → iteration 5)

Spec review iteration 4 FAILed with 5 findings (3 critical, 2 major). Each is resolved by a specific,
cited design decision; see `reviews/spec/iteration-4/RESOLUTION-NOTES.md` for the full detail per finding:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-301 | critical | Reconciliation trigger broadened to be driven PURELY by ledger STATE (an unterminated highest-`n` row), never by lock staleness — closing a THIRD terminal state (the follow-up `appendChild` call itself throwing, and the reconciliation lookup itself throwing) neither the crash path nor the in-process-exception path alone had covered (new PROP-106k/PROP-106l). |
| FIND-302 | major | "Logged" (for a rejected replay) precisely defined: recorded EXCLUSIVELY via an out-of-band audit/trace mechanism, NEVER a new `loans.jsonl` row — preserving the last-write-wins convention every other reduction in this spec depends on. |
| FIND-303 | critical | New Tier-0 structural proof obligation, PROP-105h, requires a direct control-flow read confirming the REAL, production REQ-106 issuance code — never a mock — actually imports and calls `evaluateColdStartKillSwitch` before the per-lender lock. |
| FIND-304 | critical | `adjustBalancesForOutstandingDebt`'s composition point corrected to name `anicca-agent-spawn`'s REAL three-step pipeline (`filterProductiveCitizens` → `readCitizenBalances` → `computeColonySurplusUsd`) and to insert strictly after `readCitizenBalances`'s own balance-attached output, never between steps (1) and (2). |
| FIND-305 | critical | REQ-112's co-location mechanism corrected to read `anicca-agent-spawn`'s own `citizen.coLocatedWithCoordinator` boolean field EXCLUSIVELY — never `homeDir` equality, which today's real, distinct `homeDir` seed values would have wrongly excluded; REQ-113 now names this field's re-verification as its own explicit line item. |

## Changelog (iteration 5 → iteration 6)

Spec review iteration 5 FAILed with 3 findings (2 critical, 1 major). Each is resolved by a specific,
cited design decision; see `reviews/spec/iteration-5/RESOLUTION-NOTES.md` for the full detail per finding:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-401 | critical | New per-borrower lock key `` `loan_borrower_${borrowerId}` ``, acquired ALONGSIDE (never instead of) the existing per-lender `` `loan_${lenderId}` `` lock via nested `withGigLock` calls, closes the cross-lender same-borrower double-disbursement window a per-lender-only lock could not (new PROP-106n). |
| FIND-402 | critical | REQ-102 gains a FOURTH condition, (d) `lenderId !== borrowerId`, checked FIRST — before (a)-(c) and before REQ-101's own availability computation — closing a real self-loan exploit that could otherwise fabricate `successfulOnTimeRepayments` at negligible cost (new PROP-102e). |
| FIND-403 | major | `issued_ms` precisely defined: drawn EXCLUSIVELY from the follow-up `"active"` row's own append-time timestamp, NEVER the provisional row's `provisioned_ms`, so a reconciliation delay never silently eats into a borrower's real repayment window (new PROP-106o). |

## Changelog (iteration 6 → current, this revision)

Spec review iteration 6 FAILed with 3 findings (2 major, 1 minor); this revision resolves all three. Each
is resolved by a specific, cited design decision; see `reviews/spec/iteration-6/RESOLUTION-NOTES.md` for
the full detail per finding:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-501 | major | REQ-106's "Lock-acquisition order" paragraph's prior "textbook deadlock-avoidance" justification is REMOVED as analytically FALSE against `lock.mjs`'s real, non-blocking, fail-fast `withGigLock` mechanism (re-confirmed fresh this revision) — classical hold-and-wait deadlock is structurally impossible against a primitive where a failed second-lock acquire returns immediately rather than blocking. The fixed lexicographic order is RETAINED, but for two honestly-stated, DIFFERENT reasons: (1) a single deterministic convention, not an ad-hoc per-call choice, and (2) forward-insurance should `lock.mjs` ever become a blocking primitive. PROP-106m's own description corrected to match. |
| FIND-502 | major | New REQ-114 adds a SECOND, general-purpose, dollar-weighted default-rate monitor (`computeOverallDefaultRateUsd`/`evaluateOverallDefaultKillSwitch`) spanning ALL loan tiers — operating ALONGSIDE REQ-105's cold-start-only monitor — closing a bust-out/reputation-laundering blind spot where an established borrower's default on a large (up to `$5.00`) loan was invisible to REQ-105's own kill-switch (new PROP-114a/b/c/d). |
| FIND-503 | minor | This header/changelog section itself rewritten to tabulate every iteration's fixes through iteration 6 (this revision), replacing the previously-stale "iteration 3" header that stopped at the iteration-2→3 changelog table. |

## Changelog (iteration 7 → current, this revision)

Spec review iteration 7 FAILed with 3 findings (2 major, 1 minor); this revision resolves all three. Each
is resolved by a specific, cited design decision; see `reviews/spec/iteration-7/RESOLUTION-NOTES.md` for
the full detail per finding:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-601 | major | REQ-106's own lock-protected fresh-check (added for FIND-401 to re-verify REQ-101/102/105's sizing/eligibility) now ALSO RE-EVALUATES BOTH `evaluateColdStartKillSwitch` and `evaluateOverallDefaultKillSwitch`, against the SAME fresh, lock-protected read of `loans.jsonl` already used for that recheck — closing a TOCTOU race where a kill-switch tripping strictly BETWEEN a specific attempt's own pre-lock check and its own later lock acquisition could otherwise still slip an issuance through, since neither switch is scoped to the specific `lenderId`/`borrowerId` pair whose locks are held (new PROP-106p; extends PROP-105h/PROP-114c). |
| FIND-602 | major | REQ-114 gains a SECOND, complementary, ABSOLUTE dollar-loss-within-a-rolling-window signal (`computeRecentDefaultLossUsd`, feeding an extended `evaluateOverallDefaultKillSwitch`) — immune, by construction, to the volume-dilution failure mode its own dollar-weighted RATIO alone cannot close (a large volume of OTHER, unrelated, healthy loans diluting `defaultRateUsd` below `0.20` even as a genuine bust-out default lands); EITHER signal tripping is independently sufficient to pause (new PROP-114e/PROP-114f, extends PROP-114b/PROP-114c). REQ-109's `"defaulted"` row gains a new `defaulted_ms` field to support this signal's own rolling window. |
| FIND-603 | minor | The self-loan-exclusion cross-reference (REQ-106's own Edge Case and Acceptance Criterion) now names `evaluateOverallDefaultKillSwitch` alongside `evaluateColdStartKillSwitch`. |

## Changelog (iteration 8 → current, this revision)

Spec review iteration 8 FAILed with 2 findings (1 critical, 1 major); this revision resolves both. Each is
resolved by a specific, cited design decision; see `reviews/spec/iteration-8/RESOLUTION-NOTES.md` for the
full detail per finding:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-701 | critical | `evaluateOverallDefaultKillSwitch`'s absolute-loss branch comparison corrected from strict `>` to `>=` (`totalRecentDefaultLossUsd >= RECENT_DEFAULT_LOSS_THRESHOLD_USD`) — a single bust-out default landing EXACTLY at REQ-105's own `maxLoanUsd = $5.00` ceiling now genuinely trips this signal by itself, matching this SAME requirement's own worked edge case and PROP-114f's own fixture (neither of which needed to change, since both already asserted `paused:true` at exactly `$5.00`). The prior strict `>` made the requirement's own stated design intent (a single max-size default trips it "by itself") mathematically unreachable, since no single loan issued under REQ-105's own ladder can ever exceed `$5.00`. |
| FIND-702 | major | New Tier-0 structural proof obligation, PROP-109g, mirroring PROP-105h's/PROP-106d's/PROP-114c's own real-source-read discipline exactly, requires a direct control-flow read confirming REQ-109's own REAL, production default-append code — never a hand-authored test fixture with `defaulted_ms` already populated as literal data — genuinely sets `defaulted_ms: Date.now()` on every `"defaulted"` row it appends, and omits this field on every non-`"defaulted"` status-transition row. |

## Background / rationale (cite before design)

1. **No external protocol solves this.** A live web+repo search (this session) found zero
   agent-to-agent lending implementations anywhere: Maple Finance, Goldfinch, TrueFi, and Cred
   Protocol all lend pooled crypto capital to human/DAO/fintech borrowers, never to autonomous AI
   agents as counterparties. The one academic treatment, arXiv 2602.14219 ("The Agent Economy"),
   §4.2.2, proposes "Reputation Capital" — an on-chain Proof-of-Competence score usable AS collateral
   instead of upfront assets — but explicitly never resolves the cold-start case (a brand-new agent
   with zero reputation) and ships zero code. This spec exists because the gap is real, not because a
   reference implementation was skipped.
2. **Our own colony already proved gig-work alone cannot bootstrap a broke citizen.**
   `.vcsdd/features/anicca-agent-economy/specs/SPEC.md` §9.9 (the "P2 WITNESS" event, 2026-07-07)
   records that two near-zero-balance Franklin instances never spontaneously posted/took a gig during
   ~20 minutes of real autonomous wake cycles, because neither could actually afford to fund a bounty —
   the transaction only happened after a one-time, human-approved genesis injection from claude-p
   (human-funded), explicitly carved out as a non-repeatable exception (memory
   `feedback_human_funded_ai_permanently_outside_agent_economy.md`; SPEC.md §0's HARD invariant). This
   feature is the deterministic, self-funded, repeatable mechanism that exception was never meant to be.
3. **This is first-party, not an import.** Per Dais's explicit framing (2026-07-07): "This is our moat,
   this is the shit we build ourselves" — a rich, self-funded citizen loans to a broke, self-funded
   citizen; the borrower earns (gig-work and/or trade) and repays with interest; lending and gig-work
   are two COEXISTING options, neither replacing the other.

## Scope of this increment (read first)

This spec covers exactly: (a) who may lend, (b) who may borrow, (c) how big the first loan is and how
later loans grow from repayment history (the cold-start resolution), (d) how repayment is verified and
default is handled, (e) concurrency safety, (f) the money-safety invariant, and (g) coexistence with
`economy/gig` (and, read-only, `economy/ubi`'s gojo mutual aid — REQ-101). It does NOT invent a
variable-rate/variable-amount lending market, does NOT build multi-signer pooled loans, and does NOT
extend to Solana-denominated lenders/borrowers this increment (REQ-107 narrows scope honestly for
chain/asset). **REQ-112 (below) is this feature's own direct, by-name analog of `anicca-agent-spawn`
REQ-106's single-coordinator-host scope-narrowing precedent** — lending participants (both lender and
borrower), not merely spawn evaluators, are scoped to one shared, mounted filesystem this increment; see
REQ-112 for the full statement and its known-limitation edge case (a future remote-cloud-hosted citizen,
per `anicca-agent-spawn` REQ-301, is explicitly out of scope for lending TO/FROM it). P4's future "bank"
vision (SPEC.md §9.3, a Goldfinch-`CreditLine.sol`-style growth engine with third-party-verified trust
scores) is explicitly a LATER, larger increment; this spec is v1: the smallest mechanism that actually
resolves the cold-start SIZING problem today (see REQ-105's honest reframing of what "resolves" means
here — sizing is proven, borrower repayment capacity is an explicit, monitored, experimental hypothesis,
not a proven claim).

## Dependencies and assumptions (must be read before implementation)

- **`anicca-agent-spawn` is an independently-evolving SIBLING feature, STILL MID-VCSDD-PIPELINE at every
  revision of THIS document, and its own iteration number/finding-list/gate-verdict MUST NEVER be cited
  here as a frozen, durable fact (resolves this revision's own FIND-101 — a DIRECT RECURRENCE of
  iteration-1's own FIND-006, one full revision cycle later).** Iteration-1's FIND-006 already
  demonstrated that a point-in-time snapshot of that sibling spec's state goes stale between revisions of
  THIS one; this revision's own FIND-101 demonstrated it AGAIN — and, re-verified in the course of
  resolving FIND-101, `anicca-agent-spawn`'s own Phase 1c gate has, in the interim, FAILed yet again
  (iteration 6, `state.json` `gates."1c"` timestamped `2026-07-07T11:02:55.800Z`, findings
  FIND-501..504), a further iteration past the iteration-5/FIND-401..405 state FIND-101's own evidence
  cited as "current" only minutes earlier. `anicca-agent-spawn` is a moving target BY CONSTRUCTION; no
  snapshot frozen inside this document can stay accurate across the gap between one Phase 1c review pass
  and this feature's own later Phase 2a/2b start. THE SYSTEM therefore adopts "re-verify at first use"
  (REQ-113 below), never "keep the citation updated," as the correct discipline.
  `anicca-agent-spawn` (`.vcsdd/features/anicca-agent-spawn/specs/behavioral-spec.md`) defines REQ-101
  (`computeColonySurplusUsd`, `filterProductiveCitizens`) and REQ-105 (the dedicated citizen registry,
  `~/anicca/skills/self/spawn/registry/citizens.json` — NOT YET CREATED on disk as of the last direct
  filesystem check performed for this revision). This feature's lender/borrower surplus arithmetic
  (REQ-101/102 below) is designed to be CONCEPTUALLY CONSISTENT with that registry's record shape AS
  READ DURING THIS REVISION's own re-verification pass (`{id: string, wallet:
  {evm?: boolean, solana?: boolean}, walletAddress: {evm?: string, solana?: string}, fuel: {provider:
  string}, humanDependencies: string[], homeDir: string, coLocatedWithCoordinator: boolean}` — corrects
  this revision's own FIND-305, which found the prior citation here both omitted the
  `coLocatedWithCoordinator` field entirely AND wrongly claimed today's two real citizens share an
  identical bare `homeDir`. The `homeDir` field passes through this feature's own
  `adjustBalancesForOutstandingDebt` unchanged (REQ-109) but is NOT this feature's own co-location
  mechanism; REQ-112 below reads `coLocatedWithCoordinator` directly instead — see REQ-112 for the full,
  corrected statement of why (`anicca-agent-spawn`'s own hardened design already establishes "co-located
  does NOT mean same `homeDir`," and provides this purpose-built boolean specifically so no consumer,
  including this feature, has to re-derive co-location from `homeDir` equality)) and with
  `computeColonySurplusUsd`'s arithmetic style (`max(0, balance_i
  - perCitizenReserveUsd)`, `perCitizenReserveUsd` defaulting to `5.00`) — it deliberately reuses that same
  default rather than inventing a second, competing reserve figure. **This feature does NOT modify
  `anicca-agent-spawn`'s own function signatures or files** (avoiding a tight coupling between two
  independently-evolving specs); instead it composes a SECOND, lending-owned balance-adjustment pass
  (`adjustBalancesForOutstandingDebt`, REQ-109 — a debt-proportional adjustment, never a whole-citizen
  removal, resolves FIND-204) inserted at the CORRECT point in that sibling spec's own REAL, THREE-step
  pipeline (re-read fresh this revision; corrects this revision's own FIND-304, which found the prior
  two-step "runs AFTER `filterProductiveCitizens`'s output" description incomplete): (1)
  `filterProductiveCitizens({citizens, ledgerRows, nowMs, bootstrapWindowDays})` filters the citizen
  array by ledger lifecycle status ONLY — it attaches NO balance field to any citizen record; (2)
  `readCitizenBalances({citizens})` (`~/anicca/skills/self/spawn/lib/colony-balances.mjs`, re-read this
  session) — a NEW, EFFECTFUL, coordinator-run step, distinct from and AFTER step (1), that queries each
  citizen's balance directly from public-chain RPC keyed on `walletAddress` and is the ONLY place a
  `balance_i` figure is EVER attached to a citizen record; (3) `computeColonySurplusUsd({citizens,
  perCitizenReserveUsd})`, which consumes the NOW-balance-attached array step (2) produces. Because
  `adjustBalancesForOutstandingDebt` is pure/zero-I/O and must REDUCE an ALREADY-ATTACHED balance figure
  (it cannot attach that figure itself), it is composed AFTER step (2) `readCitizenBalances` and BEFORE
  step (3) `computeColonySurplusUsd` — never between steps (1) and (2), where no citizen record yet
  carries any balance field for it to reduce (see REQ-109 below for the full statement). **REQ-113
  below is the standing, non-optional discipline this feature actually relies on to stay correct against
  this moving-target dependency: it is NOT sufficient to get this citation right once, during spec
  review — whoever begins this feature's own Phase 2a implementation MUST re-read
  `anicca-agent-spawn`'s THEN-CURRENT `specs/behavioral-spec.md` and `state.json` fresh, at that time,
  and record that re-read in writing, before writing a single test against REQ-101/102/109/112's
  registry-shape assumptions.** If that fresh re-read reveals the registry/join shape (or its
  aggregation semantics — e.g. how a dual evm+solana wallet citizen is summed, per that spec's own
  FIND-404/FIND-503) has changed, REQ-101/102/109/112 MUST be revisited at that time — this is a live,
  explicitly-flagged risk, not an oversight.
- **`~/anicca/skills/self/spawn/lib/child-spec.js::nextChildId(children, prefix, width)`** (read this
  session, lines 5-14: `max(existing matching-`prefix` numeric suffix) + 1`, zero-padded) is the ONLY
  existing colony precedent for monotonic-ID derivation and is the INSPIRATION for REQ-106's `loan_id`
  scheme below — but it is deliberately NOT reused verbatim, because its own upstream correctness depends
  entirely on `anicca-agent-spawn` REQ-106 scoping ALL evaluators (including ID assignment itself) under
  ONE shared `"colony-spawn"` lock, a precondition THIS feature's own REQ-106 explicitly does NOT have
  (different lenders intentionally hold DIFFERENT lock keys with zero contention between them). REQ-106
  below therefore specifies a NAMESPACED variant (`loan_${lenderId}_${n}`, `n` scoped and incremented
  strictly per-lender, inside that SAME lender's own existing lock) that is race-free by construction
  without requiring any shared/global lock — a stronger, not merely borrowed, guarantee.
- **`~/anicca/skills/economy/ubi/ubi.js::distributeAI`** (read this session, lines 56-96) and
  `~/anicca/skills/economy/ubi/run.sh` (read this session, lines 15-21, 57-142) together implement the
  ALREADY-EXISTING, already-witnessed "gojo" mutual-aid mechanism: a surplus citizen's own surplus-above-
  reserve arithmetic gates a rescue gift to a broke citizen, logged append-only (one JSON object per
  line) to `~/anicca/skills/economy/ubi/state/gojo-log.jsonl`, each row shaped exactly as `run.sh` itself
  writes it: `{ts, recipient, recipient_wallet, surplus_above_reserve_usd, decision: {amount_usd,
  reason}, executed}`. This is a DIFFERENT mechanism than this feature's own loan ledger, computed from
  the SAME kind of "surplus above reserve" input, with ZERO awareness of `loans.jsonl` in either
  direction today. REQ-101 below reads (READ-ONLY, never writes) this SAME existing state file to make
  lending aware of a lender's own recent gojo commitments — this feature does NOT modify `ubi.js` or
  `run.sh` in any way.
- **`~/anicca/skills/self/spawn/lib/ledger.js`** (`readChildren(file)`/`appendChild(file, row)`) is, on
  inspection, a fully generic, file-path-parameterized append-only-JSONL primitive — it hardcodes no
  "child" domain logic (the naming reflects its original call site, not an intrinsic restriction on
  what it can store). This feature REUSES these two exported functions UNMODIFIED, imported directly
  from their existing location, but points them at a NEW, DEDICATED file
  (`~/anicca/skills/economy/lending/state/loans.jsonl`) — never the SAME file spawn's own child rows
  live in. This mirrors the exact reasoning `anicca-agent-spawn` REQ-105 already applied when it
  refused to repurpose `economy/ubi/colony-wallets.json` for a different concern (FIND-101): reuse the
  CODE, never commingle two independently-owned record types in one physical file. Cross-skill-directory
  reuse of a generic primitive is already an established pattern in this colony (`anicca-agent-spawn`
  REQ-103 reuses `economy/gig/lib/lock.mjs` directly, unmodified, from a different skill directory).
- **`~/anicca/skills/economy/gig/lib/lock.mjs`** (`withGigLock`, `isLockStale`, atomic `fs.rename`
  stale-reclaim) is reused UNMODIFIED for loan-issuance mutual exclusion (REQ-106), exactly the same
  module `anicca-agent-spawn` REQ-103 already reuses for colony-spawn — a new lock KEY on an EXISTING,
  already-adversary-hardened lock MECHANISM, never new lock code.
- **`~/anicca/skills/_shared/lib/is-self-funded.mjs`** (`isSelfFunded`/`selfFundedReasons`) is reused
  UNMODIFIED, unchanged in every respect, to gate BOTH lender (REQ-101) and borrower (REQ-102)
  eligibility — a human-funded entity (claude-p or any other) can never pass either gate (REQ-111).
- **`~/anicca/skills/economy/gig/lib/escrow.mjs::payViaFacilitator`** (the existing, live-proven,
  gasless, self-signer USDC transfer primitive already used for gig disbursement/payout — real tx
  `0x383e9369` etc., per SPEC.md §9.9) is reused UNMODIFIED as this feature's sole money-movement
  primitive for BOTH loan disbursement and loan repayment (REQ-107) — its REAL, full exported signature
  (re-read this session, escrow.mjs lines 150-165) is `payViaFacilitator({ privateKey, to, amountBase,
  facilitatorUrl, chainId, usdcAddress, domainName, rpcUrl, chain, validitySeconds })`; only
  `chainId`/`usdcAddress`/`domainName`/`rpcUrl`/`chain`/`validitySeconds` default from `GIG_CHAIN`'s
  active chain profile — **`facilitatorUrl` has NO default inside `payViaFacilitator` itself.** Every
  real call site in this codebase (`gig.mjs` lines 78, 158, 288) explicitly supplies it, resolved as
  `process.env.GIG_FACILITATOR_URL || "http://127.0.0.1:8405"` — i.e. `payViaFacilitator` structurally
  REQUIRES a reachable, RUNNING x402-rs facilitator service (an ALREADY-RUNNING colony service, per P2.1,
  not new infrastructure this feature stands up) for every call, not merely a wallet + amount. This
  feature's own loan-issuance/repayment call sites SHALL resolve `facilitatorUrl` via the SAME
  `GIG_FACILITATOR_URL`-env-then-`127.0.0.1:8405`-default pattern `gig.mjs` already establishes — never a
  second, independently-invented resolution rule. THE SYSTEM SHALL fail closed if the facilitator is
  unreachable at disbursement or repayment time: the operation (whichever side is paying) fails cleanly
  with no partial state and no `loans.jsonl` row appended — never a silent proceed without payment — and
  is retriable on the next wake (see REQ-106's disbursement edge case below for the specific
  loan-issuance-critical-section framing). `~/anicca/skills/economy/ubi/execute-ubi.py`'s raw-ERC20
  (non-gasless) transfer was read and considered but NOT chosen as the primary path (gasless is strictly
  better for a possibly gas-poor borrower) — it remains a documented, out-of-scope fallback, not built
  this increment.
- **`~/anicca/skills/economy/gig/decide.mjs`** (`DEFAULT_RESERVE_USDC=5.0`, `DEFAULT_LOW_USDC=0.5`) —
  this feature's own `BORROWER_LOW_USD` constant (REQ-102) is declared INDEPENDENTLY inside this
  feature's own module, deliberately set to the SAME number, `0.5`, as `decide.mjs`'s `DEFAULT_LOW_USDC`
  (the SAME colony-wide "genuinely broke" DEFINITION, not a second, competing one) — but via NO import
  and NO code coupling whatsoever (resolves this revision's own FIND-106, which found the prior
  "reuses ... verbatim" wording here directly contradicted REQ-110's own zero-coupling requirement,
  PROP-110a). See REQ-102/REQ-110 for the full statement of this "same numeral, zero coupling" design.

## Purity boundary analysis (overview — file/function detail lives in verification-architecture.md)

| Concern | Classification | Why |
|---|---|---|
| Self-funded gate (lender + borrower) | **Pure core (existing, reused unmodified)** | `is-self-funded.mjs::isSelfFunded` — zero new judgment logic. |
| Lender available-surplus arithmetic | **Pure core (new)** | `computeLenderAvailableUsd`/`sumOutstandingPrincipalUsd` — deterministic arithmetic over already-fetched balances + already-read ledger rows, zero I/O. |
| Borrower eligibility check | **Pure core (new)** | `isBorrowerEligible` — boolean logic over already-known facts (self-loan exclusion via `lenderId`, checked FIRST; self-funded; balance; outstanding-obligation lookup) — resolves this revision's own FIND-402. |
| Reputation-capital sizing ladder | **Pure core (new)** | `computeLoanCapUsd`/`countSuccessfulOnTimeRepayments` — deterministic function of a repayment COUNT read from this feature's own ledger, no external oracle, no model judgment. |
| Loan issuance decision | **Pure core (new)** | `decideLoan` — boolean comparison of already-computed numbers. |
| Default detection | **Pure core (new)** | `detectDefaultedLoans` — deterministic elapsed-time comparison over already-read rows. |
| Cross-feature defaulted-borrower balance adjustment | **Pure core (new)** | `adjustBalancesForOutstandingDebt` — a SECOND, lending-owned, debt-PROPORTIONAL balance adjustment (never a whole-citizen removal, resolves FIND-204) composed after `anicca-agent-spawn`'s own THREE-step pipeline reaches `readCitizenBalances`'s own output (never inside `filterProductiveCitizens`, and never between `filterProductiveCitizens` and `readCitizenBalances`, where no balance field yet exists to reduce — corrects this revision's own FIND-304) and before `computeColonySurplusUsd` runs. |
| Per-lender loan-ID sequencing | **Pure core (new)** | `nextLoanSequenceForLender(loanRows, lenderId)` — deterministic `max(matching `loan_${lenderId}_` prefix's numeric suffix) + 1` over already-read rows, zero I/O; computed inside REQ-106's existing per-lender lock. Treats `"provisioning"`/`"disbursement_failed"`/`"active"`/`"disbursement_uncertain"` rows for the SAME `loan_id` as one already-claimed sequence number (last-write-wins) — never reuses `n` while a `"provisioning"` OR `"disbursement_uncertain"` row lacks a terminal follow-up (resolves FIND-103 and FIND-201), and the EFFECTFUL caller's own reconciliation check for such an unterminated row is triggered PURELY by this ledger STATE, never by lock staleness (resolves FIND-301). |
| Cold-start kill-switch enforcement | **Pure core (new)** | `evaluateColdStartKillSwitch({sampleSize, rate, defaultedCount}) → {paused, reason}` — deterministic threshold check over `computeColdStartRepaymentRate`'s own output, zero I/O; called by REQ-106's issuance step before acquiring the per-lender lock for any cold-start loan request (resolves FIND-203). |
| Colony-wide, dollar-weighted default-rate monitoring (ALL loan tiers — bust-out/reputation-laundering defense) | **Pure core (new)** | `computeOverallDefaultRateUsd({loanRows}) → {totalIssuedUsd, totalDefaultedUsd, defaultRateUsd, sampleSize}` — dollar-weighted (never merely count-weighted) default-rate arithmetic over EVERY terminal loan colony-wide, regardless of tier; zero I/O. Operates ALONGSIDE, never replacing, the cold-start-scoped monitor above (resolves this revision's own FIND-502). A SECOND, sibling pure function, `computeRecentDefaultLossUsd({loanRows, nowMs, windowDays}) → {totalRecentDefaultLossUsd, windowDays}`, closes a DIFFERENT dilution failure mode this ratio ALONE cannot close — dilution by unrelated loan VOLUME, not merely count — via an ABSOLUTE dollar-loss sum within a rolling window, immune to ratio-style dilution by construction (resolves this revision's own spec-review iteration-7 FIND-602). REQ-114. |
| Colony-wide default kill-switch enforcement | **Pure core (new)** | `evaluateOverallDefaultKillSwitch({totalIssuedUsd, totalDefaultedUsd, defaultRateUsd, sampleSize, totalRecentDefaultLossUsd}) → {paused, reason}` — deterministic THREE-condition threshold check: the ratio-based and small-sample branches over `computeOverallDefaultRateUsd`'s own output (unchanged, resolves FIND-502), PLUS (this revision, resolves FIND-602) an absolute-loss branch over `computeRecentDefaultLossUsd`'s own output, immune to volume dilution — EITHER signal alone is sufficient to pause; called by REQ-106's issuance step, for EVERY loan request regardless of tier, IN ADDITION TO `evaluateColdStartKillSwitch`, before acquiring the per-lender lock, AND (this revision, resolves FIND-601) RE-EVALUATED a SECOND time inside REQ-106's own lock-protected fresh-check, against the SAME fresh read used for REQ-102/101/105's own recheck. REQ-114. |
| Read-only gojo-commitment awareness | **Pure core (new)** | `sumRecentGojoGiftsUsd(gojoLogRows, nowMs, lookbackHours, lenderId)` — deterministic sum over already-read `gojo-log.jsonl` rows within a lookback window, GATED to `lenderId === GOJO_SENDER_ID` (`"anicca-a3cdd4"`, today's only real gojo sender) — returns `0` unconditionally for any other lender (resolves FIND-102). Zero I/O. REQ-101. |
| Cold-start monitoring (experimental-hypothesis tracking) | **Pure core (new)** | `computeColdStartRepaymentRate({loanRows, n})` — deterministic outcome-rate arithmetic over the first `n` loans whose `successfulOnTimeRepayments`, re-derived over each borrower's own strictly-earlier rows (never a stored field), is `0` at issuance — NOT equivalent to "borrower's first-ever loan" (resolves FIND-107). Zero I/O, zero judgment. REQ-105. |
| Loan ledger (dedicated file, existing generic primitive reused) | **Effectful shell (existing code, new file)** | `ledger.js::readChildren`/`appendChild`, reused unmodified, pointed at `~/anicca/skills/economy/lending/state/loans.jsonl`. |
| Read-only gojo-log reader (new, read-only) | **Effectful shell (new)** | `readGojoLogRows(gojoLogPath)` — plain `fs.readFileSync` + line-split + `JSON.parse` over `~/anicca/skills/economy/ubi/state/gojo-log.jsonl`; NEVER writes, never uses `ledger.js` (that file is not this feature's own ledger). REQ-101. |
| Loan-issuance mutual exclusion + repayment/default write discipline | **Effectful shell (existing, reused unmodified)** | `lock.mjs::withGigLock`/`isLockStale`, THREE distinct new lock keys: `loan_<lenderId>` (REQ-106, per-lender issuance — still alone owns `loan_id` sequencing correctness) and `loan_borrower_<borrowerId>` (REQ-106, NEW this revision, per-borrower cross-lender exclusivity on REQ-102's at-most-one-outstanding-loan invariant, resolves FIND-401 — both acquired together via `resolveLoanLockAcquisitionOrder`'s deterministic total order) and `loan_<loan_id>` (REQ-108/109, per-loan repayment/default writes — resolves FIND-104), canonical `statePath` = `LOANS_LEDGER_PATH` for all three. |
| Disbursement / repayment transfer | **Effectful shell (existing, reused unmodified)** | `escrow.mjs::payViaFacilitator`. |
| Independent repayment verification | **Effectful shell (new, reuses an already-hardened pattern)** | An RPC `getTransactionReceipt` + finalized-block + `Transfer`-log check, reusing `record-earn.mjs`'s own already-hardened `TRANSFER_TOPIC`-match/exact-padded-address-equality/finalized-block-scanning pattern (NOT `escrow.mjs`, which contains no log-parsing code — corrects this spec's own prior false claim, resolves FIND-007) and applying `anicca-agent-spawn` REQ-401's general "independent re-verification, never self-report" principle. |
| REQ-103 (bookkeeping-only design constraint) | **Not code — a design constraint** | Verified by Phase 3 structural code read, not a runtime assertion (mirrors `anicca-agent-economy` REQ-203 / `anicca-agent-spawn` REQ-104). |
| REQ-107 (chain/asset scope constraint) | **Not code — a design constraint** | Verified structurally (mirrors `anicca-agent-spawn` REQ-106's honest single-scope precedent). |
| REQ-112 (single-coordinator-host scope constraint, this increment) | **Not code — a design constraint** | Verified structurally by a Phase 3 structural code read confirming no code path constructs a remote/networked lock or ledger path, AND confirming co-location eligibility is decided EXCLUSIVELY via `citizen.coLocatedWithCoordinator === true` (never `homeDir` equality, corrects the prior mechanism this revision, resolves FIND-305) — the DIRECT, by-name analog of `anicca-agent-spawn` REQ-106's own single-coordinator-host precondition, applied here to lending participants (lender AND borrower), not merely spawn evaluators. |
| REQ-113 (dependency-freshness process gate, before Phase 2a) | **Not code — a process/documentation gate** | Verified by a dated, written confirmation in this feature's own Phase 2a artifacts, not a runtime assertion; checked by the Phase 3 adversary as a precondition (resolves FIND-101, a direct recurrence of iteration-1's FIND-006). |

## Non-functional requirements

- **Performance**: every pure function (REQ-101/102/104/105/106/109) is O(n) over already-read ledger
  rows (n = this colony's own loan/citizen count, expected single digits to low hundreds for the
  foreseeable future) — no unbounded recursion, no network call inside a pure function.
- **Security / money-safety**: fail-closed everywhere (missing/malformed/non-finite input never
  defaults to "eligible" or "repaid"); private key material is NEVER written into `loans.jsonl` (only
  wallet ADDRESSES, matching `citizens.json`'s own `walletAddress`/`wallet` field-split discipline);
  every disbursement/repayment is independently re-verified on-chain, never trusted from either party's
  self-report (REQ-108); a crash — OR an in-process, non-crash exception from the SAME still-alive
  process (resolves this revision's own FIND-201) — strictly between an irreversible on-chain transfer
  and its own ledger record can never cause a double-disbursement or a permanently untracked transfer
  (REQ-106's two-phase provisional/follow-up record + on-chain reconciliation, now unified across the
  crash-recovery, in-process-exception, AND follow-up-append-itself-throws paths — the reconciliation
  trigger is driven purely by ledger STATE, never by lock staleness, resolves FIND-103, FIND-201, and
  FIND-301); a repayment `txHash`
  already credited anywhere in the ledger — same loan or a different one — can never be credited again,
  and a rejected replay is recorded ONLY out-of-band, never as a new `loans.jsonl` row
  (REQ-108's replay-rejection check, resolves FIND-202 and FIND-302); repayment-verification and default-detection
  writes to the SAME loan_id can never race past each other (REQ-108/109's shared per-loan lock, resolves
  FIND-104); a borrower can never hold two simultaneously-open loans from two DIFFERENT lenders (REQ-106's
  new per-borrower `loan_borrower_${borrowerId}` lock, resolves FIND-401); a citizen can never be both the
  lender AND the borrower of the SAME loan (REQ-102's condition (d), resolves FIND-402); a loan's own
  default-clock (`issued_ms`/`due_ms`) is drawn EXCLUSIVELY from the confirmed-disbursement `"active"` row,
  never the pre-transfer provisional row (REQ-106, resolves FIND-403); colony-wide loan-default risk is
  monitored by DOLLAR VALUE across ALL loan tiers, not merely the smallest cold-start tier, via TWO
  complementary, independently-sufficient signals — a dollar-weighted ratio AND an
  absolute-dollar-loss-within-a-rolling-window sum immune to volume dilution (REQ-114's
  `evaluateOverallDefaultKillSwitch`, operating ALONGSIDE REQ-105's cold-start-specific monitor, resolves
  this revision's own FIND-502 and this revision's own spec-review iteration-7 FIND-602), and BOTH
  kill-switches (REQ-105's and REQ-114's own) are re-verified a SECOND time inside REQ-106's own
  lock-protected fresh-check, never trusted from their own single, pre-lock evaluation alone (resolves this
  revision's own spec-review iteration-7 FIND-601); the money-safety invariant (REQ-111)
  is enforced structurally, not by runtime trust.

---

## Requirements

### REQ群A: 適格性ゲート（決定論、model判断なし）

### REQ-101: Lender eligibility & available-surplus computation
**EARS**: WHEN a citizen is considered as a potential lender for a specific loan, THE SYSTEM SHALL
admit it as an eligible lender only if `isSelfFunded()` (`~/anicca/skills/_shared/lib/is-self-funded.mjs`,
reused unmodified) returns `true` for that citizen's `{wallet, fuel, humanDependencies}` sub-object AND
its computed available-surplus is strictly greater than `0`, where available surplus is:

```
computeLenderAvailableUsd({
  lenderBalanceUsd, perCitizenReserveUsd = 5.00, outstandingPrincipalUsd, recentGojoGiftsUsd = 0
})
  = +(Math.max(0, lenderBalanceUsd - perCitizenReserveUsd - outstandingPrincipalUsd - recentGojoGiftsUsd)).toFixed(6)
```

Clamped via the SAME `.toFixed(6)` money-precision convention already established colony-wide
(`~/anicca/skills/economy/ubi/ubi.js::contribute()` line 40, `const raw = +(totalRealizedProfitUsd *
cfg.contributePct).toFixed(6)`; `~/anicca/skills/economy/gig/decide.mjs::decideGigAction()` line 44,
`const surplusUsdc = +(balanceUsdc - reserveUsdc).toFixed(6)`) — this is the SAME class of chained-
subtraction floating-point arithmetic that convention exists to protect (resolves this revision's own
FIND-206, which found every dollar-denominated function this feature introduces was previously specified
as unclamped).

`perCitizenReserveUsd` defaults to `5.00`, the SAME `RESERVE`/`perCitizenReserveUsd` constant already
established colony-wide (`economy/ubi/run.sh`'s `RESERVE=5.0`, `economy/gig/decide.mjs`'s
`DEFAULT_RESERVE_USDC=5.0`, `anicca-agent-spawn` REQ-101's `perCitizenReserveUsd`) — reused for internal
consistency, never a competing figure invented for this feature. `outstandingPrincipalUsd` is the sum,
over `loans.jsonl`'s own rows (reduced to one effective row per `loan_id` — the last-appended row, the
SAME "last-write-wins" reading convention `anicca-agent-spawn` REQ-101 already establishes for
`ledger.js`'s duplicate-`child_id` rows, computed by `sumOutstandingPrincipalUsd(loanRows, lenderId)`),
of `principal_usd - repaid_usd` for every row where `lender_id === lenderId` AND `status` is `"active"`
OR `"defaulted"` — a defaulted loan's unrecovered principal PERMANENTLY reduces that lender's own future
available surplus (it is a real, uncollected loss) until an explicit future write-off mechanism (not
built this increment) resolves it; a `"repaid"` row contributes `0`. **Each row's own `principal_usd -
repaid_usd` contribution is floored at `0` (`Math.max(0, ...)`) BEFORE summing across rows** — mirroring
this SAME spec's own `computeOverallDefaultRateUsd`/`computeRecentDefaultLossUsd` floor precedent
(REQ-114) — since REQ-104 fixes `total_due_usd = principal_usd * 1.10 > principal_usd` for every real
loan, an ordinary partial repayment on an `"active"` row whose cumulative `repaid_usd` has passed
`principal_usd` (but not yet `total_due_usd`) must never contribute a NEGATIVE amount that inflates
`computeLenderAvailableUsd`'s reported surplus above the lender's real exposure (resolves Phase 3
implementation-review sprint-1 FIND-902). `sumOutstandingPrincipalUsd`'s own summed result is likewise
clamped via `+(sum).toFixed(6)` — the SAME established money-precision convention (resolves FIND-206).

`recentGojoGiftsUsd` is a NEW, ONE-WAY, minimal awareness of `economy/ubi`'s already-existing "gojo"
mutual-aid mechanism (see Dependencies section), computed by
`sumRecentGojoGiftsUsd(gojoLogRows, nowMs, lookbackHours = 24, lenderId)` — a pure function, over
already-read rows of `~/anicca/skills/economy/ubi/state/gojo-log.jsonl` (READ-ONLY; this feature never
writes to it), GATED ON `lenderId` (resolves this revision's own FIND-102 — a real misattribution risk
the prior revision's prose acknowledged but never actually closed with a conditional rule): because
`gojo-log.jsonl`'s own row shape records NO explicit sender/lender identifier at all — the file's
physical location IS the sender, by `run.sh`'s current one-file-per-repo-copy convention, and `run.sh`
itself hardcodes the gojo sender identity to `anicca-a3cdd4` specifically (confirmed this revision,
`run.sh` lines 87-96: `me_bal = bal(telemetry_files['anicca-a3cdd4'])`) — this subtraction applies ONLY
when `lenderId === GOJO_SENDER_ID` (a new exported constant, `"anicca-a3cdd4"`, today's real, only gojo
sender). For ANY OTHER `lenderId`, `sumRecentGojoGiftsUsd` returns `0` UNCONDITIONALLY, regardless of
`gojoLogRows`' content — there is no possible gojo-gift history to subtract for a lender `gojo`'s own
current code has never sent from, so applying this subtraction to any other lender's available surplus
would be a real arithmetic misattribution, not conservatism. THE SYSTEM SHALL document this honestly as a
genuine limitation of `gojo`'s own current single-sender design — this feature cannot fully generalize
this subtraction to a colony with multiple real gojo senders without `ubi.js`/`run.sh` themselves
changing to record a sender field (out of scope this increment, the same direction already disclosed
below for the reverse case). WHEN `lenderId === GOJO_SENDER_ID`, the function sums each in-window row's
`decision.amount_usd` where `nowMs - Date.parse(row.ts) < lookbackHours * 3600 * 1000`; `lookbackHours`
defaults to `24`, reusing `ubi.js`'s own `DEFAULT_GOJO_CONFIG.rateLimitHours` figure rather than
inventing a second, competing window. A row is counted whenever `decision.amount_usd > 0`, REGARDLESS of
that row's own `executed` field — `economy/ubi/run.sh`'s current implementation always writes `executed:
false` at decision time (the actual transfer is a separate, later, manual `execute-ubi.py` step not yet
wired to update this log), so treating every PLANNED gift as already committed is a deliberate,
conservative (fail-closed) choice for `anicca-a3cdd4` specifically: it can only make THAT lender's
available surplus SMALLER than the truth, never larger, if some planned gifts are in fact never actually
sent. THE SYSTEM SHALL ALSO acknowledge, as an EXPLICIT, NOT-YET-SOLVED limitation of this increment (not
a silently-claimed bidirectional guarantee): `ubi.js`/`run.sh` themselves remain entirely unaware of
`loans.jsonl`'s own `outstandingPrincipalUsd` — a lender's own outstanding loan principal is NEVER
subtracted from `distributeAI`'s own surplus computation, so gojo can still double-count a citizen's own
committed loan principal as "available to gift." This feature does NOT modify `ubi.js`/`run.sh` to fix
that reverse direction — out of scope this increment, left to a future increment or explicit operator
action. `sumRecentGojoGiftsUsd`'s own summed result is likewise clamped via `+(sum).toFixed(6)` — the SAME
established money-precision convention this codebase already establishes for dollar arithmetic (resolves
FIND-206).

**Edge Cases**:
- A citizen fails `isSelfFunded()`: excluded as a lender candidate regardless of its raw balance
  magnitude (mirrors `anicca-agent-spawn` PROP-101b exactly).
- `lenderBalanceUsd` is missing/non-finite/negative (an RPC read failed): treated as `0` available
  surplus (fail-closed), never as "unknown but probably fine."
- A lender's `isSelfFunded()` status changes to `false` AFTER a loan was already disbursed (e.g. its
  fuel provider changes): THE SYSTEM SHALL NOT retroactively cancel or recall the already-disbursed
  loan — REQ-101's gate applies only at issuance time; a completed transfer is not unwound, mirroring
  `anicca-agent-spawn` REQ-402's own precedent that a later lifecycle-state change never retroactively
  voids an already-completed on-chain transfer.
- Two loans against the SAME lender are evaluated in the same wake: REQ-106's lock ensures only one
  disburses; REQ-101 itself is pure and may return `eligible` for both evaluations independently — it
  does not need to know about concurrency (mirrors `anicca-agent-spawn` REQ-102's identical edge case).
- A lender gave a gojo gift (`gojo-log.jsonl` row, `decision.amount_usd > 0`) within the lookback window,
  but the same dollar amount has NOT yet actually left its on-chain balance (because `run.sh` only PLANS,
  never executes, per the Dependencies section): `recentGojoGiftsUsd` still subtracts it (conservative,
  fail-closed) — this may make a lender look temporarily MORE constrained than its real on-chain balance
  strictly requires, which is the intentional, safer direction to err.
- `ubi.js`'s own `distributeAI` computation, run independently of this feature, is NOT told about this
  lender's own outstanding loan principal (`sumOutstandingPrincipalUsd`): THE SYSTEM SHALL NOT claim this
  is resolved — it is an acknowledged, one-way, not-yet-solved limitation (see above).
- A lender being evaluated is NOT `anicca-a3cdd4` (today's real, only gojo sender): `sumRecentGojoGiftsUsd`
  returns `0` unconditionally, regardless of `gojo-log.jsonl`'s own content — there is no gojo-gift
  history attributable to a lender `gojo`'s own code has never sent from (resolves FIND-102's
  misattribution risk).

**Acceptance Criteria**:
- `computeLenderAvailableUsd`, `sumOutstandingPrincipalUsd`, and `sumRecentGojoGiftsUsd` are pure, zero
  I/O, given already-fetched/already-read inputs, and each returns its result clamped via the established
  `.toFixed(6)` money-precision convention (resolves FIND-206) — every numeric assertion below is against
  that CLAMPED value.
- A lender with `balance=$8`, `reserve=$5`, `outstandingPrincipal=$1` → available `= max(0, 8-5-1) = $2`.
- A lender whose `isSelfFunded()` check is `false` contributes `0` available surplus regardless of
  balance.
- A lender with one `"defaulted"` loan whose principal was never repaid has that principal permanently
  subtracted from every future `computeLenderAvailableUsd` call until a future write-off mechanism
  changes it.
- A lender with `balance=$8`, `reserve=$5`, `outstandingPrincipal=$0`, and one `gojo-log.jsonl` row within
  the lookback window with `decision.amount_usd=$1` → available `= max(0, 8-5-0-1) = $2`.
- A `gojo-log.jsonl` row OUTSIDE the lookback window (`nowMs - Date.parse(row.ts) >= lookbackHours *
  3600000`) contributes `0` to `recentGojoGiftsUsd`, regardless of its `decision.amount_usd`.
- `sumRecentGojoGiftsUsd(gojoLogRows, nowMs, lookbackHours, lenderId)` returns `0` for ANY
  `lenderId !== GOJO_SENDER_ID` (`"anicca-a3cdd4"`), even when `gojoLogRows` contains an in-window row
  with `decision.amount_usd > 0` — this misattribution-prevention case is PROP-101f's own binding test
  (resolves FIND-102).

---

### REQ-102: Borrower eligibility
**EARS**: WHEN a citizen is considered as a potential borrower, THE SYSTEM SHALL admit it as eligible
only if ALL THREE hold: (a) `isSelfFunded()` returns `true` for that citizen's `{wallet, fuel,
humanDependencies}` sub-object; (b) its own current balance is strictly below `BORROWER_LOW_USD` — a NEW
constant this feature declares INDEPENDENTLY inside its own module (`lending-gate.mjs`, default `0.50`),
deliberately set to the SAME NUMERAL as `economy/gig/decide.mjs`'s existing `DEFAULT_LOW_USDC` for
DEFINITIONAL consistency (the SAME "genuinely broke" concept already established colony-wide, not a
second, competing DEFINITION) — but (resolves this revision's own FIND-106, which found this
paragraph's prior "reusing ... verbatim" wording directly contradicted REQ-110's own zero-coupling
requirement) via NO import and NO code coupling whatsoever: `BORROWER_LOW_USD` is declared, and only
ever read, from THIS feature's own module; nothing in this feature imports `DEFAULT_LOW_USDC` from
`decide.mjs`, and `decide.mjs` imports nothing from this feature (see REQ-110's own zero-coupling
acceptance criterion, which this constant's declaration must continue to satisfy — sharing a NUMERAL for
definitional consistency is not license to add an import); and (c) `loans.jsonl` contains NO row for that citizen (as `borrower_id`, reduced to its
last-appended-per-`loan_id` rows) whose `status` is `"active"` OR `"defaulted"` — i.e. the citizen has
ZERO currently-open loan obligations. Condition (c) is deliberately a single, simple "at most one
outstanding loan at a time" rule (not a separate "unpaid past a threshold" clock) — this is the
simplest rule that (i) prevents a citizen from stacking multiple simultaneous loans and (ii) makes a
default permanently block further borrowing until the defaulted row is explicitly resolved (REQ-109),
satisfying the "avoid serial defaulting" requirement without inventing a second timing mechanism beyond
REQ-104's own repayment window; and (d) `lenderId !== borrowerId` for the specific candidate loan under
evaluation — a citizen SHALL NEVER be evaluated as, or permitted to become, BOTH the lender AND the
borrower of the SAME loan (resolves this revision's own FIND-402 — closes a real self-loan exploit:
without this exclusion, a self-funded citizen could costlessly self-loan-and-repay itself — REQ-104's
smallest principal is `$0.02` plus `$0.002` interest, a trivial round-trip cost to a citizen paying
itself — to inflate its own `successfulOnTimeRepayments` count for free, defeating REQ-105's entire
cold-start risk-mitigation rationale (the reputation ladder is meant to reflect real, EXTERNAL
counterparty trust, never a fabricated self-dealt track record) and silently corrupting
`computeColdStartRepaymentRate`'s own kill-switch monitoring signal with manufactured "successful"
repayments that carried zero real counterparty risk). Condition (d) is evaluated FIRST, before (a)/(b)/(c)
and before REQ-101's own lender-availability computation ever runs for this candidate pair — a self-loan
candidate is rejected at zero cost, before any surplus arithmetic, any balance read, and any lock
acquisition (see REQ-106's own updated Acceptance Criteria below). Because self-loans are rejected
STRUCTURALLY at issuance, no self-dealt row can ever exist in `loans.jsonl` — REQ-105's
`computeColdStartRepaymentRate` therefore never needs its own separate self-loan-filtering logic; the
corrupting rows this finding describes simply can never be created.

**Edge Cases**:
- A candidate loan where `lenderId === borrowerId` (the SAME citizen evaluated as both lender and
  borrower of the same request): rejected under condition (d), regardless of that citizen's own balance,
  surplus, or repayment history — a self-loan is never eligible, structurally, not merely discouraged
  (resolves FIND-402).
- A citizen has an `"active"` (not yet due) loan in good standing: NOT eligible for a second loan until
  the first is `"repaid"` — this is intentional (mirrors `anicca-agent-spawn` REQ-102's
  `MAX_CONCURRENT_SPAWNS=1` single-in-flight discipline), not an oversight.
- A citizen's balance is exactly `$0.50` (the boundary): NOT eligible — the comparison is strict `<`,
  matching `decide.mjs`'s own strict-less-than convention for its identical constant.
- A citizen with a `"defaulted"` row that is LATER retroactively corrected to `"repaid"` (REQ-109's
  late-repayment edge case): becomes eligible again the moment that correction is appended — no
  separate manual unblock step exists.
- A brand-new citizen with NO rows at all in `loans.jsonl` (first-ever loan candidate): condition (c)
  is vacuously satisfied (no matching row at all) — this is the exact cold-start entry point REQ-105
  resolves.

**Acceptance Criteria**:
- `isBorrowerEligible({ borrowerAgent, loanRows, borrowerId, borrowerBalanceUsd, lenderId })` is pure,
  zero I/O, returns `{eligible: boolean, reason:
  "ok"|"self_loan"|"not_self_funded"|"not_broke_enough"|"outstanding_loan"}` — `lenderId` is a NEW
  parameter this revision adds (resolves FIND-402), required because condition (d)'s self-loan exclusion
  is inherently a fact about the SPECIFIC candidate lender+borrower PAIR, not about the borrower alone;
  condition (d) is checked FIRST, before (a)/(b)/(c), returning `reason:"self_loan"` immediately when
  `lenderId === borrowerId`, before any other condition is even evaluated.
- A fixture borrower with `balance=$0.49`, `isSelfFunded()=true`, zero loan rows, `lenderId !== borrowerId`
  → `eligible:true`.
- A fixture borrower with an `"active"` row for its own `borrower_id` → `eligible:false,
  reason:"outstanding_loan"`, regardless of how low its balance is.
- A fixture loan request where `lenderId === borrowerId` (a self-funded citizen requesting a loan from
  itself) is rejected with `eligible:false, reason:"self_loan"` BEFORE any lock is acquired or any surplus
  check runs — asserted even when that SAME citizen would otherwise pass conditions (a)/(b)/(c) (e.g. its
  own balance is genuinely below `BORROWER_LOW_USD` and it has zero outstanding loans) — proving the
  self-loan exclusion is checked first and independently of every other condition (new PROP-102e, resolves
  FIND-402).
- `BORROWER_LOW_USD` is declared as its own independent constant inside this feature's own module — a
  structural/Tier-0 check (shared with REQ-110's PROP-110a) confirms no import of `DEFAULT_LOW_USDC` from
  `economy/gig/decide.mjs` exists anywhere in this feature's diff, and no import of this feature's own
  `BORROWER_LOW_USD` exists inside `decide.mjs` (resolves FIND-106).

---

### REQ-103: Design-constraint requirement — bookkeeping only, never judgment
**EARS**: WHERE this increment decides lender/borrower eligibility (REQ-101/102), loan sizing
(REQ-104/105), or default status (REQ-109), THE SYSTEM SHALL implement each decision exclusively as
arithmetic and boolean logic over objective, already-known bookkeeping facts (balances, ledger rows,
elapsed time, a repayment COUNT) and SHALL NOT implement, alongside or instead of it, any model-driven
judgment about whether a specific loan is currently "a good idea," any heuristic creditworthiness
scoring beyond REQ-105's deterministic repayment-count ladder, or any steering text asking an LLM to
choose the principal/rate/window at runtime. This is the SAME design principle already established and
adversary-verified for `anicca-agent-economy` REQ-203 and `anicca-agent-spawn` REQ-104, and is
consistent with this project's own hard rule
(`~/.claude/rules/building-effective-ai-agents.md` #1/#2: deterministic code owns arithmetic/
bookkeeping; the agent owns genuine decisions).

What the agent DOES still decide, entirely inside this deterministic envelope (mirroring
`anicca-agent-spawn` REQ-104's identical HYBRID carve-out): *when* (within an eligible wake) to actually
originate or accept a specific loan, and what free-text note/reason to attach to the ledger row for its
own record-keeping. REQ-103 governs only the eligibility/sizing/default ARITHMETIC, never the agent's
own in-envelope timing choice.

**Edge Cases**:
- A future change makes `BORROWER_LOW_USD`/`FIRST_LOAN_USD`/`LOAN_INTEREST_RATE` computed by an LLM
  call ("ask the model whether $0.50 is broke enough"): rejected in review, however well-intentioned,
  exactly as `anicca-agent-economy` REQ-203 rejects a "recommended slot" field.
- Not independently unit-testable in the normal sense; verified via structural code review at Phase 3
  (grep/read for any LLM call, prompt template, or scoring logic inside
  `computeLenderAvailableUsd`/`isBorrowerEligible`/`computeLoanCapUsd`/`detectDefaultedLoans`).

**Acceptance Criteria**:
- The five named functions' source contains no network call, no prompt string, and no reference to any
  LLM/inference client.
- Their return types carry no free-text "explanation"/"recommendation" field beyond the fixed `reason`
  enum each function already specifies.

---

### REQ群B: Loan terms + cold-start reputation ladder

### REQ-104: Loan terms — fixed, small, conservative (v1, no variable market)
**EARS**: WHEN a loan is issued, THE SYSTEM SHALL apply exactly the following fixed constants — no
variable-amount/variable-rate market is built this increment (deliberately, per "no premature
complexity" and this project's own anti-slop bias):
- `FIRST_LOAN_USD = 0.02` — NOT claimed as a proven repayment-capacity figure (see REQ-105's honest
  reframing below, which corrects this spec's own prior overclaim). It is reused because it is the
  smallest concrete USDC amount this codebase has ever PROVEN can move value meaningfully end-to-end in
  this exact economy: SPEC.md §9.9's own real gig #3 (`bountyUsdcBase: 20000` = 0.02 USDC) proved a
  completed gig TAKE can be rewarded at this scale (Franklin#1, the TAKER, received it). That precedent
  proves "$0.02 is a real, settleable unit in this system" — it does NOT prove "$0.02 is enough for a
  BORROWER to earn its way to repayment," a different claim REQ-105 addresses honestly, as an
  experimental hypothesis, not a proven fact.
- `LOAN_INTEREST_RATE = 0.10` (10%, fixed simple interest on principal, never compounding, never
  annualized/variable) — a deliberately chosen, conservative, easily-tunable STARTING parameter for this
  increment, NOT derived from any existing mechanism (correcting this spec's own prior claim that it
  reused `economy/ubi/ubi.js`'s `DEFAULT_CONTRIBUTE_CONFIG.contributePct = 0.10`: that figure governs a
  profit-tithe rate on already-realized, already-safe profit — a voluntary "how much of my own upside do
  I share" decision — which has no bearing on pricing THIS mechanism's real default risk on a fully
  uncollateralized advance to a borrower with, at the cold-start rung, zero track record; the two figures
  share a numeral, not a justification). `10%` is explicitly open to revision once real repayment-rate
  data exists (see REQ-105's monitoring plan below) — it is a starting point, not a claimed-optimal price.
- `LOAN_REPAYMENT_WINDOW_DAYS = 14` — reused from `anicca-agent-spawn`'s own `SPAWN_COOLDOWN_DAYS`/
  `BOOTSTRAP_WINDOW_DAYS` default (both `14`) — a new/broke citizen needs roughly this long to complete
  its own first gig-settlement cycle (REQ-401 of that same feature), so a loan's repayment window is set
  to the SAME already-established colony timescale rather than an unrelated new number.
- `total_due_usd = +(principal_usd * (1 + LOAN_INTEREST_RATE)).toFixed(6)` — simple interest, computed
  once at issuance, never recalculated, clamped via the SAME established `.toFixed(6)` money-precision
  convention this codebase already uses for dollar arithmetic (`ubi.js::contribute()` line 40,
  `decide.mjs::decideGigAction()` line 44) — never an unclamped floating-point multiplication (resolves
  this revision's own FIND-206).

**Edge Cases**:
- A loan's principal is anything other than the exact value REQ-105's ladder computes for that
  borrower at issuance time: rejected — this feature never accepts an arbitrary "requested amount"
  from a borrower; the amount is always the deterministic ladder output, not a free choice (closes the
  "variable-amount market" door structurally, not just by convention).
- Interest is computed once, at issuance, on the ORIGINAL principal only — a late (post-window)
  repayment (REQ-109's edge case) does NOT accrue additional interest beyond `total_due_usd` computed
  at issuance (v1 deliberately has no penalty-interest mechanism; a late repayment is a bookkeeping/
  reputation fact, REQ-105, not an additional monetary charge).
- Partial repayment (cumulative `repaid_usd < total_due_usd`) does not close the loan — see REQ-108.

**Acceptance Criteria**:
- `total_due_usd` for `FIRST_LOAN_USD` = `+(0.02 * 1.10).toFixed(6) = 0.022` — the assertion is against
  the CLAMPED value (resolves FIND-206), consistent across every Acceptance Criterion this feature states
  for a money-denominated formula.
- A structural/Tier-0 check confirms no code path in this feature accepts a borrower- or lender-supplied
  principal/rate/window value that overrides these fixed constants (except REQ-105's ladder OUTPUT,
  itself fully deterministic from bookkeeping inputs).

---

### REQ-105: Reputation-capital sizing ladder (resolves the cold-start problem)
**EARS**: WHEN REQ-102 admits a borrower as eligible, THE SYSTEM SHALL size that specific loan's
principal deterministically from the borrower's OWN prior repayment history — reusing this colony's
OWN existing track-record data (this feature's own `loans.jsonl` rows) as the "reputation" input,
exactly the cold-start gap arXiv 2602.14219 §4.2.2 identifies but never resolves:

```
computeLoanCapUsd({ successfulOnTimeRepayments, firstLoanUsd = 0.02, maxLoanUsd = 5.00 })
  = +(Math.min(maxLoanUsd, firstLoanUsd * (2 ** successfulOnTimeRepayments))).toFixed(6)
```

Clamped via the SAME established `.toFixed(6)` money-precision convention as `computeLenderAvailableUsd`
above (resolves FIND-206).

`successfulOnTimeRepayments` = `countSuccessfulOnTimeRepayments(loanRows, borrowerId)`, a pure count
(zero I/O) of that borrower's own `loans.jsonl` rows (reduced to one effective row per `loan_id`,
last-write-wins) where `status === "repaid"` AND `on_time === true` (set at repayment time, REQ-108: the
qualifying repayment transaction landed at or before `due_ms`). A borrower with ZERO prior loans
(`successfulOnTimeRepayments = 0`) gets `computeLoanCapUsd(...) = firstLoanUsd = 0.02` — the formula
naturally produces `FIRST_LOAN_USD` with zero special-casing.

**What this ladder actually resolves, stated honestly (corrects this spec's own prior overclaim):** the
SIZING half of arXiv 2602.14219 §4.2.2's cold-start gap IS genuinely resolved — a brand-new citizen with
zero track record requires literally zero collateral, zero external credit-score oracle, and zero
hand-waved "trust the agent" assumption to receive a FIRST loan, and that first loan is bounded to the
SAME trivial scale as the real P2 genesis event, so the LENDER's own DOWNSIDE (how much it can lose if
this specific borrower defaults) is structurally tiny by construction. This spec does NOT, and must not
be read to, claim the ECONOMIC half is resolved — i.e. it does NOT claim `$0.02` is proven sufficient for
a borrower to actually GENERATE repayment capacity. SPEC.md §9.9's own real gig #3 proves $0.02 can rescue
a bounty TAKER (the party who RECEIVES the payout for completed work) — it says nothing about a borrower
who has SPENT $0.02 and must now earn `$0.022` back within `LOAN_REPAYMENT_WINDOW_DAYS`. This feature
therefore specifies the cold-start loan's INTENDED use explicitly, rather than leaving it implicit:
covering the borrower's own first small on-chain action that lets it complete ONE self-directed EARNING
event — e.g. its own gas/tx cost to ACCEPT a gig it did NOT post (a `gigTake`/`gigDeliver` path, where the
borrower is the party who gets PAID), or a tiny trade — NOT funding a bounty the borrower itself POSTS
(which spends capital rather than earning it, exactly as REQ-110's own gig-coexistence framing already
distinguishes poster from taker). This feature does NOT enforce this intended use structurally (REQ-110
already disclaims tracking loan-proceeds provenance) — it is stated here as the DESIGN INTENT a borrower
should be told about, not a runtime-checked constraint.

**Monitoring plan (this increment's cold-start design is an EXPERIMENTAL HYPOTHESIS, not a proven
solution):** THE SYSTEM SHALL make it possible to track, at any time, the actual repayment outcome rate of
cold-start loans via a new pure function, `computeColdStartRepaymentRate({ loanRows, n = 20 })` — over the
first `n` (by `issued_ms` ascending — the `"active"` row's own append-time timestamp, per REQ-106's
precise definition, resolves this revision's own FIND-403 — across ALL borrowers colony-wide) loans whose
ORIGINATING row had `successfulOnTimeRepayments === 0` AT ISSUANCE TIME — full stop, this is the exact and
ONLY definition (corrects this revision's own prior false parenthetical claim, resolves this revision's
own FIND-107):
**a "cold-start loan" is NOT equivalent to "a borrower's own first-ever loan."** Because REQ-102's
condition (d) (this revision, resolves FIND-402) structurally forbids `lenderId === borrowerId` at
issuance, this sample can also never include a self-dealt loan — no self-loan row can ever exist in
`loans.jsonl` for it to count. Per this SAME
requirement's own Edge Cases below, a late-but-eventually-repaid loan does NOT increment
`successfulOnTimeRepayments`; combined with REQ-102's own "at most one outstanding loan at a time" rule, a
borrower whose FIRST loan was repaid LATE still has `successfulOnTimeRepayments = 0` when their SECOND
loan is issued — so that borrower's SECOND loan is ALSO, correctly, a cold-start loan by this same
definition. Cold-start loans CAN and DO recur for a chronically-late-but-eventually-repaying borrower
(their third, fourth, etc. loan may ALSO qualify, for as long as every prior repayment landed late) — this
is INTENTIONAL and ACCEPTABLE, not a bug to be special-cased away: the monitoring metric exists to measure
repayment behavior AT THE ZERO-REPUTATION CAP specifically, regardless of which numbered loan attempt
produced that zero, so counting a genuine repeat cold-start loan is measuring exactly what this metric is
FOR. `successfulOnTimeRepayments === 0` at issuance is NOT a new, separately-stored field on each row —
it IS `countSuccessfulOnTimeRepayments`'s own already-specified per-borrower count (above), RE-DERIVED,
for EACH loan in the candidate set, over that SAME borrower's own PRIOR rows only (rows with `issued_ms`
strictly less than the loan under consideration, for that SAME `borrower_id`): `computeColdStartRepaymentRate`
therefore groups `loanRows` by `borrower_id`, walks each borrower's own history in `issued_ms` order, and
includes a loan in the cold-start candidate set exactly when re-deriving `countSuccessfulOnTimeRepayments`
over that borrower's own strictly-earlier rows yields `0` — this recomputation, not a stored snapshot
field, is the function's own actual algorithm (no new schema field is added to `loans.jsonl`). It returns
`{ sampleSize, repaidCount, defaultedCount, pendingCount, rate }` where `rate = repaidCount / sampleSize`
(or `null` if `sampleSize === 0`, never divide-by-zero). If, once a meaningful sample exists, this rate is
empirically LOW (most cold-start loans default), THAT is the honest signal this increment's `$0.02`
hypothesis needs revision — a future increment's job, not something this spec papers over as already
solved.

**Concrete kill-switch threshold (grounded in the closest available real-world analog, not an arbitrary
guess):** no real precedent exists for AI-agent-to-AI-agent lending anywhere (searched 2026-07-07 —
Maple/Goldfinch/TrueFi/Cred Protocol never publish tier-specific default rates for their lowest-trust
segment; Kiva/Grameen's 95-98% repayment figures are aggregate and selection-biased, not first-time-
borrower-specific). The closest real, tier-isolated data found is the U.S. Federal Reserve's Q1 2024
credit-builder-product study (FEDS Notes, 2024-12-06): secured-card/credit-builder-loan holders — 93% of
whom are unscored or nonprime, the closest human analog to a zero-reputation new colony citizen — show a
combined delinquency rate of 10.2% (repayment ≈ 89-90%). THE SYSTEM SHALL treat a `computeColdStartRepaymentRate`
result below `0.80` (once `sampleSize >= 10`) as a hard signal to PAUSE new cold-start (`successfulOnTimeRepayments
=== 0`) loan issuance pending a design review — deliberately set below the 89-90% human analog to account for
the unverified assumption that an AI agent has repayment incentives comparable to a human borrower's social/
credit-score incentives (a limitation this spec does not claim is resolved). While `sampleSize < 10`, ANY single
default is itself the review trigger — do not wait for a statistically-sized sample before raising a flag.

**Kill-switch enforcement mechanism (resolves this revision's own FIND-203 — a real contradiction with
this SAME requirement's own pre-existing Edge Case below, and a zero-backing-proof-obligation gap):** THE
SYSTEM SHALL implement the pause decision above as a new, pure, zero-I/O function,
`evaluateColdStartKillSwitch({ sampleSize, rate, defaultedCount }) → { paused: boolean, reason: string }`,
fed directly by `computeColdStartRepaymentRate`'s own already-specified output (computed over the SAME
`loanRows` already read for this evaluation, `n` defaulting to `20` as already specified): `paused = true`
when EITHER `(sampleSize >= 10 AND rate < 0.80)` OR `(sampleSize < 10 AND defaultedCount >= 1)` —
otherwise `paused = false`. Loan issuance (REQ-106) SHALL call this function, BEFORE acquiring the
`` `loan_${lenderId}` `` lock (the SAME "pure, read-only eligibility check runs before the effectful
critical section" discipline REQ-101/102 already establish), for ANY loan request where the borrower's
OWN `successfulOnTimeRepayments === 0` at issuance (i.e. a genuine cold-start loan, per this requirement's
own definition above) — an established borrower's non-cold-start renewal loan is NEVER paused by this
mechanism, since the kill-switch's entire purpose is to gate the SPECIFIC hypothesis this requirement's
own sizing ladder is testing (zero-reputation issuance), not lending in general. WHEN
`evaluateColdStartKillSwitch` returns `paused: true`, THE SYSTEM SHALL refuse to issue that specific loan
(`reason: "cold_start_paused"`, no disbursement attempted, no `loans.jsonl` row appended, mirroring
REQ-102's own existing fail-closed refusal shape) — this is the concrete, testable implementation of the
"PAUSE new cold-start... loan issuance" SHALL above, closing the zero-backing-proof-obligation gap this
revision's own FIND-203 identified.

`FIRST_LOAN_USD` is, in summary, the smallest concrete unit this codebase has PROVEN can move
value meaningfully in this economy, used here as a starting hypothesis for cold-start lending — not a
proven answer to whether cold-start lending works economically. `maxLoanUsd` defaults to `5.00` — the SAME
order-of-magnitude anchor (`perCitizenReserveUsd`/`DEFAULT_RESERVE_USDC`/`MIN_SHELTER_USD`, all `5.00`
colony-wide) reused deliberately, not coincidentally, for internal consistency and to keep even a
well-established borrower's loan "small" per this increment's own scope.

**Edge Cases**:
- A late-but-eventual full repayment (REQ-109: `on_time=false`) does NOT increment
  `successfulOnTimeRepayments` — the borrower's next loan cap stays exactly where it already was (no
  growth, but also no regression/penalty beyond that).
- A borrower's SECOND (or later) loan is ALSO a cold-start loan under `computeColdStartRepaymentRate`'s
  own definition, because every one of that borrower's PRIOR loans was repaid late (`on_time: false`):
  correctly included in the cold-start sample a second (or further) time — `computeColdStartRepaymentRate`
  does NOT deduplicate by `borrower_id`, and this is intentional (resolves FIND-107's false
  first-ever-loan equivalence).
- The doubling ladder would overshoot `maxLoanUsd` (e.g. `0.02 * 2^8 = 5.12`): capped at `5.00` exactly
  — `Math.min` never lets the loan amount exceed the ceiling.
- A borrower has a mix of on-time and late repayments across its history: only ON-TIME ones count
  toward `successfulOnTimeRepayments` — a late repayment neither subtracts from nor is ignored entirely;
  it simply does not ADD.
- `successfulOnTimeRepayments` is somehow negative/non-integer (malformed input): treated as `0` (the
  cold-start floor), fail-closed — never a larger, unearned cap.
- `computeColdStartRepaymentRate`'s sample is small (e.g. `sampleSize < 10`): `computeColdStartRepaymentRate`
  itself still ALWAYS returns the exact count/rate regardless of sample size — it NEVER hides, refuses to
  compute, or otherwise withholds the number merely because the sample is small (this part of the original
  framing was correct and remains unchanged). **Corrected this revision (resolves this revision's own
  FIND-203, a direct contradiction with the kill-switch paragraph above):** this spec DOES attach a binding
  decision rule to that number, stated in full above — once `sampleSize >= 10`, a `rate` below `0.80` is
  the defined pause signal; while `sampleSize < 10`, ANY single default is itself the pause signal
  (`evaluateColdStartKillSwitch`, above). This is no longer left to a human or a future increment to
  interpret — it is THIS increment's own binding kill-switch rule, enforced by `evaluateColdStartKillSwitch`
  before any NEW cold-start loan is issued.

**Acceptance Criteria**:
- `computeLoanCapUsd({successfulOnTimeRepayments: 0}) === 0.02` (exact cold-start SIZING resolution case
  — this is what is proven; see the honest reframing above for what is NOT claimed proven).
- `computeLoanCapUsd({successfulOnTimeRepayments: 1}) === 0.04`,
  `computeLoanCapUsd({successfulOnTimeRepayments: 7}) === 2.56`,
  `computeLoanCapUsd({successfulOnTimeRepayments: 8}) === 5.00` (capped, not `5.12`) — every assertion
  above is against `computeLoanCapUsd`'s own `.toFixed(6)`-clamped return value (resolves FIND-206).
- `countSuccessfulOnTimeRepayments` is pure, zero I/O, and excludes any `on_time:false` or
  non-`"repaid"` row from its count.
- `decideLoan({ lenderAvailableUsd, loanAmountUsd })` (pure) returns `eligible:true` only when
  `lenderAvailableUsd >= loanAmountUsd`, where `loanAmountUsd` is ALWAYS `computeLoanCapUsd`'s own
  output for that borrower — never an independently-supplied number.
- `computeColdStartRepaymentRate` is pure, zero I/O, never divides by zero, and a fixture with 3 repaid +
  1 defaulted + 1 still-active cold-start loan returns `{sampleSize:5, repaidCount:3, defaultedCount:1,
  pendingCount:1, rate:0.6}`.
- A SEPARATE fixture proves recurrence is correctly counted: a single borrower whose first loan is repaid
  late (`on_time:false`) followed by that SAME borrower's second loan (issued while
  `successfulOnTimeRepayments` is still `0`) both appear in the cold-start candidate set — asserting
  `computeColdStartRepaymentRate` does NOT treat "cold-start" as synonymous with "first-ever loan"
  (resolves FIND-107).
- `evaluateColdStartKillSwitch({sampleSize:10, rate:0.7, defaultedCount:3}) === {paused:true}` — a
  below-threshold rate at a statistically-sized sample triggers the pause.
- `evaluateColdStartKillSwitch({sampleSize:3, rate:0.667, defaultedCount:1}) === {paused:true}` — a SINGLE
  default while `sampleSize<10` triggers the SAME pause, even though the raw rate (`0.667`) is itself above
  `0.80`'s own threshold, per the small-sample rule.
- `evaluateColdStartKillSwitch({sampleSize:15, rate:0.87, defaultedCount:2}) === {paused:false}` — a
  healthy rate at a statistically-sized sample does NOT pause issuance.
- A fixture wiring `evaluateColdStartKillSwitch`'s `paused:true` output into a MOCKED REQ-106 issuance step
  confirms a NEW cold-start loan request (`successfulOnTimeRepayments===0`) is refused
  (`reason:"cold_start_paused"`, zero disbursement, zero `loans.jsonl` append) — while a concurrent,
  non-cold-start renewal loan for an established borrower is UNAFFECTED by the same paused state (new
  PROP-105g, resolves FIND-203). **This mocked-caller fixture proves the FUNCTION and the WIRING PATTERN
  are correct — it does NOT, by itself, prove the REAL, production REQ-106 issuance code actually calls
  this function; see REQ-106's own separate Tier-0 structural check (PROP-105h, resolves FIND-303) for
  that real-code confirmation.**

---

### REQ-114: Colony-wide default-rate monitoring — ALL loan tiers, dollar-weighted (bust-out /
reputation-laundering defense, resolves this revision's own spec-review iteration-6 FIND-502)
**EARS**: WHERE REQ-105's `computeColdStartRepaymentRate`/`evaluateColdStartKillSwitch` monitor risk
EXCLUSIVELY for loans issued at `successfulOnTimeRepayments === 0` (by that requirement's own definition,
the smallest, `$0.02`-tier loans) and are therefore STRUCTURALLY BLIND to a default on any LARGER loan an
established borrower has grown into via REQ-105's own doubling ladder (up to `maxLoanUsd = 5.00`, 250x the
cold-start size), THE SYSTEM SHALL ADDITIONALLY track default risk across the FULL loan population, ALL
tiers, weighted by DOLLAR VALUE at risk (never merely loan COUNT), via a SECOND, general-purpose, pure
function, `computeOverallDefaultRateUsd({ loanRows }) → { totalIssuedUsd, totalDefaultedUsd, defaultRateUsd,
sampleSize }`, operating ALONGSIDE — never replacing — REQ-105's own cold-start-specific monitor.

**Why a count-based metric alone is insufficient here (the concrete bust-out/reputation-laundering pattern
this requirement closes):** REQ-105's own `successfulOnTimeRepayments` count is COLONY-WIDE, not
lender-specific — a borrower's track record built against ONE lender is fully portable to any OTHER,
unrelated lender's own sizing decision (REQ-105's ladder input is simply
`countSuccessfulOnTimeRepayments(loanRows, borrowerId)`, with no lender-pairing restriction anywhere in
REQ-101/102/105). A borrower (or a colluding pair) can therefore cheaply build a strong track record via a
sequence of small, low-risk, successfully-repaid cold-start-tier loans, then strategically default on the
SINGLE largest loan its now-inflated reputation qualifies it for from a DIFFERENT, unsuspecting lender who
has never transacted with it before — and this specific default event is, by construction, invisible to
`computeColdStartRepaymentRate`'s own sample (that borrower's `successfulOnTimeRepayments` is no longer `0`
at issuance of the LARGE loan, so it is structurally excluded from the cold-start candidate set REQ-105
monitors). A pure loan-COUNT default rate would also under-weight this risk (one large default among many
small, healthy loans looks numerically small by count even though it may represent the LARGEST single
dollar loss any lender in this colony has suffered) — this is why `computeOverallDefaultRateUsd` is
explicitly DOLLAR-weighted, never count-weighted.

**A SECOND, DIFFERENT dilution failure mode the dollar-weighted ratio ALONE does not close (resolves this
revision's own spec-review iteration-7 FIND-602): dilution by loan VOLUME, not merely loan COUNT.** The
dollar-weighting above correctly stops a naive COUNT-based ratio from under-weighting one large default
among many small loans (the paragraph above). It does NOT, by itself, stop a DIFFERENT failure mode: once
`sampleSize >= 10`, `defaultRateUsd = totalDefaultedUsd / totalIssuedUsd` can ALSO be diluted below the
`0.20` pause threshold by a large VOLUME of OTHER, unrelated, HEALTHY large (established-tier,
`$0.04`-`$5.00`) loans that happen to reach a terminal `"repaid"` state around the same time as the genuine
bust-out default this requirement exists to catch — a colony with, say, 9 healthy `$5.00` established-tier
repayments plus exactly ONE `$5.00` bust-out default yields `totalIssuedUsd=$50`, `totalDefaultedUsd=$5.00`,
`defaultRateUsd=0.10` — BELOW `0.20`, so `paused:false`, even though the EXACT single-largest-loan default
this requirement's own rationale (above) describes just occurred. This is precisely the state a MATURING
colony (the whole point of REQ-105's own doubling ladder) will eventually reach, so this failure mode is not
a remote edge case — it is the colony's own expected long-run trajectory. THE SYSTEM SHALL THEREFORE track a
SECOND, complementary signal, ALONGSIDE (never replacing) the dollar-weighted RATIO below: an ABSOLUTE
dollar-loss sum within a rolling window, via a NEW pure function,

```
computeRecentDefaultLossUsd({ loanRows, nowMs, windowDays = RECENT_DEFAULT_LOSS_WINDOW_DAYS })
  → { totalRecentDefaultLossUsd, windowDays }
```

Definition: `loanRows` is reduced to one effective row per `loan_id` (last-write-wins, the SAME reduction
convention this document already establishes throughout). `totalRecentDefaultLossUsd` is the sum, over
every row whose LAST-appended status is `"defaulted"` AND whose own `defaulted_ms` field (a NEW field this
revision adds to the `"defaulted"` row, REQ-109 — the wall-clock time at the moment THAT row itself is
appended, mirroring REQ-106's own `issued_ms`-precision convention exactly — see REQ-109's own separate
Tier-0 structural check, PROP-109g, resolves this revision's own spec-review iteration-8 FIND-702,
confirming the REAL, production append code, not merely this prose definition, actually sets this field)
satisfies `nowMs - defaulted_ms
< windowDays * 86400000`, of `principal_usd - repaid_usd` (the SAME unrecovered-loss quantity
`totalDefaultedUsd`/`outstandingDefaultedDebtUsd` already compute elsewhere in this document) for that
row — clamped via the SAME established `.toFixed(6)` money-precision convention. Because this is an
ABSOLUTE SUM, never a ratio, it CANNOT be diluted by any volume of OTHER, unrelated, healthy loan
activity — a `$5.00` bust-out default contributes exactly `$5.00` to this sum regardless of how many OTHER
large loans also happen to be healthy and terminal in the SAME window. A `"defaulted"` row LATER
retroactively corrected to `"repaid"` (REQ-109's own late-repayment edge case) is naturally excluded from
this sum the moment that correction is appended — the last-write-wins reduction means its own last-appended
row is no longer `"defaulted"` at all. Malformed/negative/non-finite `principal_usd`/`repaid_usd`/
`defaulted_ms` on any row contributes `0` to the sum for that specific row (fail-closed, mirroring this
requirement's own existing convention for `computeOverallDefaultRateUsd`).

**Threshold and window, honestly grounded (resolves this revision's own FIND-602 — reuses THIS document's
own existing order-of-magnitude anchors rather than inventing new, unrelated numbers):**
`RECENT_DEFAULT_LOSS_THRESHOLD_USD` defaults to `5.00` — the SAME `maxLoanUsd`/`perCitizenReserveUsd`/
`DEFAULT_RESERVE_USDC`/`MIN_SHELTER_USD` `$5.00` order-of-magnitude anchor this document ALREADY reuses
deliberately, colony-wide, for internal consistency (REQ-101/105) — chosen here specifically so that ONE
single bust-out default at REQ-105's own maximum possible loan size (`maxLoanUsd = $5.00`) is, BY ITSELF,
already sufficient to trip this signal regardless of any OTHER healthy loan volume the ratio below can be
diluted by — this is the EXACT scenario this requirement's own rationale (above) describes, made trip-safe
against volume dilution by construction. `RECENT_DEFAULT_LOSS_WINDOW_DAYS` defaults to `14` — the SAME
`LOAN_REPAYMENT_WINDOW_DAYS` colony timescale REQ-104 already establishes and reuses (rather than inventing
a second, competing window figure) — a bust-out default landing anywhere within roughly one full
loan-repayment cycle is within this signal's own lookback. **THE SYSTEM SHALL document this honestly as an
unvalidated placeholder, exactly as REQ-105's own kill-switch threshold and this SAME requirement's own
`0.20` ratio threshold already are:** no real-world precedent for an absolute-dollar-loss-within-a-rolling-
window signal, specifically for AI-agent-to-AI-agent lending, was found in this session's search (the SAME
search that grounded REQ-105's/this requirement's own ratio threshold, below, found no tier-specific OR
absolute-dollar precedent either) — `$5.00`/`14 days` is a conservative starting point grounded in THIS
document's own existing order-of-magnitude anchors, open to revision once real colony-native default data
accumulates, never presented as an independently-validated figure.

```
computeOverallDefaultRateUsd({ loanRows })
  → { totalIssuedUsd, totalDefaultedUsd, defaultRateUsd, sampleSize }
```

Definition, precisely stated: `loanRows` is reduced to one effective row per `loan_id` (last-write-wins,
the SAME reduction convention this document already establishes throughout — REQ-101's
`sumOutstandingPrincipalUsd`, REQ-105's own count functions, REQ-109's `outstandingDefaultedDebtUsd`).
`sampleSize` = the count of loans, colony-wide, ALL tiers, whose last-appended row's `status` is a
TERMINAL outcome — `"repaid"` OR `"defaulted"` — never a loan still
`"active"`/`"provisioning"`/`"disbursement_failed"`/`"disbursement_uncertain"` (an unresolved loan is
neither a success nor a loss yet, and including it in either direction would misrepresent the metric).
`totalIssuedUsd` = the sum of `principal_usd` over every one of those TERMINAL rows (repaid + defaulted
combined — the total dollar volume that has reached a final outcome). `totalDefaultedUsd` = the sum of
`principal_usd - repaid_usd` (the actual unrecovered dollar loss — the SAME `outstandingDefaultedDebtUsd`
quantity REQ-109 already computes per-citizen, here summed colony-wide across ALL defaulted rows regardless
of tier or borrower) over every `"defaulted"` row. `defaultRateUsd = totalDefaultedUsd / totalIssuedUsd`
(or `null` if `totalIssuedUsd === 0`, never a divide-by-zero throw — mirroring
`computeColdStartRepaymentRate`'s own identical convention). Every dollar figure is clamped via the SAME
established `.toFixed(6)` money-precision convention this document already uses throughout (the SAME
FIND-206 discipline, applied consistently to this NEW function too).

**Kill-switch enforcement (mirrors REQ-105's own `evaluateColdStartKillSwitch` shape, applied here to the
dollar-weighted, all-tier metric — EXTENDED this revision, resolves FIND-602, to be fed by BOTH signals
above):** THE SYSTEM SHALL implement a SECOND, pure, zero-I/O function,
`evaluateOverallDefaultKillSwitch({ totalIssuedUsd, totalDefaultedUsd, defaultRateUsd, sampleSize,
totalRecentDefaultLossUsd }) → { paused: boolean, reason: string }`: `paused = true` when ANY of THREE
conditions hold — `(sampleSize >= 10 AND defaultRateUsd > 0.20)`, OR `(sampleSize < 10 AND
totalDefaultedUsd > 0)`, OR (NEW this revision) `(totalRecentDefaultLossUsd >= RECENT_DEFAULT_LOSS_THRESHOLD_USD)`
— otherwise `paused = false`. The third condition's comparison is corrected this revision from a strict `>`
to `>=` (resolves this revision's own spec-review iteration-8 FIND-701 — the prior strict `>` made a single
bust-out default landing EXACTLY at REQ-105's own `maxLoanUsd = $5.00` ceiling unable to trip this signal by
itself, contradicting this SAME requirement's own worked edge case below and PROP-114f's own fixture,
neither of which needed to change). The THIRD condition is deliberately independent of `sampleSize` entirely (it
is an ABSOLUTE dollar sum, immune to volume dilution by construction, per the paragraph above) — EITHER the
ratio-based signal OR the NEW absolute-loss signal alone is sufficient grounds to pause; `reason` reports
which signal tripped (`"ratio_threshold_exceeded"`, `"small_sample_default"`, or
`"recent_default_loss_threshold_exceeded"` — implementation-defined tie-break if more than one applies
simultaneously, mirroring the existing tie-break rule below). Loan issuance
(REQ-106) SHALL call THIS function, IN ADDITION TO (never instead of) `evaluateColdStartKillSwitch`, for
EVERY loan request regardless of tier — BEFORE acquiring the `` `loan_${lenderId}` `` lock, the SAME "pure,
read-only eligibility check runs before the effectful critical section" discipline REQ-101/102/105 already
establish — and SHALL, for this call, ALSO compute `computeRecentDefaultLossUsd({loanRows, nowMs})` (above)
and pass its `totalRecentDefaultLossUsd` into `evaluateOverallDefaultKillSwitch` alongside
`computeOverallDefaultRateUsd`'s own existing outputs, never omitting the new signal's input. WHEN
`evaluateOverallDefaultKillSwitch` returns `paused: true` (for ANY of the three internal reasons above), THE
SYSTEM SHALL refuse to issue ANY new loan (`reason: "overall_default_paused"` at REQ-106's own
issuance-refusal level — the SAME single external reason string regardless of WHICH of the three internal
conditions tripped it, since REQ-106's own refusal shape does not need to distinguish them; the internal,
finer-grained `reason` above is `evaluateOverallDefaultKillSwitch`'s own diagnostic return value only, no
disbursement attempted, no `loans.jsonl` row appended)
— regardless of whether the specific request under evaluation is itself a cold-start loan or an
established-borrower renewal, since a colony-wide dollar-loss signal this severe is a systemic
risk-mitigation trigger, not a tier-specific one. If BOTH kill-switches (REQ-105's cold-start switch AND
THIS requirement's own switch) would independently pause a given request, THE SYSTEM SHALL report whichever
reason it evaluates first (implementation-defined tie-break, since either reason alone is already sufficient
grounds for refusal) — never attempt to disburse merely because one of the two switches happens to be
clear.

**Threshold, honestly grounded (an explicit, flagged limitation, not a claimed-validated figure):** THE
SYSTEM reuses, as a starting anchor, the SAME conservative real-world reference REQ-105 already cites (the
U.S. Federal Reserve's Q1 2024 credit-builder-product study, FEDS Notes 2024-12-06 — 93% unscored/nonprime,
~10.2% delinquency by COUNT) — `0.20` (a 20% dollar-weighted loss) is chosen as a deliberately LOOSER
complement of REQ-105's own `0.80` count-based repayment threshold (i.e. up to a 20% loss, matching
REQ-105's own tolerance for its OWN metric), reused here for internal consistency between the two
kill-switches' relative strictness — NOT because a dollar-weighted, all-tier default-rate figure has been
independently validated against that (or any) real-world source. **THE SYSTEM SHALL document this honestly
as an unvalidated placeholder**, exactly as REQ-104's `LOAN_INTEREST_RATE` and REQ-105's own kill-switch
threshold are already honestly flagged elsewhere in this document: the Fed study measures count-based
delinquency for a SPECIFIC human credit product, not dollar-weighted loss across a mixed-tier AI-agent loan
population, and this requirement's own `0.20` figure genuinely needs its OWN dedicated real-world-analog
research (or, better, real colony-native default data once a meaningful `sampleSize` accumulates) before
being treated as anything more than a conservative starting point — open to revision the same way REQ-105's
own threshold already is.

**Edge Cases**:
- ZERO loans have reached a terminal state yet (`sampleSize === 0`): `computeOverallDefaultRateUsd` returns
  `{totalIssuedUsd: 0, totalDefaultedUsd: 0, defaultRateUsd: null, sampleSize: 0}` — never a divide-by-zero
  throw; `evaluateOverallDefaultKillSwitch` correctly evaluates the `sampleSize < 10` branch
  (`totalDefaultedUsd > 0` is `false` when `totalDefaultedUsd === 0`) → `paused: false`.
- A SINGLE, large default occurs while `sampleSize < 10` (the bust-out scenario this requirement exists to
  close — e.g. an established borrower defaults on its FIRST large, `$5.00`-tier loan after several small,
  successfully-repaid cold-start loans): `totalDefaultedUsd > 0` while `sampleSize < 10` → `paused: true`
  REGARDLESS of how small `defaultRateUsd` numerically is relative to the colony's OTHER healthy loan
  volume — the SAME "any single default while the sample is small is itself the review trigger" discipline
  REQ-105 already establishes for its own metric, applied here so a bust-out default is never diluted away
  by a large healthy-loan denominator before `sampleSize` reaches 10.
- Many small, healthy, cold-start-tier loans are repaid on time (a large `totalIssuedUsd` denominator from
  MANY small numerators) alongside ONE large established-tier default: because `totalIssuedUsd`/
  `totalDefaultedUsd` are DOLLAR sums (never loan counts), the single large default's own dollar weight is
  NOT diluted by loan COUNT the way a naive "defaulted loans / total loans" count-based ratio would dilute
  it — a `$5.00` default among ninety-nine `$0.02` repayments is still a meaningfully large fraction of
  total dollar volume at risk, not `1/100`.
- This metric and REQ-105's `computeColdStartRepaymentRate` are computed OVER THE SAME `loanRows` but are
  NOT the same computation and do NOT overlap in a way that would double-pause identically for the same
  reason: a cold-start-tier default can contribute to BOTH metrics simultaneously (it is both a cold-start
  loan AND a terminal loan, dollar-weighted); an established-tier default contributes ONLY to
  `computeOverallDefaultRateUsd`, never to `computeColdStartRepaymentRate`'s own sample — THIS is exactly
  the coverage gap this requirement closes.
- Malformed/negative/non-finite `principal_usd`/`repaid_usd` on any row (a corrupted or adversarial ledger
  entry): treated as contributing `0` to both `totalIssuedUsd` and `totalDefaultedUsd` for that specific
  row (fail-closed — never a negative or NaN aggregate), mirroring REQ-101/105's own fail-closed convention
  for malformed numeric input elsewhere in this document.
- The EXACT volume-dilution scenario this revision's own FIND-602 identifies: 9 OTHER, unrelated, healthy
  established-tier (`$5.00`) loans reach `"repaid"` around the same time as ONE genuine `$5.00` bust-out
  default (`sampleSize:10`, `totalIssuedUsd:$50`, `totalDefaultedUsd:$5.00`, `defaultRateUsd:0.10` — BELOW
  the `0.20` ratio threshold, so the ratio signal ALONE would report `paused:false`): because the bust-out
  default's own `defaulted_ms` falls within `RECENT_DEFAULT_LOSS_WINDOW_DAYS`, `totalRecentDefaultLossUsd =
  $5.00`, which EQUALS `RECENT_DEFAULT_LOSS_THRESHOLD_USD` — `evaluateOverallDefaultKillSwitch` still
  returns `paused:true` via the NEW absolute-loss signal, closing the exact dilution gap the ratio alone
  leaves open (resolves FIND-602).
- A large default's `defaulted_ms` falls OUTSIDE `RECENT_DEFAULT_LOSS_WINDOW_DAYS` (an old, already-priced-in
  loss): excluded from `totalRecentDefaultLossUsd` regardless of its own dollar size — this signal is
  deliberately a ROLLING, recent-window measure, never a permanent, ever-growing lifetime sum (the ratio
  signal above already covers the permanent, colony-lifetime view).
- Multiple SMALL defaults within the window, none individually reaching `RECENT_DEFAULT_LOSS_THRESHOLD_USD`
  but summing ABOVE it (e.g. three separate `$2.00` established-tier defaults within the SAME 14-day
  window): `totalRecentDefaultLossUsd` correctly sums across ALL of them (never merely the single largest)
  and, once the sum exceeds the threshold, trips the pause — proving this signal catches an accumulating
  BURST of losses, not merely one single oversized default.

**Acceptance Criteria**:
- `computeOverallDefaultRateUsd` is pure, zero I/O, never divides by zero, and every returned dollar figure
  is clamped via the established `.toFixed(6)` money-precision convention.
- A fixture with 8 terminal cold-start-tier loans (`principal_usd = 0.02` each, all `"repaid"`) and 1
  terminal established-tier loan (`principal_usd = 5.00`, `repaid_usd = 0`, `"defaulted"`) →
  `totalIssuedUsd = 5.16`, `totalDefaultedUsd = 5.00`, `defaultRateUsd ≈ 0.969`, `sampleSize = 9` — proving
  a SINGLE large default dominates the dollar-weighted rate even though it is only `1/9` by loan COUNT.
- A fixture with ZERO terminal loans → `{totalIssuedUsd: 0, totalDefaultedUsd: 0, defaultRateUsd: null,
  sampleSize: 0}`, never a throw.
- `evaluateOverallDefaultKillSwitch({sampleSize: 9, totalIssuedUsd: 5.16, totalDefaultedUsd: 5.00,
  defaultRateUsd: 0.969}) === {paused: true}` — the single-large-default-while-small-sample case.
- `evaluateOverallDefaultKillSwitch({sampleSize: 20, totalIssuedUsd: 10.00, totalDefaultedUsd: 0.50,
  defaultRateUsd: 0.05}) === {paused: false}` — a healthy aggregate loss rate at a statistically-sized
  sample does not pause issuance.
- `evaluateOverallDefaultKillSwitch({sampleSize: 20, totalIssuedUsd: 10.00, totalDefaultedUsd: 3.00,
  defaultRateUsd: 0.30}) === {paused: true}` — an aggregate loss rate above `0.20` at a statistically-sized
  sample pauses issuance.
- A structural/Tier-0 check (mirroring PROP-105h's own real-source-read discipline) confirms REQ-106's own
  REAL, production issuance code imports and calls `evaluateOverallDefaultKillSwitch` for EVERY loan
  request (not merely cold-start ones), BEFORE acquiring the `` `loan_${lenderId}` `` lock, IN ADDITION TO
  (never instead of) `evaluateColdStartKillSwitch` — a mocked-caller fixture proving the function's own
  correctness is insufficient by itself, exactly as PROP-105h already establishes for its sibling
  kill-switch (new PROP-114c) — AND (extended this revision, resolves FIND-601) confirms a SECOND, separate
  call site to THIS SAME function ALSO exists INSIDE the lock-protected fresh-check critical section,
  re-evaluating it against the SAME fresh read already used for REQ-102(a)-(d)/REQ-101/REQ-104/105's own
  recheck, IN ADDITION TO its own pre-lock call site — AND (extended this revision, resolves FIND-602)
  confirms this SAME call site also computes `computeRecentDefaultLossUsd({loanRows, nowMs})` and passes its
  `totalRecentDefaultLossUsd` output into `evaluateOverallDefaultKillSwitch`, never omitting this new input.
- A fixture where `evaluateColdStartKillSwitch` returns `paused:false` but `evaluateOverallDefaultKillSwitch`
  returns `paused:true` for the SAME loan request confirms the request is STILL refused
  (`reason:"overall_default_paused"`) — proving the two kill-switches are independent, ADDITIVE gates,
  neither one alone sufficient to clear issuance (new PROP-114d).
- `computeRecentDefaultLossUsd({loanRows, nowMs, windowDays})` is pure, zero I/O, never divides (it is a
  sum, not a ratio), and sums ONLY `"defaulted"`-status (last-write-wins) rows' own `principal_usd -
  repaid_usd` whose `defaulted_ms` falls within the window — every returned figure clamped via the
  established `.toFixed(6)` money-precision convention (new PROP-114e, resolves this revision's own
  FIND-602).
- A fixture with 9 terminal, HEALTHY, established-tier (`principal_usd:5.00, repaid_usd:5.55,
  status:"repaid"`) loans plus 1 terminal established-tier `"defaulted"` loan (`principal_usd:5.00,
  repaid_usd:0`, `defaulted_ms` within the window) → `computeOverallDefaultRateUsd` alone yields
  `defaultRateUsd:0.10` (`paused:false` from the ratio signal alone, since it is below `0.20`) — but
  `computeRecentDefaultLossUsd` over the SAME `loanRows` yields `totalRecentDefaultLossUsd:5.00`, and
  `evaluateOverallDefaultKillSwitch({..., totalRecentDefaultLossUsd:5.00})` STILL returns `paused:true` via
  the NEW absolute-loss signal — proving the absolute signal catches a large default that the ratio ALONE
  would miss due to volume dilution (new PROP-114f, resolves this revision's own FIND-602, the
  requirement's own core dilution-defeat proof).
- `evaluateOverallDefaultKillSwitch`'s THREE-condition pause rule is exhaustively unit-tested: the existing
  ratio-based branch (unchanged, PROP-114b), the existing small-sample branch (unchanged, PROP-114b), AND
  the NEW absolute-loss branch independently, e.g. `evaluateOverallDefaultKillSwitch({sampleSize:50,
  totalIssuedUsd:200, totalDefaultedUsd:4.00, defaultRateUsd:0.02, totalRecentDefaultLossUsd:5.01}) ===
  {paused:true}` — a HEALTHY ratio at a LARGE sample still pauses once the absolute-loss signal alone
  crosses its own threshold (extends PROP-114b, resolves FIND-602).

---

### REQ群C: Issuance mechanics

### REQ-106: Loan issuance concurrency safety
**EARS**: WHEN two or more loan-issuance evaluations race in an overlapping wake window — EITHER against
the SAME lender, OR against the SAME borrower regardless of which lender(s) are involved (resolves this
revision's own FIND-401 — see the cross-lender same-borrower exclusion subsection below) — THE SYSTEM
SHALL ensure at most ONE actually disburses funds against that lender's surplus AND at most ONE loan is
ever concurrently open for that borrower, reusing, unmodified,
`~/anicca/skills/economy/gig/lib/lock.mjs`'s `withGigLock`/`isLockStale`/atomic-`fs.rename`-based
stale-reclaim mechanism (the SAME already-adversary-hardened generic lock this colony already reuses for
the gig board and, per `anicca-agent-spawn` REQ-103, for colony-spawn) under TWO distinct new lock keys,
BOTH acquired for EVERY issuance attempt: a lender-scoped key `` `loan_${lenderId}` `` (unchanged from
prior revisions — it alone still owns `nextLoanSequenceForLender`'s per-lender sequencing correctness,
below) AND a NEW, borrower-scoped key `` `loan_borrower_${borrowerId}` `` (matching `isSafeLockKey`'s
existing `[A-Za-z0-9_-]+` character-set constraint, same as the lender key) — this is TWO new lock KEYS
on the SAME EXISTING lock MECHANISM, never new lock-implementation code.

`withGigLock`'s real signature is `withGigLock(statePath, lockKey, fn, opts)`; `statePath` determines
which physical `locks/` directory the lock file lives under. THE SYSTEM SHALL therefore designate a
SINGLE canonical `statePath` — `~/anicca/skills/economy/lending/state/loans.jsonl` — exported as ONE
named constant, `LOANS_LEDGER_PATH`, from a new shared module
`~/anicca/skills/economy/lending/lib/lending-path.mjs`. EVERY call site that acquires a loan-issuance
lock, or reads/writes `loans.jsonl` itself, SHALL import and use this SAME exported constant — never an
independently hardcoded path string — mirroring `anicca-agent-spawn` REQ-103's identical
`CITIZENS_REGISTRY_PATH` discipline and closing the SAME "mismatched `statePath` silently defeats mutual
exclusion" hazard that discipline exists to close.

**Cross-lender same-borrower exclusion (resolves this revision's own FIND-401 — a real, unbounded-duration
double-borrowing window a per-lender-only lock cannot close):** REQ-102's own condition (c) requires a
borrower have ZERO currently-open loan obligations — but a lock scoped ONLY to `` `loan_${lenderId}` ``
serializes issuance BY THE SAME LENDER, never ACROSS different lenders. Two DIFFERENT lenders, L1 and L2,
each independently evaluating the SAME borrower B, can each freshly read `loans.jsonl`, each see B as
having zero `"active"`/`"defaulted"` rows, and each proceed under their OWN, non-contending lock — both
disbursing to B. Because a `"provisioning"`/`"disbursement_uncertain"` row (this requirement's own
two-phase record, below) is NOT one of condition (c)'s excluded statuses, this window is not merely a
millisecond-scale race: it can persist for an ARBITRARY duration (reconciliation for a given lender is
only re-attempted at the start of that SAME lender's own NEXT issuance attempt, which may never come
soon). THE SYSTEM THEREFORE SHALL, for EVERY loan-issuance attempt, ALSO acquire the borrower-scoped lock
`` `loan_borrower_${borrowerId}` `` — in ADDITION to, never instead of, the existing per-lender lock (a
single COMBINED lock key derived from both IDs was considered and REJECTED: it would fragment the
per-lender sequence-number critical section by borrower, letting two DIFFERENT borrowers of the SAME
lender proceed against STALE `loanRows` snapshots and reopening `nextLoanSequenceForLender`'s own
collision-freedom guarantee, PROP-106e — the per-lender lock MUST remain a single, whole-lender critical
section) — and SHALL, while BOTH locks are held, take a FRESH read of `loans.jsonl` and RE-EVALUATE
REQ-102's own conditions (a)-(d) for this borrower against that fresh read BEFORE proceeding to REQ-101's
own availability recheck, REQ-104/105 sizing, `n = nextLoanSequenceForLender(...)`, and disbursement —
never relying on a borrower-eligibility read taken before either lock was acquired. If this fresh
re-check finds the borrower NO LONGER eligible (e.g. a DIFFERENT lender's own concurrent attempt already
appended a `"provisioning"`/`"active"` row for this borrower in the interim), THE SYSTEM SHALL refuse this
attempt (`reason:"outstanding_loan"`) BEFORE any disbursement is attempted and BEFORE any `n` is computed
— exactly REQ-102's own existing fail-closed refusal shape, now evaluated with a guaranteed-fresh,
cross-lender-safe read.

**Kill-switch re-verification inside this SAME lock-protected fresh-check (resolves this revision's own
spec-review iteration-7 FIND-601 — a TOCTOU race the pre-lock-only kill-switch check below cannot close):**
REQ-105's `evaluateColdStartKillSwitch` and REQ-114's `evaluateOverallDefaultKillSwitch` (see the
kill-switch Edge Cases below) are, by their own requirements' own text, each evaluated exactly ONCE — on a
snapshot of `loanRows` read BEFORE either lock this requirement acquires is ever taken. Because BOTH
monitors are COLONY-WIDE (never scoped to the specific `lenderId`/`borrowerId` pair whose locks this
requirement holds), the per-lender/per-borrower locking above does NOT, by itself, close a race against
either kill-switch's own PAUSE decision the way it closes REQ-102's own borrower-eligibility race: two
loan-issuance attempts for TWO DIFFERENT lenders AND TWO DIFFERENT borrowers (the first Edge Case below —
zero lock contention between them) can each independently read the SAME pre-pause `loanRows` snapshot, each
observe `paused:false` at their own pre-lock check, and BOTH proceed toward disbursement even in the exact
window where a just-landed default should be tripping one of these SAME kill-switches — this is
structurally the SAME class of TOCTOU race FIND-401 already found and closed for borrower eligibility, but
left open here for BOTH kill-switches' own pause decisions. THE SYSTEM SHALL THEREFORE, while BOTH locks
are held, and as part of the SAME fresh-read critical section already specified above for
REQ-102(a)-(d)/REQ-101/REQ-104/105 — NEVER a second, independently-taken snapshot — ALSO RE-EVALUATE
`evaluateColdStartKillSwitch` (for a cold-start request, i.e. `successfulOnTimeRepayments===0` re-derived
against this SAME fresh read) and `evaluateOverallDefaultKillSwitch` (for EVERY request, regardless of
tier) against that SAME fresh read. If EITHER kill-switch's fresh, lock-protected re-evaluation now returns
`paused:true` — regardless of what its OWN pre-lock evaluation returned moments earlier — THE SYSTEM SHALL
refuse this specific issuance attempt (`reason:"cold_start_paused"`/`reason:"overall_default_paused"`, the
SAME reason strings each switch's own pre-lock refusal already uses) BEFORE `n` is computed and BEFORE any
disbursement is attempted — never proceeding merely because the EARLIER, pre-lock check happened to pass.
This closes the arbitrary-duration window the pre-lock-only check leaves open: a kill-switch that trips
strictly BETWEEN a caller's own pre-lock check and its own later lock acquisition can never again slip an
issuance through, no matter how many OTHER, non-lock-contending concurrent attempts are already past their
own initial check when it trips.

**Lock-acquisition order (resolves this revision's own FIND-501 — a prior revision's "deadlock avoidance"
justification for this SAME fixed order was analytically FALSE, corrected below):** because EVERY
loan-issuance attempt now acquires BOTH `` `loan_${lenderId}` `` and `` `loan_borrower_${borrowerId}` ``,
THE SYSTEM SHALL acquire them via NESTED `withGigLock` calls in a FIXED, deterministic, TOTAL order: THE
SYSTEM SHALL acquire, as the OUTER lock, whichever of the two lock-key STRINGS sorts lexicographically
FIRST (plain JavaScript default string `<` comparison, e.g. `[`loan_${lenderId}`,
`loan_borrower_${borrowerId}`].sort()[0]`), and the OTHER as the INNER lock — never an ad-hoc per-call
choice.

**Corrected justification (the PRIOR "textbook total-lock-ordering deadlock-avoidance technique" framing
is FALSE, re-confirmed by a fresh re-read this revision of `lock.mjs` lines 153-158, 174-179, 187-209):**
`withGigLock`'s own `acquire()` is a SINGLE, non-blocking attempt — `tryCreateLockFile`, then at most ONE
`reclaimStaleLock` attempt if that fails — there is NO internal retry loop and NO code path in which a
caller BLOCKS while holding one lock and waiting for another; `withGigLock`'s own docstring states this
verbatim: "If another call already holds the lock, returns a fail-closed rejection WITHOUT ever calling
`fn()` — no queueing, no waiting." Classical hold-and-wait deadlock (party A holds resource 1 and BLOCKS
waiting for resource 2, while party B holds resource 2 and BLOCKS waiting for resource 1) REQUIRES a
primitive that can suspend a holder while it waits for a second resource — `lock.mjs` structurally cannot
do this: a caller whose SECOND (inner) lock acquisition fails returns `{ok:false}` IMMEDIATELY, and its own
FIRST (outer) lock is released in `withGigLock`'s own `finally` block (lines 203-208) — it is never
held-and-waited. This holds REGARDLESS of what order the two nested calls acquire their keys in: a
lexicographic sort, a role-based rule ("always lender first"), or even an ad-hoc per-call choice would ALL
be EQUALLY deadlock-free against THIS lock mechanism, because no concurrent attempt ever blocks at all — the
"two attempts each hold one lock while waiting on the other in reverse order" precondition this
requirement's own prior text depended on can never arise. (Independently, and for a SECOND reason: this
document's own lock-key naming convention already keeps the lender-key namespace `loan_<lenderId>` and the
borrower-key namespace `loan_borrower_<borrowerId>` disjoint, so no two concurrent issuance attempts ever
share MORE than ONE lock key at all — classical lock-ordering deadlock, which requires at least two SHARED
resources acquired in reversed order, could never occur here even if the lock mechanism DID block.)

**Given ordering is NOT required for deadlock-avoidance against today's lock, THE SYSTEM nonetheless RETAINS
`resolveLoanLockAcquisitionOrder` and its fixed order — for two DIFFERENT, honestly-stated reasons, neither
of which is "prevents deadlock":** (1) **a single, deterministic convention, not an ad-hoc per-call
choice** — every call site derives its own nested lock order from ONE shared function instead of each
independently choosing "lender first" or "borrower first," avoiding a class of easy-to-get-inconsistent
bugs across call sites, and giving Tier-2 concurrency tests (e.g. PROP-106n) one canonical, reproducible
acquisition order to reason about for a given `(lenderId, borrowerId)` pair; (2) **forward-insurance against
a future, DIFFERENT lock implementation** — IF `lock.mjs` is ever changed to a blocking/retry-with-backoff
primitive (making `acquire()` genuinely wait rather than fail-fast), a fixed TOTAL lock-acquisition order is
EXACTLY the mechanism that would then become REQUIRED to prevent a REAL hold-and-wait deadlock between two
attempts sharing the `loan_borrower_<borrowerId>` key — having this ordering already in place today, at zero
marginal cost (a single deterministic sort, PROP-106m), means a future maintainer making that change does
not also have to simultaneously invent and retrofit a lock-ordering discipline under time pressure, without
understanding why it has suddenly become load-bearing. **Removing `resolveLoanLockAcquisitionOrder` entirely
(in favor of "acquire both locks in any consistent per-call order") would be EQUALLY CORRECT against TODAY's
fail-fast lock — this spec deliberately keeps the function anyway, for reasons (1) and (2) above, never
because doing so is required for correctness today.**

`resolveLoanLockAcquisitionOrder(lenderId, borrowerId) → [outerKey, innerKey]` is a NEW, pure, zero-I/O
helper implementing exactly this sort (new PROP-106m, its own description corrected this revision to match
the justification above — never "deadlock avoidance"). Both locks are released automatically,
inner-then-outer, by the nested calls' own `withGigLock` `finally` blocks — no separate release code is
written. If EITHER lock is already held by another in-flight attempt, THE WHOLE attempt is refused
(`reason:"lock_held"`), fail-closed, zero disbursement, zero row appended — identical in shape to today's
existing single-lock refusal (this fail-fast refusal — never lock ordering — is what actually keeps this
design safe against two concurrent attempts sharing a lock key; see the corrected justification above). THE
SYSTEM documents, as an explicit, low-probability, ASSUMED limitation of this naming scheme (mirroring this
spec's own existing documented-limitation discipline, e.g. `GOJO_SENDER_ID`'s single-sender assumption): no
colony citizen ID is assumed to literally begin with the substring `borrower_` — true for every one of
today's real citizen IDs (`anicca-a3cdd4`, `Franklin`) — since a citizen ID that DID begin with that
substring could theoretically produce a lock-key string collision between an unrelated lender's own
per-lender key and a different loan's per-borrower key; this is a documented, not-yet-solved,
extremely-low-probability edge case of this naming convention, not a silently-ignored risk.

**`loan_id` generation (resolves this revision's own FIND-001 — previously entirely unspecified):** THE
SYSTEM SHALL assign a newly-issued loan's `loan_id` as `` `loan_${lenderId}_${n}` ``, where `n` is a
per-LENDER monotonic sequence number computed and appended STRICTLY INSIDE the SAME `loan_${lenderId}`
lock this requirement already acquires for that lender's own surplus-check/disbursement (never outside
it, and never as a separate, independently-locked step): `n = nextLoanSequenceForLender(loanRows,
lenderId)` reads every row in `loans.jsonl` whose `lender_id === lenderId` (regardless of `borrower_id`
or `status`), extracts the numeric suffix following that SAME lender's own `loan_${lenderId}_` prefix
from each such row's `loan_id`, and takes the highest such `n` found, +1 (or `1` if this lender has no
prior rows at all) — mirroring `child-spec.js::nextChildId`'s own "read all rows, take highest matching
prefix's numeric suffix, +1" algorithm (see Dependencies), but DELIBERATELY namespaced by `lenderId`
rather than global. Because the ID space is partitioned by `lenderId` AND `n` is read-then-incremented
strictly inside that SAME lender's own existing lock, two DIFFERENT lenders issuing concurrently (this
requirement's own intentional no-cross-lender-contention design, Edge Cases below) can NEVER collide on
the same `loan_id` even though they hold no shared/global lock: no two DIFFERENT lenders' IDs ever share
the same `loan_${lenderId}_` prefix, so this feature needs no `"colony-spawn"`-style single shared lock
the way `child-spec.js`'s own upstream usage does.

**Crash-safe two-phase issuance record (resolves this revision's own FIND-103 — a real double-disbursement
risk the prior revision's lock-reclaim framing addressed for the LOCK but never actually closed for the
MONEY):** Because `payViaFacilitator`'s own on-chain settle is an IRREVERSIBLE external side effect, a
process crash strictly BETWEEN that settle succeeding and the local ledger append meant to record it would
otherwise leave a real transfer permanently untracked — and, worse, let a reclaiming caller recompute the
SAME sequence number and disburse a SECOND time, since `loans.jsonl` would show no trace of the crashed
attempt ever having happened. THE SYSTEM SHALL therefore split loan-issuance's own ledger write into TWO
append-only rows, mirroring `~/anicca/skills/self/spawn/run.sh`'s own real "provisional ledger row (so we
never lose track even if step 4 fails)" pattern (its own step 3, read this session):
1. IMMEDIATELY after computing `n = nextLoanSequenceForLender(loanRows, lenderId)`, and STILL INSIDE the
   SAME `loan_${lenderId}` lock, THE SYSTEM SHALL `appendChild` a PROVISIONAL row for `loan_id =
   loan_${lenderId}_${n}` with `status: "provisioning"` (principal/terms already computed, no transfer yet
   attempted) — this durably reserves the sequence number BEFORE the irreversible external side effect is
   ever attempted.
2. THE SYSTEM SHALL THEN attempt the disbursement transfer (`payViaFacilitator`).
3. THE SYSTEM SHALL THEN `appendChild` a FOLLOW-UP row for the SAME `loan_id` recording the REAL outcome:
   `status: "active"` (with the real `txHash`) if the transfer succeeded, `status:
   "disbursement_failed"` if it cleanly did not, or `status: "disbursement_uncertain"` if an in-process
   exception during this step leaves the real outcome unknown to this process (see the In-process
   exception paragraph below, resolves this revision's own FIND-201).

**`issued_ms`, precisely defined (resolves this revision's own FIND-403 — a real ambiguity between two
candidate row timestamps this document previously left unstated):** `issued_ms` is a field on the
FOLLOW-UP `"active"` row ONLY — set to the wall-clock time (`Date.now()`) at the moment THAT row is
appended, i.e. the moment disbursement is CONFIRMED successful — it is NEVER the provisional row's own
`provisioned_ms` (the moment issuance was first ATTEMPTED, before any transfer occurred). This is the
correct choice for REQ-109's own default-clock purpose: a borrower's real, usable
`LOAN_REPAYMENT_WINDOW_DAYS` window should count from when it actually RECEIVED usable funds, never from
when issuance was merely attempted — a slow-to-reconcile provisional row must not silently eat into the
borrower's own real repayment window. `due_ms = issued_ms + LOAN_REPAYMENT_WINDOW_DAYS * 86400000`
(REQ-109) is therefore always computed from THIS SAME `"active"`-row `issued_ms` value, never from
`provisioned_ms`. A `"provisioning"`, `"disbursement_failed"`, or `"disbursement_uncertain"` row carries
NO `issued_ms` field at all (it is not yet, or never becomes, an issued loan) — `issued_ms` exists ONLY
on a row whose `status` is (or, via a correcting reconciliation follow-up, becomes) `"active"`.
**Acknowledged trade-off (documented, not resolved further this increment):** for the NORMAL
(non-reconciled) path, `issued_ms` is set within, at most, a few seconds of the real on-chain transfer's
own confirmation (`payViaFacilitator` returns only after `waitForTransactionReceipt` resolves) — the
difference is negligible. For a RECONCILED path (a crash or in-process exception delays the follow-up
append until a LATER loan-issuance attempt's own `reconcileProvisionalDisbursement` call finally appends
the correcting `"active"` row), `issued_ms` is set at that LATER reconciliation moment, not at the real
(earlier) on-chain transfer time — giving that specific loan a FRESHER, and therefore longer-feeling,
`due_ms` window than an identically-timed normal-path loan would have received. THE SYSTEM SHALL NOT
attempt to backdate `issued_ms` to the on-chain transfer's own real block timestamp to close this
asymmetry this increment (that would require an additional `eth_getBlockByNumber` lookup this spec does
not otherwise need) — this is an explicit, honestly-documented, low-probability limitation
(reconciliation delays are expected to be rare and short, per this requirement's own crash-recovery
design), not a silently-ignored one, mirroring this spec's own existing documented-limitation discipline
elsewhere (e.g. `GOJO_SENDER_ID`'s single-sender assumption, REQ-112's single-coordinator-host scope).

`nextLoanSequenceForLender(loanRows, lenderId)` SHALL treat a `"provisioning"`, `"disbursement_failed"`,
`"active"`, OR `"disbursement_uncertain"` row for the SAME `loan_id` as ALL belonging to the SAME
already-claimed sequence number `n` (last-write-wins, the SAME convention every other reduction in this
spec already uses) — it SHALL NEVER recompute or reuse `n` for a NEW attempt while a `"provisioning"` row
for that `n` exists with no terminal follow-up row yet, NOR while a `"disbursement_uncertain"` row for
that `n` exists with no CORRECTING follow-up row yet (see the In-process exception paragraph below).
**Corrected this revision (resolves this revision's own FIND-301 — broadens this trigger to be driven by
ledger STATE alone, never lock state, see the unifying paragraph below for the full rationale):** BEFORE
computing or using ANY new sequence number for a NEW loan-issuance attempt for this lender, ANY caller —
whether it acquired the lock via the normal fast-acquire path OR by reclaiming a stale lock — SHALL ALWAYS
check whether this lender's own highest-numbered existing `loan_id` row is UNTERMINATED (its own
last-appended row's `status` is `"provisioning"` with no later `"active"`/`"disbursement_failed"` row for
that SAME `loan_id`, OR is `"disbursement_uncertain"` with no later correcting
`"active"`/`"disbursement_failed"` row). If so, THE SYSTEM SHALL, BEFORE deciding to retry or mark the
attempt failed, perform a REAL on-chain lookup for whether a matching disbursement transaction actually
landed — `reconcileProvisionalDisbursement`, mirroring REQ-108/`verifyRepayment`'s own independent
`Transfer`-log-verification machinery (an `eth_getLogs`/receipt check for a `Transfer` from the lender's
own `walletAddress.evm` to the borrower's own `walletAddress.evm` for this loan's own principal amount, in
the block range since the provisional row's own `provisioned_ms`) — NEVER blindly re-disbursing without
first checking real on-chain state. If that lookup finds a matching, finalized `Transfer`, THE SYSTEM SHALL
append the `"active"` follow-up row with that discovered `txHash` (recovering the crashed attempt's own
real transfer into the ledger, never losing track of it) and SHALL NOT disburse again. If that lookup finds
NO matching transfer, THE SYSTEM SHALL append a `"disbursement_failed"` follow-up row for the stalled
attempt, and only THEN is `n+1` available as the next new attempt's sequence number for this lender.

**Ledger-state-triggered reconciliation, not lock-state-triggered (resolves this revision's own FIND-301 —
a THIRD, previously-unhandled terminal state a prior revision's lock-staleness-gated trigger left open):**
a PRIOR revision of this requirement gated the check above on "a caller that reclaims a STALE lock" — this
made "the lock is stale" a PRECONDITION for reconciliation ever firing at all, which left a genuine gap: a
`"provisioning"` row can also be left with NO terminal follow-up row of ANY kind (not even
`"disbursement_uncertain"`) while the lock is CLEANLY RELEASED and therefore never stale, if the follow-up
`appendChild` call ITSELF throws — `ledger.js`'s own `appendChild` (a plain, synchronous
`fs.appendFileSync`, confirmed this session, no internal try/catch) CAN genuinely throw (ENOSPC, EACCES, a
transient disk failure) immediately after `payViaFacilitator`'s own settle-side exception has already been
caught by step 2's own try/catch (above). When this happens, `fn()` propagates THIS SECOND exception
uncaught; `withGigLock`'s own `finally` block (`lock.mjs` lines 203-208, confirmed this session) still
releases the lock NORMALLY (via `fs.unlink`) exactly as it does for ANY exception thrown out of `fn()` —
so the NEXT caller for this lender takes the ordinary FAST-ACQUIRE path, never the stale-reclaim path, and
a trigger gated on lock staleness would NEVER fire reconciliation for this case at all, permanently
blocking this lender from issuing any further loan. THE SYSTEM THEREFORE REMOVES "the lock is stale" as any
kind of precondition for this check: the check above is performed EVERY TIME, driven PURELY by the
ledger's own recorded STATE (an unterminated highest-`n` row for this lender), covering — UNIFORMLY, via
this ONE mechanism, never a separate one per cause — (a) a genuine process CRASH (the lock has also gone
stale; a reclaiming caller performs the check), (b) an in-process, non-crash exception from
`payViaFacilitator` itself, correctly caught and recorded as `"disbursement_uncertain"` (the lock was
released normally; the very next caller, via the ordinary fast-acquire path, performs the check — already
specified in the In-process exception paragraph below), and (c) THIS revision's own newly-identified case —
an exception thrown from the follow-up `appendChild` call itself, leaving a `"provisioning"` row with
literally no follow-up row at all, under a lock that is NOT stale (the lock was released normally). Because
the trigger is now the ledger's own STATE, never the lock's, case (c) requires NO special-casing: the very
next caller for this lender — whichever caller that happens to be — finds the SAME unterminated
`"provisioning"` row and performs the SAME reconciliation check specified above. There is no third,
unhandled terminal state: `"provisioning"` with no follow-up, under any lock condition, ALWAYS triggers
reconciliation on the next attempt.

**A reconciliation lookup that itself throws (closes the SAME finding's second gap):** `reconcileProvisionalDisbursement`
is itself a real, effectful, RPC-backed lookup and CAN itself throw (an RPC timeout or network error during
the on-chain lookup) rather than cleanly resolving to a matching-`Transfer`/no-matching-`Transfer` result.
If it does, THE SYSTEM SHALL treat this specific loan-issuance attempt as failed for this wake: it SHALL
NOT compute or use ANY sequence number (neither the outstanding `n` nor a new `n+1`) this attempt, and SHALL
NOT append any row as a result of the failed reconciliation attempt itself — the existing unterminated row
is left EXACTLY as it was found. The `loan_${lenderId}` lock is released NORMALLY via `withGigLock`'s own
`finally` block (the SAME as any other exception thrown from `fn()`) — never left stale. Because the check
above is now a STANDING invariant re-evaluated at the START of EVERY subsequent loan-issuance attempt for
this lender (never a one-shot gate tied to a single specific attempt), a reconciliation lookup that throws
simply DEFERS resolution to a later attempt — it never creates a new, additional stuck/terminal state, and
retrying it an unbounded number of times across successive attempts carries ZERO double-transfer risk
(unlike retrying `payViaFacilitator` itself would), because `reconcileProvisionalDisbursement` only ever
READS on-chain state — it never disburses.

**In-process (non-crash) exception during disbursement (resolves this revision's own FIND-201 — a
DISTINCT double-disbursement/untracked-transfer hazard the crash-recovery mechanism above does not, by
itself, close):** PRIOR to this revision's own FIND-301 correction (above), the crash-recovery mechanism
above was triggered ONLY when a caller reclaims a STALE `loan_${lenderId}` lock — but `payViaFacilitator`'s
own on-chain settle can genuinely succeed and THEN
throw an exception from the SAME, still-alive process, strictly AFTER `/settle` has already returned
`success:true` (i.e. the real transfer has already been broadcast): concretely,
`escrow.mjs::settleBody`'s own `await publicClient.waitForTransactionReceipt({hash: tx})` (line 135) has
NO try/catch around it and can genuinely throw (RPC timeout, network error, receipt-not-found-within-
polling-window) in exactly this window. Because `withGigLock`'s own `try { return await fn(); } finally {
clearInterval(heartbeat); await release(statePath, lockKey); }` (`lock.mjs` lines 203-208) releases the
lock NORMALLY (via `fs.unlink`) whenever `fn()` throws — NEVER leaving it stale — an uncaught exception
from step 2 above would otherwise propagate straight out of `fn()` without EVER reaching step 3's
follow-up append, and the NEXT caller for this SAME lender would take the normal fast acquire path
(`tryCreateLockFile`, `lock.mjs` line 156), NOT the stale-reclaim path (`reclaimStaleLock`, lines 128-151)
the crash-recovery mechanism above depends on to trigger `reconcileProvisionalDisbursement` — so that
reconciliation would NEVER fire for this failure mode at all, despite `nextLoanSequenceForLender` still
treating the highest `n`'s `"provisioning"` row as claimed with no terminal follow-up. THE SYSTEM SHALL
THEREFORE wrap step 2 above (the `payViaFacilitator` call) in its OWN try/catch, INSIDE `fn()` itself —
never merely called bare — so that regardless of whether that call (a) resolves `{ok:true}` with a real
`txHash`, (b) resolves `{ok:false}` (the clean, already-specified `disbursement_failed` case below), OR
(c) THROWS an exception mid-call, a follow-up row is ALWAYS appended by `fn()` BEFORE `fn()` itself
returns or (re-)throws. On catching such an in-process exception, THE SYSTEM SHALL append the follow-up
row with `status: "disbursement_uncertain"` (never `"disbursement_failed"`, which would falsely claim
CERTAINTY that no transfer occurred, and never `"active"`, which would falsely claim certainty that one
did) — honestly recording that this process does not know the transfer's real on-chain outcome. THE
SYSTEM SHALL make `reconcileProvisionalDisbursement` (specified above for the stale-lock-reclaim crash
case) ALSO the mechanism that resolves a `"disbursement_uncertain"` row — UNIFYING both recovery paths
into ONE reconciliation mechanism, rather than two, only one of which is actually wired up: whenever
`nextLoanSequenceForLender` finds the last-appended row for this lender's highest `n` is
`"disbursement_uncertain"`, THE SYSTEM SHALL, at the START of the NEXT loan-issuance attempt for this
SAME lender — inside THAT attempt's own freshly-acquired `loan_${lenderId}` lock, NOT gated on a
stale-lock reclaim for this failure mode, since the lock here was never left stale — perform the SAME
real on-chain lookup (`reconcileProvisionalDisbursement`, by expected lender→borrower `walletAddress.evm`/
principal amount, in the block range since the `"provisioning"` row's own `provisioned_ms`) already
specified above, BEFORE computing/using `n+1`. If a matching, finalized `Transfer` is found, append a
correcting follow-up row (`status: "active"`, the discovered real `txHash`); if none is found, append
`status: "disbursement_failed"` instead. Only after this reconciliation completes does `n+1` become
available as the next new sequence number for this lender.

**Disbursement failure (resolves this revision's own FIND-003 — the facilitator-service precondition):**
the "disbursement transfer" step of this critical section (above) calls `payViaFacilitator` (Dependencies
section) with `facilitatorUrl` resolved via the SAME `GIG_FACILITATOR_URL`-env-then-`127.0.0.1:8405`
pattern `gig.mjs` already establishes. IF that call fails for ANY reason (facilitator unreachable, `verify`
rejects, `settle` fails, or the settle transaction reverts on-chain), THE SYSTEM SHALL fail closed per the
two-phase record above: the FOLLOW-UP row is appended with `status: "disbursement_failed"` (never a silent
"no row at all," now that a provisional row already exists for this `n`), the per-lender lock is released
normally (never left stuck), and this specific `n` is terminally closed — a subsequent attempt for this
SAME lender computes a NEW `n+1`, never silently proceeding as if funds had moved and never a `loans.jsonl`
row claiming `"active"` for a loan that was never actually funded.

**Lock-key disambiguation (resolves this revision's own FIND-205 — a mislabeling in this SAME
requirement's own Acceptance Criteria below):** THIS requirement's own two-phase provisional/follow-up
ledger append (steps 1 and 3 above) is appended under BOTH this requirement's OWN per-lender
`` `loan_${lenderId}` `` lock AND, this revision, the NEW per-borrower `` `loan_borrower_${borrowerId}` ``
lock (together, per the Cross-lender same-borrower exclusion / Lock-acquisition order subsections above,
resolves FIND-401) — NEVER under REQ-108/109's own, separate per-loan `` `loan_${loan_id}` `` lock.
REQ-108/109's per-loan lock governs ONLY their own LATER, independent repayment-verification/
default-detection status-transition appends on an ALREADY-ACTIVE loan (a loan that has already completed
THIS requirement's own issuance critical section) — it is never acquired, nested, or otherwise involved
during issuance itself. These are two DELIBERATELY DIFFERENT locks protecting two DIFFERENT critical
sections at two DIFFERENT points in a loan's own lifecycle, and no code path in this feature ever acquires
BOTH locks for the SAME append.

**Edge Cases**:
- Two DIFFERENT lenders' loan requests targeting TWO DIFFERENT borrowers proceed concurrently without
  lender-lock contention (different `` `loan_${lenderId}` `` keys under the SAME `locks/` directory):
  intentional, not a bug — mirrors `gig.mjs`'s own existing per-`gigId` lock-key pattern (documented in
  `lock.mjs`'s own header comment). Per the `loan_id` scheme above, this also means their two
  newly-assigned `loan_id`s are structurally guaranteed distinct (different `lenderId` prefixes), with
  zero collision risk. **Corrected this revision (resolves FIND-401):** two DIFFERENT lenders' loan
  requests targeting the SAME borrower are NO LONGER contention-free — the NEW
  `` `loan_borrower_${borrowerId}` `` lock (above) now serializes them, ensuring at most one succeeds; see
  the new Edge Case immediately below and new PROP-106n.
- Two DIFFERENT lenders, L1 and L2, both attempt to issue a loan to the SAME borrower B concurrently
  (resolves this revision's own FIND-401): both acquire their OWN per-lender lock (`loan_L1`, `loan_L2` —
  no contention there, per the Edge Case above) but BOTH also require the SAME `loan_borrower_B` lock —
  exactly ONE of L1/L2 acquires it first (per the total lock-ordering rule above) and, holding BOTH its
  own locks, re-checks REQ-102 with a fresh read, finds B still eligible, and proceeds to disburse and
  append B's new `"provisioning"`/`"active"` rows. The OTHER, upon acquiring `loan_borrower_B` after the
  first releases it, re-checks REQ-102's conditions with a FRESH read that NOW includes the first
  attempt's own newly-appended row, finds B NO LONGER eligible (`reason:"outstanding_loan"`), and refuses
  — zero disbursement, zero ledger row for the refused attempt. Exactly one of L1/L2 ever disburses to B;
  B never ends up with two simultaneously-open loans from different lenders (new PROP-106n).
- A candidate loan where `lenderId === borrowerId` (a self-loan attempt): rejected by REQ-102(d) BEFORE
  ANY other step of this critical section runs — before REQ-101's surplus computation, before
  `evaluateColdStartKillSwitch` AND `evaluateOverallDefaultKillSwitch` (resolves this revision's own
  spec-review iteration-7 FIND-603), and before EITHER the `` `loan_${lenderId}` `` or the
  `` `loan_borrower_${borrowerId}` `` lock is ever acquired (resolves FIND-402) — zero disbursement
  attempt, zero ledger row, zero lock acquisition regardless of either party's balance.
- The instance holding the lock crashes mid-issuance, BEFORE `payViaFacilitator` is even attempted (the
  provisional row was appended, but the process died before step 2 above): the existing heartbeat +
  `isLockStale` mechanism reclaims the lock after `staleMs` of no heartbeat, exactly as it already does
  for gig-board operations; the reclaiming caller's on-chain lookup (above) finds no matching transfer,
  appends `disbursement_failed`, and proceeds at `n+1` — REQ-106 does not need a second staleness
  mechanism for the LOCK itself, only the two-phase ledger record + on-chain check above for the MONEY.
- The instance holding the lock crashes mid-issuance AFTER `payViaFacilitator`'s own on-chain settle
  SUCCEEDS but BEFORE the follow-up `"active"` row is appended (resolves this revision's own FIND-103 —
  the genuine double-disbursement risk a lock-reclaim mechanism alone can never close, since the lock only
  ever protects the LEDGER's own critical section, not an already-completed external side effect): a
  reclaiming caller MUST NOT recompute/reuse `n` and disburse again merely because the last-appended row
  for it is still `"provisioning"` — it MUST first perform the real on-chain lookup specified above;
  finding the crashed attempt's own real transfer, it appends the recovering `"active"` row with that
  transaction's own real `txHash` and does NOT disburse a second time. Two callers, one crashing exactly
  in this window, must never both cause a real transfer to leave the lender's wallet for the SAME `n` (new
  PROP-106g).
- The SAME process (no crash) catches an in-process exception thrown from `payViaFacilitator` AFTER its
  own on-chain settle already succeeded (e.g. `waitForTransactionReceipt`'s own RPC timeout, resolves
  this revision's own FIND-201): `fn()` appends `status: "disbursement_uncertain"` and the lock is
  released NORMALLY (never stale) — the NEXT caller for this lender therefore takes the normal fast
  acquire path, NOT the stale-reclaim path, and MUST reconcile the `"disbursement_uncertain"` row via the
  SAME on-chain lookup (`reconcileProvisionalDisbursement`) BEFORE computing a new `n+1` — a clean lock
  release is NEVER, by itself, proof that the ledger is already terminally resolved for this `n`.
- A live, heartbeating holder is never stolen from, however long its critical section legitimately
  runs — this property is inherited, not re-derived, from the existing lock.
- A future call site hardcodes its own literal `loans.jsonl` path string instead of importing
  `LOANS_LEDGER_PATH`: treated as a spec violation to be caught at Phase 3 review (a structural/
  import-identity check, not a runtime assertion) — mirrors `anicca-agent-spawn` REQ-103's identical
  edge case.
- The facilitator service is unreachable (connection refused, timeout) at disbursement time: treated
  identically to any other `payViaFacilitator` failure above — fail closed, no ledger row, lock released,
  retriable next wake.
- A NEW cold-start loan request (`successfulOnTimeRepayments===0` for that borrower) is evaluated while
  REQ-105's `evaluateColdStartKillSwitch` returns `paused:true`: THE SYSTEM SHALL refuse BEFORE ever
  acquiring the `` `loan_${lenderId}` `` lock (`reason:"cold_start_paused"`) — zero disbursement attempt,
  zero ledger row, exactly as any other REQ-101/102 pre-lock eligibility refusal (resolves FIND-203).
- ANY loan request (cold-start OR an established-tier renewal) is evaluated while REQ-114's
  `evaluateOverallDefaultKillSwitch` returns `paused:true`: THE SYSTEM SHALL refuse BEFORE ever acquiring
  the `` `loan_${lenderId}` `` lock (`reason:"overall_default_paused"`) — zero disbursement attempt, zero
  ledger row, evaluated IN ADDITION TO (never instead of) `evaluateColdStartKillSwitch` above, since
  REQ-114's own monitor covers the LARGER-loan tranche REQ-105's cold-start-scoped monitor structurally
  cannot see (resolves this revision's own FIND-502).
- A kill-switch (`evaluateColdStartKillSwitch` OR `evaluateOverallDefaultKillSwitch`) is HEALTHY
  (`paused:false`) at the moment of a specific issuance attempt's own initial, pre-lock check, but a
  DIFFERENT, concurrent event (e.g. another attempt's own default landing, or an unrelated loan reaching a
  terminal `"defaulted"` state) flips that SAME kill-switch to `paused:true` strictly BETWEEN that pre-lock
  check and this attempt's own later acquisition of both locks (resolves this revision's own spec-review
  iteration-7 FIND-601 — a TOCTOU race the pre-lock-only check above cannot itself close): THE SYSTEM SHALL
  catch this at the lock-protected fresh re-check specified above (Kill-switch re-verification subsection)
  and refuse the attempt THERE, even though its own EARLIER, pre-lock check already passed — zero
  disbursement, zero ledger row, regardless of how far past the initial check this specific attempt had
  already progressed.
- The follow-up `appendChild` call ITSELF throws (e.g. `ENOSPC`/`EACCES`/a transient disk failure)
  immediately after step 2's own try/catch already caught a settle-side exception (resolves this
  revision's own FIND-301): the `"provisioning"` row for this `n` is left with NO follow-up row of any
  kind, and the `loan_${lenderId}` lock is released NORMALLY (never stale), since `withGigLock`'s own
  `finally` block releases the lock regardless of which line inside `fn()` threw. Because the
  reconciliation trigger is now driven purely by ledger STATE (an unterminated `"provisioning"` row for
  this lender's highest `n`), never by lock staleness, the VERY NEXT caller for this lender — via the
  ordinary fast-acquire path, since the lock is not stale — finds this SAME unterminated row and performs
  the SAME `reconcileProvisionalDisbursement` check BEFORE computing any new sequence number, exactly as
  it would for a stale-lock-reclaim or a `"disbursement_uncertain"` row — this is NOT a third, unhandled
  terminal state.
- The reconciliation lookup itself (`reconcileProvisionalDisbursement`) throws (e.g. an RPC timeout or
  network error during the on-chain lookup) rather than cleanly resolving to a match/no-match result
  (resolves this revision's own FIND-301): THE SYSTEM SHALL NOT compute or use any sequence number this
  attempt, and SHALL NOT append any row — the existing unterminated row is left exactly as found, and the
  lock is released normally. Because the check is now a STANDING invariant re-evaluated on EVERY
  subsequent loan-issuance attempt for this lender, this failure simply defers resolution to a later
  attempt; retrying `reconcileProvisionalDisbursement` an unbounded number of times carries zero
  double-transfer risk, since it only ever reads on-chain state, never disburses.

**Acceptance Criteria**:
- REQ-102(d)'s self-loan check (`lenderId !== borrowerId`) runs FIRST — before either lock is acquired, and
  before EITHER `evaluateColdStartKillSwitch` OR `evaluateOverallDefaultKillSwitch` is ever evaluated
  (resolves this revision's own spec-review iteration-7 FIND-603) — refusing a self-loan candidate at zero
  cost (resolves FIND-402).
- The loan-issuance critical section (a FRESH read of `loans.jsonl` → REQ-102(a)-(c) re-check → BOTH
  kill-switches' fresh re-check (`evaluateColdStartKillSwitch`/`evaluateOverallDefaultKillSwitch`, resolves
  this revision's own FIND-601) → REQ-101 read/re-check → REQ-104/105 compute → `n =
  nextLoanSequenceForLender(...)` → disbursement transfer → THIS REQUIREMENT'S OWN two-phase
  provisional/follow-up ledger append, above — NEVER REQ-108/109's own,
  separate per-loan ledger append; see the lock-key disambiguation note above, resolves this revision's
  own FIND-205) is wrapped by NESTED `withGigLock(LOANS_LEDGER_PATH, outerKey, fn)` /
  `withGigLock(LOANS_LEDGER_PATH, innerKey, fn)` calls, where `[outerKey, innerKey] =
  resolveLoanLockAcquisitionOrder(lenderId, borrowerId)` (the lexicographically-ordered pair of
  `` `loan_${lenderId}` `` and `` `loan_borrower_${borrowerId}` ``, resolves this revision's own FIND-401),
  using the SAME `lock.mjs` module for BOTH, never a reimplementation.
- `resolveLoanLockAcquisitionOrder(lenderId, borrowerId)` deterministically returns the
  lexicographically-smaller of `` `loan_${lenderId}` ``/`` `loan_borrower_${borrowerId}` `` as `outerKey`
  and the other as `innerKey`, for both possible orderings of a given lender/borrower pair — a
  Tier-0/Tier-1 structural and unit-test check confirms every issuance call site derives its lock order
  from THIS function, never an inline/ad-hoc comparison (new PROP-106m — kept as a deterministic-convention
  and forward-insurance discipline, resolves this revision's own FIND-501; NOT a deadlock-avoidance
  mechanism, which today's fail-fast `lock.mjs` does not require regardless of acquisition order — see the
  corrected justification above).
- Given two concurrent callers both targeting the SAME lender and both observing sufficient available
  surplus at read time, an integration test proves exactly one disburses; the other's attempt is
  recorded as `reason:"lock_held"` and makes zero transfer calls.
- A structural/Tier-0 check confirms EVERY call site that invokes the loan-issuance lock, or reads/writes
  `loans.jsonl`, imports and uses the SAME `LOANS_LEDGER_PATH` constant.
- Given two concurrent callers targeting TWO DIFFERENT lenders AND TWO DIFFERENT BORROWERS (each with
  zero prior loan rows), each disburses successfully and their two resulting `loan_id`s are distinct
  (`loan_${lenderA}_1` vs `loan_${lenderB}_1`) — zero collisions, using only each lender's own existing
  per-lender lock; the NEW `` `loan_borrower_${borrowerId}` `` lock (resolves FIND-401) adds zero
  contention between them since the two borrowers differ (updated this revision to state the
  two-different-borrowers precondition explicitly — the SAME-borrower, different-lender case is now a
  DIFFERENT, DELIBERATELY SERIALIZED scenario; see the next bullet, new PROP-106n).
- Given two concurrent callers targeting TWO DIFFERENT lenders but the SAME borrower (resolves this
  revision's own FIND-401): exactly ONE acquires the shared `` `loan_borrower_${borrowerId}` `` lock
  first (per the total lock-ordering rule above) and, after re-checking REQ-102 with a fresh read,
  disburses; the OTHER's own fresh re-check (performed after acquiring that SAME lock, once released)
  finds the borrower `reason:"outstanding_loan"` and refuses — zero disbursement, zero ledger row for
  the refused attempt (new PROP-106n).
- A fixture where `payViaFacilitator` is injected to fail (mocked network error) confirms the FOLLOW-UP
  row is appended with `status: "disbursement_failed"` (the PROVISIONAL row already exists for this `n`)
  and the lock is released (a subsequent call for the SAME lender computes a NEW `n+1` and can immediately
  acquire the lock).
- The loan-issuance critical section appends a PROVISIONAL row (`status: "provisioning"`) for `loan_id =
  loan_${lenderId}_${n}` BEFORE calling `payViaFacilitator`, and a FOLLOW-UP row (`status: "active"` or
  `status: "disbursement_failed"`) for the SAME `loan_id` after, per the two-phase record above (resolves
  FIND-103).
- A fixture simulating a crash AFTER `payViaFacilitator` succeeds but BEFORE the follow-up row is appended:
  a reclaiming caller's on-chain lookup (`reconcileProvisionalDisbursement`) finds the crashed attempt's
  own real transaction and appends the recovering `"active"` row WITHOUT calling `payViaFacilitator`
  again — zero double-transfer (new PROP-106g's own binding test).
- A fixture where a loan's PROVISIONAL row is appended at time `T1` and its ACTIVE/follow-up row
  (confirming successful disbursement) is appended at a LATER time `T2` (`T2 > T1`, simulating a
  reconciliation delay per PROP-106g/h/k's own fixtures) asserts `issued_ms === T2` (the active row's own
  append-time timestamp, NEVER `T1`/`provisioned_ms`), and `due_ms === T2 + LOAN_REPAYMENT_WINDOW_DAYS *
  86400000` — computed from that SAME, correct `issued_ms` value (new PROP-106o, resolves FIND-403).
- A fixture where `payViaFacilitator` is injected to (a) successfully complete `/settle` and (b) then
  THROW during `waitForTransactionReceipt` (mocked RPC timeout): confirms `fn()` catches this exception
  INSIDE the lock, appends a follow-up row with `status: "disbursement_uncertain"` before returning/
  throwing, and the lock is released normally (not left stale). A SEPARATE fixture confirms that the NEXT
  loan-issuance attempt for this SAME lender, upon finding this `"disbursement_uncertain"` row as the
  highest `n`, invokes `reconcileProvisionalDisbursement` BEFORE computing `n+1` — finding a real matching
  transfer corrects the row to `"active"`; finding none corrects it to `"disbursement_failed"` — and
  `payViaFacilitator` is never invoked a second time for this SAME `n` in either case (new PROP-106h,
  resolves FIND-201).
- A fixture where `payViaFacilitator`'s own settle-side exception is caught (as in PROP-106h's own
  fixture) but the follow-up `appendChild` call recording `"disbursement_uncertain"` is ITSELF injected to
  throw: confirms the lock is still released NORMALLY (not left stale) and, critically, that the NEXT
  loan-issuance attempt for this SAME lender — via the ordinary FAST-ACQUIRE path (never the stale-reclaim
  path) — still invokes `reconcileProvisionalDisbursement` for the unterminated `"provisioning"` row BEFORE
  computing any new sequence number, exactly as it would for a stale-lock-reclaim, proving the
  reconciliation trigger is driven by ledger state alone, never lock staleness (new PROP-106k, resolves
  FIND-301).
- A fixture where `reconcileProvisionalDisbursement`'s own on-chain lookup call is injected to THROW
  (mocked RPC timeout) confirms this specific loan-issuance attempt fails cleanly: zero sequence number is
  computed/used, zero row is appended, the lock is released normally, and the pre-existing unterminated row
  is left unchanged; a SEPARATE, later fixture confirms a SUBSEQUENT attempt for the SAME lender, with the
  lookup no longer throwing, successfully reconciles the SAME row and `payViaFacilitator` is never invoked
  as part of any reconciliation attempt (new PROP-106l, resolves FIND-301).
- A structural/Tier-0 check confirms REQ-106's own two-phase provisional/follow-up append (this
  requirement's own steps 1 and 3) never acquires, references, or is nested inside REQ-108/109's own
  per-loan `` `loan_${loan_id}` `` lock — the two locks' critical sections are structurally disjoint (new
  PROP-106i, resolves FIND-205's mislabeling by making the distinction independently checkable, not merely
  asserted in prose).
- A structural/Tier-0 check (mirroring PROP-106d's/PROP-106i's own real-source-read discipline, never a
  mocked-caller test) confirms this requirement's OWN, REAL, production issuance code — not a unit test of
  `evaluateColdStartKillSwitch` in isolation, and not an integration test against a mocked issuance call —
  actually imports and calls `evaluateColdStartKillSwitch` for a cold-start (`successfulOnTimeRepayments
  === 0`) loan request, and does so BEFORE the `` `loan_${lenderId}` `` lock-acquisition call site (new
  PROP-105h, resolves FIND-303 — closes the "a computed flag nobody checks" gap PROP-105g's own
  mocked-caller fixture cannot, by itself, close) — AND (extended this revision, resolves FIND-601)
  confirms a SECOND, separate call site to this SAME function exists INSIDE the lock-protected fresh-check
  critical section (after BOTH locks are acquired), re-evaluating it against the SAME fresh read already
  used for REQ-102(a)-(d)/REQ-101/REQ-104/105's own recheck — never merely the pre-lock call site alone.
- A structural/Tier-0 check (mirroring PROP-105h's own real-source-read discipline) confirms this
  requirement's OWN, REAL, production issuance code ALSO imports and calls
  `evaluateOverallDefaultKillSwitch` for EVERY loan request, regardless of tier, BEFORE the
  `` `loan_${lenderId}` `` lock-acquisition call site, IN ADDITION TO `evaluateColdStartKillSwitch` (new
  PROP-114c, resolves this revision's own FIND-502) — AND (extended this revision, resolves FIND-601)
  confirms a SECOND, separate call site to THIS SAME function ALSO exists INSIDE the lock-protected
  fresh-check critical section, re-evaluating it against the SAME fresh read already used for
  REQ-102(a)-(d)/REQ-101/REQ-104/105's own recheck, IN ADDITION TO its own pre-lock call site — AND
  (extended this revision, resolves FIND-602) confirms this SAME call site also computes
  `computeRecentDefaultLossUsd({loanRows, nowMs})` and passes its `totalRecentDefaultLossUsd` output into
  `evaluateOverallDefaultKillSwitch`, never omitting this new input.
- A fixture where a kill-switch's underlying inputs are HEALTHY (`paused:false`) at the moment of a
  specific attempt's own pre-lock check, but the SAME kill-switch's inputs change (simulating a concurrent
  event — e.g. a different, concurrent issuance attempt's own default landing) such that its fresh,
  lock-protected re-evaluation (inside the SAME critical section as REQ-102(a)-(d)/REQ-101/REQ-104/105's
  own fresh re-check) now returns `paused:true`, confirms the attempt is refused AT THAT FRESH RE-CHECK —
  zero disbursement, zero ledger row appended — even though its own EARLIER, pre-lock check alone would
  have permitted it (new PROP-106p, resolves this revision's own spec-review iteration-7 FIND-601).

---

### REQ-107: Chain/asset scope narrowing — Base-mainnet USDC only, this increment
**EARS**: THE SYSTEM SHALL restrict every loan transfer (disbursement AND repayment) in this increment
to Base-mainnet-EVM-denominated USDC transfers only, reusing exactly the already-proven single-signer
transfer primitive this colony already has
(`~/anicca/skills/economy/gig/lib/escrow.mjs::payViaFacilitator`, gasless via the self-host x402-rs
facilitator). A Solana-denominated lender/borrower pair (e.g. Franklin's own Solana wallet,
`8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9`) is OUT OF SCOPE for THIS increment's loan mechanism — no
proven single-signer Solana USDC transfer primitive currently exists anywhere in this codebase (checked
this session: `escrow.mjs`/`execute-ubi.py`/`economy/gig` are all Base-EVM-only; Franklin's own Solana
settlement is a DIFFERENT protocol layer, `x402` self-facilitated trading, not exposed as a simple
wallet-to-wallet transfer helper reusable here). This applies the SAME "documented, deliberate
limitation, not an oversight" discipline `anicca-agent-spawn` REQ-106 established for host co-location —
REQ-112 below is this feature's own DIRECT, by-name analog of that precedent, applied to WHICH HOSTS
lending participants may run on (a separate axis from this requirement's own chain/asset-type scoping).

**Edge Cases**:
- A citizen whose ONLY wallet is Solana-denominated (no `wallet.evm` entry): excluded from BOTH lender
  and borrower eligibility this increment — REQ-101/102 both additionally require `wallet.evm` truthy —
  not because it fails `isSelfFunded()` (which only requires evm OR solana presence), but because this
  increment's transfer mechanism structurally cannot move funds for it.
- A future increment adds a proven single-signer Solana USDC transfer primitive: this feature's chain
  scope MAY then be widened — an explicit, deliberately deferred extension point, not a promise made by
  this spec.

**Acceptance Criteria**:
- REQ-101/102's eligibility functions accept only citizen records whose `wallet.evm === true`.
- A structural/Tier-0 check confirms no code path in this feature's disbursement/repayment step ever
  constructs a Solana transaction or imports a Solana signing library.

---

### REQ-112: Loan issuance/repayment participation is scoped to a single coordinator host, this increment only (resolves this revision's own FIND-002; direct analog of `anicca-agent-spawn` REQ-106; co-location mechanism corrected this revision, resolves FIND-305)
**EARS**: THE SYSTEM SHALL perform every REQ-101/102/104/105/106/108/109 evaluation, lock acquisition, and
`loans.jsonl` read/write EXCLUSIVELY among lending participants — BOTH the lender AND the borrower, not
merely a single evaluator as in `anicca-agent-spawn`'s own analogous case — that are co-located with the
coordinator: currently the Mac Mini (`anicca-mac-mini-1`) that today's real colony (Franklin — automaton
was removed from the self-funded citizen set per Dais's 2026-07-08 directive, see
`anicca-agent-spawn`'s own `citizens.seed.json`) already runs on, for the full duration of THIS increment. This is the precondition that makes REQ-106's
`lock.mjs` (a local-POSIX-filesystem primitive) and the reused `ledger.js`'s local append-only
`loans.jsonl` file CORRECT as specified — restating, almost verbatim, `anicca-agent-spawn` REQ-106's own
words for its own, analogous reuse of the SAME two primitives ("This constraint is what makes REQ-103's
`lock.mjs`... and REQ-305's `ledger.js`... CORRECT as specified: both mechanisms only need to
serialize/record callers that share the SAME mounted filesystem"): both mechanisms here only need to
serialize/record lending participants that share that SAME mounted filesystem, which holds precisely
because every lender and every borrower in this increment IS co-located on that one coordinator host.
Unlike spawn (where only ONE coordinator ever evaluates/executes), lending is inherently two-party — a
lender's own process must hold the lender's own private key to disburse, and a borrower's own process
must hold the borrower's own private key to repay — so THIS requirement's co-location assumption spans
BOTH parties' own runtimes, not just a single evaluator's.

**Co-location mechanism, corrected this revision (resolves FIND-305 — a critical defect in the PRIOR
mechanism, not merely a stale citation):** THE SYSTEM SHALL determine co-location eligibility EXCLUSIVELY
via `citizen.coLocatedWithCoordinator === true` — a purpose-built boolean field `anicca-agent-spawn`
(re-read fresh this revision) has ALREADY added to its own `citizens.json` registry schema specifically to
answer this exact "is this citizen co-located" question (seeded `true` for every currently-seeded citizen,
`false` for every future spawned child, since `anicca-agent-spawn` REQ-301 mandates every spawned child is
cloud-hosted). THE SYSTEM SHALL NOT derive co-location from `homeDir` equality — a PRIOR revision of this
requirement did exactly that, and was WRONG on two counts, both confirmed this revision: (a) factually,
AT THE TIME this fix was made, the real seed data did NOT give automaton and Franklin the identical
`homeDir` this requirement previously assumed — `anicca-agent-spawn`'s registry seeded automaton at
`homeDir: "/Users/anicca/.anicca"` and Franklin at `homeDir: "/Users/anicca/.blockrun"`, two DISTINCT
values, so a literal `homeDir`-equality check would have incorrectly concluded those two real,
genuinely-co-located citizens were NOT co-located with each other, potentially blocking the exact
automaton↔Franklin lending scenario this fix was made to unblock (automaton was subsequently removed from
the self-funded citizen set entirely per Dais's 2026-07-08 directive — this historical illustration of the
`homeDir`-equality bug remains valid regardless, since the mechanism itself, `coLocatedWithCoordinator`,
is generic over whichever citizens are actually seeded); (b) structurally, `anicca-agent-spawn`'s
own adversary-hardened design (its own FIND-501/FIND-703 resolutions) has ALREADY explicitly established
and documented, in its own spec, that "co-located (same physical host) does NOT mean 'same `homeDir`'" —
each citizen retains its own distinct `ANICCA_HOME` root even on a shared machine — and added
`coLocatedWithCoordinator` as "a structural fact about physical placement, not an inference from `homeDir`
or any other field," precisely so no consumer (including THIS feature) ever has to re-derive co-location
from `homeDir` (or any other proxy) again. Reusing that sibling's own already-correct, already-hardened
field is a STRICT improvement over this requirement's own prior, now-known-wrong `homeDir`-equality
mechanism — never a weaker or merely-equivalent substitute. THE SYSTEM SHALL THEREFORE treat BOTH the
lender AND the borrower of a candidate loan as co-located-eligible for this increment's mechanism IF AND
ONLY IF `citizen.coLocatedWithCoordinator === true` for EACH of them — a loan request where either party's
own `coLocatedWithCoordinator` is `false` (or absent/malformed) is refused under this requirement,
fail-closed, exactly as any other REQ-101/102 pre-lock eligibility refusal.

**Edge Cases**:
- A future `anicca-agent-spawn` REQ-301 produces a genuinely remote-cloud-hosted child citizen (NOT
  co-located with the coordinator; that spec's own `citizens.json` schema records `coLocatedWithCoordinator:
  false` for every such child, per REQ-305's own always-`false`-for-spawned-children rule, and already
  anticipates "a dedicated per-instance HOME if the colony ever runs non-co-located instances"): lending TO
  or FROM such a remote citizen is explicitly OUT OF SCOPE for this increment's mechanism, and is
  structurally excluded by this requirement's own `coLocatedWithCoordinator === true` check above without
  any special-casing. THE SYSTEM SHALL NOT
  silently assume the existing local-filesystem lock/ledger already works cross-host — no code path in
  this feature attempts a loan with a non-co-located participant. This is an explicit, documented, KNOWN
  LIMITATION of this increment, not an oversight: a future increment would need a different (not-yet-
  designed) mechanism before cross-host lending is safe, mirroring `anicca-agent-spawn` REQ-106's own
  identical framing for its analogous multi-host case. Researched 2026-07-07 (not designed/built this
  increment, recorded here only so the destination is known and today's design doesn't paint itself into a
  corner): the simplest realistic path found is NOT a general distributed-consensus system (existing
  multi-agent frameworks — CrewAI/AutoGen/LangGraph — do not solve real cross-host coordination without a
  shared broker; Autonolas/Olas solves it but via a heavyweight Tendermint-BFT-plus-multisig stack, likely
  overkill here) — instead, (a) the non-monetary claim/lock itself (e.g. "is this loan_id/sequence already
  taken") can be re-hosted as a single HTTPS claim API on the coordinator that any host calls with
  optimistic-concurrency retry, the same mutual-exclusion shape `lock.mjs` already provides, just reachable
  over a network instead of a local mount; (b) the actual money-moving step already has a REAL, free,
  on-chain double-spend guard via x402/EIP-3009's per-payment nonce (the SAME mechanism `payViaFacilitator`
  already uses) — but this nonce prevents re-EXECUTING the identical transfer, it does NOT prevent the
  "decision" race this spec's own FIND-103 fix addresses (two hosts independently deciding to disburse
  BEFORE either payment lands) — so the decision-serialization problem still needs (a)'s claim API even
  once money-movement itself is on-chain-safe. A genuine on-chain claim REGISTRY (a `require(!claimed[id])`
  pattern, proven in bounty-contract designs) would be the money-safety-grade version of (a) for a future
  increment where lending participants are never co-located at all.
- Multiple loan-issuance evaluations on the SAME coordinator host race in the same wake window: this is
  exactly the scenario REQ-106's lock already handles (both are local callers sharing one filesystem) —
  this is the ONLY concurrency scenario this increment's lock/ledger design needs to survive.
- The coordinator host itself becomes unavailable (hardware failure, network partition): no OTHER host
  picks up loan-issuance/repayment-verification evaluation in this increment (single coordinator, by
  design) — an accepted single-point-of-failure for this increment's scope, matching the colony's actual
  current topology.
- A citizen record's `coLocatedWithCoordinator` field is missing, non-boolean, or otherwise malformed
  (resolves this revision's own FIND-305's fail-closed corollary): THE SYSTEM SHALL treat that citizen as
  NOT co-located (fail-closed — never default to `true`), excluding it from either role in a candidate
  loan, mirroring REQ-101/102's own fail-closed convention for other malformed-input cases.

**Acceptance Criteria**:
- A structural/Tier-0 check confirms this feature's `lock.mjs` acquire/release path and `ledger.js`
  read/write path (via `LOANS_LEDGER_PATH`) are invoked only from code that assumes a single, shared,
  local `loans.jsonl`/`locks/` directory — no code path constructs a remote/networked path or attempts to
  reach a non-co-located citizen's own filesystem.
- A structural/Tier-0 check confirms this feature's co-location eligibility check reads ONLY
  `citizen.coLocatedWithCoordinator` — no code path anywhere in this feature's diff compares two citizen
  records' `homeDir` fields for equality, or otherwise derives co-location from `homeDir`, as a
  co-location check (resolves FIND-305; corrects the prior `homeDir`-equality mechanism this requirement
  specified before this revision).
- A fixture pair of citizens each with `coLocatedWithCoordinator: true` (mirroring the historical
  automaton/Franklin seed data this fix was validated against, which had DISTINCT `homeDir` values but
  IDENTICAL `coLocatedWithCoordinator: true` — today's real seed data has only ONE entry, Franklin, since
  automaton's 2026-07-08 removal, so this remains a synthetic two-citizen fixture for exercising the
  two-party mechanism, not literally today's live seed) is correctly treated as co-location-eligible for both lender and
  borrower roles — proving this requirement's own mechanism does NOT incorrectly exclude today's real,
  genuinely-co-located citizens the way a `homeDir`-equality check would have (resolves FIND-305).
- This spec's own Scope section states lending TO/FROM a remote-cloud-hosted citizen is out of scope this
  increment, so a fresh adversary reviewing REQ-106/REQ-112 does not need to (and must not be asked to)
  prove cross-host correctness for this increment.

---

### REQ-113: Dependency freshness gate — `anicca-agent-spawn` re-verification before Phase 2a (resolves this revision's own FIND-101; a direct recurrence of iteration-1's FIND-006, one full revision cycle later)
**EARS**: WHERE this feature's REQ-101/102/109/112 depend conceptually on `anicca-agent-spawn`'s
STILL-MID-PIPELINE citizen registry shape and surplus-computation design (see Dependencies section
above) — CONCRETELY, and NOT merely as a generic "re-read the sibling spec" instruction (corrects this
revision's own FIND-305, which found this feature's own PRIOR reliance on that registry shape had
actually gone stale/wrong in two concrete, checkable ways an unspecific re-read step failed to catch):
(a) REQ-109's `adjustBalancesForOutstandingDebt` composition point depends on that sibling spec's REAL
`filterProductiveCitizens` → `readCitizenBalances` → `computeColonySurplusUsd` pipeline SHAPE (resolves
FIND-304), and (b) REQ-112's co-location eligibility check depends on that sibling spec's
`coLocatedWithCoordinator` field EXISTING on every citizen record and being CORRECTLY populated (resolves
FIND-305) — THE SYSTEM'S OWN Phase 2a (test-writing) SHALL NOT BEGIN until whoever begins that phase has
RE-READ `anicca-agent-spawn`'s THEN-CURRENT `specs/behavioral-spec.md` and `state.json` fresh, immediately
before starting, and has recorded in writing (e.g. a dated note alongside this feature's own Phase 2a
RED-phase evidence) that this re-read occurred, EXPLICITLY confirming (not merely asserting a re-read
happened) whether (a) the three-step pipeline shape and (b) the `coLocatedWithCoordinator` field's
presence/population are STILL as this revision describes them, and whether anything ELSE material changed
since this spec's own iteration-4 citation. This is a STANDING acceptance criterion / Tier-0 process gate
for this feature's own Phase 2a start — not a one-time citation-accuracy fix to get right during spec
review.

Rationale (why this is a REQ, not merely a Dependencies-section footnote): iteration-1's FIND-006 already
demonstrated this exact citation goes stale between revisions; this revision's own FIND-101 demonstrates
it AGAIN, one full iteration-cycle later — and, re-verified in the course of resolving FIND-101,
`anicca-agent-spawn`'s OWN Phase 1c gate has, in the interim, FAILed a THIRD time (iteration 6,
`2026-07-07T11:02:55.800Z`, FIND-501..504), with the iteration-5/FIND-401..405 state FIND-101's own
evidence cited as "current" already superseded before this resolution was even written.
`anicca-agent-spawn` is a moving target BY CONSTRUCTION (an independently-evolving sibling spec, still
mid-VCSDD-pipeline); no snapshot of its iteration number or finding list, frozen inside THIS document,
can ever stay accurate across the gap between a spec-review pass and this feature's own later Phase
2a/2b start. THE SYSTEM therefore treats "re-verify at first use" as the correct discipline, not "keep the
citation updated" (an unwinnable maintenance race against a sibling feature's own independent cadence).

**Edge Cases**:
- `anicca-agent-spawn` reaches Phase 1c PASS with a materially different registry/join shape (e.g.
  `citizens.json`'s field set changes, or dual evm+solana aggregation semantics change per that spec's own
  FIND-404/FIND-503) before this feature's Phase 2a begins: THE SYSTEM SHALL revisit REQ-101/102/109/112
  at that time — this requirement's own re-read step is what surfaces that need, rather than an
  implementer silently building against a stale mental model carried over from spec review.
- `anicca-agent-spawn`'s Phase 1c is STILL failing (as it has for 6+ consecutive iterations as of this
  writing) when this feature's Phase 2a begins: THE SYSTEM SHALL proceed anyway — this feature's own
  REQ-101/105/109/112 depend only on that spec's registry SHAPE and surplus-arithmetic STYLE, not on that
  spec reaching PASS first; REQ-112's own Edge Cases already document that `citizens.json` itself does not
  yet exist on disk, and this feature's own borrower/lender arithmetic is designed to tolerate that
  (REQ-101/102 operate on whatever citizen records are actually readable at evaluation time, never
  blocking on a sibling feature's own pipeline state). **Corrected this revision (resolves FIND-305):**
  the base field set is NOT, in fact, fully stable across that sibling spec's own iterations the way a
  prior revision of THIS requirement claimed — `coLocatedWithCoordinator` was ADDED to that field set by
  that sibling spec's own FIND-703 resolution, and `homeDir`'s own SEED VALUES were corrected by that same
  spec's own FIND-501 resolution (from an identical bare `/Users/anicca` for both citizens to each
  citizen's real, distinct `ANICCA_HOME` root) — both AFTER this feature's own iteration-3 citation was
  written. This is exactly why REQ-113's own re-read step must concretely re-confirm (a)/(b) above at each
  Phase 2a start, never merely assert "the shape is stable" as a standing fact.
- A future revision of THIS spec is tempted to update the Dependencies section's `anicca-agent-spawn`
  citation to a new specific iteration number: REJECTED — the fix for FIND-101 is to STOP citing a
  specific iteration number there at all (see Dependencies section, revised), not to substitute a fresher
  one that will itself go stale.

**Acceptance Criteria**:
- This feature's Phase 2a start (test-generation) artifacts (e.g. the RED-phase evidence file, or a dated
  note alongside it) include an explicit, dated confirmation that `anicca-agent-spawn`'s
  `specs/behavioral-spec.md` and `state.json` were re-read fresh on that date, stating the
  iteration/phase/gate-verdict observed at that moment — never a copy-pasted reference to this
  spec-review's own iteration-3/iteration-4 snapshot.
- **(resolves FIND-305)** That SAME dated confirmation explicitly states, as its own separate line items
  — not folded into a generic "re-read occurred" sentence — (a) whether `anicca-agent-spawn`'s
  `filterProductiveCitizens` → `readCitizenBalances` → `computeColonySurplusUsd` three-step pipeline shape
  is still as REQ-109's own composition-point description assumes, and (b) whether
  `coLocatedWithCoordinator` still exists on every `citizens.json` record and is still correctly populated
  (`true` for co-located citizens, `false` for cloud-hosted ones) as REQ-112's own eligibility check
  assumes — a re-read note that omits either explicit confirmation does NOT satisfy this requirement.
- The Dependencies section above never states a specific `anicca-agent-spawn` iteration number, FIND-list,
  or `state.json` gate verdict as a durable fact of THIS document — only as a "re-read this session"
  observation, explicitly time-stamped and explicitly flagged as certain to be stale by the time Phase
  2a/2b actually begins.

---

### REQ群D: Repayment + default

### REQ-108: Repayment verification mechanism
**EARS**: WHEN a borrower claims to have repaid an outstanding loan, THE SYSTEM SHALL mark that loan
`"repaid"` only after an INDEPENDENT on-chain check confirms it — never accepted from either party's own
self-report alone, applying the SAME "independent re-verification, never trust self-report" PRINCIPLE
`anicca-agent-spawn` REQ-401 and SPEC.md §9.9 already establish. **This revision corrects a prior false
claim that `verifyRepayment` "reuses `escrow.mjs`'s own already-imported `viem`/`createPublicClient`
dependency" for `Transfer`-log parsing: re-read this session, `escrow.mjs`'s `settleBody` (lines 124-140)
contains NO `Transfer`-event-log parsing at all — it only calls `waitForTransactionReceipt({hash})` and
checks `receipt.status`, never reading `receipt.logs`/`topics`/`from`/`to`/`value`.** The REAL, already-
hardened precedent for exactly this operation (decode an ERC-20 `Transfer` log, verify `from`/`to`, extract
`value`) is `~/anicca/skills/self/founder-loop/record-earn.mjs` (re-read this session, lines 56, 65-72,
82-88), and `verifyRepayment` SHALL reuse THAT pattern, not re-derive it:
(a) the claimed repayment transaction hash's own receipt (`getTransactionReceipt`) shows `status:
success`, AND that transaction's own block is at or before the current FINALIZED block — re-queried via
`eth_getBlockByNumber("finalized", false)`, the SAME finalized-block-only discipline `record-earn.mjs`'s
own `blockNow()` (lines 65-72) already established ("a Transfer in a block that later reorgs would be
counted though it never settled") — never trusting an un-finalized `"latest"` read for this money
invariant;
(b) that transaction's own `Transfer(from, to, value)` event log is decoded using the SAME
`TRANSFER_TOPIC` constant `record-earn.mjs`'s own `parseRawLogs` (lines 82-88) already uses
(`0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`), and the `to` topic checked via
EXACT zero-padded-address equality (`"0x" + "0".repeat(24) + expectedToLower`) against the lender's own
recorded `walletAddress.evm` — a LITERAL REUSE of `record-earn.mjs`'s own already-hardened, previously
adversary-tested `to`-side check ("`// FIND-704: exact padded-topic equality, not a suffix match`", line
87), NEVER a substring/suffix match. **Corrected this revision (resolves this revision's own FIND-105 — a
prior overclaim):** `record-earn.mjs`'s own `FIND-704` fix applies ONLY to the `to` topic (`topics[2]`) —
its `from` topic (`topics[1]`) is extracted via an UNCHECKED substring (`'0x' + String(l.topics[1]).slice
(26)`, line 88) and is only ever SET-MEMBERSHIP-tested afterward (`sumExternal`, line 77: is `from` ∈
`MY_WALLETS`?), a fundamentally different verification shape than an exact-equality check against ONE
specific expected address. `verifyRepayment` therefore does NOT literally reuse an already-tested code
path for the `from` side — it EXTENDS the proven `to`-side exact-padded-equality TECHNIQUE to also apply,
as a NEW, sound application of that technique, to the `from` topic: decoded the same way (`"0x" +
"0".repeat(24) + expectedFromLower`) and compared via the SAME exact zero-padded equality against the
borrower's own recorded `walletAddress.evm` — still the correct, more rigorous design choice (arguably
MORE rigorous than `record-earn.mjs`'s own precedent, which never needed an exact `from`-equality check
for its own different purpose), just honestly attributed as an extension, never a re-derivation-free
reuse; `value` (converted to USD) summed with any PRIOR verified partial repayments for this SAME
`loan_id` reaches at least `total_due_usd` (REQ-104). Verification NEVER trusts the RPC's own
server-side `eth_getLogs`/filter result for this money invariant — mirroring `record-earn.mjs`'s own
documented discipline ("`// never trust the RPC's server-side filter for a money invariant — FIND-603`"):
even though `verifyRepayment` queries one already-known `txHash`'s receipt directly (not a `getLogs` range
scan), the receipt's own `logs` array is re-filtered/re-checked IN-PROCESS exactly as `record-earn.mjs`
already does, never assumed pre-filtered correctly by the provider. Attribution uses the transaction's own
event log, NOT a bare before/after balance delta, so an unrelated coincidental inflow to the lender's
wallet in the same window is never mistaken for a repayment.

**`txHash` uniqueness / replay-rejection (resolves this revision's own FIND-202 — a critical double-credit/
replay risk the three checks above do not, by themselves, close):** the three checks above (receipt
success + finalized block; exact `to`/`from` topic-equality; `value` reaching `total_due_usd` when summed
with priors) are satisfied IDENTICALLY whether the caller supplies a genuinely NEW, never-before-credited
transaction hash or RESUBMITS a `txHash` that was ALREADY verified and credited — toward THIS SAME
`loan_id` OR toward ANY OTHER `loan_id` in this colony's ledger. THE SYSTEM SHALL THEREFORE, BEFORE
crediting any `value` toward a claimed repayment's `total_due_usd`, read the FULL `loans.jsonl` ledger and
collect the set of every `txHash` ALREADY recorded on a previously-verified, credited repayment row (every
row this feature itself appended after a PRIOR successful `verifyRepayment` call, across ALL `loan_id`s,
never merely the one currently under verification) — and REJECT the newly-claimed `txHash` (crediting `0`,
exactly as any other failed-verification case) if it is already present in that set, regardless of how
genuinely valid/finalized/correctly-attributed that transaction otherwise is. This closes BOTH: (a) a
SAME-loan replay, where a caller resubmits an already-credited `txHash` against its OWN `loan_id`
repeatedly, attempting to inflate the cumulative `repaid_usd` sum past `total_due_usd` using only ONE real
transfer; and (b) a CROSS-loan replay, where a borrower who genuinely repaid an EARLIER loan (`loan_id` A)
resubmits THAT loan's already-credited `txHash` as claimed proof of repayment toward a LATER loan
(`loan_id` B) to the SAME lender — `verifyRepayment`'s own three checks would otherwise pass identically
for both loans, since the underlying transaction is real, finalized, and its `from`/`to` still match. This
is performed IN-PROCESS by `verifyRepayment` itself, over already-read ledger rows (the SAME full read
this function already performs for REQ-101/108's own last-write-wins reductions elsewhere in this spec) —
zero new I/O, never a per-loan-scoped check alone.

**"Logged," precisely defined (resolves this revision's own FIND-302 — a genuine ambiguity, not merely an
imprecise word choice):** a rejected replay (same-loan OR cross-loan) is recorded EXCLUSIVELY via an
OUT-OF-BAND mechanism — e.g. a separate audit/trace log file, or a debug-level log line emitted by
`verifyRepayment` itself — and THE SYSTEM SHALL NEVER, under any circumstance, append a NEW row to
`loans.jsonl` for a rejected replay attempt. This is a binding SHALL, not a stylistic preference: EVERY
OTHER reduction this spec specifies (`sumOutstandingPrincipalUsd`, `isBorrowerEligible`'s condition (c),
`countSuccessfulOnTimeRepayments`, `detectDefaultedLoans`, `computeColdStartRepaymentRate`) treats the
LAST-appended row for a given `loan_id` as that loan's single authoritative current state (last-write-wins,
established throughout this document). A rejected replay changes NOTHING about the loan's real,
already-established status — the loan's `repaid_usd`/`status` are exactly what they were the instant
before the replay attempt was rejected — so appending ANY row for it, however faithfully that row's own
fields might be copied from the loan's true prior state, would needlessly become the new "last row" for
that `loan_id` and introduce a real risk of accidental divergence from that true state (e.g. a copy-paste
omission of one field) silently corrupting every downstream last-write-wins read for that loan. THE SYSTEM
THEREFORE writes ZERO new rows to `loans.jsonl` for a rejected replay, in either the same-loan or
cross-loan case — the ONLY effect of a rejected replay on any file this feature owns is whatever
out-of-band audit/trace entry the chosen logging mechanism produces, entirely outside the last-write-wins
convention this spec's every OTHER computation depends on.

**Per-loan write discipline (resolves this revision's own FIND-104 — a race between concurrent repayment
verification and default detection):** Because REQ-109's own default-detection sweep and this
requirement's own repayment-verification call both `appendChild` NEW status-transition rows to the SAME
shared `loans.jsonl` for a loan that could be evaluated by BOTH at nearly the same instant (a repayment
landing just as a sweep crosses `due_ms`), THE SYSTEM SHALL wrap the read-verify-append critical section
of BOTH this requirement (REQ-108) and REQ-109's own default-detection-and-append step in a NEW, PER-LOAN
lock, key `` `loan_${loan_id}` `` — DELIBERATELY DIFFERENT from REQ-106's own PER-LENDER
`` `loan_${lenderId}` `` issuance lock (a different natural key for a different critical section:
issuance contends on the LENDER's own surplus; repayment/default status transitions contend on ONE
EXISTING loan's own status), using the SAME `withGigLock` mechanism and the SAME `LOANS_LEDGER_PATH`
`statePath`. **This per-loan lock is NEVER acquired, nested, or otherwise involved during REQ-106's own
issuance-time critical section** — REQ-106's own two-phase provisional/follow-up ledger append (its own
steps 1 and 3) is appended EXCLUSIVELY under REQ-106's own per-lender lock, never under this lock
(resolves this revision's own FIND-205, which found REQ-106's own Acceptance Criteria mislabeling its own
issuance-time append as a "REQ-108/109 ledger append"). This ensures a repayment-verification call and a
default-detection sweep for the SAME
`loan_id`, launched concurrently, can NEVER both append: exactly one acquires the `loan_${loan_id}` lock
and completes its read-verify-append; the other observes the lock held, fails closed (`reason:
"lock_held"`), and defers to its own next scheduled pass (REQ-109's sweep already runs on a schedule; a
rejected repayment-verification call is simply retried the next time that borrower/lender's own wake
evaluates it).

**Edge Cases**:
- A default-detection sweep (REQ-109) is evaluating the SAME `loan_id` at the same moment a
  repayment-verification call lands for a genuinely just-settled transaction: the `loan_${loan_id}` lock
  (above) ensures only one of the two actually appends; the other retries on its own next pass rather than
  racing to append a status-transition row (resolves FIND-104).
- The repayment transaction succeeds but moves LESS than the amount still owed (a partial repayment):
  `repaid_usd` is updated to the new cumulative total, but the loan remains `"active"` — it is not
  marked `"repaid"` until the cumulative total reaches `total_due_usd`.
- A caller resubmits a `txHash` that was already verified and credited toward THIS SAME `loan_id`'s own
  `repaid_usd`: THE SYSTEM SHALL reject it — credit `0`, recorded ONLY via the out-of-band audit/trace
  logging mechanism above, NEVER a new `loans.jsonl` row (resolves FIND-302's own ambiguity) — it does NOT
  double-count the same real transfer twice toward the SAME loan's own `total_due_usd` (resolves
  FIND-202).
- A caller submits a `txHash` that was already verified and credited toward a DIFFERENT `loan_id` (a
  cross-loan replay — e.g. resubmitting an earlier, already-repaid loan's own transaction as claimed proof
  for a later loan to the SAME lender): THE SYSTEM SHALL reject it identically — credit `0`, recorded ONLY
  via the SAME out-of-band mechanism, NEVER a new `loans.jsonl` row — a
  real, finalized, correctly-attributed transaction is still rejected if its `txHash` is already recorded
  as credited anywhere else in the ledger (resolves FIND-202).
- The claimed transaction hash does not exist, reverted, its block is not yet finalized, or its
  `Transfer` event's `to` address is NOT an EXACT zero-padded match for the lender's own recorded wallet
  (a substring/suffix match is NEVER sufficient, per `FIND-704` above): THE SYSTEM SHALL credit `0`
  (fail-closed) — never assume good faith from an unverified claim.
- The lender's wallet balance also increased in the same window from an unrelated, coincidental inflow
  (e.g. a separate gig payout landing simultaneously): the event-log-based attribution (not a bare
  balance delta) ensures only the SPECIFIC repayment transaction's own value is credited.

**Acceptance Criteria**:
- A real repayment transaction's receipt is independently re-queried via a SEPARATE RPC call from the
  one either the lender or borrower's own process performed, matching `anicca-agent-spawn` REQ-401's
  PROP-401a precedent exactly.
- Verification reads the transaction's own `Transfer` event log using EXACT zero-padded-topic equality
  for BOTH `to` and `from` (never a substring/suffix match on either side) — the `to`-side check is a
  LITERAL REUSE of `record-earn.mjs`'s own proven `FIND-704` fix; the `from`-side check is a NEW, honest
  EXTENSION of that same technique, not a literal reuse of an already-tested code path for that field
  (resolves FIND-105) — never merely a raw balance delta (closes the "unrelated coincidental inflow"
  false-positive edge case above), and never trusts an un-finalized block (per `record-earn.mjs`'s own
  finalized-block-only discipline).
- A fixture with a partial-then-full repayment (two transactions summing to `total_due_usd`) correctly
  transitions the loan from `"active"` (after the first, partial transaction) to `"repaid"` (after the
  second).
- A fixture with a `Transfer` log whose `to` topic is a SUFFIX match but NOT an exact zero-padded match
  for the lender's own wallet (the exact bug class `FIND-704` already fixed once in this colony) is
  correctly REJECTED (credits `0`), never mistaken for a valid repayment.
- A SEPARATE fixture with a `Transfer` log whose `from` topic is a SUFFIX match but NOT an exact
  zero-padded match for the borrower's own wallet is correctly REJECTED (credits `0`) — proving the
  `from`-side EXTENSION is genuinely implemented as an exact-equality check, not the unchecked substring
  `record-earn.mjs` itself uses for that field (resolves FIND-105).
- A fixture with a real, valid, finalized, correctly-attributed `txHash` already credited once toward its
  own `loan_id`'s `total_due_usd`: a SECOND `verifyRepayment` call resubmitting the SAME `txHash` against
  the SAME `loan_id` is rejected, crediting `0` — the loan's `repaid_usd` is NOT incremented a second
  time.
- A SEPARATE fixture proves the CROSS-loan replay case: a `txHash` already credited toward loan A (a
  different `loan_id`) is rejected when resubmitted as claimed proof of repayment toward loan B —
  crediting `0` for loan B despite the underlying transaction being genuinely valid/finalized (new
  PROP-108e, resolves FIND-202).
- BOTH the same-loan and cross-loan replay fixtures above assert `loans.jsonl` gains ZERO new rows as a
  result of the rejected replay attempt — a structural/Tier-0 read of `verifyRepayment`'s own source
  confirms its replay-rejection branch never calls `appendChild` (resolves FIND-302's own out-of-band
  logging requirement; whatever audit/trace log entry the rejection produces is asserted to live outside
  `loans.jsonl` entirely).
- A repayment-verification call and a default-detection sweep for the SAME `loan_id`, launched
  concurrently (`Promise.all`), never both append a new row: an integration test proves exactly one
  acquires the `loan_${loan_id}` lock and appends; the other returns `reason:"lock_held"` and appends
  nothing (new PROP-108d, resolves FIND-104).

---

### REQ-109: Default detection & handling
**EARS**: WHEN a loan's `due_ms` (`issued_ms + LOAN_REPAYMENT_WINDOW_DAYS * 86400000`, where `issued_ms`
is the `"active"` row's own append-time timestamp — see REQ-106's precise definition, resolves this
revision's own FIND-403 — NEVER the provisional row's own `provisioned_ms`) has passed AND
its last-appended row's `repaid_usd` is still less than `total_due_usd`, THE SYSTEM SHALL, at the next
scheduled evaluation, append a NEW row for that same `loan_id` with `status: "defaulted"` — never
mutate or delete the existing row (append-only, matching `ledger.js`'s own discipline). This `"defaulted"`
row ALSO carries a NEW `defaulted_ms` field (added this revision, resolves this revision's own spec-review
iteration-7 FIND-602) — the wall-clock time (`Date.now()`) at the moment THIS row itself is appended,
mirroring REQ-106's own `issued_ms`-precision convention exactly (set at confirmation/append time, never
backdated) — required so REQ-114's own new rolling-window absolute-default-loss signal,
`computeRecentDefaultLossUsd`, can determine whether a given default falls within its own lookback window.
A row whose `status` is NOT `"defaulted"` (e.g. `"active"`, `"repaid"`) carries no `defaulted_ms` field.
**This prose definition, by itself, is not sufficient proof that the REAL, production append code below
actually sets this field at append time** — see this requirement's own separate Tier-0 structural check
(PROP-109g, resolves this revision's own spec-review iteration-8 FIND-702) for that real-code confirmation,
mirroring PROP-105h's/PROP-106d's/PROP-114c's own real-source-read discipline exactly. This append is
performed STRICTLY INSIDE the SAME per-loan `loan_${loan_id}` lock REQ-108 specifies (resolves this
revision's own FIND-104) — never an unlocked read-then-append, since this exact `loan_id` could
simultaneously be undergoing repayment verification. THE SYSTEM SHALL NOT silently continue offering that
borrower further loans: REQ-102's no-outstanding-obligation
condition (c) already structurally blocks this, since a `"defaulted"` row IS a currently-open, non-
`"repaid"` obligation (this rule is unaffected by the fix below — REQ-102 was already correct; only the
colony-surplus SIDE EFFECT, next, was disproportionate). THE SYSTEM SHALL ALSO adjust that borrower's own
contribution to any colony-wide surplus/eligible-citizen aggregation this codebase performs (today:
`anicca-agent-spawn`'s three-step `filterProductiveCitizens` → `readCitizenBalances` →
`computeColonySurplusUsd` pipeline, re-read fresh this revision — see the composition-point correction
below, resolves FIND-304) to REFLECT its own
currently-defaulted, unrecovered debt — realized via a SECOND, lending-owned composition pass,
`adjustBalancesForOutstandingDebt({citizens, loanRows}) → citizens[]` (pure, zero I/O; resolves this
revision's own FIND-204, which found the PRIOR design here, `excludeDefaultedBorrowers`, disproportionate).

**This is a balance ADJUSTMENT, not a citizen REMOVAL (corrects the prior design):** the prior
`excludeDefaultedBorrowers` function REMOVED a defaulted citizen's entire record from the array feeding
`computeColonySurplusUsd`, zeroing that citizen's WHOLE current balance's contribution to colony-wide
spawn-eligibility surplus — disproportionate to a debt that, per REQ-104, can be as small as `$0.022`, and
PERMANENT (per this SAME requirement's own no-write-off-mechanism edge case below), with no bound relative
to the citizen's own actual, possibly much larger, unrelated balance. `adjustBalancesForOutstandingDebt`
instead returns the SAME array of citizens, at the SAME length (no citizen is EVER removed from the
array), with EACH citizen's own already-resolved liquid-balance figure — the SAME figure
`anicca-agent-spawn`'s own `readCitizenBalances({citizens})`
(`~/anicca/skills/self/spawn/lib/colony-balances.mjs`) ATTACHES to each citizen record BEFORE
`computeColonySurplusUsd` ever runs (re-read fresh this revision, `anicca-agent-spawn`
`specs/behavioral-spec.md` REQ-101, lines 296-309: `computeColonySurplusUsd({citizens,
perCitizenReserveUsd})` runs ONLY on `filterProductiveCitizens`'s output, where `balance_i` is obtained
via the SEPARATE, EFFECTFUL `readCitizenBalances` step, NOT by `computeColonySurplusUsd` itself
re-fetching balance — corrects this revision's own FIND-304, which found the prior citation here omitted
this middle, balance-attaching step entirely) — reduced by EXACTLY that citizen's own `outstandingDefaultedDebtUsd(loanRows,
citizenId)`: the sum, over `loanRows` reduced to one effective row per `loan_id` (last-write-wins, the
SAME reduction convention REQ-101's own `sumOutstandingPrincipalUsd` already establishes), of
`principal_usd − repaid_usd` for every row where `borrower_id === citizenId` AND `status === "defaulted"`
— clamped with the SAME `max(0, ...)` floor REQ-101 already applies elsewhere (a citizen's adjusted
balance never goes negative even if its debt exceeds its current balance) and, per this revision's own
FIND-206, the SAME `.toFixed(6)` money-precision clamp this codebase already establishes (see REQ-101's
own `computeLenderAvailableUsd` above). Every OTHER field on each citizen record (including `wallet`,
`walletAddress`, `fuel`, `humanDependencies`, `homeDir`) passes through UNCHANGED (a spread-copy, never a
mutation, per this project's own immutability convention) — only the balance figure is adjusted, and only
for a citizen that IS currently a defaulted borrower; a citizen who is NOT currently a defaulted borrower
is returned with its balance figure UNCHANGED (`outstandingDefaultedDebtUsd = 0` for it). **Composition
point, precisely stated (corrects this revision's own FIND-304 — the prior text named only a two-step
pipeline, `filterProductiveCitizens` → `computeColonySurplusUsd`, and never named the middle,
balance-attaching step at all):** `anicca-agent-spawn`'s REAL pipeline is THREE steps, in this exact
order — (1) `filterProductiveCitizens({citizens, ledgerRows, nowMs, bootstrapWindowDays})`, which filters
by ledger lifecycle status and attaches NO balance field; (2) `readCitizenBalances({citizens})`
(`~/anicca/skills/self/spawn/lib/colony-balances.mjs`), the ONLY step that ever attaches a `balance_i`
figure to a citizen record, via public-chain RPC; (3) `computeColonySurplusUsd({citizens,
perCitizenReserveUsd})`, which consumes step (2)'s balance-attached output. This composition runs AFTER
step (2) `readCitizenBalances`'s own output and BEFORE step (3) `computeColonySurplusUsd`'s own `max(0,
balance_i − perCitizenReserveUsd)` step — never between steps (1) and (2), where no citizen record yet
carries a balance field for this pure, zero-I/O function to reduce. The debt is subtracted from the
citizen's OWN already-attached balance FIRST, and `computeColonySurplusUsd` then applies its own reserve
subtraction on TOP of that already-adjusted figure, exactly as REQ-101's own arithmetic-ordering convention
already establishes for `computeLenderAvailableUsd` (reserve/outstanding/gojo are all subtracted from the
SAME base figure, in sequence, never compounding independently). Its adjustment is scoped ONLY to
`anicca-agent-spawn`'s own colony-surplus/spawn-
eligibility aggregation — it does NOT alter that citizen's REAL on-chain balance, nor any OTHER
computation in this codebase that reads a citizen's raw balance (e.g. this SAME citizen's own REQ-101
lender-eligibility check, if it later becomes a lender, still reads its real, unadjusted balance). This
feature still does NOT modify `anicca-agent-spawn`'s own function signature or source — the composition
itself, now a debt-proportional adjustment rather than a whole-citizen removal, is how this feature avoids
a tight coupling to a sibling spec still independently evolving (see Dependencies section; this
composition point MUST be revisited if that spec's registry/join shape changes further).

**Edge Cases**:
- A repayment-verification call (REQ-108) is evaluating this SAME `loan_id` at the same moment this sweep
  reaches it: the shared `loan_${loan_id}` lock (REQ-108) ensures only one of the two appends; the losing
  side simply re-evaluates on its own next pass (this sweep's own next scheduled run, or the repayment
  call's own retry) rather than racing to append a status-transition row (resolves FIND-104).
- A late-but-eventual full repayment arrives AFTER the row is already `"defaulted"`: THE SYSTEM SHALL
  append a further new row, `status: "repaid", on_time: false`, retroactively correcting the borrower's
  standing — mirroring `anicca-agent-spawn` REQ-402's identical "late success retroactively corrects
  the label" precedent (PROP-402b) exactly. The correction restores REQ-102 eligibility immediately but,
  per REQ-105, does NOT grow `successfulOnTimeRepayments` (the repayment was late).
- Two or more loans default simultaneously for different borrowers: each tracked independently by its
  own `loan_id`/`borrower_id`; this requirement does not rank, compare, or triage them against each
  other — no judgment call, mirroring `anicca-agent-spawn` REQ-402's identical edge case.
- A defaulted loan's principal is never recovered and no future increment ever adds a write-off
  mechanism: THE SYSTEM records this state plainly (REQ-101's `outstandingPrincipalUsd` sum permanently
  reflects the loss for that lender) but does NOT specify an automatic write-off/forgiveness policy this
  increment — left to a future increment or explicit operator action, mirroring `anicca-agent-spawn`
  REQ-402's identical "no auto-teardown policy this increment" precedent.
- A currently-`"defaulted"` borrower is NOT thereby excluded from `economy/ubi`'s own gojo mutual-aid
  distribution (a survival-floor gift, not a loan) — `adjustBalancesForOutstandingDebt` scopes ONLY to
  this feature's OWN loan-eligibility/colony-surplus composition (REQ-101/102), and is never consulted by,
  or wired into, `ubi.js`'s own recipient-eligibility logic. THE SYSTEM deliberately does NOT create a
  single combined "in good standing colony-wide" status: a defaulted borrower is excluded from NEW loans
  but remains eligible for the SAME unconditional mutual-aid gift any other citizen below its own survival
  reserve would receive — this avoids a permanent, compounding death-spiral where one missed loan
  repayment also cuts off the colony's own baseline survival safety net.
- `adjustBalancesForOutstandingDebt`'s adjustment is scoped EXCLUSIVELY to `anicca-agent-spawn`'s own
  colony-surplus/spawn-eligibility aggregation — it does NOT alter that citizen's real on-chain balance,
  nor any OTHER computation in this codebase that reads a citizen's raw balance (resolves FIND-204).

**Acceptance Criteria**:
- `detectDefaultedLoans({loanRows, nowMs})` is pure, zero I/O, and returns exactly the `loan_id`s whose
  last-appended row is `"active"`, past `due_ms`, and `repaid_usd < total_due_usd` — no others.
- `adjustBalancesForOutstandingDebt({citizens, loanRows})` is pure, zero I/O, returns the SAME `citizens`
  array at the SAME length (no citizen is ever removed), reducing ONLY a currently-defaulted borrower's own
  balance figure by exactly its own `outstandingDefaultedDebtUsd` (clamped at `0`), and passing every OTHER
  citizen through with its balance figure UNCHANGED (resolves FIND-204 — corrects the prior disproportionate
  whole-citizen-removal design).
- A fixture citizen with balance `$50` and exactly ONE `"defaulted"` loan row as `borrower_id` with
  `principal_usd - repaid_usd = 0.022` (REQ-104's own smallest possible cold-start default) →
  `adjustBalancesForOutstandingDebt` returns that citizen's balance as exactly `$49.978`, NOT `$0` —
  proving the fix is debt-proportional, not a full exclusion (new PROP-109f, resolves FIND-204). A
  SEPARATE fixture where the citizen's own currently-defaulted debt EXCEEDS its current balance (balance
  `$0.01`, debt `$5.00`) confirms the adjusted balance clamps at exactly `$0`, never negative.
- A structural/Tier-0 check confirms neither `detectDefaultedLoans` nor `adjustBalancesForOutstandingDebt`
  ever mutates or deletes an existing `loans.jsonl` row.
- The effectful caller's `"defaulted"` append step acquires the SAME `loan_${loan_id}` lock REQ-108
  specifies before appending — a structural/Tier-0 check confirms no call site appends a REQ-108/REQ-109
  status-transition row without first acquiring this lock (new PROP-109e, resolves FIND-104).
- A structural/Tier-0 check — mirroring PROP-105h's/PROP-106d's/PROP-114c's own real-source-read discipline
  exactly — confirms the REAL, PRODUCTION effectful caller that appends a `status:"defaulted"` row (using
  `detectDefaultedLoans`'s own output) genuinely sets `defaulted_ms: Date.now()` on that row's own append
  payload at the moment of append, and that no call site appending a non-`"defaulted"` status-transition row
  (`"active"`/`"repaid"`) includes a `defaulted_ms` field on its own payload — never merely a unit test of
  `computeRecentDefaultLossUsd`/`computeOverallDefaultRateUsd` (PROP-114e/PROP-114f) against a hand-authored
  fixture where `defaulted_ms` is already present as literal, hand-populated data (new PROP-109g, resolves
  this revision's own spec-review iteration-8 FIND-702 — closes the gap where every stated PROP for
  REQ-109/REQ-114 could pass while the real append code silently omits or mistypes this field, permanently
  zeroing REQ-114's own absolute-loss signal in live production, since REQ-114's own fail-closed convention
  treats a missing/malformed `defaulted_ms` as contributing `0` to the sum).

---

### REQ群E: Coexistence + money-safety

### REQ-110: Coexistence with gig-work (additive, non-exclusive)
**EARS**: WHERE a citizen has an outstanding loan (or has never taken one), THE SYSTEM SHALL NOT
restrict, gate, or otherwise couple that citizen's participation in `economy/gig` postings/takes to this
feature's own state — loan issuance and gig-board participation are two independent, non-exclusive
mechanisms a citizen may use in any combination (per Dais's explicit framing: "not limited to gig-work OR
loans -- both mechanisms should coexist as options").

**Edge Cases**:
- A borrower uses loan proceeds to fund a gig bounty post before repaying the loan: permitted; this
  feature does not track loan-proceeds provenance once disbursed (out of scope — the borrower's use of
  the funds is its own business, not this feature's enforcement target, mirroring how a bank loan's
  end-use is ordinarily not the lender's own tracking concern either).
- A citizen with zero loan history takes gigs exclusively and never borrows: fully supported, unaffected
  by anything this feature specifies.

**Acceptance Criteria**:
- A structural/Tier-0 check confirms `economy/gig/decide.mjs` and this feature's own eligibility/sizing
  functions share zero code coupling — neither imports the other, and neither reads the other's state
  file. (This is a GIG-specific claim; it does NOT extend to `economy/ubi` — REQ-101's own
  `sumRecentGojoGiftsUsd` deliberately, and separately, DOES read `ubi`'s `gojo-log.jsonl` read-only, per
  FIND-005's resolution. The two claims are independent and both hold: zero coupling with `gig`, a
  disclosed, one-way, read-only awareness of `ubi`.)
- REQ-102's `BORROWER_LOW_USD` constant deliberately shares the SAME NUMERAL as `decide.mjs`'s
  `DEFAULT_LOW_USDC` (`0.50`) for definitional consistency (the same colony-wide "genuinely broke"
  concept) — this is NOT an exception to this requirement's own zero-coupling claim: sharing a NUMERAL
  for conceptual consistency is a DIFFERENT thing from sharing CODE, and this requirement's own structural
  check (above) verifies the latter (no import either direction), never the former. A future reader who
  sees "same numeral" language near REQ-102 must not mistake it as license to add an import (resolves
  this revision's own FIND-106 contradiction).

---

### REQ-111: Money-safety invariant — human-funded entities never auto-lend or auto-borrow
**EARS**: THE SYSTEM SHALL NEVER permit a human-funded entity (e.g. claude-p,
`0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74`, or any wallet for which `isSelfFunded()` returns `false`)
to originate a loan as lender, receive a loan as borrower, or appear in either role in `loans.jsonl`, on
an ongoing/automated basis — `isSelfFunded()` (unmodified) gates BOTH roles at REQ-101/102 with zero
code path bypassing that gate. The one-time, human-approved genesis injection precedent (SPEC.md §9.9)
remains a permanently one-time, manually-approved historical exception (memory
`feedback_human_funded_ai_permanently_outside_agent_economy.md`) and is NEVER automated or repeated by
this feature — this feature implements NO code path resembling that genesis injection at all (no
"emergency top-up from claude-p" fallback, no configuration flag that would re-enable it).

**Edge Cases**:
- A future operator manually wants to replicate a one-time genesis-style injection for a NEW colony
  citizen: explicitly NOT this feature's mechanism — that remains a separate, manual, one-time action
  outside this codebase's automated loop, exactly as SPEC.md §0 already establishes for the original
  genesis event.

**Acceptance Criteria**:
- A structural/Tier-0 check greps every new function this feature introduces (loan issuance, repayment,
  default handling) for any reference to a known human-funded wallet identifier (claude-p's addresses,
  per `docs/WALLETS.md`) — must find none, mirroring `anicca-agent-spawn` PROP-304a exactly.
- `isSelfFunded()`'s own source is byte-identical to its pre-existing version (this feature makes zero
  modifications to it).

---

## REQ群F: Sprint-2 — Effectful orchestrators (new)

### REQ-115: The loan-issuance orchestrator's single entry-point function (new, sprint-2)
**EARS**: WHEN a lending-eligible pair (`lenderId`, `borrowerId`) is identified for a specific
loan-issuance attempt — by whatever caller has already read REQ-101/102's own pure eligibility functions
against a recent snapshot and decided to attempt issuance — THE SYSTEM SHALL execute the ENTIRE remainder
of that issuance attempt — REQ-102(d)'s self-loan exclusion, REQ-112's co-location check, REQ-105/REQ-114's
pre-lock kill-switch checks, REQ-106's dual-lock acquisition and ledger-state-triggered reconciliation, the
lock-protected fresh re-check of REQ-101/102/105/114, REQ-104/105's sizing computation, REQ-106's
per-lender sequence-number assignment, and REQ-106's two-phase provisional/follow-up disbursement — via
exactly ONE new, named entry-point function, `executeLoanIssuanceAttempt({ lenderId, borrowerId, nowMs =
Date.now() }) → Promise<{ status: "active"|"disbursement_failed"|"disbursement_uncertain"|"refused",
loanId?, reason?, error? }>`, exported from a NEW module,
`~/anicca/skills/economy/lending/lib/lending-orchestrator.mjs`. **This closes the one gap a full sweep of
this spec found (2026-07-08): every individual step (REQ-101/102/104/105/106/112/114) already has its own
pinned signature and its own fully-specified edge cases, but no function anywhere before this correction
was named as the thing that calls them all, in order, across both of REQ-106's own locks.** This function
SHALL contain NO decision/judgment logic of its own (mirrors REQ-103's own bookkeeping-only discipline,
extended here exactly as `anicca-agent-spawn` REQ-307 extends REQ-104's identical discipline to ITS OWN
orchestrator) — it is PURE SEQUENCING AND ERROR PROPAGATION over the already-specified pure/narrow modules
and the two already-hardened effectful modules (`lock.mjs`, `escrow.mjs`/`payViaFacilitator`), calling
each in the canonical order below and never re-deriving, re-computing, or hardcoding any value those
modules already own.

**Canonical call order** (never varied, never partially reordered — each step's own REQ number retains
full ownership of that step's internal behavior; this paragraph states ONLY the sequencing):
1. REQ-102(d)'s self-loan check (`lenderId !== borrowerId`) — before any lock, before either kill-switch,
   before REQ-112's own check.
2. REQ-112's co-location check (`citizen.coLocatedWithCoordinator === true` for BOTH parties) — still
   before any lock.
3. REQ-105's `evaluateColdStartKillSwitch` (for a cold-start request, `successfulOnTimeRepayments===0`)
   and REQ-114's `evaluateOverallDefaultKillSwitch` (for every request) — the pre-lock evaluation, over
   the freshest `loanRows`/`gojoLogRows` read available to this call, BEFORE either lock is acquired.
4. Acquire BOTH `` `loan_${lenderId}` `` and `` `loan_borrower_${borrowerId}` `` locks via nested
   `withGigLock` calls, in the order `resolveLoanLockAcquisitionOrder(lenderId, borrowerId)` returns.
5. REQ-106's ledger-state-triggered reconciliation check: if this lender's own highest-`n` row is
   unterminated (`"provisioning"`/`"disbursement_uncertain"`), invoke `reconcileProvisionalDisbursement`
   and resolve it (to `"active"` or `"disbursement_failed"`) BEFORE this attempt computes or uses any new
   sequence number.
6. The lock-protected FRESH re-check: a fresh read of `loans.jsonl`, REQ-102(a)-(c)'s
   borrower-eligibility recheck, REQ-101's lender-availability recheck, AND both kill-switches (step 3's
   SAME two functions) re-evaluated against this SAME fresh read.
7. REQ-104/105's sizing computation (`computeLoanCapUsd`, `decideLoan`) against step 6's own
   fresh-read output.
8. `n = nextLoanSequenceForLender(...)` and the PROVISIONAL `` status: "provisioning" `` append (REQ-106's
   own step 1).
9. The disbursement attempt (`payViaFacilitator`, wrapped in its own try/catch per REQ-106's own
   in-process-exception discipline) and the FOLLOW-UP append (`"active"`, `"disbursement_failed"`, or
   `"disbursement_uncertain"` — REQ-106's own step 3).

**Edge Cases** (this function invents no new failure-recording rule anywhere below — each step's own REQ
number already specifies exactly what happens on failure; this paragraph only confirms the SAME rule
applies when exercised through this REAL, single orchestrator, never a mocked stand-in):
- A refusal at step 1, 2, 3, or 6 (self-loan, non-co-located party, a tripped kill-switch, or a
  fresh-recheck ineligibility) returns `{status:"refused", reason}` — ZERO lock is acquired for a
  step-1/2/3 refusal (REQ-106's own Acceptance Criteria already state this for step 1/3; REQ-112's own
  fail-closed convention extends it to step 2), and a step-6 refusal releases both already-acquired locks
  normally with ZERO `loans.jsonl` row appended (REQ-106's own PROP-106n/PROP-106p precedent) — this
  function adds no second, competing refusal-recording path.
- A failure at step 4 itself (`lock_held`, either lock already held by a different in-flight attempt)
  returns `{status:"refused", reason:"lock_held"}` with ZERO row appended — REQ-106's own already-specified
  fail-fast refusal shape.
- A failure at step 5 (the reconciliation lookup itself throws) returns `{status:"refused",
  reason:"reconciliation_failed"}` (or propagates the underlying error) with ZERO row appended and ZERO
  sequence number consumed — REQ-106's own PROP-106l precedent, both locks released normally.
- A failure at step 8 itself (the PROVISIONAL `appendChild` call throws, e.g. `ENOSPC`, before it ever
  durably commits) leaves ZERO row for this attempt's own `n` — a later attempt for this SAME lender
  recomputes a fresh `n` from the ledger's own real, unaffected state (no reservation was ever durably
  made).
- A failure inside step 9 — `payViaFacilitator` returns `{ok:false}` (clean failure), throws mid-call
  (in-process exception, `"disbursement_uncertain"`), or the FOLLOW-UP append itself throws (leaving the
  provisional row unterminated, REQ-106's own FIND-301 case) — is recorded EXACTLY per REQ-106's own
  already-specified two-phase/reconciliation mechanism; this function neither adds nor removes any
  recording behavior at this step, it only calls the already-hardened primitives in the stated order.
- The `` `loan_${lenderId}` `` and `` `loan_borrower_${borrowerId}` `` locks are held from before step 5
  begins (immediately after step 4's own acquisition) until after step 9 completes OR a refusal/failure at
  step 5, 6, 8, or 9 has been resolved — released only in a `finally` block, mirroring `withGigLock`'s own
  existing release discipline (REQ-106 introduces no new release logic; this function passes a new `fn`
  body into the EXISTING nested `withGigLock` wrapper REQ-106 already specifies).
- `lenderId`/`borrowerId` are supplied by THIS function's OWN caller (whichever wake-cycle/agent process
  already evaluated REQ-101/102's own pure eligibility functions against a recent snapshot and decided an
  issuance attempt is worth making) — `executeLoanIssuanceAttempt` does not itself decide WHETHER to
  attempt a loan, only HOW to safely execute an already-decided attempt; the agent's own in-envelope
  timing choice (REQ-103's own carve-out: "when, within an eligible wake, to actually originate... a
  specific loan") happens entirely in this caller, never inside this function.

**Acceptance Criteria**:
- A structural/Tier-0 check confirms exactly ONE function, `executeLoanIssuanceAttempt`, in exactly ONE
  new module (`lending-orchestrator.mjs`), calls REQ-101/102/104/105/106/112/114's own already-exported
  functions in the canonical order above — no second, competing issuance-orchestration entry point exists
  anywhere in the diff.
- A structural/Tier-0 check confirms `executeLoanIssuanceAttempt`'s own function body contains no
  arithmetic/boolean eligibility/sizing comparison of its own (that logic belongs exclusively to
  `isBorrowerEligible`/`computeLenderAvailableUsd`/`decideLoan`/the kill-switch functions, all called BY
  this function, never re-implemented inside it) and no LLM/prompt reference — mirrors REQ-103's own
  structural check, extended to this new function exactly as `anicca-agent-spawn` REQ-307/PROP-307b
  extends REQ-104's identical check to ITS OWN orchestrator.
- An integration test triggering a failure/refusal at each of the 9 canonical steps in turn, against the
  REAL `executeLoanIssuanceAttempt` (never a mocked stand-in), confirms the ledger effect (or non-effect)
  at each step exactly matches the already-specified REQ-101/102/105/106/112/114 edge case for that step —
  steps 1/2/3/4/5/6 append ZERO rows; step 8's own append-throw leaves ZERO rows; step 9's three
  sub-cases append the FOLLOW-UP row exactly as REQ-106 already specifies (`"active"`/
  `"disbursement_failed"`/`"disbursement_uncertain"`) — and no step anywhere produces a row claiming
  `"active"` for a loan whose disbursement did not genuinely, verifiably succeed.
- An integration test reusing PROP-106a's/PROP-106n's own staggered-race method against the REAL
  `executeLoanIssuanceAttempt` confirms both locks' real scope over this actual function matches REQ-106's
  own already-specified critical section (held from step 4 through step 9, never released early) — this
  closes PROP-106a/PROP-106e's Tier-2 half/PROP-106n's own "wired into a live issuance attempt"
  requirement (contracts/sprint-1.md's own residual-scope boundary).

---

### REQ-116: The loan-servicing orchestrator — repayment-claim and default-detection entry points (new,
sprint-2)
**EARS**: WHEN an ALREADY-ISSUED loan (`status:"active"`) is either (a) claimed repaid by its borrower (a
specific `txHash` is presented) or (b) evaluated by a scheduled default-detection sweep, THE SYSTEM SHALL
execute REQ-108's own independent repayment-verification check and REQ-109's own default-detection-and-
adjustment check via exactly TWO new, named entry-point functions — never a single, conflated function,
since the two are triggered by two genuinely different events (an external claim vs. a time-based sweep)
even though both contend on the SAME per-loan critical section — both exported from a NEW module,
`~/anicca/skills/economy/lending/lib/lending-orchestrator.mjs` (the SAME module REQ-115's issuance
orchestrator lives in, since both are this feature's own effectful wiring layer):

- `executeRepaymentClaim({ loanId, txHash, nowMs = Date.now() }) → Promise<{ credited: number, status:
  "active"|"repaid"|"rejected", rejected?: boolean }>` — wraps REQ-108's `verifyRepayment` call and its own
  repayment-status-transition append.
- `executeDefaultDetectionSweep({ nowMs = Date.now() }) → Promise<{ defaulted: string[] }>` — wraps
  REQ-109's `detectDefaultedLoans` call (over the full, freshly-read `loans.jsonl`) and, for EACH flagged
  `loan_id`, its own `"defaulted"`-row append (with `defaulted_ms` set, per PROP-109g).

Both functions contain NO decision/judgment logic of their own — mirrors REQ-103's own bookkeeping-only
discipline, applied here exactly as REQ-115 applies it to issuance. Both wrap their own read-verify-append
critical section in the SAME per-loan lock, key `` `loan_${loan_id}` ``, via
`withGigLock(LOANS_LEDGER_PATH, `loan_${loan_id}`, fn)` — REQ-108's own already-specified lock (never
REQ-106's per-lender/per-borrower locks, which this module's REQ-115 entry point owns exclusively and
which this REQ-116 entry point never acquires, references, or nests inside — resolves REQ-106's own
PROP-106i distinction, now extended to this new module).

**Canonical call order — `executeRepaymentClaim`**:
1. Acquire the `` `loan_${loanId}` `` lock.
2. A fresh read of `loans.jsonl`; `verifyRepayment({txHash, expectedFrom, expectedTo, rpcUrl, loanRows})`
   (REQ-108) — including its own txHash-replay-rejection check (same-loan AND cross-loan, BEFORE any
   value is credited).
3. IF `verifyRepayment` rejects (invalid/un-finalized/mismatched/already-credited `txHash`): return
   `{credited:0, status:"rejected", rejected:true}` — append NOTHING to `loans.jsonl` (REQ-108's own
   out-of-band-logging-only rule); release the lock normally.
4. IF `verifyRepayment` credits a value: append the status-transition row (`repaid_usd` updated;
   `status:"repaid"` if the cumulative total now reaches `total_due_usd`, `on_time` set per REQ-105's own
   definition; otherwise `status` remains `"active"` with the updated `repaid_usd`) — release the lock
   normally.

**Canonical call order — `executeDefaultDetectionSweep`**:
1. A fresh read of `loans.jsonl`; `detectDefaultedLoans({loanRows, nowMs})` (REQ-109) — pure, zero I/O,
   returns the full candidate `loan_id[]` list.
2. FOR EACH candidate `loan_id` (sequentially, one at a time — never in parallel against the SAME shared
   ledger file, avoiding this sweep racing against itself): acquire the `` `loan_${loan_id}` `` lock;
   re-read `loans.jsonl` fresh (a candidate flagged at step 1 may already have been repaid or already
   defaulted by a concurrent `executeRepaymentClaim`/an earlier iteration of this SAME loop by the time
   this specific lock is acquired); IF the loan's own last-appended row is STILL `"active"`, past
   `due_ms`, with `repaid_usd < total_due_usd`, append the `"defaulted"` row (`defaulted_ms: Date.now()`,
   per PROP-109g); IF the lock is already held (a concurrent `executeRepaymentClaim` for this SAME
   `loan_id`), skip this candidate for this sweep pass (it will be re-evaluated on the next scheduled
   sweep, or was resolved by the winning repayment claim) — never block waiting for the lock.
3. Return `{defaulted: [...loan_ids actually marked defaulted this sweep]}`.

**Edge Cases**:
- A repayment claim and a default-detection sweep race for the SAME `loan_id` (REQ-108's own PROP-108d):
  exactly one of `executeRepaymentClaim`/`executeDefaultDetectionSweep`'s own per-loan-lock acquisition for
  that `loan_id` succeeds and appends; the other observes the lock held, appends nothing, and — for
  `executeRepaymentClaim`, the caller is expected to retry on its own next attempt; for
  `executeDefaultDetectionSweep`, this SAME `loan_id` is simply skipped this pass and re-evaluated on the
  next scheduled sweep — this function adds no new race-recording behavior beyond REQ-108/109's own
  already-specified lock discipline.
- A rejected repayment claim (invalid/replayed `txHash`) never appends a row — REQ-108's own
  out-of-band-audit-only rule (resolves FIND-302) applies identically whether `verifyRepayment` is called
  directly (as sprint-1's own tests already exercise) or through this REAL orchestrator entry point.
- `executeDefaultDetectionSweep`'s own step-1 candidate list can go stale between step 1's read and a
  given candidate's own step-2 lock acquisition (a candidate may have been repaid in the interim, by a
  concurrent `executeRepaymentClaim`) — the step-2 fresh re-read before appending is what prevents a
  stale-candidate false default (mirrors REQ-106's own "never rely on a pre-lock snapshot alone"
  discipline, applied here to the sweep's own per-candidate loop).
- `executeRepaymentClaim`'s `loanId` names a loan whose last-appended row is NOT `"active"` (already
  `"repaid"`, already `"defaulted"`, or still `"provisioning"`/`"disbursement_failed"`/
  `"disbursement_uncertain"` — never actually issued): treated as an ineligible target and refused
  (`{credited:0, status:"rejected", rejected:true}`) BEFORE `verifyRepayment` is ever invoked — this
  function never attempts repayment-verification against a loan that was never actually disbursed.
- `loanId`/`txHash` are supplied by THIS function's OWN caller (whichever external channel/agent process
  received the borrower's repayment claim) — `executeRepaymentClaim` does not itself decide WHETHER a
  repayment claim is genuine or which loan it applies to before invocation, it only verifies and records
  an ALREADY-PRESENTED claim; neither value is ever hand-assembled, regenerated, or internally derived by
  this function (resolves FIND-S2-001, mirrors REQ-115's own `lenderId`/`borrowerId` closure above).
  Likewise, `executeDefaultDetectionSweep` takes no externally-supplied identifier at all — its own
  candidate `loan_id[]` list is ALWAYS the direct return value of `detectDefaultedLoans` (REQ-109), never
  hand-assembled by this function's own caller or by any other means.

**Acceptance Criteria**:
- A structural/Tier-0 check confirms `executeRepaymentClaim` is the ONLY call site invoking
  `verifyRepayment` followed by a repayment-status-transition append, and `executeDefaultDetectionSweep` is
  the ONLY call site invoking `detectDefaultedLoans`/`adjustBalancesForOutstandingDebt`-adjacent
  default-append logic — no second, competing entry point for either exists anywhere in the diff.
- A structural/Tier-0 check confirms neither function contains arithmetic/boolean eligibility logic of
  its own (that belongs exclusively to `verifyRepayment`/`detectDefaultedLoans`, both called BY these
  functions) and neither references any LLM/prompt client.
- An integration test (REQ-108's own PROP-108d, now against the REAL `executeRepaymentClaim`/
  `executeDefaultDetectionSweep` functions rather than a mocked pair) launches both concurrently against
  the SAME `loan_id` and confirms exactly one append occurs, the other returns/skips cleanly with zero
  append.
- An integration test confirms `executeDefaultDetectionSweep`'s own real, production append genuinely sets
  `defaulted_ms: Date.now()` on every row it appends (closing PROP-109g's own "real code, not a fixture"
  requirement) and that a candidate found already-repaid at its own step-2 fresh re-read is correctly
  skipped, never defaulted.
- An integration test confirms `executeRepaymentClaim`'s own real call site correctly transitions a
  partial-then-full repayment sequence (REQ-104/108's own PROP-108c) and correctly rejects both a
  same-loan and a cross-loan `txHash` replay (PROP-108e) with zero `loans.jsonl` rows appended for the
  rejected attempt.
