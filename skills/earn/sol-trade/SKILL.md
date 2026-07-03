# sol-trade — Franklin-Trading base agent, run AS-IS (W2)

**No strategy lives here.** The base agent
[`BlockRunAI/Franklin-Trading`](https://github.com/BlockRunAI/Franklin-Trading)
(`npm i -g @blockrun/franklin-trading`) researches, debates, sizes and trades by itself, and pays
for its OWN model calls via x402 USDC from its OWN Solana wallet
`8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9` (~/.blockrun/). APIキー不要 — the wallet IS the
fuel (release-copy bullet V5). SSOT: colony spec §0.25 + §10 W2.

## Run

```bash
./run.sh    # one real pass. No dry-run mode exists (HARD 0.24).
```

## Money-safety guards

| Guard | How |
|---|---|
| kill-switch | `touch KILL` here → next run exits |
| LLM spend cap | `--max-spend` per pass (`SOL_TRADE_MAX_SPEND`, default $0.25) |
| bankroll | whatever USDC sits in ITS wallet — the agent sees the real number and decides |

## Verified 2026-07-04 (first real pass)

Funded via real bridge (Base→Solana, Across, $1.50→1.327 USDC) + 0.003 SOL gas (tx 52rB7…).
Agent paid opus-4.8 via x402 from its own wallet, checked its balance itself, and judged:
"$1.33 with ~0.4% round-trip fees = no edge, a directional trade is a coinflip with fee drag —
wait." Correct autonomous behavior; 0 forced trades. Trace → `../state/sol-trade.trace.jsonl`.

## If a run errors (self-heal, H4)

Running agent: read the error, fix your own setup (`~/.blockrun/`, CLI), re-run. Never force a
trade to "show progress" — a reasoned WAIT is a valid outcome.
