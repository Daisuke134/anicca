---
feature: trading-polymarket-spawn
phase: 1b
mode: lean
iteration: 1
inherits: earn-shared-skeleton (PROP-A1..A9, PROP-B1..B6, PROP-C1..C3, PROP-D1..D3, PROP-E1..E5, PROP-F1..F2, PROP-G1..G3, PROP-H1, PROP-J8)
---

# Verification Architecture — trading-polymarket-spawn (v1)

## Purity Boundary Map

### Pure Core (deterministic, no side effects, formally verifiable)

| Function | Module | Inputs | Output |
|----------|--------|--------|--------|
| `kellyFraction(edge, market_p, bankroll, kelly_max, min_pos, gas_reserve)` | `skills/earn/pm-trade/risk.py` | 6 floats | `float` position size or 0 |
| `riskGate(risk_state, position_usdc, config)` | `skills/earn/pm-trade/risk.py` | typed records | `{decision: ALLOW\|HALT, reason: str}` |
| `edgePredicate(model_p, market_p)` | `skills/earn/pm-trade/risk.py` | 2 floats | `bool` |
| `positionSize(kelly_f, bankroll, min_size, gas_reserve)` | `skills/earn/pm-trade/risk.py` | 4 floats | `float` |
| `spawnEligible(treasury, net_pos_days, recent_spawns, config)` | `skills/self/spawn-child/spawn.py` | typed records | `{eligible: bool, reason: str}` |
| `titheAmount(realized_pnl, tithe_pct, min_tithe)` | `skills/self/spawn-child/spawn.py` | 3 floats | `float` |
| `jurisdictionVenueFilter(jurisdiction, venue, menu)` | `skills/earn/pm-trade/risk.py` | str, str, dict | `bool` (True = allowed) |
| `selectTier(balanceUsdc, env)` | `runtime/loop/tier.mjs` | float, dict | `{tier, model}` (existing) |
| `isEarnSlot(slot)` | `runtime/loop/earn-slot.mjs` | str | `bool` (existing) |
| `earnSkillRelPath(slot)` | `runtime/loop/earn-slot.mjs` | str | `str` (existing) |

### Effectful Shell (I/O bound; tested via integration/E2E)

| Component | Side Effects |
|-----------|-------------|
| `pm.py` | REST calls to Polymarket/Kalshi/Hyperliquid CLOB; writes to `risk_state.json`, `events/` |
| `ensure-solana-wallet.mjs` | ed25519 keygen + file write to `$ANICCA_HOME/.automaton/solana.json` |
| EVM key gen + Base tx broadcast | entropy read; `wallet.json` write; on-chain USDC transfer |
| `git clone` + `install.sh` | disk writes to `$CHILD_HOME` |
| `anicca-daemon.sh` child boot | process spawn (tmux); log file writes |
| `appendLedgerLine` | O_APPEND write to `ledger.jsonl` (existing) |
| `spawn-log.jsonl` append | O_APPEND write |
| `bot2bot.sh` gh issue create | gh API call |
| Predexon x402 fetch | outbound HTTP; x402 USDC settlement |

## Proof Obligations

