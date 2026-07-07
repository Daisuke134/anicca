# Verification Architecture — anicca-agent-lending (Phase 1b)

**feature**: anicca-agent-lending · **mode**: strict · **increment**: same as `behavioral-spec.md`
(in-colony agent-to-agent lending, Base-mainnet USDC only, v1 fixed-terms + reputation ladder) ·
**日付**: 2026-07-07 · **revision**: iteration 2, revised (spec review iteration-1 findings FIND-001..008
resolved — see `reviews/spec/iteration-1/RESOLUTION-NOTES.md`)

## Purity Boundary Map (file/function level)

| Layer | Location | Purity | Notes |
|---|---|---|---|
| **Pure Core (existing, reused unmodified)** | `~/anicca/skills/_shared/lib/is-self-funded.mjs::isSelfFunded`/`selfFundedReasons` | PURE | Already implemented, already unit-tested. Gates BOTH lender (REQ-101) and borrower (REQ-102) eligibility; zero modification, zero new judgment logic. |
| **Pure Core (new)** | new module `~/anicca/skills/economy/lending/lib/lending-gate.mjs::computeLenderAvailableUsd({lenderBalanceUsd, perCitizenReserveUsd, outstandingPrincipalUsd, recentGojoGiftsUsd=0}) → number` | PURE (new) | `max(0, balance - reserve - outstanding - recentGojoGiftsUsd)`; zero I/O once given already-fetched/already-summed inputs. `recentGojoGiftsUsd` resolves FIND-005 (see `sumRecentGojoGiftsUsd` below). REQ-101's acceptance criteria. |
| **Pure Core (new)** | same file, `sumOutstandingPrincipalUsd(loanRows, lenderId) → number` | PURE (new) | Reduces `loanRows` to one effective row per `loan_id` (last-appended, last-write-wins — same convention `anicca-agent-spawn` REQ-101 established for `ledger.js`), sums `principal_usd - repaid_usd` over rows where `lender_id===lenderId` and `status` is `"active"` or `"defaulted"`. REQ-101. |
| **Pure Core (new)** | same file, `sumRecentGojoGiftsUsd(gojoLogRows, nowMs, lookbackHours=24) → number` | PURE (new) | Sums already-read `~/anicca/skills/economy/ubi/state/gojo-log.jsonl` rows' `decision.amount_usd` within a lookback window (reuses `ubi.js`'s own `DEFAULT_GOJO_CONFIG.rateLimitHours=24`), zero I/O. Resolves FIND-005 (one-way, read-only gojo-commitment awareness). REQ-101. |
| **Pure Core (new)** | same file, `isBorrowerEligible({borrowerAgent, loanRows, borrowerId, borrowerBalanceUsd}) → {eligible, reason}` | PURE (new) | Three-condition boolean gate (self-funded, below `BORROWER_LOW_USD`, zero open obligation). REQ-102. |
| **Pure Core (new)** | same file, `computeLoanCapUsd({successfulOnTimeRepayments, firstLoanUsd, maxLoanUsd}) → number` | PURE (new) | `min(maxLoanUsd, firstLoanUsd * 2^n)` — the cold-start-resolving reputation ladder. REQ-105. |
| **Pure Core (new)** | same file, `countSuccessfulOnTimeRepayments(loanRows, borrowerId) → number` | PURE (new) | Counts last-row-per-`loan_id` entries where `status==="repaid" && on_time===true` for the given `borrowerId`. REQ-105. |
| **Pure Core (new)** | same file, `decideLoan({lenderAvailableUsd, loanAmountUsd}) → {eligible, reason}` | PURE (new) | `eligible: lenderAvailableUsd >= loanAmountUsd`; `loanAmountUsd` is always `computeLoanCapUsd`'s own output. REQ-105. |
| **Pure Core (new)** | same file, `detectDefaultedLoans({loanRows, nowMs}) → loanId[]` | PURE (new) | Elapsed-time comparison over already-read rows (`now >= due_ms && repaid_usd < total_due_usd`), zero I/O. REQ-109. |
| **Pure Core (new)** | same file, `excludeDefaultedBorrowers({citizens, loanRows}) → citizens[]` | PURE (new) | A SECOND, lending-owned filter, composed AFTER `anicca-agent-spawn`'s own `filterProductiveCitizens` output — never a modification of that function. REQ-109. |
| **Pure Core (new)** | same file, `nextLoanSequenceForLender(loanRows, lenderId) → number` | PURE (new) | `max(matching `loan_${lenderId}_` prefix's numeric suffix over already-read rows) + 1` (or `1` if none) — mirrors `child-spec.js::nextChildId`'s own algorithm, but namespaced per-lender. Computed strictly INSIDE REQ-106's existing per-lender lock by the EFFECTFUL caller. Resolves FIND-001. REQ-106. |
| **Pure Core (new)** | same file, `computeColdStartRepaymentRate({loanRows, n=20}) → {sampleSize, repaidCount, defaultedCount, pendingCount, rate}` | PURE (new) | Outcome-rate arithmetic over the first `n` colony-wide cold-start-originated loans (by `issued_ms` ascending), zero I/O, zero judgment — the monitoring-plan companion to REQ-105's sizing ladder, resolving FIND-004's "experimental hypothesis, not proven solution" honesty requirement. REQ-105. |
| **Pure Core (new)** | new module `~/anicca/skills/economy/lending/lib/lending-path.mjs::LOANS_LEDGER_PATH` | PURE (new, a constant) | The single, canonical absolute path to `loans.jsonl` — both REQ-106's lock `statePath` and every REQ-101/108/109 read/write converge on this ONE exported value, mirroring `anicca-agent-spawn`'s `CITIZENS_REGISTRY_PATH` discipline exactly. |
| **Not code — design constraint** | REQ-103 (bookkeeping-only design constraint on REQ-101/102/104/105/109) | N/A | Directly analogous to `anicca-agent-economy` REQ-203 / `anicca-agent-spawn` REQ-104; verified by Phase 3 structural code read (grep for LLM calls/prompt strings/scoring fields), never a runtime assertion. |
| **Not code — design constraint** | REQ-107 (Base-mainnet-USDC-only scope constraint, this increment) | N/A | Mirrors `anicca-agent-spawn` REQ-106's honest single-scope precedent; verified by a Phase 3 structural code read confirming no Solana transaction/signing-library code path exists in this feature's diff. |
| **Not code — design constraint** | REQ-112 (single-coordinator-host scope constraint, this increment) | N/A | Resolves FIND-002 — the DIRECT, by-name analog of `anicca-agent-spawn` REQ-106's own single-coordinator-host precondition, applied here to BOTH lending participants (lender AND borrower), not merely one evaluator; verified by a Phase 3 structural code read confirming no code path constructs a remote/networked lock or ledger path. |
| **Effectful Shell (existing, reused unmodified)** | `~/anicca/skills/self/spawn/lib/ledger.js::readChildren`/`appendChild` | EFFECTFUL (existing) | Generic, file-path-parameterized append-only-JSONL primitives, unmodified, pointed at a NEW dedicated file, `~/anicca/skills/economy/lending/state/loans.jsonl` — never the file spawn's own child rows live in. |
| **Effectful Shell (new, read-only)** | new module `~/anicca/skills/economy/lending/lib/gojo-read.mjs::readGojoLogRows(gojoLogPath) → row[]` | EFFECTFUL (new) | Plain `fs.readFileSync` + line-split + `JSON.parse` over `~/anicca/skills/economy/ubi/state/gojo-log.jsonl` — NEVER writes; never uses `ledger.js` (that file is `ubi`'s own, not this feature's ledger). Feeds `sumRecentGojoGiftsUsd`. Resolves FIND-005. REQ-101. |
| **Effectful Shell (existing, reused unmodified)** | `~/anicca/skills/economy/gig/lib/lock.mjs::withGigLock`/`isLockStale` | EFFECTFUL (existing, adversary-hardened) | New lock key `` `loan_${lenderId}` ``, `statePath = LOANS_LEDGER_PATH`. REQ-106. Same module `anicca-agent-spawn` REQ-103 already reuses for colony-spawn — a new key on an existing mechanism, not new lock code. |
| **Effectful Shell (existing, reused unmodified)** | `~/anicca/skills/economy/gig/lib/escrow.mjs::payViaFacilitator({privateKey, to, amountBase})` | EFFECTFUL (existing, live-proven) | Sole disbursement/repayment transfer primitive this feature uses, in either direction (lender→borrower at issuance, borrower→lender at repayment) — a generic single-signer gasless USDC transfer, not a new transfer mechanism. REQ-104/107/108. |
| **Effectful Shell (new, reuses an already-hardened pattern)** | new module `~/anicca/skills/economy/lending/lib/lending-verify.mjs::verifyRepayment({txHash, expectedFrom, expectedTo, rpcUrl})` | EFFECTFUL (new) | Corrects a prior false claim (FIND-007) that this reused `escrow.mjs`'s own `viem`/`createPublicClient` import for `Transfer`-log parsing — `escrow.mjs::settleBody` contains NO log-parsing code at all (only `waitForTransactionReceipt`+`status` check). The REAL, already-hardened precedent this module reuses is `~/anicca/skills/self/founder-loop/record-earn.mjs`'s `blockNow()`/`parseRawLogs` (lines 65-72, 82-88): finalized-block-only scanning discipline, `TRANSFER_TOPIC` match, and EXACT zero-padded-address equality for the `to`/`from` topics (never a suffix match — `record-earn.mjs`'s own inline comment documents the previously-fixed real bug this deliberately avoids re-introducing: `FIND-704`), plus never trusting the RPC's own server-side filter for a money invariant (`record-earn.mjs`'s own `FIND-603` discipline). Mirrors `anicca-agent-spawn` REQ-401's general "independent re-verification, never self-report" principle while reusing `record-earn.mjs`'s specific, already-bug-fixed log-decoding mechanics. REQ-108. |
| **Effectful Shell (existing, out of scope, read-only dependency)** | `anicca-agent-spawn`'s `~/anicca/skills/self/spawn/registry/citizens.json` + `computeColonySurplusUsd`/`filterProductiveCitizens` | EFFECTFUL (existing, another feature, not modified) | This feature reads citizen records conceptually consistent with that registry's CURRENT shape (re-verified this revision, includes `homeDir` — resolves FIND-006's stale-citation finding) and composes `excludeDefaultedBorrowers` AFTER that feature's own filter output — it does NOT modify that feature's source. REQ-112 also reads each citizen's `homeDir` to confirm co-location. Flagged as a live coupling risk (see behavioral-spec.md Dependencies section) since that registry does not yet exist on disk and that spec is still mid-pipeline. |

## Verification tiers (this feature's convention, consistent with `anicca-agent-spawn`'s and
`anicca-agent-economy`'s own `verification-architecture.md` files)

- **Tier 0**: structural/existence checks — no runtime execution of the audited code required (REQ-103's
  no-LLM/no-scoring check; REQ-104's no-arbitrary-principal structural check; REQ-106's canonical
  `LOANS_LEDGER_PATH` import-identity check; REQ-107's no-Solana-code-path check; REQ-109's append-only/
  never-mutate check; REQ-110's zero-coupling-with-`decide.mjs` check; REQ-111's no-human-funded-wallet-
  reference grep and `isSelfFunded()`-byte-identical check; REQ-112's no-remote/networked-path structural
  check).
- **Tier 1**: pure-function unit tests — deterministic fixtures, no filesystem/network/real wall-clock
  sleep, fast (milliseconds). REQ-101's `computeLenderAvailableUsd`/`sumOutstandingPrincipalUsd`/
  `sumRecentGojoGiftsUsd`, REQ-102's `isBorrowerEligible`, REQ-104's `total_due_usd` arithmetic, REQ-105's
  `computeLoanCapUsd`/`countSuccessfulOnTimeRepayments`/`decideLoan`/`computeColdStartRepaymentRate`,
  REQ-106's `nextLoanSequenceForLender` and reused `isLockStale` wiring (the predicate itself is already
  Tier-1-proved upstream; this feature's own obligation is only proving the NEW `loan_<lenderId>` key is
  wired correctly), REQ-109's `detectDefaultedLoans`/`excludeDefaultedBorrowers`.
- **Tier 2**: integration tests — real module wiring (real `fs`, small injected timing constants,
  concurrent `Promise.all` calls against the real lock module) plus fresh-context adversary review of
  the disk artifacts (no live chain spend required for this tier). REQ-106's concurrent-issuance race,
  crashed-holder reclaim, cross-lender `loan_id`-collision-freedom test, and injected-facilitator-failure
  fail-closed test, REQ-108's partial-then-full repayment transition (against a real, injected
  transaction-receipt fixture), REQ-109's retroactive-correction test.
- **Tier 3**: live, no-mock E2E — real on-chain transfers and independent RPC re-verification, executed
  the same way the P2 gig-board witness and SPEC.md §9.9's own witness already did (real tx hashes,
  independent re-verification), per this project's HARD RULE 0.24 (on-chain-verified only, no paper/
  simulated claims). REQ-108's real repayment-verification E2E (a real disbursement + a real repayment
  transaction, independently re-confirmed via a SEPARATE RPC call). **A first Tier-3 pass on Base
  Sepolia is an acceptable precursor, but this increment's own completion requires at least one real
  Base-mainnet-class result — mirroring SPEC.md §9.9's own correction that only a mainnet-class
  settlement counts as the actual witness**, and directly reusing the SAME `payViaFacilitator`/
  `escrow.mjs` chain-selection discipline (`GIG_CHAIN=base`) that already fixed the domain-name bug
  SPEC.md §9.9 documents.

