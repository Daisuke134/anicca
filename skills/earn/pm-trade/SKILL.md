# pm-trade — Polymarket base agent, run AS-IS (W1)

**The strategy is NOT here and never will be.** The base agent
[`BlockRunAI/polymarket-agent`](https://github.com/BlockRunAI/polymarket-agent) does its OWN market
analysis (paid per-request via BlockRun x402), its OWN sizing (its Kelly config), and its OWN execution
(py-clob-client, EOA direct `signature_type=0`). This skill is a thin harness: run it for real, record
the trace, stay out of the way. (SSOT: colony spec §0.25 THE PIVOT + §10 W1.)

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
