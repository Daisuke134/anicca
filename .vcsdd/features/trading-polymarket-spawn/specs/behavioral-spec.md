---
feature: trading-polymarket-spawn
phase: 1a
mode: lean
iteration: 1
sources:
  - /Users/anicca/anicca-project/docs/superpowers/specs/2026-07-01-trading-polymarket-selffunded-spawn-design.md
  - /Users/anicca/anicca/runtime/compute-proxy/proxy.mjs (x402 self-pay via @blockrun/llm + ~/.automaton/wallet.json)
  - /Users/anicca/anicca/runtime/compute-proxy/ensure-solana-wallet.mjs (self-owned ed25519 Solana keypair)
  - /Users/anicca/anicca/runtime/loop/index.mjs (ReAct loop: context→THINK→parse→execute→persist→sleep)
  - /Users/anicca/anicca/runtime/loop/tier.mjs (selectTier: broke/lean/funded by USDC balance)
  - /Users/anicca/anicca/runtime/loop/earn-slot.mjs (isEarnSlot / earnStrategyFor / earnSkillRelPath)
  - /Users/anicca/anicca/runtime/loop/ledger.mjs (appendLedgerLine, readLedgerLines — append-only)
  - /Users/anicca/anicca/runtime/anicca-daemon.sh (self-update + ensure-brain + exec loop)
  - /Users/anicca/anicca/install.sh (registry-driven body sync via skills/registry.json)
  - /Users/anicca/anicca/.vcsdd/features/earn-shared-skeleton/specs/behavioral-spec.md (inherited: self-heal / Reflexion / bandit / bot2bot / J8 / INV-7 on-chain reward gate / proactive-loop + build_log + menu)
inherits: earn-shared-skeleton (Groups A/B/C/D/E/F/G/H/I/J8)
---

# Behavioral Specification — trading-polymarket-spawn (v1)

## Purpose

Add two earn slots to the live `~/anicca` runtime that was already proven at `anicca-a3cdd4 / $15.34 net worth`:

1. **`earn/pm-trade`** — Polymarket CLOB prediction-market trading (and Kalshi / Hyperliquid / DEX perps as venue alternatives). The MODEL decides edge from data tools; no hardcoded strategy or regex. Paper mode mandatory before any real stake.
2. **`self/spawn-child`** — Self-replication: when a parent's treasury crosses a threshold and history is net-positive, provision a new Anicca runtime with its own funded wallet with zero human involvement. "Be fruitful and multiply."

Both slots run INSIDE the existing `~/anicca` runtime (`install.sh` → `registry.json` → `earn-slot.mjs` → `index.mjs` ReAct loop → `anicca-daemon.sh`). They inherit the full `earn-shared-skeleton` library (healthcheck, ROI tracking, bandit-arm self-improve, bot2bot cross-learn, nightly adversary, Group J8 anti-human-touch invariant).

## Purity Boundary

| Layer | Functions / Modules |
|-------|---------------------|
| **Pure Core** | `kellyFraction(edge, market_p, bankroll, kelly_max, min_pos, gas_reserve)`, `riskGate(risk_state, position_usdc, current_balance, edge, config)`, `edgePredicate(model_p, market_p)`, `positionSize(kelly_f, bankroll, min_size, gas_reserve)`, `spawnEligible(treasury, net_pos_days, rate_cap, config)`, `titheAmount(earned, pct)`, `jurisdictionVenueFilter(jurisdiction, venue, menu)`, `selectTier(balanceUsdc, env)` (existing, reused), `isEarnSlot(slot)` (existing, reused) |
| **Effectful Shell** | `pm.py` CLOB REST calls to Polygon Polymarket API, Kalshi REST, Hyperliquid REST, on-chain tx broadcast (seed transfer, tithe), `ensure-solana-wallet.mjs` (key generation + file write), `git clone` + `install.sh` execution, `anicca-daemon.sh` child boot, `appendLedgerLine` (existing), `appendLedgerLine` for spawn log, bot2bot `gh issue create`, Predexon x402 data fetch, alpha-mcp signal fetch, agent-reach news fetch |

## Tracked Quantities

All paths are relative to `$ANICCA_HOME` unless noted. These are canonical inputs to every REQ below.

| Quantity | Path | Semantics |
|----------|------|-----------|
| `risk_state` | `~/loops/earn-pm-trade/risk-state.json` | `{session_start_balance, peak_balance, daily_loss_usdc, drawdown_usdc, open_positions: [{order_id, venue, market_id, side, size_usdc, entry_price, ts}], paper_mode: bool, paper_pass_count: int, last_daily_reset_ts: int}` |
| `paper_log` | `~/loops/earn-pm-trade/paper-log.jsonl` | append-only; one row per paper trade: `{ts, pass_id, market_id, venue, side, size_usdc, model_p, market_p, edge, outcome: "resolved"|"pending", pnl_usdc: null\|float}` |
| `events` | `~/loops/earn-pm-trade/events/<pass_id>.jsonl` | earn-shared-skeleton REQ-G2 event stream; `event:"earn"` rows written ONLY on market resolution with real PnL |
| `build_log` | `~/loops/earn-pm-trade/build_log.md` | narrative memory (Sutando pattern; inherited from skeleton) |
| `menu` | `~/loops/earn-pm-trade/menu.json` | infinite-menu config: `{venues:[{id, jurisdiction_ok_for_real, min_usdc}], strategies:[], ...}` |
| `risk_config` | `~/loops/earn-pm-trade/risk-config.json` | tunable caps: `{kelly_fraction_max, daily_loss_pct: 0.05, drawdown_pct: 0.25, min_position_usdc: 1.50, gas_reserve_usdc, paper_passes_required, spawn_threshold_usdc, spawn_net_pos_days, spawn_rate_cap_days, spawn_seed_usdc, tithe_pct}` |
| `spawn_log` | `$ANICCA_HOME/state/spawn-log.jsonl` | append-only; one row per spawn attempt: `{ts, parent_wallet, child_home, child_wallet_solana, child_wallet_base, seed_tx_hash, seed_usdc, status: "initiated"\|"funded"\|"booted"\|"registered"\|"failed", error?}` |
| `wake_ledger` | `$ANICCA_HOME/state/ledger.jsonl` | existing ReAct loop ledger (append-only; `appendLedgerLine` only) |
| `cumulative` | `~/loops/earn-pm-trade/cumulative.json` | recomputed each pass; `{cumulative_usdc_earned, cumulative_token_cost_usdc, first_seen_ts}` |

