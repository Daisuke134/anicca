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

## Sprint-2 Addendum (Phase 5, `lending-orchestrator.mjs` — closing sprint-1's 19 deferred obligations)

**date**: 2026-07-08 · **verifier**: fresh-context Phase 5 session (sprint-2)

### Summary

| Metric | Count |
|---|---|
| Obligations targeted this sprint (`contracts/sprint-2.md`'s own "Deferred-obligation disposition") | 19 |
| **Promoted to `required:true`/`status:"proved"` this session** | **19 / 19** |
| Intentionally left `status:"skipped"`/`required:false` (PROP-108a, Tier-3, genuinely requires a real on-chain spend, mirrors `anicca-agent-spawn` sprint-2's own CRIT-206 treatment) | 1 |
| Pre-existing target-feature test suite | **120/120 passing** (89 sprint-1 + 30 sprint-2, unchanged, re-run this session) |
| New proof harness added | `verification/proof-harnesses/sprint2-orchestrator-residual-props.mjs` (13 scenarios, 3 consecutive runs, 0 flakiness) |
| Security static analysis | Semgrep, 2 configs, 261 rules, 0 findings on `lending-orchestrator.mjs` — see `security-report.md`'s Sprint-2 Addendum |
| Purity boundary audit | Confirmed intact, zero drift — see `purity-audit.md`'s Sprint-2 Addendum |

Of the 19 targeted obligations, 7 were found to already be genuinely, directly proved by
`lending-orchestrator.test.mjs`'s own pre-existing 30 tests (no new evidence needed beyond reading the
already-GREEN test file and, for the 5 Tier-0 structural ones, this session's own direct source read).
The remaining 12 had a genuine, real evidentiary gap — the existing test suite covered an adjacent but
not identical scenario (e.g. only the "found:true" half of a reconciliation branch, or a naive-Promise.all
race that does not reliably exercise the specific sequential-handoff path the obligation's own text
requires) — and are closed by 13 new scenarios in the new proof harness, each driving the REAL,
unmodified orchestrator functions via their own already-designed `deps` injection seam, never a
re-implementation or mock of the orchestrator itself.

### Proof Obligations

| state.json ID | PROP anchor | Tier | Disposition | Evidence |
|---|---|---|---|---|
| PROP-019 | PROP-106a | 2 | **Proved** | `lending-orchestrator.test.mjs`: "PROP-115c step 4 (lock_held...)" (real lock exclusivity, zero rows) + "PROP-115d" (staggered concurrent real issuance, exactly one active, others `lock_held` while in flight, succeeds only after release) |
| PROP-020 | PROP-106b | 1/2 | **Proved** | New harness: "a real backdated (stale) `loan_${lenderId}.lock` file is reclaimed..." (+ a FRESH, non-stale control lock correctly rejected) and "two concurrent callers racing to reclaim the SAME stale lock -- exactly one reclaims and succeeds" |
| PROP-027 | PROP-108c | 2 | **Proved** | `lending-orchestrator.test.mjs`: partial-credit test (line 539) + full-credit test (line 552), chained values; PLUS new harness scenario driving the SAME loan through two REAL sequential `executeRepaymentClaim` calls, asserting status sequence `active → active → repaid` |
| PROP-037 | PROP-106e | 1/2 | **Proved** (Tier-2 half; Tier-1 half already proved sprint-1) | New harness: "two different lenders concurrently disbursing to two different borrowers succeed with distinct, non-colliding loan_ids" (`loan_LenderA_1`/`loan_LenderB_1`) |
| PROP-038 | PROP-106f | 2 | **Proved** | `lending-orchestrator.test.mjs`: "PROP-115c step 9 sub-case 1" (disbursement_failed follow-up) + new harness scenario: the SAME lender's very next attempt computes n+1 and succeeds immediately (lock genuinely reacquirable, no wedge) |
| PROP-039 | PROP-112a | 0 | **Proved** | Structural source read (this session): zero `homeDir` references anywhere in `lending-orchestrator.mjs` (`grep -n homeDir` → 0 hits), zero remote/networked path construction (all `fs.*` calls resolve from `deps.ledgerFile \|\| LOANS_LEDGER_PATH`), co-location decided exclusively via `citizen.coLocatedWithCoordinator !== true` (lines 281/284); PLUS `lending-orchestrator.test.mjs`'s own happy-path test (two distinct citizens, both `coLocatedWithCoordinator: true`, succeeds) and "PROP-115c step 2" (non-co-located refusal) |
| PROP-040 | PROP-106g | 2 | **Proved** | `lending-orchestrator.test.mjs`: "PROP-115c step 5 happy" (found:true half — no double-disbursement) + new harness scenario: found:false half — stale row closed out as `disbursement_failed`, never re-disbursed, attempt still proceeds at n+1 (disburse invoked exactly once, only for the genuine new n=2) |
| PROP-041 | PROP-108d | 2 | **Proved** | `lending-orchestrator.test.mjs`: "PROP-116c" (repayment claim vs default-detection sweep race on the SAME `loan_id`, real `withGigLock`, exactly one wins) |
| PROP-042 | PROP-109e | 0 | **Proved** | Structural source read (this session): both `appendLoanRow` call sites for a REQ-108/109 status-transition row (`executeRepaymentClaim` line ~347, `executeDefaultDetectionSweep` line ~391) are lexically INSIDE their own `withGigLock(lockStatePath, \`loan_${loanId}\`, ...)` callback — confirmed by direct read, no call site appends outside this lock |
| PROP-045 | PROP-106h | 2 | **Proved** | `lending-orchestrator.test.mjs`: "PROP-115c step 9 sub-case 2" (uncertain follow-up on in-process exception) + new harness scenario: a stale row seeded as `disbursement_uncertain` (not `provisioning`) is reconciled by the next attempt via the IDENTICAL mechanism, proving the unification (FIND-201) is genuine |
| PROP-046 | PROP-106i | 0 | **Proved** | `lending-orchestrator.test.mjs`: "CRIT-204 structural" (issuance function body never references `` `loan_${loanId}` ``; servicing functions never reference the issuance lock keys) — direct match to this obligation's own requirement |
| PROP-049 | PROP-105h | 0 | **Proved** | Structural source read (this session): `evaluateColdStartKillSwitch` imported (line 21); called at step 3 pre-lock (via `evaluateKillSwitches`, line 290, before lock acquisition at line 297-302) AND again at step 6 inside the lock (line 205, after both locks held, against the fresh read) — both call sites confirmed by direct read; PLUS "PROP-115c step 3 (REQ-105 cold-start...)" test proving the pre-lock call site functions on real inputs |
| PROP-050 | PROP-106k | 2 | **Proved** | New harness scenario: a genuine double-fault (settle-side exception caught, but the catch block's OWN `disbursement_uncertain` follow-up append also throws) leaves the ledger exactly as found (only the original `provisioning` row, zero mutation), releases the lock normally, and the next attempt for the SAME lender still invokes reconciliation for this SAME unterminated row before computing a new sequence number |
| PROP-051 | PROP-106l | 2 | **Proved** | `lending-orchestrator.test.mjs`: "PROP-115c step 5 (reconciliation lookup itself throws)" (clean failure, zero mutation) + new harness scenario: a later attempt with a working lookup resolves the SAME row exactly once, and a THIRD attempt never re-invokes reconcile once the row is terminal |
| PROP-054 | PROP-106n | 2 | **Proved** | New harness scenario (staggered, mirrors `lending-orchestrator.test.mjs`'s own PROP-115d technique since a naive `Promise.all` is timing-dependent and does not reliably exercise the sequential-handoff path): LenderD is locked out (`lock_held`) while LenderC's own critical section is mid-flight, then — after LenderC completes and releases — LenderD's OWN fresh recheck correctly observes the shared borrower now has an outstanding loan and refuses with `outstanding_loan`; zero rows for the refused attempt, the borrower never carries two simultaneous active/provisioning loans (deduplicated last-write-wins by `loan_id`) |
| PROP-055 | PROP-106o | 1/2 | **Proved** | New harness scenario: a stale row's own `provisioned_ms` (T1, backdated 3 days) is distinguished from the reclaiming call's own LATER `nowMs` (T2) — the reconciled follow-up row's `issued_ms === T2` (never T1) and `due_ms === T2 + 14 days` |
| PROP-058 | PROP-114c | 0 | **Proved** | Structural source read (this session): `evaluateKillSwitches` (lines 133-158) computes `computeRecentDefaultLossUsd` and calls `evaluateOverallDefaultKillSwitch` at BOTH step 3 (pre-lock, line 290) and step 6 (lock-protected fresh-check, line 205), always passing the freshly-computed `totalRecentDefaultLossUsd`; PLUS "PROP-115c step 3 (REQ-114 overall default...)" test proving the pre-lock call site functions on real inputs |
| PROP-060 | PROP-106p | 2 | **Proved** | New harness scenarios (both variants): the ledger is deterministically poisoned (10 cold-start defaults / one $5.00 recent default) via the `reconcile` deps-seam hook, which fires between step 3's pre-lock read and step 6's lock-protected fresh read — proving the SECOND, lock-protected re-check genuinely catches a kill-switch trip the pre-lock check could not have seen, reproduced separately for `evaluateColdStartKillSwitch` and `evaluateOverallDefaultKillSwitch` |
| PROP-063 | PROP-109g | 0 | **Proved** | Structural source read (this session): exactly one `defaulted_ms` occurrence in the file (line 391, `executeDefaultDetectionSweep`'s own append payload), set from the function's own `nowMs` parameter (defaults to `Date.now()` at the true entry point); no other append call site includes this field; PLUS `lending-orchestrator.test.mjs`'s own "defaulted_ms genuinely set at append time" test |

**PROP-025 (PROP-108a, Tier 3) — intentionally NOT promoted.** Confirmed this session:
`state.json`'s PROP-025 entry remains `status:"skipped"`/`required:false` (verified programmatically
before and after this session's own `state.json` write). Per `contracts/sprint-2.md`'s own
"Deferred-obligation disposition" section, this obligation genuinely requires a real, live on-chain
disbursement-then-repayment pair through the real orchestrator — this sprint's own CRIT-206 explicitly
permits an honest re-deferral rather than a fabricated/borrowed-artifact proof, mirroring
`anicca-agent-spawn` sprint-2's own identical treatment of its 3 Tier-3 obligations. This session did
**not** attempt a real-money spend and did **not** promote this obligation.

### Test evidence (sprint-2)

```
cd ~/anicca && node --test skills/economy/lending/lib/__tests__/*.test.mjs
# tests 120, pass 120, fail 0, cancelled 0, skipped 0, todo 0

node verification/proof-harnesses/sprint2-orchestrator-residual-props.mjs   (run 3x consecutively)
# {"total": 13, "passed": 13, "failed": 0, "failedNames": []}   -- identical result all 3 runs
```

## Sprint-3 Addendum (Phase 5, `run.sh` + `scripts/wake-gate.mjs` + `registry.json` `economy/lending` slot — REQ-117, the autonomous daemon-wake entry point)

**date**: 2026-07-08 · **verifier**: fresh-context Phase 5 session (sprint-3)

### Summary

| Metric | Count |
|---|---|
| Obligations targeted this sprint (`state.json`'s own sprint-3 additions) | 4 (PROP-067/068/069/070 = PROP-117a/b/c/d) |
| **Promoted to `status:"proved"` this session** | **4 / 4** |
| Pre-existing target-feature test suite | **131/131 passing** (120 sprint-1/sprint-2 + 11 sprint-3, unchanged, re-run this session) |
| New proof harness added | 0 — the existing 11 sprint-3 tests (`wake-gate.test.mjs`/`wake-gate-structural.test.mjs`, already Phase-2b-GREEN and Phase-3-adversary-PASSed) already constitute genuine Tier-0/Tier-2 proof directly against each obligation's own `passThreshold` text (Gate item 13, `specs/verification-architecture.md` lines 542-566) — no evidentiary gap found |
| Security static analysis | Semgrep, 2 configs, 264 rules, 0 findings on `run.sh`/`scripts/wake-gate.mjs`; shellcheck 0 warnings/errors — see `security-report.md`'s Sprint-3 Addendum |
| Purity boundary audit | Confirmed intact (Effectful Shell classification accurate, zero re-implemented judgment logic), zero drift — see `purity-audit.md`'s Sprint-3 Addendum |

Unlike sprint-2 (19 obligations, 12 requiring a new proof harness), this sprint's own 4 obligations were
each independently checked against their own literal Gate-item-13 wording and found already, genuinely
covered by the Phase 2b test suite — this session's job was to independently re-run that suite fresh
(never accept a prior log) and to cross-read `behavioral-spec.md`'s own REQ-117 prose for the
documentation-only halves of PROP-117a/PROP-117c that no test can assert (an EARS/Edge-Cases wording
claim, not a runtime behavior).

### Proof Obligations

| state.json ID | PROP anchor | Tier | Disposition | Evidence |
|---|---|---|---|---|
| PROP-067 | PROP-117a | 0 | **Proved** | `wake-gate-structural.test.mjs`'s own "PROP-117a structural" test: a repo-wide walk (`~/anicca`, excluding `node_modules`/`.git`/`__tests__`/`__pycache__`) over every `.mjs`/`.js` file confirms `executeLoanIssuanceAttempt`/`executeDefaultDetectionSweep` each have EXACTLY one production import+call site (`skills/economy/lending/scripts/wake-gate.mjs`), and `executeRepaymentClaim` has ZERO — independently re-run this session (PASS, 788ms). Cross-confirmed by Phase 3's own independent fresh-context adversary review (`reviews/impl/sprint-3/output/verdict.json`, `structural_integrity` dimension, PASS, zero findings, its own separately-performed repo-wide grep). The documentation half — REQ-117's own text stating the `executeRepaymentClaim` exclusion is "AN EXPLICIT, DELIBERATE, DOCUMENTED LIMITATION" never a silent omission — read directly this session at `behavioral-spec.md` step 8 (line 2663) and confirmed present in the REQ's own prose, not merely asserted by a test. |
| PROP-068 | PROP-117b | 0 | **Proved** | `wake-gate-structural.test.mjs`'s own "PROP-117b" test: imports the REAL `liveSlotNames` (`runtime/loop/prompt.mjs`) and `earnSkillRelPath` (`runtime/loop/earn-slot.mjs`) — never re-implemented stand-ins — asserts `registry.json`'s `slots["economy/lending"]` entry has `status:"live"`/`dir:"skills/economy/lending"`, asserts `liveSlotNames(registry).includes("economy/lending")`, and replicates `runtime/loop/index.mjs:498`'s own real `path.join(ANICCA_HOME, "skills", ...rel.split("/"))` join expression to resolve to the real `run.sh` file. This session independently re-read `index.mjs:481-499` (`runSkillWithKillRef`, module-private/non-exported, so it cannot be imported directly — mirrors the sibling `self/spawn` precedent) and confirmed the test's own join logic is byte-for-byte identical to the real production expression, never a divergent reimplementation. Independently re-run this session (PASS). Cross-confirmed by Phase 3's own independent 3-file chain trace (`earn-slot.mjs:30-33`, `prompt.mjs:32-36`, `index.mjs:124,494,498`) in `structural_integrity`, PASS. |
| PROP-069 | PROP-117c | 2 | **Proved** | `wake-gate.test.mjs`'s three dedicated fixtures: fixture 1 (two Solana-only citizens — the `wallet.evm===true` exclusion, isolated from scarcity) and fixture 2 (exactly one fully-qualifying EVM citizen — the `lenderId!==borrowerId` impossibility, isolated from the wallet-exclusion path) each independently produce `selectedPair===null`/`issuance===null`/`sweep` deep-equal `{defaulted:[]}` (still runs exactly once)/zero ledger rows — a clean, honest no-op for BOTH of today's independently-sufficient reasons, each its own fixture, never conflated. Fixture 3 drives a real two-citizen wake against the REAL, unmodified `executeLoanIssuanceAttempt` (only `disburse` stubbed, mirroring sprint-2's own already-approved `happyDeps()` convention) to a genuine `{status:"active"}` outcome — not merely "reached", the literal FIND-1004/1006 silent-refusal regression this fixture exists to catch. All 3 independently re-run this session (PASS). The Edge-Cases documentation half (REQ-117's own text stating BOTH reasons "SHALL NOT" be conflated into one vague explanation) read directly this session at `behavioral-spec.md` lines 2728-2746 and confirmed to state both reasons separately, by name. |
| PROP-070 | PROP-117d | 0 | **Proved** | `wake-gate-structural.test.mjs`'s own "PROP-117d structural" test: confirms no `balanceUsd`/`surplusUsd`/`defaultRateUsd`/`repaymentRate` relational (`<`/`>`/`=`) comparison exists anywhere in `scripts/wake-gate.mjs`'s own source (all such comparisons live exclusively inside the already-exported `lending-gate.mjs` functions it calls), and confirms zero `ANICCA_ARGS` reads anywhere. Companion test confirms `scripts/wake-gate.mjs` imports nothing from `self/spawn/scripts/wake-gate.mjs` itself. Both independently re-run this session (PASS). The "no modification whatsoever to `anicca-agent-spawn`'s own files" structural diff-scope clause independently confirmed this session via `git show ccef6ee480add1f7e3d670fab53a12fbfb07339e --stat`: the sole sprint-3 commit touches exactly 5 files (`run.sh`, `scripts/wake-gate.mjs`, 2 new test files, `skills/registry.json`), zero files under `skills/self/spawn/` — and via `git log --oneline -- skills/self/spawn/` (this session), confirming no sprint-3 commit appears in that path's own history at all. |

### Test evidence (sprint-3)

```
cd ~/anicca && node --test skills/economy/lending/lib/__tests__/wake-gate.test.mjs skills/economy/lending/lib/__tests__/wake-gate-structural.test.mjs
# tests 11, pass 11, fail 0, cancelled 0, skipped 0, todo 0

cd ~/anicca && node --test skills/economy/lending/lib/__tests__/*.test.mjs
# tests 131, pass 131, fail 0, cancelled 0, skipped 0, todo 0
```
