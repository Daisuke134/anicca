# Verification Architecture — franklin-loop-revival

## Purity Boundary Map

- **Pure Core** (deterministic, no side effects, unit/property testable):
  - `runtime/loop/tier.mjs::selectTier` — UNCHANGED by this feature (existing pure
    tier arithmetic; this feature only fixes the numbers fed into it).
  - New pure predicate this feature introduces — chain-shape classification, e.g.
    `isEvmAddress(address)` / `isSolanaAddress(address)` (or an equivalent single
    `classifyAddress(address) -> 'evm'|'solana'|'invalid'`) used by the extended
    `fetchUsdcBalance` to pick a chain branch. Pure string-shape check, no I/O, no
    network, no filesystem.
  - `runtime/loop/catalog-gate.mjs::filterCatalog` — UNCHANGED, explicitly out of
    scope (see behavioral-spec.md non-goals).

- **Effectful Shell** (I/O, network, process spawn — where this feature's real
  changes live):
  - `runtime/wallet-address.mjs` (extended) or a new sibling Solana address-resolution
    helper: reads `resolve-identity.mjs::resolveSolanaSecret`'s resolved secret from
    disk (`~/.blockrun/.solana-session` or `$ANICCA_HOME/.automaton/solana.json`),
    derives a base58 public key via `@solana/web3.js`'s `Keypair` (already a repo
    dependency — no new dep) + `bs58` (already a repo dependency), prints ONLY the
    address to stdout, and CATCHES any derivation exception from a malformed secret
    (REQ-001's malformed-`.solana-session` edge case) rather than letting it crash
    the daemon.
  - `runtime/loop/balance.mjs::fetchUsdcBalance` (extended): adds a Solana branch that
    calls the existing, already unit-tested
    `skills/_shared/lib/solana-verify.mjs::usdcBalance(wallet, opts)` — REUSED, NOT
    ported/reimplemented (REQ-002; corrects iteration-1's wrong citation of
    `skills/earn/funding/lib/solana_rpc.py::spl_token_balance_units`, which is NOT
    used by this feature). `usdcBalance` already: validates the base58 wallet shape
    and throws on failure, calls `getTokenAccountsByOwner` against
    `SOLANA_RPC_URL`/mainnet default, sums parsed token amounts for mint
    `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` (`solana-verify.mjs:14`, verified
    2026-06-29 per that file's header), and returns `0` (not throw) for zero ATAs.
  - `runtime/anicca-daemon.sh`: the `INSTANCE`-branch wallet-export logic (currently
    lines 119-124, EVM-only, franklin-excluded); the `PORT`-assignment branch
    (currently lines 26-30: `if [ "$INSTANCE" = "franklin" ]; then
    PORT="${FRANKLIN_PROXY_PORT:-8403}" else PORT="${COMPUTE_PROXY_PORT:-8402}" fi`)
    — THIS BRANCH ITSELF MUST CHANGE so franklin's `PORT` resolves to `8402`
    (matching the non-franklin branch) instead of `${FRANKLIN_PROXY_PORT:-8403}`;
    the THINK endpoint/model export logic (currently lines 116-126, exports
    `OPENAI_BASE_URL="http://127.0.0.1:$PORT/v1"` at line 117 using that SAME `$PORT`
    unconditionally — line 117 itself needs no edit once the PORT-assignment branch
    above is fixed, but the branch is NOT optional, see REQ-004/FIND-006); AND the
    `ensure_brain` function for `INSTANCE=franklin` (currently lines 53-75) — this
    branch is changed to a fully specified no-op/readiness-probe-only replacement
    (REQ-004(b)/REQ-005, corrected here per FIND-009): it NEVER spawns
    `franklin proxy --port 8403 --model nvidia/llama-4-maverick --no-fallback`, and it
    is replaced by AT MOST the same `curl -sf http://127.0.0.1:$PORT/v1/models`
    readiness probe (now pointed at 8402) — it MUST NOT spawn any process
    (`clawrouter`, `franklin proxy`, or otherwise) and MUST NOT read
    `$HOME/.openclaw/.env`/`BLOCKRUN_WALLET_KEY`/any other instance's key file; the
    non-franklin branch's `ensure_brain` (lines 82-95, which DOES legitimately grep
    `$HOME/.openclaw/.env` for its OWN, different, per-design-shared use case) stays a
    structurally SEPARATE closure and must never execute for `INSTANCE=franklin`.
    Bringing ClawRouter up is exclusively `ai.anicca.clawrouter`'s own
    `RunAtLoad`+`KeepAlive` launchd job (confirmed live, no wallet key configured —
    free-tier-only), never Franklin's daemon's job. Both the PORT-assignment change
    AND the `ensure_brain` no-op replacement are required; removing only the spawn
    while leaving the PORT-assignment branch deriving `8403` from
    `FRANKLIN_PROXY_PORT` would leave `OPENAI_BASE_URL` pointed at a dead port
    (verified-wrong claim from iteration-2, corrected here per FIND-006); leaving the
    replacement's behavior unspecified (an earlier draft's gap) would allow a
    spec-compliant-but-wrong implementation that collapses the franklin/non-franklin
    branches and reads a cross-instance wallet key (FIND-009, now closed by REQ-004(b)
    and REQ-005's extended edge cases + PROP-016 below).
  - `ai.anicca.franklin-loop.plist`: `ANICCA_MODEL` / `ANICCA_FREE_MODEL` /
    `ANICCA_LEAN_MODEL` / `ANICCA_FUNDED_MODEL` values (currently all pinned to the
    rate-limited `nvidia/llama-4-maverick`) — MUST also be verified to NEVER contain
    an `ANICCA_BALANCE_OVERRIDE` key (REQ-003; this is a negative/absence check on
    the effectful shell's configuration surface, not a new capability).
  - `runtime/loop/brain.mjs::thinkProxy` — NOT modified. Its request body is
    `config.ANICCA_MODEL || ctx.model || 'auto'` (`brain.mjs:58`), but
    `config.ANICCA_MODEL` is ALWAYS `undefined` (corrected here per FIND-010: verified
    against the live `config.mjs` that `ANICCA_MODEL` is in neither its `DEFAULTS`,
    lines 13-62, nor its explicit pass-through list, lines 114-142 — `brain.mjs:58` is
    its only reference in the entire `runtime/` tree, confirmed by grep), so the
    expression ALWAYS falls through to `ctx.model`. `ctx.model` is what is actually
    config-driven: it comes from `tier.mjs::selectTier` reading
    `config.ANICCA_FREE_MODEL`/`ANICCA_LEAN_MODEL`/`ANICCA_FUNDED_MODEL` (which ARE in
    `DEFAULTS` and DO reflect env/plist overrides) and `config.OPENAI_BASE_URL`
    (`brain.mjs:49`, also in `DEFAULTS`). thinkProxy's observed behavior changes only
    because the effectful shell (daemon.sh/plist) now supplies different
    `ANICCA_FREE_MODEL`/`ANICCA_LEAN_MODEL`/`ANICCA_FUNDED_MODEL`/`OPENAI_BASE_URL`
    values, which reach THINK via `ctx.model`, not via `config.ANICCA_MODEL`.

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-001 | `classifyAddress`/`isEvmAddress`/`isSolanaAddress`: for any string, returns exactly one of `evm`/`solana`/`invalid`; a valid `0x`+40-hex string is never classified `solana`; a valid base58 32-byte-decodable string is never classified `evm`; empty/`'unknown'`/malformed strings are always `invalid` | 1 | true | node:test property/boundary table (mirrors existing `tier.test.mjs` style) |
| PROP-002 | `fetchUsdcBalance(address, config)` dispatches to exactly one chain branch per call (never both, never neither) for any address classified by PROP-001 as `evm` or `solana`; the `solana` branch calls `solana-verify.mjs::usdcBalance` (verified by test-double injection of `opts.fetchImpl`, NOT by reimplementing RPC parsing in this feature's own test) and passes its return value straight through (including the `0`-for-zero-ATAs case); an `invalid`-classified address always throws before any network call is attempted | 1 | true | node:test with a fake/mock RPC transport (existing `ANICCA_BALANCE_OVERRIDE` pattern for the EVM side; for the Solana side, inject a fake `fetchImpl` into `usdcBalance`'s existing `opts` parameter — mirroring the test-double convention already used in `skills/_shared/lib/__tests__/solana-verify.test.js` and `skills/earn/clip-promote/tests/fake_solana_rpc.mjs` — NOT a from-scratch Solana RPC mock owned by this feature) |
| PROP-003 | `fetchUsdcBalance('8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9', config)` — via its delegation to `solana-verify.mjs::usdcBalance` — against the real Solana RPC returns a finite, non-negative number matching Franklin's real on-chain USDC balance (live check, not mocked) | 0 | true | live smoke check (`node -e` one-off run against production RPC, result compared against `franklin-trading`'s own last-reported balance in `sol-trade.trace.jsonl`) |
| PROP-004 | Existing EVM `fetchUsdcBalance` behavior (including `ANICCA_BALANCE_OVERRIDE` test hooks, TTL cache, RPC-fallback list) is unchanged for any `0x...` address — full regression of the current `balance.mjs` test suite | 1 | true | existing `node:test` suite for `balance.mjs` (regression, no new tool) |
| PROP-005 | Franklin's wallet-address resolution helper, run with `ANICCA_HOME=/Users/operator/.blockrun ANICCA_INSTANCE=franklin`, prints exactly `8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9` and nothing else to stdout; run with any other `ANICCA_HOME`, prints nothing (no address, no error leaking secret material) | 1 | true | node:test + one live invocation (mirrors existing `resolve-identity.test.mjs` conventions) |
| PROP-006 | `selectTier` is invoked, on a wake where REQ-001/002 both succeed, with the real fetched balance (not a hardcoded `0`) — i.e. `currentTier` after such a wake is never `broke` when real balance > 0 | 1 | true | integration test on `runtime/loop/index.mjs`'s wake function (mirrors existing `integration.test.mjs` conventions) |
| PROP-007 | No code path added by this feature ever reads `~/.blockrun/.solana-session` (or any other instance's wallet/session file) unless the effective `ANICCA_HOME` for the CURRENT process resolves to exactly `$HOME/.blockrun` (mirrors `resolveSolanaSecret`'s existing legacy-home gate) — a foreign `ANICCA_HOME` must resolve null | 2 | true | existing + extended `resolve-identity.test.mjs` exhaustive input-table tests (this is the identity-gate invariant from memory `feedback_earn_identity_resolve_per_instance_gate_on_anicca_home`; treated as Tier 2 because it is a money-safety invariant, not just a functional property) |
| PROP-008 | The address-derivation helper never writes secret material (raw base58 secret, raw 64-byte key bytes) to stdout/stderr/logs under any input, including error paths | 1 | true | node:test asserting captured stdout/stderr never matches the known test-fixture secret string, across success AND induced-failure cases |
| PROP-009 | After the plist/daemon.sh THINK-routing fix, a live HTTP POST to `http://127.0.0.1:8402/v1/chat/completions` with the configured model succeeds (HTTP 200, valid `choices` array) at least 3 consecutive times | 0 | true | live smoke check (`curl`/`node -e` against the real running ClawRouter process — this is inherently an operational fact about a live free-tier quota, not something formally provable) |
| PROP-010 | `~/.blockrun/state/ledger.jsonl` contains zero `kind:"wake_error", error:"proxy_down"` lines in the N wakes immediately following the fix's deployment (N ≥ 3) | 0 | true | live log inspection (Done-condition check, not a unit test) |
| PROP-011 | `skills/earn/state/sol-trade.trace.jsonl` gains at least one new `action:"live-pass"` entry after the fix, produced by a wake where `currentTier.tier != 'broke'` | 0 | true | live log inspection across `~/.blockrun/state/ledger.jsonl` (tier/model at the triggering wake) cross-referenced with the trace file's new entry timestamp |
| PROP-012 | The address-derivation helper, given a fixture `.solana-session`-shaped file whose content is present/non-empty but cryptographically malformed (invalid base58 chars, or valid base58 decoding to the wrong byte length for a Solana secret key), does NOT crash the process (no uncaught exception, no non-zero crash exit distinguishable from a clean "warned and skipped" exit), prints nothing to stdout, and writes a WARNING to stderr that does not contain the fixture's raw secret string (FIND-005 / REQ-001's malformed-secret edge case) | 1 | true | node:test: exhaustive fixture table `{missing, empty, valid, malformed-base58-chars, valid-base58-wrong-length}` × assert on (stdout, stderr, crash/no-crash) — extends `resolve-identity.test.mjs` conventions |
| PROP-013 | The DEPLOYED `ai.anicca.franklin-loop.plist` at `~/Library/LaunchAgents/ai.anicca.franklin-loop.plist` contains no `ANICCA_BALANCE_OVERRIDE` key anywhere under its `<EnvironmentVariables>` dict (FIND-003 / REQ-003) | 0 | true | live artifact check: parse the actual deployed plist file (`plutil -convert json` or `defaults read`/XML parse) and assert absence of the key — not a unit test of a fixture copy |
| PROP-014 | The REAL environment of the running Franklin daemon PROCESS contains no `ANICCA_BALANCE_OVERRIDE` — checked against the process's actual inherited env, not the verifier's own shell (FIND-003 / REQ-003) | 0 | true | live process inspection: `launchctl print gui/$(id -u)/ai.anicca.franklin-loop` (shows the job's configured env) cross-checked with `ps eww <pid>`/`/proc/<pid>/environ`-equivalent for the live supervised loop process — deliberately NOT `env \| grep` in the verifier's own shell, which proves nothing about the deployed daemon |
| PROP-015 | After the fix, (i) no process is listening on `127.0.0.1:8403` for Franklin's daemon (`ensure_brain`'s `franklin proxy --port 8403 ...` spawn for `INSTANCE=franklin` no longer executes, REQ-004(b)) AND (ii) the REAL running franklin-loop daemon PROCESS's actual `OPENAI_BASE_URL`/`PORT` env resolves to ClawRouter's `8402`, NOT merely inferred from (i) — inspected the same way PROP-014 inspects `ANICCA_BALANCE_OVERRIDE` (FIND-002/FIND-006/FIND-008 / REQ-004(a)+(c)) | 0 | true | TWO checks, both required, neither substitutes for the other: (1) port/process check: `curl -sf http://127.0.0.1:8403/v1/models` fails (connection refused) AND `ps aux \| grep "franklin proxy"` shows no process owned by the franklin-loop daemon, checked immediately after a fresh daemon (re)start; (2) live process ENV check (mirrors PROP-014's method exactly): `launchctl print gui/$(id -u)/ai.anicca.franklin-loop` and/or `ps eww <pid>` for the live supervised loop process, asserting its actual `OPENAI_BASE_URL` value is `http://127.0.0.1:8402/v1` (not `:8403`) — deliberately NOT the verifier's own shell `env`, and NOT inferred from check (1) alone, since check (1) passing is consistent with BOTH the fixed state and the FIND-006-broken state (dead 8403, `PORT` still derived from `FRANKLIN_PROXY_PORT`) |
| PROP-016 | The deployed `runtime/anicca-daemon.sh`'s `INSTANCE=franklin` branch (step 2, post-fix `ensure_brain` replacement, REQ-004(b)/REQ-005) contains, in its real source text, NO reference to `$HOME/.openclaw/.env`, no `BLOCKRUN_WALLET_KEY` read/export, no `clawrouter` binary invocation, and defines/calls no function that spawns any process for `INSTANCE=franklin` — it is a no-op or, at most, a readiness probe against the already-running, separately-launchd `ai.anicca.clawrouter` job on `8402`; cross-checked live that the running franklin-loop daemon PROCESS's actual env contains no `BLOCKRUN_WALLET_KEY` variable at all (FIND-009 / REQ-004(b) / REQ-005 — this closes the exact gap the iteration-3 verdict identified: no prior PROP-0xx entry reached `anicca-daemon.sh`'s `ensure_brain` wiring, only `resolve-identity.mjs`'s own functions in isolation via PROP-007) | 0 | true | TWO checks, both required: (1) static source check: read the actual deployed `runtime/anicca-daemon.sh` file content (not a fixture copy) and grep/parse the `INSTANCE = "franklin"` branch's text for the absence of the `.openclaw/.env`, `BLOCKRUN_WALLET_KEY`, and `clawrouter` tokens, and confirm it is textually distinct from (does not merge with) the non-franklin branch's `ensure_brain` closure; (2) live process ENV check (mirrors PROP-014/015's method): `launchctl print gui/$(id -u)/ai.anicca.franklin-loop` and/or `ps eww <pid>` for the live supervised franklin-loop process, asserting no `BLOCKRUN_WALLET_KEY` variable is present in its actual environment |

## Verification Strategy

- **Tier 0** (no formal proof needed — live/operational facts about external services,
  the deployed daemon's real configuration, and log content): PROP-003, PROP-009,
  PROP-010, PROP-011, PROP-013, PROP-014, PROP-015, PROP-016. These are facts about a
  live, third-party-rate-limited endpoint, this feature's own operational log output,
  and the DEPLOYED daemon's actual source/plist/process/env (not a unit-test fixture
  standing in for it) — no amount of unit testing substitutes for actually observing
  the real wallet balance, the real HTTP response, the real ledger/trace lines
  post-fix, the real deployed plist/script content, and the real supervised process's
  env/open ports. Verified by direct commands (`curl`, `node -e`, `tail`/`grep`,
  `launchctl print`, `ps eww`, `plutil`) against the real, deployed artifacts during
  Phase 2b/3, not by mocks or by inspecting the verifier's own shell environment.
- **Tier 1** (property tests / boundary tables over pure or thinly-mocked functions):
  PROP-001, PROP-002, PROP-004, PROP-005, PROP-006, PROP-008, PROP-012. These follow
  the existing repo convention (`tier.test.mjs`, `catalog-gate.test.mjs`,
  `resolve-identity.test.mjs`, `solana-verify.test.js`) of exhaustive input-table
  `node:test` cases rather than a heavyweight fuzzing harness — consistent with
  mode=lean and with how every other pure/thin module in `runtime/loop/__tests__/`
  and `skills/_shared/lib/__tests__/` is already verified in this codebase.
- **Tier 2** (lightweight formal/invariant methods): PROP-007 — the per-instance
  identity gate is treated as a money-safety invariant (per project memory
  `feedback_earn_identity_resolve_per_instance_gate_on_anicca_home`) and gets an
  exhaustive state-table test (every combination of `{ANICCA_HOME unset, default,
  Franklin's own, a third instance's, malformed}` × `{env override present/absent}`)
  rather than a single happy-path test, mirroring how `resolve-identity.test.mjs`
  already treats the EVM side of the same gate.
- **Tier 3** (strong formal proof — Kani/similar): none required. This feature is
  JS/bash glue-configuration work over an already-pure `selectTier`/`filterCatalog`
  core; no new safety-critical arithmetic or protocol logic is introduced that would
  warrant a heavyweight prover, consistent with the rest of this Node.js codebase
  (which uses property/boundary `node:test` suites, not Kani/similar, throughout
  `runtime/loop/__tests__/`).

## Non-Goals Carried Into Verification

- No proof obligation is written for `catalog-gate.mjs`'s `DEFAULT_BOOTSTRAP_RESERVE_USDC`
  threshold behavior at Franklin's real balance (~$11.63 < $20) — that gate's
  correctness is already specified/verified under the `anicca-agent-economy` feature
  and is unmodified here (see behavioral-spec.md non-goals).
- No proof obligation is written for `skills/earn/sol-trade/run.sh` /
  `franklin-trading` CLI internals, its `$0.25` max-spend cap, or its own model
  choice (`openai/gpt-5-mini`) — untouched, already independently verified live
  (`sol-trade.trace.jsonl` history predates this feature).
- No proof obligation is written for `skills/earn/funding/lib/solana_rpc.py` — this
  feature does not port, call, or otherwise touch it (corrects iteration-1's mistaken
  citation of it as REQ-002's implementation source; the actual reused source is
  `skills/_shared/lib/solana-verify.mjs::usdcBalance`, already covered by PROP-002/003).