| ID | Description | REQ | Tier | Required | Tool |
|----|-------------|-----|------|----------|------|
| PROP-T1 | `kellyFraction(e, m, B, kmax, min, gas)`: output ∈ [min, B − gas] for any valid edge e ∈ (0,1), market_p m ∈ (0,1), bankroll B > min + gas | REQ-T5 | 1 | true | pytest property + hypothesis |
| PROP-T2 | `kellyFraction(0, m, B, ...)` = 0 for all m, B | REQ-T5 | 1 | true | pytest |
| PROP-T3 | `kellyFraction(e, 1.0, B, ...)` = 0 (denominator guard: 1−market_p = 0) | REQ-T5 | 1 | true | pytest |
| PROP-T4 | `kellyFraction(e, m, 0, ...)` = 0 (zero bankroll → zero position) | REQ-T5 | 1 | true | pytest |
| PROP-T5 | `riskGate`: daily_loss ≥ 0.05 × start_balance → HALT("daily_loss_cap_reached") for any position_usdc | REQ-T4 | 1 | true | pytest |
| PROP-T6 | `riskGate`: daily_loss < threshold AND drawdown ≥ 0.25 × peak → HALT("drawdown_cap_reached") | REQ-T4 | 1 | true | pytest |
| PROP-T7 | `riskGate`: position_usdc < min_position_usdc → HALT("below_min_position") | REQ-T4 | 1 | true | pytest |
| PROP-T8 | `riskGate`: current_balance − position_usdc < gas_reserve → HALT("insufficient_gas_reserve") | REQ-T4 | 1 | true | pytest |
| PROP-T9 | `riskGate`: edge ≤ 0 → HALT("no_edge") regardless of other fields | REQ-T4 | 1 | true | pytest |
| PROP-T10 | `riskGate`: all conditions clear → ALLOW("risk_gate_passed") | REQ-T4 | 1 | true | pytest |
| PROP-T11 | `riskGate` is pure: same inputs → identical output (no hidden state) | REQ-T4 | 2 | true | hypothesis stateless test |
| PROP-T12 | `riskGate` boundary: daily_loss exactly = threshold → HALT (≥ is inclusive, not >) | REQ-T4 | 1 | true | pytest |
| PROP-T13 | `riskGate` boundary: drawdown exactly = threshold → HALT | REQ-T4 | 1 | true | pytest |
| PROP-T14 | `jurisdictionVenueFilter("US", "polymarket", menu)` = False when `menu.venues.polymarket.jurisdiction_ok_for_real = false` | REQ-T10 | 1 | true | pytest |
| PROP-T15 | `jurisdictionVenueFilter("US", "polymarket", menu)` fails-closed when key absent from menu (→ False) | REQ-T10 | 1 | true | pytest |
| PROP-T16 | `jurisdictionVenueFilter("SG", "polymarket", menu)` = True when `menu.venues.polymarket.jurisdiction_ok_for_real = true` | REQ-T10 | 1 | true | pytest |
| PROP-T17 | `edgePredicate(model_p, market_p)` = True IFF `model_p > market_p` (strict inequality) | REQ-T3 | 1 | true | pytest |
| PROP-T18 | Paper mode: no CLOB endpoint called while `risk_state.paper_mode = true` (confirmed by call-spy) | REQ-T6 | 2 | true | integration + spy |
| PROP-T19 | Paper-to-real transition requires both paper_pass_count ≥ required AND adversary PASS file present | REQ-T6 | 2 | true | integration (state machine) |
| PROP-T20 | Paper-to-real transition fails-closed when adversary PASS file absent (even if paper_pass_count ≥ required) | REQ-T6 | 1 | true | pytest (file absent → paper stays) |
| PROP-T21 | Earn row written ONLY on market resolution, never on order placement | REQ-T8 | 2 | true | integration (spy on events file) |
| PROP-T22 | `cumulative.json.cumulative_usdc_earned` is the sum of all earn rows including negative PnL | REQ-T8 | 1 | true | pytest (negative-PnL scenario) |
| PROP-T23 | Risk state `daily_loss_usdc` is incremented by the absolute value of each negative PnL | REQ-T8 | 1 | true | pytest |
| PROP-T24 | `isEarnSlot("earn/pm-trade")` = true (earn-slot.mjs existing pure predicate) | REQ-T1 | 1 | true | node unit test |
| PROP-T25 | `earnSkillRelPath("earn/pm-trade")` = `"earn/pm-trade/run.sh"` | REQ-T1 | 1 | true | node unit test |
| PROP-S1 | `spawnEligible`: treasury < threshold → {eligible: false, reason: "insufficient_treasury"} | REQ-S1 | 1 | true | pytest |
| PROP-S2 | `spawnEligible`: net_pos_days < config.spawn_net_pos_days → {eligible: false, reason: "not_enough_net_positive_days"} | REQ-S1 | 1 | true | pytest |
| PROP-S3 | `spawnEligible`: spawn within rate_cap_days exists in log → {eligible: false, reason: "rate_cap"} | REQ-S1 | 1 | true | pytest |
| PROP-S4 | `spawnEligible`: all 4 conditions satisfied → {eligible: true} | REQ-S1 | 1 | true | pytest |
| PROP-S5 | `spawnEligible` is pure (no I/O; same inputs → same output) | REQ-S1 | 2 | true | hypothesis |
| PROP-S6 | `spawnEligible` treasury boundary: treasury exactly = threshold → eligible: true (≥ is inclusive) | REQ-S1 | 1 | true | pytest |
| PROP-S7 | `spawnEligible`: spawn_seed_usdc < 1.50 in config → {eligible: false, reason: "seed_below_minimum"} | REQ-S1 | 1 | true | pytest |
| PROP-S8 | `titheAmount(pnl, pct, min)`: result = 0 when `pnl × pct < min` | REQ-S8 | 1 | true | pytest |
| PROP-S9 | `titheAmount`: result ≤ pnl for all inputs | REQ-S8 | 1 | true | pytest |
| PROP-S10 | Child wallet address ≠ parent wallet address (collision guard) | REQ-S2 | 2 | true | integration |
| PROP-S11 | Seed transfer requires confirmed tx_hash before child boot proceeds | REQ-S4 | 2 | true | integration (stub RPC, assert boot blocked when tx unconfirmed) |
| PROP-S12 | spawn-log.jsonl never truncated; only appended | REQ-S4 | 1 | true | pytest (open mode check) |
| PROP-S13 | Multiple concurrent spawn attempts: only first proceeds (rate-cap sees "initiated" status) | REQ-S7 | 2 | true | integration (concurrent calls) |
| PROP-R1 | `registry.json` declares `earn/pm-trade` with `status: "live"` after install | REQ-T1 | 2 | true | integration (run install.sh in tmpdir) |
| PROP-R2 | Two instances with different ANICCA_HOME never share wallet.json path | REQ-R2 | 2 | true | integration |
| PROP-R3 | Bot2bot dedup: two stub instances on same market_id → second reduces or skips position | REQ-R3 | 2 | true | integration (stub gh issue API) |
| PROP-R4 | ledger.jsonl never written via truncate or O_WRONLY (only O_APPEND) | REQ-R4 | 2 | true | integration (fsevents or strace spy) |
| PROP-R5 | yield-keeper defends COMPUTE_RESERVE + reserved.json: balance $100 & reserved_usdc 60 → deploys ≤ $35; reserved.json absent → deploys balance−COMPUTE_RESERVE (legacy) | REQ-R5 | 2 | true | integration (stub execute-yield, assert deposit amount cap) |
| PROP-E2E-1 | After paper_pass_count ≥ required AND adversary PASS: a real Polygon/Base tx from wallet exists for a model-decided trade | REQ-T7, REQ-T8 | 3 | true | E2E (real tiny stake, on-chain verify) |
| PROP-E2E-2 | Child runtime with its own funded wallet completes ≥1 earn pass verified on-chain | REQ-S5, REQ-S8 | 3 | true | E2E (child boot + real tithe tx) |

