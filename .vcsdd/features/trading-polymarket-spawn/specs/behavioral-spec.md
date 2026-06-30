---
feature: trading-polymarket-spawn
phase: 1a
mode: lean
iteration: 1
sources:
  - /Users/operator/anicca-project/docs/superpowers/specs/2026-07-01-trading-polymarket-selffunded-spawn-design.md
  - /Users/operator/anicca/runtime/compute-proxy/proxy.mjs (x402 self-pay via @blockrun/llm + ~/.automaton/wallet.json)
  - /Users/operator/anicca/runtime/compute-proxy/ensure-solana-wallet.mjs (self-owned ed25519 Solana keypair)
  - /Users/operator/anicca/runtime/loop/index.mjs (ReAct loop: context→THINK→parse→execute→persist→sleep)
  - /Users/operator/anicca/runtime/loop/tier.mjs (selectTier: broke/lean/funded by USDC balance)
  - /Users/operator/anicca/runtime/loop/earn-slot.mjs (isEarnSlot / earnStrategyFor / earnSkillRelPath)
  - /Users/operator/anicca/runtime/loop/ledger.mjs (appendLedgerLine, readLedgerLines — append-only)
  - /Users/operator/anicca/runtime/anicca-daemon.sh (self-update + ensure-brain + exec loop)
  - /Users/operator/anicca/install.sh (registry-driven body sync via skills/registry.json)
  - /Users/operator/anicca/.vcsdd/features/earn-shared-skeleton/specs/behavioral-spec.md (inherited: self-heal / Reflexion / bandit / bot2bot / J8 / INV-7 on-chain reward gate / proactive-loop + build_log + menu)
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
| **Pure Core** | `kellyFraction(edge, market_p, bankroll, kelly_max, min_pos, gas_reserve)`, `riskGate(risk_state, position_usdc, current_balance, edge, config)`, `edgePredicate(model_p, market_p)`, `positionSize(kelly_f, bankroll, min_size, gas_reserve)`, `spawnEligible(treasury, net_pos_days, children, config)` (wraps `decideSpawn` from `skills/self/spawn/lib/spawn-decision.js`; `children` = `readChildren(colony_ledger)`), `titheAmount(earned, pct)`, `jurisdictionVenueFilter(jurisdiction, venue, jurisdiction_ok_for_real, kyc_required)` (effectful shell reads both scalar fields from `menu.venues[venue]` and passes as explicit args; returns `true` IFF both `jurisdiction_ok_for_real == true` AND `kyc_required == false`), `selectTier(balanceUsdc, env)` (existing, reused), `isEarnSlot(slot)` (existing, reused) |
| **Effectful Shell** | `pm.py` CLOB REST calls to Polygon Polymarket API, Kalshi REST, Hyperliquid REST, on-chain tx broadcast (seed transfer, tithe), `ensure-solana-wallet.mjs` (key generation + file write), `git clone` + `install.sh` execution, `anicca-daemon.sh` child boot, `appendLedgerLine` (existing), `appendLedgerLine` for spawn log, bot2bot `gh issue create`, Predexon x402 data fetch, alpha-mcp signal fetch, agent-reach news fetch |

## Tracked Quantities

All paths are relative to `$ANICCA_HOME` unless noted. These are canonical inputs to every REQ below.