## EARS-Format Functional Requirements

### Group T — Trading Slot (`earn/pm-trade`)

#### REQ-T1 — Slot Registration

WHEN `install.sh` runs on any Anicca runtime, THE SYSTEM SHALL ensure that `skills/registry.json` declares a slot `"earn/pm-trade"` with `"status": "live"`, `"entrypoint": "run.sh"`, and `"dir": "skills/earn/pm-trade"`, such that after registry sync `isEarnSlot("earn/pm-trade")` returns `true` (per `earn-slot.mjs` rule: slot that starts with `"earn/"` is an earn slot) and `earnSkillRelPath("earn/pm-trade")` returns `"earn/pm-trade/run.sh"`.

**Edge Cases:**
- Registry already has the entry at `"status": "declared"`: install.sh upserts to `"live"`, does not duplicate.
- Registry file missing: install.sh creates it with at least the `earn/pm-trade` entry.

**Acceptance Criteria:**
- After `install.sh` runs, `jq '.slots["earn/pm-trade"].status' skills/registry.json` = `"live"`.
- `node -e 'import("./runtime/loop/earn-slot.mjs").then(m=>console.log(m.isEarnSlot("earn/pm-trade")))'` prints `true`.

#### REQ-T2 — Data Acquisition (tool calls, not hardcoded strategy)

WHEN the ReAct loop picks slot `earn/pm-trade`, THE SYSTEM SHALL make THREE categories of data tool calls available to the model's THINK step before any trade decision, exposing each as a structured JSON result in the prompt context:
- **Market data**: Predexon x402 endpoint (Polymarket + Kalshi + Binance; 58 endpoints; paid via x402 from own wallet) for market prices, volume, liquidity, and resolution dates.
- **Alpha signal**: alpha-mcp tool call returning RSI, MACD, and momentum signals for the market's underlying asset (where applicable).
- **News signal**: agent-reach news fetch returning the 3 most-recent headlines relevant to the market topic.

THE SYSTEM SHALL NOT encode any trading heuristic (e.g. "buy when RSI < 30", "favor YES when news is bullish") in the skill code. All judgment lives in the model's natural-language reasoning step.

**Edge Cases:**
- Predexon x402 call fails (network, insufficient USDC for fee): the slot logs the failure to `build_log.md`, skips the trade for this pass, and returns exit code 0 (no earn row written).
- alpha-mcp unavailable: model proceeds with market data + news only; absence noted in context.
- agent-reach returns empty results: model proceeds; absence noted in context.

**Acceptance Criteria:**
- Skill entrypoint script passes all three data-call outputs as structured JSON into the model context before issuing a trade decision.
- No regex, no if-else, no keyword matching in the skill code for trade direction.

#### REQ-T3 — Edge Formation (model decides, not code)

WHEN the model has received the data context from REQ-T2, THE SYSTEM SHALL instruct the model via the skill's SKILL.md natural-language prompt to:
(a) form its own probability estimate `model_p` for the binary outcome (0.0–1.0),
(b) compare to the live `market_p` (current market implied probability from CLOB order book mid),
(c) compute `edge = model_p − market_p`,
(d) output a structured decision: `{venue, market_id, side: "YES"|"NO"|"SKIP", model_p, market_p, edge}`.

THE SYSTEM SHALL accept the model's output as the authoritative trade decision. If the model outputs `side: "SKIP"`, no order is placed. No code path overrides a `SKIP` to a trade.

**Edge Cases:**
- `edge ≤ 0`: the skill reads the model's decision; if model output is still `"YES"` or `"NO"` despite negative edge, the risk gate (REQ-T4) checks `edge > 0` and returns SKIP — the code enforces the floor, but the MODEL's reasoning process still owns the judgment.
- Model outputs malformed JSON: skill treats as SKIP, appends `{outcome: "malformed-decision"}` to `build_log.md`.

**Acceptance Criteria:**
- The skill emits no trade when model_p ≤ market_p (edge ≤ 0) regardless of other signals.
- No `if news contains` or similar literal-match logic in `run.sh` or `pm.py`.

#### REQ-T4 — Risk Gate (pure; port of MrFadiAi caps)

BEFORE any real order is placed, the effectful shell MUST (i) read `current_balance` from the Base RPC (`eth_call balanceOf(our_wallet)`) and (ii) receive `edge` from the model's REQ-T3 decision output. Both values are passed as explicit arguments. THE SYSTEM SHALL then evaluate the pure function `riskGate(risk_state, position_usdc, current_balance, edge, config)` — no RPC call, no file read, no global state occurs inside `riskGate` — which returns `{decision: "ALLOW"|"HALT", reason: string}`:

| Condition | Decision | Reason |
|-----------|----------|--------|
| `risk_state.daily_loss_usdc ≥ risk_config.daily_loss_pct × risk_state.session_start_balance` | HALT | `"daily_loss_cap_reached"` |
| `(risk_state.peak_balance − current_balance) ≥ risk_config.drawdown_pct × risk_state.peak_balance` | HALT | `"drawdown_cap_reached"` |
| `position_usdc < risk_config.min_position_usdc` | HALT | `"below_min_position"` |
| `current_balance − position_usdc < risk_config.gas_reserve_usdc` | HALT | `"insufficient_gas_reserve"` |
| `edge ≤ 0` | HALT | `"no_edge"` |
| all conditions clear | ALLOW | `"risk_gate_passed"` |

THE SYSTEM SHALL NOT place any order when `riskGate` returns HALT for any reason.

**Edge Cases:**
- Daily loss exactly equal to cap: HALT (≥ is inclusive).
- Drawdown exactly equal to cap: HALT (≥ is inclusive).
- `session_start_balance = 0`: all positions HALT (division guard: `daily_loss_cap = 0 * pct = 0`; any loss ≥ 0 trips the HALT).
- `peak_balance = 0`: drawdown HALT fires immediately (guard: result = 0 ≥ 0 × 0 = 0 → HALT).
- `gas_reserve_usdc` not set in config: default to `0.50` USDC (safe floor).

