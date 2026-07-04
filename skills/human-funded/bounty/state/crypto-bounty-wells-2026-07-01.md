# Crypto Bounty Wells — live probe 2026-07-01

GOAL: bounty/task platforms where an AUTONOMOUS AI earns CRYPTO to its OWN wallet,
NO GitHub account required (identity = wallet or self-creatable web/Farcaster handle),
REAL (not scam), with OPEN funded work NOW. Excludes ClawTasks + clones (Dais: dead/scam).

Method = actually fetched each (curl API + firecrawl page + GraphQL probe + playwright attempt).
Nothing below is invented — every count is from a real response captured this run.

## RANKED TABLE (sorted by real doable crypto money open NOW with NO GitHub)

| # | Platform | ALIVE? (probe) | #open funded NOW | currency / chain | identity needed | agent-doable? | scam signal | payout proof |
|---|----------|----------------|------------------|------------------|-----------------|---------------|-------------|--------------|
| 1 | **Dework** (api.deworkxyz.com) | ✅ VERIFIED — GraphQL `getTasks(statuses:["TODO"])` returned **1045** open tasks live | **184 w/ crypto reward** (of which ~30 USDC, ~18 USDT, 2 ETH; 115 = HENKAKU community token) | USDC/USDT/ETH/MATIC/DAI on Polygon, Ethereum, Optimism, Solana, BSC, Avax | **Wallet-connect OR Discord — NO GitHub** | Partial — real content/translation/X-thread/research USDC tasks exist | MEDIUM — many MLM-ish "referral/KOL/affiliate/recruitment" tasks; many stale (2025 dates); weak curation | Real DAO history; on-chain token rewards attached to tasks |
| 2 | **Bountycaster** (bountycaster.xyz) | ✅ ALIVE — sitemap lastmod 2026-04-19; homepage counters **$1.5M / 2,967 bounties**; leaderboard shows real recent Farcaster posters | ❓ **could not count** — listings render client-side behind Privy/Farcaster auth (no browser binary avail, disk too tight to install) | **USDC / ETH / DEGEN** to wallet (Base) | **Farcaster account + wallet — NO GitHub** | Yes — research/content/dev micro-bounties | LOW — public Farcaster ledger, named posters, real $ totals | Public completed-leaderboard ($44k, $32.5k posters etc.) |
| 3 | **LaborX** (laborx.com) | ✅ ALIVE — /jobs + full category tree render | ❓ count not extractable (JS-rendered, no public read API found) | USDT/USDC + others, escrow | **Email / wallet — NO GitHub** | Yes — writing/translation/dev gigs | LOW — registered trademark, escrow, long history | Known live escrow rail (prior memory) |
| 4 | **Questbook** (questbook.app) | ✅ ALIVE — homepage "$10M+ paid, 60K builders, 7K proposals"; live programs Arbitrum/Compound/ENS/TON/Fetch.AI/Axelar | GRANTS not micro-bounties; per-DAO programs (count varies) | crypto (per DAO) | **Wallet — NO GitHub** | Partial — proposal writing + milestone delivery | LOW — named blue-chip DAOs | $10M+ paid-out counter |
| 5 | **abillio** (abill.io) | ✅ ALIVE (200) | n/a — it's a payout/invoice RAIL, not a board | invoice → USDC (Solana) | email/KYC | n/a (rail) | LOW | known rail |
| 6 | **Layer3** (layer3.xyz) | ✅ ALIVE | engagement quests only (CUBEs/airdrops) — NOT funded work | points/airdrop spec | wallet | No (farming, not paid work) | n/a (not real work) | — |
| 7 | **Galxe** (galxe.com) | ✅ ALIVE (301→app) | engagement quests only | points/airdrop | wallet | No | n/a | — |
| 8 | **TalentLayer** (talentlayer.org) | ⚠️ PARTIAL — .org 200 but **app.talentlayer.org DEAD (000)** | 0 usable | — | wallet | No live board | protocol/SDK only, no inventory | — |
| 9 | **Wonderverse** (wonderverse.xyz) | ❌ DEAD — 302 redirect/parked | 0 | — | — | No | abandoned | — |
| 10 | **Charmverse** (app.charmverse.io) | ❌ DEAD — DNS resolution fails | 0 | — | — | No | pivoted away from bounties | — |
| 11 | **Moltbook** (moltbook.com / .ai) | ⚠️ NOT A BOUNTY BOARD — .com = social network FOR AI agents (Reddit-style); .ai = domain **for sale $100k** | 0 | — | — | No | not an earn rail | — |
| 12 | **Claw Earn** (clawearn.com) | ⚠️ 200 but firecrawl-blocked; **Claw* ecosystem = EXCLUDED by Dais** (ClawTasks + clones); prior memory = 0 open | 0 (excluded) | Base USDC | wallet-sig | (excluded) | EXCLUDED per Dais | — |

## TOP 1-3 TO WIRE INTO THE WALLET-NATIVE BOUNTY LOOP

1. **Dework — wire FIRST.** Only platform with a VERIFIED live count this run and a
   read API that needs NO auth: `POST https://api.deworkxyz.com/graphql`
   `query($f:GetTasksInput!){ getTasks(input:$f){ id name status rewards{ amount peggedToUsd token{ symbol network{ name } } } } }`
   with `{"f":{"statuses":["TODO"]}}`. Filter `rewards[].token.symbol ∈ {USDC,USDT,ETH,DAI}`
   to skip the 115 HENKAKU/community-token noise → ~50 real-money open tasks.
   - HONEST BLOCKER: claiming/submitting a task needs an authed Dework account
     (wallet-connect or Discord) + the org must approve you as a contributor; many
     listings are stale or MLM-flavored, so the loop must score for freshness +
     legitimacy before bidding. Reading is open; earning needs the auth + approval step.

2. **Bountycaster — wire SECOND.** Best identity fit (Farcaster + wallet, USDC/ETH/DEGEN
   on Base, zero GitHub) and demonstrably alive/recent.
   - HONEST BLOCKER: claiming a bounty = replying to a Farcaster cast, which needs a
     Farcaster FID (small onchain registration fee or a Neynar managed signer) AND a
     way to count/scan open bounties (data is behind Privy/Farcaster-auth client render —
     this run could not server-side count it; need a Farcaster hub query or an authed
     headless browser). Set up the FID + signer once, then it's a clean wallet-native loop.

3. **LaborX — wire THIRD (fallback fiat-ish crypto gigs).** Real escrow, no GitHub,
   email/wallet identity.
   - HONEST BLOCKER: bid-based + client-selection (slower than claim-based bounties);
     no public read API found this run, so inventory scanning needs an authed session
     or HTML render.

## DEAD / NOT-USABLE (do not retry)
TalentLayer app (dead), Wonderverse (parked), Charmverse (DNS dead), Moltbook (not a board),
Claw Earn / ClawTasks ecosystem (Dais-excluded), Layer3 + Galxe (engagement quests, not paid work).

## VERIFICATION GAPS (honesty)
- Bountycaster & LaborX exact OPEN counts NOT obtained — JS/auth-gated; no chromium binary
  installed (data volume at 95%, 9.9 GB free → skipped browser install per disk-hygiene rule).
  Both are confirmed ALIVE by other evidence, but the live count is unverified.
- Dework count IS verified (raw GraphQL response, 1045 TODO / 184 rewarded captured this run).
