# Purity Boundary Audit — franklin-loop-revival (Phase 5)

## Declared Boundaries
- Pure Core: `runtime/loop/address-classify.mjs` (`isEvmAddress`/`isSolanaAddress`/`classifyAddress`, zero I/O).
- Effectful Shell: `runtime/wallet-address-solana.mjs` (reads `.solana-session`), `runtime/loop/balance.mjs` Solana branch (network read via `solana-verify.mjs::usdcBalance`), `runtime/anicca-daemon.sh` wiring, `ai.anicca.franklin-loop.plist` config.

## Observed Boundaries (this session's own independent re-verification)
- `address-classify.mjs`: confirmed pure predicates, no imports with side effects, unit-tested (`address-classify.test.mjs`).
- `balance.mjs`: Solana branch delegates to the reused `solana-verify.mjs::usdcBalance` with no `opts.mint` override and no reimplemented RPC parsing; EVM path byte-for-byte unchanged (adversary-verified).
- `wallet-address-solana.mjs`: single effect = read secret file → derive pubkey; single output = public address; no other I/O.

## Summary
Purity boundary respected: one new pure module + isolated effectful shells that reuse already-hardened primitives. No pure/effectful mixing introduced; EVM path untouched.