## Verification Strategy

### Tier 0 — No Formal Proof (trivially correct or single-line)

- `earnSkillRelPath("earn/pm-trade")` string return (single-line string concat in existing module)
- `registry.json` JSON schema (static file; validated by `jq` in install.sh)
- Env var wiring (`ANICCA_HOME`, `CHILD_HOME`) — covered by integration smoke

### Tier 1 — Unit / Property Tests (pytest + hypothesis)

All pure functions in the Pure Core table above. Fixture corpus:

**Kelly / RiskGate fixtures:**

| fixture id | inputs | expected output |
|------------|--------|-----------------|
| KF-01 | edge=0.1, market_p=0.6, bankroll=10.0, kelly_max=0.05, min=1.50, gas=0.50 | float ∈ [1.50, 9.50] |
| KF-02 | edge=0.0, market_p=0.5, bankroll=10.0, ... | 0 (no edge) |
| KF-03 | edge=0.1, market_p=1.0, ... | 0 (denominator guard) |
| KF-04 | edge=0.1, market_p=0.5, bankroll=0.0, ... | 0 (zero bankroll) |
| KF-05 | edge=0.1, market_p=0.5, bankroll=1.0, min=1.50, gas=0.50 | 0 (bankroll − gas = 0.50 < min 1.50 → SKIP) |
| RG-01 | daily_loss=5.0, start_balance=100.0, daily_loss_pct=0.05, position=2.0 | HALT("daily_loss_cap_reached") |
| RG-02 | peak=100.0, current=75.0, drawdown_pct=0.25, all others clear | HALT("drawdown_cap_reached") |
| RG-03 | position=1.0, min_position=1.50 | HALT("below_min_position") |
| RG-04 | current=2.0, position=1.8, gas_reserve=0.50 | HALT("insufficient_gas_reserve") |
| RG-05 | edge=0.0, all other caps clear | HALT("no_edge") |
| RG-06 | edge=0.05, daily_loss=0.0, drawdown=0.0, position=2.0, balance=10.0, gas=0.50, min=1.50 | ALLOW("risk_gate_passed") |
| RG-07 | daily_loss=5.0 exactly = threshold (0.05×100) | HALT (boundary: ≥ inclusive) |
| RG-08 | drawdown=25.0 exactly = 0.25×100 | HALT (boundary: ≥ inclusive) |

