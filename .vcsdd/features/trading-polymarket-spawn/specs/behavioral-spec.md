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

# Behavioral Specification — trading-polymarket-spawn (v1, trading-only after scope split)

## Purpose

Add the **`earn/pm-trade`** trading earn slot to the live `~/anicca` runtime that was already proven at `anicca-a3cdd4 / $15.34 net worth`. This feature covers **trading only**; spawn is deferred to a separate feature `spawn-child-earn`.

1. **`earn/pm-trade`** — Polymarket CLOB prediction-market trading (and Kalshi / Hyperliquid / DEX perps as venue alternatives). The MODEL decides edge from data tools; no hardcoded strategy or regex. Paper mode mandatory before any real stake.

The slot runs INSIDE the existing `~/anicca` runtime (`install.sh` → `registry.json` → `earn-slot.mjs` → `index.mjs` ReAct loop → `anicca-daemon.sh`). It inherits the full `earn-shared-skeleton` library (healthcheck, ROI tracking, bandit-arm self-improve, bot2bot cross-learn, nightly adversary, Group J8 anti-human-touch invariant).

**Spawn deferred**: `self/spawn-child` (Group S, REQ-S1..S9) is deferred to feature `spawn-child-earn`. The existing `skills/self/spawn/run.sh` must first be extended with (a) a real on-chain seed-transfer step (currently a manual-print at `run.sh:196`) and (b) `ANICCA_VENUE_POLICY_PATH` consumption + child `menu.json` bootstrap via cloud-init (currently zero grep hits in `skills/self/spawn/`). All deferred requirements and findings (FIND-014, FIND-016, FIND-019, FIND-020, FIND-021) are preserved verbatim in `out-of-scope.jsonl`.

## Purity Boundary

| Layer | Functions / Modules |
|-------|---------------------|
| **Pure Core** | `kellyFraction(edge, market_p, bankroll, kelly_max, min_pos, gas_reserve)`, `riskGate(risk_state, position_usdc, current_balance, edge, config)`, `edgePredicate(model_p, market_p)`, `positionSize(kelly_f, bankroll, min_size, gas_reserve)`, `jurisdictionVenueFilter(jurisdiction_ok_for_real, kyc_required)` (effectful shell reads `menu.venues[venue].jurisdiction_ok_for_real` and `menu.venues[venue].kyc_required` then passes both as explicit scalar args; returns `true` IFF `jurisdiction_ok_for_real == true` AND `kyc_required == false`), `selectTier(balanceUsdc, env)` (existing, reused), `isEarnSlot(slot)` (existing, reused) |
| **Effectful Shell** | `pm.py` CLOB REST calls to Polygon Polymarket API, Kalshi REST, Hyperliquid REST, on-chain tx broadcast (earn-settle), `ensure-solana-wallet.mjs` (key generation + file write), `appendLedgerLine` (existing), bot2bot `gh issue create` (trade dedup), Predexon x402 data fetch, alpha-mcp signal fetch, agent-reach news fetch |

## Tracked Quantities

All paths are relative to `$ANICCA_HOME` unless noted. These are canonical inputs to every REQ below.

