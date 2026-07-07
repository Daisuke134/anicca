# Behavioral Spec — anicca-agent-lending (Phase 1a)

**feature**: anicca-agent-lending · **mode**: strict · **increment**: in-colony agent-to-agent lending
(citizen-to-citizen loans, first-party Anicca capability, no external protocol import) · **日付**:
2026-07-07 · **revision**: iteration 1

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
`economy/gig`. It does NOT invent a variable-rate/variable-amount lending market, does NOT build
multi-signer pooled loans, and does NOT extend to Solana-denominated lenders/borrowers this increment
(REQ-107 narrows scope honestly, mirroring `anicca-agent-spawn` REQ-106's single-coordinator-host
scope-narrowing precedent). P4's future "bank" vision (SPEC.md §9.3, a Goldfinch-`CreditLine.sol`-style
growth engine with third-party-verified trust scores) is explicitly a LATER, larger increment; this
spec is v1: the smallest mechanism that actually resolves the cold-start problem today.

## Dependencies and assumptions (must be read before implementation)

- **`anicca-agent-spawn` (currently mid-VCSDD-pipeline, Phase 1c spec review iteration 5,
  `.vcsdd/features/anicca-agent-spawn/specs/behavioral-spec.md`)** defines REQ-101
  (`computeColonySurplusUsd`, `filterProductiveCitizens`) and REQ-105 (the dedicated citizen registry,
  `~/anicca/skills/self/spawn/registry/citizens.json` — NOT YET CREATED on disk as of this writing;
  confirmed absent via a direct filesystem check this session). This feature's lender/borrower surplus
  arithmetic (REQ-101/102 below) is designed to be CONCEPTUALLY CONSISTENT with that registry's record
  shape (`{id, wallet: {evm?, solana?}, walletAddress: {evm?, solana?}, fuel, humanDependencies}`) and
  with `computeColonySurplusUsd`'s exact arithmetic style (`max(0, balance_i - perCitizenReserveUsd)`,
  `perCitizenReserveUsd` defaulting to `5.00`) — it deliberately reuses that same default rather than
  inventing a second, competing reserve figure. **This feature does NOT modify
  `anicca-agent-spawn`'s own function signatures or files** (avoiding a tight coupling between two
  independently-evolving specs); instead it composes a SECOND, lending-owned filter pass
  (`excludeDefaultedBorrowers`, REQ-109) that runs AFTER `filterProductiveCitizens`'s output. **If
  `anicca-agent-spawn`'s registry/join shape changes further before it reaches Phase 1c PASS, this
  spec's REQ-101/102/109 MUST be revisited** — this is a live, explicitly-flagged risk, not an
  oversight.
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
  primitive for BOTH loan disbursement and loan repayment (REQ-107) — a generic
  `payViaFacilitator({privateKey, to, amountBase})` call from whichever side is paying, not a new
  transfer mechanism. `~/anicca/skills/economy/ubi/execute-ubi.py`'s raw-ERC20 (non-gasless) transfer
  was read and considered but NOT chosen as the primary path (gasless is strictly better for a
  possibly gas-poor borrower) — it remains a documented, out-of-scope fallback, not built this
  increment.
- **`~/anicca/skills/economy/gig/decide.mjs`** (`DEFAULT_RESERVE_USDC=5.0`, `DEFAULT_LOW_USDC=0.5`) —
  this feature reuses `DEFAULT_LOW_USDC=0.5` verbatim as the "genuinely broke" threshold for borrower
  eligibility (REQ-102), the SAME number this codebase already uses colony-wide to mean "broke," rather
  than inventing a second, competing "broke" definition.

## Purity boundary analysis (overview — file/function detail lives in verification-architecture.md)