| Quantity | Path | Semantics |
|----------|------|-----------|
| `risk_state` | `~/loops/earn-pm-trade/risk-state.json` | `{session_start_balance, peak_balance, daily_loss_usdc, drawdown_usdc, open_positions: [{order_id, venue, market_id, side, size_usdc, entry_price, ts}], paper_mode: bool, paper_pass_count: int, last_daily_reset_ts: int}` |
| `paper_log` | `~/loops/earn-pm-trade/paper-log.jsonl` | append-only; one row per paper trade: `{ts, pass_id, market_id, venue, side, size_usdc, model_p, market_p, edge, outcome: "resolved"|"pending", pnl_usdc: null\|float}` |
| `events` | `~/loops/earn-pm-trade/events/<pass_id>.jsonl` | earn-shared-skeleton REQ-G2 event stream; `event:"earn"` rows written ONLY on market resolution with real PnL |
| `build_log` | `~/loops/earn-pm-trade/build_log.md` | narrative memory (Sutando pattern; inherited from skeleton) |
| `menu` | `~/loops/earn-pm-trade/menu.json` | infinite-menu config: `{venues:[{id, jurisdiction_ok_for_real, kyc_required, min_usdc}], strategies:[], ...}` |
| `risk_config` | `~/loops/earn-pm-trade/risk-config.json` | tunable caps: `{kelly_fraction_max, daily_loss_pct: 0.05, drawdown_pct: 0.25, min_position_usdc: 1.50, gas_reserve_usdc, paper_passes_required, spawn_threshold_usdc, spawn_net_pos_days, spawn_rate_cap_days, spawn_seed_usdc, tithe_pct}` |
| `colony_ledger` | `$ANICCA_HOME/state/children.jsonl` | append-only; managed by `skills/self/spawn/lib/ledger.js` (`readChildren`/`appendChild`); one row per spawned child: `{child_id, parent_wallet, child_wallet, child_inbox, status: "provisioning"\|"active"\|"failed", provider_id, spawned_ms, seed_usdc, host, dashboard_id, ...}` |
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
  - **Polymarket (Polygon)**: call `eth_getLogs(chain=Polygon, address=USDC_POLYGON, topics=[ERC20_Transfer_topic0, <settlement_addrs_topic>, checksummed_our_polygon_wallet])` for blocks starting at or after `market_end_ts`, where `settlement_addrs_topic` is a topic[1] filter covering ONLY the Polymarket CTF Exchange and NegRiskAdapter settlement contract addresses (configured in `settle_verify_config.json`; not hardcoded in code). The matching Transfer event MUST satisfy ALL of:
    1. `from` is in the `POLYMARKET_SETTLEMENT_ADDRS` allowlist (CTF Exchange or NegRiskAdapter; any Transfer from a non-allowlist address — including sibling tithes, wallet top-ups, or unrelated market payouts — is REJECTED),
    2. the raw USDC amount (6-decimal) equals `gross_payout_usdc` computed for THIS resolved position (`position_size_usdc × settlement_price`), with tolerance ±1 raw unit for integer rounding only,
    3. the tx containing the Transfer references THIS market's `condition_id` (verified by calling `eth_getTransactionReceipt` and confirming a matching `PositionRedemption` or `PayoutRedemption` log from the CTF contract in the same tx).
  The `tx_hash` from the matching log event is the `receipt_id`. Any Transfer that fails ANY of these three sub-conditions is REJECTED; the earn row is NOT written.
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

WHEN `risk_state.paper_mode == false` AND the model has selected a venue for a real stake, THE SYSTEM SHALL read BOTH `menu.json`'s `venue.jurisdiction_ok_for_real` AND `venue.kyc_required` for the selected venue and pass both as explicit scalar arguments to the pure function `jurisdictionVenueFilter(jurisdiction, venue, jurisdiction_ok_for_real, kyc_required)`. `jurisdictionVenueFilter` returns `True` IFF BOTH conditions hold: `jurisdiction_ok_for_real == true` AND `kyc_required == false`. If either fails, THE SYSTEM SHALL NOT place a real order and SHALL reroute to the next venue in `menu.json` that passes `jurisdictionVenueFilter`. **Kalshi MUST NOT be used for real stakes**: Kalshi is a US-regulated exchange requiring SSN/identity KYC (`kyc_required: true`), which a no-human-in-the-loop instance cannot complete (J8 violation). The only currently-eligible programmatic real-stake fallback for US-jurisdiction instances is Hyperliquid perps (via `hl.py`; `kyc_required: false`, no identity KYC required for EVM wallet perp trading). Polymarket paper trades remain allowed regardless of jurisdiction flag.