| Quantity | Path | Semantics |
|----------|------|-----------|
| `risk_state` | `~/loops/earn-pm-trade/risk-state.json` | `{session_start_balance, peak_balance, daily_loss_usdc, drawdown_usdc, open_positions: [{order_id, venue, market_id, side, size_usdc, entry_price, filled_size, ts}], paper_mode: bool, paper_pass_count: int, last_daily_reset_ts: int}` — `entry_price` = CLOB mid price at fill time (USDC per outcome share, e.g. 0.65 for a YES at 65¢); `filled_size` = USDC actually spent at fill (may be less than `size_usdc` for partial fills); `shares_held` = `filled_size / entry_price` (computed, not stored — the number of CTF outcome tokens held; for a Polymarket binary winning redemption, `gross_payout_usdc = shares_held × $1.00`) |
| `paper_log` | `~/loops/earn-pm-trade/paper-log.jsonl` | append-only; one row per paper trade: `{ts, pass_id, market_id, venue, side, size_usdc, model_p, market_p, edge, outcome: "resolved"|"pending", pnl_usdc: null\|float}` |
| `events` | `~/loops/earn-pm-trade/events/<pass_id>.jsonl` | earn-shared-skeleton REQ-G2 event stream; `event:"earn"` rows written ONLY on market resolution with real PnL |
| `build_log` | `~/loops/earn-pm-trade/build_log.md` | narrative memory (Sutando pattern; inherited from skeleton) |
| `menu` | `~/loops/earn-pm-trade/menu.json` | infinite-menu config: `{venues:[{id, jurisdiction_ok_for_real, kyc_required, min_usdc}], strategies:[], ...}` |
| `risk_config` | `~/loops/earn-pm-trade/risk-config.json` | tunable caps: `{kelly_fraction_max, daily_loss_pct: 0.05, drawdown_pct: 0.25, min_position_usdc: 1.50, gas_reserve_usdc, paper_passes_required}` |
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
    2. the raw USDC amount (6-decimal) equals `gross_payout_usdc` computed for THIS resolved position: for a Polymarket CTF binary YES/NO winning outcome, `gross_payout_usdc = shares_held × $1.00` where `shares_held = filled_size / entry_price` (both fields from the `risk_state.open_positions` row; see Tracked Quantities). Tolerance ±1 raw unit (6-decimal USDC) for integer rounding only. For a losing outcome, `gross_payout_usdc = 0` and no Transfer event is expected (no earn row written). (`settlement_price` is NOT a valid formula term — Polymarket CTF binary redemption pays $1.00 per winning share, not `size × settlement_price`.)
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

WHEN `risk_state.paper_mode == false` AND the model has selected a venue for a real stake, THE SYSTEM SHALL read BOTH `menu.json`'s `venue.jurisdiction_ok_for_real` AND `venue.kyc_required` for the selected venue and pass both as explicit scalar arguments to the pure function `jurisdictionVenueFilter(jurisdiction_ok_for_real, kyc_required)`. `jurisdictionVenueFilter` returns `True` IFF BOTH conditions hold: `jurisdiction_ok_for_real == true` AND `kyc_required == false`. If either fails, THE SYSTEM SHALL NOT place a real order and SHALL reroute to the next venue in `menu.json` that passes `jurisdictionVenueFilter`. **Kalshi MUST NOT be used for real stakes**: Kalshi is a US-regulated exchange requiring SSN/identity KYC (`kyc_required: true`), which a no-human-in-the-loop instance cannot complete (J8 violation). The only currently-eligible programmatic real-stake fallback for US-jurisdiction instances is Hyperliquid perps (via `hl.py`; `kyc_required: false`, no identity KYC required for EVM wallet perp trading). Polymarket paper trades remain allowed regardless of jurisdiction flag.

`install.sh` provisions ALL venues with `jurisdiction_ok_for_real: false` AND `kyc_required: true` by default. The operator configures the instance's own `menu.json` to enable real-stake venues. Parent-to-child venue policy propagation is deferred to feature `spawn-child-earn`.

**Edge Cases:**
- All real-stake venues have `jurisdiction_ok_for_real: false` OR `kyc_required: true`: no real trade placed; slot logs `build_log.md` entry `"all venues jurisdiction-blocked; paper only"`.
- `menu.json` missing `jurisdiction_ok_for_real` key: default to `false` (fail-closed).
- `menu.json` missing `kyc_required` key: default to `true` (fail-closed; KYC assumed required until explicitly cleared to `false`).

**Acceptance Criteria:**
- With `polymarket.jurisdiction_ok_for_real: false`, no real Polymarket CLOB call is issued.
- With `polymarket.jurisdiction_ok_for_real: true` AND `kyc_required: false`, real CLOB calls are allowed.
- `jurisdictionVenueFilter(kyc_required=True, ...)` returns `False` regardless of `jurisdiction_ok_for_real` value (belt-and-suspenders; `kyc_required` is an explicit parameter, not read from a global).

### Group S — Spawn Slot (`self/spawn-child`) — DEFERRED

