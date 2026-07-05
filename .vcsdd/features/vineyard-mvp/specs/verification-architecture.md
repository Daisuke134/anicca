# Vineyard MVP — Verification Architecture (VCSDD Phase 1b, strict mode)

**Feature**: `vineyard-mvp` · **Mode**: strict · **Companion**: `specs/behavioral-spec.md` (REQ-001..020 —
REQ-019/020 added in the Phase 1c spec-review gate, iteration 2→3, closing FIND-005/FIND-006)
**Language profile**: mixed — Node.js `.mjs` (core/cli/api/engine wrappers), Python 3.11+ (the 3 copied/
adapted Polymarket + Hyperliquid scripts), Bash (`run.sh`). No single VCSDD `language` profile applies;
tooling below is chosen per-module rather than assuming one language-specific formal-verification stack
(e.g. Kani is Rust-only and does not apply here — see Tier 3 note).

## Purity Boundary Map

### Pure / deterministic core (no I/O, referentially transparent given explicit inputs)
| Module.function | Why it is pure |
|---|---|
| `core/brain.mjs`'s `pickEngine({lastRun, candidates})` | Pure function of its two explicit arguments — deterministic sort, zero I/O, zero wall-clock read inside the function itself (the caller stamps `lastRun[engineName] = Date.now()` outside the picker). The single cleanest purity example in the system — a direct instance of `building-effective-ai-agents.md`'s "deterministic code for tools/bookkeeping" principle. |
| `core/wallet.mjs`'s `base58(buf)`, `normalizeEvmKey(key)`, `isValidId(id)` | Pure buffer/string/regex transforms — same input always yields same output, no I/O. `isValidId` (REQ-019) is the exact predicate `instanceDir`/`core/ledger.mjs`'s `ledgerPath` both call before their own effectful `path.join`/`fs.*` calls. |
| `engines/polymarket.mjs`'s `parseFundOutput`, `parseTradeOutput`, `parseRedeemOutput` | Pure string→JSON parsers over an explicit stdout string; throw on empty input, never read/write anything. |
| `engines/hyperliquid.mjs`'s `parseHlOutput` | Pure `JSON.parse` over the trimmed stdout string. |
| `engines/solana.mjs`'s `lastLines(text, n)` | Pure string slicing. |
| `core/ledger.mjs`'s `sumRealized(lines)` | Pure fold over an ALREADY-PARSED array of ledger-line objects (`net_usdc` vs `earn_usdc - cost_usdc` vs `0`, `Number.isFinite` guard) — zero I/O, referentially transparent. This is the exact accounting logic Phase 5 audits most closely for REQ-005/PROP-005. `realizedPnl(id, dataDir)` is NOT itself pure — it is a 1-line composition (`sumRealized(readLedger(id, dataDir))`) that calls the effectful `readLedger`; it lives in the effectful-shell table below, not here. |
| `engines/lib/cost-basis.mjs`'s `applyDelta(costBasisObj, venue, delta)` | Pure — takes an already-read cost-basis object, returns a NEW object with `venue`'s value adjusted and floored at 0 (never mutates its input, zero I/O). `adjust(venue, delta, filePath)` is NOT itself pure (read → `applyDelta` → write); it lives in the effectful-shell table below as a thin wrapper around this kernel. NOTE: `seedIfEmpty(seed, filePath)` was NOT split the same way — it still performs its own inline `readCostBasis`/`write` I/O and is classified as effectful below, not here (unlike `adjust`, no pure kernel has been extracted from it in this feature's scope). |

### Effectful shell (real side effects — I/O, subprocess, network, on-chain broadcast)
| Module.function | Side effect |
|---|---|
| `core/wallet.mjs`'s `generateWallet`, `resolveEvmPrivateKey`, `resolveSolanaSecret`, `resolveAddresses` | Filesystem read/write of key material (`wallet.json`/`solana.json`, `chmod 600`); `generateWallet` additionally calls real CSPRNG (`generatePrivateKey()`, `crypto.generateKeyPairSync`) — non-deterministic by design on first call, deterministic (idempotent) thereafter via the file it wrote. |
| `core/registry.mjs`'s `readRegistry`/`writeRegistry`/`registerSpawn`/`updateSpawn` | Filesystem read/write of `spawns.json`; `registerSpawn` also stamps a non-deterministic wall-clock `created: new Date().toISOString()`. |
| `core/ledger.mjs`'s `appendLedger`/`readLedger`, and `realizedPnl(id, dataDir)` | Filesystem append/read of `<id>.jsonl`; `appendLedger` stamps a wall-clock `ts`. `realizedPnl` is the thin effectful composition `sumRealized(readLedger(id, dataDir))` — its only I/O is the `readLedger` call; the summation itself is the pure `sumRealized` kernel above. |
| `engines/lib/cost-basis.mjs`'s `readCostBasis`/`write`/`adjust`/`seedIfEmpty` | Filesystem read/write of `cost-basis.json`. `adjust(venue, delta, filePath)` is a thin wrapper (`read → applyDelta → write`) around the pure `applyDelta` kernel above; `seedIfEmpty` performs its own inline read/write and has no separated pure kernel in this feature's scope. |
| `engines/yield.mjs`'s `run()` | Real RPC calls (Base chain), real on-chain deploy/refill transactions, real cost-basis file I/O (via the above `engines/lib/cost-basis.mjs` functions). |
| `engines/polymarket.mjs`'s `fund()`, `trade()`, `redeem()` | `child_process.execFile` spawning real Python processes that make real HTTP calls (Polymarket gamma-api/relayer-v2) and submit real on-chain orders/redemptions on Polygon. |
| `engines/hyperliquid.mjs`'s `account()`, `market()`, `open()`, `close()` | `child_process.execFile` spawning `hl.py`, which makes real Hyperliquid API calls and can open/close real leveraged positions. |
| `engines/solana.mjs`'s `run()`, `setup()` | `child_process.spawn` of `run.sh` → `franklin-trading`, an autonomous agent that makes real x402 model-payment calls and real Solana/Jupiter transactions; `HOME` env override is the isolation mechanism (a real, deliberate side-effect boundary, not an accidental one). |
| `core/loop.mjs`'s `runOnce`/`runLoop` | Orchestrates all of the above; also reads wall-clock (`Date.now()` for `lastRun`) and (`runLoop`) sleeps via `setTimeout`. |
| `cli/index.mjs`, `api/server.mjs` | Top-level effectful shell: `process.argv`/HTTP request parsing, `console.log`/HTTP response writing, process exit codes, `app.listen`. Deterministic DISPATCH code (matches the Anthropic "tools are deterministic, the agent/operator decision is not" pattern) but I/O-heavy by nature. |

**Why this boundary matters for Phase 5**: `verification/purity-audit.md` (Phase 5) will diff this
*declared* boundary against the *observed* one (e.g. grep for `fs.`/`child_process`/`fetch`/`requests.`
inside files declared pure above — any hit is a boundary violation to investigate before Phase 6).

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|---|---|---|---|
| PROP-001 | Repo scaffold structure matches the declared tree (dirs, `package.json` fields, `.gitignore` entries) — REQ-001 | 0 | false | manual code inspection / `git log` |
| PROP-002 | `generateWallet(id, env, overrideKeys)` is idempotent (same id → same address on re-call, `overrideKeys` silently ignored once an identity exists) and distinct ids never collide — REQ-002 | 1 | false | node:test (`core/wallet.test.mjs`) |
| PROP-003 | **Fail-closed key isolation: instance B can NEVER resolve or sign with instance A's key, and no ambient/global env var can ever override any id's resolved key** — REQ-003 (the single most important proof obligation in this feature) | 2 | **true** | node:test baseline (`core/wallet.test.mjs`, Task 3: "FAIL-CLOSED"/"ISOLATION" tests) PLUS the "REGRESSION: ambient env var has zero effect on ANY id's resolution" tests (Task 3, added after the Phase-1c fix removed the ambient-override code path entirely — there is no longer a footgun to fuzz; these regression tests instead prove the deleted branch cannot silently reappear) hardened in Phase 5 by re-running both test families against many adversarial instance-id pairs (including ids sharing prefixes/substrings, AND path-traversal-shaped ids such as `"../x"`, `"a/b"`, `"../../etc"`, absolute paths, and ids differing only by a trailing `/..` — per FIND-007's specific callout that PROP-003's fuzz corpus must not silently assume every generated id is already filesystem-safe) via `fast-check` property-based generation of id pairs, confirming `resolveEvmPrivateKey`/`resolveSolanaSecret` for id B never equals, derives from, or falls back to id A's material for any generated pair, AND that any path-traversal-shaped generated id is rejected by `isValidId`/`instanceDir` (REQ-019/PROP-019) rather than silently resolving outside `<VINEYARD_HOME>/instances/` |
| PROP-004 | Registry never persists/exposes private key material; duplicate `id` registration is rejected — REQ-004 | 1 | **true** | node:test (`core/registry.test.mjs`) + grep-based static check (no `privateKey`/`secretKey` string reaches `registerSpawn`/`updateSpawn` call sites) |
| PROP-005 | Ledger only ever records a real subprocess/tx-derived number or an honest skip/wait marker; `realizedPnl` is always `Number.isFinite`, never `NaN`, never fabricated — REQ-005 | 1 | **true** | node:test (`core/ledger.test.mjs`, including a direct unit test of the pure `sumRealized(lines)` kernel over in-memory arrays) + code-path audit of `core/loop.mjs`'s `normalizeResult()` (every field it emits must trace back to the engine's own returned object, never invented) |
| PROP-006 | Polymarket funding ALWAYS routes through the bridge onramp (`fund_via_bridge.py`); no code path performs a raw pUSD transfer or raw deposit-wallet deploy — REQ-006 | 2 | **true** | exhaustive call-site enumeration (every path from `vineyard fund`/`POST /fund` to a chain-touching call is traced and shown to terminate in exactly one subprocess invocation, `fund_via_bridge.py`) + node:test (`engines/polymarket.test.mjs` fund-half) |
| PROP-007 | A fresh deployment's first-ever Polymarket registration without a registered `SOURCE_KEY` fails with the script's own explicit, actionable error — never hangs, never silently no-ops — REQ-007 (D8) | 1 | false | manual verification note (plan Task 8 Step 8) + documentation-presence check (README/llms.txt state the bootstrap requirement) |
| PROP-008 | `engines/yield.mjs` + `engines/lib/cost-basis.mjs` never mix two instances' cost-basis state; `run({evmPrivateKey:null})` fails closed — REQ-008 | 1 | false | node:test (`engines/cost-basis.test.mjs`, including a direct unit test of the pure `applyDelta(costBasisObj, venue, delta)` kernel over in-memory objects; `engines/yield.test.mjs`) |
| PROP-009 | `parseTradeOutput` correctly parses `place_order.py`'s real single-line JSON shape and throws a clear error on empty stdout — REQ-009 | 1 | false | node:test (`engines/polymarket.test.mjs` trade-half) against a real-format fixture |
| PROP-010 | `redeem.py`'s `DEPOSIT_WALLET` is resolved ONLY from `POLYMARKET_DEPOSIT_WALLET` env (raises/fails closed if absent — never silently falls back to the original hardcoded founder-wallet constant); `parseRedeemOutput` correctly handles 0..N per-condition rows — REQ-010 (D6) | 1 | **true** | node:test (`engines/polymarket.test.mjs` redeem-half) + Python-side inspection that the hardcoded `DEPOSIT_WALLET = "0x904B50d2..."` literal no longer exists in the copied file (`grep -c "0x904B50d2" redeem.py` → 0) |
| PROP-011 | `parseHlOutput` correctly parses all 4 real `hl.py` output shapes (account/market/open/skipped); `BLOCKRUN_WALLET_KEY` is always injected so `hl.py`'s fragile relative-path fallback is never reached — REQ-011 (D7) | 1 | false | node:test (`engines/hyperliquid.test.mjs`) against real-format fixtures |
| PROP-012 | `franklin-trading`'s `HOME`-scoped `.blockrun/` store is isolated per instance — instance X's Solana engine state never collides with instance Y's or the real `~/.blockrun/` — REQ-012 (D4) | 2 | **true** | empirical, harmless real invocation (`HOME=<tmp> franklin-trading setup solana`, plan Task 12 Step 3, no network/funds) re-run for ≥2 distinct instance ids to confirm structurally disjoint directory trees, hardened in Phase 5 as a repeatable check rather than a one-off manual observation |
| PROP-013 | `core/brain.mjs`'s automatic candidate universe is closed to exactly `{yield, solana, polymarket-redeem}` — Hyperliquid `open` and Polymarket `place_order`/trade NEVER enter the automatic pick set; `pickEngine` is a pure, deterministic function — REQ-013 | 1 | **true** | node:test (`core/brain.test.mjs`) + static/grep check that `AUTOMATIC_ENGINES` (or the `run` verb's default `candidates`) never includes `hl`/`pm-trade` |
| PROP-014 | `runOnce` is a total function — for every reachable input (missing key, missing deposit wallet, engine throwing) it resolves to a ledger line and never rejects/throws — REQ-014 | 1 | **true** | node:test (`core/loop.test.mjs`) with dependency-injected fake engines covering the skip/success/array-normalization branches |
| PROP-015 | Every CLI verb has a corresponding HTTP verb with equivalent semantics (spawn/fund/run/status/list/trade/redeem) — REQ-015 | 0 | false | structural diff of `cli/index.mjs`'s `switch` cases vs `api/server.mjs`'s `app.<verb>` routes + smoke-test parity (plan Tasks 6, 15) |
| PROP-016 | `openapi.json` is valid JSON and its `paths` are a 1:1 match with the actual Express routes; `llms.txt` documents every verb — REQ-016 | 0 | false | `JSON.parse` validity check (plan Task 16 Step 3) + manual cross-reference of `llms.txt`/`openapi.json`/`api/server.mjs` |
| PROP-017 | README's documented quickstart succeeds end-to-end against a genuinely clean `git clone` (not the working tree) — REQ-017 | 1 | **true** | shell E2E script (`git clone` → `npm install` → venv+pip install → `spawn --fund N`), run twice per plan (Task 17 Step 2, Task 18 Step 3) |
| PROP-018 | No engine's automated test performs a real network/subprocess/on-chain call (all use fixtures/dependency injection); every engine has a separately-labeled, non-automated manual verification step for its real pass — REQ-018 | 1 | **true** | test-file code review (assert each `*.test.mjs` only imports pure parser/DI-friendly functions, never calls `execFile`/`spawn` with a real, unmocked binary in the automated suite) + grep for `fake`/`dry`/`mock`/`dummy`/`simulated` in any executable code path (not test/doc comments) |
| PROP-019 | **`id` is validated against `^[a-z0-9][a-z0-9_-]{0,63}$` (`core/wallet.mjs`'s `isValidId`) at EVERY independent per-id path-construction choke point — `instanceDir(id, env)` and `core/ledger.mjs`'s `ledgerPath(id, dataDir)` — and both throw `invalid instance id: <id>` BEFORE any `fs.*` call; an invalid `id` at the API layer (`POST /spawn` and every other id-consuming route) returns `400 {"error":"invalid instance id"}`, never an unhandled crash** — REQ-019 (closes FIND-005: id path-traversal / arbitrary-file-write) | 2 | **true** | node:test (`core/wallet.test.mjs` Task 3 addendum: reject/accept corpus + "throws before any fs access" test; `core/ledger.test.mjs` Task 5 addendum: same for `ledgerPath`) + node:test (`api/server.test.mjs`: `POST /spawn` with a path-traversal id → 400) + static/grep check that `instanceDir`/`ledgerPath` are the only two `path.join(..., id, ...)`-shaped functions in the codebase and both call `isValidId` before their `path.join` — hardened in Phase 5 as part of PROP-003's `fast-check` id-pair fuzz corpus (path-traversal-shaped ids included, not just prefix/substring collisions) |
| PROP-020 | **`POST /fund`/`POST /trade`/`POST /redeem` require `Authorization: Bearer <VINEYARD_API_KEY>` (constant-time comparison via `crypto.timingSafeEqual`, never `===` on the raw header); a missing/wrong token → `401` and the underlying engine is never invoked; the API server refuses to start at all (`process.exit(1)`) if `VINEYARD_API_KEY` is unset; `POST /spawn`/`GET /list`/`GET /status/:id`[`/full`]/`POST /run` remain deliberately unauthenticated** — REQ-020 (closes FIND-006: no auth on money-moving API routes) | 1 | **true** | node:test (`api/server.test.mjs`: no-header→401 + never-reaches-engine, wrong-token→401, correct-token→passes-auth-gate, `/spawn`/`/list`/`/status`→no-auth-required) + static/grep check that `requireApiKey` middleware is applied to exactly `{/fund, /trade, /redeem}` and nowhere else |

## Verification Strategy

- **Tier 0** (no formal proof needed — structural/manual code inspection is sufficient because the
  property is a static shape/parity fact, not a runtime behavior): PROP-001 (scaffold shape), PROP-015
  (CLI/API verb parity), PROP-016 (`llms.txt`/`openapi.json` validity + sync). These are checked by
  diffing file trees/route tables and by `JSON.parse`, not by executing the system under varied inputs.
- **Tier 1** (property tests / fixture-based unit tests — `node:test` + `assert/strict` for all `.mjs`
  modules, the retained Python `test_redeem.py` pure-function tests for the untouched redeem helpers):
  PROP-002, 004, 005, 007, 008, 009, 010, 011, 013, 014, 017, 018, **020**. Each of these is covered by a
  concrete, already-specified test file in the ground-truth plan (Tasks 2, 4, 5, 7, 8, 9, 10, 11, 13, 14,
  17, 18, **15's `api/server.test.mjs`**) testing the deterministic wrapper/parser/bookkeeping/auth logic
  against real-format fixtures or dependency-injected fakes — never a live network/chain call. PROP-020
  is Tier 1, not Tier 2, because bearer-token auth is a fixed, small, fully-enumerable state space
  (present-correct / present-wrong / absent) — no fuzz corpus adds coverage a handful of example-based
  tests don't already give.
- **Tier 2** (lightweight formal methods — property-based fuzzing over the input space + exhaustive
  call-path enumeration, standing in for a full model-checker given this stack has no Rust component):
  PROP-003 (fail-closed key isolation — the ambient-override footgun FIND-001/FIND-002 identified in the
  Phase 1c spec-review gate is now structurally removed from `core/wallet.mjs`; Phase 5 hardens this
  property by (a) `fast-check` generating many adversarial instance-id pairs to fuzz the id-scoped
  file-resolution boundary, and (b) re-running the "ambient env var has zero effect" regression test to
  confirm the deleted override branch has not silently reappeared — since this is money-safety-critical
  and a handful of example-based tests, while necessary, are not sufficient on their own to claim "never"
  for an unbounded id space), PROP-006 (bridge-onramp-only funding — exhaustive enumeration of every call
  path from the `fund` verb to a chain-touching operation, showing all of them terminate in the one
  approved subprocess), PROP-012 (Solana `HOME`-scoped isolation — repeatable, structural directory-tree
  verification across multiple instance ids, not a single anecdotal run), **PROP-019** (id-format
  validation at every per-id path-construction choke point — Tier 2, not Tier 1, because the safe/unsafe
  id shape space is effectively unbounded (arbitrary strings, arbitrary `../` depth, arbitrary special
  characters) and Phase 5 hardens the example-based `core/wallet.test.mjs`/`core/ledger.test.mjs` tests
  by folding path-traversal-shaped ids into the SAME `fast-check` id-pair generator already used for
  PROP-003, rather than trusting a fixed, hand-picked list of "obviously bad" strings to be exhaustive).
- **Tier 3** (strong formal proof): **none required for this feature.** This codebase is Node.js/Python/
  Bash; SMT-based tools like Kani are Rust-specific and do not apply. If a stronger guarantee is later
  desired for PROP-003 specifically, `core/wallet.mjs`'s key-resolution logic has a small, finite branch
  space (per-instance file → `null` — there is no ambient env-override branch to model at all, that
  branch has been deleted) that would be amenable to a lightweight model-checking tool (e.g. TLA+ on the
  resolver's state machine) as a future stretch item — this is explicitly NOT blocking Phase 6 for this
  feature; Tier 2's exhaustive/property-based coverage is the accepted bar.

## Phase 5 hand-off notes

- `verification/purity-audit.md` (Phase 5) should diff the Purity Boundary Map above against `grep -n
  "fs\.\|child_process\|execFile\|spawn(\|fetch(\|requests\." across every file this document classifies
  as "pure" — any hit is a declared-vs-observed boundary violation to resolve before Phase 6.
- `verification/security-report.md` (Phase 5) should specifically re-verify PROP-003 (isolation, INCLUDING
  a grep confirming `core/wallet.mjs` contains zero references to `VINEYARD_EVM_PRIVATE_KEY`/
  `VINEYARD_SOLANA_PRIVATE_KEY` — the ambient-override code path must never silently reappear),
  PROP-004 (no key leak in registry), PROP-010 (no hardcoded founder-wallet fallback survives in the
  copied `redeem.py`), PROP-018 (no fake/mock/dry-run code path), **PROP-019** (id-format validation at
  every per-id path choke point — `core/wallet.mjs`'s `instanceDir` AND `core/ledger.mjs`'s `ledgerPath`,
  confirmed via the same `fast-check` id-pair fuzz corpus as PROP-003, INCLUDING path-traversal-shaped
  ids per FIND-007), and **PROP-020** (API-key auth on `/fund`/`/trade`/`/redeem`, INCLUDING a grep
  confirming `requireApiKey` is applied to exactly those 3 routes and nowhere else) as its money-safety
  core — this closes the exact gap FIND-007 identified: the Phase 5 hand-off list, as originally
  written, would have let both FIND-005 and FIND-006's regression classes ship to Phase 6 undetected.
- All 12 `required: true` proof obligations above must reach `status: "proved"` in `state.json` before
  this feature can transition to `complete` (schema-enforced by `GATE_PREREQUISITES['6']`/
  `validateConvergenceForCompletion`).
