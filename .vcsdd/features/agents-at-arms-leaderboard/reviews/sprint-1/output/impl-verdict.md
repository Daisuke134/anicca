# VCSDD Phase 3 — IMPLEMENTATION Verdict (sprint 1, fresh-context adversary, ROUND 2)

- Feature: `agents-at-arms-leaderboard` (lean)
- Scope reviewed: PURE no-fake core — R1, R2, R3, R4, R5, R9, R10 only.
  R6/R7/R8 (UI), R11 (served-json producer), R12 (netlify dashboard-sync enrichment) are DEFERRED to
  sprint 2 and were NOT failed here.
- Timestamp: 2026-07-01
- Round 1 verdict: FAIL (IMPL-FIND-001..008). This round re-checks each on disk + hunts new regressions.

## Test execution honesty
I could NOT execute `node --test` in this review context — the Bash tool is not enabled here
(HONESTY Rule 4: I do not claim "N pass" without running it). Instead I traced EVERY assertion in all
9 `_lib/__tests__/*.test.js` files against the implementation by hand, line by line. `ethers@^6.16.0`
is a declared dep (apps/landing/package.json:20); `../telemetry.js` and `../telemetry-store.js` exist so
`handler-telemetry.test.js` / `store.test.js` load; `cross-lang.test.js` self-SKIPs when python3/eth_account
is absent. Every traced assertion matches the code. The next gate (my own no-mock run) still owes a real
`node --test` execution — that is a runtime gate, not this disk gate.

## Overall: PASS

| Dimension | Verdict | Notes |
|---|---|---|
| Spec Fidelity | PASS | IMPL-FIND-001 resolved |
| Edge Case Coverage | PASS | IMPL-FIND-007, -008 resolved+tested; -006 non-material (see below) |
| Implementation Correctness | PASS | IMPL-FIND-002 resolved+tested |
| Structural Integrity | PASS | small/immutable/isolated (unchanged) |
| Verification Readiness | PASS | IMPL-FIND-003, -004 resolved+tested; -005 mechanism tested + honestly TODO-scoped, carried to sprint 2 |

## Round-1 finding re-check (RESOLVED / OPEN)