**DEFERRED to feature `spawn-child-earn`.** All REQ-S1..S9 text is preserved verbatim in `out-of-scope.jsonl`. See that file for the full requirements, proof obligations, integration tests, and linked findings (FIND-014, FIND-016, FIND-019, FIND-020, FIND-021). Prerequisites that must be built in `skills/self/spawn/run.sh` before this feature can be accurately specified: (a) real on-chain seed-transfer step, (b) `ANICCA_VENUE_POLICY_PATH` consumption and child `menu.json` bootstrap via `cloud-init.sh`.


### Group R — Runtime Integration Invariants

#### REQ-R1 — Compute Self-Pay for Trading Decisions

THE SYSTEM SHALL route all LLM inference during the `earn/pm-trade` slot's THINK step through the existing compute-proxy at `$OPENAI_BASE_URL` (default `http://127.0.0.1:8402/v1`). Every inference is paid in USDC via x402 from the instance's own wallet. All wallet-consuming modules in the runtime (`proxy.mjs`, `execute-yield.mjs`, `hl.py`, `anicca-daemon.sh`'s `ensure_brain`) resolve the wallet from `process.env.HOME + "/.automaton/wallet.json"` (or Python's `os.path.expanduser("~/.automaton/wallet.json")`). `$HOME` is the system home directory of the running instance. No human key is used.

**Acceptance Criteria:**
- With the compute-proxy running and wallet funded, a full `earn/pm-trade` pass produces a `[proxy]` log entry with a USDC x402 settlement.
- With the compute-proxy down, the pass fails with exit code non-zero; ledger records `kind: "skill_error"`.

#### REQ-R2 — Wallet Collision Guard (one wallet per instance)

WHEN the `earn/pm-trade` slot boots, THE SYSTEM SHALL verify that `$HOME/.automaton/wallet.json` belongs exclusively to this instance. `ensure-solana-wallet.mjs` writes ONLY the Solana ed25519 keypair to `solana.json` and does NOT create `wallet.json`. THE SYSTEM SHALL fail-closed: if `wallet.json` is missing or unreadable at boot, the slot exits non-zero without placing any trade.

**Acceptance Criteria:**
- Two Anicca instances on the same host with different `$HOME` values resolve `wallet.json` to different paths (`$HOME/.automaton/wallet.json`) and hold different wallet addresses.

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
| NFR-1 | `pm.py` (Polymarket + Kalshi adapter) and `settle-verify.py` SHALL run under Python 3.11+ with no dependencies beyond `requests`, `eth-account`, and the Polymarket/Kalshi SDK (or raw REST). A `skills/earn/pm-trade/requirements.txt` file SHALL enumerate all Python deps for the slot; `install.sh` installs from this file. |
| NFR-2 | A full `earn/pm-trade` pass (data acquisition → edge → risk gate → paper trade) SHALL complete within 120s (matching `SKILL_TIMEOUT_S` default). |
| NFR-3 | All file mutations (wallet, ledger files) SHALL use tmp-file + atomic rename or `O_APPEND` for crash-safety. `risk_state.json` transitions use tmp-file + atomic rename. `appendLedgerLine` and `events/*.jsonl` use `appendFileSync` (O_APPEND). |
| NFR-4 | No secret (private key, mnemonic) SHALL be logged to `build_log.md`, `ledger.jsonl`, or any append-only log. Redaction via `redactPrivateKeyPatterns` (existing `env-filter.mjs`) is MANDATORY before any string from skill output enters the ledger. |
| NFR-5 | All scripts SHALL pass `shellcheck --severity=warning` with zero warnings. |

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
| EDGE-R1: compute-proxy wallet.json missing on startup | Slot exits non-zero; `kind: "skill_missing"` in ledger; no trade; daemon restarts. |
| EDGE-R2: Two instances accidentally share the same ANICCA_HOME | Wallet guard (REQ-R2) should prevent this; if bypass occurs, concurrent `O_APPEND` writes to ledger.jsonl are still atomic (POSIX, writes < 4096 bytes). |
