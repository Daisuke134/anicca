# Security Hardening Report

**Feature**: spawn-funding-swap · **Sprint**: 1 · **Phase**: 5 · **Date**: 2026-07-10

## Tooling

| Tool | Availability | Invocation |
|---|---|---|
| Semgrep | Available (`/opt/homebrew/bin/semgrep`, v1.168.0) | `semgrep --config=auto --config=p/security-audit --config=p/secrets skills/self/spawn-funding-swap/ --exclude="__tests__" --json --quiet` |
| `node --test` (live, own runner) | Available | `cd ~/anicca && node --test skills/self/spawn-funding-swap/lib/__tests__/*.test.mjs` (also re-runs PROP-021's test-money static scan and PROP-017's purity-boundary static scan as real executable tests, not just prose) |
| Manual grep-based scans | Performed, this session | Hardcoded-secret literal scan, second-conversion-site scan, real-client wiring reachability check, npm-audit-finding reachability check — see `security-results/manual-review-scans.txt` |
| `npm audit` | Available | `npm audit --omit=dev` (repo-wide, ~/anicca) |
| Wycheproof (crypto test vectors) | **Not applicable** | This feature performs zero cryptographic primitive implementation of its own — signing is fully delegated to `viem`'s `privateKeyToAccount`/injected `BaseSigner` and Akash's own CLI keyring; no custom crypto (hashing, ECDSA, KDF) is implemented anywhere in `skills/self/spawn-funding-swap/`. Wycheproof-style vector testing is out of scope for this feature by design, not by omission. |