**SpawnEligible fixtures:**

| fixture id | inputs | expected |
|------------|--------|----------|
| SE-01 | treasury=10.0, threshold=40.0 | {eligible:false, reason:"insufficient_treasury"} |
| SE-02 | treasury=50.0, net_pos_days=2, required=3 | {eligible:false, reason:"not_enough_net_positive_days"} |
| SE-03 | treasury=50.0, net_pos_days=5, recent_spawn_within_14d=true | {eligible:false, reason:"rate_cap"} |
| SE-04 | treasury=40.0 (= threshold), net_pos_days=3, no_recent_spawn, seed=20.0 | {eligible:true} |
| SE-05 | seed_usdc=1.0 (< 1.50) | {eligible:false, reason:"seed_below_minimum"} |
| SE-06 | treasury=39.99 (just below threshold) | {eligible:false} |
| SE-07 | treasury=40.01 | {eligible:true} |

**Hypothesis property sweep:**

- `kellyFraction` with hypothesis `given(floats(0.001,0.999), floats(0.001,0.9999), floats(0.1,1000.0), ...)`: output always ≤ bankroll − gas_reserve AND ≥ 0.
- `riskGate` with hypothesis: if any HALT condition is present, result is HALT (= HALT conditions are sufficient individually, not needing conjunction).
- `spawnEligible` with hypothesis: eligible=True requires ALL four conditions simultaneously.

### Tier 2 — Integration Tests (real filesystem, stub network)

Each test boots a minimal Anicca runtime in a `tmpdir` with `ANICCA_HOME=<tmpdir>` and `ANICCA_TEST_MODE=1`. Network calls are stubbed via `pytest-mock` or `responses`.

**Integration test suite:**

| test id | description | assertion |
|---------|-------------|-----------|
| INT-T1 | Paper mode: run full skill pass with stub CLOB returning valid order JSON | Zero CLOB endpoint calls (spy confirms); paper-log.jsonl has 1 row |
| INT-T2 | Paper-to-real gate: paper_pass_count < required | paper_mode stays true |
| INT-T3 | Paper-to-real gate: paper_pass_count ≥ required AND adversary PASS file present | paper_mode transitions to false (atomic rename) |
| INT-T4 | Paper-to-real gate: paper_pass_count ≥ required BUT adversary file absent | paper_mode stays true (fail-closed) |
| INT-T5 | Earn row: order placed → no earn event; market resolves → earn event in events/ | Event stream correct; events/ spy confirms timing |
| INT-T6 | Risk gate halt persists: after HALT, subsequent passes do NOT call CLOB | State machine correct; daily_loss accumulated across passes |
| INT-T7 | Geoblock: polymarket.jurisdiction_ok_for_real=false → zero Polymarket CLOB calls | Spy on pm.py invocations; confirm venue=kalshi chosen instead |
| INT-T8 | isEarnSlot + registry: after install, earn/pm-trade is a registered live earn slot | Node unit test + registry JSON assertion |
| INT-T9 | Wallet isolation: two instances in different tmpdir ANICCA_HOME have different wallet.json | Address inequality assertion |
| INT-T10 | Spawn eligibility: all conditions met → spawn-log gets "initiated" row | spawn-log.jsonl assertion |
| INT-T11 | Spawn rate cap: second spawn within 14d → no new "initiated" row | spawn-log unchanged after second call |
| INT-T12 | Spawn net-positive guard: cumulative_usdc_earned=0 → no spawn | spawnEligible returns false |
| INT-T13 | Seed transfer fails → child home cleaned up; spawn-log at "failed" | tmpdir deleted; spawn-log status check |
| INT-T14 | Bot2bot dedup: two instances stub-gh-issue on same market_id → second instance skips or reduces | Integration with stub gh client |
| INT-T15 | ledger.jsonl written only via O_APPEND (no truncation) | File open mode spy |
| INT-T16 | Concurrent spawn attempts: only first proceeds | Thread-concurrent calls; only one "initiated" row |
| INT-T17 | Earn event REQ-G2 three-check gate: endpoint not in allowlist → no earnings.jsonl append | Stub endpoint; assert earnings.jsonl unchanged |
| INT-T18 | Earn event REQ-G2: response hash mismatch → no append | Stub re-fetch with different body |
| INT-T19 | compute-proxy down → skill exits non-zero; ledger records kind: "skill_error" | No CLOB call; kind check |
| INT-T20 | Kelly fraction + riskGate: position size clamped when computed value > wallet − gas | position_usdc ≤ wallet_balance − gas_reserve assertion |