**Parent-provisioned venue policy (no-human-in-loop for spawned children)**: `install.sh` provisions ALL venues with `jurisdiction_ok_for_real: false` AND `kyc_required: true` by default. For the PARENT instance, the parent configures its own `menu.json` (human-funded body = human operator). For a SPAWNED CHILD instance, the spawn invocation (REQ-S5) SHALL include a venue policy snapshot (`parent_venue_policy.json`) derived from the parent's `menu.json` entries where both `jurisdiction_ok_for_real: true` AND `kyc_required: false`. The child's `install.sh` bootstrap uses this parent-provided policy as the initial `menu.json`, so the child can reach real-stake venues the parent has confirmed are programmatic-access-only. This is NOT a human-operator action — the parent instance acts as the authoritative venue policy source for its children (no-human-in-loop per REQ-J8).

**Edge Cases:**
- All real-stake venues have `jurisdiction_ok_for_real: false` OR `kyc_required: true`: no real trade placed; slot logs `build_log.md` entry `"all venues jurisdiction-blocked; paper only"`.
- `menu.json` missing `jurisdiction_ok_for_real` key: default to `false` (fail-closed).
- `menu.json` missing `kyc_required` key: default to `true` (fail-closed; KYC assumed required until explicitly cleared to `false`).
- Spawned child with no parent venue policy file: all venues remain at install.sh defaults (all blocked); child runs paper-only until parent policy is applied.

**Acceptance Criteria:**
- With `polymarket.jurisdiction_ok_for_real: false`, no real Polymarket CLOB call is issued.
- With `polymarket.jurisdiction_ok_for_real: true` AND `kyc_required: false`, real CLOB calls are allowed.
- `jurisdictionVenueFilter` called with `kyc_required: true` returns `False` regardless of `jurisdiction_ok_for_real` value (belt-and-suspenders; `kyc_required` is an explicit parameter, not read from a global).
- A spawned child whose parent included `parent_venue_policy.json` with `hyperliquid: {jurisdiction_ok_for_real: true, kyc_required: false}` can reach real Hyperliquid stakes without any human operator action.

### Group S — Spawn Slot (`self/spawn-child`)

**Delegation invariant**: `self/spawn-child` is a **thin wrapper** around the existing, live-E2E-proven `skills/self/spawn/run.sh` (SKILL.md verified 2026-06-16). The spawn skill handles all provisioning mechanics — wallet generation (`scripts/gen-wallet.sh`), AgentMail inbox, provisional colony ledger row, DigitalOcean/Akash droplet provisioning, USDC seed transfer, telemetry registration, final colony ledger row — on an **isolated separate droplet** where the child's `clawrouter` binds its own `:8402` with no port collision with the parent. The wrapper's sole additions are: (a) the trading-treasury additional gate (`net_pos_days`), (b) passing `spawn_seed_usdc` and `parent_venue_policy.json` to `run.sh`, and (c) extracting children from `$ANICCA_HOME/state/children.jsonl` (via `lib/ledger.js readChildren`) for the eligibility check. `spawn-log.jsonl` is NOT used; `$ANICCA_HOME/state/children.jsonl` is the sole colony ledger.

#### REQ-S1 — Spawn Eligibility Check (pure)

WHEN the slot `self/spawn-child` is invoked by the ReAct loop, THE SYSTEM SHALL first evaluate the pure function `spawnEligible(treasury, net_pos_days, children, config)` where:
- `treasury` = `current_balance − risk_config.gas_reserve_usdc − risk_config.spawn_seed_usdc` (= surplus available after retaining gas + one seed)
- `net_pos_days` = count of calendar days in `cumulative.json` history where `usdc_earned_that_day > token_cost_that_day`
- `children` = array from `readChildren($ANICCA_HOME/state/children.jsonl)` via `skills/self/spawn/lib/ledger.js` (empty array if file absent)
- `config` = `risk_config.{spawn_threshold_usdc, spawn_net_pos_days, spawn_rate_cap_days, spawn_seed_usdc, spawn_hard_cap}`