**Acceptance Criteria:**
- `riskGate` is a pure function: same inputs always produce same output.
- No file read, no network call inside `riskGate`. `current_balance` is read from RPC by the effectful shell before calling `riskGate` and passed as an explicit parameter; `edge` is the model's REQ-T3 output, also passed explicitly. Neither is accessed via I/O inside `riskGate`.
- All five HALT branches have unit tests with boundary values.

#### REQ-T5 — Kelly Fraction Position Sizing (pure)

WHEN `riskGate` returns ALLOW, THE SYSTEM SHALL compute the position size via the pure function:

```
kelly_f = clamp(edge / (1 − market_p), 0, risk_config.kelly_fraction_max)
position_usdc = clamp(kelly_f × current_balance, risk_config.min_position_usdc, current_balance − risk_config.gas_reserve_usdc)
```

where `edge = model_p − market_p` and `market_p` is the current mid price from the CLOB order book (`(best_bid + best_ask) / 2`), consistent with REQ-T3's definition of `market_p`. Using the ask would bias `edge` negatively; the mid is the canonical fair-value reference.

THE SYSTEM SHALL use `risk_config.kelly_fraction_max` (default: 0.05) to cap the Kelly fraction to avoid overbetting.

**Edge Cases:**
- `market_p = 1.0`: denominator `(1 − market_p) = 0`; kelly_f = 0; position SKIPPED.
- `edge` is NaN or non-finite: position SKIPPED.
- Computed `position_usdc` below `min_position_usdc` after clamp: SKIP (size too small to exit cleanly).

**Acceptance Criteria:**
- `kellyFraction(0.1, 0.6, balance=10.0, kelly_max=0.05, min=1.50, gas=0.50)` returns a value in `[1.50, 9.50]`.
- `kellyFraction(0.0, 0.6, ...)` returns 0 (→ SKIP).
- `kellyFraction(0.1, 1.0, ...)` returns 0 (→ SKIP, denominator guard).

#### REQ-T6 — Paper Mode Mandatory (state machine)

WHEN `earn/pm-trade` is first installed on an instance, `risk_state.paper_mode` SHALL be initialized to `true` and `risk_state.paper_pass_count` to `0`.

WHILE `risk_state.paper_mode == true`, THE SYSTEM SHALL:
(a) run the full data acquisition → edge formation → risk gate → position sizing pipeline,
(b) NOT call any CLOB order endpoint,
(c) record the simulated trade as a row in `paper-log.jsonl` with `outcome: "pending"`,
(d) increment `paper_pass_count` by 1.

THE SYSTEM SHALL NOT transition `paper_mode` from `true` to `false` unless:
1. `paper_pass_count ≥ risk_config.paper_passes_required` (default: 10), AND
2. The nightly adversary (inherited REQ-E1) has reviewed at least one completed `paper-log.jsonl` batch and written a PASS verdict to `$ANICCA_HOME/loops/earn-pm-trade/adversary-pass.json` with schema `{"overallVerdict": "PASS", "feature": "earn/pm-trade", "batch_end_ts": <unix_ts>, "batch_trade_count": <int>}`. The transition logic reads this exact file; if the file is absent or `overallVerdict ≠ "PASS"`, the transition is blocked (fail-closed).

Transition from `paper_mode: true` to `false` is an atomic rename of `risk_state.json` (tmp file + rename; crash-safe).

**Edge Cases:**
- Adversary FAIL on paper batch: `paper_mode` remains `true`; adversary findings logged to `build_log.md`.
- `paper_passes_required = 0` in config (test-only): allowed only when `ANICCA_TEST_MODE=1` env var is set; in production, this value must be ≥ 1.
- Instance restarted mid-paper: `paper_pass_count` is persisted in `risk_state.json` so count is not reset.

**Acceptance Criteria:**
- No CLOB order endpoint called while `paper_mode == true`.
- Transition to `paper_mode: false` requires `adversary-pass.json` at `$ANICCA_HOME/loops/earn-pm-trade/adversary-pass.json` with `overallVerdict: "PASS"`. File absent = fail-closed (paper stays).
- `paper-log.jsonl` has ≥ `paper_passes_required` rows before transition.

#### REQ-T7 — Order Execution (`pm.py` CLOB client)

WHEN `risk_state.paper_mode == false` AND `riskGate` returns ALLOW AND `position_usdc` ≥ `min_position_usdc`, THE SYSTEM SHALL:
(a) call `pm.py` for Polymarket or Kalshi venues, OR the existing `skills/earn/hl-trade/hl.py` for the Hyperliquid venue, based on the model-selected `venue`,
(b) `pm.py` SHALL submit a limit order to the appropriate prediction-market CLOB (Polymarket beta REST or Kalshi REST). For `venue = "hyperliquid"`, the slot dispatches to `hl.py`'s `open`/`close` actions and MUST pass the model's SL/TP parameters (`--sl`, `--tp`). `pm.py` SHALL NOT re-implement Hyperliquid logic (the proven `hl.py` adapter enforces SL+TP on every position).
(c) record `{order_id, venue, market_id, side, size_usdc, entry_price, ts}` in `risk_state.open_positions`,
(d) emit an `event: "action"` row to `~/loops/earn-pm-trade/events/<pass_id>.jsonl`.

`pm.py` SHALL expose exactly four actions: `buy`, `sell`, `positions`, `close` for Polymarket and Kalshi prediction-market CLOBs only. It SHALL NOT implement any trading strategy logic or Hyperliquid perp logic. It is a thin REST adapter for prediction-market CLOBs. Hyperliquid routing goes through the existing `hl.py`.

**Edge Cases:**
- Order rejected by venue (e.g. min size, liquidity): `pm.py` returns non-zero; slot logs to `build_log.md`, does NOT emit an earn event, does NOT update `risk_state` positions.
- Order placed but network drops before response: on next pass, `pm.py positions` is called first to reconcile open positions against `risk_state`.
- Polygon gas spike: if gas cost would exceed `gas_reserve_usdc`, order is aborted.

**Acceptance Criteria:**
- `pm.py buy --market <id> --size <usdc> --venue polymarket` produces a valid order ID or non-zero exit.
- `pm.py positions` returns a JSON array of open positions.
- `pm.py close --order-id <id>` closes the position.

