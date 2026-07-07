# Verification Report — anicca-agent-lending (Phase 5, Formal Hardening)

**date**: 2026-07-08 · **mode**: strict · **sprint**: 1 · **verifier**: fresh-context Phase 5 session
(not the same context as Phase 2/3's Builder/adversary passes)

**Scope note (language/toolchain)**: `state.json`'s `language: "typescript"` field is a stale profile
default — this feature (and the whole `~/anicca` sibling codebase) is plain ESM JavaScript (`.mjs`),
tested via Node's built-in `node:test` runner. Every command below was run as
`cd ~/anicca && node --test skills/economy/lending/lib/__tests__/*.test.mjs`, never vitest/Stryker.
`fast-check` (added this session, `~/anicca/package.json` devDependencies, v4.8.0) is used for Tier-1
property-based tests — it is JS/TS-agnostic and fits this repo's real toolchain.

## Summary

| Metric | Count |
|---|---|
| Required proof obligations, Tier > 0 (this session's scope; Tier 0 already verified Phase 3) | 51 |
| **Proved this session** | **38** |
| Not provable this sprint (orchestrator does not exist yet — see below) | 13 |
| Full target-feature test suite | **89/89 passing** (0 fail, 0 skipped) — 79 pre-existing + 10 new `fast-check` property tests |
| New test file added | `skills/economy/lending/lib/__tests__/lending-gate.property.test.mjs` (10 tests, `~/anicca`) |
| Live E2E artifact | Real Base-mainnet (chain 8453) USDC Transfer, tx `0x849362757b4ec7e2a6f982384475a2d08156b2d3162741880e4719ed05598a44`, block `0x2e16535` — see PROP-025 below |
| Security static analysis | Semgrep `--config=auto` + `--config=p/security-audit --config=p/secrets`: **0 findings** across 261 rules; manual read surfaced 2 LOW-severity, non-blocking observations (see `security-report.md`) |
| Purity boundary audit | Confirmed intact — see `purity-audit.md` |

**The headline finding of this phase**: of the 51 required Tier>0 obligations, **13 cannot be proved
this sprint because the effectful loan-issuance/repayment orchestrator they depend on does not exist
yet** — this is a pre-existing, already-adversary-reviewed (PASS) scope boundary explicitly recorded in
`contracts/sprint-1.md`'s own "Known residual scope boundary" section, not a defect introduced or
discovered this phase. Two additional obligations (PROP-037's Tier-2 half, PROP-055, plus PROP-038 —
see "Contract-listing gap" below) share the identical root cause but were **not** explicitly named in
that contract section; this is flagged as a completeness gap in the contract's own listing, not a new
scope decision. **Because `vcsdd-state.js`'s own Phase-6 gate prerequisite requires literally every
`required:true` obligation to reach `status:"proved"` before Phase 6 (convergence) can be entered, these
13 obligations structurally block Phase 6 today.** This is a decision for the orchestrator (team-lead):
either open a sprint-2 that builds the orchestrator and closes these for real, or make an explicit,
recorded decision to downgrade some/all of them to `required:false` citing this sprint contract's
already-PASSed scope boundary (a scope decision, not something this session unilaterally applied).

## Proof Obligations

### Proved (38)

| ID | PROP anchor | Tier | Evidence |
|---|---|---|---|
| PROP-001 | 101a | 1 | `lending-gate.test.mjs:80-96` (3 fixtures) + NEW `lending-gate.property.test.mjs` "PROP-101a (property)" (500 runs: never negative, exact `max(0,...)` formula for arbitrary finite inputs) |
| PROP-002 | 101b | 1 | `lending-gate.test.mjs:98` |
| PROP-003 | 101c | 1 | `lending-gate.test.mjs:107` + NEW property test "PROP-101c (property)" (200 runs: NaN/undefined/±Infinity/negative → finite, non-negative, never throws) |
| PROP-004 | 101d | 1 | `lending-gate.test.mjs:115` |
| PROP-005 | 101e | 1 | `lending-gate.test.mjs:127` |
| PROP-006 | 102a | 1 | `lending-gate.test.mjs:175,187` |
| PROP-007 | 102b | 1 | `lending-gate.test.mjs:199` + NEW property test "PROP-102b (property)" (500 runs: strict-`<` boundary swept across `[0, 2*BORROWER_LOW_USD]`) |
| PROP-008 | 102c | 1 | `lending-gate.test.mjs:208` |
| PROP-009 | 102d | 1 | `lending-gate.test.mjs:215` |
| PROP-011 | 104a | 1 | `lending-gate.test.mjs:255,259` + NEW property test "PROP-104a (property)" (500 runs: exact formula for arbitrary principal `[0,10000]`) |
| PROP-013 | 104c | 1 | `lending-gate.test.mjs:263` |
| PROP-014 | 105a | 1 | `lending-gate.test.mjs:274` |
| PROP-015 | 105b | 1 | `lending-gate.test.mjs:278` + NEW property test "PROP-105b (property)" (41 runs, n=0..40: monotonic, clamped at `maxLoanUsd`, exact doubling formula) |
| PROP-016 | 105c | 1 | `lending-gate.test.mjs:284,295` |
| PROP-017 | 105d | 1 | `lending-gate.test.mjs:304` |
| PROP-018 | 105e | 1 | `lending-gate.test.mjs:309` + NEW property test "PROP-105e (property)" (300 runs: negative/non-integer/NaN/±Infinity → always exactly `firstLoanUsd`, never throws) |
| PROP-021 | 106c | 1 | Reuses `isLockStale`'s own already-proved Tier-1 fixtures (`anicca-agent-economy` REQ-101, `~/anicca/skills/economy/gig/lib/lock.mjs`) — `lock.mjs` is reused **unmodified** by this feature (confirmed: zero edits to that file in this feature's diff), so its own upstream proof still applies; no new proof needed, matching the doc's own stated rationale |
| PROP-023 | 107a | 1 | `lending-gate.test.mjs:244` |
| PROP-028 | 109a | 1 | `lending-gate.test.mjs:377` |
| PROP-029 | 109b | 1 | `lending-gate.test.mjs:387,409` |
| PROP-035 | 101f | 1 | `lending-gate.test.mjs:146,165` |
| PROP-036 | 105f | 1 | `lending-gate.test.mjs:317,329,335` |
| PROP-044 | 105g | 1 | `lending-gate.test.mjs:344,348,352,356` — the doc's own Tool/Method column asks for a fixture wiring into a **mocked** REQ-106 issuance call (not the real one), which the "PROP-105g: mocked-caller wiring" test at line 356 does exactly; this does not depend on the (not-yet-built) real orchestrator |
| PROP-048 | 109f | 1 | `lending-gate.test.mjs:387,402` |
| PROP-052 | 102e | 1 | `lending-gate.test.mjs:221` |
| PROP-053 | 106m | 1 | `lending-gate.test.mjs:442,452` + NEW property test "PROP-106m (property)" (300 runs: deterministic `[outerKey,innerKey]` ordering + idempotence, for arbitrary lender/borrower id strings) — pure function, zero orchestrator dependency |
| PROP-056 | 114a | 1 | `lending-gate.test.mjs:462,475,479` |
| PROP-057 | 114b | 1 | `lending-gate.test.mjs:485,492,499,506` + NEW property test "PROP-114b (property)" (600 runs total: the absolute-loss `>=` boundary holds exactly at `RECENT_DEFAULT_LOSS_THRESHOLD_USD` for arbitrary otherwise-healthy `sampleSize`/`defaultRateUsd` combinations, both above and below the threshold) |
| PROP-061 | 114e | 1 | `lending-gate.test.mjs:533,548` |
| PROP-062 | 114f | 1 | `lending-gate.test.mjs:560` — the doc's own Tool/Method column specifies "the exact fixture described" (a single canonical dilution-defeat scenario, not a swept range); the existing fixture matches it exactly, so no property-test generalization applies here |
| PROP-064 | 114g | 1 | `lending-gate.test.mjs:585` + NEW property test "PROP-114g (property)" (500 runs: `max(0, principal - max(0,repaid))` floor holds for arbitrary `repaid_usd` incl. extreme negatives; negative `repaid_usd` proved indistinguishable from `0` for every generated case) |
| PROP-065 | 101g | 1 | `lending-gate.test.mjs:134` + NEW property test "PROP-101g (property)" (500 runs: per-row floor at 0 for arbitrary `repaid_usd`) |
| PROP-066 | 108f | 1 | `lending-verify.test.mjs` (malformed `log.data` + malformed `receipt.blockNumber`, both against a real local mock RPC HTTP server) — fully self-contained, no orchestrator dependency |
| PROP-026 | 108b | 2 | `lending-verify.test.mjs` (real local `node:http` mock RPC server; valid-transfer, FIND-704 to-topic-suffix rejection, FIND-105 from-topic-suffix rejection, reverted-tx rejection) |
| PROP-031 | 109d | 2 | `lending-gate.test.mjs:233` — pure-fixture wiring of `isBorrowerEligible`/`countSuccessfulOnTimeRepayments`, no real fs/lock/network needed despite the tier-2 label |
| PROP-047 | 108e | 2 | `lending-verify.test.mjs` (same-loan replay + cross-loan replay rejection tests, against real mock-RPC-verified genuine transactions) |
| PROP-059 | 114d | 2 | `lending-gate.test.mjs:518` — the doc's own Tool/Method specifies "a mocked REQ-106 issuance call" (not the real orchestrator) |
| PROP-025 | 108a | 3 | **Live, no-mock E2E** — see below |

#### PROP-025 (Tier 3) — live E2E detail

Team-lead's Step 2(a) resolution: this sprint's own code has no lending-specific disbursement or
repayment (no orchestrator exists to create one — see below), so instead of the sprint's own "loan
repayment," this session queried **already-existing live Base-mainnet infrastructure directly**: the real
public RPC `https://mainnet.base.org`.

1. Read the chain's own current `finalized` block (`eth_getBlockByNumber("finalized")`), then scanned a
   50-block window ending there via `eth_getLogs` for a real USDC `Transfer` event — found tx
   `0x849362757b4ec7e2a6f982384475a2d08156b2d3162741880e4719ed05598a44`, block `0x2e16535`
   (a genuinely finalized, real, historical Base-mainnet USDC transfer; not a lending repayment
   semantically, but a real on-chain `Transfer` event indistinguishable, from `verifyRepayment`'s own
   point of view, from a real repayment).
2. Called the REAL, delivered, production `verifyRepayment` (imported directly from
   `~/anicca/skills/economy/lending/lib/lending-verify.mjs`, zero mocking) against this real tx, with
   `expectedFrom`/`expectedTo` derived from the receipt's own logged addresses.
   Result: `{"credited":0.119999,"rejected":false}` — correctly credited the real on-chain value.
3. **Independently cross-confirmed** the same receipt via a SEPARATE RPC provider
   (`https://base-rpc.publicnode.com`, different infra from `mainnet.base.org`) — `status`/`blockNumber`
   matched exactly, satisfying PROP-108a's own "not trusted from either party's own self-report... a
   SEPARATE RPC call" requirement literally, live.
4. Negative control: same real tx, wrong `expectedTo` → `{"credited":0,"rejected":true}` (proves the
   address-match logic is not a rubber stamp).
5. Replay-rejection control: same real `txHash` pre-recorded in a `loanRows` fixture → `{"credited":0,
   "rejected":true}` (proves FIND-202's replay defense also holds against a genuinely real, valid,
   finalized `txHash`, live).

Full script + raw output: `verification/proof-harnesses/prop-108a-live-mainnet-e2e.mjs` and its
`.output.log`. **Honest scope caveat**: this proves `verifyRepayment`'s own attribution/finalization/
replay-rejection mechanics live, against real chain data — it does NOT (and cannot yet) prove a genuine
lending-specific disbursement→repayment cycle, since no such cycle exists without the orchestrator. This
is the literal "already-existing live infrastructure" resolution the assigning message's Step 2(a)
anticipated for exactly this situation.

### Not provable this sprint — orchestrator does not exist (13)

`contracts/sprint-1.md`'s own "Known residual scope boundary" section (already adversary-PASSed,
`reviews/contracts/sprint-1/`) states verbatim: *"This sprint's four modules do NOT include the effectful
loan-issuance/repayment ORCHESTRATOR... Consequently, the Tier-2/3 proof obligations that depend on that
orchestration actually existing and running — PROP-106a/b/n..., PROP-106g/h/k/l..., PROP-106p...,
PROP-108c/d..., and PROP-112a's runtime co-location check — are NOT satisfied by this sprint and MUST NOT
be scored as delivered against this contract... tracked as a separate, future sprint."*

