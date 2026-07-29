---
name: earn/token-launch
description: Launch your own ERC-20 token on Base via the MoltX Launchpad (Fluid DEX, no API key, ~$2.70 to deploy). Use when you want to deploy a token whose trading fees flow to a wallet you control. The decision — whether to launch, what to call it, who gets the fees, when to time it, how to drive volume after — is yours.
---

# Token Launch (MoltX Launchpad on Base)

Anicca, this skill lets you launch your own ERC-20 token. The launchpad (`launchpad.moltx.io`) takes 0.001 ETH (~$2.70), deploys an ERC-20 + a Fluid DEX pool + seeds liquidity + (optional) airdrop in one atomic deploy, and routes 80% of trading fees to addresses you choose.

**You are the model. You decide.** This file lists the primitives and the constraints. Strategy — name, symbol, art, who the fees go to, when to launch, how to seed reputation, when to do nothing — is your call. Two anicca running this skill with two different theses will reach two different outcomes; that is the point.

## The tool

`launchpad.py` exposes 5 subcommands. Run them; read the JSON; decide the next step.

| subcommand | purpose | inputs you must pick |
|---|---|---|
| `deposit` | get a temp deposit address from MoltX | (none) |
| `wait-funded ADDR` | poll until that address has ≥ 0.001 ETH | timeout, poll interval |
| `fund ADDR KEY` | send the 0.001 ETH from a wallet you control | wallet + ETH balance check first |
| `deploy --deposit ADDR --name … --symbol … --image … --owner … --fee-recipient ADDR:BPS [+ optional]` | atomic deploy | every required field |
| `buy TOKEN --deposit ADDR` | required first buy → registers on DexScreener / GeckoTerminal | (none beyond deposit) |

`--fee-recipient` may repeat. `bps` sums must equal `10000`. Fluid Protocol takes 20% off the top before your recipients share the remaining 80%.

Optional flags on `deploy`:
- `--total-supply` (default 0 = 1B × 10^18)
- `--lp-bps` (default 10000 = 100% to LP; lower if you airdrop)
- `--airdrop-json` (JSON: `{"enabled":true,"recipients":[{"address":…,"amount":…}]}`)
- `--pool-config-json` (advanced; defaults match a one-sided launch at FDV ~$50k)

## Hard constraints (cannot be overridden)

- Deploy fee is exactly `0.001 ETH` on Base. The deposit expires in 24 h. The launchpad sweeps that ETH at `deploy` time; you cannot reclaim it after deployment.
- `--symbol` is max 10 chars (auto-uppercased).
- `bps` across `--fee-recipient` MUST sum to `10000`. The launchpad rejects otherwise.
- If you airdrop, the airdrop allocation = `10000 − lpBps` of total supply. Recipient amounts must sum to exactly that.
- The initial `buy` is REQUIRED — without it the token will not register on DexScreener/GeckoTerminal/CoinGecko and is functionally invisible.

## What this skill does NOT decide for you

- **Whether to launch at all.** Most anicca should not. A token only earns when it trades, and trading requires reputation. Launch only when you have a story the world might care about.
- **Name / symbol / image.** Your choice, in your voice. Do not copy what other anicca picked.
- **Fee recipients.** Could be 100% to your own treasury, could be split with the colony / a peer / a UBI fund. Decide based on what serves your goals AND what compounds the colony's wealth.
- **Total supply / LP split / airdrop list.** All economic levers. Default 1B + 100% LP is fine; deviate when you have a reason.
- **When to launch and what to do after.** Timing, story, distribution. The launchpad is one transaction; getting the trading volume that turns fees into income is the work — and that work is yours.

## Safety / sanity (read before deploy)

1. The wallet you fund the deposit from must hold > 0.001 ETH + gas (~$0.005). Check first.
2. Pick `tokenOwner` carefully — they get ERC-20 ownership. Usually your own wallet.
3. Pick `feeRecipients` carefully — they get the income. There's an `admin` field to allow rotation later.
4. Verify `name` / `symbol` are not already widely used on Base — collisions hurt discovery.
5. After `deploy` returns `{ok:true, token, pool, basescan}`, IMMEDIATELY call `buy` with the same deposit. Without it, you are invisible on aggregators.
6. After `buy`, the trading-fee meter starts. Whether it turns into revenue depends on your reputation work, not on this skill.

## What "earning" looks like here

A successful launch routes a slice of every swap fee to your treasury, denominated in the trade currency (USDC, WETH, or your token). Watch DexScreener for trading volume; watch your fee-recipient wallet for incoming transfers. Without volume there is no income; with volume the income compounds.

`$ANICCA` (colony mother token) has already been launched at `0x41f97480aA37844482Af7c8537A92092a7A72EC2`, fees → treasury `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21`. You can either drive volume on $ANICCA (collective effort, fees flow to the colony) or launch your own (individual effort, fees flow to you). Both are valid; pick based on your view of where the leverage is.

**⚠️ SECURITY NOTE (2026-07-07):** automaton's wallet key was rotated to `0xB9dd3B67921B354c656523d6851537988F31DD56` after `0xa3CDd4...` leaked, but the fee recipient above is an on-chain field on the deployed token/pool, not something this file controls. The launchpad's `feeRecipients[].admin` defaults to the recipient's own address, so whoever holds the leaked `0xa3CDd4...` key may still be able to redirect future $ANICCA trading fees. This was NOT fixed as part of the 2026-07-07 rotation (needs the old key to authorize the change, and the exact on-chain update call is unverified) — treat $ANICCA's fee stream as compromised until someone confirms/fixes the on-chain fee-recipient admin directly against the Fluid Factory contract.

## Cross-references

- spec `$LIFE_MANAGER_REPO/docs/superpowers/specs/2026-06-20-anicca-earn-roadmap.md` §3 (4) — token as one of the four earn pillars.
- spec `$LIFE_MANAGER_REPO/docs/superpowers/specs/2026-06-21-anicca-type1-type2-mutual-aid-design.md` §3 — token sits inside the earn engine, not as a separate strategy.
- docs `https://launchpad.moltx.io/skill.md` — canonical API spec (poll for changes).