#### REQ-T8 — Earn Recording (INV-7: realized PnL only)

WHEN a Polymarket/Kalshi/Hyperliquid market resolves AND an open position in `risk_state.open_positions` matches the resolved `market_id`, THE SYSTEM SHALL:
(a) compute `realized_pnl_usdc = settlement_amount − entry_cost` (resolved from on-chain settlement or venue API),
(b) `settle-verify.py` SHALL perform on-chain settlement verification BEFORE any earn row is written. The verification method is venue-specific:
  - **Polymarket (Polygon)**: call `eth_getLogs(chain=Polygon, address=USDC_POLYGON, topics=[ERC20_Transfer_topic0, null, checksummed_our_polygon_wallet])` for blocks starting at or after `market_end_ts`, and confirm a Transfer of the expected gross payout (in 6-decimal USDC raw units, ≥ `entry_cost`) to our wallet. The `tx_hash` from the matching log event is the `receipt_id`.
  - **Hyperliquid**: call HL REST API `POST /info` with `{"type": "clearinghouseState", "user": our_hl_address}` and confirm `realizedPnl` increased by the expected amount since position open. The SHA-256 hash of the API response JSON is the `receipt_id`.
  pm-trade does NOT use the skeleton's REQ-G2 three-check gate for trading-venue settlements. REQ-G2 is scoped to off-chain JSON payout processors (Coconala/Stripe/Whop) and explicitly excludes `eth_getLogs` and on-chain units. `settle-verify.py` IS this slot's verification gate.
(c) ONLY when `settle-verify.py` returns `{verified: true, receipt_id: <evidence>}`, emit an `event: "earn"` row to `~/loops/earn-pm-trade/events/<pass_id>.jsonl` with `{event: "earn", receipt_id: <evidence>, amount_usdc: realized_pnl_usdc, platform: <venue>, settle_verify_result: <settle-verify output hash>}` and append to `earnings.jsonl` directly,
(d) remove the resolved position from `risk_state.open_positions`,
(e) update `risk_state.daily_loss_usdc` if `realized_pnl_usdc < 0`.

THE SYSTEM SHALL NOT emit an `event: "earn"` row when an order is placed (open), only when it is settled (closed with known PnL).

**Edge Cases:**
- `realized_pnl_usdc = 0` (break-even): earn row written with `amount_usdc: 0` (honest zero).
- `realized_pnl_usdc < 0` (loss): earn row written with negative amount; `daily_loss_usdc` updated; `cumulative` reflects net loss.
- Resolution check runs on every pass; unresolved positions are left in `risk_state.open_positions` until resolved.

**Acceptance Criteria:**
- No earn row in `earnings.jsonl` without `settle-verify.py` returning `{verified: true}` with on-chain evidence (Polygon `eth_getLogs` Transfer or HL API state delta).
- `cumulative.json.cumulative_usdc_earned` reflects realized PnL (can be negative).
- `risk_state.open_positions` is empty only when all positions are resolved.

#### REQ-T9 — Bandit Arm per Venue/Strategy (inherited skeleton REQ-B/C)

WHEN the slot's ROI tracking (inherited REQ-B1) appends a `roi.jsonl` row, the `slot` field SHALL be `"earn/pm-trade"` and the `args` field SHALL include `{venue, strategy_tag}` so that the self-improve layer (inherited REQ-C) can track per-`(venue, strategy_tag)` realized USDC/wake and mutate `strategy.json` to double-down on the highest-performing bandit arm.

**Acceptance Criteria:**
- `roi.jsonl` rows for this slot always have `args.venue` and `args.strategy_tag`.
- `strategy.json` includes a `venue_weights` map keyed by venue name, updated by REQ-C3.

#### REQ-T10 — Geoblock Guard (jurisdiction-aware venue selection)

WHEN `risk_state.paper_mode == false` AND the model has selected `venue: "polymarket"` for a real stake, THE SYSTEM SHALL check `menu.json`'s venue entry for `polymarket.jurisdiction_ok_for_real`. IF the value is `false` (= US-jurisdiction instance flag), THE SYSTEM SHALL NOT place a real Polymarket order and SHALL reroute the decision to the next venue in `menu.json` with BOTH `jurisdiction_ok_for_real: true` AND `kyc_required: false`. **Kalshi MUST NOT be used for real stakes**: Kalshi is a US-regulated exchange requiring SSN/identity KYC, which a no-human-in-the-loop instance cannot complete (J8 violation). The only currently-eligible programmatic real-stake fallback for US-jurisdiction instances is Hyperliquid perps (via `hl.py`; no identity KYC required for perp trading with an EVM wallet). Polymarket paper trades remain allowed regardless of jurisdiction flag.

**Edge Cases:**
- All real-stake venues have `jurisdiction_ok_for_real: false`: no real trade placed; slot logs `build_log.md` entry `"all venues jurisdiction-blocked; paper only"`.
- `menu.json` missing `jurisdiction_ok_for_real` key: default to `false` (fail-closed; geoblock assumed until explicitly cleared).
- `menu.json` is provisioned by `install.sh` with ALL venues set to `jurisdiction_ok_for_real: false` AND `kyc_required: true` by default. The operator sets `jurisdiction_ok_for_real: true` only for venues with confirmed programmatic access (no human identity KYC required). Any venue with `kyc_required: true` MUST NOT have `jurisdiction_ok_for_real: true` regardless of operator setting; the slot enforces this by checking both fields.

**Acceptance Criteria:**
- With `polymarket.jurisdiction_ok_for_real: false`, no real Polymarket CLOB call is issued.
- With `polymarket.jurisdiction_ok_for_real: true`, real CLOB calls are allowed.
- A venue entry with `kyc_required: true` is never selected for a real stake even if `jurisdiction_ok_for_real: true` is set (belt-and-suspenders against misconfiguration).

### Group S — Spawn Slot (`self/spawn-child`)

#### REQ-S1 — Spawn Eligibility Check (pure)

