# earn/pm-trade — Polymarket momentum/latency earn slot

CLOUD-portable (wallet-only, no browser, no KYC). Base = `BlockRunAI/polymarket-agent`. The MODEL/loop drives
it; all judgment math is pure + tested. **Money-safe today: no signing / order-placement code exists in this
slot — the real executor is intentionally not wired (fail-closed).**

## Strategy
Pure resting-book arbitrage (YES+NO < $1) does NOT exist on Polymarket — verified live 2026-07-04, 0 arbs
across 70 markets, all pinned at sum = $1.0010 (0.1¢ min spread). The real edge is **momentum/latency**: the
5-min BTC up/down market reprices slower than Binance spot, so a signed edge appears when spot has already
moved this window. `lib.arb_pair_profit` stays as a cheap always-on check.

## Files
| File | Role | Pure? |
|---|---|---|
| `lib.py` | edge / Quarter-Kelly `position_size` / `settle_pnl` / `side_won` / `arb_pair_profit` | pure |
| `momentum.py` | `prob_up_from_return` / `momentum_edge` / `side_and_prob` (latency edge) | pure |
| `decide.py` | WIRING: live Binance BTC klines + Polymarket 5-min market → momentum → Kelly → paper record | shell |
| `resolve.py` | mark open paper trades `resolved` via the Binance window outcome → real `pnl_usdc` | shell |
| `gate.py` | PRODUCE `PM_PAPER_PASS` from the resolved paper ledger (≥20 trades, ≥55% win, net≥0) | pure core |
| `run.sh` | produce gate → decide → real order fail-closed | shell |
| `pm-paper.py` | standalone live read-only paper mechanics (discover/paper-buy/mark) | shell |
| `test_lib.py` (11) + `test_strategy.py` (12) | 23 tests, all GREEN | — |

## Loop (paper → gate → real)
1. cron every ~1 min during a window: `run.sh` → `decide.py` records a paper trade when momentum edge ≥ `PM_MIN_EDGE` (default 0.03).
2. cron each window close: `resolve.py` marks trades resolved with real P&L from the Binance candle.
3. `gate.py` PASSes only after ≥20 resolved trades with ≥55% win-rate and non-negative net.
4. ONLY then wire the real executor (polymarket-agent, RPC = `polygon-bor-rpc.publicnode.com`) and do a $1 live order → first earned tx.

## Ledger
`~/loops/earn-pm-trade/paper-positions.jsonl` (append-only; momentum rows tagged `src:"momentum"`).

## Safety
`run.sh` real branch is fail-closed; `PM_PAPER_PASS` is produced from the ledger, never trusted from env.
No private key is read and no order endpoint is POSTed anywhere in this slot.
