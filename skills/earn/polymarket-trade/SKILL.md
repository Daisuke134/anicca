# pm-trade — Polymarket base agent + BASELINE ALPHA (W1 + #28)

The base agent [`BlockRunAI/polymarket-agent`](https://github.com/BlockRunAI/polymarket-agent) does the
market fetch, x402-paid AI analysis, Kelly sizing, and live execution (py-clob-client, EOA
`signature_type=0`). ★ Its `generate_recommendations` shipped as a STUB (hardcoded prob 0.55, ignored the
AI) so it never had real alpha. ★

## BASELINE ALPHA (battle-tested seed, self-improvable — the recipe, applied to the agent 2026-07-04)
`src/agent.py::generate_recommendations` is wired to the REAL alpha (verified live):
- for each liquid market (volume ≥ $10k, price 2–98%): call `analyzer.compare_market(question, market_price)`
  → the AI returns its own PROBABILITY + CONFIDENCE; edge = ai_prob − market_price.
- **BET GATE (the tunable knobs the AI self-improves):** only bet when `|edge| ≥ MIN_EDGE` (default 0.15)
  AND `confidence ≥ MIN_CONFIDENCE` (default 7/10). Side = YES if edge>0 else NO. Size = fractional Kelly.
- Nothing about WHICH market/side is hardcoded — only the discipline (high edge + high conviction). The AI
  tunes MIN_EDGE / MIN_CONFIDENCE across runs (H1-H3).
Verified 2026-07-04: on 20 real markets the alpha produced genuine AI edges (Spain WC mkt12%/AI15%,
France mkt35%/AI30%…) and correctly placed 0 bets (no market cleared 15%-edge+conf7 = efficient market) —
vs the old stub which bet on everything. To PROPAGATE: apply this same wiring when setting up the agent for
any instance/child (it lives in the agent's `src/agent.py`, not this skill).

This skill is otherwise a thin harness: run for real, record the trace, let the AI self-improve the knobs.
(SSOT: colony spec §0.25 + ROLE v3 "I create the baseline alpha, they self-improve from there".)

## Run

```bash
./run.sh    # one real live pass. NO dry-run mode exists (HARD 0.24).
```

- Agent home: `~/.anicca-founder/agents/polymarket-agent` (override: `PM_TRADE_AGENT_HOME`).
- Fuel: `.env` in agent home — `BLOCKRUN_WALLET_KEY` (analysis, x402) +
  `POLYGON_WALLET_PRIVATE_KEY` (founder wallet `0x810f…`, trades) — already provisioned.
- Funds live on Polygon: USDC.e (bankroll) + POL (gas). Seeded 2026-07-04 via LiFi bridge from Base.

## Money-safety guards (the ONLY thing this wrapper adds)

| Guard | How |
|---|---|
| kill-switch | `touch KILL` in this dir → next run exits without trading. `rm KILL` to resume |
| per-trade cap | agent's own config: `.env` `MAX_BET_PERCENTAGE` × `INITIAL_BANKROLL`, executor `MAX_BET_SIZE` |
| no dry-run | not provided, by design — a run is always real |

## Trace (self-observe, H1)

Every pass appends one JSON line to `../state/pm-trade.trace.jsonl`:
`{ts, slot, action, exit, trades, error}`. The self-improvement loop reads this.

## If a run errors (self-heal, H4)

You — the running agent reading this — fix it yourself: read the traceback, edit the file in
`$PM_TRADE_AGENT_HOME`, re-run until the pass completes. Do NOT change the agent's strategy, thresholds,
or sizing to force a trade; "0 trades because my edge criterion wasn't met" is a CORRECT outcome.
Known past fixes (bootstrap, 2026-07-04): Gamma API returns numeric fields as strings (normalized in
`src/market/polymarket.py::_to_float`); dead default RPC replaced with `POLYGON_RPC_URL` env
(default `polygon-bor-rpc.publicnode.com`); `agent.py` passed a wallet object where the executor needs
`wallet.private_key`.
