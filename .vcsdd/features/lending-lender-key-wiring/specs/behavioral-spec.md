# Behavioral Spec — lending-lender-key-wiring (lean VCSDD)

Fix to feature `anicca-agent-lending` (sprint-3, `skills/economy/lending/scripts/wake-gate.mjs`).
No `.vcsdd/features/anicca-agent-lending` directory exists in this repo (`~/anicca`), so this fix is
tracked as its own lean feature, scoped to the exact gap below — it does not re-derive, and must not
duplicate, anicca-agent-lending's own already-converged REQ-101..117/PROP-1xx contract.

## Changelog

- **impl iter1 fixes FIND-001..004** (2026-07-11, impl-review iteration-1): added REQ-119 (lender
  signer-must-equal-recorded-lender guard, dual-layer: `wake-gate.mjs` pre-lock + `defaultDisburse`
  defensive backstop), REQ-120 (bounded reconciliation block-range scan, replaces
  `fromBlock:"earliest"`), REQ-121 (GIG_CHAIN=base + live-facilitator-port operator precondition +
  in-code refusal). See `reviews/impl/iteration-1/output/findings/FIND-001..004.json`.

## Root cause (verified live)

`lending-orchestrator.mjs`'s `defaultDisburse` (line 169-176) calls
`payViaFacilitator({ privateKey: deps.lenderPrivateKey, ... })`, but the ONLY production call site
(`wake-gate.mjs::runWakeGate` → `executeLoanIssuanceAttempt`) never resolved or injected
`deps.lenderPrivateKey`. Every real wake therefore crashed inside `payViaFacilitator` at
`privateKeyToAccount(undefined)` with `TypeError: Cannot read properties of undefined (reading
'slice')`, landing a `disbursement_uncertain` row (`loan_Franklin_1`, confirmed live in
`~/.blockrun/skills/economy/lending/state/loans.jsonl`) and never actually settling on-chain.

A second, related gap: `defaultReconcile` (line 160-167) reads `deps.rpcUrl`, which `wake-gate.mjs`
also never supplied — so even after fixing the key, `resolveStaleProvisioning`'s own reconciliation
lookup (`reconcileProvisionalDisbursement`) would itself throw on `rpcCall(undefined, ...)`, and the
stuck `loan_Franklin_1` row would block that lender's every subsequent wake forever
(`reason:"reconciliation_failed"`).

## Requirements

### REQ-118a: lender EVM key resolution
**EARS**: WHEN `runWakeGate` selects a candidate lender/borrower pair for a real issuance attempt,
THE SYSTEM SHALL resolve the LENDER's own EVM signing key via `resolve-identity.mjs`'s
`resolveEvmPrivateKey({env})` (or an injected `deps.resolveLenderPrivateKey` override) and forward it
as `deps.lenderPrivateKey` into `executeLoanIssuanceAttempt`.

**Edge Cases**:
- Key unresolvable (no env override, no `.automaton/wallet.json` under the lender's own
  `ANICCA_HOME`): refuse with `{status:"refused", reason:"lender_private_key_unresolved"}` BEFORE
  `executeLoanIssuanceAttempt` is ever called — zero ledger rows, zero risk of an undefined key
  reaching `payViaFacilitator`.
- A resolved key must reach `deps.lenderPrivateKey` unchanged (never re-derived/mutated).

**Acceptance Criteria**:
- `wake-gate.test.mjs` fail-closed test: unresolvable key → refused, zero rows.
- `wake-gate.test.mjs` mock-resolve-identity test: resolved key is genuinely forwarded (spy asserts
  the seam was invoked exactly once).

### REQ-118b: rpcUrl wiring for reconciliation
**EARS**: WHEN `runWakeGate` invokes `executeLoanIssuanceAttempt`, THE SYSTEM SHALL supply a real
`deps.rpcUrl` (override, else `env.BASE_RPC_URL`, else `https://mainnet.base.org` — the same default
every other production caller in this repo already uses) so `resolveStaleProvisioning`'s own
reconciliation lookup is genuinely reachable.

**Edge Cases**:
- A lender with a pre-existing stuck `disbursement_uncertain`/`provisioning` row for its own highest
  loan sequence number must have that row reconciled (via a REAL on-chain lookup, never
  `rpcCall(undefined,...)`) on the NEXT wake for that lender, before any new sequence number is
  consumed — never a permanent block.
- Idempotent: reconciliation is read-only (`reconcileProvisionalDisbursement`); a fresh issuance
  attempt afterward must disburse AT MOST once (money-safety — never double-disburse for the same
  stuck row).

**Acceptance Criteria**:
- `wake-gate.test.mjs` recovery test: a stuck row (reproducing the real `loan_Franklin_1` symptom) is
  resolved to `disbursement_failed` (no matching on-chain transfer found — the crash happened before
  any HTTP call), then a FRESH row (next sequence number) reaches `active`, with exactly one real
  `disburse` call for that wake.