This session independently confirmed the underlying fact: `~/anicca/skills/economy/lending/` contains
exactly the 4 delivered modules (`lending-path.mjs`, `lending-gate.mjs`, `gojo-read.mjs`,
`lending-verify.mjs`) and their tests — no orchestrator file exists anywhere in this feature's diff
(`git log -- skills/economy/lending/` shows only the 5 Phase 2/hardening commits already on record).

| ID | PROP anchor | Tier (state.json) | Why it cannot be proved this sprint | Contract-listed? |
|---|---|---|---|---|
| PROP-019 | 106a | 2 | Requires two concurrent real disbursement calls via a real issuance call site | Yes |
| PROP-020 | 106b | 2 | Requires a real crashed-holder-reclaim scenario inside a real issuance flow | Yes |
| PROP-027 | 108c | 2 | Requires a real partial→full repayment transition tied to a real loan's ledger state, written by the orchestrator | Yes |
| PROP-040 | 106g | 2 | Requires the reconciliation lookup wired into a real issuance attempt's own append flow (today it is exercised directly, in isolation — see `PROP-038` note below) | Yes |
| PROP-041 | 108d | 2 | Requires a real repayment-verification call racing a real default-detection sweep for the same `loan_id`, both via `withGigLock` | Yes |
| PROP-045 | 106h | 2 | Same root cause as PROP-040 — reconciliation-into-live-issuance wiring | Yes |
| PROP-050 | 106k | 2 | Same root cause as PROP-040 | Yes |
| PROP-051 | 106l | 2 | Same root cause as PROP-040 | Yes |
| PROP-054 | 106n | 2 | Requires two different lenders racing a real issuance attempt against the same borrower | Yes |
| PROP-060 | 106p | 2 | Requires the second, lock-protected kill-switch re-check inside a real issuance critical section | Yes |
| PROP-037 | 106e | 2 | Tier-1 half (namespacing) already PROVED (see above); the Tier-2 half explicitly needs "two concurrent... real disbursement calls" — same missing orchestrator | **No — contract-listing gap** |
| PROP-055 | 106o | 2 | Needs the real follow-up-append code to set `issued_ms` from its own append time — that append code is the orchestrator | **No — contract-listing gap** |
| PROP-038 | 106f | 1 (state.json label) | The doc's own description is about the orchestrator's two-phase append+lock-release behavior on a `payViaFacilitator` failure; only `reconcileProvisionalDisbursement`'s own narrower "not found" signal is tested today (`lending-verify.test.mjs`, "PROP-106f/PROP-106g" test) — the full claim needs the orchestrator despite this ID's `tier:1` label in `state.json` | **No — contract-listing gap, and a tier-label discrepancy vs. the doc's own Tier-2 prose** |

**Contract-listing gap, reported for the orchestrator's attention**: `contracts/sprint-1.md`'s own
"Known residual scope boundary" section explicitly names 10 of these 13 IDs. This session's own read of
the delivered code confirms the remaining 3 (PROP-037's Tier-2 half, PROP-055, PROP-038) share the
identical root cause (no orchestrator exists) but were not named in that list. This is flagged as a
**completeness gap in the contract's own prose**, not a new scope decision by this session — the
underlying fact (no orchestrator exists) is unambiguous and independently verified either way.

## Test evidence

```
cd ~/anicca && node --test skills/economy/lending/lib/__tests__/*.test.mjs
# tests 89, pass 89, fail 0, cancelled 0, skipped 0, todo 0
```
Full log: `verification/fuzz-results/full-suite-89-run.log`.

New file this session: `skills/economy/lending/lib/__tests__/lending-gate.property.test.mjs` (10
`fast-check` property tests, ~4,500 total generated-input runs across all 10 properties). `fast-check`
added as a devDependency: `~/anicca/package.json` → `"devDependencies": {"fast-check": "^4.8.0"}`.