Raw Semgrep output: `security-results/semgrep-raw.json` (0 results, 0 errors, 12 files scanned, this
session's live run). Raw manual-scan transcript: `security-results/manual-review-scans.txt`.

## Findings

**Semgrep: 0 findings across `p/security-audit` + `p/secrets` + `auto`, 12 files scanned, 0 errors.**

Files scanned (confirmed from the raw JSON `paths.scanned`): `bin/spawn-funding-swap.mjs`,
`lib/driver.mjs`, `lib/ledger-store.mjs`, `lib/pure/{base-units,constants,funding-check,ledger-plan,
route-validation,settlement,swap-need}.mjs`, `lib/resolve-swap-identity.mjs`,
`lib/resolve-swap-state-dir.mjs` — all 12 delivered non-test source files in this feature.

**Manual review (no blocking findings):**

| Area checked | Result |
|---|---|
| Injection (shell/SQL/eval) | None of the 12 files invokes a shell, `eval`, or SQL. `lib/pure/**` are zero-I/O pure functions. `ledger-store.mjs` calls only `node:fs/promises` APIs (`fs.mkdir`, `fs.readFile`, `fs.writeFile`) against a path built from `path.join(stateDir, destinationAddress + ".json")` — `destinationAddress` is the hardcoded `DESTINATION_AKASH_ADDRESS` constant, never untrusted input (see Path traversal row). No shell command is built from any external string anywhere in the feature. |
| Unsafe deserialization | `ledger-store.mjs`'s `readState`/`writeState` use `JSON.parse`/`JSON.stringify` with a custom bigint-marker `jsonReviver`/`jsonReplacer` (lines 17-26) on a file this same process previously wrote — never untrusted network input. `lib/pure/ledger-plan.mjs`'s `reconcileLedgerOnResume` DOES parse arbitrary/possibly-corrupt disk content (`JSON.parse` wrapped in try/catch, line 40) but fails closed to the literal string `'CORRUPT'` on any parse error or shape mismatch (never treated as "empty/start fresh") — the money-safety-critical case (PROP-009's crash-recovery guarantee) is explicitly covered by `driver-crash-recovery.test.mjs`. |
| Missing input validation on money-affecting fields | `toBaseUnits`/`fromBaseUnits` (`lib/pure/base-units.mjs`) throw (fail closed) on NaN/negative/non-finite/overflow/wrong-decimals inputs (PROP-022/023, confirmed live this session). `capUsd`/`usdEquivalentOf` (`lib/pure/swap-need.mjs`) fail closed on NaN/negative (`capUsd` → `0`) and non-positive/non-finite price (`usdEquivalentOf` → throw). `checkSourceFunded`/`verifySettlement` use exact `bigint`-vs-`bigint` comparisons throughout — no float-equivalent comparison anywhere on a money-affecting path (grep-confirmed, `security-results/manual-review-scans.txt`). |
| Path traversal | `ledger-store.mjs`'s `stateFilePath(stateDir, destinationAddress)` builds the ledger file path from `stateDir` (resolved via `resolve-swap-state-dir.mjs`, either an explicit env override or `resolveStateDir()`'s own colony-wide durable-state convention — never caller-supplied per-request input) and `destinationAddress` (always the hardcoded `DESTINATION_AKASH_ADDRESS = "akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523"` literal in `bin/spawn-funding-swap.mjs`, never read from `process.env` or any external input — confirmed by source read, no override path exists). No file path in this feature is built from untrusted external/user-controlled input. |
| Integer overflow / precision loss | All on-chain money amounts (`requiredBaseUnits`, balances, settlement deltas) are `bigint` throughout `lib/pure/funding-check.mjs`/`settlement.mjs`/`route-validation.mjs` and `driver.mjs` — never plain `number` past the single `toBaseUnits`/`fromBaseUnits` choke point (REQ-012). `toBaseUnits` itself explicitly guards the one place a `number` intermediate exists (the pre-conversion float) against `Number.MAX_SAFE_INTEGER` overflow (`base-units.mjs:36-39`, confirmed live by `PROP-022(d)`'s overflow-guard test). No unguarded float money-math path exists anywhere in this feature — this is the exact FIND-001/FIND-002 defect class the feature's own iteration history (Phase 1b spec revisions) was built to close. |
| Hardcoded secrets | Semgrep's `p/secrets` ruleset: 0 findings. Manual grep for private-key-shaped literals (`0x[0-9a-f]{64}`, PEM headers) across the feature: 0 matches (`security-results/manual-review-scans.txt`). No private key, API key, or credential is hardcoded anywhere in the 12 files. |
| Identity isolation (fail-closed, no shared-env fallback) | `resolve-swap-identity.mjs`'s `resolveOwnBaseIdentity` gates on `ANICCA_HOME` being explicitly a non-empty string BEFORE `resolveEvmPrivateKey` is ever invoked (source-read confirmed, lines 38-40) — there is no `SPAWN_FUNDING_SWAP_EXPECTED_BASE_SIGNER_ADDRESS`/`SOURCE_BASE_ADDRESS` env-var read anywhere in the feature (grep-confirmed: zero matches for either string outside this file's own explanatory comments). `bin/spawn-funding-swap.mjs`'s `buildDeps()` calls `resolveOwnBaseIdentity` and checks `identity.ok` BEFORE any real-client module is even dynamically imported (source-read confirmed, lines 54-64) — a failed identity resolution can never reach a lock/price/route/sign call. This closes the exact identity-leak class documented in `feedback_earn_identity_resolve_per_instance_gate_on_anicca_home.md`. |
| Money-safety literals never overridable | `SWAP_MAX_USD=20`, `MIN_GAS_WEI=1_000_000_000_000_000n`, `TOLERANCE_BPS=50` (`lib/pure/constants.mjs`) are all module-level `const` literals, defined exactly once, with zero `process.env`/CLI-flag/config read anywhere in their defining module or any call site (grep-confirmed across the full feature — the only `process.env` reads in the entire feature are for `ANICCA_HOME`/`AKASH_KEY_NAME`/`SPAWN_FUNDING_SWAP_THRESHOLD_AKT`/`SPAWN_FUNDING_SWAP_LEG_TIMEOUT_MS`/`SPAWN_FUNDING_SWAP_STATE_DIR`/`SPAWN_FUNDING_SWAP_FAKE_DEPS_MODULE`, none of which touch the three money-safety caps). PROP-012's live-executed hostile-env test additionally proves `capUsd`'s output is bit-identical regardless of a spoofed `process.env.SWAP_MAX_USD`. `DESTINATION_AKASH_ADDRESS` (`bin/spawn-funding-swap.mjs:35`) is likewise a hardcoded literal with zero env override path — confirmed no test (production or fixture) ever sets a `SPAWN_FUNDING_SWAP_DESTINATION_AKASH_ADDRESS` override, matching the module's own documentation. |
| npm-audit (repo-wide, dependency vulnerabilities) | 25 findings (23 moderate, 2 high) in the `~/anicca` monorepo's `node_modules`, all in the `@reown/appkit`/`@walletconnect/universal-provider` transitive chain. Confirmed by grep that `skills/self/spawn-funding-swap/` imports neither `@reown/*` nor `walletconnect` anywhere — these findings are unreachable from this feature's own import graph (the feature's only external dependency is `viem/accounts`). Flagged for repo-wide awareness, **non-blocking for this feature's Phase 5 gate**. |

## Summary

0 blocking findings. Semgrep: 0/0 across 12 in-scope files. Manual review found no injection,
deserialization, path-traversal, hardcoded-secret, integer-overflow/precision-loss, or identity-isolation
issue. All three money-safety literal constants are confirmed non-overridable by any env/config path,
live-proved by PROP-012. The one repo-wide `npm audit` finding set is confirmed unreachable from this
feature's code. No security-hardening action required before Phase 6.