| Concern | Classification | Why |
|---|---|---|
| Self-funded gate (lender + borrower) | **Pure core (existing, reused unmodified)** | `is-self-funded.mjs::isSelfFunded` — zero new judgment logic. |
| Lender available-surplus arithmetic | **Pure core (new)** | `computeLenderAvailableUsd`/`sumOutstandingPrincipalUsd` — deterministic arithmetic over already-fetched balances + already-read ledger rows, zero I/O. |
| Borrower eligibility check | **Pure core (new)** | `isBorrowerEligible` — boolean logic over already-known facts (self-funded, balance, outstanding-obligation lookup). |
| Reputation-capital sizing ladder | **Pure core (new)** | `computeLoanCapUsd`/`countSuccessfulOnTimeRepayments` — deterministic function of a repayment COUNT read from this feature's own ledger, no external oracle, no model judgment. |
| Loan issuance decision | **Pure core (new)** | `decideLoan` — boolean comparison of already-computed numbers. |
| Default detection | **Pure core (new)** | `detectDefaultedLoans` — deterministic elapsed-time comparison over already-read rows. |
| Cross-feature defaulted-borrower exclusion | **Pure core (new)** | `excludeDefaultedBorrowers` — a SECOND, lending-owned filter composed after (never inside) `anicca-agent-spawn`'s own `filterProductiveCitizens`. |
| Loan ledger (dedicated file, existing generic primitive reused) | **Effectful shell (existing code, new file)** | `ledger.js::readChildren`/`appendChild`, reused unmodified, pointed at `~/anicca/skills/economy/lending/state/loans.jsonl`. |
| Loan-issuance mutual exclusion | **Effectful shell (existing, reused unmodified)** | `lock.mjs::withGigLock`/`isLockStale`, new lock key `loan_<lenderId>`, canonical `statePath` = `LOANS_LEDGER_PATH`. |
| Disbursement / repayment transfer | **Effectful shell (existing, reused unmodified)** | `escrow.mjs::payViaFacilitator`. |
| Independent repayment verification | **Effectful shell (new, reuses an already-imported pattern)** | An RPC balance-read + `getTransactionReceipt` check, reusing `escrow.mjs`'s own already-imported `viem`/`createPublicClient` dependency and mirroring `anicca-agent-spawn` REQ-401's exact independent-verification method. |
| REQ-103 (bookkeeping-only design constraint) | **Not code — a design constraint** | Verified by Phase 3 structural code read, not a runtime assertion (mirrors `anicca-agent-economy` REQ-203 / `anicca-agent-spawn` REQ-104). |
| REQ-107 (chain/asset scope constraint) | **Not code — a design constraint** | Verified structurally (mirrors `anicca-agent-spawn` REQ-106's honest single-scope precedent). |

## Non-functional requirements

- **Performance**: every pure function (REQ-101/102/104/105/108/109) is O(n) over already-read ledger
  rows (n = this colony's own loan/citizen count, expected single digits to low hundreds for the
  foreseeable future) — no unbounded recursion, no network call inside a pure function.
- **Security / money-safety**: fail-closed everywhere (missing/malformed/non-finite input never
  defaults to "eligible" or "repaid"); private key material is NEVER written into `loans.jsonl` (only
  wallet ADDRESSES, matching `citizens.json`'s own `walletAddress`/`wallet` field-split discipline);
  every disbursement/repayment is independently re-verified on-chain, never trusted from either party's
  self-report (REQ-108); the money-safety invariant (REQ-111) is enforced structurally, not by runtime
  trust.

---

## Requirements

### REQ群A: 適格性ゲート（決定論、model判断なし）

### REQ-101: Lender eligibility & available-surplus computation
**EARS**: WHEN a citizen is considered as a potential lender for a specific loan, THE SYSTEM SHALL
admit it as an eligible lender only if `isSelfFunded()` (`~/anicca/skills/_shared/lib/is-self-funded.mjs`,
reused unmodified) returns `true` for that citizen's `{wallet, fuel, humanDependencies}` sub-object AND
its computed available-surplus is strictly greater than `0`, where available surplus is:

```
computeLenderAvailableUsd({ lenderBalanceUsd, perCitizenReserveUsd = 5.00, outstandingPrincipalUsd })
  = max(0, lenderBalanceUsd - perCitizenReserveUsd - outstandingPrincipalUsd)
```

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
built this increment) resolves it; a `"repaid"` row contributes `0`.

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

**Acceptance Criteria**:
- `computeLenderAvailableUsd` and `sumOutstandingPrincipalUsd` are pure, zero I/O, given already-fetched
  inputs.
- A lender with `balance=$8`, `reserve=$5`, `outstandingPrincipal=$1` → available `= max(0, 8-5-1) = $2`.
- A lender whose `isSelfFunded()` check is `false` contributes `0` available surplus regardless of
  balance.
- A lender with one `"defaulted"` loan whose principal was never repaid has that principal permanently
  subtracted from every future `computeLenderAvailableUsd` call until a future write-off mechanism
  changes it.

---

### REQ-102: Borrower eligibility
**EARS**: WHEN a citizen is considered as a potential borrower, THE SYSTEM SHALL admit it as eligible
only if ALL THREE hold: (a) `isSelfFunded()` returns `true` for that citizen's `{wallet, fuel,
humanDependencies}` sub-object; (b) its own current balance is strictly below `BORROWER_LOW_USD`
(default `0.50`, reusing `economy/gig/decide.mjs`'s existing `DEFAULT_LOW_USDC` constant verbatim — the
SAME "genuinely broke" definition already established colony-wide, not a second, competing threshold);
and (c) `loans.jsonl` contains NO row for that citizen (as `borrower_id`, reduced to its
last-appended-per-`loan_id` rows) whose `status` is `"active"` OR `"defaulted"` — i.e. the citizen has
ZERO currently-open loan obligations. Condition (c) is deliberately a single, simple "at most one
outstanding loan at a time" rule (not a separate "unpaid past a threshold" clock) — this is the
simplest rule that (i) prevents a citizen from stacking multiple simultaneous loans and (ii) makes a
default permanently block further borrowing until the defaulted row is explicitly resolved (REQ-109),
satisfying the "avoid serial defaulting" requirement without inventing a second timing mechanism beyond
REQ-104's own repayment window.

**Edge Cases**:
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
- `isBorrowerEligible({ borrowerAgent, loanRows, borrowerId, borrowerBalanceUsd })` is pure, zero I/O,
  returns `{eligible: boolean, reason: "ok"|"not_self_funded"|"not_broke_enough"|"outstanding_loan"}`.
- A fixture borrower with `balance=$0.49`, `isSelfFunded()=true`, zero loan rows → `eligible:true`.
- A fixture borrower with an `"active"` row for its own `borrower_id` → `eligible:false,
  reason:"outstanding_loan"`, regardless of how low its balance is.

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
- `FIRST_LOAN_USD = 0.02` — reused, not invented: the EXACT bounty amount (`bountyUsdcBase: 20000` =
  0.02 USDC) SPEC.md §9.9's own real gig #3 already proved is "enough to complete one real gig" in this
  exact system — the smallest historically-proven useful unit this colony has ever actually settled.
- `LOAN_INTEREST_RATE = 0.10` (10%, fixed simple interest on principal, never compounding, never
  annualized/variable) — reused from `economy/ubi/ubi.js`'s own `DEFAULT_CONTRIBUTE_CONFIG.contributePct
  = 0.10`, the same order-of-magnitude "modest, sustainable slice" figure this codebase already uses for
  a conceptually similar purpose, rather than an unrelated invented percentage.
- `LOAN_REPAYMENT_WINDOW_DAYS = 14` — reused from `anicca-agent-spawn`'s own `SPAWN_COOLDOWN_DAYS`/
  `BOOTSTRAP_WINDOW_DAYS` default (both `14`) — a new/broke citizen needs roughly this long to complete
  its own first gig-settlement cycle (REQ-401 of that same feature), so a loan's repayment window is set
  to the SAME already-established colony timescale rather than an unrelated new number.
- `total_due_usd = principal_usd * (1 + LOAN_INTEREST_RATE)` — simple interest, computed once at
  issuance, never recalculated.

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
- `total_due_usd` for `FIRST_LOAN_USD` = `0.02 * 1.10 = 0.022`.
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
  = min(maxLoanUsd, firstLoanUsd * (2 ** successfulOnTimeRepayments))
```

