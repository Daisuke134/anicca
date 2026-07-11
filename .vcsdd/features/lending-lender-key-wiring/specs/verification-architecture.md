# Verification Architecture — lending-lender-key-wiring (lean VCSDD)

## Changelog
- **impl iter3 fixes FIND-201/202** (2026-07-11): added PROP-122a/b (REQ-122 exact-value match),
  PROP-123a/b/c (REQ-123 facilitator mainnet preflight), and PROP-124a/b (REQ-124, FIND-201's new
  cross-loan tx_hash-replay guard) to the Proof Obligations table below — all three were introduced in
  behavioral-spec.md by impl-review iteration-2/3 but never previously reflected here (FIND-202: a real
  drift between the two governing spec documents). Verification Strategy paragraph's test count updated
  accordingly. See `reviews/impl/iteration-3/output/findings/FIND-201..202.json`.

## Purity Boundary Map
- **Pure Core**: `lending-gate.mjs`, `lending-orchestrator.mjs`'s own sequencing (unchanged, sprint-2
  converged) — deterministic, already formally verified under `anicca-agent-lending`. New this fix:
  `lending-signer.mjs` (`deriveSignerAddress`/`addressesEqual`) — pure, deterministic, no I/O.
- **Effectful Shell**: `wake-gate.mjs::runWakeGate`'s new key/rpcUrl resolution (env/file reads) and
  its new REQ-119 signer-match guard (in-memory comparison, no I/O), plus `defaultDisburse`/
  `defaultReconcile` (network I/O) — extended this fix (impl-review iteration-1) with a bounded
  `eth_blockNumber`+`eth_getLogs` scan (REQ-120) and dual REQ-119/REQ-121 defensive guards evaluated
  before `payViaFacilitator`.

