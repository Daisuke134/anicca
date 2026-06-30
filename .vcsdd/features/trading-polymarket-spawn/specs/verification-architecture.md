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
| `riskGate(risk_state, position_usdc, current_balance, edge, config)` | `skills/earn/pm-trade/risk.py` | typed records | `{decision: ALLOW\|HALT, reason: str}` |
| `edgePredicate(model_p, market_p)` | `skills/earn/pm-trade/risk.py` | 2 floats | `bool` |
| `positionSize(kelly_f, bankroll, min_size, gas_reserve)` | `skills/earn/pm-trade/risk.py` | 4 floats | `float` |
| `jurisdictionVenueFilter(jurisdiction_ok_for_real, kyc_required)` | `skills/earn/pm-trade/risk.py` | bool, bool | `bool` (True = BOTH `jurisdiction_ok_for_real == true` AND `kyc_required == false`; effectful shell reads both scalars from `menu.venues[venue]` and passes as explicit args; no `jurisdiction`/`venue` string args — they are vestigial and removed) |
| `selectTier(balanceUsdc, env)` | `runtime/loop/tier.mjs` | float, dict | `{tier, model}` (existing) |
| `isEarnSlot(slot)` | `runtime/loop/earn-slot.mjs` | str | `bool` (existing) |
| `earnSkillRelPath(slot)` | `runtime/loop/earn-slot.mjs` | str | `str` (existing) |

### Effectful Shell (I/O bound; tested via integration/E2E)

| Component | Side Effects |
|-----------|-------------|
| `pm.py` | REST calls to Polymarket/Kalshi/Hyperliquid CLOB; writes to `risk_state.json`, `events/` |
| `ensure-solana-wallet.mjs` | ed25519 keygen + file write to `$ANICCA_HOME/.automaton/solana.json` |
| EVM key gen + Base tx broadcast | entropy read; `wallet.json` write; on-chain USDC transfer |
| `appendLedgerLine` | O_APPEND write to `ledger.jsonl` (existing) |
| `bot2bot.sh` gh issue create | gh API call (trade dedup only; spawn bot2bot deferred to `spawn-child-earn`) |
| Predexon x402 fetch | outbound HTTP; x402 USDC settlement |

## Proof Obligations

