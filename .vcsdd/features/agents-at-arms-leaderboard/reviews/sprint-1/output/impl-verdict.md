# VCSDD Phase 3 — IMPLEMENTATION Verdict (sprint 1, fresh-context adversary)

- Feature: `agents-at-arms-leaderboard` (lean)
- Scope reviewed: PURE no-fake core — R1, R2, R3, R4, R5, R9, R10 only.
  R6/R7/R8 (UI), R11 (served-json producer), R12 (dashboard-sync enrichment) are DEFERRED to sprint 2 and were NOT failed here (noted deferred).
- Timestamp: 2026-07-01
- Tests were NOT re-run (Bash unavailable in this context). Judgment is by static disk analysis + the sprint-1 green-phase evidence log (claims 42 pass / 0 fail). Two claimed-GREEN requirements (R5 stale, R2 ordering) are NOT actually proven by any assertion on disk — see findings.

## Overall: FAIL

| Dimension | Verdict | Findings |
|---|---|---|
| Spec Fidelity | FAIL | IMPL-FIND-001 |
| Edge Case Coverage | FAIL | IMPL-FIND-006, IMPL-FIND-007, IMPL-FIND-008 |
| Implementation Correctness | FAIL | IMPL-FIND-002 |
| Structural Integrity | PASS | (see positive evidence) |
| Verification Readiness | FAIL | IMPL-FIND-003, IMPL-FIND-004, IMPL-FIND-005 |

## What genuinely holds (positive evidence)
- Self-transfer anti-buy is REAL and TESTED: `excludeSet(row)` adds `row.id` (leaderboard-constants.js:12-17); enrich.test.js:66-80 proves a self-funded "whale" (inflow from own id, $1M) does NOT out-rank a $50 external earner. This is the strongest headline claim and it stands.
- Cross-language signing-bytes contract is intact: `verifyTelemetry` recovers the signer from the verbatim `message` and never re-serializes (telemetry-verify.js:22-37); cross-lang.test.js proves a python `5.0`/`0.0` message verifies. Appending optional keys in `canonicalMessage` (telemetry-verify.js:15-18) does not regress this because the verifier is verbatim.
- Schema back-compat is additive-only and correctly guarded (`o.tags !== undefined` etc., telemetry-schema.js:16-29); existing fixtures still `ok:true` (schema.additive.test.js:10).
- Structural Integrity PASS: files are small, cohesive, immutable (`{...row}` spreads, no mutation), reader I/O is isolated behind the injected `reader` in enrich.js only; aggregate is I/O-free except for the clock read noted below. Names are accurate.

## Spec Fidelity — FAIL
- IMPL-FIND-001 (critical): `isVerified(src) = src !== 'unverified'` (telemetry-aggregate.js:4-6) counts rows with ABSENT `*_src`, so `sumVerified` sums SELF-ASSERTED figures whenever enrichment has not run. R4 mandates `=== 'chain'` strictly. aggregate.test.js:12-16 locks in the wrong behavior (total=150 from src-less rows). Because `dashboard-sync.js:14` serves `aggregate(rawRows)`, the live `total_net_worth_usd` is currently a sum of self-asserted balances instead of the R4-required `undefined`.

## Edge Case Coverage — FAIL
- IMPL-FIND-006 (medium): `Number(bigint)` precision loss above 2^53 for whale balances (enrich.js:24-25); silently-wrong VERIFIED figure; untested.
- IMPL-FIND-007 (medium): two independent enrich reads can yield `revenue_today_usd > revenue_mo_usd`, violating R9's invariant on the authoritative chain path; aggregate never re-validates.
- IMPL-FIND-008 (low): a NaN reader output (`ethUsdPrice()`) is stamped `src='chain'` and propagates to a NaN total, violating R4 "never NaN"; no `Number.isFinite` guard, no test.

## Implementation Correctness — FAIL
- IMPL-FIND-002 (major): enrich flags `earn_src='unverified'` on a read throw but leaves the SELF-ASSERTED `revenue_mo_usd` in the row (only overwritten on success). `aggregate.js:35` `selfFunded` reads `revenue_mo_usd` for every row with NO `earn_src` gate, so `self_funded_pct` is driven by self-reported numbers for unverified/un-enriched rows — a served fake headline stat.

## Verification Readiness — FAIL
- IMPL-FIND-003 (major): R5 `stale` (aggregate.js:40) has ZERO proving test; the only "stale" assertion (verify.test.js:60) is the unrelated verifier freshness check. It is untestable as written because aggregate reads `Date.now()` (aggregate.js:30) with no injectable clock (purity_boundary: a "pure" fn per the verification-architecture reads wall-clock + `new Date()`).
- IMPL-FIND-004 (major): R2's core guarantees "unverified never out-ranks verified" and the `net_worth_usd` tie-break are UNTESTED; the only ranking test uses two both-verified rows. The `rankCmp` verified-vs-unverified and net_worth-tie branches are unexercised.
- IMPL-FIND-005 (major): `SEED_ADDRESSES` is a placeholder `0x…a1` (leaderboard-constants.js:10) and the seed anti-buy test references `SEED_ADDRESSES[0]` dynamically — it proves nothing about the real treasury (0x810f) being excluded. In production, seed/treasury money CAN currently buy rank; the headline claim is false until the constant is filled. `OUR_INSTANCE_IDS` is `[]`.

## Must-fix before sprint-1 core can be called done (core scope only)
1. `isVerified` → strict `=== 'chain'` (IMPL-FIND-001).
2. Gate `self_funded_pct`/`selfFunded` on verified earnings, or null out unverified figures in enrich (IMPL-FIND-002).
3. Inject the clock into `aggregate` and add the R5 `stale` test (IMPL-FIND-003).
4. Add R2 tests: unverified-below-verified + net_worth tie-break (IMPL-FIND-004).
5. Fill real `SEED_ADDRESSES` + `OUR_INSTANCE_IDS` and test against a concrete seed addr (IMPL-FIND-005).
6. Handle non-finite / >2^53 / non-monotonic reader outputs (IMPL-FIND-006/007/008).
