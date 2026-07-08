# Behavioral Spec — franklin-loop-revival

## Context (grounded, verified 2026-07-08)

Franklin (`ai.anicca.franklin-loop` launchd job, `ANICCA_INSTANCE=franklin`,
`ANICCA_HOME=/Users/operator/.blockrun`, Solana wallet
`8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9`, real balance ≈ $11.63 USDC after the
2026-07 top-up) is running but structurally cannot use its own funds. Two independent,
verified root causes (confirmed by reading the exact source lines and live process
env/logs, not assumed):

**Root cause A — wallet/balance never resolves, tier stuck at `broke`:**
- `runtime/anicca-daemon.sh:119-124` only runs the `ANICCA_WALLET_ADDRESS` derivation
  `if [ "$INSTANCE" != "franklin" ]` — for `INSTANCE=franklin` the block is skipped
  entirely and the comment ("leaving ANICCA_WALLET_ADDRESS unset for Franklin is
  correct — the loop just keeps tier=broke, non-fatal") is a stale 2026-06 assumption
  from when Franklin held $0. `runtime/wallet-address.mjs` itself is also EVM-only
  (`viem.privateKeyToAccount`) and has no Solana branch.
- Even if an address were exported, `runtime/loop/balance.mjs::fetchUsdcBalance`
  hard-validates `/^0x[0-9a-fA-F]{40}$/` and queries Base mainnet's USDC ERC-20
  contract only — a base58 Solana address would still fail with
  `invalid wallet address`.
- Live evidence (`~/.blockrun/logs/daemon.err`, current): every wake logs
  `[loop] WARNING: ANICCA_WALLET_ADDRESS not set, using "unknown"` then
  `[loop] Balance fetch failed: invalid wallet address: unknown — keeping tier=broke`.
  `runtime/loop/index.mjs:230-244` initializes `liquidUsdc = 0` and only overwrites it
  inside the failing try-block, so `currentTier` never leaves `{tier:'broke', model:
  ANICCA_FREE_MODEL}` and `ctx.balanceUsdc` shown to the model is always `0`, never
  the real ~$11.63.

**Root cause B — THINK is pinned to an exhausted model on the wrong endpoint:**
- `ai.anicca.franklin-loop.plist` sets `ANICCA_MODEL=ANICCA_FREE_MODEL=ANICCA_LEAN_MODEL=
  ANICCA_FUNDED_MODEL=nvidia/llama-4-maverick` and `FRANKLIN_PROXY_PORT=8403`.
  `runtime/anicca-daemon.sh:53-75` starts `franklin proxy --port 8403 --model
  nvidia/llama-4-maverick --no-fallback` for `INSTANCE=franklin`, then (line 117)
  unconditionally exports `OPENAI_BASE_URL=http://127.0.0.1:$PORT/v1` (`$PORT=8403`
  for franklin). The actual pinning mechanism (re-verified this iteration against the
  live `runtime/loop/config.mjs`, correcting a prior draft's wrong claim — see FIND-010):
  `ANICCA_MODEL` is in NEITHER `config.mjs`'s `DEFAULTS` (lines 13-62) NOR its explicit
  pass-through list (lines 114-142), so `config.ANICCA_MODEL` is ALWAYS `undefined`
  regardless of what the plist exports (`brain.mjs:58` is its only reference in the
  entire `runtime/` tree, confirmed by grep). `runtime/loop/brain.mjs::thinkProxy`
  builds its request body as `config.ANICCA_MODEL || ctx.model || 'auto'` — since
  `config.ANICCA_MODEL` is always `undefined`, this expression ALWAYS falls through to
  `ctx.model`, and it is `ctx.model` that actually carries the exhausted-model pin: it
  is produced by `runtime/loop/tier.mjs::selectTier(balance, config)` reading
  `config.ANICCA_FREE_MODEL`/`ANICCA_LEAN_MODEL`/`ANICCA_FUNDED_MODEL` — which ARE in
  `config.mjs`'s `DEFAULTS` and DO correctly reflect the plist's `nvidia/llama-4-maverick`
  overrides. The net effect on THINK is identical either way (the exhausted model
  reaches every wake), and the prescribed fix is unchanged (REQ-004 still requires
  moving all four plist model keys off `nvidia/llama-4-maverick`, since
  `ANICCA_FREE_MODEL`/`ANICCA_LEAN_MODEL`/`ANICCA_FUNDED_MODEL` are the three that
  actually matter) — but the mechanism is `ctx.model` via `tier.mjs`, NOT
  `config.ANICCA_MODEL`. Fixing root cause A alone still cannot fix THINK.
- Live evidence (`~/.blockrun/logs/daemon.err`, `~/.blockrun/state/ledger.jsonl`,
  current): roughly half of all wakes fail with
  `[loop] THINK failed: proxy_down: HTTP 429: {"type":"error","error":{"type":
  "rate_limit_error","message":"[nvidia/llama-4-maverick] Free model capacity
  exhausted — retry shortly, or use a paid model..."}}`, recorded as
  `kind:"wake_error", error:"proxy_down"` in the ledger — a wasted wake, no skill runs.
- The already-running, shared ClawRouter instance (`ai.anicca.clawrouter` launchd job,
  confirmed live via `curl http://127.0.0.1:8402/v1/models`) answers on port 8402 and
  is a distinct process from Franklin's own `franklin proxy` on 8403. Free-tier models
  on ClawRouter settle at $0 regardless of whose wallet started the router (per the
  existing non-franklin branch of `anicca-daemon.sh`'s own comments), so Franklin can
  reach it as a client for $0 THINK calls without paying, spending, or exposing any
  wallet key.

**What this spec explicitly does NOT change (verified, in scope boundary):**
- `skills/earn/sol-trade/run.sh` and the `franklin-trading` CLI it shells out to:
  this already resolves Franklin's real Solana balance and pays its own model calls
  via its own x402 flow (`openai/gpt-5-mini`, `$0.25` max-spend/pass), fully
  independent of the loop's `think()`/`OPENAI_BASE_URL`. Confirmed live in
  `skills/earn/state/sol-trade.trace.jsonl` and `~/.blockrun/state/ledger.jsonl`
  (`slot:"earn/sol-trade"` entries already show real balances, e.g. "$11.63 USDC").
  This spec's fixes let the *outer loop* wake reliably and route `earn/sol-trade`
  (and any other slot) correctly with a real balance in context — it does not touch
  sol-trade's own internals, spend cap, or model.
- `skills/economy/*`, any other instance's wallet/cron/keys, and
  `runtime/loop/catalog-gate.mjs`'s `DEFAULT_BOOTSTRAP_RESERVE_USDC` ($20 default) are
  untouched. Note (documented, not fixed here): even after this spec's fixes,
  Franklin's ~$11.63 stays below that separate $20 bootstrap-reserve threshold, so
  `filterCatalog` will still *offer* `earn/sol-trade` as absent from the tool-schema
  hint it sends the model (risk-tagged `"capital"`, no `alwaysAvailable`, no
  open-position carve-out registered for it) — this is a pre-existing, separately
  specified gate (`anicca-agent-economy` feature) and changing its threshold/logic is
  out of scope. It does not block this feature's Done condition because
  `parseToolCall` performs no enum enforcement (confirmed by reading
  `runtime/loop/parse-tool-call.mjs`) — a chosen slot is executed by name whether or
  not it was in the offered tool list, exactly as already observed live.

## Purity Boundary Analysis

- **Pure core** (deterministic, no I/O, formally testable): `runtime/loop/tier.mjs`
  (`selectTier` — untouched by this feature); a new address-shape predicate (e.g.
  `isEvmAddress`/`isSolanaAddress`) that this feature introduces to let
  `fetchUsdcBalance` dispatch by chain — pure string-shape classification, no I/O.
- **Effectful shell** (I/O, network, process spawn — this feature's real surface):
  `runtime/wallet-address.mjs` (extended with a Solana branch, or a new sibling
  module — derives a public key in-process, no network call), `runtime/loop/balance.mjs
  ::fetchUsdcBalance` (extended with a Solana branch that DELEGATES to the existing,
  already-tested `skills/_shared/lib/solana-verify.mjs::usdcBalance(wallet, opts)` —
  no new Solana RPC request/parsing code is written by this feature; see REQ-002),
  `runtime/anicca-daemon.sh` (instance-branch wallet export, THINK endpoint/model
  export, the `PORT`-assignment branch (currently lines 26-30) that determines what
  port `OPENAI_BASE_URL` resolves to for franklin — this branch itself MUST change,
  not just the spawn below, see REQ-004 — AND replacing `ensure_brain`'s
  `INSTANCE=franklin` branch, currently spawning `franklin proxy --port 8403 ...`,
  with a no-op/readiness-probe-only branch that never spawns a process and never
  reads `$HOME/.openclaw/.env` or any other instance's key file — see REQ-004(b) and
  REQ-005),
  `ai.anicca.franklin-loop.plist` (model/env
  values; MUST NOT gain an `ANICCA_BALANCE_OVERRIDE` key — see REQ-003),
  `runtime/loop/brain.mjs::thinkProxy` (unchanged code, but its externally-supplied
  config now points at a different endpoint/model — config-driven, no logic change
  required).

## Requirements

### REQ-001: Franklin's own Solana wallet address resolves at daemon start
**EARS**: WHEN the loop daemon starts with `ANICCA_INSTANCE=franklin` THE SYSTEM SHALL
resolve and export `ANICCA_WALLET_ADDRESS` as Franklin's own base58 Solana public
address, derived in-process from the exact secret `skills/earn/lib/resolve-identity.mjs
::resolveSolanaSecret` resolves for Franklin's own `ANICCA_HOME`
(`/Users/operator/.blockrun`), instead of leaving the variable unset.
**Edge Cases**:
- `~/.blockrun/.solana-session` missing/unreadable/empty: export nothing (leave
  `ANICCA_WALLET_ADDRESS` unset), log a WARNING, do not crash the daemon, and do NOT
  fall back to scanning any other dot-directory or instance's wallet/session file.
- **`~/.blockrun/.solana-session` present but cryptographically malformed** (its
  content is non-empty, so `resolve-identity.mjs::readRawSecretFile`
  (`resolve-identity.mjs:39-46`, which only trims whitespace and checks non-empty
  length — it does NOT validate base58 shape or byte length) returns it as a
  "resolved" secret, but the content is not a valid Solana secret key: not valid
  base58, or valid base58 that decodes to the wrong byte length, or any input that
  makes `Keypair` derivation throw): THE SYSTEM SHALL catch that derivation error,
  treat it identically to the missing/empty case — export nothing (leave
  `ANICCA_WALLET_ADDRESS` unset), log a WARNING, and do NOT crash the daemon. This is
  a defined "warn and continue" behavior, not a crash, and is symmetric with the
  missing-file edge case above (`resolve-identity.mjs` itself already never throws;
  this feature's NEW address-derivation helper — the thing that actually calls
  `Keypair` on the resolved secret — is what must add this catch).
- Non-franklin instance (`ANICCA_INSTANCE` unset or `clawrouter`): existing EVM
  (`viem`) address resolution behavior is unchanged byte-for-byte (regression).
- A process spawned with `ANICCA_INSTANCE=franklin` but a *different* `ANICCA_HOME`
  than `/Users/operator/.blockrun`: MUST resolve nothing for Franklin's real wallet
  (fail-closed), mirroring `resolveSolanaSecret`'s existing `legacyHome` gate.
**Acceptance Criteria**:
- Running the new/extended address-resolution helper with
  `ANICCA_HOME=/Users/operator/.blockrun ANICCA_INSTANCE=franklin` prints exactly
  `8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9` to stdout and nothing else on stdout.
- `runtime/anicca-daemon.sh`'s `if [ "$INSTANCE" != "franklin" ]` wallet-export gate
  (current lines 119-124) is replaced with a branch that resolves an EVM address for
  non-franklin and a Solana address for franklin — no instance is left permanently
  unresolved by construction.
- Running the new/extended address-resolution helper against a fixture file
  containing malformed content (invalid base58, or valid base58 of the wrong byte
  length) prints nothing to stdout, exits without crashing (exit code reflects
  "warned and skipped", not a process crash/uncaught exception), and any WARNING
  written to stderr does not contain the fixture's raw secret string.

### REQ-002: Chain-aware USDC balance fetch (reuses `solana-verify.mjs`, no porting)
**EARS**: WHEN the loop's balance-fetch step is given a resolved wallet address THE
SYSTEM SHALL dispatch to the wallet's actual chain — Base ERC-20 `balanceOf` for a
`0x`-prefixed 40-hex address (existing `balance.mjs` code path, unchanged), or, for a
base58 Solana address, THE SYSTEM SHALL delegate to the existing, already
unit-tested `skills/_shared/lib/solana-verify.mjs::usdcBalance(wallet, opts)` —
and SHALL NOT reimplement or port a second Solana-balance code path (in particular,
it MUST NOT port `skills/earn/funding/lib/solana_rpc.py::spl_token_balance_units`;
that Python helper returns raw token units with no mint constant and no decimals
handling and is out of scope for this feature).
**Edge Cases**:
- Address is `'unknown'`, empty, or matches neither chain's shape: throw (preserves
  the existing invariant — caller keeps the prior tier, no crash of the loop). For
  the Solana branch this is inherited for free from `usdcBalance`'s own guard
  (`solana-verify.mjs:85-87`: throws `not a base58 wallet: ...` for anything failing
  its base58 shape check `B58_RE`), not re-implemented.
- Solana RPC failure/timeout: throw (identical fail path to the existing Base RPC
  failure handling — caller keeps prior tier). Inherited from `usdcBalance`'s `rpc()`
  helper (`solana-verify.mjs:19-31`), which throws on a non-OK HTTP status or an
  RPC-level `error` field — no new retry/fallback logic is added for the Solana
  branch beyond what `usdcBalance` already does.
- Wallet holds zero SPL token accounts for the USDC mint: `usdcBalance` already
  returns `0` (not an error) in this case (`solana-verify.mjs:83,95`: "Returns 0 (no
  throw) when the ATA does not exist") — this feature's dispatch code MUST pass that
  return value through unchanged, mirroring the existing "no ERC-20 balance found →
  0" case on the Base side.
- The Solana USDC mint used MUST be the exact constant already defined and verified
  at `skills/_shared/lib/solana-verify.mjs:14`:
  `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` (native USDC SPL mint on Solana
  mainnet, verified against `getTokenAccountsByOwner` 2026-06-29 per that file's own
  header comment) — this feature MUST NOT hardcode a second, independently-typed
  copy of this constant. `USDC_MINT` at `solana-verify.mjs:14` is a module-private
  `const` and is NOT exported (the file's only exports are `sigStatus`,
  `usdcDeltaForSig`, and `usdcBalance` — verified against the real file); there is
  therefore exactly ONE compliant implementation path, not a choice of two: this
  feature's dispatch code MUST call `usdcBalance(wallet, opts)` with NO `opts.mint`
  override at all, letting `solana-verify.mjs` supply its own default
  (`opts.mint || USDC_MINT`) internally. Importing a named `USDC_MINT` constant from
  that module is not a real implementation option and MUST NOT be attempted.
**Acceptance Criteria**:
- Calling the balance fetch with `8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9`
  returns the real numeric USDC balance (~$11.63 at spec-writing time) — obtained by
  calling `solana-verify.mjs`'s `usdcBalance(wallet, opts)` — instead of throwing
  `invalid wallet address`.
- Calling the balance fetch with an existing `0x...` address and existing test
  fixtures/overrides (`ANICCA_BALANCE_OVERRIDE`) behaves exactly as before
  (regression baseline for the EVM path stays green).
- No new Solana JSON-RPC request-building/parsing code is added by this feature's
  balance-fetch dispatch layer; the only new code is the chain-shape dispatch (REQ-002)
  plus a thin call into `usdcBalance` — verified by review showing the dispatch
  module imports `usdcBalance` from `skills/_shared/lib/solana-verify.mjs` rather than
  defining its own `getTokenAccountsByOwner` call.

### REQ-003: Tier reflects Franklin's real balance (no permanent `broke`, no override backdoor)
**EARS**: WHEN Franklin's wallet address (REQ-001) and real balance (REQ-002) both
resolve successfully on a wake THE SYSTEM SHALL compute `currentTier` via the
existing, unmodified `runtime/loop/tier.mjs::selectTier` pure function using that
real balance — eliminating the current permanent `tier: 'broke'` caused by the
`'unknown'` address short-circuit — and SHALL NOT set `currentTier` to `'lean'` or
`'funded'` by any means other than a real, successfully-fetched balance (REQ-001 +
REQ-002 actually working).
**Edge Cases**:
- `selectTier`'s own pure boundary rules (0 → broke, `0 < x <= 1.00` → lean, `>1.00`
  → funded, non-finite/negative → broke) are unchanged — this feature supplies
  correct *inputs*, it does not alter tier arithmetic.
- A single wake's RPC failure after a previously-successful fetch: tier holds its
  last-known value (existing `index.mjs` catch-block behavior, unchanged).
- `ctx.balanceUsdc` shown to the model in the assembled prompt reflects the real
  balance instead of always `0`.
- **`ANICCA_BALANCE_OVERRIDE` MUST NOT be set in the deployed
  `ai.anicca.franklin-loop.plist`.** `balance.mjs:32-40` reads this env var (test-only
  escape hatch: an arbitrary numeric string bypasses ALL address validation and RPC
  calls and is returned directly as the balance) — it exists solely for this
  feature's own regression tests (REQ-002's EVM-path acceptance criterion) and MUST
  NEVER appear as an `<EnvironmentVariables>` key in the production plist for any
  instance. A deployment that sets it would let `currentTier` read `'lean'`/`'funded'`
  from a fabricated number without REQ-001/REQ-002 ever actually resolving Franklin's
  real wallet/balance — the exact "tier gamed without real balance" loophole this
  requirement forbids.
**Acceptance Criteria**:
- Across a sample of real wakes after the fix, `currentTier.tier` is observed as
  `'lean'` or `'funded'` (never permanently `'broke'`) whenever the real balance is
  greater than $0 — verified from `~/.blockrun/state/ledger.jsonl` wake lines no
  longer showing the `unknown`/`invalid wallet address` failure pair.
- The DEPLOYED `ai.anicca.franklin-loop.plist` (the file actually loaded by
  `launchctl`, read directly from
  `~/Library/LaunchAgents/ai.anicca.franklin-loop.plist`) contains no
  `ANICCA_BALANCE_OVERRIDE` key under its `<EnvironmentVariables>` dict.
- The REAL environment of the running Franklin daemon PROCESS (inspected via
  `launchctl print gui/$(id -u)/ai.anicca.franklin-loop` and/or `ps eww <pid>` /
  `/proc`-equivalent on the live PID — not the verifier's own shell `env`, which
  proves nothing about what the supervised process actually inherited) also shows no
  `ANICCA_BALANCE_OVERRIDE` — this closes the gap where a plist could omit the key
  while a wrapper script or parent shell still exports it into the daemon's actual
  process environment.

### REQ-004: THINK routes to ClawRouter AND the dedicated 8403 franklin proxy is disabled
**EARS**: WHEN `ANICCA_INSTANCE=franklin` THE SYSTEM SHALL, by changing ALL THREE of
the following (not a subset), make the THINK step's HTTP calls
(`brain.mjs::thinkProxy`'s `OPENAI_BASE_URL`) — and any skill subprocess that
inherits the same env — reach the already-running shared ClawRouter endpoint
(`http://127.0.0.1:8402/v1`, confirmed live and healthy on its free tier) using a
model id confirmed live and non-rate-limited on that endpoint:
(a) change `runtime/anicca-daemon.sh`'s `PORT`-assignment branch (currently lines
26-30: `if [ "$INSTANCE" = "franklin" ]; then PORT="${FRANKLIN_PROXY_PORT:-8403}"
else PORT="${COMPUTE_PROXY_PORT:-8402}"; fi`) so that for `INSTANCE=franklin`,
`PORT` resolves to ClawRouter's `8402` (e.g. `${COMPUTE_PROXY_PORT:-8402}`, matching
the non-franklin branch) instead of `${FRANKLIN_PROXY_PORT:-8403}` — this is the
EXACT SAME `$PORT` variable that line 117 already uses unconditionally
(`export OPENAI_BASE_URL="http://127.0.0.1:$PORT/v1"`), so changing only this
assignment (no change needed at line 117 itself) is both necessary and sufficient
to make `OPENAI_BASE_URL` resolve to 8402 for franklin;
(b) change `runtime/anicca-daemon.sh`'s `ensure_brain` wiring for `INSTANCE=franklin`
(currently lines 53-75) so it NEVER starts `franklin proxy --port 8403 --model
nvidia/llama-4-maverick --no-fallback`, and REPLACE it with a fully specified
no-op/readiness-probe-only branch: franklin's step-2 brain-bringup becomes, AT MOST,
the SAME `curl -sf http://127.0.0.1:$PORT/v1/models` readiness probe the franklin
branch already has (now pointed at 8402 per (a)) — it MUST NOT define or call any
`ensure_brain` function that spawns a `clawrouter` process, a `franklin proxy`
process, or any other process for `INSTANCE=franklin`; it MUST NOT read
`$HOME/.openclaw/.env`, `BLOCKRUN_WALLET_KEY`, or any other instance's wallet/key
file under any circumstance to do so. Bringing ClawRouter up is EXCLUSIVELY the
ALREADY-RUNNING, SEPARATELY-launchd `ai.anicca.clawrouter` job's own responsibility
(`~/Library/LaunchAgents/ai.anicca.clawrouter.plist`: `KeepAlive=true` +
`RunAtLoad=true`, confirmed live this iteration — PID present, listening on
`127.0.0.1:8402`, `<EnvironmentVariables>` deliberately has NO `BLOCKRUN_WALLET_KEY`
key at all, i.e. it is free-tier-only by design, verified against the live plist
file) — never Franklin's. Franklin's daemon reaches it as a same-machine loopback
HTTP client only (REQ-004(a)'s `OPENAI_BASE_URL`/`PORT` fix), which needs no
credential for the free-tier path, so franklin's `ensure_brain` replacement has no
legitimate reason to read any key file at all, cross-instance or otherwise; AND
(c) update the deployed `ai.anicca.franklin-loop.plist` so `FRANKLIN_PROXY_PORT` is
no longer the value that `PORT` derives from for franklin (either by removing the
`FRANKLIN_PROXY_PORT` key from the plist entirely, or by leaving the key present but
confirming (a) means the daemon script no longer reads it into `PORT` for franklin —
either is acceptable, but the deployed plist's `FRANKLIN_PROXY_PORT=8403` value MUST
NOT be the thing `OPENAI_BASE_URL` resolves through after this fix).
All THREE are required, not just any one or two: (a) alone without (b) would leave a
dead/rate-limited `franklin proxy` orphan on 8403 still holding the external
`@blockrun/franklin` CLI's own wallet-resolution code
(`getOrCreateSolanaWallet()`, invoked by that binary, NOT this repo's
`resolve-identity.mjs`) alive and reachable — the exact external code path that once
caused `franklin proxy`'s startup banner to briefly report the wrong wallet
(`Efpap5SHn6e7wSqFu6ndURHPQrVaP91WnBS27yEuVy11` instead of Franklin's real
`8FpqdcCH...`) before self-correcting (see REQ-005's edge case); (b) alone without
(a) is the FIND-006 regression — removing only the 8403 spawn while `PORT` still
resolves to `${FRANKLIN_PROXY_PORT:-8403}` leaves `OPENAI_BASE_URL` pointed at a
dead `:8403` where NOTHING listens, so THINK fails on EVERY wake
(connection-refused) instead of the current ~50% (rate-limited 429) — strictly worse
than today, and a literal-but-wrong reading of a "retire 8403" instruction; (a)+(b)
without (c) risks a future redeploy of the plist re-introducing (b)'s spawn via a
stale `FRANKLIN_PROXY_PORT` default if `ensure_brain`'s franklin branch is ever
restored, so the plist itself must not keep asserting 8403 as Franklin's brain port.
**Edge Cases**:
- ClawRouter (8402) itself becomes unreachable: `think()` must still surface a
  `wake_error` via the existing retry/catch path in `index.mjs` (unchanged code),
  never crash the loop. There is no fallback to the disabled 8403 franklin proxy —
  that path is fully retired, not kept as a hidden fallback.
- Cold-boot ordering (ClawRouter not yet listening on 8402 when Franklin's daemon
  starts, e.g. immediately after a machine reboot): `ai.anicca.clawrouter` and
  `ai.anicca.franklin-loop` are BOTH independently `RunAtLoad`+`KeepAlive` launchd
  jobs (confirmed live in both deployed plists), so neither depends on the other's
  start order — both start in parallel. If Franklin's THINK call races ahead of
  ClawRouter's readiness, it fails exactly like the "ClawRouter (8402) itself becomes
  unreachable" edge case above (retry/catch → `wake_error`, no crash); Franklin's
  daemon MUST NOT compensate by spawning its own ClawRouter or `franklin proxy`
  instance, or by reading any key file to do so — the next wake (`SLEEP_BASE_S`
  later) simply retries against 8402 once launchd has finished bringing ClawRouter
  up on its own.
- The chosen free-tier model id later also becomes rate-limited or renamed: the fix
  MUST be expressed as configurable env values (`ANICCA_MODEL`/`ANICCA_FREE_MODEL`/
  `ANICCA_LEAN_MODEL`/`ANICCA_FUNDED_MODEL`/`OPENAI_BASE_URL`), not a second
  hardcoded proxy binary pin, so an operator can update the model id without a code
  change.
- The selected model must be verified live (an actual `/v1/models` + a real
  zero-payment completion call against ClawRouter on 8402) before being written into
  the plist — not assumed from memory of an older, possibly-renamed model catalog.
- Retiring the `franklin proxy`/8403 branch of `ensure_brain` MUST NOT remove or
  break the franklin-specific telemetry poster (step 3 of `anicca-daemon.sh`,
  `telemetry-post-franklin.mjs`) — that poster is independent of THINK routing and is
  out of scope for this requirement (unchanged).
- `FRANKLIN_FREE_MODEL` (the model-id env value, distinct from the port) and the
  `franklin` CLI dependency line (`npm install -g @blockrun/franklin` inside
  `ensure_brain`, which after (b) is simply never reached for `INSTANCE=franklin`)
  become dead configuration once the 8403 branch is retired; this requirement does
  not mandate deleting `FRANKLIN_FREE_MODEL` or that npm-install line from the
  plist/script in this sprint — leaving unreachable/inert code and an unused model-id
  value is harmless. This is narrower than iteration-2's edge case: it does NOT cover
  `FRANKLIN_PROXY_PORT`, whose consumption for `PORT`/`OPENAI_BASE_URL` is load-bearing
  and MUST change per (a)/(c) above — leaving `FRANKLIN_PROXY_PORT`'s effect on
  `PORT` untouched is exactly the FIND-006 regression and is explicitly NOT
  permitted.
**Acceptance Criteria**:
- After the fix, at least 3 consecutive real Franklin wakes show a THINK call
  succeeding (no `kind:"wake_error", error:"proxy_down"` line in
  `~/.blockrun/state/ledger.jsonl`) using the ClawRouter endpoint/model.
- `ai.anicca.franklin-loop.plist`'s `ANICCA_MODEL`/`ANICCA_FREE_MODEL`/
  `ANICCA_LEAN_MODEL`/`ANICCA_FUNDED_MODEL` values no longer point Franklin's THINK
  path at a rate-limited model with no live alternative, AND
  `runtime/anicca-daemon.sh`'s `PORT`-assignment branch (lines 26-30) no longer
  derives franklin's `PORT` from `FRANKLIN_PROXY_PORT`/`8403` — franklin's `PORT`
  resolves to `8402` by the same code path the non-franklin branch already uses.
- After the fix, no `franklin proxy` process is running/listening on port 8403 for
  Franklin's daemon (verified via `curl -sf http://127.0.0.1:8403/v1/models` failing
  and/or `ps aux | grep "franklin proxy"` showing no live process spawned by the
  franklin-loop daemon), AND Franklin's `OPENAI_BASE_URL` resolves to
  `http://127.0.0.1:8402/v1` — this second half MUST be verified against the REAL
  running franklin-loop daemon process's actual environment (e.g. `launchctl print
  gui/$(id -u)/ai.anicca.franklin-loop` and/or `ps eww <pid>`), not merely inferred
  from the absence of an 8403 listener (an absent 8403 listener is consistent with
  BOTH the fixed state and the FIND-006-broken state, so it alone proves nothing
  about where `OPENAI_BASE_URL` actually points).
- The deployed `runtime/anicca-daemon.sh`'s `INSTANCE=franklin` branch (step 2, post-fix)
  contains NO reference to `$HOME/.openclaw/.env` or `BLOCKRUN_WALLET_KEY` anywhere in
  its source, and defines/calls no function that spawns `clawrouter` or
  `franklin proxy` — verified by direct read of the real, deployed file (see REQ-005,
  PROP-016). This is the check that closes FIND-009: REQ-004(b)'s replacement
  behavior is a fully specified no-op/readiness-probe, not left to implementer choice.

### REQ-005: Per-instance identity gate preserved (no cross-instance leakage)
**EARS**: WHEN any wallet-, balance-, or brain/proxy-spawn-resolution code touched by
this feature runs for any instance — including `runtime/anicca-daemon.sh`'s
`ensure_brain` wiring itself, not only library-level identity-resolution functions —
THE SYSTEM SHALL continue to gate resolution strictly on that
instance's own `ANICCA_HOME` (mirroring `resolve-identity.mjs`'s existing priority
order: named env override → `$ANICCA_HOME/.automaton/{wallet.json,solana.json}` →
legacy path gated to the *rightful* default home only → null), and SHALL NOT scan,
read, or derive an address/balance/wallet-key from any other dot-directory's
wallet/session/env file — including `$HOME/.openclaw/.env` and `BLOCKRUN_WALLET_KEY`
— under any circumstance. This explicitly covers Franklin's (`INSTANCE=franklin`)
`ensure_brain` replacement behavior (REQ-004(b)): it MUST NOT fall into, merge with,
or otherwise execute the non-franklin branch's `$HOME/.openclaw/.env` grep /
`resolve-identity.mjs evm` fallback (`anicca-daemon.sh`'s non-franklin `ensure_brain`,
lines 82-95), because that path resolves a DIFFERENT instance's (the shared
ClawRouter/OpenClaw automaton's) key, not Franklin's own — a spec-compliant-but-wrong
implementation that collapses the franklin/non-franklin `if`/`else` into one
`ensure_brain` would otherwise have Franklin's own daemon read another instance's
wallet-key file, which is exactly the leakage this requirement forbids (FIND-009).
**Edge Cases**:
- A spawn with `ANICCA_HOME` unset or defaulted to `~/.anicca`: must never resolve
  Franklin's `~/.blockrun/.solana-session` secret.
- A foreign `ANICCA_HOME`: must resolve `null`/empty for Franklin's identity, never
  silently substitute a different instance's wallet (this is the exact failure class
  already observed once live — `franklin proxy`'s banner briefly reported wallet
  `Efpap5SHn6e7wSqFu6ndURHPQrVaP91WnBS27yEuVy11` instead of Franklin's real
  `8FpqdcCH...` wallet before self-correcting; this MUST NOT recur as a consequence
  of this feature's changes).
- Franklin's `ensure_brain` replacement (REQ-004(b)) implemented by collapsing/merging
  the franklin and non-franklin branches of `anicca-daemon.sh`'s
  `if [ "$INSTANCE" = "franklin" ]; then ... else ... fi` block into a single
  `ensure_brain`: MUST NOT occur. The two branches stay structurally distinct — the
  franklin branch becomes a no-op/readiness-probe (REQ-004(b)), the non-franklin
  branch's `$HOME/.openclaw/.env` grep / `BLOCKRUN_WALLET_KEY` / `clawrouter` spawn
  logic is untouched and never executes when `INSTANCE=franklin` — even though
  REQ-004(a) edits the shared `PORT`-assignment lines that both branches read from
  (a separate, earlier code block, not the `ensure_brain` closures themselves).
**Acceptance Criteria**:
- The existing `runtime/loop/__tests__/resolve-identity.test.mjs` suite remains green
  (regression) and is extended (not replaced) with cases for any new
  address-derivation helper this feature adds.
- No new code path added by this feature reads `~/.blockrun/.solana-session` unless
  the effective `ANICCA_HOME` resolves to exactly `$HOME/.blockrun` (the same gate
  `resolveSolanaSecret` already enforces).
- The deployed `runtime/anicca-daemon.sh`'s `INSTANCE=franklin` branch (step 2,
  post-fix) contains NO reference to `$HOME/.openclaw/.env` or `BLOCKRUN_WALLET_KEY`
  anywhere in its source, verified by direct read of the real file (PROP-016) — not a
  fixture copy, not an assumption from reading only the non-franklin branch.

### REQ-006: Private key material never crosses a process/log boundary
**EARS**: WHEN deriving Franklin's Solana public address (REQ-001) THE SYSTEM SHALL
derive it in-process from the resolved secret and SHALL NEVER print, log, export as
an environment variable, or persist the secret itself — only the derived base58
public address may cross a process or log boundary.
**Edge Cases**:
- Any error path (missing file, malformed secret, RPC failure) must not include the
  raw secret in its error message or stderr output.
- Any new environment variable this feature introduces to carry the derived address
  must be named so it is NOT matched by `env-filter.mjs`'s `PRIVATE_KEY_REGEX`
  removal list only if it is genuinely non-secret (the address itself is public and
  fine to pass through unscrubbed; the secret must never be assigned to an env var
  read by a child process).
**Acceptance Criteria**:
- Manual/automated review of the new address-derivation helper shows no
  `console.log`/`process.stdout.write`/`process.stderr.write` of secret material.
- Existing `runtime/loop/__tests__/env-filter.test.mjs` (`scrubPrivateKeys`,
  `redactPrivateKeyPatterns`) remains green (regression) — no relaxation of the
  private-key redaction patterns is made by this feature.

## Non-Functional Requirements

- **Regression safety**: the non-franklin (`clawrouter`) daemon path — wallet
  resolution, balance fetch, THINK routing — must be byte-for-byte unchanged in
  behavior; other running instances on this machine must not be restarted,
  reconfigured, or have their wallets touched.
- **No new spend/keys**: this feature introduces no new spend caps, no new private
  keys, and does not modify `skills/economy/*` or any other instance's cron/skill
  config.
- **Observability**: after the fix, `~/.blockrun/state/ledger.jsonl` wake lines and
  `skills/earn/state/sol-trade.trace.jsonl` trace lines are the source of truth for
  verifying Done — no new logging format is required, only correct existing signals
  (`tier`, `model`, absence of `wake_error:proxy_down`).