WHEN the slot `self/spawn-child` is invoked by the ReAct loop, THE SYSTEM SHALL first evaluate the pure function `spawnEligible(treasury, net_pos_days, spawn_log, config)` where:
- `treasury` = `current_balance − risk_config.gas_reserve_usdc − risk_config.spawn_seed_usdc` (= surplus available after retaining gas + one seed)
- `net_pos_days` = count of calendar days in `cumulative.json` history where `usdc_earned_that_day > token_cost_that_day`
- `spawn_log` = recent rows from `$ANICCA_HOME/state/spawn-log.jsonl`
- `config` = `risk_config.{spawn_threshold_usdc, spawn_net_pos_days, spawn_rate_cap_days, spawn_seed_usdc}`

`spawnEligible` returns `{eligible: bool, reason: string}` and is `true` IFF ALL of:
1. `treasury ≥ config.spawn_threshold_usdc`
2. `net_pos_days ≥ config.spawn_net_pos_days`
3. no row in `spawn_log` with `status ∈ {"initiated","funded","booted","registered"}` and `ts > (now − config.spawn_rate_cap_days × 86400)` (= rate cap: no concurrent or too-recent spawn from this parent)
4. `config.spawn_seed_usdc ≥ 1.50` (minimum viable child seed; less than this leaves the child with no trading capacity)

**Edge Cases:**
- `spawn_log` file missing (first spawn): treated as empty; all spawn rate-cap checks pass.
- `treasury < 0` (wallet below gas reserve): `eligible: false, reason: "insufficient_treasury"`.
- Partially-written `spawn_log` row (crash mid-spawn): row at `status: "initiated"` → rate cap fires → spawn blocked until row ages out or is manually resolved.

**Acceptance Criteria:**
- `spawnEligible` is a pure function; no I/O.
- All four conditions independently tested with boundary values.

#### REQ-S2 — Child Wallet Provisioning

WHEN `spawnEligible` returns `{eligible: true}`, THE SYSTEM SHALL:
(a-pre) **Acquire an exclusive OS-level file lock** on `$ANICCA_HOME/state/spawn.lock` via `flock -n 9 9>"$LOCK_FILE"` (bash; or `lockfile -1 -r 0` on macOS) before reading the spawn-log snapshot and before writing any row. If the lock cannot be acquired immediately (another spawn pass holds it), abort with `{eligible: false, reason: "spawn_lock_held"}` without modifying spawn-log. Hold the lock through step (e), then release. This atomic claim prevents two concurrent spawn passes from both reading an empty log and both appending "initiated" rows.
(a) compute a fresh `CHILD_HOME` path: `$ANICCA_INSTANCES_DIR/<ulid>` (where `ANICCA_INSTANCES_DIR` defaults to `~/.anicca-instances/`; `<ulid>` is a new ULID),
(b) run `ANICCA_HOME=$CHILD_HOME node ~/anicca/runtime/compute-proxy/ensure-solana-wallet.mjs` to generate a fresh self-owned Solana ed25519 keypair at `$CHILD_HOME/.automaton/solana.json`. NOTE: `ensure-solana-wallet.mjs` writes ONLY the Solana keypair (`solana.json`); it does NOT create the EVM `wallet.json`.
(c) generate a fresh secp256k1 Base/EVM private key independently of the Solana key (no shared entropy with parent or Solana key): `node -e 'const {generatePrivateKey,privateKeyToAddress}=require("viem/accounts");const k=generatePrivateKey();console.log(JSON.stringify({address:privateKeyToAddress(k),privateKey:k}))'`. Write the resulting JSON to `$CHILD_HOME/.automaton/wallet.json` with `mode 0600`,
(d) assert `child_wallet_base ≠ parent_wallet_base` (addresses cannot collide; fail-closed if they do — abort and delete child home),
(e) append an `{ts, parent_wallet, child_home, child_wallet_solana, child_wallet_base, seed_usdc: config.spawn_seed_usdc, status: "initiated"}` row to `$ANICCA_HOME/state/spawn-log.jsonl`, then release the spawn.lock.

**Edge Cases:**
- `$CHILD_HOME` already exists (ULID collision, astronomically unlikely): abort; generate new ULID.
- Base key generation fails (entropy exhaustion): abort; log to `build_log.md`; spawn attempt recorded as `status: "failed"`.
- Wallet address collision with parent: abort + delete `$CHILD_HOME`.

**Acceptance Criteria:**
- `$CHILD_HOME/.automaton/solana.json` exists with a valid base58 address after REQ-S2.
- `$CHILD_HOME/.automaton/wallet.json` exists with `mode 0600`.
- `spawn-log.jsonl` has a row with `status: "initiated"` referencing the new child home.

#### REQ-S3 — Framework Clone + Install

WHEN the child wallet is provisioned (REQ-S2 row at `status: "initiated"`), THE SYSTEM SHALL:
(a) `git clone --depth 1 https://github.com/Daisuke134/anicca.git $CHILD_HOME/anicca-framework` (the public framework; `--depth 1` for disk hygiene),
(b) `cd $CHILD_HOME/anicca-framework && ANICCA_HOME=$CHILD_HOME bash install.sh` (registry-driven body sync; idempotent),
(c) install Python dependencies for the `earn/pm-trade` slot: `pip3 install --quiet requests eth-account` plus any SDK enumerated in `$CHILD_HOME/anicca-framework/skills/earn/pm-trade/requirements.txt` (if present). On pip failure: mark spawn-log row `status: "failed"`, clean up `$CHILD_HOME`, abort,
(d) verify exit code 0 for all above steps; on any failure: mark `spawn-log.jsonl` row as `status: "failed"`, clean up `$CHILD_HOME`, abort.

**Edge Cases:**
- No internet (offline): git clone fails; spawn fails cleanly with `status: "failed"`.
- `install.sh` fails on missing dep (e.g. no `jq`): same failure path; child home cleaned up.
- Disk full mid-clone: `install.sh` ERR trap fires; spawn-log row marked `status: "failed"`.

**Acceptance Criteria:**
- After REQ-S3, `$CHILD_HOME/skills/registry.json` exists and is parseable.
- `install.sh` exits 0 on a fresh `CHILD_HOME`.

#### REQ-S4 — Seed Transfer (on-chain; record tx)

