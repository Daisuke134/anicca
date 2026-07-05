# Vineyard MVP — Behavioral Specification (VCSDD Phase 1a, strict mode)

**Feature**: `vineyard-mvp` · **Mode**: strict (real crypto wallets, private keys, on-chain money movement)
**Ground truth**: `docs/superpowers/specs/2026-07-05-vineyard-hackathon-design.md` (design, §0-11) +
`docs/superpowers/plans/2026-07-05-vineyard-mvp.md` (18-task TDD plan, incl. discrepancy table D1-D9 —
treated as authoritative over the design spec's original assumptions wherever they conflict).
**Scope**: spec TODO items **B-I** of the design (repo scaffold, wallet spawn, Polymarket bridge fund,
all 4 engines wired, earn loop, llms.txt+REST+OpenAPI, README quickstart). **Explicitly out of scope**
for this feature's DONE gate: TODO **G** (Web App UI), **J** (hyperframes demo video), **K** (submission
docs copy pass) — these need their own follow-up VCSDD features once this backend is real and running
(see "Scope boundary note" at the end of this document).

## Purity boundary analysis (summary — full map in verification-architecture.md)

- **Pure/deterministic core (candidates)**: `base58()` keygen encoding, `pickEngine()` (brain.mjs),
  `realizedPnl()`'s summation arithmetic, all `parse*Output()` / `lastLines()` string-and-JSON parsers
  (polymarket.mjs, hyperliquid.mjs, solana.mjs), `cost-basis.mjs`'s `adjust()`/`seedIfEmpty()` arithmetic.
  These take explicit inputs (a string, a plain object) and return a value with no I/O of their own.
- **Effectful shell**: `wallet.mjs`'s `generateWallet()`/`resolveEvmPrivateKey()`/`resolveSolanaSecret()`
  (filesystem read/write of key material), `registry.mjs` (spawns.json read/write), `ledger.mjs`'s
  `appendLedger()`/`readLedger()` (filesystem), every engine's `run()`/`fund()`/`trade()`/`redeem()`/
  `setup()` (child_process exec/spawn — real subprocess + real on-chain broadcast), `loop.mjs`'s
  `runOnce()`/`runLoop()` (orchestrates all of the above), and the CLI/API layers.

## Edge case catalog (cross-cutting — see also per-requirement Edge Cases below)

- **Empty inputs**: empty engine stdout (fund/trade/redeem parsers), empty candidate list (brain
  picker), empty ledger file (realizedPnl/readLedger), a `spawns.json` that doesn't exist yet.
- **Boundary values**: cost-basis withdraw larger than current basis (must floor at 0, never negative);
  `realizedPnl` on a line with neither `net_usdc` nor `earn_usdc`/`cost_usdc` (must be 0, never `NaN`).
- **Concurrent/multi-instance access**: two instances spawned under one `VINEYARD_HOME` must never read
  or write each other's `wallet.json`/`solana.json`/`cost-basis.json`/`.blockrun/` state.
- **Error conditions**: duplicate spawn id (registry rejects), unknown id passed to `status`/`redeem`
  (fail closed, not a crash), a fresh deployment's very first Polymarket registration with no
  already-registered `SOURCE_KEY` available (D8 — the underlying script errors explicitly, does not hang).

## Non-functional requirements

- **Performance bounds (subprocess timeouts, per plan Tasks 8-12)**: Polymarket fund ≤300s, Polymarket
  trade ≤120s, Polymarket redeem ≤300s, Hyperliquid calls ≤60s, Solana engine run ≤600s. A wrapper must
  not block indefinitely on a hung child process.
- **Security constraints**: `wallet.json`/`solana.json` are written `chmod 600`. Private key material
  (`privateKey`, `secretKey`, `secretKeyBytes`) is NEVER returned by `resolveAddresses()`, `GET /list`,
  `GET /status/:id`, or logged to stdout/ledger — only public addresses and public-safe metadata cross
  those boundaries.
- **Reproducibility/supply-chain**: Python dependency versions are pinned exactly to the versions
  verified installed in the real anicca venvs (plan D9: `polymarket-client==0.1.0b13`,
  `hyperliquid-python-sdk==0.24.0`, `eth-account==0.13.7`, `python-dotenv==1.2.2`, `web3==7.16.0`,
  `requests==2.34.2`) — no invented package names or unpinned floating versions for the money-moving path.
