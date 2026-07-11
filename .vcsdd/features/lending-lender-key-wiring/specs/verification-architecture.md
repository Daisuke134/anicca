# Verification Architecture — lending-lender-key-wiring (lean VCSDD)

## Purity Boundary Map
- **Pure Core**: `lending-gate.mjs`, `lending-orchestrator.mjs`'s own sequencing (unchanged, sprint-2
  converged) — deterministic, already formally verified under `anicca-agent-lending`.
- **Effectful Shell**: `wake-gate.mjs::runWakeGate`'s new key/rpcUrl resolution (env/file reads) and
  the pre-existing `defaultDisburse`/`defaultReconcile` (network I/O, unchanged this fix).

## Proof Obligations
| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-118a | Unresolvable lender key → refused, zero rows, zero risk of `undefined` reaching `payViaFacilitator` | 1 | true | node:test |
| PROP-118b | Resolved key genuinely forwarded into `executeLoanIssuanceAttempt`'s own deps | 1 | true | node:test (spy) |
| PROP-118c | A stuck `disbursement_uncertain` row is reconciled via a real `rpcUrl`, never permanently blocks the lender, never double-disburses | 1 | true | node:test (mock JSON-RPC server) |
| PROP-118d | No regression: all 5 pre-existing `wake-gate.test.mjs` fixtures + full `anicca-agent-lending` suite (134 tests) still pass | 0 | true | node:test |
| PROP-118e | No key material logged/persisted | 0 | true | manual grep of diff + `result` return shape |

## Verification Strategy
- **Tier 0**: money-safety (no logging) — verified by grep of the diff and of `runWakeGate`'s own
  returned/logged shape (no code path constructs a value containing the key).
- **Tier 1**: property/example tests via `node:test`, mirroring the existing `wake-gate.test.mjs`
  conventions exactly (tmp-dir fixtures, mock JSON-RPC server reused verbatim from
  `lending-verify.test.mjs`'s own `startMockRpc` precedent) — RED (3 new tests fail against the
  pre-fix code, captured via `git stash`) then GREEN (8/8 pass).
- **Tier 2/3**: not applicable — this is a narrow wiring fix over already-hardened (sprint-2/3,
  Phase-5-complete) pure functions; no new arithmetic/decision logic is introduced.
