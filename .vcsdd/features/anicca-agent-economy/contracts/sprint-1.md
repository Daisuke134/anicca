---
status: draft
feature: anicca-agent-economy
sprint: 1
date: 2026-07-07
negotiationRound: 1
scope: "Gig-board concurrency hardening (REQ-101..103: lock-staleness liveness + atomic stale-reclaim, cross-gigId shared-board-file protection, zero-regression of round-1/2/3 fund-safety invariants); bootstrap-reserve catalog eligibility gate (REQ-201..203: BOOTSTRAP_RESERVE_USDC threshold, registry.json risk/alwaysAvailable classification of all 17 live slots, open-position carve-out for hl_trade/yield, bookkeeping-only design constraint); business.blockrun.ai seller-channel research spike (REQ-301..302: feasibility record + non-blocking guarantee on the gig-board witness track). Files touched: skills/economy/gig/lib/lock.mjs, skills/economy/gig/gig.mjs (both in ~/anicca), runtime/loop/catalog-gate.mjs (new), runtime/loop/index.mjs, runtime/loop/package.json, skills/registry.json, .vcsdd/features/anicca-agent-economy/evidence/business-blockrun-ai-research.md."
criteria:
  - id: CRIT-001
    dimension: spec_fidelity
    description: >
      isLockStale(nowMs, mtimeMs, staleMs) is extracted as an independently exported pure function
      from skills/economy/gig/lib/lock.mjs, and acquire() calls it rather than re-implementing the
      Date.now() - stat.mtimeMs > staleMs comparison inline (REQ-101 binding acceptance criterion,
      PROP-101a/b/d); AND REQ-101's headline liveness guarantee -- a live holder's lock is never
      stolen by elapsed wall-clock time alone -- is protected by name.
    weight: 0.15
    passThreshold: >
      A control-flow read of ~/anicca/skills/economy/gig/lib/lock.mjs shows (1) `isLockStale` present
      in the module's export list/signature, (2) `acquire()`'s stale-branch invoking `isLockStale(...)`
      by name rather than containing its own inline `Date.now() - ... > staleMs` comparison, and (3)
      lock.test.mjs's PROP-101a/b/c(purity-half)/d tests import and exercise `isLockStale` directly
      (not only indirectly through `acquire()`). Evidence on file: sprint-1-green-phase.log lines
      17, 96-98, 288 (8/8 lock.test.mjs PASS) and lines 309-317 (Phase 2c: extraction refactored
      into `tryCreateLockFile`/`reclaimStaleLock` helpers with identical control flow, re-verified
      48/48). (4) Additionally, lock.test.mjs's integration-level test named exactly
      `★GAP 1★ a live holder's lock is NEVER stolen while it's still working past staleMs (heartbeat
      keeps it alive)` (lock.test.mjs:24-61) is present BY NAME and passes when independently re-run
      by the adversary, mirroring CRIT-002's by-name treatment of the atomicity test. FAIL if the
      comparison is still inlined anywhere in `acquire()`, if `isLockStale` is not importable from
      outside the module, or if the `★GAP 1★` test is missing, renamed away, weakened (e.g. reduced
      from its full multi-heartbeat/3x-staleMs long-running scenario to a single-tick check), or
      fails on the adversary's own independent re-run.
  - id: CRIT-002
    dimension: spec_fidelity
    description: >
      Stale-lock reclaim is atomic (no check-then-act window where two concurrent reclaimers can both
      succeed) — REQ-101's binding "atomic filesystem primitive, never check-then-act" requirement,
      PROP-101c (Tier 2 atomicity half).
    passThreshold: >
      A read of `acquire()`'s reclaim branch in ~/anicca/skills/economy/gig/lib/lock.mjs confirms it
      uses a single atomic primitive (fs.rename to a unique trash path, per sprint-1-green-phase.log
      lines 99-105) rather than the prior unlink-then-open sequence, and the Tier-2 test "two
      concurrent stale-lock reclaim attempts on the SAME lock key — exactly ONE must win" (named
      `★PROP-101c (Tier 2, atomicity)★` in lock.test.mjs) passes when actually re-run by the adversary
      itself (not merely accepted from the builder's log). FAIL if the reclaim path still contains an
      unlink-then-open sequence, or if the adversary's own re-run of the atomicity test fails or flakes
      across 3 repeated executions.
    weight: 0.15
  - id: CRIT-003
    dimension: edge_case_coverage
    description: >
      A slow operation on one gigId never clobbers a concurrent, already-succeeded operation on an
      unrelated gigId, including the 3-way case across three distinct gigIds (REQ-102, PROP-102a/b/c).
    weight: 0.15
    passThreshold: >
      The adversary independently re-runs `node --test __tests__/gig.test.mjs` in
      ~/anicca/skills/economy/gig and confirms `★PROP-102a (3-way)★`, `★PROP-102b★`, and `★PROP-102c★`
      all pass, AND performs its own control-flow read of `gig.mjs`'s `applyAndSave()` confirming (a)
      the board is re-read fresh from disk immediately before each mutation (not a stale in-memory
      snapshot), (b) the shared `"_board"` lock's critical section covers only the local
      read-mutate-write, not the network/settle step, and (c) the bounded backoff retry
      (`BOARD_LOCK_RETRY_ATTEMPTS`/`_DELAY_MS`, per sprint-1-green-phase.log lines 106-116) is scoped
      ONLY to the shared board lock, never to per-gigId locks. FAIL if the 3-way test fails/flakes on
      independent re-run, or if the retry logic is found to also apply to per-gigId lock acquisition
      (which would reintroduce a fund-safety fail-open risk).
  - id: CRIT-004
    dimension: verification_readiness
    description: >
      The full pre-existing skills/economy/gig test suite (store/decide/lock/gig/ensure-agent-id) is
      genuinely green with zero regressions, and the round-1 fail-open exploits (self-verify,
      same-gig double-pay) are independently re-attacked by the Phase 3 adversary itself — not
      accepted from the builder's same-day self-report (REQ-103, PROP-103a/b).
    weight: 0.15
    passThreshold: >
      Adversary runs `cd ~/anicca/skills/economy/gig && node --test __tests__/*.test.mjs` itself and
      confirms exactly 48/48 pass (matching sprint-1-green-phase.log lines 78-92), with the specific
      fund-safety assertions `★FINDING 1★` (non-poster rejected), `★FINDING 2★` (concurrent same-gig
      double-verify pays exactly once), and `★FINDING 3★` (invalid ERC-8004 identity rejected at
      post/take/payout) all present and passing by name. Tier-3 live/testnet re-attack of the round-1
      exploits MUST be executed by the adversary with its own new transaction hashes/timestamps — a
      reference to `evidence/p2.2-security-fixes-round3.md` alone does NOT satisfy this criterion.
      "Out of scope for THIS sprint's binary pass" refers ONLY to reliance on the stale round-3
      self-report as a substitute for execution — it does NOT place Tier-3 live re-execution itself
      out of scope. That live re-execution is the Phase 3 adversary's own MANDATORY obligation to
      perform, per REQ-103's binding acceptance criterion (behavioral-spec.md:170-175: "this
      re-attack MUST be independently executed by the Phase 3 adversary itself... a builder's own
      prior self-report is evidence of history, not a substitute for the fresh, independent
      re-verification this requirement demands") and verification-architecture.md's Gate item (3)
      (verification-architecture.md:144-148: "the round-1 exploit scripts are re-attempted by the
      adversary itself, live, producing its own new transaction hashes"). FAIL if the count is not
      exactly 48/48, if any of the three named FINDING tests is missing/renamed away, if the
      adversary substitutes the round-3 self-report for its own independent Tier-3 run, OR if the
      adversary performs NO Tier-3 live/testnet re-attack at all (an outright skip is itself a FAIL,
      identical in effect to substitution — the absence of any independent Tier-3 attempt fails this
      criterion exactly as substituting the old report would).
  - id: CRIT-005
    dimension: spec_fidelity
    description: >
      filterCatalog is a pure, deterministic function whose exclusion decisions are based solely on
      the explicit risk/alwaysAvailable classification of all 17 currently-live skills/registry.json
      slots (matching behavioral-spec.md's REQ-201 classification table verbatim), and contains no
      ranking/scoring/preference logic (REQ-201/203, PROP-201a-h — PROP-201i is explicitly EXCLUDED
      from this criterion's scope, since CRIT-006 exclusively and concretely grades PROP-201i's
      lazy/fail-open hl_trade query behavior — PROP-201g, PROP-203a/b).
    weight: 0.2
    passThreshold: >
      Adversary (1) parses ~/anicca/skills/registry.json itself and confirms all 17 `status: "live"`
      slots carry an explicit `risk: "safe"`, `risk: "capital"`, or `alwaysAvailable: true` field
      matching behavioral-spec.md's table exactly (report/cook=alwaysAvailable; self/spawn,
      self/spawn-child, self/issue-dev, self/coordinate, economy/gig, economy/ubi, x402_sell,
      earn/clip, earn/clip-producer, earn/video=risk:safe; yield, hl_trade, token_launch,
      earn/sol-trade, earn/polymarket-trade=risk:capital) — independently re-deriving at least a
      sample of these from the named slots' own code, not merely trusting the table; (2) re-runs
      `cd ~/anicca/runtime/loop && node --test __tests__/catalog-gate.test.mjs
      __tests__/registry-classification.test.mjs` and confirms 17/17 + 3/3 pass; (3) reads
      `catalog-gate.mjs`'s diff and confirms zero scoring/ranking/preference fields on the return
      type and zero new prompt-steering text in `index.mjs`'s wiring (scope: this increment's own new
      code only, per PROP-203b's post-REQ-204-split scoping — NOT an audit of prompt.mjs's
      pre-existing `## COLONY BOOTSTRAP PRIORITY`/`## MINDSET` sections, which are explicitly out of
      this sprint's scope). FAIL if any live slot is untagged, if a tag mismatches the table, if the
      test counts differ from 17/17 and 3/3, or if any scoring/ranking logic is found in the new diff.
  - id: CRIT-006
    dimension: edge_case_coverage
    description: >
      The catalog restriction is non-sticky: a balance transition from below to at/above
      BOOTSTRAP_RESERVE_USDC between two consecutive wakes restores the exact full, unfiltered
      slot list on the very next wake, with no persisted "still restricted" state (REQ-202,
      PROP-202a/b), and the open-position carve-out (hl_trade/yield) behaves per its two distinct,
      specified mechanisms (PROP-201f/h/i).
    weight: 0.1
    passThreshold: >
      Adversary confirms, from catalog-gate.test.mjs's own two-successive-call test, that
      `filterCatalog` holds no state across calls (PROP-202a) and that a below→at/above transition
      between two calls restores the full list (PROP-202b) — both already asserted in the 17/17 run
      above. Additionally confirms via a deliberately-induced failure (unreachable/rejecting query
      function) that `hasOpenRiskPositionOf('hl_trade')` resolves `true` (fail-open), not `false`,
      and that this query is never invoked when balanceUsdc >= BOOTSTRAP_RESERVE_USDC (spy/call-count
      = 0 in that case) — matching PROP-201i(a)/(b)/(c)'s three named tests. FAIL if any state leakage
      between calls is found, if the hl_trade query fires unconditionally on every wake, or if a
      forced query failure resolves to `false`/an uncaught throw instead of `true`.
  - id: CRIT-007
    dimension: spec_fidelity
    description: >
      The business.blockrun.ai research record contains all five required items (a)-(e), each
      supported by concrete, re-checkable evidence rather than a bare assertion (REQ-301,
      PROP-301a/b).
    weight: 0.05
    passThreshold: >
      `.vcsdd/features/anicca-agent-economy/evidence/business-blockrun-ai-research.md` exists and
      contains distinct, separately-headed sections for (a) seller/listing API existence — finding:
      NO, only manual Telegram onboarding (t.me/bc1max); (b) fee/take-rate — finding: not discoverable
      for third-party sellers; (c) Coinbase CDP dependency location — finding: marketplace-side, buyer
      role only, seller-side unknown; (d) implementation-effort estimate — finding: not applicable, no
      path to size; (e) recommendation — DEPRIORITIZE vs. the self-built gig board. Adversary
      spot-checks at least 2 of the 9 cited sources (e.g. re-runs `gh pr view 83 --repo
      BlockRunAI/Franklin` and confirms state OPEN/mergedAt null, or re-scrapes `blockrun.ai` and
      confirms the "Add yours... Contact us" copy is still present) and confirms the claim matches.
      FAIL if any of (a)-(e) is missing, is a bare assertion with no cited evidence, or if a
      spot-checked source contradicts the record's claim without the record being updated.
  - id: CRIT-008
    dimension: verification_readiness
    description: >
      This increment introduces no new dependency from the gig-board witness track onto REQ-301's
      research record's existence or completion (REQ-302, PROP-302a).
    weight: 0.05
    passThreshold: >
      Adversary greps `skills/economy/gig/WITNESS-RUNBOOK.md` (and any other gig-board witness
      runbook/code path) for references to `REQ-301`, `business.blockrun.ai`, or
      `business-blockrun-ai-research.md` and confirms zero gating hits — matching
      research-record.test.mjs's own PROP-302a check (sprint-1-green-phase.log lines 262, 273-282,
      183-186 of business-blockrun-ai-research.md). FAIL if any new conditional/gate in the witness
      runbook or gig-board code references the research record's status.
knownResidualFindings:
  - "3-way cross-gigId board-lock race (originally surfaced as a genuine RED-phase finding under
    PROP-102a's 3-way extension, sprint-1-red-phase.log lines 118-140): fixed in Phase 2b via a
    bounded backoff retry on the shared \"_board\" lock in gig.mjs's applyAndSave(), scoped only to
    that lock (never per-gigId locks). Re-verified green in Phase 2b (48/48) and again after Phase 2c
    refactor (48/48, sprint-1-green-phase.log lines 341-347). The Phase 3 adversary MUST independently
    re-run the 3-way test itself (not merely accept the builder's log) as part of CRIT-003."
  - "Stale-lock unlink-then-open race (surfaced as a \"noteworthy\" reproducible finding during
    Phase 2a, sprint-1-red-phase.log lines 59-72, masked at RED time by lock.test.mjs's whole-file
    import failure): fixed in Phase 2b via an atomic fs.rename-based reclaim replacing the prior
    fs.unlink-then-fs.open('wx') sequence (sprint-1-green-phase.log lines 99-105), and refactored in
    Phase 2c into tryCreateLockFile()/reclaimStaleLock() helpers with identical control flow
    (sprint-1-green-phase.log lines 309-317). Re-verified green (8/8 lock.test.mjs) both before and
    after refactor. The Phase 3 adversary MUST independently re-run the Tier-2 atomicity test itself
    as part of CRIT-002, not accept the builder's report of it passing."
---

## Execution-Tooling Note (Phase 3 Prerequisite)

Several criteria below (CRIT-002, CRIT-003, CRIT-004, CRIT-006, CRIT-007) require an adversary to
independently EXECUTE code (`node --test ...`) or, for CRIT-004's Tier-3 half, perform a live/testnet
chain re-attack. These execution-bound acceptance criteria are satisfied during **Phase 3's
implementation review**, by a review agent explicitly provisioned with a code-execution tool
(Bash/shell) and, for CRIT-004's Tier-3 half, live/testnet chain access. This contract-negotiation
phase itself is a disk-only (Read/Grep/Glob) review and does not itself execute code or chains — its
job is to verify that the contract's text correctly and unambiguously specifies these obligations, not
to discharge them. A disk-only contract-review pass being unable to run `node --test` or touch a live
chain is not itself a violation of these criteria; it becomes a violation only if a Phase 3 review
claims PASS on CRIT-002/003/004/006/007 without actually being equipped with, and using, an
execution-capable (and, where required, chain-capable) tool.

## Scope

This sprint delivers the exact 8-requirement, 25-proof-obligation increment defined in
`specs/behavioral-spec.md` (REQ-101..103, REQ-201..203, REQ-301..302; REQ-204 was split out of this
increment on 2026-07-07 per Dais-approved decision and is tracked as an independent future backlog
item — it is NOT part of this sprint's scope and no CRIT below evaluates it):

1. **Gig-board concurrency hardening (REQ-101..103)** — `skills/economy/gig/lib/lock.mjs` (extracted
   `isLockStale`, atomic `fs.rename`-based stale reclaim) and `skills/economy/gig/gig.mjs` (bounded
   backoff retry on the shared `"_board"` lock for cross-gigId protection), with zero regression of
   the round-1/2/3 fund-safety invariants (poster-auth, no-double-pay, ERC-8004 re-verification).
2. **Bootstrap-reserve catalog eligibility gate (REQ-201..203)** — new `runtime/loop/catalog-gate.mjs`
   (`filterCatalog`, `hasOpenRiskPositionOfYield`, `hasOpenRiskPositionOfHlTrade`), `runtime/loop/index.mjs`
   wiring, and explicit `risk`/`alwaysAvailable` classification of all 17 currently-live
   `skills/registry.json` slots.
3. **business.blockrun.ai seller-channel research spike (REQ-301..302)** — a factual research record
   at `evidence/business-blockrun-ai-research.md` recommending DEPRIORITIZE, with a structural
   guarantee that this research introduces no gate on the parallel gig-board witness track.

Phase 2b/2c evidence on file: `evidence/sprint-1-green-phase.log` (target-feature-tests: PASS,
regression-baseline: PASS — 48/48 in `skills/economy/gig`, 17/17 + 3/3 in `runtime/loop`'s new
catalog-gate/registry-classification tests, 72/76 unit + 12/12 integration in `runtime/loop`'s
pre-existing suites with the same 4 pre-existing unrelated tier-default failures unchanged, 3/3 in
the research-record test).

## Known residual findings (see frontmatter `knownResidualFindings` for full detail)

Two genuine concurrency findings surfaced during Phase 2a's RED-phase testing (not silently papered
over): a 3-way cross-gigId board-lock race, and a stale-lock unlink-then-open race. Both are recorded
as fixed in Phase 2b and re-verified in Phase 2c per `evidence/sprint-1-green-phase.log`. The Phase 3
adversary is required to independently re-execute both fixes' regression tests itself (CRIT-002,
CRIT-003) rather than accept the builder's self-reported PASS as sufficient — this is the same
independent-verification standard REQ-103/PROP-103b already demands for the round-1 fund-safety
exploits, applied consistently to this sprint's own two new findings.