- **Fail-closed default**: every resolver/wrapper/loop function that cannot proceed safely (missing key,
  missing deposit wallet, empty subprocess output, unspawned instance id) returns a null/skip/clear-error
  result rather than throwing an unhandled exception or silently fabricating a success.

---

## Requirements

### REQ-001: Repo scaffold and structure
**EARS**: WHEN the Vineyard repo is initialized THE SYSTEM SHALL create the standalone directory tree
(`cli/ api/ core/ engines/{lib,python/{polymarket,hyperliquid},shell/solana} data/{ledgers,instances}`),
a `package.json` declaring `bin: vineyard`, Node `>=20`, and `@blockrun/franklin-trading` as an
`optionalDependency`, plus a `.gitignore` that excludes `node_modules/`, `engines/python/.venv/`,
`data/instances/`, `data/spawns.json`, `data/ledgers/*.jsonl`, and `.env`.
**Edge Cases**:
- Re-running scaffold on an already-initialized directory must not silently overwrite an existing
  `data/spawns.json` or `data/instances/` (those are gitignored precisely so a re-clone never inherits
  another deployment's wallets).
**Acceptance Criteria**:
- `git -C ~/vineyard log --oneline` shows a scaffold commit before any wallet/engine code is committed.
- `~/vineyard` is a **separate repo**, never a subdirectory of the anicca monorepo (design §1).

### REQ-002: Per-instance wallet generation (idempotent, isolated)
**EARS**: WHEN `vineyard spawn` (or `core/wallet.mjs`'s `generateWallet(id)`) is called for an instance id
THE SYSTEM SHALL create (or, if already present, return unchanged) an EVM keypair (`viem`
`generatePrivateKey`/`privateKeyToAccount`) and a Solana ed25519 keypair (Node `crypto.generateKeyPairSync`
+ base58) persisted at `<VINEYARD_HOME>/instances/<id>/{wallet.json,solana.json}`.
**Edge Cases**:
- Re-spawning the SAME id must be idempotent — it must return the identical EVM + Solana address on the
  second call, never regenerate (plan Task 2, test "generateWallet: idempotent").
- Two DIFFERENT ids must always get two different wallets (never accidental key reuse).
- `VINEYARD_HOME` unset defaults to `$HOME/.vineyard`; an explicit `VINEYARD_HOME` env override always wins.
**Acceptance Criteria**:
- `core/wallet.test.mjs` (plan Task 2) passes: address format `0x[0-9a-fA-F]{40}` for EVM, non-empty
  base58 string for Solana, both `wallet.json` and `solana.json` exist on disk after generation.

### REQ-003: Fail-closed key isolation — CRITICAL, single most important requirement in this feature
**EARS**: WHEN any code path (a wrapper, the loop, the CLI/API) resolves a private key for instance id
`X` THE SYSTEM SHALL resolve ONLY the key material stored under `<VINEYARD_HOME>/instances/X/`
(or the global env override, which is a single-process-invocation convention, not a cross-instance
leak path) and SHALL NEVER read, fall back to, or return another instance's key — a resolution for an
unspawned or foreign id SHALL return `null`, never throw, and never silently substitute someone else's key.
**Edge Cases**:
- Instance B has no wallet yet → `resolveEvmPrivateKey('B')`/`resolveSolanaSecret('B')` return `null`,
  never throw, and never fall back to instance A's key (plan Task 3, "FAIL-CLOSED" tests).
- Instance A and instance B are both spawned → `resolveEvmPrivateKey('A') !== resolveEvmPrivateKey('B')`,
  and each independently re-derives to its own recorded address (plan Task 3, "ISOLATION" test, verified
  via an independent `viem` re-derivation, not just trusting `wallet.mjs`'s own bookkeeping).
- A malformed or corrupted `wallet.json` for id `X` must resolve to `null` for `X`, not throw, and must
  never cause a fallback read of any other instance's directory.
- This is the ONE property that, if it silently regressed, would let a bug in one instance's code path
  drain a different instance's real funds — treat any weakening of this boundary as a P0 defect.
**Acceptance Criteria**:
- `core/wallet.test.mjs` (plan Tasks 2-3) — 9 tests total, 0 failures, including the 4 explicit
  isolation assertions added in Task 3, already implemented and passing per the ground-truth plan.
- No function in `core/wallet.mjs` ever iterates over `<VINEYARD_HOME>/instances/*` to find a "similar"
  or "legacy shared" wallet — the anicca-specific legacy-shared-`$HOME`-fallback branch is intentionally
  NOT ported (plan Task 2 introduction) because a fresh repo has no such convention to honor and every
  such fallback is a potential isolation leak.

### REQ-004: Spawn registry — public-safe metadata only
**EARS**: WHEN an instance is registered (`registerSpawn`) THE SYSTEM SHALL persist only public-safe
fields (`id, evm, solana, fund, engine, created`) to `<VINEYARD_HOME>/spawns.json`, SHALL reject
registering a duplicate `id`, and SHALL NEVER write private key material into the registry file.
**Edge Cases**:
- `readRegistry()` on a fresh `VINEYARD_HOME` with no `spawns.json` yet returns `[]`, never throws.
- `registerSpawn` with an id already present throws a clear `already registered` error rather than
  silently overwriting the existing row (which could orphan or shadow an existing wallet's metadata).
- `findSpawn` for an unknown id returns `null`, never throws.
**Acceptance Criteria**:
- `core/registry.test.mjs` (plan Task 4) — 5 tests, 0 failures.
- Static/structural check: no code path in `registry.mjs`/`cli/index.mjs`/`api/server.mjs` ever passes
  `wallet.privateKey`/`solana.secretKey` into a `registerSpawn`/`updateSpawn` call.

### REQ-005: On-chain-verified-only ledger — never paper/simulated P&L
**EARS**: WHEN an engine pass produces a result THE SYSTEM SHALL append exactly one JSONL line to
`data/ledgers/<id>.jsonl` carrying either a real transaction/subprocess-derived outcome (`net_usdc`, or
`earn_usdc`/`cost_usdc`, with a real `tx` hash where applicable) or an honest `status: "skip"`/`"wait"`
marker for a reasoned no-trade pass — and SHALL NEVER record a fabricated, hypothetical, or paper-traded
P&L number.
**Edge Cases**:
- `realizedPnl` sums `net_usdc` when present, else falls back to `earn_usdc - cost_usdc`, else contributes
  `0` for a skip/wait line — the sum must be `Number.isFinite`, never `NaN`, regardless of which lines
  are present (plan Task 5, all 5 `ledger.test.mjs` cases).
- A ledger read on an instance with no jsonl file yet returns `[]`, never throws.
- Two different instance ids' ledgers must never mix — `readLedger('z2', dataDir)` must never include a
  line appended for `'z3'`.
**Acceptance Criteria**:
- `core/ledger.test.mjs` (plan Task 5) — 5 tests, 0 failures.
- `core/loop.mjs`'s `normalizeResult()` is the only place that shapes an engine's raw result into a
  ledger line, and it always derives `net_usdc` from the engine's own real returned fields — it never
  invents a P&L value that the engine itself did not report.

### REQ-006: Polymarket bridge-onramp fund registration — never a raw transfer
**EARS**: WHEN `vineyard fund <id> <amount>` (or `POST /fund`) is called THE SYSTEM SHALL register and
fund the instance's Polymarket deposit wallet EXCLUSIVELY by invoking the copied `fund_via_bridge.py`
(bridge Collateral Onramp) — THE SYSTEM SHALL NEVER raw-deploy a deposit wallet or raw-transfer pUSD
outside that onramp path (design §8, money-safety invariant #2).
**Edge Cases**:
- `parseFundOutput` must handle BOTH the "already-registered" branch
  (`{deposit_wallet, registered:true, already:true}`) and the "fresh-registration" branch
  (`{deposit_wallet, bridge_address, registered:true, balance_usdc}`) — both are real fixture shapes
  read from `fund_via_bridge.py`'s own `main()` (plan Task 8).
- Empty stdout from the child process throws a clear `no output` error rather than returning `undefined`
  (plan Task 8, test "throws a clear error on empty stdout").
**Acceptance Criteria**:
- `engines/polymarket.test.mjs` fund-half tests (plan Task 8) — 3 tests, 0 failures.
- `engines/python/polymarket/fund_via_bridge.py` is copied byte-for-byte, zero edits (verified: it
  already reads all inputs from env vars and has a proper `__main__` guard — plan Task 8 intro).
- Manual (non-automated) verification note is present and distinct from the automated test: a real
  bridge registration is confirmed separately via `get_balance_allowance` resolving (design DONE §9.2).

### REQ-007: Polymarket bootstrap — the D8 chicken-and-egg SOURCE_KEY requirement
**EARS**: WHEN a brand-new Vineyard deployment attempts its VERY FIRST Polymarket bridge registration
(no instance's deposit wallet is registered yet) THE SYSTEM SHALL require an explicit `sourceKey`
(env `SOURCE_KEY`, CLI `--source-key`) belonging to an ALREADY-REGISTERED Polymarket wallet — THE SYSTEM
SHALL NOT attempt to self-bootstrap registration from the new, still-unregistered instance's own key,
and SHALL surface the underlying script's own explicit error rather than hanging or silently no-op'ing.
**Edge Cases**:
- This is the one documented human-provided seed touchpoint the design's own architecture diagram already
  accounts for ("human → one-time crypto seed", design §2) — it must be documented in README/llms.txt as
  such, not silently glossed over as if it "just works" for every deployment (plan discrepancy D8).
- A subsequent instance CAN use any prior Vineyard instance's already-registered deposit wallet as its
  `SOURCE_KEY`, so only the very first registration on a given deployment needs the operator's own
  polymarket.com-onboarded wallet.
**Acceptance Criteria**:
- README "First-time setup" and `llms.txt` "Notes for an agent driving this repo" both state the
  bootstrap requirement explicitly (plan Task 16 §"Notes", Task 17 §"First-time setup").
- `fund({sourceKey})` wrapper param plumbing is present (plan Task 8, `engines/polymarket.mjs`'s `fund()`).

### REQ-008: Yield engine — Aave/Morpho/Fluid deposit (Node, param-scoped per instance)
**EARS**: WHEN the automatic loop or an operator invokes the yield engine (`engines/yield.mjs`'s `run()`)
THE SYSTEM SHALL deposit idle USDC to Aave/Morpho/Fluid using the resolved instance's EVM private key
passed as an explicit parameter (never resolved internally by the engine itself), and SHALL scope its
cost-basis bookkeeping (`engines/lib/cost-basis.mjs`) to a per-instance `filePath` rather than one
anicca-style shared-`$HOME` file.
**Edge Cases**:
- `run({evmPrivateKey: null})` fails closed: returns `{abort: "no wallet key"}`, never throws (plan
  Task 7, `yield.test.mjs`).
- Two different instances' cost-basis files must never mix state (plan Task 7, cost-basis test "two
  different files (two instances) never mix state").
- `recordWithdraw` floors the venue basis at 0, never negative (plan Task 7, cost-basis test).
**Acceptance Criteria**:
- `engines/cost-basis.test.mjs` (5 tests) + `engines/yield.test.mjs` (1 test), 0 failures.
- A REAL deploy/refill/hold pass against a funded EVM wallet is a documented, separate manual
  verification step (plan Task 7 Step 10) — not claimed as covered by the automated unit test.

### REQ-009: Polymarket TRADE engine — parameterized `place_order.py` (D1)
**EARS**: WHEN an operator or LLM agent calls `vineyard trade <id> --engine pm` (or `POST /trade`) with
an explicit `tokenId`, `side`, `amountUsd`, `maxPrice` THE SYSTEM SHALL submit a real FAK market order via
the NEW parameterized `engines/python/polymarket/place_order.py` (derived from `v2_full_flow.py`'s exact
proven call sequence — SIWE mint → `SecureClient.create` → approve neg-risk spenders →
`create_market_order(order_type="FAK")` → `post_order` — but parameterized via argparse instead of
hardcoded constants, per plan discrepancy D1) — THE SYSTEM SHALL NEVER shell out to the original
`v2_full_flow.py` directly, since that script is a hardcoded one-off with no argparse/`__main__` guard.
**Edge Cases**:
- `parseTradeOutput` parses the single compact JSON line `place_order.py` prints; empty stdout throws a
  clear `no output` error (plan Task 9).
- Side/size/market selection is supplied by the CALLER, never inferred/hardcoded by
  `engines/polymarket.mjs` or `core/brain.mjs` — see REQ-013 (no hardcoded trading judgment).
**Acceptance Criteria**:
- `engines/polymarket.test.mjs` trade-half tests (plan Task 9) — 3 additional tests (6 cumulative), 0
  failures.
- A real order placement against a real open market's `token_id` is a documented, separate manual
  verification step (plan Task 9 Step 6), confirmed via a real `order_id` and a matched fill on
  `data-api.polymarket.com/positions` — never claimed via the unit test alone.

### REQ-010: Polymarket REDEEM engine — copy + 4 documented edits (D6)
**EARS**: WHEN an operator or the automatic loop invokes redeem (`engines/polymarket.mjs`'s `redeem()`)
THE SYSTEM SHALL collect already-resolved Polymarket winnings via the copied `redeem.py`, with its
`DEPOSIT_WALLET` resolved from `os.environ["POLYMARKET_DEPOSIT_WALLET"]` (never Dais's hardcoded founder
wallet `0x904B50d2...`), its relayer-key cache path scoped per instance via
`POLYMARKET_RELAYER_CACHE` (default `~/.vineyard/.pm-relayer-apikey`), and with the external
anicca-specific `~/anicca/skills/earn/lib/record.mjs` ledger writer call removed — `core/ledger.mjs` is
the sole ledger writer for Vineyard.
**Edge Cases**:
- `DEPOSIT_WALLET = os.environ["POLYMARKET_DEPOSIT_WALLET"]` must raise (fail closed) if the env var is
  absent — it must NEVER silently fall back to Dais's real founder wallet constant that existed in the
  original anicca script.
- `parseRedeemOutput` returns `[]` (not an error) for a genuine "nothing to redeem" outcome, and returns
  one row per redeemed condition (0..N) for a real redemption pass (plan Task 10).
- All 4 edits (DEPOSIT_WALLET/env, `AGENT_ENV`/`load_dotenv` removal, relayer-cache rescoping, ledger-call
  removal) must leave every on-chain money-safety code path (CTF operator approval, neg-risk dispatch,
  registry checks, `fetch_receipt_status`'s independent RPC confirmation) byte-identical/untouched.
**Acceptance Criteria**:
- `engines/polymarket.test.mjs` redeem-half tests (plan Task 10) — 3 additional tests (9 cumulative), 0
  failures. `test_redeem.py`'s existing pure-function tests (`dedupe_redeemable_conditions`,
  `classify_market_type`, `compute_recovered_amount`, `build_ledger_line`) still pass unmodified.
- A real redeem pass against an already-resolved market position is a documented, separate manual
  verification step (plan Task 10 Step 8) confirming a real `tx_hash` with `status=0x1`.

### REQ-011: Hyperliquid engine — `hl.py` copied verbatim, key injected (D7)
**EARS**: WHEN an operator calls a Hyperliquid primitive (`account`/`market`/`open`/`close` via
`engines/hyperliquid.mjs`) THE SYSTEM SHALL copy `hl.py` with ZERO edits and SHALL ALWAYS inject the
instance's resolved EVM private key into the child process as `BLOCKRUN_WALLET_KEY`, so `hl.py`'s own
env-first key resolution branch always short-circuits before ever reaching its fragile hardcoded
relative-path `resolve-identity.mjs` subprocess fallback (which assumes anicca's directory layout and
would not resolve correctly inside Vineyard's repo layout).
**Edge Cases**:
- `parseHlOutput` must `JSON.parse` the WHOLE trimmed stdout (not just the last line) because `hl.py`'s
  `cmd_*` functions each print one pretty-printed (`indent=2`), multi-line JSON object — unlike the
  Polymarket scripts' compact single-line JSON (plan Task 11).
- Must correctly parse all 4 real shapes: `account` (`account_value_usd`, `withdrawable_usd`,
  `open_positions`), `market` (`coin`, `price`, `change_pct_window`), `open` (`opened`, `entry`, `size`,
  `stop_loss`, `take_profit`), and the "already-open" skip shape (`skipped`, `szi`).
**Acceptance Criteria**:
- `engines/hyperliquid.test.mjs` (plan Task 11) — 5 tests, 0 failures.
- A real account/market read + a real open/close pass against a funded Hyperliquid account is a
  documented, separate manual verification step (plan Task 11 Step 6) — an actual directional judgment
  call is explicitly NOT automated or fabricated by this wrapper.

### REQ-012: Solana engine — wraps `franklin-trading` CLI, HOME-scoped isolation (D3/D4/D5)
**EARS**: WHEN the automatic loop or an operator invokes the Solana engine (`engines/solana.mjs`'s
`run()`/`setup()`) THE SYSTEM SHALL shell to the copied `run.sh`, which itself invokes the globally
installed `@blockrun/franklin-trading` CLI — a separate autonomous trading agent that does its OWN
research/sizing/execution and pays its own model calls via x402 — and SHALL isolate that agent's own
wallet/session store per instance by spawning it with `HOME` set to
`<VINEYARD_HOME>/instances/<id>/` (reusing `core/wallet.mjs`'s existing `instanceDir(id)` boundary),
so that instance X's `.blockrun/` state never collides with instance Y's or with the real `~/.blockrun/`.
**Edge Cases**:
- `run.sh` is copied minus exactly ONE line (the anicca-specific telemetry POST to
  `runtime/dashboard/telemetry-post-franklin.mjs`, D5) — every other line (kill-switch, prompt,
  `franklin-trading start` invocation, trace write) is byte-identical.
- Output is FREEFORM TEXT, not JSON — `lastLines(text, n)` returns the last N non-empty lines, matching
  `run.sh`'s own existing OUTTAIL pattern; a shorter input than N returns everything available (plan
  Task 12).
- HOME-scoped isolation is empirically verified, not assumed: `HOME=<tmp> franklin-trading setup solana`
  creates an isolated `<tmp>/.blockrun/{.solana-session,payment-chain}`, distinct from the real
  `~/.blockrun/` (plan Task 12 Step 3, a real harmless local-keygen-only invocation).
**Acceptance Criteria**:
- `engines/solana.test.mjs` (plan Task 12) — 3 tests, 0 failures.
- `which franklin-trading` resolves to a real binary (declared as an `optionalDependency` in
  `package.json`, Task 1).
- A real funded Solana swap/WAIT pass is a documented, separate manual verification step (plan Task 12
  Step 8) — both a filled swap and a reasoned WAIT are valid real outcomes; a fabricated fill is not.

### REQ-013: `core/brain.mjs` — deterministic engine picker, NEVER hardcoded trading judgment
**EARS**: WHEN the automatic `vineyard run` loop needs to pick which engine to invoke this pass THE
SYSTEM SHALL select deterministically among ONLY the engines safe to invoke unattended with no external
decision required (`yield`, `solana`, `polymarket-redeem`) using round-robin-by-recency bookkeeping
(`pickEngine`) — THE SYSTEM SHALL NEVER hardcode which market, side, or size to trade as a regex/if-else
inside `brain.mjs` or any engine wrapper; that judgment belongs exclusively to whoever calls
`vineyard trade` with explicit parameters (a human operator or an LLM agent), per the project rule
`~/.claude/rules/building-effective-ai-agents.md` ("no hardcoded judgment; the model decides via tools").
**Edge Cases**:
- Hyperliquid `open` (a directional bet) and Polymarket `place_order`/trade (a market/side/size bet) are
  reachable ONLY via the explicit `trade` command (REQ-009/REQ-015) — NEVER via the automatic candidate
  list. This is a deliberate scope decision, documented here and in the plan (Task 13), not an oversight.
- With no run history, `pickEngine` picks the first candidate deterministically; with history, it picks
  whichever candidate ran longest ago (or never); an empty candidate list returns `null`, never throws
  (plan Task 13, all 4 test cases).
**Acceptance Criteria**:
- `core/brain.test.mjs` (plan Task 13) — 4 tests, 0 failures.
- Code inspection: `AUTOMATIC_ENGINES` (or equivalent candidate universe consumed by the `run`
  CLI/API verb) contains exactly `['yield', 'solana', 'polymarket-redeem']` — no code path adds
  `hyperliquid` or a Polymarket trade/place-order action to that automatic set.

### REQ-014: `core/loop.mjs` — wake → pick → earn → ledger, fails closed
**EARS**: WHEN `runOnce`/`runLoop` executes one pass for instance `id` THE SYSTEM SHALL: pick an engine
via `core/brain.mjs`, resolve that engine's required key via `core/wallet.mjs`, invoke the (dependency-
injected) engine module, normalize its result, and append exactly one ledger line via `core/ledger.mjs`
— and WHEN the required key/deposit-wallet is missing THE SYSTEM SHALL write an honest `status: "skip"`
ledger line (with a `reason` field) instead of throwing or fabricating a result.
**Edge Cases**:
- No wallet yet for the picked engine's chain → writes a `{status:"skip", reason:"no-evm-key"}` (or
  `"no-solana-key"`/`"no-deposit-wallet"`) ledger line, never throws (plan Task 14, test 1).
- With a spawned wallet, the picked engine's `run()` is called with the resolved key as an explicit
  parameter and its real result (e.g. `{kind:"yield", action:"hold", ...}`) is recorded (plan Task 14,
  test 2).
- A `polymarket-redeem` result (an ARRAY of per-condition rows) is normalized into ONE ledger line with a
  summed `net_usdc` and a `tx` array — e.g. two rows `(10-3)+(5-5) = 7` (plan Task 14, test 3).
- `engines` are always dependency-injected (never hardcoded module imports inside `loop.mjs`) so
  `core/loop.test.mjs` never makes a real network/subprocess call — production callers (`cli/index.mjs`,
  `api/server.mjs`) pass the real engine modules.
**Acceptance Criteria**:
- `core/loop.test.mjs` (plan Task 14) — 3 tests, 0 failures.
- Every reachable branch of `runOnce` resolves to a return value (a ledger line); none reject/throw
  (this is also PROP-014 in verification-architecture.md).

### REQ-015: CLI + REST API verb parity
**EARS**: WHEN a capability is exposed via the CLI (`vineyard spawn|fund|run|status|list|trade|redeem`)
THE SYSTEM SHALL expose the IDENTICAL capability via an HTTP verb with equivalent semantics
(`POST /spawn`, `POST /fund`, `POST /run`, `GET /status/:id[/full]`, `GET /list`, `POST /trade`,
`POST /redeem`) — so an agent driving Vineyard over HTTP can do everything a human can do over the CLI,
with no CLI-only or API-only capability gap.
**Edge Cases**:
- `spawn`/`fund`/`run`/`trade`/`redeem` share the SAME underlying `core/*` + `engines/*` functions in
  both the CLI dispatcher and the Express route handler (plan Task 6, Task 15) — no duplicated,
  divergent logic between the two surfaces.
- `dashboard` (CLI) has no HTTP equivalent yet because the Web App UI (design TODO G) is explicitly
  out of scope for this feature (see Scope boundary note) — the CLI command prints a clear message
  rather than silently doing nothing.
**Acceptance Criteria**:
- `cli/index.mjs`'s command list and `api/server.mjs`'s route list match 1:1 for every in-scope verb
  (spawn/fund/run/status/list/trade/redeem), verified by smoke tests in plan Tasks 6 and 15 (both a
  direct CLI invocation and a `curl` HTTP call against a scratch `VINEYARD_HOME`/`VINEYARD_DATA_DIR`).

### REQ-016: `llms.txt` + `openapi.json` — machine-readable, zero-human-click agent path
**EARS**: THE SYSTEM SHALL ship an `llms.txt` documenting every CLI verb and its equivalent HTTP verb in
one-line usage form, and an `openapi.json` describing every REST route's request/response shape, so that
another AI agent can spawn/fund/run/monitor Vineyard instances entirely programmatically without a human
click and without an MCP server (design §1: "No MCP — CLI + REST API + llms.txt already give an agent a
machine-readable path").
**Edge Cases**:
- `openapi.json` must be valid, parseable JSON (plan Task 16 Step 3: `JSON.parse` succeeds).
- `llms.txt` must document the D8 bootstrap requirement (REQ-007) and the "no dry run — a skip/wait is
  honest, never fabricated" invariant (REQ-018) explicitly, not just the happy path.
**Acceptance Criteria**:
- `node -e "JSON.parse(...); console.log('valid JSON')"` on `openapi.json` succeeds (plan Task 16).
- Every path documented in `llms.txt` has a corresponding `paths` entry in `openapi.json` and a
  corresponding route in `api/server.mjs` (REQ-015 parity extended to the machine-readable docs).

### REQ-017: README — one-command quickstart, verified from a clean clone
**EARS**: THE SYSTEM SHALL ship a `README.md` whose documented quickstart sequence (`npm install`,
create the Python venv, install pinned requirements, `node cli/index.mjs spawn --fund N`) SHALL succeed
end-to-end when run against a genuinely clean `git clone` of the repository — NOT merely against the
existing working tree's untracked scratch state — so that "any agent can download this with ease"
(design §1) is a verified property, not an aspiration.
**Edge Cases**:
- The clean-clone quickstart must be exercised at least twice as an acceptance gate: once right after
  writing the README (plan Task 17 Step 2) and once again as the final integration check after all other
  tasks are committed (plan Task 18 Step 3) — a passing run right after writing the README does not
  guarantee later commits didn't silently break the quickstart.
- A stale `node_modules/`, a pre-existing `.venv/`, or leftover `data/instances/` in the WORKING tree must
  never be what makes the quickstart "pass" — the verification clone must be a fresh `git clone` into a
  scratch directory with none of that state, per `.gitignore` (REQ-001).
**Acceptance Criteria**:
- `git clone ~/vineyard /tmp/<scratch>` → `npm install` → venv + pinned `pip install` → `spawn --fund N`
  all succeed with exit code 0 and print a real JSON row with a `0x...` EVM address and a base58 Solana
  address (plan Task 17 Step 2, Task 18 Step 3). This satisfies design DONE criterion §9.6.

### REQ-018: No dry run — automated-test boundary vs. real on-chain pass (HARD RULE 0.24)
**EARS**: THE SYSTEM SHALL NEVER simulate, mock, or fabricate a trade/fund/redeem outcome and present it
as if it were real — every engine's `run()`/`fund()`/`trade()`/`redeem()` call against a real key IS a
real pass with real on-chain consequences (a real fill, a real skip, or a real honest WAIT) — and THE
SYSTEM'S automated test suite SHALL cover ONLY the deterministic wrapper/parser logic (via real-format
stdout fixtures and dependency injection), while the actual trade pass against a funded wallet SHALL be
documented as a SEPARATE, explicitly-labeled manual verification step, never silently conflated with
"unit tested" or "verified."
**Edge Cases**:
- Every engine task in the ground-truth plan (Tasks 7-12) carries its own explicit
  "Manual (non-automated) verification note — HARD RULE 0.24" step, distinct from its automated test
  step — this separation must be preserved; a future refactor must not merge or blur the two.
- No `--dry-run` flag exists on any of the underlying Python scripts by design (per plan Task 8 intro)
  — the wrapper must not invent one that produces a fake success without a real subprocess call.
- A `skip`/`wait` ledger line for an unfunded wallet or "no trading edge this pass" is a VALID, HONEST
  outcome — it must never be rewritten upstream (CLI/API/dashboard) into an apparent success.
**Acceptance Criteria**:
- For every engine (yield/polymarket-fund/polymarket-trade/polymarket-redeem/hyperliquid/solana), the
  plan's own task shows an automated test step AND a separately labeled manual verification step — never
  one masquerading as the other (plan Tasks 7 Step 10, 8 Step 8, 9 Step 6, 10 Step 8, 11 Step 6, 12 Step 8).
- Grep-level check: none of the engine `.mjs`/`.py` files contain the literal words
  "fake"/"dry"/"mock"/"dummy"/"simulated" in a code path that would execute during a real invocation.

---

## Scope boundary note (gap flagged between the two ground-truth documents, not silently resolved)

The design spec's §9 DONE criteria (items 1-8) include the Web App UI (item 4) and the hyperframes demo
video (item 7) as part of "done." The implementation plan explicitly scopes itself to TODO items **B-I**
only and calls out G (Web App UI), J (demo video), K (submission docs), and L (VCSDD wrapping) as
out-of-scope, needing their own follow-up plans (plan header + Task 18 Step 6). **This feature's
(`vineyard-mvp`) DONE gate is therefore REQ-001 through REQ-018 above (spec TODO B-I) — it does NOT
include the Web App UI or demo video**, which should be tracked as separate, later VCSDD features once
this backend is real and running. This narrowing is carried over from the plan, not invented here.

A second, related narrowing: the design spec's §2 architecture diagram shows Polymarket's full pipeline
("bridge-fund register → FAK order → auto-redeem") and Hyperliquid's full pipeline ("trend-follow...
always stop+TP") as if `brain.mjs` picks among all 4 engines' complete automatic pipelines. The plan's
Task 13 explicitly narrows this: the AUTOMATIC `vineyard run` loop only rotates among `yield`, `solana`,
and `polymarket-redeem` — Hyperliquid `open` and Polymarket `place_order`/trade are reachable ONLY via
the explicit, human/agent-directed `vineyard trade` command (REQ-009, REQ-013), never picked
automatically. This spec (REQ-013) encodes the plan's narrower, documented scope as the requirement,
not the design diagram's more automatic-sounding framing — flagged here rather than silently invented
one way or the other.
