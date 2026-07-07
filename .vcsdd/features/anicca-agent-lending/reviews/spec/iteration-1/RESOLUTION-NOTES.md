# Spec Review Iteration 1 — Resolution Notes

**feature**: anicca-agent-lending · **mode**: strict · **date**: 2026-07-07
**verdict resolved**: FAIL (8 findings: 2 critical, 4 major, 1 medium, 1 minor) → all 8 addressed below,
targeted edits only, no scope creep beyond what each finding required.

Both spec files' headers were bumped to `revision: iteration 2` and a `## Changelog (iteration 1 →
iteration 2)` table was added to `specs/behavioral-spec.md` (lines 8-23) summarizing all 8 resolutions
in one place, mirroring `anicca-agent-spawn`'s own established changelog convention.

Every source file cited by the findings was re-read fresh this session before editing (not assumed from
memory): `~/anicca/skills/economy/gig/lib/escrow.mjs`, `~/anicca/skills/economy/gig/gig.mjs`,
`~/anicca/skills/economy/ubi/ubi.js`, `~/anicca/skills/economy/ubi/run.sh`,
`~/anicca/skills/self/founder-loop/record-earn.mjs`, `~/anicca/skills/economy/gig/lib/lock.mjs`,
`~/anicca/skills/self/spawn/lib/child-spec.js`, `~/anicca/skills/economy/gig/decide.mjs`, and
`anicca-agent-spawn`'s current `specs/behavioral-spec.md` (REQ-105 lines 424-547, REQ-106 lines 550-587)
plus its `state.json` (`currentPhase: "1b"`).

---

## FIND-001 (critical) — `loan_id` generation unspecified

**Fix**: `specs/behavioral-spec.md` REQ-106 (lines 499-582, specifically the new "`loan_id` generation"
paragraph, lines ~536-550) now fully specifies: `loan_id = loan_${lenderId}_${n}`, where `n =
nextLoanSequenceForLender(loanRows, lenderId)` is a per-LENDER monotonic sequence — read every row for
that lender, take the highest matching-prefix numeric suffix, +1 — computed and appended STRICTLY INSIDE
the SAME `loan_${lenderId}` lock REQ-106 already acquires for that lender's own surplus-check/
disbursement. Because the ID space is namespaced by `lenderId` and the per-lender lock is already held,
two DIFFERENT lenders issuing concurrently (REQ-106's own intentional no-cross-lender-contention design)
can never collide — no shared/global lock is needed, a stronger guarantee than `child-spec.js`'s own
upstream usage (which depends on `anicca-agent-spawn` REQ-106's single shared `"colony-spawn"` lock).

- Dependencies section (behavioral-spec.md lines 95-104): new bullet citing `child-spec.js::nextChildId`
  (read fresh, lines 5-14) as the INSPIRATION, explicitly explaining why it is NOT reused verbatim.
- REQ-106 Edge Cases (lines ~552-556) and Acceptance Criteria (lines ~572-576) gained new bullets: two
  different lenders' `loan_id`s are structurally guaranteed distinct; a fixture assertion
  (`loan_${lenderA}_1` vs `loan_${lenderB}_1`).
- Purity Boundary Map (`specs/verification-architecture.md`, new row after `excludeDefaultedBorrowers`):
  `nextLoanSequenceForLender` classified Pure Core (new).
- New proof obligation **PROP-106e** (verification-architecture.md, Proof Obligations table, Tier 1/2):
  "Two DIFFERENT lenders issuing concurrently... produce DISTINCT `loan_id`s with zero collisions, using
  only their own existing per-lender locks."
- Gate item (3) (verification-architecture.md) extended to require the adversary confirm `loan_id`
  generation happens strictly inside the per-lender lock and is namespace-collision-free.

## FIND-002 (critical) — missing single-coordinator-host scoping

**Fix**: New requirement **REQ-112** added to `specs/behavioral-spec.md` (lines 596-660, inserted between
REQ-107 and REQ群D), titled "Loan issuance/repayment participation is scoped to a single coordinator
host, this increment only" — a direct, by-name analog of `anicca-agent-spawn` REQ-106 (re-read fresh,
lines 550-587), restating that spec's own "This constraint is what makes `lock.mjs`... and `ledger.js`...
CORRECT as specified" language almost verbatim, but extended to BOTH lending participants (lender AND
borrower), not merely one evaluator, since lending is inherently two-party (each side needs its own
private key to sign its own side of the transfer). Explicitly flags, as a known limitation/future work,
that a future `anicca-agent-spawn` REQ-301 remote-cloud-hosted citizen is out of scope for lending
TO/FROM it this increment.

- Scope section (behavioral-spec.md lines 48-65) updated to reference REQ-112 by name instead of the
  prior vague mirror-citation on REQ-107.
- REQ-107 (line ~583) updated to no longer misattribute the host-scoping precedent to itself; now points
  to REQ-112 as the direct analog.
- Purity Boundary Map (verification-architecture.md): new row, REQ-112 classified "Not code — design
  constraint," plus a note added to the existing `citizens.json`/`computeColonySurplusUsd` row about
  `homeDir` (REQ-112 reads it for co-location confirmation).
- New proof obligation **PROP-112a** (Tier 0, structural check for no remote/networked path).
- Gate item (10) (new) requires the adversary confirm no remote/networked code path exists and the
  known-limitation framing is present, not silently omitted.

## FIND-003 (major) — `payViaFacilitator` signature/facilitator-service precondition omitted

**Fix**: Dependencies section (`specs/behavioral-spec.md`, the `escrow.mjs::payViaFacilitator` bullet,
lines 134-155) rewritten to cite the REAL, full signature re-read from `escrow.mjs` lines 150-165:
`payViaFacilitator({ privateKey, to, amountBase, facilitatorUrl, chainId, usdcAddress, domainName,
rpcUrl, chain, validitySeconds })`, explicitly stating `facilitatorUrl` has NO default inside the
function itself, and citing the real resolution pattern this codebase already uses (`gig.mjs`'s own
`FACILITATOR_URL = process.env.GIG_FACILITATOR_URL || "http://127.0.0.1:8405"`, re-read fresh, lines 78,
158, 288) as the SAME mechanism this feature's own call sites SHALL reuse. Fail-closed behavior specified:
if the facilitator is unreachable at disbursement/repayment time, the operation fails cleanly, no partial
state, no ledger row appended, retriable next wake.

- REQ-106 (lines ~522-533, new "Disbursement failure" paragraph) specifies the exact fail-closed
  behavior for the loan-issuance critical section: no `loans.jsonl` row appended, lock released normally.
- REQ-106 Edge Cases/Acceptance Criteria gained a facilitator-unreachable bullet and a fixture assertion
  (injected `payViaFacilitator` failure → zero ledger row, lock releases).
- New proof obligation **PROP-106f** (Tier 2, integration test with mocked facilitator failure).
- Gate item (3) extended to require confirming this fail-closed behavior.

## FIND-004 (major) — $0.02 cold-start repayment pathway unfounded

**Fix**: REQ-104's `FIRST_LOAN_USD` bullet (`specs/behavioral-spec.md` lines 368-375) rewritten to stop
claiming $0.02 is a proven repayment-capacity figure — SPEC.md §9.9's gig #3 proves $0.02 rescues a
bounty TAKER (who receives payout), not a borrower who must earn $0.022 back. REQ-105 (lines 411-475)
rewritten with an explicit "What this ladder actually resolves, stated honestly" section separating the
PROVEN sizing claim (zero-collateral cold-start issuance, arXiv 2602.14219 §4.2.2's sizing half) from
the UNPROVEN economic claim (borrower repayment capacity) — no longer conflated. The cold-start loan's
INTENDED use is now stated explicitly: covering the borrower's own first small on-chain action to
complete ONE self-directed EARNING event (e.g. its own gas/tx cost to accept a gig it did NOT post) —
NOT funding a bounty the borrower itself posts.

- New "Monitoring plan" paragraph (REQ-105, lines ~437-447) adds `computeColdStartRepaymentRate({loanRows,
  n=20}) → {sampleSize, repaidCount, defaultedCount, pendingCount, rate}` — a new pure function tracking
  the actual repayment outcome rate of the first `n` cold-start loans colony-wide, explicitly framed as
  monitoring an EXPERIMENTAL HYPOTHESIS, not a proven solution.
- REQ-105 Edge Cases/Acceptance Criteria gained bullets for this function (small-sample caveat, exact
  fixture assertion).
- Purity Boundary Map: new row, `computeColdStartRepaymentRate` classified Pure Core (new).
- New proof obligation **PROP-105f**; PROP-105a's own description (verification-architecture.md) edited
  to say it proves the SIZING half only, not the economic half.
- Gate item (2) rewritten to require the adversary confirm the spec does NOT overclaim the economic half
  and that the monitoring-plan function is present.

## FIND-005 (major) — zero coordination with existing gojo/UBI mutual-aid

**Fix**: Read `~/anicca/skills/economy/ubi/ubi.js` (full) and `~/anicca/skills/economy/ubi/run.sh` (full)
fresh this session. Dependencies section (`specs/behavioral-spec.md`, new bullet, lines 105-115) cites
`distributeAI` and the real `gojo-log.jsonl` row shape `run.sh` actually writes:
`{ts, recipient, recipient_wallet, surplus_above_reserve_usd, decision: {amount_usd, reason}, executed}`.
REQ-101 (lines 202-289) extended with a ONE-WAY, minimal, read-only fix: `computeLenderAvailableUsd`
gains a new `recentGojoGiftsUsd` term, computed by new pure function `sumRecentGojoGiftsUsd(gojoLogRows,
nowMs, lookbackHours=24)` (reusing `ubi.js`'s own `DEFAULT_GOJO_CONFIG.rateLimitHours=24`, not inventing a
new window) over rows read (read-only, via new effectful reader `readGojoLogRows`) from
`~/anicca/skills/economy/ubi/state/gojo-log.jsonl`. Explicitly notes `run.sh` currently always writes
`executed: false` (the real send is a separate, unwired manual step), so every planned gift is treated as
committed — a deliberate, conservative (fail-closed) choice. `ubi.js`/`run.sh` are NOT modified.

- REQ-101's Edge Cases/Acceptance Criteria (lines ~253-271) gained bullets for the new term, including an
  exact fixture (`balance=8, reserve=5, outstanding=0, recentGojoGiftsUsd=1 → available=2`).
- The REVERSE direction (gojo unaware of `loans.jsonl`) is explicitly, honestly flagged as an
  ACKNOWLEDGED, NOT-YET-SOLVED limitation — not claimed fixed.
- REQ-110's Acceptance Criteria (lines ~774-782) gained a clarifying note that its "zero coupling" claim
  is GIG-specific and does not contradict REQ-101's new, disclosed, one-way `ubi` read.
- Purity Boundary Map: two new rows (`sumRecentGojoGiftsUsd` pure; `readGojoLogRows` effectful, read-only).
- New proof obligation **PROP-101f**.
- Gate items (1) and (8) extended to require the adversary confirm the read-only property, correct
  windowing, and that the disclosed reverse-direction limitation is present, not omitted.

## FIND-006 (medium) — stale `citizens.json` citation

**Fix**: Re-read `anicca-agent-spawn`'s CURRENT `specs/behavioral-spec.md` fresh (REQ-105, lines 424-547;
`state.json` shows `currentPhase: "1b"`, the spec's own header self-describes as "iteration 4"). The
Dependencies section's citation (`specs/behavioral-spec.md` lines 69-94) is updated to the CURRENT record
shape: `{id: string, wallet: {evm?: boolean, solana?: boolean}, walletAddress: {evm?: string, solana?:
string}, fuel: {provider: string}, humanDependencies: string[], homeDir: string}` — including the
`homeDir` field that spec's own iteration added to resolve ITS OWN FIND-202/FIND-303. The citation also
now states this spec's own phase status accurately (not the stale "Phase 1c spec review iteration 5"
claim) and explicitly notes this drift is direct, present-tense evidence the citation must be
re-verified at each future revision, not merely trusted.

- Purity Boundary Map's `citizens.json` row (verification-architecture.md) updated to note the shape is
  re-verified and includes `homeDir`, which REQ-112 (FIND-002's fix) also reads.

## FIND-007 (major) — `verifyRepayment` falsely claims `escrow.mjs` reuse

**Fix**: Re-read `escrow.mjs::settleBody` (lines 124-140) fresh — confirmed it contains NO
`Transfer`-log-parsing code (only `waitForTransactionReceipt` + `status` check). Re-read
`~/anicca/skills/self/founder-loop/record-earn.mjs` fresh (lines 56, 65-72, 82-88) — the REAL,
already-hardened precedent. REQ-108 (`specs/behavioral-spec.md`, lines 665-729) rewritten: `verifyRepayment`
now cites `record-earn.mjs`'s own `blockNow()` finalized-block-only discipline (never trusting an
un-finalized `"latest"` read) and `parseRawLogs`'s `TRANSFER_TOPIC`-match + EXACT zero-padded-address
equality for `to`/`from` (never a substring/suffix match — reusing the file's own documented,
previously-fixed bug, `FIND-704`), and never trusting the RPC's own server-side filter for a money
invariant (`FIND-603`).

- Purity Boundary Map (both `specs/behavioral-spec.md` line ~179 and `specs/verification-architecture.md`
  row 26) corrected — the SAME false claim was present in BOTH spec files and both are now fixed.
- REQ-108 Edge Cases/Acceptance Criteria gained bullets for finalized-block confirmation and a fixture
  reproducing the exact `FIND-704` suffix-match bug class (must be REJECTED, never credited).
- PROP-108a/b (verification-architecture.md) descriptions and Tool/Method columns updated accordingly.
- Gate item (4) rewritten to cite the correct precedent and require finalized-block confirmation.

## FIND-008 (minor) — interest rate justification is a numeric coincidence

**Fix**: REQ-104's `LOAN_INTEREST_RATE` bullet (`specs/behavioral-spec.md` lines 376-384) rewritten:
removed the false "reused from `ubi.js`'s `contributePct`" framing (a profit-tithe rate on already-safe
profit has no bearing on default-risk pricing on an uncollateralized advance). Replaced with an honest
statement: `LOAN_INTEREST_RATE=0.10` is a deliberately chosen, conservative, easily-tunable STARTING
parameter, not derived from any existing mechanism, explicitly open to revision once real repayment-rate
data exists (ties directly into FIND-004's monitoring-plan framing, `computeColdStartRepaymentRate`).

---

## Files touched

- `/Users/anicca/anicca-project/.vcsdd/features/anicca-agent-lending/specs/behavioral-spec.md`
  (iteration 1 → iteration 2; 543 lines → 821 lines)
- `/Users/anicca/anicca-project/.vcsdd/features/anicca-agent-lending/specs/verification-architecture.md`
  (iteration 1 → iteration 2; 179 lines → 220 lines)
- `/Users/anicca/anicca-project/.vcsdd/features/anicca-agent-lending/reviews/spec/iteration-1/RESOLUTION-NOTES.md`
  (this file, new)

No other files were touched: `state.json`, the reviews manifest, and verdict files under
`reviews/spec/iteration-1/output/` were left untouched per instructions. Nothing was committed or pushed.