## Proof Obligations

| ID | REQ | Description | Tier | Required | Tool / Method |
|---|---|---|---|---|---|
| PROP-101a | REQ-101 | `computeLenderAvailableUsd` computes `max(0, balance - reserve - outstanding)` correctly over a mixed fixture | 1 | true | unit test, fixed fixture, assert exact numeric output (e.g. `balance=8, reserve=5, outstanding=1 → 2`) |
| PROP-101b | REQ-101 | A citizen failing `isSelfFunded()` contributes `0` available surplus regardless of raw balance magnitude | 1 | true | unit test: fixture with `balance=1000`, `isSelfFunded()→false` → assert lender excluded |
| PROP-101c | REQ-101 | Missing/non-finite/negative `lenderBalanceUsd` yields `0` available surplus (fail-closed), never throws | 1 | true | unit test: `NaN`/`undefined`/negative fixtures → finite `0` result, no throw |
| PROP-101d | REQ-101 | `sumOutstandingPrincipalUsd` reduces `loanRows` to one effective row per `loan_id` (last-appended wins) before summing, and includes `"defaulted"` rows' unrecovered principal permanently in the sum | 1 | true | unit test: a `loan_id` with a `"provisioning"`-then-`"active"`-then-`"defaulted"` row sequence for the SAME id → assert only the last row's status/amount is used, and a `"defaulted"` row's principal is included in the sum (never silently written off) |
| PROP-101e | REQ-101 | A lender's `isSelfFunded()` status changing to `false` after a loan was already disbursed does not retroactively cancel that loan (REQ-101's gate applies only at issuance time) | 1 | true | unit test: a fixture where the lender's current `isSelfFunded()` result is `false` but an already-`"active"` `loans.jsonl` row for it exists → assert the existing row is untouched (no code path deletes/mutates it) |
| PROP-101f | REQ-101 | `sumRecentGojoGiftsUsd` correctly sums `gojo-log.jsonl` rows' `decision.amount_usd` within the lookback window (regardless of `executed`) and excludes rows outside it, feeding `computeLenderAvailableUsd`'s new `recentGojoGiftsUsd` term (resolves FIND-005) | 1 | true | unit test, fixed fixture: one in-window gift row (`amount_usd>0`), one out-of-window row, one `amount_usd:0` row → assert only the in-window `amount_usd>0` row is summed; plus `computeLenderAvailableUsd({balance:8, reserve:5, outstanding:0, recentGojoGiftsUsd:1}) === 2` |
| PROP-102a | REQ-102 | `isBorrowerEligible` returns `eligible:true` only when ALL THREE conditions hold (self-funded, below `BORROWER_LOW_USD`, zero open obligation) | 1 | true | unit test, exhaustive branch coverage of the three conditions (each independently failing) |
| PROP-102b | REQ-102 | Balance exactly `$0.50` (the boundary) is NOT eligible — strict `<`, matching `decide.mjs`'s own convention for the same constant | 1 | true | unit test at the exact boundary value and at `boundary - 0.01` |
| PROP-102c | REQ-102 | A citizen with an `"active"` (not overdue) loan in good standing is NOT eligible for a second loan, regardless of how low its balance is | 1 | true | unit test: fixture with balance `$0.01` and one `"active"` row for its own `borrower_id` → `eligible:false, reason:"outstanding_loan"` |
| PROP-102d | REQ-102 | A brand-new citizen with ZERO rows in `loans.jsonl` passes condition (c) vacuously (the cold-start entry point) | 1 | true | unit test: fixture with no matching rows at all → condition (c) passes |
| PROP-103a | REQ-103 | `computeLenderAvailableUsd`/`isBorrowerEligible`/`computeLoanCapUsd`/`detectDefaultedLoans`/`excludeDefaultedBorrowers`'s source contains no network call, no prompt/LLM-client reference, and no scoring/ranking/free-text-recommendation field on any return value | 0 | true | Phase 3 structural grep/read of the diff; fails if any such reference is found, exactly as `anicca-agent-economy` PROP-203a/b and `anicca-agent-spawn` PROP-104a already established |
| PROP-104a | REQ-104 | `total_due_usd = principal_usd * (1 + LOAN_INTEREST_RATE)` computes exactly `0.022` for `FIRST_LOAN_USD=0.02` | 1 | true | unit test, fixed fixture, exact numeric assertion |
| PROP-104b | REQ-104 | No code path in this feature accepts a borrower- or lender-supplied principal/rate/window value that overrides the fixed constants (except `computeLoanCapUsd`'s own deterministic output) | 0 | true | structural/Tier-0 grep across the issuance code for any externally-supplied principal/rate/window parameter — must find none besides the ladder's own computed value |
| PROP-104c | REQ-104 | A late (post-window) repayment's `total_due_usd` is identical to the value computed at issuance — no additional interest accrues | 1 | true | unit test: a loan repaid past `due_ms` → assert `total_due_usd` unchanged from its issuance-time value |
| PROP-105a | REQ-105 | `computeLoanCapUsd({successfulOnTimeRepayments: 0}) === 0.02` — the exact cold-start SIZING case, requiring zero collateral/reputation | 1 | true | unit test, direct assertion — this proves the SIZING half of arXiv 2602.14219 §4.2.2's gap (zero-collateral first-loan issuance); it does NOT prove borrower repayment capacity is resolved — that is REQ-105's explicit, monitored, experimental-hypothesis claim (PROP-105f), never a proven fact (resolves FIND-004's overclaim) |
| PROP-105b | REQ-105 | `computeLoanCapUsd` at `n=1,7,8` produces `0.04, 2.56, 5.00` (capped, not `5.12`) | 1 | true | unit test, exact numeric assertions at each boundary |
| PROP-105c | REQ-105 | `countSuccessfulOnTimeRepayments` excludes any row with `on_time:false` or `status !== "repaid"` from its count | 1 | true | unit test: mixed fixture (on-time repaid, late repaid, active, defaulted) → assert only the on-time-repaid row is counted |
| PROP-105d | REQ-105 | `decideLoan`'s `loanAmountUsd` argument is always `computeLoanCapUsd`'s own output for that borrower, never an independently-supplied number | 1 | true | unit test wiring the two functions together against a fixture, plus a structural/Tier-0 check confirming no other call site supplies `loanAmountUsd` |
| PROP-105e | REQ-105 | A malformed/negative/non-integer `successfulOnTimeRepayments` input is treated as `0` (fail-closed), never a larger unearned cap | 1 | true | unit test: `-1`/`NaN`/`1.5` fixtures → assert `computeLoanCapUsd` returns `firstLoanUsd` (the floor), never throws, never a larger value |
| PROP-105f | REQ-105 | `computeColdStartRepaymentRate({loanRows, n})` correctly computes `{sampleSize, repaidCount, defaultedCount, pendingCount, rate}` over the first `n` colony-wide cold-start-originated loans, never divides by zero — the monitoring-plan companion that makes REQ-105's "experimental hypothesis, not proven solution" framing (resolves FIND-004) a verifiable, not merely asserted, property | 1 | true | unit test: a fixture with 3 repaid + 1 defaulted + 1 still-active cold-start loan → assert `{sampleSize:5, repaidCount:3, defaultedCount:1, pendingCount:1, rate:0.6}`; a fixture with zero cold-start loans → assert `rate:null`, never a division-by-zero throw |
| PROP-106a | REQ-106 | Given two concurrent callers targeting the SAME lender, both observing sufficient available surplus at read time, exactly one disburses; the other returns `reason:"lock_held"` with zero transfer calls | 2 | true | integration test: two `Promise.all`-raced calls into `withGigLock(LOANS_LEDGER_PATH, `loan_${lenderId}`, fn)`, assert exactly one invocation of the (mocked) transfer step |
| PROP-106b | REQ-106 | A crashed holder's lock (no heartbeat for ≥ `staleMs`) is reclaimable by exactly one subsequent caller | 1/2 | true | reuses the exact Tier-1 `isLockStale` fixture tests already proved upstream (`anicca-agent-economy` REQ-101) plus a Tier-2 test creating a real backdated `loan_<lenderId>.lock` file |
| PROP-106c | REQ-106 | A live, heartbeating holder is never stolen from, however long its critical section legitimately runs | 1 | true | reuses the exact Tier-1 fixture proof already established upstream for `isLockStale` — no new proof needed |
| PROP-106d | REQ-106 | EVERY call site in the implementation that acquires a loan-issuance lock, or reads/writes `loans.jsonl`, imports and passes the SAME exported `LOANS_LEDGER_PATH` constant — never an independently hardcoded path string | 0 | true | structural/Tier-0 check: source-grep or import-identity check across the diff confirming a single import site and zero hardcoded `loans.jsonl` path strings elsewhere |
| PROP-106e | REQ-106 | Two DIFFERENT lenders issuing concurrently (each with zero prior loan rows) produce DISTINCT `loan_id`s with zero collisions, using only each lender's own existing per-lender lock — no shared/global lock required (resolves FIND-001) | 1/2 | true | Tier-1 unit test: `nextLoanSequenceForLender(loanRows, lenderId)` over a fixture with rows for TWO different lenders → assert each lender's own sequence is independent and namespaced (`loan_${lenderA}_1` vs `loan_${lenderB}_1`); Tier-2 integration test: two concurrent `Promise.all`-raced real disbursement calls against two DIFFERENT lenders → assert both succeed and their resulting `loan_id`s are distinct |
| PROP-106f | REQ-106 | If `payViaFacilitator` fails for any reason (facilitator unreachable, `verify`/`settle` failure, reverted settle tx) at disbursement time, the loan-issuance critical section fails cleanly: zero `loans.jsonl` row is appended and the per-lender lock is released normally (resolves FIND-003's fail-closed requirement) | 2 | true | integration test: inject a mocked `payViaFacilitator` that rejects/returns `{ok:false}` → assert no `loans.jsonl` row is appended and a subsequent call for the SAME lender can immediately re-acquire the lock |
| PROP-107a | REQ-107 | REQ-101/102's eligibility functions accept only citizen records whose `wallet.evm === true`; a Solana-only citizen is excluded from both roles | 1 | true | unit test: fixture citizen with `wallet: {solana: true}` only, no `wallet.evm` → assert excluded from lender AND borrower eligibility |
| PROP-107b | REQ-107 | No code path in this feature's disbursement/repayment step constructs a Solana transaction or imports a Solana signing library | 0 | true | structural grep across the feature's diff for any `@solana/web3.js`/`solana` keypair import — must find none |
| PROP-112a | REQ-112 | This feature's `lock.mjs` acquire/release path and `ledger.js` read/write path (via `LOANS_LEDGER_PATH`) are invoked only from code that assumes a single, shared, local `loans.jsonl`/`locks/` directory — no code path constructs a remote/networked path or attempts to reach a non-co-located citizen's own filesystem (resolves FIND-002) | 0 | true | structural/Tier-0 check: source-grep/read across the diff confirming no remote-filesystem/networked-lock construction and, where used, citizen records' `homeDir` is only ever compared for equality (co-location check), never used to construct a remote connection |
| PROP-108a | REQ-108 | A real repayment transaction's receipt is independently re-queried via a SEPARATE RPC call, not trusted from either party's own self-report, and its block is confirmed FINALIZED (not merely `"latest"`) before crediting | 3 | true | live E2E: a fresh, independent `getTransactionReceipt` + `eth_getBlockByNumber("finalized")` query taken by a process that is neither the lender nor the borrower, performed after a real repayment transaction |
| PROP-108b | REQ-108 | Verification reads the transaction's own `Transfer(from,to,value)` event log for attribution (decoded via `record-earn.mjs`'s own already-hardened `TRANSFER_TOPIC`-match + EXACT zero-padded-address-equality pattern, never a substring/suffix match per `FIND-704`), not merely a raw before/after balance delta (resolves FIND-007's mischaracterization) | 1/2 | true | unit/integration test: a fixture where the lender's balance ALSO increases from an unrelated, simultaneous inflow → assert only the specific repayment transaction's own logged value is credited, not the full balance delta; PLUS a fixture whose `to` topic is a SUFFIX match but not an EXACT zero-padded match for the lender's wallet → assert REJECTED (credits `0`), reproducing `record-earn.mjs`'s own previously-fixed `FIND-704` bug class and confirming it is not re-introduced here |
| PROP-108c | REQ-108 | A partial-then-full repayment (two transactions summing to `total_due_usd`) correctly transitions the loan from `"active"` (after the first, partial transaction) to `"repaid"` (after the second) | 2 | true | integration test: inject two real-shaped receipt fixtures in sequence, assert the loan's status transitions exactly once, at the correct point |
| PROP-109a | REQ-109 | `detectDefaultedLoans` returns exactly the `loan_id`s whose last-appended row is `"active"`, past `due_ms`, and `repaid_usd < total_due_usd` | 1 | true | unit test, fixed fixture: one overdue-unpaid loan, one on-time-repaid loan, one not-yet-due active loan → assert only the first is flagged |
| PROP-109b | REQ-109 | `excludeDefaultedBorrowers` excludes exactly the citizens with a currently-`"defaulted"` row as `borrower_id`, passing through unfiltered every other citizen | 1 | true | unit test, fixed fixture mirroring `anicca-agent-spawn` PROP-101d's own structure (defaulted citizen, healthy citizen, no-row citizen) |
| PROP-109c | REQ-109 | Neither `detectDefaultedLoans` nor `excludeDefaultedBorrowers` ever mutates or deletes an existing `loans.jsonl` row (append-only) | 0 | true | structural read of both functions' source confirming no `fs.writeFile`/`fs.unlink`/array-mutation of an existing row — only a NEW row is ever proposed for append by a separate, effectful caller |
| PROP-109d | REQ-109 | A late-but-eventual full repayment after a `"defaulted"` row retroactively appends `status:"repaid", on_time:false`, restoring REQ-102 eligibility immediately but NOT incrementing REQ-105's `successfulOnTimeRepayments` count | 1/2 | true | unit test: a fixture already `"defaulted"`, followed by a qualifying repayment fixture → assert `isBorrowerEligible` becomes `true` again AND `countSuccessfulOnTimeRepayments` is unchanged |
| PROP-110a | REQ-110 | `economy/gig/decide.mjs` and this feature's own eligibility/sizing functions share zero code coupling | 0 | true | structural/Tier-0 check: `decide.mjs` imports nothing from `economy/lending/`, and this feature's own modules import nothing from `economy/gig/decide.mjs` (only the UNRELATED, already-shared primitives — `lock.mjs`, `escrow.mjs` — are imported by both, which is expected reuse, not coupling of DECISION logic) |
| PROP-111a | REQ-111 | No new function this feature introduces references a known human-funded wallet identifier (claude-p's addresses, per `docs/WALLETS.md`) | 0 | true | structural grep across the feature's diff for `0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74` or any other documented human-funded wallet identifier — must find none |
| PROP-111b | REQ-111 | `is-self-funded.mjs`'s own source is byte-identical to its pre-existing version | 0 | true | structural diff of the file against its pre-modification version — zero changes |

## Verification Strategy

- **Tier 0** (no runtime execution of the audited code): REQ-103's no-LLM/no-scoring check (PROP-103a);
  REQ-104's no-arbitrary-principal structural check (PROP-104b); REQ-106's canonical-`statePath`
  import-identity check (PROP-106d); REQ-107's no-Solana-code-path structural check (PROP-107b);
  REQ-109's append-only structural check (PROP-109c); REQ-110's zero-coupling check (PROP-110a);
  REQ-111's no-human-funded-wallet-reference grep (PROP-111a) and `isSelfFunded()`-byte-identical check
  (PROP-111b); REQ-112's no-remote/networked-path structural check (PROP-112a).
- **Tier 1** (pure-function unit tests): REQ-101's arithmetic and fail-closed checks (PROP-101a-e) plus
  its new gojo-awareness check (PROP-101f); REQ-102's three-condition gate and boundary checks
  (PROP-102a-d); REQ-104's interest arithmetic and no-late-interest-accrual checks (PROP-104a/c);
  REQ-105's cold-start SIZING resolution and ladder-boundary checks (PROP-105a-e — PROP-105a proves the
  SIZING half of arXiv 2602.14219 §4.2.2's gap, NOT a claim that borrower repayment capacity is proven;
  see PROP-105f, the monitoring-plan companion) plus its cold-start monitoring check (PROP-105f);
  REQ-106's `nextLoanSequenceForLender` collision-freedom check (PROP-106e, Tier-1 half) and reused
  `isLockStale` wiring (PROP-106b/c, reusing the already-proved upstream fixtures); REQ-107's
  Solana-exclusion check (PROP-107a); REQ-109's default-detection and exclusion-filter checks
  (PROP-109a/b).
- **Tier 2** (integration, real module wiring + fresh-context adversary disk review, no live chain spend
  required): REQ-106's concurrent-issuance race (PROP-106a), crashed-holder reclaim (PROP-106b,
  integration half), cross-lender `loan_id`-collision-freedom check (PROP-106e, Tier-2 half), and
  injected-facilitator-failure fail-closed check (PROP-106f); REQ-108's event-log-attribution (using
  `record-earn.mjs`'s own exact-padded-topic-equality pattern) and partial-then-full transition checks
  (PROP-108b/c); REQ-109's retroactive-correction check (PROP-109d, integration half).
- **Tier 3** (live, no-mock E2E, HARD RULE 0.24): REQ-108's real repayment-verification E2E (PROP-108a)
  — a real disbursement transfer (`payViaFacilitator`), a real repayment transfer, and an independent,
  separately-performed, finalized-block-confirmed RPC re-verification. **Per the Tier-3 policy this
  feature inherits from `anicca-agent-spawn`/SPEC.md §9.9, a Base-Sepolia-first pass is an acceptable
  precursor, but this increment's own completion requires at least one real Base-mainnet-class result.**

## Gate

Phase 3 (adversarial review) must confirm, via fresh-context, disk-only review plus (for the Tier-3
item) live re-execution performed by the adversary itself:

(1) REQ-101/102's eligibility arithmetic is read end-to-end confirming: `isSelfFunded()` gates BOTH
lender and borrower with no human-funded wallet leaking into either role (PROP-101b, PROP-111a), the
"broke" threshold is strictly-less-than at the boundary (PROP-102b), the outstanding-obligation check
blocks a second loan regardless of balance (PROP-102c), `sumOutstandingPrincipalUsd`'s last-write-wins
reduction correctly includes a defaulted loan's unrecovered principal (PROP-101d), and
`sumRecentGojoGiftsUsd`'s new, read-only awareness of `ubi`'s `gojo-log.jsonl` is genuinely READ-ONLY
(never writes) and correctly windowed (PROP-101f) — the adversary MUST also explicitly confirm the
Dependencies section's disclosed, acknowledged, NOT-YET-SOLVED reverse-direction limitation (gojo itself
remains unaware of `loans.jsonl`) is honestly stated, not silently omitted — a control-flow read, not
merely an outcome check;

(2) REQ-105's reputation-capital ladder is read end-to-end confirming: the cold-start case
(`successfulOnTimeRepayments=0 → $0.02`) requires literally zero collateral/reputation and is bounded to
the SAME trivial scale as the real P2 genesis event (PROP-105a — this proves the SIZING half of arXiv
2602.14219 §4.2.2's gap; the adversary MUST explicitly confirm the spec does NOT overclaim the ECONOMIC
half — i.e. it does not assert $0.02 is proven sufficient for a borrower to generate repayment capacity
— and that REQ-105's monitoring-plan function `computeColdStartRepaymentRate` (PROP-105f) is present as
the mechanism for tracking whether this experimental hypothesis holds up empirically), the doubling
ladder is correctly capped (PROP-105b), and a late repayment never grows the ladder (PROP-104c/PROP-
109d);

(3) REQ-106's mutual exclusion is proven under a deliberately-induced concurrent race against the SAME
lender, confirming exactly one disburses and the other logs `reason:"lock_held"` with zero transfer side
effects (PROP-106a), AND that the loan-issuance lock is genuinely wired through the EXISTING,
already-hardened `lock.mjs` module rather than a fresh reimplementation (control-flow read, not a grep
for the word "lock"), AND that EVERY call site acquiring this lock imports the SAME exported
`LOANS_LEDGER_PATH` constant (PROP-106d), AND that `loan_id` generation (`nextLoanSequenceForLender`) is
computed STRICTLY INSIDE that SAME per-lender lock, is namespaced by `lenderId`, and produces zero
collisions across two DIFFERENT concurrently-issuing lenders with no shared/global lock (PROP-106e —
resolves FIND-001), AND that a facilitator-unreachable/failed disbursement fails cleanly with zero
`loans.jsonl` row appended and the lock released normally (PROP-106f — resolves FIND-003);

(4) REQ-108's repayment verification is read end-to-end confirming it NEVER trusts either party's own
self-report: the receipt is independently re-queried AND its block is confirmed finalized before
crediting (PROP-108a), attribution uses the transaction's own `Transfer` event log decoded via
`record-earn.mjs`'s own already-hardened `TRANSFER_TOPIC`-match + EXACT zero-padded-address-equality
pattern — never a substring/suffix match, and never `escrow.mjs` (which contains no such logic at all,
resolving FIND-007) — not a bare balance delta (PROP-108b), correctly handling a partial-then-full
sequence (PROP-108c);

(5) REQ-109's default handling is read end-to-end confirming: `detectDefaultedLoans`/
`excludeDefaultedBorrowers` are append-only and never mutate an existing row (PROP-109c), a late
retroactive correction restores eligibility without growing reputation (PROP-109d), and the
cross-feature composition (`excludeDefaultedBorrowers` applied AFTER `anicca-agent-spawn`'s own
`filterProductiveCitizens`, never a modification of that function's source) is confirmed structurally —
the adversary MUST also flag, as an explicit open risk (not a blocking finding by itself, since this
increment's own Dependencies section already discloses it), that `anicca-agent-spawn`'s registry is not
yet built and this composition point will need re-verification once it is;

(6) REQ-103's design constraint holds — no LLM/prompt/scoring code exists anywhere in
`computeLenderAvailableUsd`/`isBorrowerEligible`/`computeLoanCapUsd`/`detectDefaultedLoans`/
`excludeDefaultedBorrowers`'s diff (PROP-103a), matching the identical `anicca-agent-economy` REQ-203 /
`anicca-agent-spawn` REQ-104 precedent this feature explicitly follows;

(7) REQ-107's scope-narrowing constraint holds structurally — no Solana transaction/signing-library code
path exists anywhere in this feature's diff (PROP-107b), and REQ-101/102 structurally require
`wallet.evm===true` (PROP-107a);

(8) REQ-110's coexistence claim holds structurally — `economy/gig/decide.mjs` and this feature's own
decision functions share zero code coupling beyond the already-shared, unrelated primitives (`lock.mjs`,
`escrow.mjs`) (PROP-110a) — and, separately, the adversary confirms REQ-101's disclosed, one-way,
read-only `ubi`/`gojo-log.jsonl` awareness does NOT contradict this claim (it is a distinct, explicitly
scoped exception, never silently conflated with "zero coupling");

(9) REQ-111's money-safety invariant holds — a grep across this feature's entire diff for any
human-funded wallet identifier returns zero matches (PROP-111a), and `is-self-funded.mjs` itself is
confirmed byte-identical to its pre-existing version (PROP-111b);

(10) REQ-112's single-coordinator-host scope constraint holds structurally — no code path in this
feature's diff constructs a remote/networked lock or ledger path (PROP-112a), this is confirmed as the
DIRECT, by-name analog of `anicca-agent-spawn` REQ-106's own precondition (resolves FIND-002), and the
adversary MUST confirm the spec's own known-limitation framing (lending TO/FROM a future remote-cloud-
hosted citizen is explicitly out of scope, never silently assumed to already work) is present, not
omitted.
