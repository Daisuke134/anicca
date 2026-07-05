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


> ### ★★ NEW-EOA ONBOARDING GATE (2026-07-05, root cause of "error resolving address") ★★
> A BRAND-NEW EOA cannot trade on Polymarket CLOB until Polymarket's backend KNOWS it.
> The CLOB derives the funder (deposit wallet) from the *authenticated EOA* + signature_type;
> if the EOA was never onboarded, `get_balance_allowance` / `post_order` return
> **`error resolving address`** (and `create_or_derive_api_key` has nothing to derive →
> "the order signer address has to be the address of the API KEY"). Verified 2026-07-05:
> automaton (old EOA 0xa3CDd4, onboarded in a prior session) trades with the EXACT same
> scripts that FAIL for Franklin (fresh EOA 0x3EcCAD24 minted by #26). Deploy method,
> wallet_type (DEPOSIT_WALLET/sig3), funding ($5.95 > automaton's $4.95) are all IDENTICAL —
> the only difference is backend registration of the EOA. Source: Polymarket/py-clob-client-v2
> issues #70/#77/#87/#91 (crp4222, running in production) + our own A/B on identical scripts.
>
> ★ THE REPEATABLE FIX (must run ONCE per fresh instance EOA, human-zero): onboard the EOA to
>   Polymarket so the backend registers the EOA↔deposit-wallet pair. crp4222's verified recipe:
>   "if the wallet never touched the app, log in with it and do ONE manual action, then derive
>   again." Practically = drive polymarket.com in CloakBrowser with THIS instance's EOA
>   (connect wallet → the app deploys+registers the sig-3 deposit wallet) ONCE, before any API
>   trade. Bake this onboarding step into the spawn/born-with flow so every self-funded AI is
>   registered at birth. Until then, a fresh instance funds fine but cannot place CLOB orders.


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