| ID | Description | REQ | Tier | Required | Tool |
|----|-------------|-----|------|----------|------|
| PROP-T1 | `kellyFraction(e, m, B, kmax, min, gas)`: output ∈ [min, B − gas] for any valid edge e ∈ (0,1), market_p m ∈ (0,1), bankroll B > min + gas | REQ-T5 | 1 | true | pytest property + hypothesis |
| PROP-T2 | `kellyFraction(0, m, B, ...)` = 0 for all m, B | REQ-T5 | 1 | true | pytest |
| PROP-T3 | `kellyFraction(e, 1.0, B, ...)` = 0 (denominator guard: 1−market_p = 0) | REQ-T5 | 1 | true | pytest |
| PROP-T4 | `kellyFraction(e, m, 0, ...)` = 0 (zero bankroll → zero position) | REQ-T5 | 1 | true | pytest |
| PROP-T5 | `riskGate`: daily_loss ≥ 0.05 × start_balance → HALT("daily_loss_cap_reached") for any position_usdc | REQ-T4 | 1 | true | pytest |
| PROP-T6 | `riskGate(state, pos, current_balance, edge, cfg)`: daily_loss < threshold AND (peak − current_balance) ≥ 0.25 × peak → HALT("drawdown_cap_reached"); `current_balance` is an explicit arg, not an RPC call inside `riskGate` | REQ-T4 | 1 | true | pytest |
| PROP-T7 | `riskGate`: position_usdc < min_position_usdc → HALT("below_min_position") | REQ-T4 | 1 | true | pytest |
| PROP-T8 | `riskGate`: current_balance − position_usdc < gas_reserve → HALT("insufficient_gas_reserve") | REQ-T4 | 1 | true | pytest |
| PROP-T9 | `riskGate`: edge ≤ 0 → HALT("no_edge") regardless of other fields | REQ-T4 | 1 | true | pytest |
| PROP-T10 | `riskGate`: all conditions clear → ALLOW("risk_gate_passed") | REQ-T4 | 1 | true | pytest |
| PROP-T11 | `riskGate(risk_state, pos, current_balance, edge, config)` is pure: same 5-tuple of inputs → identical output (no hidden state, no I/O) | REQ-T4 | 2 | true | hypothesis stateless test |
| PROP-T12 | `riskGate` boundary: daily_loss exactly = threshold → HALT (≥ is inclusive, not >) | REQ-T4 | 1 | true | pytest |
| PROP-T13 | `riskGate` boundary: drawdown exactly = threshold → HALT | REQ-T4 | 1 | true | pytest |
| PROP-T14 | `jurisdictionVenueFilter(jurisdiction_ok_for_real=False, kyc_required=False)` = False (jurisdiction blocked) | REQ-T10 | 1 | true | pytest |
| PROP-T14b | `jurisdictionVenueFilter(jurisdiction_ok_for_real=True, kyc_required=True)` = False (kyc_required veto fires even when jurisdiction_ok_for_real=True; belt-and-suspenders against misconfiguration) | REQ-T10 | 1 | true | pytest |
| PROP-T15 | `jurisdictionVenueFilter(jurisdiction_ok_for_real=False, kyc_required=True)` = False (both fields fail-closed) | REQ-T10 | 1 | true | pytest |
| PROP-T15b | Effectful shell reads `menu.venues[venue].kyc_required` before calling `jurisdictionVenueFilter`; absent `kyc_required` key defaults to `True` (fail-closed — venue assumed KYC-required until explicitly cleared) → `jurisdictionVenueFilter(kyc_required=True, ...)` = False | REQ-T10 | 1 | true | pytest (absent key → default True → False) |
| PROP-T16 | `jurisdictionVenueFilter(jurisdiction_ok_for_real=True, kyc_required=False)` = True (both flags clear = allowed) | REQ-T10 | 1 | true | pytest |
| PROP-T17 | `edgePredicate(model_p, market_p)` = True IFF `model_p > market_p` (strict inequality) | REQ-T3 | 1 | true | pytest |
| PROP-T18 | Paper mode: no CLOB endpoint called while `risk_state.paper_mode = true` (confirmed by call-spy) | REQ-T6 | 2 | true | integration + spy |
| PROP-T19 | Paper-to-real transition requires both paper_pass_count ≥ required AND adversary PASS file present | REQ-T6 | 2 | true | integration (state machine) |
| PROP-T20 | Paper-to-real transition fails-closed when adversary PASS file absent (even if paper_pass_count ≥ required) | REQ-T6 | 1 | true | pytest (file absent → paper stays) |
| PROP-T21 | Earn row written ONLY on market resolution, never on order placement | REQ-T8 | 2 | true | integration (spy on events file) |
| PROP-T22 | `cumulative.json.cumulative_usdc_earned` is the sum of all earn rows including negative PnL | REQ-T8 | 1 | true | pytest (negative-PnL scenario) |
| PROP-T23 | Risk state `daily_loss_usdc` is incremented by the absolute value of each negative PnL | REQ-T8 | 1 | true | pytest |
| PROP-T24 | `isEarnSlot("earn/pm-trade")` = true (earn-slot.mjs existing pure predicate) | REQ-T1 | 1 | true | node unit test |
| PROP-T25 | `earnSkillRelPath("earn/pm-trade")` = `"earn/pm-trade/run.sh"` | REQ-T1 | 1 | true | node unit test |
<!-- PROP-S1..S13 deferred to feature spawn-child-earn; preserved verbatim in out-of-scope.jsonl -->
| PROP-R1 | `registry.json` declares `earn/pm-trade` with `status: "live"` after install | REQ-T1 | 2 | true | integration (run install.sh in tmpdir) |
| PROP-R2 | Two instances with different ANICCA_HOME never share wallet.json path | REQ-R2 | 2 | true | integration |
| PROP-R3 | Bot2bot dedup: two stub instances on same market_id → second reduces or skips position | REQ-R3 | 2 | true | integration (stub gh issue API) |
| PROP-R4 | ledger.jsonl never written via truncate or O_WRONLY (only O_APPEND) | REQ-R4 | 2 | true | integration (fsevents or strace spy) |
| PROP-R5 | `execute-yield.mjs` (the surplus-math module, not yield-keeper.mjs) with EFFECTIVE_RESERVE = COMPUTE_RESERVE + reserved.json.reserved_usdc: balance $100, reserved_usdc 60 → deploys ≤ $35; reserved.json absent AND earn/pm-trade registered → deploys $0 (fail-safe, no sweep); reserved.json absent AND earn/pm-trade not in registry → deploys balance−COMPUTE_RESERVE (legacy) | REQ-R5 | 2 | true | integration (stub Base RPC balanceOf; assert deposit call amount for all 3 cases) |
| PROP-T26 | Earn row for Polymarket CTF binary winning settlement: only written when `settle-verify.py` returns `{verified: true}` with a Transfer where (1) `from` ∈ `POLYMARKET_SETTLEMENT_ADDRS`, (2) amount equals `gross_payout_usdc = shares_held × 1.00 USDC` (±1 raw 6-decimal unit), where `shares_held = filled_size / entry_price` (both from the matching `risk_state.open_positions` row), and (3) tx contains matching `condition_id` PositionRedemption/PayoutRedemption event; no earn row when no matching Transfer found. (`position_size_usdc × settlement_price` is NOT the correct formula — it is replaced by this definition.) | REQ-T8 | 2 | true | integration (stub Polygon RPC → no matching log → assert earnings.jsonl unchanged; stub → matching log with amount = round(filled_size/entry_price * 1e6) ±1 meeting all 3 sub-conditions → assert earn row written) |
| PROP-T26b | `settle-verify.py` REJECTS a Transfer where `from` is NOT in `POLYMARKET_SETTLEMENT_ADDRS` (e.g. an unrelated transfer, wallet top-up, or wrong-market payout) — no earn row written even if `amount >= entry_cost`; INV-7 not satisfied by a misattributed transfer | REQ-T8 | 2 | true | integration (stub Polygon RPC with Transfer `from`=random address, amount >= entry_cost → assert earnings.jsonl unchanged) |
<!-- PROP-R6, PROP-S14, PROP-E2E-2 deferred to feature spawn-child-earn; preserved verbatim in out-of-scope.jsonl -->
| PROP-E2E-1 | After paper_pass_count ≥ required AND adversary PASS: a real Polygon/Base tx from wallet exists for a model-decided trade | REQ-T7, REQ-T8 | 3 | true | E2E (real tiny stake, on-chain verify) |