### REQ-119: lender signer must equal the ledger's recorded lender (impl-review iteration-1, FIND-001, critical)
**EARS**: WHEN `runWakeGate` has resolved a `lenderPrivateKey` for a selected pair, THE SYSTEM SHALL
derive that key's own on-chain signer address (`privateKeyToAccount(key).address`) and refuse the
attempt (`reason:"lender_not_this_instance"`) BEFORE `executeLoanIssuanceAttempt` is ever called
UNLESS that derived address equals the selected `lenderId`'s own registered `walletAddress.evm`
(case-insensitive). `defaultDisburse` (`lending-orchestrator.mjs`) performs the SAME check
independently, against `loanRow.lender_wallet`, and throws before `payViaFacilitator` is ever called —
a defensive second layer, in case `executeLoanIssuanceAttempt` is ever invoked directly, bypassing
`wake-gate.mjs`.

**Root cause**: `economy/lending/run.sh` is invoked on EACH self-funded citizen's own wake cadence
(mirroring `self/spawn/run.sh`'s shape); `findSelectedPair` scans the FULL shared registry/ledger,
independent of which instance is currently executing. A pre-fix comment in `wake-gate.mjs` ASSERTED
"an instance can only ever sign as itself here" without enforcing it — if Franklin2's own wake
resolves Franklin2's own key while the deterministic pair-selection scan (over the SAME shared
state) selects `{lenderId:"Franklin", ...}`, the disbursement would be signed by Franklin2's own key
for a loan the ledger attributes to Franklin.

**Edge Cases**:
- Franklin2's own wake resolves Franklin2's own key, `findSelectedPair` selects Franklin as lender →
  refused `lender_not_this_instance`, zero rows, `disburse` never called.
- The resolved key's derived address genuinely matches the selected lenderId's own registered wallet
  → proceeds exactly as before this fix (no observable behavior change for the correct case).

**Acceptance Criteria**:
- `wake-gate.test.mjs`: Franklin2-resolves-Franklin2's-key-while-Franklin-selected → refused, no
  ledger rows, `disburse` never invoked.
- `wake-gate.test.mjs`: matching signer/wallet → proceeds to a genuine `active` outcome.
- `lending-orchestrator.test.mjs`: the REAL `defaultDisburse` (not the `deps.disburse` test stub)
  throws `lender_signer_mismatch` before any network call when `deps.lenderPrivateKey`'s derived
  address does not match `loanRow.lender_wallet`.

### REQ-120: bounded reconciliation block-range scan (impl-review iteration-1, FIND-002, critical)
**EARS**: WHEN `executeLoanIssuanceAttempt`'s reconciliation step (`defaultReconcile`) scans on-chain
Transfer logs for a stuck row, THE SYSTEM SHALL bound the `eth_getLogs` request to a fixed block span
(`fromBlock = latest - LENDING_RECONCILE_LOOKBACK_BLOCKS`, `toBlock = latest`, both a single
`eth_blockNumber` snapshot) — NEVER `fromBlock:"earliest"` against a real provider.

**Root cause**: this fix's own `deps.rpcUrl` wiring (REQ-118b) makes `defaultReconcile`'s
pre-existing `fromBlock: deps.reconcileFromBlock || "earliest"` reachable against a REAL provider
(`https://mainnet.base.org`) for the first time. This codebase's own prior FIND-702 fix
(`skills/self/founder-loop/record-earn.mjs`) already discovered — against this exact RPC — that
public JSON-RPC providers reject/truncate `eth_getLogs` calls spanning too many blocks (documented
range there: "commonly 2,000-10,000 blocks"). An unbounded "earliest" scan would make
`reconciliationResult` throw, surfacing as `reason:"reconciliation_failed"` on every subsequent wake
— the exact "permanently blocks the lender" failure mode REQ-118b's own acceptance criteria forbid.