`successfulOnTimeRepayments` = `countSuccessfulOnTimeRepayments(loanRows, borrowerId)`, a pure count
(zero I/O) of that borrower's own `loans.jsonl` rows (reduced to one effective row per `loan_id`,
last-write-wins) where `status === "repaid"` AND `on_time === true` (set at repayment time, REQ-108: the
qualifying repayment transaction landed at or before `due_ms`). A borrower with ZERO prior loans
(`successfulOnTimeRepayments = 0`) gets `computeLoanCapUsd(...) = firstLoanUsd = 0.02` — the formula
naturally produces `FIRST_LOAN_USD` with zero special-casing, resolving the cold-start problem WITHOUT
any collateral, any external credit-score oracle, or any hand-waved "trust the agent" assumption: the
FIRST loan any brand-new citizen ever receives requires literally zero reputation and is bounded to the
SAME trivial scale as the real P2 genesis event, so the LENDER's own risk on a totally-unknown borrower
is structurally tiny by construction. `maxLoanUsd` defaults to `5.00` — the SAME order-of-magnitude
anchor (`perCitizenReserveUsd`/`DEFAULT_RESERVE_USDC`/`MIN_SHELTER_USD`, all `5.00` colony-wide) reused
deliberately, not coincidentally, for internal consistency and to keep even a well-established
borrower's loan "small" per this increment's own scope.

