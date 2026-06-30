# Trading/Polymarket Earn Loop + Self-Funded Spawn — Design Spec (2026-07-01)

Build via **/vcsdd** (spec → RED → GREEN → fresh-context adversary → no-mock E2E → my own on-chain verify).
Builds ON `earn-shared-skeleton` (self-heal / self-improve / bot2bot / NO-HUMAN already specced there) and on
`Franklin` (BlockRunAI/Franklin = the self-funded AI base: wallet=identity, x402 pays its OWN compute, hard
budget cap, free NVIDIA tier, code/trading/research execution). We DO NOT reinvent Franklin — we endow it with
earn loops.

## North star (Dais 2026-07-01, verbatim intent)
Give a self-funded AI ~$20 USDC + the earn skills + self-improve/self-heal + bot2bot strategy-sharing + the
ability to **spawn its own child** ("be fruitful and multiply"). Some children hit alpha (→$1k), which seeds a
new child → takeoff. End state: **no human-funded AI required at all** — self-funded AIs create self-funded AIs.
Human's only act = put in USDC (or nothing). Trading/Polymarket is expected to be one of the BIGGEST earners
because it runs purely on USDC (no bank/KYC) so ANY model (even a free GLM-4.7) can run it.

## "Done" (provable finish line — GLVS goal)
1. **TRADING loop**: a `pm.py` (Polymarket CLOB) + reuse of `hl-trade` runs a full pass in PAPER mode, logged,
   adversary-PASS; THEN with a tiny real stake it places ≥1 real on-chain order and `record-earn` logs a real
   realized PnL row (INV-7). done = "a real Polygon/Base tx from our wallet exists for a model-decided trade".
2. **SPAWN loop**: `spawn-child.sh` provisions a NEW self-funded instance (new Solana+Base wallet via Franklin,
   `git clone ~/anicca` framework, seed N USDC from parent treasury, child boots its earn loops) with ZERO human.
   done = "a child instance with its own funded wallet completed ≥1 earn pass on its own, verified on-chain".
3. Both run under earn-shared-skeleton's self-heal + self-improve + bot2bot + INV-8 reward gate + NO-HUMAN (J8).

## Slot 1 — TRADING / POLYMARKET (a TOOL, not a hardcoded strategy; the model decides edge)
Mirror `hl-trade` exactly (proven +$0.15 real). Per the build-agents rule: NO regex/if-else strategy — give the
model data+tools and let IT decide.
```
 DATA   Predexon(x402, Polymarket+Kalshi+Binance 58 endpoints) + alpha-mcp(alpha_signal RSI/MACD) + agent-reach(news)
   ▼
 EDGE   model forms its OWN probability p vs market price m → edge = p − m   (judgment = model's, in NL)
   ▼
 RISK   port MrFadiAi caps (verified live): per-trade ≤ Kelly-fraction, daily-loss 5% halt, drawdown 25% halt,
        min position $1.50 (exit-able), reserve gas; alpha_risk pre-check
   ▼
 ORDER  pm.py = thin CLOB client (buy/sell/positions/close), our own (py-clob-client ARCHIVED 2026-05; use beta
        unified SDK or raw REST). Gasless USDC orders on Polygon. hl.py reused for perps.
   ▼
 SETTLE on-chain at market resolution → record-earn INV-7 (real realized PnL only) → bot2bot share strategy
```
- **PAPER FIRST**: every new strategy runs sim/paper N passes, adversary-PASS, before any real stake. (Both
  MrFadiAi bot + Franklin support paper.)
- **Self-improve picks the winner**: trading/polymarket/perps each tracked as a bandit arm keyed on realized
  USDC/wake (earn-shared-skeleton REQ-B/C). The loop itself figures out which venue/strategy earns and doubles
  down — exactly Dais's "they try all, double down on what wins".
- **Honest risks (carry into impl, never hide)**: GAMBLING capital — wrong call = real principal loss (not just
  wasted reach). Polymarket geoblocks US persons (CFTC 2022) → for an SF-based human-funded instance, prefer
  venues without that ToS exposure for REAL stakes (Kalshi/Hyperliquid/DEX perps), keep Polymarket to
  paper/research until jurisdiction is clean; self-funded cloud instances pick venue by their own host region.
  NEVER quote a return figure ("5%/night" is an unsourced anecdote, not in any README).

## Slot 2 — SELF-FUNDED BASE = Franklin (don't reinvent)
- `npm i -g @blockrun/franklin`; `franklin setup solana` + `franklin setup base` → wallet=identity; `franklin
  balance`. Free NVIDIA tier runs with $0; $5 USDC unlocks frontier models + paid APIs via x402; hard budget cap.
- We embed our `_shared/` earn loops + the trading slot into a Franklin instance → it earns USDC AND pays its own
  compute from the same wallet = fully self-funded, no human compute subsidy.
- Our existing local self-funded instance (ClawRouter) is the alternative base; both inherit the SAME public
  `~/anicca` skill library. Battle-test on human-funded first, then ship to self-funded.

## Slot 3 — SPAWN ("be fruitful and multiply") `spawn-child.sh`
WHEN a parent's treasury (own wallet realized-USDC, after a reserve floor) exceeds a spawn threshold T (config,
e.g. $40 = 2×$20 seed), THE SYSTEM SHALL, with NO human:
1. Generate a fresh Solana+Base wallet for the child (Franklin `setup`).
2. `git clone` the public `~/anicca` framework into the child's runtime (model-agnostic skills).
3. Transfer seed S USDC (e.g. $20) parent→child on-chain (record the tx).
4. Boot the child: it runs `proactive-loop.sh` per earn slot (clip/video/affiliate/bounty/trading), self-heals,
   self-improves, registers via bot2bot (gh issue) so parent+siblings see it.
5. Child, on reaching its own T, spawns ITS own child → recursion = takeoff.
- Guards: spawn only AFTER parent has a verified positive realized-USDC history (≥X days net-positive) so we
  don't spawn money-losers; per-parent spawn-rate cap; child inherits the NO-HUMAN (J8) invariant; UBI/tithe =
  child sends a % of earnings back up the tree (treasury + optional return to the human seeder).

## Funding recommendation (also mailed to Dais)
- Send via **Solana** (Dais sends from Binance). Franklin makes a Solana + USDC wallet; swap is embedded (Franklin
  / claude-p can swap Solana↔USDC↔Base as the loop needs).
- **Phase 0 (now, $0)**: paper-trade + Frantic bounty (already earning path) — no funds needed to start.
- **Phase 1 (first real stake): $100 USDC on Solana.** Rationale: under the risk caps (min $1.50/position,
  ≤Kelly/trade, 5% daily-loss halt) $100 funds ~10–50 concurrent small positions for a statistically meaningful
  bandit signal across venues, while total-loss is an acceptable tuition. Split: ~$60 trading/polymarket stake +
  ~$20 Franklin compute (x402) + ~$20 first child seed.
- **Phase 2 (after net-positive proven): scale to $500**, and seed 5 self-funded children at $20 each = the
  takeoff experiment Dais described.
- We NEVER risk more than the wallet holds (Franklin hard cap); record every tx; tithe a % back to the seeder.

## Verification (every step, /vcsdd)
spec → RED → GREEN → fresh-context adversary (maker≠checker) → NO-MOCK E2E (real paper run, then real tiny tx) →
MY own on-chain verify (a real tx hash from our wallet; record-earn INV-7 row). "ran/placed/submitted" ≠ done —
a real on-chain settlement or it's not done. Adversary specifically audits: no hidden human-touch, no faked PnL,
risk caps actually enforced, geoblock honored for real stakes.