## Verification Strategy

### Tier 0 — No Formal Proof (trivially correct or single-line)

- `earnSkillRelPath("earn/pm-trade")` string return (single-line string concat in existing module)
- `registry.json` JSON schema (static file; validated by `jq` in install.sh)
- Env var wiring (`ANICCA_HOME`) — covered by integration smoke

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

<!-- SE-01..SE-07 (SpawnEligible fixtures) deferred to spawn-child-earn; preserved in out-of-scope.jsonl -->

**Hypothesis property sweep:**

- `kellyFraction` with hypothesis `given(floats(0.001,0.999), floats(0.001,0.9999), floats(0.1,1000.0), ...)`: output always ≤ bankroll − gas_reserve AND ≥ 0.
- `riskGate` with hypothesis: if any HALT condition is present, result is HALT (= HALT conditions are sufficient individually, not needing conjunction).

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
| INT-T7 | Geoblock: polymarket.jurisdiction_ok_for_real=false → zero Polymarket CLOB calls; kalshi.kyc_required=true → zero Kalshi CLOB calls even if jurisdiction_ok_for_real=true; hyperliquid.jurisdiction_ok_for_real=true AND kyc_required=false → hl.py invoked | Spy on pm.py and hl.py invocations; confirm all three branches |
| INT-T8 | isEarnSlot + registry: after install, earn/pm-trade is a registered live earn slot | Node unit test + registry JSON assertion |
| INT-T9 | Wallet isolation: two instances started with different `HOME` env values (`HOME=$TMPDIR_A` vs `HOME=$TMPDIR_B`) resolve `wallet.json` to different paths and different secp256k1 addresses | `process.env.HOME` path inequality + address inequality assertion; confirms `proxy.mjs` wallet read uses `$HOME`, not `$ANICCA_HOME` |
<!-- INT-T10..T13, INT-T16 (spawn tests) deferred to spawn-child-earn; preserved in out-of-scope.jsonl -->
| INT-T14 | Bot2bot dedup: two instances stub-gh-issue on same market_id → second instance skips or reduces | Integration with stub gh client |
| INT-T15 | ledger.jsonl written only via O_APPEND (no truncation) | File open mode spy |
| INT-T17 | Earn event REQ-G2 three-check gate: endpoint not in allowlist → no earnings.jsonl append | Stub endpoint; assert earnings.jsonl unchanged |
| INT-T18 | Earn event REQ-G2: response hash mismatch → no append | Stub re-fetch with different body |
| INT-T19 | compute-proxy down → skill exits non-zero; ledger records kind: "skill_error" | No CLOB call; kind check |
| INT-T20 | Kelly fraction + riskGate: position size clamped when computed value > wallet − gas | position_usdc ≤ wallet_balance − gas_reserve assertion |
| INT-T21 | reserved.json absent + earn/pm-trade in registry: execute-yield.mjs deploys $0 (fail-safe) | Stub Base RPC balanceOf=$100; assert no deposit call issued; assert output `deposited_usdc: 0` |

