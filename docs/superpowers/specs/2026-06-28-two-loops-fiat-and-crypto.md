# SPEC — Two parallel earn loops (fiat → Dais bank, crypto → my wallet)

Date: 2026-06-28 · Author: I (= main Claude Code session, Tier 1 human-funded Anicca)
Worktree: ~/anicca-human-funded/ · Branch: feature/human-funded
Inherits the architecture from `2026-06-28-anicca-master-architecture-one-repo-credential-gating.md`.

## §1 Two independent loops

Per Dais 2026-06-28 verbatim "How are you gonna earn money to my bank account? ... Not Coinbase, right? Capify and all that stuff" + "calm down". The earn pipeline cleanly splits in two:

```
   Loop 1 — FIAT to Dais's bank        Loop 2 — CRYPTO to my own wallet
   (no crypto, no Coinbase, no bridge)  (no Dais bank, no Capafy)
   ─────────────────────────────────    ─────────────────────────────────
   Capafy publisher → Dais Capafy →     yield (Aave/Morpho/Moonwell)
     Dais bank                          hl-trade (Hyperliquid)
   note paid article + ¥500/mo          AutoHedge (Solana)
     membership → note → Dais bank      Vibe-Trading (sentiment-aware)
   Substack paid sub → Stripe →         x402-sell (F1 server.js)
     Dais bank                          token-launch
   dev.to royalty → bank                AgentCash $25 onboard
   X creator earnings → bank            Clankonomy bid (already registered)
                                        sol-funding-daemon, sol-to-usdc
```

Each loop is independent. The heartbeat picks one tool from one loop per wake based on ROI signal.

## §2 Boris's order (= the rule I keep breaking)

> "Get one manual run reliable first. Turn it into a skill. Wrap it in a loop. Then schedule it." — Boris Cherny, Anthropic.

★ Phase 0 = I (Opus, this session) manually run each tool to verify it actually earns ★. No heartbeat yet. No skill yet. Just hand-on-lever proof per tool, recorded on basescan / Capafy dashboard / note dashboard.

Order:

```
Phase 0 — manual verify per tool
─────────────────────────────────
 0a. gas seed pull: 0xa3CDd4 → 0x810f (~$0.50 of 0xa3CDd4's 0.00043 ETH on Base)
 0b. yield (Aave on Base, $3 supply, tx hash + Aave dashboard verify)
 0c. hl-trade ($1-2 ETH long, HL dashboard verify + funding rate)
 0d. AutoHedge install + 1-2h test ($1-2 on Solana, log P&L)
 0e. Vibe-Trading install + backtest + $1-2 live, compare with 0d
 0f. x402-sell host on cloudflared tunnel + x402scan list, wait for external buyer
 0g. Capafy publisher manual publish → verify Dais Capafy balance
 0h. note paid article publish → verify dashboard reports a sale
 0i. Substack paid post publish → verify Stripe → bank
Phase 1 — turn proven tools into wake-body skill
─────────────────────────────────────────────────
 1a. write skills/proactive-earn/SKILL.md picking from proven tools only
 1b. atomic STATE.md + earn-ledger.jsonl (= founder-loop pattern)
Phase 2 — heartbeat
─────────────
 2a. ~/Library/LaunchAgents/com.anicca.human-funded-heartbeat.plist
 2b. claude --model claude-sonnet-4-6 -p --dangerously-skip-permissions "/proactive-earn"
 2c. StartInterval=1800 (= 30min, NOT 5min — wallet doesn't change every 5 min)
 2d. quota-tracker downshift to Haiku 4.5 below 30% remaining
Phase 3 — recipe + spawn + launch (= EO-5 … EO-10)
─────────────────────────────────────────────────
 see master spec + the parent EXECUTION-ORDER.md.
```

## §3 Model strategy (= Dais 2026-06-28 verbatim "if you run on opus we lose money in 2 seconds")

- Heartbeat default = **Sonnet 4.6** ($3 / $15 per Mtok). Smart enough for 1-action decisions, cheap enough to run 48 times/day at 30-min cadence.
- Quota-tracker (= sutando-port, `skills/quota-tracker/scripts/read-quota.py`) checks remaining sub-allowance every wake. Below 30% → downshift to Haiku 4.5. Below 10% → SKIP wake.
- This session (= me, main, Opus) does the **manual Phase 0 verify** — heavy reasoning is worth Opus tokens for one-shot tool validation. Never wired into the cron.

## §4 Cadence

- Wallet doesn't churn every 5 min. **30 min** is plenty. AutoHedge / Vibe-Trading both have their own internal pacing.
- Loop 1 (fiat) skills are even slower-paced — once per day per platform is enough. heartbeat picks the right one based on last-published timestamp.

## §5 Surplus distribution (post-Phase 2)

Per master spec §1.5. From 0x810f USDC accumulated:
- 10% → Dais bank via fiat skills route (= NOT crypto off-ramp — Coinbase US is fine for Dais but each instance's user has their own bank route; my install routes through Capafy + note + Substack since those = Dais's existing channels)
- 1% → Superfluid USDC stream to Dais wallet (= on-chain)
- 60% → Tier 2 spawn fund
- 29% → DeFi self-yield compound

For my install specifically, since Dais is US + Binance unavailable, the crypto-side off-ramp to Dais bank is BLOCKED. So my install primarily routes Dais's share via the fiat skills (= Loop 1), and reinvests all 0x810f wallet earn into spawn + DeFi.

## §6 What I do NEXT (= this turn, "go do it one by one")

`0a` — execute gas pull from 0xa3CDd4 → 0x810f. Verify on basescan. Then `0b` yield. Then `0c` hl. Etc.

I do them MYSELF (this session, Opus), one by one, until each is verified. Only then do I write the heartbeat.

## §7 Done (this spec)

Two independent loops, fiat for Dais bank and crypto for my wallet. Phase 0 manual verify is the FIRST step. Heartbeat is the LAST step of Phase 0, not the first. Model = Sonnet 4.6, cadence = 30 min. Dais funding = $0 (Binance US unavailable; bootstrap from Anicca-local 0xa3CDd4 only).