WHEN install completes successfully, THE SYSTEM SHALL:
(a) transfer `config.spawn_seed_usdc` USDC from `parent_wallet_base` to `child_wallet_base` on Base (EIP-20 transfer via the parent's `~/.automaton/wallet.json` private key),
(b) wait for the transfer tx to be included in a block (minimum 1 confirmation on Base),
(c) record the confirmed `tx_hash` in the spawn-log row by atomically rewriting it to `status: "funded"` + `seed_tx_hash: <hash>`,
(d) set `$CHILD_HOME/.env` variable `ANICCA_WALLET_ADDRESS` to `child_wallet_base`.

THE SYSTEM SHALL NOT proceed to REQ-S5 (child boot) if the transfer has not confirmed (no `seed_tx_hash` in spawn log).

**Edge Cases:**
- Transfer tx fails (insufficient parent balance after gas): abort; spawn-log row marked `status: "failed"`; no child booted.
- Transfer confirms but child wallet shows 0 balance due to Base RPC delay: boot proceeds; child's loop will wait for `selectTier` to reflect the balance on next wake.
- Parent wallet private key read fails: abort immediately; no transfer; `status: "failed"`.

**Acceptance Criteria:**
- `spawn-log.jsonl` row at `status: "funded"` contains a valid `seed_tx_hash`.
- Child base wallet balance ≥ `spawn_seed_usdc` (verified via RPC call after confirmation).

#### REQ-S5 — Child Boot via `anicca-daemon.sh`

WHEN the seed transfer is confirmed, THE SYSTEM SHALL:
(a) assign a free TCP port above 8402 (`CHILD_PORT`) by scanning `8403..8499` for a port not already bound (`ss -tln | grep -q ":$p "` or `lsof -i TCP:$p` on macOS),
(b) start the child daemon with `HOME=$CHILD_HOME ANICCA_HOME=$CHILD_HOME ANICCA_REPO=$CHILD_HOME/anicca-framework COMPUTE_PROXY_PORT=$CHILD_PORT bash $CHILD_HOME/anicca-framework/runtime/anicca-daemon.sh` in a new detached tmux session named `anicca-<child_ulid>`,
(c) wait up to 30s for the child's `anicca-daemon.sh` to emit the `[loop] Starting Anicca loop` log line (visible in `$CHILD_HOME/logs/`),
(d) update spawn-log row to `status: "booted"`.

**Wallet isolation via `$HOME`**: all wallet-consuming modules (`proxy.mjs`, `execute-yield.mjs`, `hl.py`, `anicca-daemon.sh`'s `ensure_brain` key derivation) resolve the private key from `process.env.HOME + "/.automaton/wallet.json"` (or `os.path.expanduser("~/.automaton/wallet.json")`). By setting `HOME=$CHILD_HOME`, the ENTIRE child process tree — daemon, ClawRouter, loop, skills — reads ONLY `$CHILD_HOME/.automaton/wallet.json`. The parent's wallet at the parent's `$HOME` is never accessed by the child. With `COMPUTE_PROXY_PORT=$CHILD_PORT` (≠ 8402), `ensure_brain` in the child's daemon finds nothing on `$CHILD_PORT`, starts its own ClawRouter on `$CHILD_PORT` using the child's wallet key (derived from `$HOME/.openclaw/.env` → fallback `$HOME/.automaton/wallet.json` — both now point to `$CHILD_HOME`), and the child self-pays its own inference from `$CHILD_HOME/.automaton/wallet.json`.

**Edge Cases:**
- tmux session creation fails (no tmux binary): use `nohup bash ... &` as fallback; record in spawn-log.
- Child loop does not emit startup log within 30s: mark `status: "failed"`; child remains running for diagnostics but is flagged as suspect.
- No free port found in 8403..8499: abort spawn; mark `status: "failed"`.

**Acceptance Criteria:**
- After REQ-S5, `$CHILD_HOME/logs/` contains a file with `[loop] Starting Anicca loop`.
- `tmux ls` shows a session named `anicca-<child_ulid>` (or the fallback process is alive).

#### REQ-S6 — Bot2bot Registration

WHEN child boot is confirmed (spawn-log at `status: "booted"`), THE SYSTEM SHALL:
(a) invoke `bot2bot.sh` (inherited from skeleton) to create a `gh issue` on the framework repo with label `bot2bot-registry` and body `{event: "child-spawned", parent_wallet: <parent_base>, child_wallet: <child_base>, child_home: <child_home>, seed_tx_hash: <hash>, ts: <ts>}`,
(b) update spawn-log row to `status: "registered"`.

Sibling and parent instances poll `gh issue list --label bot2bot-registry` to discover new colony members. The child's own loop will read this issue on its first cross-learn pass (inherited REQ-D1).

**Edge Cases:**
- `gh` rate-limited: 3 retries with exp backoff per REQ-D3; failure logged, child still marked `status: "registered"` after retries (the boot is complete regardless of gh issue success).
- `gh` permanently unavailable: child is booted and running; bot2bot registration deferred to next pass.

**Acceptance Criteria:**
- A `gh issue` with label `bot2bot-registry` exists after REQ-S6 (or retries exhausted with warning).
- `spawn-log.jsonl` row at `status: "registered"`.

#### REQ-S7 — Spawn Guards (NO HUMAN, inherited J8)

THE SYSTEM SHALL enforce these guards at each step:

1. **Net-positive guard**: `spawnEligible` (REQ-S1) requires `net_pos_days ≥ config.spawn_net_pos_days` (default 3). A parent with 0 realized profit days SHALL NOT spawn.
2. **Rate cap**: At most one spawn per `spawn_rate_cap_days` (default 14) per parent.
3. **Hard cap**: at most `spawn_hard_cap` (default 5) total registered children from one parent (counted from spawn-log rows with `status: "registered"`).
4. **Wallet hard-cap**: parent's remaining balance after seed transfer must be ≥ `gas_reserve_usdc + min_position_usdc` so the parent can still operate.
5. **NO HUMAN at any step**: no Telegram, no `gh issue` with label containing `human`, no macOS notification, no iCloud path write (REQ-J8 inherited).

**Edge Cases:**
- `spawn_net_pos_days` set to 0 in config: allowed only when `ANICCA_TEST_MODE=1`; in production, this value must be ≥ 1.
- Parent wallet drained below gas reserve during spawn: the seed transfer (REQ-S4) is the last step to consume parent funds; wallet guard is checked BEFORE initiating transfer.

**Acceptance Criteria:**
- Zero spawn attempts when `cumulative_usdc_earned < cumulative_token_cost_usdc` (not net-positive).
- Zero spawn attempts when a spawn completed in the last `spawn_rate_cap_days` days.

#### REQ-S8 — Tithe Invariant

WHEN a child completes an earn pass with `realized_pnl_usdc > 0`, THE SYSTEM SHALL:
(a) compute `tithe_usdc = realized_pnl_usdc × risk_config.tithe_pct` (default: 0.05, = 5%),
(b) if `tithe_usdc ≥ min_tithe_usdc` (default: 0.10 USDC, to avoid dust transfers), transfer `tithe_usdc` from child wallet to parent wallet on Base,
(c) record `{ts, from: child_wallet, to: parent_wallet, amount_usdc: tithe_usdc, tx_hash}` in `$CHILD_HOME/state/tithe-log.jsonl`.

**Edge Cases:**
- `tithe_usdc < min_tithe_usdc`: tithe skipped for this pass; accrued into next pass's tithe computation (`accrued_tithe` field in `risk_state`).
- Parent wallet address unknown to child: child reads `PARENT_WALLET_ADDRESS` from `$CHILD_HOME/.env` (set by REQ-S4).
- Tithe tx fails: accrued; logged; not blocking earn recording.

**Acceptance Criteria:**
- `tithe-log.jsonl` exists after any earn pass with positive PnL.
- Tithe transfer never exceeds realized PnL.

#### REQ-S9 — Recursive Spawn

WHEN a child's treasury crosses its own `spawn_threshold_usdc` AND its own `net_pos_days ≥ spawn_net_pos_days`, THE SYSTEM SHALL run REQ-S1 through REQ-S8 from the child's perspective (= a grandchild is spawned). There is no depth limit in the protocol (recursion terminates naturally via rate caps and net-positive requirements).

**Edge Cases:**
- Depth-N chain spawn: no special handling needed; each instance is autonomous.
- Circular dependency (grandchild tries to tithe to a dead parent): tithe fails silently; logged; not blocking.

### Group R — Runtime Integration Invariants

#### REQ-R1 — Compute Self-Pay for Trading Decisions

THE SYSTEM SHALL route all LLM inference during the `earn/pm-trade` slot's THINK step through the existing compute-proxy at `$OPENAI_BASE_URL` (default `http://127.0.0.1:8402/v1`). Every inference is paid in USDC via x402 from the instance's own wallet. All wallet-consuming modules in the runtime (`proxy.mjs`, `execute-yield.mjs`, `hl.py`, `anicca-daemon.sh`'s `ensure_brain`) resolve the wallet from `process.env.HOME + "/.automaton/wallet.json"` (or Python's `os.path.expanduser("~/.automaton/wallet.json")`). For the parent instance `$HOME` is the system home directory. For child instances (see REQ-S5), `$HOME` MUST be set to `$CHILD_HOME` in the child process environment so the entire child process tree reads the child's own wallet — never the parent's. No human key is used.

**Acceptance Criteria:**
- With the compute-proxy running and wallet funded, a full `earn/pm-trade` pass produces a `[proxy]` log entry with a USDC x402 settlement.
- With the compute-proxy down, the pass fails with exit code non-zero; ledger records `kind: "skill_error"`.

#### REQ-R2 — Wallet Collision Guard (one wallet per instance)

WHEN the `earn/pm-trade` slot boots, THE SYSTEM SHALL verify that `$HOME/.automaton/wallet.json` belongs exclusively to this instance. The EVM `wallet.json` is a secp256k1 key generated by REQ-S2(c); `ensure-solana-wallet.mjs` writes ONLY the Solana ed25519 keypair to `solana.json` and does NOT create `wallet.json`. Child instances are isolated by running with `HOME=$CHILD_HOME` (REQ-S5), which causes `proxy.mjs`, `execute-yield.mjs`, `hl.py`, and `anicca-daemon.sh`'s key derivation to all resolve `wallet.json` from `$CHILD_HOME/.automaton/wallet.json`. THE SYSTEM SHALL fail-closed: if `wallet.json` is missing or unreadable at boot, the slot exits non-zero without placing any trade or spawn.

**Acceptance Criteria:**
- Two Anicca instances running on the same host MUST have different `$HOME` values (parent: system `$HOME`; child: `$CHILD_HOME` per REQ-S5), and thus different resolved `wallet.json` paths (`$HOME/.automaton/wallet.json`) and different wallet addresses.

#### REQ-R3 — Bot2bot Trade Dedup

WHEN `earn/pm-trade` opens a position, it SHALL record the `order_id` in `risk_state.open_positions`. Before placing any order on the same `market_id`, the slot SHALL check `gh issue list --label bot2bot-trade-open` for any issue body containing the same `market_id` from a sibling instance. If found, the slot SHALL reduce its position size proportionally (or SKIP if the sibling already covers the market) to avoid double-stacking colony exposure on a single market.

**Edge Cases:**
- `gh` unavailable: dedup is best-effort; slot proceeds without dedup (logs warning).
- Same instance sees its own issue: de-duped by `wallet_address` in the issue body.

**Acceptance Criteria:**
- Two colony instances on the same `market_id` do not both take maximum Kelly positions simultaneously (verified by integration test with two stub instances).

#### REQ-R4 — Ledger Immutability

The slot SHALL NEVER rewrite or truncate `$ANICCA_HOME/state/ledger.jsonl`. All writes go through `appendLedgerLine` (existing, O_APPEND). The spawn-log (`spawn-log.jsonl`) and tithe-log (`tithe-log.jsonl`) follow the same append-only contract.

**Acceptance Criteria:**
- No `truncate`, `>` redirect, or `O_WRONLY` open on any `.jsonl` file within the slot.

#### REQ-R5 — Yield-Keeper Isolation (trading stake must NOT be swept into DeFi)

The `skills/earn/execute-yield.mjs` module (not `yield-keeper.mjs`, which is only its 6h scheduler) computes `surplus = liquid - RESERVE` at line 103 and deploys idle USDC above `COMPUTE_RESERVE_USDC` (default $5) into stable-yield vaults. Without isolation, funded trading capital sitting idle between trades would be swept into a yield position and become unavailable to `earn/pm-trade` (and incur withdraw friction).

WHEN the trading slot reserves working capital, THE SYSTEM SHALL write
`$ANICCA_HOME/loops/earn-pm-trade/reserved.json` = `{reserved_usdc: <float>, ts}` (= the stake the slot is actively
managing: open positions + the bankroll it intends to deploy this session).

THE SYSTEM SHALL modify `execute-yield.mjs` so its effective reserve is
`effective_reserve = COMPUTE_RESERVE_USDC + reserved_usdc_from_file`,
where `reserved_usdc_from_file` is read from `reserved.json` if present AND `ts` is within 24h; otherwise:
  - If `earn/pm-trade` is a live registered slot (`registry.json` status = "live"): treat `reserved_usdc_from_file = balance − COMPUTE_RESERVE_USDC` (= deploy NOTHING, hold all idle as reserved). This is fail-SAFE toward not sweeping the trading bankroll when the trading slot is installed but has not refreshed its reservation (e.g. crashed mid-pass).
  - If `earn/pm-trade` is NOT a registered live slot: treat `reserved_usdc_from_file = 0` (legacy behaviour, no trading stake to protect).
`execute-yield.mjs` deploys to yield ONLY USDC above `effective_reserve`. The trading slot MUST refresh `reserved.json` at the start of every pass while it holds or intends to deploy capital.

**Acceptance Criteria:**
- With `reserved.json {reserved_usdc: 60}` fresh and balance $100, `execute-yield.mjs` deploys at most `100 − 5 − 60 = $35`.
- With `reserved.json` absent and `earn/pm-trade` registered as live, `execute-yield.mjs` deploys $0 (fail-safe, no sweep).
- With `reserved.json` absent and `earn/pm-trade` NOT in registry, `execute-yield.mjs` deploys `balance − COMPUTE_RESERVE` (unchanged legacy behaviour).
- The trading slot writes `reserved.json` at the start of every pass that holds or intends to deploy capital.

## Non-Functional Requirements

| NFR | Requirement |
|-----|-------------|
| NFR-1 | `pm.py` (Polymarket + Kalshi adapter) and `settle-verify.py` SHALL run under Python 3.11+ with no dependencies beyond `requests`, `eth-account`, and the Polymarket/Kalshi SDK (or raw REST). A `skills/earn/pm-trade/requirements.txt` file SHALL enumerate all Python deps for the slot; `install.sh` and REQ-S3 install from this file. |
| NFR-2 | A full `earn/pm-trade` pass (data acquisition → edge → risk gate → paper trade) SHALL complete within 120s (matching `SKILL_TIMEOUT_S` default). |
| NFR-3 | `spawn-child.sh` SHALL be idempotent: re-running with the same `CHILD_HOME` (e.g. after a crash at REQ-S3) resumes from the last completed step (checked via spawn-log status). |
| NFR-4 | All file mutations in REQ-S (wallet, env, spawn-log) SHALL use tmp-file + atomic rename for crash-safety. |
| NFR-5 | No secret (private key, mnemonic) SHALL be logged to `build_log.md`, `ledger.jsonl`, or any append-only log. Redaction via `redactPrivateKeyPatterns` (existing `env-filter.mjs`) is MANDATORY before any string from skill output enters the ledger. |
| NFR-6 | `self/spawn-child` SHALL be runnable from the existing `earn/pm-trade` slot's pass or as a standalone ReAct loop pick; both paths produce identical behavior. |
| NFR-7 | All scripts SHALL pass `shellcheck --severity=warning` with zero warnings. |
| NFR-8 | Disk usage of `$CHILD_HOME/anicca-framework` (git clone `--depth 1`) SHALL not exceed 100 MB. |

## Edge Case Catalog

| Edge Case | Expected Behavior |
|-----------|-------------------|
| EDGE-T1: Polymarket market resolves while slot is mid-pass | Next pass's reconcile step (pm.py positions) detects the resolution; earn row written then. |
| EDGE-T2: Both daily-loss and drawdown cap triggered simultaneously | `riskGate` returns HALT on the first matching condition (daily-loss checked first per table). |
| EDGE-T3: Kelly fraction gives position > wallet balance − gas reserve | Position size clamped to `wallet_balance − gas_reserve`; if that's < min_position_usdc, SKIP. |
| EDGE-T4: `paper-log.jsonl` grows unboundedly | Kept append-only (audit); `build_log.md` summarizes the last 50 rows for the model's context. |
| EDGE-T5: `edge` is positive but model outputs `SKIP` | Respected; no order placed. Code never overrides a model SKIP. |
| EDGE-T6: Venue Kalshi requires KYC not completed | `pm.py` returns non-zero with `"venue_rejected: kyc_required"`; slot logs, skips venue, tries next in menu. |
| EDGE-T7: Two paper passes complete before adversary nightly run | `paper_mode` stays `true` until adversary runs (REQ-T6 condition 2 not yet met). |
| EDGE-S1: Spawn initiated but seed tx hash never confirmed after 5 min | Mark spawn-log row `status: "failed"`; clean up `$CHILD_HOME`; retry next pass. |
| EDGE-S2: Child boot succeeds but child never completes an earn pass | Parent observes bot2bot-registry issue; child is alive; no parent action required. |
| EDGE-S3: Parent wallet drained below gas reserve by trading loss | `spawnEligible` treasury check fails; no spawn; slot logs `"insufficient_treasury"`. |
| EDGE-S4: git clone size exceeds 100 MB (repo bloat) | clone exits with `--depth 1` size error; spawn-log marks `status: "failed"`. |
| EDGE-S5: Multiple concurrent spawn attempts from same parent | Rate-cap check in `spawnEligible` sees `status: "initiated"` row and blocks all but the first. |
| EDGE-R1: compute-proxy wallet.json missing on startup | Slot exits non-zero; `kind: "skill_missing"` in ledger; no trade; daemon restarts. |
| EDGE-R2: Two instances accidentally share the same ANICCA_HOME | Wallet guard (REQ-R2) should prevent this; if bypass occurs, concurrent `O_APPEND` writes to ledger.jsonl are still atomic (POSIX, writes < 4096 bytes). |
