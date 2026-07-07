# Purity Boundary Audit

**Feature**: anicca-agent-spawn · **Sprint**: 1 · **Phase**: 5 · **Date**: 2026-07-08

## Declared Boundaries

Per `specs/verification-architecture.md`'s "Purity Boundary Map (file/function level)" (§232):

| Module | Declared classification | Declared basis |
|---|---|---|
| `treasury-gate.mjs` | **Pure Core** | Zero I/O; consumes already-fetched balances/ledger rows, returns a deterministic decision/aggregate. Only import is `isSelfFunded` (itself pure). |
| `colony-balances.mjs` | Effectful-via-injection | `readCitizenBalances` orchestrates injected `fetchEvmBalanceUsd`/`fetchSolanaBalanceUsd` async callbacks; no direct network/fs call of its own. |
| `registry-path.mjs` | **Effectful Shell** (corrected, resolves FIND-1002) | Built from `os.homedir()` + `resolveStateDir({})` real reads at module-load time — explicitly NOT Pure Core despite computing constants, per the doc's own correction of a prior mislabeling. |
| `citizens-registry.mjs` | **Effectful Shell** | `bootstrapCitizensRegistry` performs real `fs/promises` I/O (`mkdir`, `open(...,"wx")`, `writeFile`). |
| `cloud-target.mjs` | Pure (`selectCloudTarget`) + Effectful-via-injection (`fetchAktUsdPrice`/`fetchNosUsdPrice`) | `selectCloudTarget` is synchronous, zero I/O; the price-fetch functions delegate to an injected `fetchImpl`. |
| `needs-solana-wallet.mjs` | **Pure Core** | Plain boolean conditional over given inputs. |
| `akash-funding-gate.mjs` | Pure sequencing + Effectful-via-injection | `evaluateAkashFundingGate`'s own two-pass sequencing logic is deterministic; `queryBalanceAkt`/`attemptBridge` are injected callbacks. Reuses `computeSpawnGate` (pure, unmodified import). |
| `shelter-cost-ledger.js` | **Effectful Shell** | Thin delegation to `ledger.js`'s real `fs` read/append. |
| `child-spec.js` | **Pure Core** | `nextChildId`/`buildChildSpec` — zero imports of `fs`/`path`/any Node built-in; deterministic, throws on invalid input. |

## Observed Boundaries

Confirmed by direct source read of all 9 delivered files (this session, fresh context):

- **`treasury-gate.mjs`**: control-flow read confirms its only import is `isSelfFunded` from
  `../../../_shared/lib/is-self-funded.mjs` (itself pure). No `fs`, `fetch`, `require("http")`,
  `readFileSync`, or any network/filesystem global appears anywhere in the file. The only `Date.now()`
  reference is `decideColonySpawn`'s own `nowMs = Date.now()` default parameter — never an internal call
  inside a function body. **Matches declared "Pure Core" exactly** (also satisfies `contracts/sprint-1.md`
  CRIT-001's own pass condition, independently re-confirmed this session).
- **`colony-balances.mjs`**: `readCitizenBalances` has no `fs`/`path` import at all (confirmed via this
  session's own new `spawn-gap-coverage.test.mjs` "PROP-101e" structural check, which greps the source
  for exactly this). All network access is via the two REQUIRED injected parameters — matches declared
  shape.
- **`registry-path.mjs`**: source read confirms `COORDINATOR_HOME = os.homedir()` (direct call, module-load
  time) and `CITIZENS_REGISTRY_PATH` built from `resolveStateDir({})` inside a `try/catch`. **Matches
  declared "Effectful Shell" exactly** — genuinely environment-coupled, not a hardcoded literal.
- **`citizens-registry.mjs`**: confirmed `fs.mkdir`/`fs.open(...,"wx")`/`handle.writeFile`/`handle.close`
  — no `existsSync`/`fs.stat` check precedes the exclusive-create (matches CRIT-007's pass condition, and
  this session's own `spawn-gap-coverage.test.mjs`/existing `citizens-registry.test.mjs` structural test
  both confirm this via source-text regex). **Matches declared "Effectful Shell" exactly.**
- **`cloud-target.mjs`**: `selectCloudTarget` is a single synchronous function with zero awaits/imports
  beyond its own parameters. `fetchSpotPriceUsd` wraps a REQUIRED `fetchImpl` parameter in try/catch,
  fails closed to `0`. **Matches declared split exactly.**
- **`needs-solana-wallet.mjs`**: single exported function, zero imports beyond the module's own
  `SOLANA_SETTLED_SKILLS` constant. **Matches declared "Pure Core" exactly.**
- **`akash-funding-gate.mjs`**: `evaluateAkashFundingGate`'s only non-parameter import is
  `computeSpawnGate` from `../../spawn-child/lib/akt-cost-gate.js` (confirmed present, unmodified — no
  diff against that file this sprint). All chain/network access is via the two REQUIRED injected
  callbacks. **Matches declared split exactly.**
- **`shelter-cost-ledger.js`**: confirmed it calls `ledger.js`'s `readChildren`/`appendChild` directly
  (no re-implemented `fs` logic of its own — matches `contracts/sprint-1.md`'s Phase 2c refactor note #2,
  independently re-confirmed by reading the current file, which is a 2-function, 16-line pure delegation
  wrapper). **Matches declared "Effectful Shell" exactly.**
- **`child-spec.js`**: confirmed zero `require`/`import` of any Node built-in or other module anywhere in
  the file. **Matches declared "Pure Core" exactly.**

## Summary

**No drift detected.** All 9 delivered modules' observed core/shell classification matches
`specs/verification-architecture.md`'s declared Purity Boundary Map exactly, independently re-confirmed
by a fresh-context source read this session (not merely trusting the Phase 3 adversary's own prior
sign-off). No hidden side effects, no verifier-hostile coupling (e.g., no module silently reaches for
`process.env`/ambient globals outside its documented injection points), and the two files with corrected
classifications from FIND-1002 (`registry-path.mjs`) and this sprint's Phase 2c refactor
(`shelter-cost-ledger.js`) both hold under this session's own independent re-read.

**One residual note, not a purity-boundary defect**: the Purity Boundary Map also declares a **tenth**
artifact, `~/anicca/skills/self/spawn/registry/citizens.seed.json`, as a "Static config asset (git-tracked,
NEVER mutated at runtime)". This file does not exist in the current tree (`skills/self/spawn/` has no
`registry/` subdirectory). This is a missing-deliverable finding (see `verification-report.md`'s "Missing
seed deliverable" section) rather than a core/shell drift — there is no code to misclassify, only an
absent file the Map assumed would be present.

**No required follow-up before Phase 6** on purity grounds specifically; the missing-seed-file and
orchestrator-blocked findings are proof-obligation-coverage matters (see `verification-report.md`), not
purity-boundary violations in the code that DOES exist.