### Tier 3 — E2E (real on-chain; run against live Base/Polygon with minimal stake)

These tests are the "done" conditions from the design spec. Run manually (or in CI with a funded test wallet) after all Tier 1/2 tests pass.

| E2E id | Description | Verifiable Done Condition |
|--------|-------------|--------------------------|
| E2E-1 | Paper run (≥ required passes) followed by adversary PASS and then a real tiny stake on Polygon | A real Polygon tx hash from `~/.automaton/wallet.json` exists; `events/<pass_id>.jsonl` has `event: "earn"` with `platform_api_call.response_sha256` verifiable on Polymarket settlement API; `earnings.jsonl` has a row with non-null `receipt_id`. |
<!-- E2E-2 (spawn) deferred to spawn-child-earn; preserved in out-of-scope.jsonl -->

**E2E execution procedure:**

1. Fund test wallet `$ANICCA_HOME/.automaton/wallet.json` on Base with 5.0 USDC (via Solana on-ramp).
2. Set `risk_config.paper_passes_required = 2` (test value).
3. Run 2 paper passes; confirm `paper-log.jsonl` has 2 rows.
4. Run nightly adversary (`adversary-daily.sh earn/pm-trade`); wait for PASS verdict.
5. Confirm `paper_mode` transitions to `false`.
6. Run 1 real pass with `risk_config.min_position_usdc = 1.50`; confirm on-chain order.
7. Wait for market resolution; confirm earn row in `earnings.jsonl`.
8. Confirm `cumulative.json.cumulative_usdc_earned` reflects realized PnL.

<!-- Step 9 (spawn E2E) deferred to spawn-child-earn feature. -->

## Regression Baseline (inherited)

All `earn-shared-skeleton` tests (PROP-A1..J8) continue to pass unchanged. The new slot extends earn-slot.mjs without modifying it; the existing unit test suite for `earn-slot.mjs` must remain green after the `earn/pm-trade` slot is added to `registry.json`.

## Anti-Slop Commitments

| Risk | Mitigation |
|------|-----------|
| Hardcoded strategy in skill code | PROP-T3 (no regex/keyword) + adversary static analysis of `run.sh` and `pm.py` |
| Fake PnL (earn event without real settlement) | PROP-T21 + PROP-T26 + PROP-T26b + `settle-verify.py` on-chain gate: Polymarket CTF binary = `eth_getLogs` Transfer where `from` ∈ `POLYMARKET_SETTLEMENT_ADDRS` + `gross_payout_usdc = shares_held × $1.00` (where `shares_held = filled_size / entry_price`) ±1 raw unit + matching `condition_id` in tx; HL = API realizedPnl delta. Unrelated transfers are REJECTED by PROP-T26b. REQ-G2 skeleton gate is NOT used for trading venues; `settle-verify.py` is the dedicated gate. |
| Paper mode bypass | PROP-T18 + PROP-T19 + PROP-T20 (state machine tests) |
| Wallet collision / cross-instance key sharing | PROP-R2 (two instances with different ANICCA_HOME never share wallet.json path) |
| Kelly overbetting | PROP-T1 hypothesis sweep + kelly_fraction_max cap |
| Ledger truncation | PROP-R4 (O_APPEND mode spy) |