**Edge Cases**:
- Lookback default: 9000 blocks (matches record-earn.mjs's own proven-safe `MAX_SPAN` for this exact
  RPC, ~5h at Base's ~2s/block). Overridable via `LENDING_RECONCILE_LOOKBACK_BLOCKS` — an operator
  with a less-frequent wake cadence than the lookback window risks missing a genuine on-chain
  reconciliation match for a row stuck longer than that window; widening the lookback must stay
  within whatever range limit the real provider actually enforces (never re-introduce "earliest").
- The real production `loan_Franklin_1` row's own crash happened BEFORE any facilitator/on-chain call
  ever went out (confirmed: `privateKeyToAccount(undefined)` throws inside `signAuthorization`,
  before any HTTP fetch) — so its own reconciliation genuinely has nothing to find on-chain
  regardless of window size; this bound does not change that row's own correct
  `disbursement_failed` outcome.

**Acceptance Criteria**:
- `wake-gate.test.mjs`'s REQ-118 recovery fixture's mock RPC genuinely REJECTS `fromBlock:"earliest"`
  or any span wider than a real provider's own limit, and the fix's own bounded call still succeeds.

### REQ-121: mainnet chain + facilitator preconditions (impl-review iteration-1, FIND-003, medium)
**EARS**: WHEN `defaultDisburse` is about to settle real lending money, THE SYSTEM SHALL refuse
(`lending_chain_not_mainnet`) unless `GIG_CHAIN` (or the caller's `deps.gigChain` test override)
resolves to exactly `"base"` — `escrow.mjs`'s own `GIG_CHAIN` constant defaults to testnet
(`base-sepolia`) when unset, and that default must never be silently treated as "go ahead" for a real
lending disbursement.

**Operator precondition** (verified live 2026-07-11): the colony's live x402 facilitator process runs
on port **8405** with `GIG_CHAIN=base` (confirmed via `lsof -iTCP:8405` and
`~/.anicca-signing/gig-board/.env`). `skills/economy/gig/WITNESS-RUNBOOK.md`'s own §"go live"
recommendation of a SEPARATE port 8407 facilitator was never actually adopted in production — that
section is stale; going live for lending means the lender's own per-instance env has
`GIG_CHAIN=base` and `GIG_FACILITATOR_URL=http://127.0.0.1:8405` (both already set for the
`anicca-a3cdd4`/coordinator body), matching `defaultDisburse`'s own existing `8405` fallback default.

**Edge Cases**:
- `GIG_CHAIN` unset or `"base-sepolia"` → refused `lending_chain_not_mainnet`, even when the signer
  genuinely matches `loanRow.lender_wallet` (REQ-119's guard passing does not bypass this one).
- A test needing to exercise `defaultDisburse`'s own real control flow without settling real money
  supplies `deps.gigChain`/`deps.allowNonMainnetChain:true` explicitly — production never sets either.

**Acceptance Criteria**:
- `lending-orchestrator.test.mjs`: the REAL `defaultDisburse`, GIG_CHAIN unset/testnet, genuinely
  matching signer → throws `lending_chain_not_mainnet` before any network call.
- `lending-orchestrator.test.mjs`: matching signer + `GIG_CHAIN=base` → both defensive guards pass
  (proven by a DIFFERENT, network-layer error surfacing once `payViaFacilitator` is genuinely
  reached, never either guard's own error).

## Non-functional requirements

- **Money-safety**: `deps.lenderPrivateKey` is never logged, printed, or persisted to any ledger/trace
  file — it only ever flows in-memory from `resolveEvmPrivateKey`/`deps.resolveLenderPrivateKey` into
  `executeLoanIssuanceAttempt`'s own `deps`, and into `lending-signer.mjs::deriveSignerAddress` (which
  returns only the DERIVED public address, never the key itself). Verified: `git diff` contains no
  `console.log`/`JSON.stringify` of any private-key-shaped value, and `runWakeGate`'s own returned
  `result` object (the ONLY thing the CLI entrypoint logs) never includes it.
- **Fail-closed**: an unresolvable key must refuse, never proceed with `undefined`; a resolved key
  whose derived signer address does not match the ledger's own recorded lender must refuse
  (REQ-119), never sign; a non-mainnet/unset `GIG_CHAIN` must refuse to disburse (REQ-121), never
  silently settle against testnet.
- **Scope discipline**: the $0.02 cold-start disbursement cap (`lending-gate.mjs::computeLoanCapUsd`)
  is untouched by this fix.

## Purity boundary

- **Pure core**: unchanged — `lending-gate.mjs` (eligibility/sizing/kill-switches),
  `lending-orchestrator.mjs`'s own sequencing (already converged, sprint-2, not modified). New this
  fix: `lending-signer.mjs::deriveSignerAddress`/`addressesEqual` — pure, deterministic (viem's own
  `privateKeyToAccount`), no I/O.
- **Effectful shell** (this fix's own scope): `wake-gate.mjs::runWakeGate`'s new
  `resolveLenderPrivateKey({env})` call, `rpcUrl` resolution, and the new REQ-119 signer-match guard
  (a plain in-memory comparison, no I/O of its own) — the actual effectful RPC/facilitator calls
  remain entirely inside `lending-orchestrator.mjs`'s already-hardened `defaultReconcile`/
  `defaultDisburse`, which this fix extends with: a bounded (never `"earliest"`)
  `eth_blockNumber`+`eth_getLogs` reconciliation scan (REQ-120), and the same REQ-119 signer-match
  guard plus a REQ-121 `GIG_CHAIN=="base"` guard, both evaluated BEFORE `payViaFacilitator` is called.
