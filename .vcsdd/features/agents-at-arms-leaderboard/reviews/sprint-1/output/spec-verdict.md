# VCSDD Phase 1c Spec-Review Verdict (ROUND 5 / RE-REVIEW) — agents-at-arms-leaderboard

- Feature: `agents-at-arms-leaderboard` (lean mode)
- Review scope: `reviews/sprint-1/` (behavioral spec gate, **v5 spec**)
- Reviewer: fresh-context adversary (disk-only, zero builder context)
- Round: 5 (re-review of the v5 rewrite)
- Timestamp: 2026-07-01
- Artifact under judgment: `.vcsdd/features/agents-at-arms-leaderboard/specs/behavioral-spec.md` (v5)

## Overall verdict: **PASS**

All three round-4 must-fix items are genuinely resolved on disk, and the core invariant INV-NOFAKE is
now provable within an honestly-stated scope. No new load-bearing defect found. The remaining items are
Phase-2 refinements explicitly out of a Phase-1 gate's bar (listed below as non-blocking).

| Dimension | R1 | R2 | R3 | R4 | **R5** |
|---|---|---|---|---|---|
| 1. Spec Fidelity | FAIL | FAIL | FAIL | FAIL | **PASS** |
| 2. Edge Cases | FAIL | FAIL | FAIL | PASS | **PASS** |
| 3. Impl Correctness (testability) | FAIL | FAIL | FAIL | FAIL | **PASS** |
| 4. Structural Integrity | FAIL | FAIL | FAIL | FAIL | **PASS** |
| 5. Verification Readiness | FAIL | FAIL | FAIL | FAIL | **PASS** |

---

## Round-4 must-fix disposition (every item re-checked against disk)

### 1. R4-FIND-002 + R3-FIND-001/-006 (per-row exclude set + HONEST INV-NOFAKE) — **RESOLVED**
- Per-row exclude is now defined as a helper, not a static set: `excludeSet(row) → Set<string>` =
  `{ row.id } ∪ OUR_INSTANCE_IDS ∪ SEED_ADDRESSES` (PER ROW), with only `OUR_INSTANCE_IDS` /
  `SEED_ADDRESSES` as checked-in constants (`behavioral-spec.md:19-22`). R3 passes `excludeSet(row)` to
  the per-id inflow call (`:48-49`). The incoherence (one static set cannot hold an arbitrary entrant's
  own id) is gone; self-transfers from a hackathon entrant's own wallet are now excluded.
- The overclaim is gone. INV-NOFAKE (`:78-86`) now claims ONLY what it delivers: ranked `revenue_*` is
  on-chain external USDC inflow (not self-asserted), and self/seed/treasury self-funding cannot buy rank.
  The donation/airdrop/fresh-sybil hole is explicitly disclosed as a KNOWN v1 LIMITATION with the
  earn-ledger settlement cross-check named as the follow-up (`:82-86`). This is exactly the
  "downgrade-to-true-scope + document the residual hole" path round-4 offered.
- The anti-buy claim is provable: the reader's `externalInflowsUsd(addr, sinceTs, excludeSet)` excludes
  `from ∈ excludeSet` (`:30`), so an own-id/seed-only inflow → 0. The 1b R3 proof now matches
  ("only inflows from its OWN id / a SEED address → revenue 0 → NOT rank #1", `:102`).

### 2. R4-FIND-001 (`net_worth_usd` dimensioned) — **RESOLVED**
- `ethUsdPrice() → number // USD per 1 ETH` added to the reader (`:29`); throw ⇒ `unverified` (`:31`,
  `:50-51`). R3 specifies `net_worth_usd = usdcBalanceAtomic(id)/1e6 + (nativeBalanceWei(id)/1e18) *
  ethUsdPrice()` (`:48`). Dimensionally sound (USD + ETH×USD/ETH = USD) and exactly testable with a mock
  reader; 1b R3 proof checks the dimensioned formula (`:102`).