`spawnEligible` returns `{eligible: bool, reason: string}` and is `true` IFF ALL of:
1. `treasury ≥ config.spawn_threshold_usdc` (= parent has surplus above gas + seed)
2. `net_pos_days ≥ config.spawn_net_pos_days` (= trading-specific profitability gate, checked BEFORE decideSpawn)
3. `decideSpawn({balanceUsdc: treasury, children, rateLimitDays: config.spawn_rate_cap_days, maxChildren: config.spawn_hard_cap, minBalanceUsdc: config.spawn_threshold_usdc})` returns `{eligible: true}` — per `skills/self/spawn/lib/spawn-decision.js`; this subsumes the balance check (condition 1 above, re-verified by decideSpawn), rate-limit check (no child with `spawned_ms` within last `spawn_rate_cap_days` days), and concurrency cap (`children.length < spawn_hard_cap`)
4. `config.spawn_seed_usdc ≥ 1.50` (minimum viable child seed; less than this leaves the child with no trading capacity)

**Edge Cases:**
- `children.jsonl` file missing (first spawn): `readChildren` returns `[]`; all rate-cap and concurrency-cap checks pass.
- `treasury < 0` (wallet below gas reserve): `eligible: false, reason: "insufficient_treasury"`.
- A child row with `status: "provisioning"` (crash mid-spawn): it has a `spawned_ms` timestamp → rate cap fires → spawn blocked until row ages out.

**Acceptance Criteria:**
- `spawnEligible` is a pure function; no I/O.
- All four conditions independently tested with boundary values.

#### REQ-S2 — Spawn Invocation (thin wrapper around `skills/self/spawn/run.sh`)

WHEN `spawnEligible` returns `{eligible: true}`, THE SYSTEM SHALL invoke the existing spawn skill:

```
ANICCA_SEED_USDC=$config.spawn_seed_usdc \
ANICCA_SPAWN_HOST=${ANICCA_SPAWN_HOST:-do} \
ANICCA_VENUE_POLICY_PATH=$parent_venue_policy_path \
bash $ANICCA_REPO/skills/self/spawn/run.sh
```

