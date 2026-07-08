# Purity Boundary Audit — anicca-agent-lending (Phase 5, Formal Hardening)

## Declared Boundaries

Per `specs/verification-architecture.md`'s own "Purity Boundary Map" (lines 9-40):

| File | Declared purity |
|---|---|
| `lending-gate.mjs` | Pure Core — every exported function, zero I/O |
| `lending-path.mjs` | Pure Core (constant only) — `LOANS_LEDGER_PATH`, computed once at module load, no runtime logic |
| `gojo-read.mjs` | Effectful Shell (new, read-only) — `fs.readFileSync` only, never writes |
| `lending-verify.mjs` | Effectful Shell (new) — JSON-RPC `fetch` calls only, no filesystem access |

`contracts/sprint-1.md`'s own CRIT-001/CRIT-009 criteria (already adversary-PASSed) restate this exact
same boundary as a binding sprint-1 acceptance criterion.

## Observed Boundaries (this session's own independent re-verification)

Ran directly against the delivered source (not re-trusting Phase 3's own prior confirmation):

```
cd ~/anicca/skills/economy/lending/lib
grep -n -F "fs."                                    *.mjs   -> 1 hit:  gojo-read.mjs:10 (fs.readFileSync)
grep -n -F "fetch("                                 *.mjs   -> 1 hit:  lending-verify.mjs:17 (inside rpcCall())
grep -n -F "Date.now()"                             *.mjs   -> 0 hits
grep -n "^import"                                   *.mjs   -> 4 hits: gojo-read (fs), lending-gate (isSelfFunded only),
                                                                        lending-path (path, url); lending-verify has NO import
                                                                        statements at all (uses global fetch/Buffer/BigInt)
grep -n -F -e "writeFile" -e "appendFile" -e "unlink" *.mjs  -> 0 hits
```

- **`lending-gate.mjs`**: confirmed its ONLY import is `isSelfFunded` from `../../../_shared/lib/is-self-funded.mjs`
  (itself pure, unmodified — see below). Every `nowMs` a function needs
  (`computeRecentDefaultLossUsd`, `sumRecentGojoGiftsUsd`, `detectDefaultedLoans`) is an explicit
  parameter; zero internal `Date.now()` reads anywhere in the file. Zero `fs`/`fetch`/network calls.
  **Matches the declared boundary exactly — genuinely 100% pure.**
- **`lending-path.mjs`**: exports exactly one runtime value, `LOANS_LEDGER_PATH`, computed via
  `path.join(__dirname, "..", "state", "loans.jsonl")` at module load — zero function exports, zero
  runtime logic beyond that one `path.join` call. **Matches the declared boundary — a pure constant.**
- **`gojo-read.mjs`**: its only side-effecting call is `fs.readFileSync` (confirmed: zero
  `fs.writeFileSync`/`fs.appendFileSync`/`fs.unlinkSync` anywhere in the file); `ENOENT` is the only
  caught error path (returns `[]`), everything else rethrows. **Matches the declared boundary — genuinely
  read-only.**
- **`lending-verify.mjs`**: every network call (`eth_getTransactionReceipt`, `eth_getBlockByNumber`,
  `eth_getLogs`) is routed through the single local `rpcCall()` helper — confirmed no other inline
  `fetch` call exists in the file. Zero `fs` access anywhere in this file. **Matches the declared
  boundary — network-only, single narrow chokepoint.**

### Reused-unmodified dependency (out of this diff, verified anyway for completeness)

- `~/anicca/skills/_shared/lib/is-self-funded.mjs::isSelfFunded` — PROP-111b's own Tier-0 obligation
  (structural diff against the pre-modification version) already covers byte-identity; this session's
  purity audit independently confirms `lending-gate.mjs` imports this function and calls it without
  wrapping/modifying its behavior.
- `~/anicca/skills/economy/gig/lib/lock.mjs` (`withGigLock`/`isLockStale`) and
  `~/anicca/skills/economy/gig/lib/escrow.mjs` (`payViaFacilitator`) are named in the Purity Boundary Map
  as reused-unmodified effectful shells this feature's (not-yet-built) orchestrator will call — this
  session confirms neither file appears anywhere in this feature's own diff (`git log --oneline --
  skills/economy/lending/` touches only the 4 delivered modules + their tests + this session's new
  property-test file).

## Summary

The four-module purity boundary this sprint declared holds **exactly** as stated, independently
re-verified by direct source grep this session (not merely re-trusting Phase 3's prior confirmation):
`lending-gate.mjs` is fully pure; `lending-path.mjs` is a pure constant; `gojo-read.mjs` and
`lending-verify.mjs` are the only two effectful modules, each narrowly scoped to exactly one purpose
(read-only fs vs. RPC-only network), matching `contracts/sprint-1.md`'s own CRIT-001/CRIT-009 criteria.
No residual risk found in the purity boundary itself; the only residual risks are the two LOW-severity,
non-purity-related observations already recorded in `security-report.md`.

## Sprint-2 Addendum (Phase 5, `lending-orchestrator.mjs`)

### Declared Boundaries

Per `specs/verification-architecture.md`'s Purity Boundary Map rows 41-42 (sprint-2 additions):
`lending-orchestrator.mjs` is the **Effectful Shell (new, sprint-2)** wiring REQ-101/102/104/105/106/
112/114's own pure/narrow `lending-gate.mjs` functions plus the two already-hardened effectful modules
(`lock.mjs::withGigLock`, `escrow.mjs::payViaFacilitator`) into one real issuance/servicing flow —
declared to contain "no decision/judgment logic of its own" (PROP-115b/PROP-116b).

### Observed Boundaries (this session's own independent re-verification)

```
cd ~/anicca/skills/economy/lending/lib
git status --short .                                          -> clean (zero uncommitted changes)
git log --oneline -- lending-gate.mjs lending-verify.mjs \
  lending-path.mjs gojo-read.mjs                                -> newest commit 46eb1e1 (sprint-1 FIND-901/902
                                                                     fix) -- no sprint-2 commit touches any of
                                                                     these four files; confirmed byte-identical
                                                                     to sprint-1's own delivered state
git log --oneline -- lending-orchestrator.mjs                  -> 1b1fae2 (Phase 2b GREEN), 3151f13 (Phase 2c
                                                                     refactor) -- entirely new file, isolated
                                                                     from the four pure/narrow modules' own
                                                                     history
```

- **Imports confirmed** (source read, `lending-orchestrator.mjs` lines 10-35): `node:fs`/`node:path`
  (its own local ledger I/O), 17 named pure functions + `LOAN_REPAYMENT_WINDOW_DAYS` from
  `./lending-gate.mjs`, `verifyRepayment`/`reconcileProvisionalDisbursement` from
  `./lending-verify.mjs`, `LOANS_LEDGER_PATH` from `./lending-path.mjs`, `withGigLock` from
  `../../gig/lib/lock.mjs`, `payViaFacilitator` from `../../gig/lib/escrow.mjs`. Zero other imports —
  confirms it wires EXACTLY the modules the Purity Boundary Map declares, nothing else.
- **No decision logic of its own**: `lending-orchestrator.test.mjs`'s own `PROP-115b/PROP-116b
  structural` test (already GREEN, re-read this session) asserts no relational/threshold comparison
  against a `balanceUsd`/`surplusUsd`/`defaultRateUsd`/`repaymentRate` value exists anywhere in the
  file's own source outside a call into an already-exported `lending-gate.mjs` function, and no
  LLM/prompt reference. This session's own manual read confirms every branch point in
  `lending-orchestrator.mjs` (kill-switch checks, eligibility checks, sizing decisions) is a direct
  `if (!result.eligible)`/`if (killSwitch.paused)`-style consumption of an already-computed pure
  function's own return value — never a new arithmetic/boolean judgment invented in this file.
- **Effectful surface is exactly**: local `loans.jsonl` read/append (via `fs.readFileSync`/
  `fs.mkdirSync`/`fs.appendFileSync`, paths always derived from `deps.ledgerFile || LOANS_LEDGER_PATH`,
  confirmed zero hardcoded/externally-derived path segments — see `security-report.md`'s own Sprint-2
  Addendum grep sweep), `withGigLock` acquisition/release (three distinct key families:
  `` `loan_${lenderId}` ``/`` `loan_borrower_${borrowerId}` `` for issuance,
  `` `loan_${loanId}` `` for servicing — confirmed structurally disjoint per the already-GREEN
  `CRIT-204 structural` test), and `payViaFacilitator`/`reconcileProvisionalDisbursement`/
  `verifyRepayment` invocations (always via the module's own `deps` seam, defaulting to the REAL
  functions in production). **Matches the declared boundary exactly.**

### Summary

The sprint-2 purity boundary holds exactly as declared: `lending-orchestrator.mjs` is a genuine
effectful shell wiring sprint-1's untouched pure core (`lending-gate.mjs`) and narrow effectful modules
(`lending-verify.mjs`/`gojo-read.mjs`/`lending-path.mjs`, all confirmed byte-identical/unmodified this
session via `git log`) plus the two pre-existing hardened effectful modules (`lock.mjs`/`escrow.mjs`),
with zero decision/judgment logic invented in the new file itself. No purity-boundary drift found across
either sprint.

## Sprint-3 Addendum (Phase 5, `run.sh` + `scripts/wake-gate.mjs`)

### Declared Boundaries

Per `specs/verification-architecture.md`'s Purity Boundary Map row 43 (sprint-3 addition):
`run.sh` + `scripts/wake-gate.mjs` are declared **Effectful Shell (new, sprint-3)** — the autonomous
daemon-wake entry point making REQ-115's `executeLoanIssuanceAttempt`/REQ-116's
`executeDefaultDetectionSweep` genuinely reachable, containing "no eligibility/sizing/servicing decision
logic of its own anywhere" (`run.sh`) and delegating "every decision" to `lending-gate.mjs`'s/
`lending-orchestrator.mjs`'s own already-hardened functions via "a single, already-computed
boolean/number combined via a single `&&`/`>`" (`scripts/wake-gate.mjs`'s own header comment,
independently confirmed this session).

### Observed Boundaries (this session's own independent re-verification)

```
cd ~/anicca/skills/economy/lending
grep -n "fs\."                          scripts/wake-gate.mjs  -> 1 hit:  line 40 (fs.readFileSync only)
grep -n "fetch("                        scripts/wake-gate.mjs run.sh  -> 0 hits
grep -n "eval(\|child_process\|exec("   scripts/wake-gate.mjs  -> 0 hits
grep -n "ANICCA_ARGS"                   scripts/wake-gate.mjs run.sh  -> 0 hits
git show ccef6ee480add1f7e3d670fab53a12fbfb07339e --stat        -> 5 files changed (2 new test files,
                                                                     run.sh, scripts/wake-gate.mjs,
                                                                     skills/registry.json); zero files
                                                                     under skills/self/spawn/
```

- **`run.sh`**: confirmed a thin `set -euo pipefail` bash wrapper — `SKILL_DIR` resolution, a `--help`
  short-circuit, a `node` presence check, best-effort env sourcing under `set -a`/`set +a`, and a single
  final `exec "$NODE" "$SKILL_DIR/scripts/wake-gate.mjs" "$@"` line. Zero eligibility/sizing/servicing
  logic of its own (independently re-confirmed via the SAME grep the structural test itself runs:
  `balanceUsd|surplusUsd|isBorrowerEligible|computeLenderAvailableUsd|decideLoan` → 0 hits in `run.sh`).
  **Matches the declared boundary exactly — a pure hand-off shell, no logic of its own.**
- **`scripts/wake-gate.mjs`**: its own I/O surface is exactly `fs.readFileSync` (`readCitizensRegistry`,
  line 40, read-only) plus the reused effectful primitives it imports and calls
  (`readChildren`/`readGojoLogRows`/`usdcBalance`/`ensureCitizensRegistry`) plus its two calls into
  `executeLoanIssuanceAttempt`/`executeDefaultDetectionSweep` (both already-classified Effectful Shells,
  sprint-2, unmodified). Zero `fs` write/append/unlink calls of its own; zero direct `fetch`/network calls
  of its own (`usdcBalance`'s own network call is that already-hardened, reused module's own concern, not
  this file's surface).
- **The ONE comparison this file performs** (`findSelectedPair`, line 88:
  `lenderAvailableUsd > 0 && borrowerEligibility.eligible === true`) is exactly the single, plain `&&`
  sequencing combinator `specs/verification-architecture.md` (lines 560-561) explicitly sanctions over
  TWO already-computed, independent pure-function outputs (`computeLenderAvailableUsd`/
  `isBorrowerEligible`, both `lending-gate.mjs`, unmodified) — confirmed by direct read this session that
  neither function's own internal arithmetic/boolean logic is re-derived or duplicated anywhere in
  `wake-gate.mjs`. This is the identical "pure sequencing, never re-deriving" discipline sprint-2's own
  purity audit already established for `lending-orchestrator.mjs`, extended here one level up, to
  candidate DISCOVERY (which pair to try) rather than candidate EXECUTION (whether that pair's loan
  proceeds).
- **`ANICCA_ARGS`**: confirmed zero reads anywhere in either file — this entry point genuinely has no
  model-driven decision lever, matching REQ-103's bookkeeping-only discipline extended to this new slot.
- **No modification to `anicca-agent-spawn`'s own files**: independently confirmed via
  `git show ccef6ee --stat` and `git log --oneline -- skills/self/spawn/` (this session) — the sole
  sprint-3 commit touches none of that sibling feature's files; `scripts/wake-gate.mjs` imports
  `_shared/lib/usdc.mjs::usdcBalance` (colony-wide-shared, not spawn-owned) rather than
  `self/spawn/scripts/wake-gate.mjs`'s own private `defaultFetchEvmBalanceUsd` helper, confirmed by this
  session's own read of both files' import lists.
- **Matches the declared boundary exactly** — a genuine Effectful Shell that reads real state and
  sequences already-hardened modules via a single plain `&&`, inventing no new judgment logic of its own,
  and touching no sibling feature's own files.

### Summary

The sprint-3 purity boundary holds exactly as declared: `run.sh` is a pure hand-off shell with zero logic
of its own, and `scripts/wake-gate.mjs` is a genuine effectful shell composing already-hardened pure/
effectful modules via one plain sequencing combinator, never re-deriving their internal logic and never
reaching into `anicca-agent-spawn`'s own files. No purity-boundary drift found across any of the three
sprints.
