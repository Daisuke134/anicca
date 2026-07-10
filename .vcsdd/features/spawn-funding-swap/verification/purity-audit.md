# Purity Boundary Audit

**Feature**: spawn-funding-swap · **Sprint**: 1 · **Phase**: 5 · **Date**: 2026-07-10

## Declared Boundaries

Per `specs/verification-architecture.md`'s "Purity Boundary Map" (lines 3-59):

| Module | Declared classification | Declared basis |
|---|---|---|
| `lib/pure/swap-need.mjs` (`computeSwapNeed`, `usdEquivalentOf`, `capUsd`) | **Pure Core** | Deterministic, no I/O — REQ-001, REQ-011, REQ-006. `SWAP_MAX_USD` is a `const` literal, this module only. |
| `lib/pure/route-validation.mjs` (`validateRoute`) | **Pure Core** | Deterministic predicate over an already-fetched route response object — REQ-002. |
| `lib/pure/ledger-plan.mjs` (`planNextLeg`, `reconcileLedgerOnResume`) | **Pure Core** | Deterministic; the ledger file's actual read is effectful (`ledger-store.mjs`), interpreting its contents is pure — REQ-004/REQ-005. |
| `lib/pure/funding-check.mjs` (`checkSourceFunded`) | **Pure Core** | Exact bigint comparison over already-fetched balances — REQ-003. |
| `lib/pure/settlement.mjs` (`verifySettlement`) | **Pure Core** | Exact bigint delta/tolerance comparison — REQ-007. |
| `lib/pure/base-units.mjs` (`toBaseUnits`, `fromBaseUnits`) | **Pure Core** | The single named dollar/AKT↔base-unit conversion choke point — REQ-012. |
| `lib/pure/constants.mjs` | **Pure Core** (literal constants module) | `SWAP_MAX_USD`/`MIN_GAS_WEI`/`TOLERANCE_BPS`/`USDC_DECIMALS_BASE`/`AKT_DECIMALS`, never `process.env`/CLI/genome/config-sourced. |
| `SkipApiClient.getRoute()`, `ChainReader.getBaseUsdc/getBaseGas/getAkashBalance()`, `BaseSigner.signAndBroadcast()`, `AkashSigner` (CLI subprocess), `RelayPoller.waitForConfirmation()`, `PriceOracle.getAktUsdPrice()` | **Effectful Shell** | HTTP/RPC/subprocess I/O; MUST be injected as parameters/interfaces, never module-level singletons (declared explicitly so Phase 2a tests substitute mocks with zero real network/chain access). |
| `LedgerStore.read()/write(state)` + canonical destination-address-keyed lock | **Effectful Shell** | Local JSON ledger file, disk I/O — REQ-005/REQ-010. |
| CLI entrypoint (`bin/spawn-funding-swap.mjs`) | **Effectful Shell** | The only place effectful clients are concretely instantiated and wired to the pure core. |