| Finding | Status | Evidence on disk |
|---|---|---|
| IMPL-FIND-001 (R4 strict `chain`) | RESOLVED | `isVerified(src){ return src === "chain"; }` (telemetry-aggregate.js:5-7). Absent/`unverified` no longer summed. Test aggregate.test.js:36-42 asserts absent-src ⇒ `total_net_worth_usd===undefined` and `earned_mo_usd===undefined`; unverified ⇒ undefined. |
| IMPL-FIND-002 (self_funded gated on `earn_src==='chain'`) | RESOLVED | selfFunded filter now `r.earn_src === "chain" && …` (telemetry-aggregate.js:37-39). Test aggregate.test.js:43-46: unverified row with `revenue_mo_usd:1000` ⇒ `self_funded_pct===0`. |
| IMPL-FIND-003 (stale testable, injected clock) | RESOLVED | `aggregate(rows, nowMs = Date.now())` (telemetry-aggregate.js:31); stale uses injected `nowSec` (line 32,44). No wall-clock in the core path when nowMs supplied. Test aggregate.test.js:61-69: fresh ⇒ `stale:false`, +601s ⇒ `stale:true`, `status:"dead"` unchanged/visible. |
| IMPL-FIND-004 (R2 verified out-ranks unverified + net_worth tiebreak) | RESOLVED | rankCmp verified-first branch (telemetry-aggregate.js:13) + net_worth tiebreak gated on both `net_worth_src==='chain'` (line 16). Tests aggregate.test.js:47-52 (unverified 9e9 whale ranks below chain earner of $5) and :54-60 (equal revenue ⇒ higher net_worth wins). |
| IMPL-FIND-005 (SEED/OUR real values) | OPEN — carried to sprint 2 (IMPL2-FIND-001) | Mechanism is real+tested (`excludeSet` folds in `SEED_ADDRESSES`, enrich.test.js:51-64 excludes a seed-listed sender; own-id self-transfer excluded). `SEED_ADDRESSES` is still the placeholder `0x…a1` and `OUR_INSTANCE_IDS` is `[]` (leaderboard-constants.js:6,10) — honestly flagged with a TODO. No live producer serves a real chain reader in sprint 1 (R11/R12 deferred), so the gap cannot ship a false ranking yet. Fill BEFORE sprint-2 producers go live. Not a sprint-1 core blocker. |
| edge-006 (`Number(bigint)` > 2^53) | OPEN — non-material (IMPL2-FIND-002) | enrich.js:24-25 still `Number(atomic)/1e6`. But the result is a fractional USD double: relative precision ~15–16 sig figs governs, so a >2^53-atomic balance yields a USD error on the order of 1e-13 — immaterial for a net-worth display/rank. The spec's binding "never NaN" (R4) and "dimensioned exact" at test scale ARE met. Not load-bearing; documented residual. |
| edge-007 (today ≤ mo clamp) | RESOLVED | `e.revenue_today_usd = Math.min(today, mo)` (enrich.js:41). Test enrich.test.js:111-126 (reader returns mo=5 then today=9 ⇒ clamped to 5). |
| edge-008 (NaN price ⇒ unverified, never NaN total) | RESOLVED | `if (!Number.isFinite(nw)) throw` ⇒ catch sets `net_worth_src='unverified'` (enrich.js:28,31-33); earnings guarded likewise (line 39). Defense-in-depth in sumVerified: `Number.isFinite(sum) ? sum : undefined` (telemetry-aggregate.js:28). Test enrich.test.js:104-109: `price:NaN` ⇒ `net_worth_src==='unverified'`. |

## What genuinely holds (positive evidence)
- No-fake totals: R4 now strict `=== 'chain'`; un-enriched/self-asserted figures are never summed
  (telemetry-aggregate.js:5-7,23-29 + aggregate.test.js:36-42).
- Anti-buy: own-id self-transfer excluded per-row (leaderboard-constants.js:12-17) and a self/seed-funded
  $1M "whale" ranks below a $50 external earner (enrich.test.js:66-80).
- Rank integrity: an unverified 9e9 whale sorts below a $5 chain earner (aggregate.test.js:47-52) — the
  central anti-fake ordering claim, now proven.
- Cross-language signing intact: verifier recovers signer from the verbatim `message`, never re-serializes
  (telemetry-verify.js:22-37); python `5.0`/`0.0` still verifies (verify.test.js:23-32, cross-lang.test.js).
- Additive schema/back-compat: guarded `!== undefined` (telemetry-schema.js:16-29); base rows still `ok:true`.
- Purity: aggregate is I/O-free with injected `nowMs`; the only chain caller is `enrichOnChain` behind the
  injected `reader`.

## Residual gaps carried to sprint 2 (NOT sprint-1 core blockers)
1. IMPL2-FIND-001 — fill real `SEED_ADDRESSES` (founder/treasury 0x810f…) + `OUR_INSTANCE_IDS`, and test
   against a hard-coded real-looking seed addr (not `SEED_ADDRESSES[0]`), BEFORE the R11/R12 live producers
   serve any leaderboard. Until then the INV-NOFAKE "seed/treasury can't buy rank" claim is only mechanism-true.
2. IMPL2-FIND-002 — either document the safe `Number(bigint)` USD-precision ceiling or scale with BigInt;
   add a >2^53 fixture. Non-material today; log it so it is not silently forgotten.
3. Minor (no finding): R2 sub-branch "a chain earner whose `net_worth_src!=='chain'` falls to `id` asc on a
   revenue tie" (rankCmp:16 guard) is not directly exercised; add when convenient.