where `parent_venue_policy_path` points to a JSON file derived from the parent's `menu.json` containing only entries where BOTH `jurisdiction_ok_for_real: true` AND `kyc_required: false` (see REQ-T10 parent-provisioned venue policy). The spawn skill (`run.sh`) handles ALL provisioning mechanics in the following order (per its verified E2E flow):
1. `scripts/gen-wallet.sh` → child secp256k1 wallet at `$STATE_DIR/.tmp-childwallet-*.json` (600-perm, distinct from parent; collision aborts)
2. AgentMail inbox provisioned via `POST /v0/inboxes` (child's own sovereign identity)
3. Provisional row appended to `$ANICCA_HOME/state/children.jsonl` via `lib/ledger.js appendChild` (never lose track)
4. DigitalOcean droplet (or Akash lease) provisioned with cloud-init that boots `clawrouter` + `automaton` as restart-always systemd units on the child's own `:8402` — **on a separate host, there is NO port collision with the parent's `:8402`**. `HOME=$CHILD_HOME` is set in the child's systemd unit environment; all child wallet reads in `proxy.mjs`, `execute-yield.mjs`, `hl.py`, and `anicca-daemon.sh` resolve to the child's OWN `$CHILD_HOME/.automaton/wallet.json`
5. USDC seed transfer (`$config.spawn_seed_usdc`) from parent wallet to child wallet on Base
6. Telemetry registration: child signs its own EIP-191 heartbeat and POSTs to `${TELEMETRY_URL}` (202 = child appears on dashboard; non-202 aborts)
7. Final `children.jsonl` row updated to `{status: "active", provider_id, wake_action: "earn", earn_on_wake: true, dashboard_id}` via `lib/ledger.js`

**NOTE: NO `CHILD_PORT`, NO `COMPUTE_PROXY_PORT` port-split**: the parent does NOT scan for free ports. The child's `clawrouter` binds `:8402` on its OWN droplet — `anicca-daemon.sh` launches it with `BLOCKRUN_WALLET_KEY=$KEY clawrouter` (no port argument; the comment at `anicca-daemon.sh:50` confirms "`:8402-only (no port split)`"). Port isolation is achieved by physical host separation, not by port numbering.

**Edge Cases:**
- `run.sh` exits non-zero (wallet collision, AgentMail failure, DO provision failure, seed transfer failure, telemetry non-202): spawn attempt is a hard failure; `children.jsonl` row left at `status: "provisioning"` or `"failed"` (the provisional append in step 3 is idempotent — the failure row serves as a rate-cap anchor); `build_log.md` records the error.
- `DIGITALOCEAN_TOKEN` absent: spawn fails cleanly; `children.jsonl` row at `"failed"`.
- `AGENTMAIL_API_KEY` absent: same failure path.

**Acceptance Criteria:**
- `children.jsonl` has a row with `status: "active"` containing `child_wallet` (≠ parent), `provider_id`, `dashboard_id` after successful spawn.
- Child droplet's systemd unit confirms `AUTOMATON_GOAL=earn` (child earns on own wake).
- `run.sh` exits 0 IFF all 7 steps complete; any failure → exit 1 + honest ledger row.

#### REQ-S3 — Framework + Slot Installation (delegated to spawn skill cloud-init)

The framework clone, `install.sh`, and Python dependency installation for `earn/pm-trade` are handled by `skills/self/spawn/scripts/cloud-init.sh` inside the child's droplet at first boot (step 4 of REQ-S2). The cloud-init script runs `git clone --depth 1 https://github.com/Daisuke134/anicca.git` and `bash install.sh` (registry-driven, idempotent; per NFR-1, `skills/earn/pm-trade/requirements.txt` is installed). If the parent provided `ANICCA_VENUE_POLICY_PATH` in REQ-S2, the cloud-init writes the policy file to `$CHILD_HOME/loops/earn-pm-trade/menu.json` BEFORE `install.sh` runs, so the child's initial menu reflects the parent-approved venue policy.

The `self/spawn-child` wrapper does NOT separately run `git clone` or `install.sh` on the parent host; it delegates entirely to the spawn skill's droplet provisioning.

**Edge Cases:**
- No internet on child droplet: cloud-init clone fails; automaton service fails to start; parent's telemetry registration step (step 6 of REQ-S2) fails → `children.jsonl` row stays at `"provisioning"` or `"failed"`.
- `install.sh` fails on missing dep on the child droplet: same outcome via step 6/7 failure.

**Acceptance Criteria:**
- After REQ-S2 completes (run.sh exits 0), the child's cloud-init has been sent to the droplet and `automaton.service` is expected to start with `AUTOMATON_GOAL=earn`.
- The `earn/pm-trade` slot is registered in the child's `skills/registry.json` after cloud-init completes.

#### REQ-S4 — Seed Transfer (on-chain; delegated to spawn skill)

The USDC seed transfer (`config.spawn_seed_usdc` from parent wallet to child wallet on Base) is performed as step 5 in `skills/self/spawn/run.sh`. The spawn skill waits for confirmation and records `seed_usdc` in the `children.jsonl` row. The `self/spawn-child` wrapper passes `ANICCA_SEED_USDC=$config.spawn_seed_usdc` to `run.sh` (step 5 uses `$SEED_USDC`). The parent's `~/.automaton/wallet.json` private key is read by the spawn skill's EIP-20 transfer step.

THE SYSTEM SHALL NOT proceed to child boot (REQ-S2 step 4) if the seed transfer has not confirmed; `run.sh` enforces this sequentially (seed transfer is step 5, droplet boot is step 4 — if step 5 fails, `run.sh` exits non-zero and the `children.jsonl` row remains at `"provisioning"`).

**Edge Cases:**
- Transfer tx fails (insufficient parent balance after gas): `run.sh` exits non-zero; `children.jsonl` row at `"failed"`; parent balance is unaffected.
- Parent wallet private key read fails: `run.sh` exits 1 immediately; no transfer.

**Acceptance Criteria:**
- `children.jsonl` row includes `seed_usdc: $config.spawn_seed_usdc` after successful spawn.
- Child base wallet balance ≥ `spawn_seed_usdc` (verified via RPC after `run.sh` exits 0).

#### REQ-S5 — Child Provisioning and Isolation (separate droplet; delegated to spawn skill)

REQ-S2's `run.sh` invocation handles all child boot mechanics. This REQ documents the isolation invariants the spawn skill enforces.

**Isolation model (SEPARATE DROPLET — not same-host port-split)**:
- The child runs on its own DigitalOcean droplet (or Akash lease). `anicca-daemon.sh` on the child droplet launches `clawrouter` with `BLOCKRUN_WALLET_KEY=$KEY clawrouter` and no port argument (`anicca-daemon.sh:50-55` confirms `:8402-only`). On a dedicated droplet, `:8402` is free — there is NO port collision with the parent.
- `HOME=$CHILD_HOME` is set in the child droplet's `automaton.service` systemd unit (written by `scripts/cloud-init.sh`). All wallet-consuming modules in the child process tree (`proxy.mjs`, `execute-yield.mjs`, `hl.py`, `anicca-daemon.sh`'s key derivation) resolve the private key from `$HOME/.automaton/wallet.json`, which on the child droplet = the child's own wallet. The parent's wallet is unreachable from the child's host.
- `COMPUTE_PROXY_PORT` is NOT set; it is NOT used by `clawrouter` (confirmed by `anicca-daemon.sh:50-55`). Port isolation is achieved by physical host separation, not by port numbering. Any prior spec wording about `CHILD_PORT` or `COMPUTE_PROXY_PORT` for ClawRouter is superseded by this requirement.