Structural enforcement declared: pure modules under `lib/pure/` MUST have no import of `node:fs`,
`node:child_process`, `node:http(s)`, or `fetch` (PROP-017); test files under this feature's test
directories are held to a symmetric rule — no import of the concrete effectful-client implementation
modules, no real endpoint literal strings outside a documented fixture-comment (PROP-021, the "Test-Money
Safety Rule").

## Observed Boundaries

Confirmed by direct source read of all 7 `lib/pure/**` files and all 5 effectful-shell files this session
(fresh context, not trusting the Phase 3 adversary's prior sign-off), plus live re-execution of the
structural guard tests:

- **`lib/pure/swap-need.mjs`**: only import is `SWAP_MAX_USD` from `./constants.mjs` (itself a zero-import
  literals module). No `fs`/`fetch`/`child_process`/`http`/`process.env` reference anywhere in the file.
  **Matches declared "Pure Core" exactly.**
- **`lib/pure/base-units.mjs`**: re-exports `capUsd`/`usdEquivalentOf` from `swap-need.mjs`; `toBaseUnits`/
  `fromBaseUnits` themselves have zero imports beyond the module's own `assertValidDecimals` helper. No
  I/O of any kind. **Matches declared "Pure Core" exactly.**
- **`lib/pure/funding-check.mjs`**: single exported function, zero imports at all. **Matches declared "Pure
  Core" exactly.**
- **`lib/pure/route-validation.mjs`**: single exported function, zero imports at all. **Matches declared
  "Pure Core" exactly.**
- **`lib/pure/settlement.mjs`**: single exported function, zero imports at all. **Matches declared "Pure
  Core" exactly.**
- **`lib/pure/ledger-plan.mjs`**: `planNextLeg`/`reconcileLedgerOnResume`, zero imports at all;
  `reconcileLedgerOnResume` calls `JSON.parse` on its `ledgerFile` PARAMETER (never reads the file itself)
  — confirmed the actual `fs.readFile` call lives exclusively in `lib/ledger-store.mjs` (`readState`,
  line 66), matching the doc's own explicit "the actual file read is effectful ... interpreting its
  contents is pure" carve-out. **Matches declared "Pure Core" exactly.**
- **`lib/pure/constants.mjs`**: zero imports, zero function calls — pure literal declarations. Grep-
  confirmed no `process.env` read anywhere in this file or in any of the other six `lib/pure/**` files
  (`security-results/manual-review-scans.txt` / direct source read this session). **Matches declared
  classification exactly.**
- **Structural guard (PROP-017), re-run live this session**:
  ```
  $ node --test skills/self/spawn-funding-swap/lib/__tests__/purity-boundary.test.mjs
  ✔ PROP-017: every file under lib/pure/** exists at all
  ✔ PROP-017: no file under lib/pure/** imports node:fs, node:child_process, node:http(s), or references fetch
  tests 2, pass 2, fail 0
  ```
- **`lib/driver.mjs`** (effectful orchestrator): imports all seven pure functions plus the four constants,
  and wires them against `deps.chainReader`/`priceOracle`/`skipApiClient`/`baseSigner`/`relayPoller`/
  `ledgerStore` — every one of these is a REQUIRED parameter on the `deps` object passed into `runSwap`
  (never a module-level singleton, never a bare `import` of a concrete client implementation). Confirmed:
  `driver.mjs` contains ZERO `node:fs`/`node:http(s)`/`fetch` imports of its own — all I/O happens through
  the injected `ctx.*` client calls (`await ctx.chainReader.getBaseUsdc(...)`, `await
  ctx.skipApiClient.getRoute(...)`, `await ctx.baseSigner.signAndBroadcast(...)`, `await
  ctx.ledgerStore.writeState(...)`, etc.), matching the declared injection-only discipline for the
  Effectful Shell clients. **Matches declared "Effectful Shell orchestrator, injection-only" shape
  exactly.**
- **`lib/ledger-store.mjs`**: confirmed real `node:fs`/`node:path` imports (`import { promises as fs } from
  "node:fs"`) and real `fs.mkdir`/`fs.readFile`/`fs.writeFile` calls, plus reuse (unmodified import, no
  local re-implementation) of `economy/gig/lib/lock.mjs`'s `withGigLock` for the canonical lock. **Matches
  declared "Effectful Shell" exactly.**
- **`lib/resolve-swap-identity.mjs`**: reads `process.env`/injected `env` parameter and calls
  `resolveEvmPrivateKey`/`privateKeyToAccount` (real key-material resolution) — genuinely effectful (reads
  ambient environment + derives a real address from real key material). Not explicitly named as its own row
  in the Phase-1b Purity Boundary Map table (the table predates this module, which was added during
  contract-review to close a FIND-002 identity-isolation gap — see its own file-header comment), but its
  behavior is unambiguously Effectful Shell by the doc's own general criteria (I/O — here, environment
  read + key derivation — MUST be injected/mockable, never a bare module-level singleton) and IS injectable
  via its `{env}` parameter (mirrored by its own dedicated test file,
  `resolve-swap-identity.test.mjs`, exercising it with injected fake env maps). **One documentation gap
  noted below** (missing table row), not a code-level drift.
- **`lib/resolve-swap-state-dir.mjs`**: reads `process.env`/injected `env` parameter, delegates to
  `resolveStateDir()` (itself effectful — reads `os.homedir()`/filesystem conventions in the sibling `spawn`
  skill). Same pattern as `resolve-swap-identity.mjs`: genuinely effectful, injectable via `{env}`, not its
  own named row in the Phase-1b table (added during Phase-3 impl review's FIND-002 STATE_DIR fix, per its
  own file-header comment). **Same documentation gap noted below.**
- **`bin/spawn-funding-swap.mjs`**: confirmed the ONLY place `../lib/real-clients/*.mjs`,
  `../lib/ledger-store.mjs`'s `createLedgerStore`, `resolve-swap-identity.mjs`, and
  `resolve-swap-state-dir.mjs` are concretely instantiated/wired together, and the only place
  `SPAWN_FUNDING_SWAP_FAKE_DEPS_MODULE` is read (the Phase 2a-defined test seam). **Matches declared "the
  only place these effectful clients are concretely instantiated and wired to the pure core" exactly.**

## Summary

**No core/shell drift detected.** All 7 `lib/pure/**` modules' observed classification matches
`specs/verification-architecture.md`'s declared Purity Boundary Map exactly, independently re-confirmed by
a fresh-context source read plus a live re-run of the PROP-017 structural guard test this session (2/2
pass). `lib/driver.mjs` correctly wires the pure core against exclusively-injected effectful clients with
zero bare imports of concrete implementations. `lib/ledger-store.mjs` and `bin/spawn-funding-swap.mjs`
match their declared Effectful Shell classification exactly, with real `node:fs` I/O confirmed present only
where declared.

**One documentation gap found (not a code-level drift or money-safety issue)**: `lib/resolve-swap-
identity.mjs` and `lib/resolve-swap-state-dir.mjs` are genuinely, correctly effectful (environment reads +
real key/path derivation, both injectable via their `{env}` parameter) but have no dedicated row in
`specs/verification-architecture.md`'s Purity Boundary Map table — both modules were added after Phase 1b
(during contract-review/Phase-3 impl-review fixes for FIND-002 identity-isolation and FIND-002
STATE_DIR-defaulting, per their own file-header comments), and the Map table was never updated to add them.
Their actual behavior is unambiguous and correctly classified in code + tests (both have dedicated test
files exercising the injected-`{env}` seam), so this is a spec-documentation completeness gap, not a
purity-boundary violation in code that exists. Mirrors the exact "missing table row for a
contract-review-added module" pattern this codebase's `anicca-agent-spawn` Phase 5 precedent also found
(`pending-registry-append.js` lacking its own Purity Boundary Map row).

**No required follow-up before Phase 6** on purity-boundary grounds. **Recommended, non-blocking follow-up**
for a future sprint: add explicit Purity Boundary Map rows for `resolve-swap-identity.mjs` and
`resolve-swap-state-dir.mjs` to `specs/verification-architecture.md` so the Map stays a complete, current
inventory of every effectful module in this feature.
