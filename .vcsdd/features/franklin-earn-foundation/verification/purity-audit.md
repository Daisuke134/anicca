# Purity Boundary Audit — franklin-earn-foundation

Maps the pure/effectful boundary for the feature's units (lean; JS/bash). Money-touching, so the
purity-critical unit is the identity-guard decision (must be a pure function of per-instance state).

## Declared Boundaries
The spec declares these pure vs effectful units:
- PURE: `parse-pass.mjs::extractLastSignature(stdout)` — string→string|null, no I/O, never throws.
- PURE: the identity-guard decision — a comparison of two derived wallet strings (OWN_WALLET vs CLI_WALLET), each derived deterministically from ANICCA_HOME only.
- PURE: `solana-verify.mjs` delta arithmetic — pre/postTokenBalances subtraction, given the RPC response.
- EFFECTFUL (isolated at the boundary): `record-swap.mjs::recordSwap` (RPC read + ledger append, injectable `fetchImpl`), `run.sh` (unset key, node identity resolution, franklin-trading CLI, trace/ledger append).

## Observed Boundaries
Verified by reading the implementation + tests:
- `parse-pass.mjs`: no `import`ed I/O, no fs/net; pure regex over the argument. Confirmed by parse-pass.test.mjs (5/5) using only in-memory strings.
- identity guard (`run.sh`): OWN/CLI wallets are derived via `wallet-address-solana.mjs` from ANICCA_HOME; ambient `ANICCA_SOLANA_PRIVATE_KEY` is `unset` (run.sh:13) BEFORE derivation, so no hidden env input leaks into the decision → the predicate is pure over per-instance state. Integration (b)(c) confirm.
- `record-swap.mjs`: the two effectful RPC calls are each wrapped in try/catch and return `status:"verify-error"` instead of throwing; the ledger append is idempotent (sig-keyed). The effect seam (`fetchImpl`) is injected in record-swap.test.mjs (8/8) and stubbed by `fake_solana_rpc.mjs` in the integration suite — the effectful unit is never invoked from a context assuming purity.
- No pure unit performs I/O; no effectful unit is called from a purity-assuming path.

## Summary
Pure judgement/parse units (parse-pass, delta math, the guard comparison) are cleanly separated from
effectful units (RPC, ledger, CLI) via injectable effect seams that the unit + integration tests
exercise hermetically. No purity-boundary violation found.