### Tier 3 — E2E (real on-chain; run against live Base/Polygon with minimal stake)

These tests are the "done" conditions from the design spec. Run manually (or in CI with a funded test wallet) after all Tier 1/2 tests pass.

| E2E id | Description | Verifiable Done Condition |
|--------|-------------|--------------------------|
| E2E-1 | Paper run (≥ required passes) followed by adversary PASS and then a real tiny stake on Polygon | A real Polygon tx hash from `~/.automaton/wallet.json` exists; `events/<pass_id>.jsonl` has `event: "earn"` with `platform_api_call.response_sha256` verifiable on Polymarket settlement API; `earnings.jsonl` has a row with non-null `receipt_id`. |
| E2E-2 | Full spawn: parent with net-positive history → child runtime with own wallet self-pays compute and completes ≥1 earn pass | `spawn-log.jsonl` row at `status: "registered"`; child's `$CHILD_HOME/state/ledger.jsonl` has ≥1 `kind: "wake"` row; `tithe-log.jsonl` has ≥1 row with a confirmed Base tx_hash for `tithe_usdc ≥ min_tithe`. |

**E2E execution procedure:**

1. Fund test wallet `$ANICCA_HOME/.automaton/wallet.json` on Base with 5.0 USDC (via Solana on-ramp).
2. Set `risk_config.paper_passes_required = 2` and `risk_config.spawn_threshold_usdc = 3.0` (test values).
3. Run 2 paper passes; confirm `paper-log.jsonl` has 2 rows.
4. Run nightly adversary (`adversary-daily.sh earn/pm-trade`); wait for PASS verdict.
5. Confirm `paper_mode` transitions to `false`.
6. Run 1 real pass with `risk_config.min_position_usdc = 1.50`; confirm on-chain order.
7. Wait for market resolution; confirm earn row in `earnings.jsonl`.
8. Confirm `cumulative.json.cumulative_usdc_earned` reflects realized PnL.
9. For spawn E2E: parent net-worth now > 3.0 USDC; run spawn slot; confirm child home + tx + child loop start.

## Regression Baseline (inherited)

All `earn-shared-skeleton` tests (PROP-A1..J8) continue to pass unchanged. The new slot extends earn-slot.mjs without modifying it; the existing unit test suite for `earn-slot.mjs` must remain green after the `earn/pm-trade` slot is added to `registry.json`.

## Anti-Slop Commitments

| Risk | Mitigation |
|------|-----------|
| Hardcoded strategy in skill code | PROP-T3 (no regex/keyword) + adversary static analysis of `run.sh` and `pm.py` |
| Fake PnL (earn event without real settlement) | PROP-T21 + REQ-G2 three-check gate (endpoint allowlist + hash fidelity + field equality) |
| Human touch in spawn flow | REQ-J8 inheritance + adversary static analysis for Telegram/gh-escalation patterns |
| Paper mode bypass | PROP-T18 + PROP-T19 + PROP-T20 (state machine tests) |
| Wallet collision / cross-instance key sharing | PROP-S10 + PROP-R2 (isolation integration tests) |
| Kelly overbetting | PROP-T1 hypothesis sweep + kelly_fraction_max cap |
| Spawn without net-positive history | PROP-S2 + PROP-S5 (pure function + hypothesis) |
| Ledger truncation | PROP-R4 (O_APPEND mode spy) |