**Edge Cases**:
- A late-but-eventual full repayment (REQ-109: `on_time=false`) does NOT increment
  `successfulOnTimeRepayments` — the borrower's next loan cap stays exactly where it already was (no
  growth, but also no regression/penalty beyond that).
- The doubling ladder would overshoot `maxLoanUsd` (e.g. `0.02 * 2^8 = 5.12`): capped at `5.00` exactly
  — `Math.min` never lets the loan amount exceed the ceiling.
- A borrower has a mix of on-time and late repayments across its history: only ON-TIME ones count
  toward `successfulOnTimeRepayments` — a late repayment neither subtracts from nor is ignored entirely;
  it simply does not ADD.
- `successfulOnTimeRepayments` is somehow negative/non-integer (malformed input): treated as `0` (the
  cold-start floor), fail-closed — never a larger, unearned cap.

**Acceptance Criteria**:
- `computeLoanCapUsd({successfulOnTimeRepayments: 0}) === 0.02` (exact cold-start resolution case).
- `computeLoanCapUsd({successfulOnTimeRepayments: 1}) === 0.04`,
  `computeLoanCapUsd({successfulOnTimeRepayments: 7}) === 2.56`,
  `computeLoanCapUsd({successfulOnTimeRepayments: 8}) === 5.00` (capped, not `5.12`).
- `countSuccessfulOnTimeRepayments` is pure, zero I/O, and excludes any `on_time:false` or
  non-`"repaid"` row from its count.
- `decideLoan({ lenderAvailableUsd, loanAmountUsd })` (pure) returns `eligible:true` only when
  `lenderAvailableUsd >= loanAmountUsd`, where `loanAmountUsd` is ALWAYS `computeLoanCapUsd`'s own
  output for that borrower — never an independently-supplied number.

---

### REQ群C: Issuance mechanics

### REQ-106: Loan issuance concurrency safety
**EARS**: WHEN two or more loan-issuance evaluations against the SAME lender race in an overlapping
wake window, THE SYSTEM SHALL ensure at most ONE actually disburses funds against that lender's
surplus — reusing, unmodified, `~/anicca/skills/economy/gig/lib/lock.mjs`'s `withGigLock`/`isLockStale`/
atomic-`fs.rename`-based stale-reclaim mechanism (the SAME already-adversary-hardened generic lock this
colony already reuses for the gig board and, per `anicca-agent-spawn` REQ-103, for colony-spawn) under a
NEW, lender-scoped lock key `` `loan_${lenderId}` `` (matching `isSafeLockKey`'s existing
`[A-Za-z0-9_-]+` character-set constraint) — this is a new lock KEY on an EXISTING lock MECHANISM, never
new lock-implementation code.