## Proof Obligations
| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-118a | Unresolvable lender key → refused, zero rows, zero risk of `undefined` reaching `payViaFacilitator` | 1 | true | node:test |
| PROP-118b | Resolved key genuinely forwarded into `executeLoanIssuanceAttempt`'s own deps | 1 | true | node:test (spy) |
| PROP-118c | A stuck `disbursement_uncertain` row is reconciled via a real `rpcUrl`, never permanently blocks the lender, never double-disburses | 1 | true | node:test (mock JSON-RPC server, RANGE-RESTRICTING as of impl-review iteration-1 — see PROP-120a) |
| PROP-118d | No regression: all pre-existing `wake-gate.test.mjs` fixtures + full lending suite (139 tests as of impl-review iteration-1) still pass | 0 | true | node:test |
| PROP-118e | No key material logged/persisted | 0 | true | manual grep of diff + `result` return shape |
| PROP-119a | Resolved key's derived signer address ≠ selected lenderId's own registered wallet → `wake-gate.mjs` refuses `lender_not_this_instance` BEFORE `executeLoanIssuanceAttempt`, zero rows, `disburse` never called | 1 | true | node:test (Franklin2-selects-Franklin fixture) |
| PROP-119b | Matching signer/wallet → proceeds exactly as before (no regression to the correct case) | 1 | true | node:test |
| PROP-119c | `defaultDisburse`'s own independent signer-match check throws `lender_signer_mismatch` BEFORE `payViaFacilitator`, for a mismatch reaching it directly (bypassing `wake-gate.mjs`) | 1 | true | node:test (real `defaultDisburse`, unreachable `facilitatorUrl` proves no network call preceded the throw) |
| PROP-120a | `defaultReconcile` never sends `fromBlock:"earliest"`; a range-restricting mock RPC (rejects any span > a real provider's own limit) still lets the fix's own bounded call succeed | 1 | true | node:test (mock RPC genuinely inspects `fromBlock`/`toBlock`, throws on an over-wide/`"earliest"` request) |
| PROP-121a | `GIG_CHAIN` unset/non-`"base"` → `defaultDisburse` refuses `lending_chain_not_mainnet` BEFORE `payViaFacilitator`, even with a genuinely matching signer | 1 | true | node:test |
| PROP-121b | Matching signer + `GIG_CHAIN=="base"` → both REQ-119/REQ-121 guards pass, proven by a DIFFERENT (network-layer) error surfacing once `payViaFacilitator` is genuinely reached | 1 | true | node:test |
| PROP-122a | REQ-122: an unrelated-value Transfer between the correct lender/borrower wallets is rejected (`found:false`), even though address+topics match | 1 | true | node:test (`lending-verify.test.mjs`, FIND-101 rejection case) |
| PROP-122b | REQ-122: an exact-value Transfer is matched even when an unrelated-value Transfer between the same two wallets also appears in the same window | 1 | true | node:test (`lending-verify.test.mjs`, FIND-101 same-window case) |
| PROP-123a | REQ-123: a `/supported` response advertising ONLY a non-mainnet network → `defaultDisburse` throws `facilitator_not_mainnet` before any `payViaFacilitator` call | 1 | true | node:test (`lending-orchestrator.test.mjs`, real `defaultDisburse`) |
| PROP-123b | REQ-123: an unreachable/malformed `/supported` fetch fails closed → throws `facilitator_not_mainnet`, never an implicit pass | 1 | true | node:test (`lending-orchestrator.test.mjs`) |
| PROP-123c | REQ-123: a `/supported` response advertising `eip155:8453`, combined with a matching signer + `GIG_CHAIN=base`, passes all three guards — proven by a DIFFERENT, network-layer error surfacing once `payViaFacilitator` is genuinely reached | 1 | true | node:test (`lending-orchestrator.test.mjs`) |
| PROP-124a | REQ-124 (FIND-201): a wallet-pair+exact-value-matching Transfer whose `tx_hash` is already recorded against a DIFFERENT `loan_id` in `loanRows` is rejected (`found:false`) — never counted as this loan's own disbursement | 1 | true | node:test (`lending-verify.test.mjs`, FIND-201 cross-loan replay case) |
| PROP-124b | REQ-124: `resolveStaleProvisioning` forwards the FULL current `loanRows` ledger (not just the stale row alone) into `reconcile({loanRow, loanRows})`, and a genuinely new `tx_hash` (not present in `loanRows`) is still matched normally (positive control) | 1 | true | node:test (`lending-verify.test.mjs` positive control + `lending-orchestrator.test.mjs` wiring assertion) |

## Verification Strategy
- **Tier 0**: money-safety (no logging) — verified by grep of the diff and of `runWakeGate`'s own
  returned/logged shape (no code path constructs a value containing the key); `lending-signer.mjs`
  returns only the derived PUBLIC address, never the key.
- **Tier 1**: property/example tests via `node:test`, mirroring the existing `wake-gate.test.mjs`/
  `lending-orchestrator.test.mjs` conventions exactly (tmp-dir fixtures, mock JSON-RPC server reused
  verbatim from `lending-verify.test.mjs`'s own `startMockRpc` precedent, now range-inspecting per
  FIND-004). Impl-review iteration-1 fix: 5 new tests (2 in `wake-gate.test.mjs`, 3 in
  `lending-orchestrator.test.mjs`) added GREEN directly against the fix (this is a defect-response
  iteration over already-GREEN sprint-1 code, not a fresh RED→GREEN cycle — each new test was run
  against the fixed code and independently checked to fail if its own corresponding guard is removed,
  in lieu of a formal `git stash` RED capture for this narrow iteration). Impl-review iteration-2 fix
  (FIND-101/102/103, PROP-122a/b, PROP-123a/b/c): 6 additional new tests across
  `lending-verify.test.mjs`/`lending-orchestrator.test.mjs`, same GREEN-directly-against-the-fix
  convention. Impl-review iteration-3 fix (FIND-201, PROP-124a/b): 3 additional new tests — 2 in
  `lending-verify.test.mjs` (cross-loan replay rejection + genuinely-new-tx_hash positive control) and 1
  in `lending-orchestrator.test.mjs` (asserts `resolveStaleProvisioning` forwards the full `loanRows`
  ledger into `reconcile()`), same GREEN-directly-against-the-fix convention. Running total: 14 new
  tests across the three impl-review iterations, all currently passing alongside the full pre-existing
  lending suite (148 tests as of impl-review iteration-3).
- **Tier 2/3**: not applicable — this is a narrow wiring fix over already-hardened (sprint-2/3,
  Phase-5-complete) pure functions; no new arithmetic/decision logic is introduced. `lending-signer.mjs`
  is a thin wrapper over viem's own already-audited `privateKeyToAccount`, not new cryptography.
