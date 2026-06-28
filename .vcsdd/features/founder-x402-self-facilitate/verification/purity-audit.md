# Purity Boundary Audit — founder-x402-self-facilitate (Phase 5, lean)

Date: 2026-06-28 · Sprint: 1 · Mode: lean · Status: PASS

## Declared Boundaries

Per `specs/verification-architecture.md` purity boundary map:

| Component | Declared side |
|---|---|
| `ROUTES` constant | PURE data |
| `BAZAAR_EXTENSION_FOR_SOCIAL_X` (declareDiscoveryExtension result) | PURE data |
| `validateEnv(env)` | PURE |
| `getMetadata(routes)` | PURE |
| `GET /health` handler (post-swap) | PURE |
| `resolveAcceptsAmount(accepts, decimals)` | PURE |
| `wrapSettle(fn)` | PURE wrapper (returns a function; the wrapper itself has no side effects until called) |
| `privateKeyToAccount` / `createWalletClient` / `toFacilitatorEvmSigner` / `new x402Facilitator()` / `registerExactEvmScheme` / `x402ResourceServer` | IMPURE (hold stateful network signers) |
| `probeGasReady(walletClient, address)` | IMPURE (single RPC at boot, cached, non-blocking) |
| `app.listen(port, cb)` | IMPURE (binds a port) |

## Observed Boundaries

Static audit of `apps/x402-agents/src/server.js`:

- All declared PURE functions perform no network I/O, no disk I/O, no `Date.now()` /
  `Math.random()` calls, and no env reads beyond their explicit arguments (validateEnv reads
  its argument; resolveAcceptsAmount is fully pure over its args).
- `ROUTES` is `Object.freeze`d at module scope; `ROUTE_ACCEPTS` is frozen and includes an
  accessor on `payTo` that reads `process.env.X402_WALLET_ADDRESS` at access time. The
  accessor is documented and tested (PROP-002/004); it is the single declared exception
  to "PURE data" — semantically the route table represents the current env's payTo, not
  a snapshot. Reasoning recorded in the iter-2 impl adversary verdict.
- `wrapSettle` invokes `console.error` only on the error path. Console output is an
  acknowledged side effect of the IMPURE settle path it wraps; the wrapper itself is PURE
  (function-returning).
- IMPURE components are confined to `createApp()` and the script entrypoint block. They
  cannot be transitively imported by tests (vitest tests do not construct the facilitator
  except where explicitly intended).

## Summary

Declared boundaries match observed boundaries. The one documented exception (`payTo`
accessor) is intentional, tested, and required for the route-config to reflect post-validation
env truth. No purity leaks. Lean mode passes the audit.