`withGigLock`'s real signature is `withGigLock(statePath, lockKey, fn, opts)`; `statePath` determines
which physical `locks/` directory the lock file lives under. THE SYSTEM SHALL therefore designate a
SINGLE canonical `statePath` — `~/anicca/skills/economy/lending/state/loans.jsonl` — exported as ONE
named constant, `LOANS_LEDGER_PATH`, from a new shared module
`~/anicca/skills/economy/lending/lib/lending-path.mjs`. EVERY call site that acquires a loan-issuance
lock, or reads/writes `loans.jsonl` itself, SHALL import and use this SAME exported constant — never an
independently hardcoded path string — mirroring `anicca-agent-spawn` REQ-103's identical
`CITIZENS_REGISTRY_PATH` discipline and closing the SAME "mismatched `statePath` silently defeats mutual
exclusion" hazard that discipline exists to close.

**Edge Cases**:
- Two DIFFERENT lenders' loan requests proceed concurrently without contention (different lock keys
  under the SAME `locks/` directory): intentional, not a bug — mirrors `gig.mjs`'s own existing
  per-`gigId` lock-key pattern (documented in `lock.mjs`'s own header comment).
- The instance holding the lock crashes mid-issuance: the existing heartbeat + `isLockStale` mechanism
  reclaims the lock after `staleMs` of no heartbeat, exactly as it already does for gig-board
  operations — REQ-106 does not need a second staleness mechanism.
- A live, heartbeating holder is never stolen from, however long its critical section legitimately
  runs — this property is inherited, not re-derived, from the existing lock.
- A future call site hardcodes its own literal `loans.jsonl` path string instead of importing
  `LOANS_LEDGER_PATH`: treated as a spec violation to be caught at Phase 3 review (a structural/
  import-identity check, not a runtime assertion) — mirrors `anicca-agent-spawn` REQ-103's identical
  edge case.

**Acceptance Criteria**:
- The loan-issuance critical section (REQ-101 read → REQ-102/104/105 compute → disbursement transfer →
  REQ-108/109 ledger append) is wrapped by `withGigLock(LOANS_LEDGER_PATH, `loan_${lenderId}`, fn)`,
  using the SAME `lock.mjs` module, never a reimplementation.
- Given two concurrent callers both targeting the SAME lender and both observing sufficient available
  surplus at read time, an integration test proves exactly one disburses; the other's attempt is
  recorded as `reason:"lock_held"` and makes zero transfer calls.
- A structural/Tier-0 check confirms EVERY call site that invokes the loan-issuance lock, or reads/writes
  `loans.jsonl`, imports and uses the SAME `LOANS_LEDGER_PATH` constant.

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
wallet-to-wallet transfer helper reusable here). This mirrors `anicca-agent-spawn` REQ-106's own honest
single-coordinator-host scope-narrowing precedent: a documented, deliberate limitation, not an
oversight.

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

### REQ群D: Repayment + default

