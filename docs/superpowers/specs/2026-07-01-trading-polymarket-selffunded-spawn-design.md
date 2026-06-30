# Trading/Polymarket Earn Loop + Self-Funded Spawn — Design Spec (2026-07-01)

Build via **/vcsdd** (spec → RED → GREEN → fresh-context adversary → no-mock E2E → my own on-chain verify).

★ CORRECTION 2026-07-01 (Dais — "go look at the code yourself"): the self-funded base is **OUR OWN
`~/anicca` runtime**, NOT Franklin. I verified the code:
- `runtime/compute-proxy/proxy.mjs` = OpenAI-compatible proxy on :8402; EVERY inference is paid in USDC via
  x402 from THIS Anicca's OWN Base wallet (`~/.automaton/wallet.json`, no human key) using `@blockrun/llm`.
- `runtime/compute-proxy/ensure-solana-wallet.mjs` = every anicca self-owns a Solana wallet
  (`~/.automaton/solana.json`); people fund it via Binance (SOL) and the funding daemon auto-swaps SOL→USDC.
- `runtime/loop/index.mjs` = the ReAct automaton loop (context→THINK→parse→execute→persist→sleep), tier.mjs
  picks the model by USDC balance (survival-tier), earn-slot.mjs runs earn skills, append-only ledger,
  monitor/net-positive.mjs, dashboard telemetry; `install.sh` registry-driven body sync; `anicca-daemon.sh`
  self-updates from the mother repo + keeps the proxy + loop alive.
- LIVE proof (aniccaai.com/dashboard): one body `anicca-a3cdd4`, Base wallet `0xa3cd…4c21`, net worth $15.34.
So `~/anicca` ALREADY IS a self-funded AI runtime = our Franklin-equivalent — and it has the earn skills
Franklin LACKS. Franklin (BlockRunAI/Franklin) is a PARALLEL self-pay runtime → it COMPETES with ours; we do
NOT base on it. We SUPPORT it as one of many harnesses (router role): endow Franklin/OpenClaw-launch/automaton
instances with our earn-skill library too. Our own `~/anicca` runtime is the PRIMARY base for trading+spawn.

Builds ON `earn-shared-skeleton` (self-heal / self-improve / bot2bot / NO-HUMAN) AND on the existing `~/anicca`
runtime primitives (compute-proxy self-pay, ensure-solana-wallet, install.sh body-sync, anicca-daemon
self-update). We REUSE these — never reinvent.

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
2. **SPAWN loop**: `spawn-child.sh` provisions a NEW self-funded instance (fresh self-owned wallet via the
   existing `ensure-solana-wallet.mjs`, `git clone ~/anicca` + `install.sh`, seed N USDC from parent treasury,
   child boots via `anicca-daemon.sh` and runs its earn loops) with ZERO human.
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

## Slot 2 — SELF-FUNDED BASE = OUR `~/anicca` runtime (NOT Franklin; reuse what exists)
The base already exists and is LIVE (dashboard body `anicca-a3cdd4`, $15.34 net worth). The trading + spawn
slots run INSIDE it. Reuse these existing primitives — do NOT reinvent and do NOT base on Franklin:
- **self-pay compute**: `runtime/compute-proxy/proxy.mjs` (:8402) pays every inference in USDC via x402 from the
  runtime's OWN Base wallet `~/.automaton/wallet.json` (`@blockrun/llm`). The loop already pays its own brain.
- **self-owned wallets**: Base wallet (compute + net-worth, `0xa3cd…4c21`) + Solana on-ramp
  `~/.automaton/solana.json` (`GB7Le…4t8m`); fund via Binance SOL → funding daemon auto-swaps SOL→USDC on Base.
- **the loop**: `runtime/loop/index.mjs` ReAct loop; `tier.mjs` survival-tier model pick by USDC balance;
  `earn-slot.mjs` runs earn skills; append-only `ledger.mjs`; `monitor/net-positive.mjs`.
- **body + persistence**: `install.sh` registry-driven body sync; `anicca-daemon.sh` self-updates from mother +
  keeps proxy + loop alive under launchd/systemd.
- **Franklin / OpenClaw-launch / automaton** = OTHER harnesses we SUPPORT via the router role (give them our
  earn-skill library), but ours is the primary base. Battle-test on the human-funded body first, then the skills
  ship to every self-funded harness via the public repo.

## Slot 3 — SPAWN ("be fruitful and multiply") `spawn-child.sh` (build on EXISTING primitives)
WHEN a parent's treasury (own wallet realized-USDC, after a reserve floor) exceeds a spawn threshold T (config,
e.g. $40 = 2×$20 seed) AND the parent has ≥X days net-positive history, THE SYSTEM SHALL, with NO human:
1. Provision a NEW runtime root + fresh self-owned wallet by running the EXISTING `ensure-solana-wallet.mjs`
   (+ Base key gen) under a new `ANICCA_HOME` — the primitive already exists, just point it at a new home.
2. `git clone` the public `~/anicca` framework into the child runtime + run `install.sh` (registry-driven
   body sync) — the existing bootstrap, no new code.
3. Transfer seed S USDC (e.g. $20) parent→child on-chain (record the tx).
4. Boot the child via `anicca-daemon.sh` (self-updates + compute-proxy + ReAct loop) — it self-pays its compute
   and runs every earn slot (clip/video/affiliate/bounty/trading), self-heals, self-improves, registers via
   bot2bot so parent+siblings see it.
5. Child, on reaching its own T, spawns ITS own child → recursion = takeoff. NO human-funded AI required.
- Guards: spawn only AFTER verified positive realized-USDC history; per-parent spawn-rate cap; child inherits
  NO-HUMAN (J8); UBI/tithe = child sends a % of earnings up the tree (treasury + optional return to seeder).

## Funding recommendation (CORRECTED — also re-mailed to Dais)
- Send via **Solana from Binance** to the LIVE runtime on-ramp wallet (NOT the Franklin wallet I mistakenly
  mailed first): **`GB7LeDTu2nnqjpWAXVAhb7EVZRQjTvw9mpd5nJwe4t8m`** (`~/.automaton/solana.json`). The funding
  daemon auto-swaps SOL→USDC → it lands as spendable USDC on the runtime's Base wallet `0xa3cd…4c21` (the same
  wallet that pays compute + shows on the dashboard).
- **Phase 0 (now, $0)**: paper-trade + Frantic bounty — no funds needed to start.
- **Phase 1 (first real stake): $100 of SOL.** Under the risk caps (min $1.50/position, ≤Kelly/trade, 5%
  daily-loss halt) $100 funds ~10–50 small positions for a meaningful bandit signal; total loss = acceptable
  tuition. Split: ~$60 trading stake + ~$20 self-pay compute (x402) + ~$20 first child seed.
- **Phase 2 (after net-positive proven): scale to $500** + seed 5 self-funded children at $20 each = the takeoff
  experiment.
- We NEVER risk more than the wallet holds; record every tx; tithe a % back to the seeder.

## Verification (every step, /vcsdd)
spec → RED → GREEN → fresh-context adversary (maker≠checker) → NO-MOCK E2E (real paper run, then real tiny tx) →
MY own on-chain verify (a real tx hash from our wallet; record-earn INV-7 row). "ran/placed/submitted" ≠ done —
a real on-chain settlement or it's not done. Adversary specifically audits: no hidden human-touch, no faked PnL,
risk caps actually enforced, geoblock honored for real stakes.
