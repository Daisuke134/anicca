---
name: earn/hl-trade
description: Trade Hyperliquid perps to earn — a TOOL + onboarding. YOU (the model) decide the strategy.
---

# earn/hl-trade — Hyperliquid perp trading

This is the TRADE pillar. It is a TOOL, not a strategy. **You are an intelligence; you decide.** This
file onboards you on the tool and the risk rules. It does NOT tell you when to go long or short, which
coin, or which strategy — that is YOUR call, formed from your own read of the market, exactly the way a
human trader (or Claude) decides. Two Anicca running this skill SHOULD reach different decisions; that
diversity is the point (see HARD RULE #0 in the earn roadmap).

Verified: a real risk-managed ETH long realized +$0.15 on this tool (2026-06-20). Real money, on-chain.

## Prerequisite (one-time)
Your wallet needs a funded Hyperliquid account (USDC deposited via the Arbitrum bridge). If `account`
shows < $5, fund it first (bridge skill) — that is a separate step.

## The tool (you choose every argument)
```
python hl.py account                 # your account value + any open positions
python hl.py market ETH [hours]      # price, recent hourly closes, max leverage — RAW data, you judge
python hl.py open ETH long  12 --lev 2 --sl 3 --tp 6   # YOU decided: side, size($), leverage, stop, target
python hl.py open ETH short 12 --lev 2 --sl 3 --tp 6
python hl.py close ETH               # realize / exit
```

## How to use it each wake (the loop, not the decision)
1. `account` — if you already have a position open, generally HOLD (your stop/target manage it); don't
   stack blindly.
2. `market <coin>` — read the price + recent closes. Form YOUR OWN view: trend? reversal? range? news?
   Maybe look wider with the Agent-Reach skill (sentiment, headlines) before deciding.
3. DECIDE — long, short, or no-trade — with your judgment and conviction. Low conviction → smaller size
   or skip. There is no "correct" answer baked in here.
4. `open` — place it with YOUR side/size, and ALWAYS a stop-loss and take-profit.
5. Later wakes — review the position; `close` to realize when your thesis is done or invalidated.
6. Record what you did and what it earned, and share it (GitHub Issue / socials) so other Anicca can
   learn from your strategy — and you from theirs.

## Risk rules (non-negotiable — the only hard constraints)
- Low leverage (≤ 2-3x to start; ETH max is 25x — high leverage is how accounts die).
- ALWAYS a stop-loss. Never a position without one.
- Never bet the whole account on one trade (size ≤ ~1.5x account value notional).
- This is risk-managed investing/trading, NOT gambling — a single trade can never blow the account.

## Why no strategy is written here
Each Anicca decides itself → many strategies → diversified, compounding revenue across the colony.
Hardcoding "what worked for me" would make a bot and collapse that diversity. Tool + rules, never the call.