### REQ-108: Repayment verification mechanism
**EARS**: WHEN a borrower claims to have repaid an outstanding loan, THE SYSTEM SHALL mark that loan
`"repaid"` only after an INDEPENDENT on-chain check confirms it — never accepted from either party's
own self-report alone, mirroring the exact method `anicca-agent-spawn` REQ-401 and SPEC.md §9.9 already
use to confirm a settlement (`eth_call balanceOf` before/after, independent of either trading party):
(a) the claimed repayment transaction hash's own receipt (`getTransactionReceipt`) shows `status:
success`; (b) that transaction's own `Transfer(from, to, value)` event log shows `from` = the
borrower's own recorded `walletAddress.evm`, `to` = the lender's own recorded `walletAddress.evm`, and
`value` (converted to USD) summed with any PRIOR verified partial repayments for this SAME `loan_id`
reaches at least `total_due_usd` (REQ-104). Attribution uses the transaction's own event log, NOT a
bare before/after balance delta, so an unrelated coincidental inflow to the lender's wallet in the same
window is never mistaken for a repayment.

**Edge Cases**:
- The repayment transaction succeeds but moves LESS than the amount still owed (a partial repayment):
  `repaid_usd` is updated to the new cumulative total, but the loan remains `"active"` — it is not
  marked `"repaid"` until the cumulative total reaches `total_due_usd`.
- The claimed transaction hash does not exist, reverted, or its `Transfer` event's `to` address is NOT
  the lender's own recorded wallet: THE SYSTEM SHALL credit `0` (fail-closed) — never assume good faith
  from an unverified claim.
- The lender's wallet balance also increased in the same window from an unrelated, coincidental inflow
  (e.g. a separate gig payout landing simultaneously): the event-log-based attribution (not a bare
  balance delta) ensures only the SPECIFIC repayment transaction's own value is credited.

**Acceptance Criteria**:
- A real repayment transaction's receipt is independently re-queried via a SEPARATE RPC call from the
  one either the lender or borrower's own process performed, matching `anicca-agent-spawn` REQ-401's
  PROP-401a precedent exactly.
- Verification reads the transaction's own `Transfer` event log, never merely a raw balance delta
  (closes the "unrelated coincidental inflow" false-positive edge case above).
- A fixture with a partial-then-full repayment (two transactions summing to `total_due_usd`) correctly
  transitions the loan from `"active"` (after the first, partial transaction) to `"repaid"` (after the
  second).

---

### REQ-109: Default detection & handling
**EARS**: WHEN a loan's `due_ms` (`issued_ms + LOAN_REPAYMENT_WINDOW_DAYS * 86400000`) has passed AND
its last-appended row's `repaid_usd` is still less than `total_due_usd`, THE SYSTEM SHALL, at the next
scheduled evaluation, append a NEW row for that same `loan_id` with `status: "defaulted"` — never
mutate or delete the existing row (append-only, matching `ledger.js`'s own discipline). THE SYSTEM SHALL
NOT silently continue offering that borrower further loans: REQ-102's no-outstanding-obligation
condition (c) already structurally blocks this, since a `"defaulted"` row IS a currently-open, non-
`"repaid"` obligation. THE SYSTEM SHALL ALSO exclude that borrower from any colony-wide surplus/eligible-
citizen aggregation this codebase performs (today: `anicca-agent-spawn`'s `computeColonySurplusUsd`/
`filterProductiveCitizens`) — realized via a SECOND, lending-owned filter pass,
`excludeDefaultedBorrowers({citizens, loanRows}) → citizens[]` (pure, zero I/O, excludes any citizen with
a currently-`"defaulted"` row as `borrower_id`), composed AFTER `filterProductiveCitizens`'s own output
and BEFORE `computeColonySurplusUsd` runs. This feature does NOT modify `anicca-agent-spawn`'s own
function signature or source — the composition itself is how this feature avoids a tight coupling to a
sibling spec still independently evolving (see Dependencies section; this composition point MUST be
revisited if that spec's registry/join shape changes further).

**Edge Cases**:
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

**Acceptance Criteria**:
- `detectDefaultedLoans({loanRows, nowMs})` is pure, zero I/O, and returns exactly the `loan_id`s whose
  last-appended row is `"active"`, past `due_ms`, and `repaid_usd < total_due_usd` — no others.
- `excludeDefaultedBorrowers({citizens, loanRows})` is pure, zero I/O, excludes exactly the citizens with
  a currently-`"defaulted"` row as `borrower_id`, and passes through unfiltered every other citizen.
- A structural/Tier-0 check confirms neither `detectDefaultedLoans` nor `excludeDefaultedBorrowers` ever
  mutates or deletes an existing `loans.jsonl` row.

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
  file.

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