### 3. R4-FIND-003 (R12 reconciles the live `dashboard-sync.js`) — **RESOLVED**
- R12 (`:73-76`) requires EVERY producer that emits `leaderboard` — INCLUDING the live netlify
  `apps/landing/netlify/functions/dashboard-sync.js` — to apply `enrichOnChain` before `aggregate`, and
  forbids serving a raw self-reported leaderboard from ANY endpoint, explicitly "(Reconciles
  dashboard-sync.js:14)". Confirmed against live code: `dashboard-sync.js:14` does return
  `aggregate(rows)` of raw rows and `telemetry-aggregate.js:10` sorts by raw `net_worth_usd` — the
  precise gameable path now governed. The 1b R12 proof (`:111`) drives a concrete test: invoke the
  netlify handler with raw rows + a mock reader → its `leaderboard` reflects ENRICHED figures
  (self-transfer excluded). The pipeline rule "enrich BEFORE aggregate, everywhere" (`:33-37`) ties both
  producers together; `aggregate` stays pure, `enrichOnChain` is the only chain caller (purity boundary).

---

## Dimension notes (positive evidence)

- **Spec Fidelity — PASS.** Each R1–R12 maps to real disk artifacts: `aggregate` emits `leaderboard`
  (`telemetry-aggregate.js:10`), verbatim-signer recovery exists (`telemetry-verify.js:17-29`),
  `EmpireDashboard` owns `DashboardData` + fetches `/dashboard.json` (`EmpireDashboard.tsx:52-56,66`),
  static `public/dashboard.json` has no leaderboard (matches `:16`). INV-NOFAKE no longer asserts an
  impossibility it cannot deliver.
- **Edge Cases — PASS.** All-unverified total → `undefined`→`—` not `$0` (R4 `:52-54`, R8 `:63`);
  `revenue_today_usd ≥0 ∧ ≤ revenue_mo_usd` and `revenue_by_source ≥0` (R9 `:65-66`); stale derivation
  and `dead`/`critical` visibility (R5 `:55`); empty filter → empty-state (R8 `:63`); self/seed anti-buy
  edge proven (R3 `:102`).
- **Impl Correctness / Testability — PASS.** Reader is mock-injectable with deterministic, dimensioned
  arithmetic; throw⇒`unverified` per figure; per-row exclude is computable at enrich time. RED tests have
  unambiguous expected values.
- **Structural Integrity — PASS.** Single enriched source guaranteed across both producers (R12 +
  pipeline rule); the served-file producer (R11) and the netlify function (R12) are both reconciled; UI
  reads the existing fetch. `aggregate` stays pure, chain I/O isolated in `enrichOnChain`.
- **Verification Readiness — PASS.** The 1b table proves each R1–R12 including the per-row anti-buy
  proof, the dimensioned net-worth proof, and the netlify-enrich proof, plus a browser E2E gate for
  R6/R7. INV-NOFAKE is provable within its stated scope.

---

## Non-blocking (Phase-2 hygiene — do NOT re-litigate at the gate)
These do not affect the core guarantee, are not testability blockers, and must not gate Phase 2:
1. `behavioral-spec.md:18` labels `leaderboard-constants.js` "checked-in," but the file does not yet
   exist on disk (Glob: none). It is a Phase-2 artifact; rename to "to be added" or create it in GREEN.
2. R2's tie-break ranks verified rows by `net_worth_usd` (`:44-45`), while R3 says an `unverified`
   net-worth figure is "never ranked" (`:50-51`). On an exact `revenue_mo_usd` tie where one row's
   `net_worth_src==='unverified'`, the tie-break key is ambiguous (flagged/undefined). Specify the
   tie-break to fall through to `id` asc when a tied row's `net_worth_src!=='chain'`.
3. R6's render contract (`:58-60`) omits `revenue_by_source`, though it is carried (R1), typed (R9), and
   signed (R10). If/when rendered, label its self-reported provenance (design §5 drill-down).

## Recommendation
Proceed to Phase 2 (RED). Build the 1b proofs as written — especially the hackathon-entrant
self/seed anti-buy proof (R3) and the netlify-handler enrich proof (R12) — then your own no-mock E2E +
CloakBrowser verify on the live `/dashboard`.
