# pm-trade — Polymarket base agent + BASELINE ALPHA (W1 + #28)

> ## ⚠️ CLOB V2 (2026-04-28+) — READ FIRST. The V1 path below is DEAD.
> Polymarket moved to **CLOB V2**. Every V1 SDK is rejected with
> `400 invalid order version`. The **steel recipe** every AI must use now lives
> in **`v2_recipe.py`** (this dir) — verified constants + proven primitives:
> 1. **FUND** — `fund_with_relay(...)` swaps USDC on any chain → Polygon **pUSD**
>    (V2's only collateral, `0xC011a7E1…`). ✅ PROVEN live 2026-07-04 (Base $5→4.95 pUSD).
> 2. **DEPOSIT WALLET** — V2 accepts orders ONLY from a **registered deposit
>    wallet** (`signature_type=3` / POLY_1271, ERC-1167 proxy owned by your EOA).
>    A raw EOA (sig 0) and a Gnosis-Safe proxy (sig 2) are BOTH rejected with
>    `maker address not allowed, please use the deposit wallet flow`. One-time
>    onboarding at polymarket.com deploys+registers it. `ensure_deposit_wallet()`.
> 3. **TRADE** — BUYs go through `create_and_post_market_order` (FAK/FOK buys ARE
>    market orders in V2; the limit path fails `invalid amounts … max 2 decimals`).
> 4. **FEES** — `fee = rate·p·(1−p)·shares`, makers 0. Sources: py-clob-client-v2
>    issue #92 + crp4222/pmq war-story.md + installed py_clob_client_v2 1.0.2.
>
> ### ✅ THE NO-HUMAN PATH THAT WORKS (proven live 2026-07-04, browser=0, human-credentials=0)
> The full E2E is in `v2_mint_deploy.py` (SIWE→relayer key→deposit-wallet deploy) +
> `v2_full_flow.py` (approve→build→post a real order). Steps, all from the AI's OWN key:
> 1. **SIWE mint** (no browser): GET `gamma-api/nonce` → EIP-4361 `personal_sign`
>    ("Welcome to Polymarket! Sign to connect.") → GET `gamma-api/login`
>    `Authorization: Bearer base64(JSON(fields):::0xsig)` → cookies →
>    POST `relayer-v2/relayer/api/auth {}` → **RelayerApiKey {apiKey,address}**.
> 2. **Deploy deposit wallet** (gasless via relayer, EOA only signs):
>    `SecureClient.create(private_key, credentials=creds, api_key=RelayerApiKey(...))`
>    auto-derives (`derive_beacon_deposit_wallet_address`) + deploys the POLY_1271
>    (sig_type 3) wallet. Ours: `0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74`.
> 3. **Fund**: Relay any-chain USDC → Polygon pUSD → the deposit wallet.
> 4. **Approve** pUSD to ALL exchanges the market may use: standard `0xE111…`,
>    neg-risk `0xe2222…`, neg-risk-adapter `0xd91E80…` (World-Cup "Will X win" =
>    neg-risk → the neg-risk approve is REQUIRED or you get `allowance is not enough`).
> 5. **Trade**: `create_market_order(...)` builds a SignedOrder (maker=signer=deposit
>    wallet, sig_type 3); `post_order(order)` posts it. SDK = `polymarket-client`
>    (py-sdk). ⚠️ `py-clob-client-v2` (PyPI 1.0.2) is the DEAD one — do not use.
>
> ### BASE STRATEGY #1 — MARKET MAKING (`market_maker.py`, the swisstony $14M/$1.44B copy)
> Posts two-sided resting **post_only** maker limit orders (fee 0) near the book:
> BUY YES near bid + BUY NO near bid (YES+NO=1 → delta-neutral, capture spread), and
> on rewards-enabled markets harvests Polymarket's daily LP pool. LIVE-proven 2026-07-04:
> real resting maker order `0x73bee6545b10` (Argentina-WC YES 5@0.17, server status=live).
> ⚠️ **CLOB min order size = 5 shares** → two-sided on a ~$0.50 market needs ~$5; LP-reward
> eligibility needs `rewardsMinSize` ($100–1000). Earning scales with capital → this is
> the concrete, honest reason to fund ($20–50 for real two-sided MM + LP rewards).
>
> ### 💵 EARNINGS LEDGER (honest — real on-chain only)
> | date | engine | in | position / P&L | proof |
> |---|---|---|---|---|
> | 2026-07-04 | pm-v2 taker | ~$3 pUSD | 1.7857 sh "Morocco win" YES @0.5599 = $0.99 (open) | order `0xdad65538…` matched; settle tx `0x7662a88b6851d12a08e1f4dd0c020254cb9f96107e6ceea7dd92965639a4bfc3` (status 0x1) |
> | 2026-07-04 | pm-v2 maker(MM base) | 5 sh @0.17 = $0.85 | resting maker order | order `0x73bee6545b10` status=live |
> | 2026-07-04 | pm-v2 MM two-sided | 5 YES@0.56 + 5 NO@0.43 (Morocco) | delta-neutral, spread capture on fill | orders `0xcd75314cd7f1` + `0xc59559c7b84a` both status=live |
>
> ### 🔧 CAPITAL RECOVERY (2026-07-04): un-stuck \$10.93 via relayer transfer_erc20
> \$10.93 (USDC.e \$5.976 + pUSD \$4.951) was stranded in a wrong wallet (POLY_PROXY
> `0x3f06`, undeployed) set up before the sig-3 path was found. Recovered with
> `SecureClient._create(wallet=0x3f06, api_key=relayer) → transfer_erc20(→deposit wallet)`
> — the relayer deployed the proxy + swept both tokens gaslessly. Deposit wallet now
> holds pUSD 6.891 + USDC.e 5.976 (≈\$12.9 tradeable). Lesson: recover, don't abandon.
>
> ★ FIRST REAL no-human position placed. browser=0, human-credentials=0. The number
> moves only on real on-chain fills — this row is a verified settle tx, not a claim. ★


> ### ★★ DEPOSIT-WALLET REGISTRY GATE (2026-07-05, CONFIRMED root cause of "error resolving address") ★★
> A deposit wallet must be in **Polymarket's relayer WALLET REGISTRY** before any CLOB call works.
> Symptoms of an UNregistered wallet (all reproduced 2026-07-05, browser=0):
>   - `get_balance_allowance` / order → **`error resolving address`**
>   - `transfer_erc20` from it → **`wallet registry validation failed: wallet 0x… is not registered`**
>   - `create_or_derive_api_key` create-path 400 + derive has nothing → "the order signer address has
>     to be the address of the API KEY".
> Verified: automaton (0xa3CDd4) trades with the EXACT scripts that FAIL for Franklin (0x3EcCAD24) —
> same SDK, same wallet_type=DEPOSIT_WALLET/sig3, Franklin MORE funded ($5.95 > $4.95). The ONLY
> difference is registry membership. NOT the EOA age, NOT a browser (none used), NOT funding amount.
>
> ★ WHY #26/#27 born-with BROKE it: `ensure-polymarket-deposit-wallet.py` deployed the ERC-1167/1967
>   proxy on-chain via a raw/SIWE path, then I funded it by sending pUSD DIRECTLY to the deposit
>   wallet (POL→pUSD swap). That leaves the wallet **on-chain-deployed but NOT in the registry** — and
>   it can no longer be `WALLET-CREATE`d ("wallet already deployed"), so it is STUCK/unregisterable.
>
> ★ THE CORRECT REPEATABLE FLOW (docs: https://docs.polymarket.com/trading/deposit-wallets +
>   /trading/bridge/deposit). Registration is done by the RELAYER `WALLET-CREATE` **and/or by funding
>   THROUGH Polymarket's Collateral Onramp (the Bridge)** — NOT by a raw deploy + raw pUSD transfer:
>   1. Let the SDK create+register the deposit wallet on a FRESH EOA via `SecureClient.create(...)`
>      (runs `submit_deposit_wallet_create` = WALLET-CREATE). Do NOT pre-deploy the proxy yourself.
>   2. FUND THROUGH THE BRIDGE, not by a direct transfer: `POST https://bridge.polymarket.com/deposit
>      {"address": <deposit wallet>}` → returns per-chain bridge addresses (evm/svm/…) →
>      send **USDC / USDC.e** (a supported asset; Polygon USDC.e min $2) to the returned EVM bridge
>      address. The Collateral Onramp wraps it to pUSD, credits the deposit wallet, AND registers it.
>      (pUSD sent directly to the deposit wallet does NOT go through the onramp → no registration.)
>   3. Then `create_or_derive_api_key` (create-path succeeds for a fresh registered account), approve
>      pUSD FROM the deposit wallet via a relayer `WALLET` batch, and place orders with maker=signer=
>      deposit wallet, signature_type=3.
>
> ★ CONFIRMED WORKING 2026-07-05 (Franklin, a FRESH self-funded EOA, browser=0): (1) POST
>   bridge.polymarket.com/deposit {"address": deposit_wallet} → EVM bridge addr; (2) send pUSD (a
>   supported bridge asset, Polygon min $2) THROUGH that bridge addr (relayer transfer_erc20 from any
>   REGISTERED wallet — e.g. mutual-aid from automaton) → onramp status COMPLETED → deposit wallet
>   REGISTERED (get_balance_allowance resolves) and any previously-stuck direct-sent pUSD becomes
>   spendable; (3) approve pUSD to the NEG-RISK spenders `0xe2222d279d744050d28e00520010520000310F59`
>   (exchange) + `0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296` (adapter) — NOT `0x4bFb41d5…` (blocked,
>   not on the allowed list); (4) create_market_order FAK + post_order → matched. Franklin bought 3.284
>   sh "Amanda Janoo Vermont Gov YES" for $2, order 0x6fa9b74a…, settle tx 0x057511e7… status 0x1.
> Bake steps 1-2 into the spawn/born-with flow so every self-funded AI is REGISTERED at birth. Never
> raw-deploy the proxy or raw-transfer pUSD to it — that produces the stuck/unregistered state above.


The base agent [`BlockRunAI/polymarket-agent`](https://github.com/BlockRunAI/polymarket-agent) provides the
data/analysis modules this skill imports: market fetch, x402-paid AI analysis, smart-money/whale signals,
and Kelly sizing. ★ Its own `PolymarketAgent.execute_trades()` (`src/agent.py`) shipped as a STUB
(`status:"skipped", reason:"Token ID not available in simplified mode"`) — it recommended but never
actually traded. `run.sh` no longer calls `main.py --live` (that path is dead for this skill; the stub
never placed an order). ★

## ★★ run.sh NOW CHAINS THREE FAIL-CLOSED STRATEGIES PER PASS (#25, 2026-07-05) ★★
`run.sh` no longer calls `main.py --live`. It now runs, in order, after the identity/registration blocks:

1. **`bundle_arb.py`** — BASE STRATEGY #2, risk-free bundle arb scan. **EXISTING, working, unchanged** —
   this task did not rebuild it, only wired it into the firing loop. Self-gating: prints "no risk-free
   bundle arb ≥0.5% right now" and no-ops when the market is efficient; buys both legs (FOK) only on a
   real locked edge (`ask_YES + ask_NO + fees < $1`).
2. **`market_maker.py`** — BASE STRATEGY #1, maker-bundle quoting. **EXISTING, working, unchanged.**
   Self-gating: HOLDs ("cash < one min bundle") instead of spamming failed orders when underfunded; else
   cancel-and-replace resting post-only quotes (BUY YES@bid + BUY NO@bid, sum<0.995).
3. **`pick.py` → `place_order.py`** — the genuinely-missing piece this task built: an autonomous
   **directional** buy (neither arb nor market-making — a real edge/confidence call on ONE side of ONE
   market). Both are new files, both fail-closed. Details below.

Each strategy is independently self-gating/fail-closed (arb no-ops when efficient, MM holds when
underfunded, pick.py WAITs when no edge clears), so chaining all three in one pass is safe — worst case
several of them no-op in the same pass. Every pass appends one structured trace line per strategy to
`../state/pm-trade.trace.jsonl` (H1).

⚠️ `bundle_arb.py` / `market_maker.py` were NOT modified by this task (per spec: wire existing alpha, don't
reinvent it) — their sizing (up to ~90% of the deposit-wallet balance per pass) and hardcoded constants
(`FEE_RATE`, `EDGE`, `MIN_SIZE`, `MARGIN`) are pre-existing, already-verified-live risk parameters, separate
from the `MAX_BET_SIZE` cap that applies only to the new directional path (`pick.py`/`place_order.py`).
There is also a separate `run_earner.sh` (hardcoded single-instance paths, `.venv-pysdk`) that already
invokes `redeem.py` + `bundle_arb.py` + `market_maker.py` on its own schedule — if both it and this
skill's `run.sh` are scheduled for the same instance, they can fire the same self-gating strategies
concurrently; that's a pre-existing scheduling question (cron config), out of this file's scope.

### `pick.py` → `place_order.py` (the new directional-buy path)
Neither hardcodes a market or a side — the MODEL (multi-model consensus + smart-money signal) decides;
the code only filters/sizes/caps:

1. **`pick.py`** (ALPHA — imports the base agent's own modules, judgment stays with the model):
   - `fetch_active_markets(min_odds, max_odds, min_liquidity)` → candidates, re-sorted **resolve-soonest
     first** (primary key), volume desc (secondary); anything resolving beyond `RESOLVE_HORIZON_DAYS`
     (default 14) is dropped — this is the fix for "WC2026/election markets = payout months away".
   - For each candidate (capped by `MAX_CANDIDATES`, default 5, a cost bound not a judgment call):
     `get_smart_money_summary(market_id)` (whale/smart-money signal, async) is fed straight into
     `AIAnalyzer.consensus_analysis(question, yes_odds, whale_data=...)` — the 3-model consensus that was
     previously wired but never actually fed the whale data.
   - **GATE:** only acts when `abs(avg_edge) >= MIN_EDGE` (0.15) AND `avg_confidence >= MIN_CONF` (7) AND
     `consensus != "MIXED"`. Sizes with `KellyCriterion`, capped by `MAX_BET_SIZE` (default $2).
   - Emits **one line of JSON** on stdout: either a trade candidate
     (`token_id, side, outcome, amount, market, end_date, edge, confidence, consensus`) or, whenever
     nothing qualifies OR a signal is unavailable, `{"action":"WAIT","reason":...}` — **fail-closed, never
     a default bet.** Verified live 2026-07-05: read-only run correctly WAITed
     (`no-short-dated-liquid-candidates`) because the soonest real market resolved in 14.7 days, just past
     the 14-day horizon — proof the horizon filter is real, not decorative.
2. **`place_order.py`** (EXECUTION — the exact working V2 flow from `v2_full_flow.py`, generalized):
   reads `TOKEN_ID` / `SIDE` (BUY only) / `AMOUNT` from env (argv fallback), re-caps `AMOUNT<=MAX_BET_SIZE`
   again (defense in depth), then SecureClient sig-3 bootstrap → relayer-key mint (SIWE) → idempotent
   neg-risk approve → `get_order_book` → best ask → `create_market_order(..., order_type="FAK")` →
   `post_order`. Emits one line of JSON: `{token_id, amount, order_id, post_result, ok}`.

`run.sh` parses `pick.py`'s JSON: `WAIT` → append `{"action":"wait",...}` to the trace and exit 0
(no-churn); a trade candidate → export `TOKEN_ID/SIDE/AMOUNT` and run `place_order.py`, appending its
result to the trace either way. The identity-resolution block, `fund_via_bridge.py` registration step, and
kill-switch are unchanged (spec §2.3, §6 — those files were never touched).

## BASELINE ALPHA (legacy — `src/agent.py::generate_recommendations`, NOT the pm-trade run path)
The base agent's own `agent.py::generate_recommendations`/`main.py --live` path (documented below) still
exists in the agent's repo and is real (not the 0.55 stub), but **`run.sh` no longer calls it** — this
skill's trade path is `pick.py` → `place_order.py` above. Kept here for anyone driving the base agent
directly (outside this skill):
- for each liquid market (volume ≥ $10k, price 2–98%): call `analyzer.compare_market(question, market_price)`
  → the AI returns its own PROBABILITY + CONFIDENCE; edge = ai_prob − market_price.
- **BET GATE (the tunable knobs the AI self-improves):** only bet when `|edge| ≥ MIN_EDGE` (default 0.15)
  AND `confidence ≥ MIN_CONFIDENCE` (default 7/10). Side = YES if edge>0 else NO. Size = fractional Kelly.
- Nothing about WHICH market/side is hardcoded — only the discipline (high edge + high conviction).
Verified 2026-07-04: on 20 real markets the alpha produced genuine AI edges (Spain WC mkt12%/AI15%,
France mkt35%/AI30%…) and correctly placed 0 bets (no market cleared 15%-edge+conf7 = efficient market) —
vs the old stub which bet on everything.

This skill is otherwise a thin harness: run for real, record the trace, let the AI self-improve the knobs.
(SSOT: colony spec §0.25 + ROLE v3 "I create the baseline alpha, they self-improve from there".)

## Run

```bash
./run.sh    # one real live pass: bundle_arb.py -> market_maker.py -> pick.py -> (WAIT | place_order.py).
            # NO dry-run mode exists (HARD 0.24).
```

- Agent home: `~/.anicca-founder/agents/polymarket-agent` (override: `PM_TRADE_AGENT_HOME`).
- Fuel: `.env` in agent home — `BLOCKRUN_WALLET_KEY` (analysis, x402) +
  `POLYGON_WALLET_PRIVATE_KEY` — already provisioned.
  ⚠️ **Two different addresses, don't confuse them (verified live 2026-07-05, both `eth_account` and
  `viem` independently derive the same result):**
  - `POLYGON_WALLET_PRIVATE_KEY` is the **owner EOA** `0x810F6D61F7606dEEE2657d3083E150a222Bc29C5` — it
    only SIGNS orders (POLY_1271 / `signature_type=3`); it does not itself hold the tradeable balance,
    and this same key doubles as the unrelated `ai.anicca.founder-loop` instance's own low-balance
    identity wallet (colony spec §25) — a coincidence of both living under `~/.anicca-founder`, not a
    typo.
  - The **deposit wallet** `0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74` (line above, "Ours:") is the
    ERC-1167 proxy the EOA owns/signs for — THIS is the maker/signer of record on every order, the
    address that holds pUSD/USDC.e, and the one colony-status.sh / the dashboard track as claude-p's PM
    wallet. If you're looking up "claude-p's PM balance" on-chain, look up `0x904B50d2…`, not `0x810f…`.
- Funds live on Polygon: USDC.e (bankroll) + POL (gas). Seeded 2026-07-04 via LiFi bridge from Base.

## Money-safety guards (the ONLY thing this wrapper adds)

| Guard | How |
|---|---|
| kill-switch | `touch KILL` in this dir → next run exits without trading (before any of the 3 strategies run). `rm KILL` to resume |
| per-trade cap (directional path) | `pick.py` Kelly-sizes + caps by `MAX_BET_SIZE` (default $2); `place_order.py` re-caps `AMOUNT<=MAX_BET_SIZE` again |
| per-trade risk (arb/maker paths) | `bundle_arb.py` / `market_maker.py`'s own pre-existing constants (`FEE_RATE`, `EDGE`, `MIN_SIZE`, `MARGIN`) — unchanged by this task |
| no dry-run | not provided, by design — a run is always real |

## Trace (self-observe, H1)

Every pass appends one structured JSON line per strategy to `../state/pm-trade.trace.jsonl`:
- `{ts, slot, action:"bundle-arb"|"market-maker", exit, output_tail}` for the two existing strategies.
- `{ts, slot, action:"wait", reason}` when `pick.py` found no qualifying directional candidate.
- `{ts, slot, action:"trade", market, end_date, edge, confidence, consensus, exit, order}` when
  `place_order.py` executed a directional buy.
The self-improvement loop reads this.

## If a run errors (self-heal, H4)

You — the running agent reading this — fix it yourself: read the traceback. For the directional path,
edit `pick.py`/`place_order.py` in this skill dir, or the base agent's `src/` modules they import from
`$PM_TRADE_AGENT_HOME` if the fetch/analysis itself is broken. For the arb/maker paths, `bundle_arb.py` /
`market_maker.py` are unchanged from their proven-live form — fix a genuine bug, don't touch their risk
constants to force a trade. Re-run until the pass completes. Do NOT change any strategy's thresholds or
sizing to force a trade; "WAIT because my edge criterion wasn't met" / "no arb right now" / "HOLD, cash
too low" are all CORRECT outcomes.
Known past fixes (bootstrap, 2026-07-04): Gamma API returns numeric fields as strings (normalized in
`src/market/polymarket.py::_to_float`); dead default RPC replaced with `POLYGON_RPC_URL` env
(default `polygon-bor-rpc.publicnode.com`); `agent.py` passed a wallet object where the executor needs
`wallet.private_key`.
