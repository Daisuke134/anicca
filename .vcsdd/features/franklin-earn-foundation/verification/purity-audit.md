# Purity Boundary Audit — franklin-earn-foundation

Maps the pure/effectful boundary for the feature's units (lean; JS/bash).

## Pure units (no I/O, deterministic, unit-tested)
- `skills/earn/sol-trade/lib/parse-pass.mjs::extractLastSignature(stdout)` — pure string→string|null: ANSI-strip + regex matchAll → LAST base58 signature. No I/O, never throws. Covered by parse-pass.test.mjs (5/5).
- `skills/_shared/lib/solana-verify.mjs::usdcDeltaForSig` delta math — the pre/postTokenBalances subtraction is pure given the RPC response; the network fetch is the effectful shell around it (injected `fetchImpl` in tests).

## Effectful units (isolated at the boundary, fail-soft)
- `skills/earn/sol-trade/lib/record-swap.mjs::recordSwap` — effects: RPC read (sigStatus/usdcDeltaForSig, each in its own try/catch → status:"verify-error" instead of throw) + ledger append via record.mjs. Idempotent (sig-keyed alreadyRecordedSig). Never sets external:true. `fetchImpl` injectable → the effect is stubbed in tests (record-swap.test.mjs 8/8) and by fake_solana_rpc.mjs in the integration suite.
- `skills/earn/sol-trade/run.sh` — effects: unset ambient key, identity resolution (node), franklin-trading CLI invocation, trace/ledger append. All fail-soft; the money-safety decision (proceed vs HALT) is a pure comparison of two derived wallet strings.

## Boundary integrity
- No pure unit performs I/O; no effectful unit is invoked from a context that assumes purity.
- The identity guard's decision input (OWN_WALLET vs CLI_WALLET) is derived deterministically from ANICCA_HOME only (ambient key unset first), so the guard is a pure predicate over per-instance state.

## Summary
Pure judgement/parse units (parse-pass, delta math, guard comparison) are separated from effectful
units (RPC, ledger, CLI) with injectable effect seams that the unit + integration tests exercise
hermetically. No purity violation found.
