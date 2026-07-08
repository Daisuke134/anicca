# Security Hardening Report — franklin-earn-foundation

Money-touching feature (real Solana wallet + earn-ledger classification). The dominant risk class is
CROSS-INSTANCE IDENTITY LEAK (one instance acting on another's wallet/key), per
`feedback_earn_identity_resolve_per_instance_gate_on_anicca_home`.

## Tooling
- `node --test` (unit: parse-pass 5/5, record-swap 8/8, regression identity-guard 12/12)
- hermetic bash integration harness `tests/test_run.sh` + `tests/fake_solana_rpc.mjs` (stubbed franklin-trading on PATH, fake local RPC on a random port, freshly-generated fixture keypairs — never Franklin's real key)
- fresh Opus adversary (2 iterations) — see verification-report.md
- captured artifacts under `verification/security-results/`

## Key Handling / Cross-Instance Identity (the core threat)
- REQ-001: `skills/earn/run.sh` unsets `ANICCA_EVM_PRIVATE_KEY` and resolves THIS instance's EVM key via `lib/resolve-identity.mjs`; fail-closed HALT if none — never falls back to ~/.openclaw/.env's BLOCKRUN_WALLET_KEY (automaton a3cdd4's key).
- FIND-001 (money-safety, FIXED): `skills/earn/sol-trade/run.sh:13` now `unset ANICCA_SOLANA_PRIVATE_KEY` BEFORE OWN_WALLET/CLI_WALLET derivation. Without it, `resolveSolanaSecret` (resolve-identity.mjs:115-119) returns the ambient var first, ignoring ANICCA_HOME → OWN==CLI for ANY instance → guard bypass. Regression-proven closed: `security-results/find001-regression.log` + integration scenario (c).
- The franklin-trading CLI reads ~/.blockrun directly and never needs the unset env var, so unsetting is safe and does not break Franklin's own pass.

## Anti-Human-Touch / No-fake
- record-swap.mjs verifies on-chain (sigStatus confirmed + real usdcDeltaForSig) before recording; a verify-error appends NOTHING to the ledger and run.sh emits a narrate-only `sol-verify-failed` trace line — no fabricated earn on RPC flake (PROP-016).

## Key / Secret Leakage
- wallet-address-solana.mjs never interpolates raw secret material into logs (REQ-006); malformed secret → static warning + exit 0.

## Spec-Gaming / AI-Slop Surface
- sol-trade records are P&L-VISIBILITY only (`external` never true) → cannot manufacture a false GATE-0 "profit" from a same-wallet round-trip (FIND-004 fixed; asserted on a WINNING swap in record-swap.test.mjs + integration (a)).
- Adversary iteration-2 traced the integration call graph and confirmed it exercises the real run.sh→guard→record-swap→solana-verify→record path over a live local RPC (not a tautological stub).

## Summary
The money-safety-critical finding (FIND-001 cross-instance guard bypass) is closed and regression-tested;
the no-fake and no-false-GATE-0 properties hold. No blocking security issue remains. Non-blocking
cosmetic findings (FIND-101/102/103) carry no key/identity/money impact.