**Venue policy provisioning (no-human-in-loop)**:
- The spawn invocation (REQ-S2) derives `parent_venue_policy.json` from the parent's `menu.json`: entries where BOTH `jurisdiction_ok_for_real: true` AND `kyc_required: false`. This file is passed to the cloud-init as `ANICCA_VENUE_POLICY_PATH` and written to the child's `$CHILD_HOME/loops/earn-pm-trade/menu.json` at bootstrap. The child can real-stake on venues the parent has confirmed require no identity KYC, without any human operator action.

**Edge Cases:**
- DO/Akash provisioning fails: `run.sh` exits 1; `children.jsonl` row at `"failed"` or `"provisioning"`.
- `parent_venue_policy.json` is empty (parent has no real-stake-eligible venues): child bootstraps with all venues blocked; child runs paper-only.
- Droplet boots but automaton fails to start: `children.jsonl` row remains at `"provisioning"` (telemetry POST was 202 but automaton health check fails); parent observes and can investigate.

**Acceptance Criteria:**
- `children.jsonl` row at `status: "active"` with valid `provider_id` after successful REQ-S2.
- Child droplet's `automaton.service` environment includes `HOME=$CHILD_HOME` (verifiable via `systemctl show automaton`).
- No `CHILD_PORT` or `COMPUTE_PROXY_PORT` env var is set or expected anywhere in the spawn flow.

#### REQ-S6 — Bot2bot Registration

WHEN the spawn skill confirms the child is active (`children.jsonl` row at `status: "active"` with `provider_id` and `dashboard_id`), THE SYSTEM SHALL additionally invoke `bot2bot.sh` (inherited from skeleton) to create a `gh issue` on the framework repo with label `bot2bot-registry` and body `{event: "child-spawned", parent_wallet: <parent_base>, child_wallet: <child_wallet>, child_inbox: <child_inbox>, provider_id: <provider_id>, seed_usdc: <seed_usdc>, ts: <ts>}`.

