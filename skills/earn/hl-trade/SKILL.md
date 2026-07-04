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

## ★ BASELINE STRATEGY (battle-tested seed — START here, then self-improve) — #24 H8 ★
You are NOT expected to invent alpha from zero (that is why you churned "close ETH" for $0). Start from this
tested trend-following baseline, then tune it across runs from your own P&L (H1-H3). It is a STARTING POINT,
not a cage — override it when you have a better-reasoned view.

1. `account` FIRST. **If you already hold a position → HOLD it** (your stop/target manage it). Do NOT stack
   a second one, and ★ do NOT call `close` on it just to "do something" ★ — close ONLY when your thesis is
   invalidated or the take-profit/stop is effectively hit.
2. **If you are FLAT** (no open position): `market <coin> 24` and read `closes_hourly` + `change_pct_window`:
   - **Uptrend** = last close is clearly above the window mean (≈ +1% or more) AND the recent closes are
     rising → open a SMALL **long**.
   - **Downtrend** = last close clearly below the mean (≈ −1% or more) AND falling → open a SMALL **short**.
   - ★ **Range / noise** (|change_pct_window| < ~1%, choppy, no clear direction) → **NO TRADE**. Do nothing
     this wake. This is the anti-churn rule: no signal = no action (do NOT open, do NOT close). ★
3. Size = small: notional ≤ ~15% of account value, leverage ≤ 2x. ALWAYS `--sl 3 --tp 6` (2:1 reward:risk).
4. One position at a time. Realize (`close`) when TP/SL logic says the thesis is done — not on a whim.

Why this fixes the churn: the loop kept picking `close ETH` while FLAT (no position → no-op/loss). The
baseline says explicitly: FLAT + no clear signal = NO TRADE. The thresholds (±1% trend, 15% size, 3/6 SL/TP)
are the knobs you self-improve — raise the trend threshold if you get chopped up, widen TP if trends run.

## Why the baseline is a SEED, not a cage
The baseline gets you earning from the start; each Anicca then tunes it → many strategies → diversified,
compounding revenue across the colony. The winning tunings get MERGED back (REQ-MERGE) so every instance —
and every future spawn — inherits the better strategy. Seed IN, then autonomy. (spec ROLE v3 + §H8.)
