# Behavioral Spec — lending-lender-key-wiring (lean VCSDD)

Fix to feature `anicca-agent-lending` (sprint-3, `skills/economy/lending/scripts/wake-gate.mjs`).
No `.vcsdd/features/anicca-agent-lending` directory exists in this repo (`~/anicca`), so this fix is
tracked as its own lean feature, scoped to the exact gap below — it does not re-derive, and must not
duplicate, anicca-agent-lending's own already-converged REQ-101..117/PROP-1xx contract.

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

## Non-functional requirements

- **Money-safety**: `deps.lenderPrivateKey` is never logged, printed, or persisted to any ledger/trace
  file — it only ever flows in-memory from `resolveEvmPrivateKey`/`deps.resolveLenderPrivateKey` into
  `executeLoanIssuanceAttempt`'s own `deps`. Verified: `git diff` contains no
  `console.log`/`JSON.stringify` of any private-key-shaped value, and `runWakeGate`'s own returned
  `result` object (the ONLY thing the CLI entrypoint logs) never includes it.
- **Fail-closed**: an unresolvable key must refuse, never proceed with `undefined`.
- **Scope discipline**: the $0.02 cold-start disbursement cap (`lending-gate.mjs::computeLoanCapUsd`)
  is untouched by this fix.

## Purity boundary

- **Pure core**: unchanged — `lending-gate.mjs` (eligibility/sizing/kill-switches),
  `lending-orchestrator.mjs`'s own sequencing (already converged, sprint-2, not modified).
- **Effectful shell** (this fix's own scope): `wake-gate.mjs::runWakeGate`'s new
  `resolveLenderPrivateKey({env})` call and `rpcUrl` resolution — both plain reads (env/file), no
  network I/O of their own; the actual effectful RPC/facilitator calls remain entirely inside
  `lending-orchestrator.mjs`'s already-hardened `defaultReconcile`/`defaultDisburse`.