Note: the spawn skill (run.sh step 6) already registers the child on the aniccaai.com dashboard via signed telemetry. The `bot2bot.sh` gh issue is the cross-colony discovery layer on top of dashboard registration.

Sibling and parent instances poll `gh issue list --label bot2bot-registry` to discover new colony members. The child's own loop will read this issue on its first cross-learn pass (inherited REQ-D1).

**Edge Cases:**
- `gh` rate-limited: 3 retries with exp backoff per REQ-D3; failure logged; child is already running (dashboard-registered); bot2bot registration deferred to next pass.
- `gh` permanently unavailable: child is running; bot2bot deferred.

**Acceptance Criteria:**
- A `gh issue` with label `bot2bot-registry` exists after REQ-S6 (or retries exhausted with warning).
- `children.jsonl` row at `status: "active"` is the source of truth for spawn completion (not bot2bot gh issue).

#### REQ-S7 — Spawn Guards (NO HUMAN, inherited J8)

THE SYSTEM SHALL enforce these guards at each step:

1. **Net-positive guard**: `spawnEligible` (REQ-S1) requires `net_pos_days ≥ config.spawn_net_pos_days` (default 3). A parent with 0 realized profit days SHALL NOT spawn.
2. **Rate cap**: At most one spawn per `spawn_rate_cap_days` (default 14) per parent.
3. **Hard cap**: at most `spawn_hard_cap` (default 5) total registered children from one parent (counted from `children.jsonl` rows with `status: "active"` via `readChildren`).
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
- Parent wallet address unknown to child: child reads `PARENT_WALLET_ADDRESS` from `$CHILD_HOME/.env` (written by the spawn skill's cloud-init, sourced from the `children.jsonl` row).
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
| NFR-3 | `self/spawn-child` SHALL be idempotent: if a `children.jsonl` row with `status: "provisioning"` exists for a child provisioned within the rate-cap window, a re-invocation detects it via `spawnEligible` rate-cap check and waits for the existing row to age out or be resolved; it does NOT spawn a second child on top of a pending one. |
| NFR-4 | All file mutations in REQ-S (wallet, env, colony-ledger) SHALL use tmp-file + atomic rename or `O_APPEND` for crash-safety. `skills/self/spawn/scripts/gen-wallet.sh` writes to a 600-perm temp file under `$STATE_DIR` and cleans it up on exit. `lib/ledger.js appendChild` uses `appendFileSync` (O_APPEND). |
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
| EDGE-S1: Spawn initiated but seed tx hash never confirmed after 5 min | `run.sh` exits 1; `children.jsonl` row left at `"provisioning"`; serves as rate-cap anchor; retry next pass after rate-cap window. |
| EDGE-S2: Child boot succeeds but child never completes an earn pass | Parent observes bot2bot-registry issue; child is alive; no parent action required. |
| EDGE-S3: Parent wallet drained below gas reserve by trading loss | `spawnEligible` treasury check fails; no spawn; slot logs `"insufficient_treasury"`. |
| EDGE-S4: git clone size exceeds 100 MB (repo bloat) | cloud-init clone exits with `--depth 1` size error; droplet fails to start automaton; telemetry POST fails; `children.jsonl` row at `"provisioning"` (never reaches `"active"`). |
| EDGE-S5: Multiple concurrent spawn attempts from same parent | Rate-cap check in `spawnEligible` sees a recent `spawned_ms` in `children.jsonl` and blocks all but the first (via `decideSpawn` rate-limit check). |
| EDGE-R1: compute-proxy wallet.json missing on startup | Slot exits non-zero; `kind: "skill_missing"` in ledger; no trade; daemon restarts. |
| EDGE-R2: Two instances accidentally share the same ANICCA_HOME | Wallet guard (REQ-R2) should prevent this; if bypass occurs, concurrent `O_APPEND` writes to ledger.jsonl are still atomic (POSIX, writes < 4096 bytes). |
