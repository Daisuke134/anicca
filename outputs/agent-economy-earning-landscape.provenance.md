# Provenance: Agent Economy earning landscape

| Source | Fixed revision / observation | Used for |
|---|---|---|
| `NSPG13/agent-bounties` | `4ce44ee5c917177d50300b1c2101e269ce18e6e7` | Claim API, sponsorship, escrow and settlement semantics |
| Agent Bounties live feed | Observed `2026-08-28T00:04:02Z`; readiness safe block `50542796`; response SHA-256 `af209cecd9f373ab33b62490d7e32dc41a11986a9fcad382c41f6192d5dae651`; contract `0x22cec92c195a6dc0f7aeaf850e7f2cacb3b6de33`; terms hash `0x7fbbc478f0fcf6306cd8dddd1b9ef9ae8007568aeaad9d1973ad0b0ee28f8607` | Current inventory, funding, reward, bond, event history, benchmark and verifier policy |
| `valory-xyz/mech-server` | `2ab578f3bd4eb5927b7315e8601d0e1a568f5953` | Mech setup, tool, metadata, execution and response flow |
| Olas website | Live read-only pages | Reported turnover, paid-request example and seller quickstart |
| `masumi-network/masumi-payment-service` | `ce960265eac56b9d468173e052e64fa4c9e7a2f2` | Registry, payments, refunds, API keys and x402 seller rail |
| Sokosumi documentation | Live read-only page | Seller marketplace and account-credit requirements |
| `nevermined-io/payments-py` | `3d8b44de584c3e6996a53ef46029a3277d3e5b01` | Paid API plans, x402, registration and API-key dependency |
| `BlockRunAI/Franklin` | `dbee7a8f9d49fdc4180de3cb964dc1421d035808` | `/market` buyer surface and guarded paid execution |
| Franklin market catalog host | DNS checked through three independent public resolvers; no A/CNAME answer | Current catalog reachability caveat |
| `Virtual-Protocol/acp-cli` | `2a72e56ca33b0c3f2180f11c09022426f71ae84e` | Escrowed job lifecycle and Privy signer dependency |
| `algora-io/algora` | `74a49d7728400152f5d640ac8d461e6664b7c2eb`; current public `/bounties` route returns 404 while the source retains org bounty routes | GitHub OAuth worker identity, Stripe Connect country/legal-operation payout account, and explicit compliance/1099 boundary |
| `ridgesai/ridges` | `9397a57e3d03756b9c6c4df29ceaef7ecb2063a0` | Bittensor miner entry and token/stake operational model |
| `Awarexone/Agentic-Bug-Hunter` | `0826b137b4d03f9bd848940427dc4e4e1454c4c2`; 709 tests passed locally | Reusable authorized scope, audit, validation and report engine plus its human-submission boundary |
| Olas marketplace subgraphs | Observed `2026-08-28T01:09:12Z`; exact endpoint pattern `https://api.subgraph.autonolas.tech/api/proxy/marketplace-{chain}`; query `requests(where:{blockTimestamp_gte:"1787792952"})`; end blocks Gnosis `47949843`, Base `50545002`, Polygon `92782883`, Optimism `156140287`; first returned blocks Gnosis `47932877`, Base `50515403`, Polygon `92741214`, Optimism `156116723`; response SHA-256 respectively `90f72f764ecf11ba05d6b78c716d27eb155a28f679dc47a2e92191376b9d8d0c`, `e0afd5330a4e7d73da008ffbdb1769edfcb70768a5b4376ca3fc347bd4f2b57e`, `4cb946e73870de9c5fc9c61b8a93899123b309d1e6e2f93edcc482be369ebaf1`, `cc36a0028c4d2f4a74d8eb28613a4e67a45f9f614170080b1d52ca7f7a89c6ef`; no indexing errors | Current Mech population, request concentration, deliveries and 24-hour activity |
| Immunefi live bounty directory | Observed `2026-08-28T01:20:16Z`; `https://immunefi.com/bug-bounty/`; 186 listed programs; response SHA-256 `9a671a952d0cc4c9fad62cea5fd1f35984c79f0f37a6dc61fca96a86ad7cffc8` | Standing security-bounty inventory and program fields |
| Code4rena official listing | Observed `2026-08-28T01:20:16Z`; `https://code4rena.com/audits`; response SHA-256 `b7077ae1f69080db021c4bfb9d4b93059a75b501498d80b25f87214e1a34655c` | Current audit availability and historical USDC pools |
| Sherlock official listing | Observed `2026-08-28T01:20:16Z`; `https://audits.sherlock.xyz/contests`; response SHA-256 `8a3e3aa1fd0b31ff584506b6f5c14fee6a9988b4ff35742fa382ce4f3dd24f4c` | Current contest availability and historical USDC pools |
| Cantina official listing/docs | Observed `2026-08-28T01:20:16Z`; `https://cantina.xyz/competitions`; response SHA-256 `ef286283f40f1a354ace7b07a0267cea10eb3764d8f93adfd299dbf7b4eaeec7` | Opportunity surface, historical payout and KYC/USDC boundary |
| `profullstack/ugig.net` | Commit `86ff9a94e11f36d47963ab3149eb626e36682ea2`; observed `2026-08-28T01:20:16Z`; endpoints `https://ugig.net/api/gigs?limit=100` and `/api/bounties?limit=100`; response SHA-256 `d5ad0fbf89bb3200685eecf1054c3328f49edf7400c8cbd70803ed6d2de976e2` and `365eb83195783e848cd06b16d165f047356fdd987feae9d5accd60dc62037a4f` | Agent registration/payment implementation and current low-liquidity inventory |
| Superteam Earn official agent API | `https://earn.superteam.fun/api/listings`, `https://superteam.fun/skill.md`; response SHA-256 `6cb7f3ceb971e1b4e4525bb2337f2dad07ac3bfb10a695dd3fef9f55a0b0c37d` and `44745026273c267572762b1851c46bda58d52a55a28cf54d7c1a72b76a6bb350` | Current agent-eligible USDC inventory and mandatory human payout-claim boundary |
| Hats Finance contracts and Arbitrum vault | `hats-finance/hats-contracts` commit `25a3811453ab7f80df0200c4f5eb8eb957ada142`; registry `0x145b550aC44c3d052e9200937DFaB0B163C538dE`; vault `0x1025B2248cB6AEAF93c7E4d10B19F90f5B4ea090`; observed Arbitrum block `499120800`; scope IPFS SHA-256 `98e3fd962476af9c3e82e19f0bdb6c54325013cba8ee84a6547518f1bec5a7ec`; claims-log SHA-256 `2deb6869003bfbf1e8c62ebe7af210ac692f3354e352a956af64ff8d7963741a` | Scope, funding, committee readiness, zero claim fee, and no vault-specific committee acceptance/payout event; researcher submissions remain unknown |
| Hats Finance official docs | `https://docs.hats.finance/welcome-to-hats-finance/bug-bounties.md`, `https://docs.hats.finance/for-security-researchers/submission-guide.md`, `https://docs.hats.finance/miscellaneous/terms-of-use-1.md`; response SHA-256 `dff49f551de2a5b89a66d04d9a07d3b4b36cc4fba8af9e36718ab6488c97350b`, `ce9a1b0acaa5b5aba965928a178fe436d198b2396744971012b57cb95ffc69ef`, `0b050a9aaccf83ef7406fae9ae422bca3b26f074eb4d58abf9f7cd836b8d23eb` | Permissionless/anonymity/no-KYC claims, on-chain submission/wallet reward mechanics, and terms boundary; explicit agent-operated permission remains unknown |
| Hats policy clarification | `https://github.com/hats-finance/hats-contracts/issues/593`; official GitHub readback state `OPEN` | Exact zero-human agent eligibility, local/fork-only testing, autonomous submission, and direct-wallet payout question; no affirmative permission yet |
| Agentic Market `isNew=true` catalog subset | Observed `2026-08-28T02:59:48.909Z`; `https://api.agentic.market/v1/services`; 2,423 services; durable observation wrapper SHA-256 `37ffa32ad179ccf26fefd58a0f87f1df26a03d348299e86939c1f3aeaf4d4fbd`; evidence `/Users/anicca/.local/state/life-manager/agent-economy-market-cohort/2026-08-28T02-59-48.909Z.json`; flag definition and listing ages unknown | Flagged-subset demand, endpoint-level 30-day calls, payer counts, prices, and gross concentration; not proof of new-seller acquisition |
| Agent marketplace independent measurements | `kristoferlund/agent-marketplace-index` commit `e07d94bd9014da94cf13f7576c00109efcc5ac45`; current snapshot `data/2026-08-27.json`; repository sanity and documentation checks pass | Cross-market evidence that x402 input purchases are active while agent labor boards have little current paid work |
| SearXNG self-hosted search substrate | `searxng/searxng` commit `9fea41204fdfa7a5cfa15b0ebd12904c520478ce`; AGPL-3.0 | Credential-free self-hosted search/content experiment substrate; not revenue proof |
| Bountycaster current inventory and FAQ | Observed `2026-08-28T03:19:38.214Z`; `https://www.bountycaster.xyz/api/v1/bounties/open` and `/in-progress`; both response SHA-256 `9ebd64c63b942e08130e85c8d7727332777ae069c429623be205eb9d51a1257f`; `https://www.bountycaster.xyz/faq` | Zero current open/in-progress inventory, peer-to-peer non-escrow payout, poster-owned completion, and Farcaster/X submission path |
| ClaudeLance mainnet contract and source | `yeheskieltame/claudelance` commit `644d1ba4faf85e8e94c0d6984de227fe35555300`; Celo v3 proxy `0x68c83D75Ee95860E83A893Aa13556AdE8411e3c8`; all-ID chain observation wrapper SHA-256 `045701fbe68ad68484a83a7f3529b9cbc8d540d36fef92c6f62db2c235acb6c1` | 261 current bounties, zero unexpired open opportunity, operator-only historical validation, ERC-8004 identity, and nonzero stake requirement |
| CashClaw and Moltlaunch | `moltlaunch/cashclaw` commit `fb5974ec0f3840ecdd973d20cd74a0735f62289c`; required npm package `@moltlaunch/cli` returns 404; public API timed out; registration UI contains pending-admin state | Autonomous task-loop pattern, but no reproducible CLI/inventory or zero-human registration/runtime path |
| Bountic source and live candidate | `skndash96/bountic` commit `2a552a4a002e9df80601073732880acd367e4e52`; observed `2026-08-28T03:29:34.560Z`; OPEN feed SHA-256 `1fe7ec97a71814d6c302fd4eab060fb31757133c25e297a958c6b77a64205c1c`; #12 detail SHA-256 `d9266b7e9fac193f122f1225090f28dbffa7ee2467f26b68c942af9041101d3c`; PAID feed SHA-256 `118c5958d2ea9cb1d1a4b3d8a98d0515bd7f5b930c606c52a8041740fffc625c` | One 10-USDC funding-success candidate; contradictory title/body, 18 competing PRs, no winner/approval/payout tx/paid timestamp, zero platform PAID rows, and wallet-tag Locus payout schema with no completed receipt |
| MergeOS source and public APIs | `mergeos-bounties/mergeos` commit `c2b238769504e4b4fa44c472422af371c8fc0d3d`; marketplace SHA-256 `16f325fd35f4723937f260fc79cf7112e7dc8b3d47572f7e1b5314fa85b8cd01`; health SHA-256 `6cdd679c5d4e9492ca3ceb5169c7e2bf39dd92cf1a6f2c0cdb07f28c5aff0263` | 989 nominal open tasks but internal MRG rewards, account/approval gates, and production `payment_mode=not-configured` |
| Lightning Bounties source and feed | `Lightning-Bounties/lb-next` commit `454096f67d94dabb28b7651985d2924a3bd86c7a`; observed `2026-08-28T03:37:59.529Z`; public feed wrapper SHA-256 `33af46f3cb370eebf62e6bd7f986c555d89787f264c60e5ab1f3166bd6f78eb4`; GitHub-state join observed `2026-08-28T03:53:09.623Z`, wrapper SHA-256 `81c891521765421b61a0fc132373de0727d2dc6d866009c4be8702cdb8750f08` | 85 rows, 62 claimed, 23 unclaimed; 13 GitHub-open, 11 open-funded, 178,591 current unexpired sats; GitHub OAuth, API claim, BOLT-11 withdrawal, stale-row and duplicate-work boundaries |
| Lightning Bounties policy clarification | `https://github.com/Lightning-Bounties/lb-next/issues/99`; official GitHub readback state `OPEN` | Exact non-human eligibility, self-created GitHub identity, API-only claim/withdrawal, zero-KYC path, and machine-readable current escrow question |
| Sphinx Tribes source and inventory | `stakwork/sphinx-tribes` commit `d28def536d4c4b616e6c149cde34a5b60442681f`; observed `2026-08-28T04:01:36.284Z`; `https://people.sphinx.chat/gobounties/all`; response SHA-256 `3fa87cc2a39b6060b647a875f221308a1ca92e0e32e0acd41326abb3243dabea` | Pubkey/JWT plus Lightning payout implementation and one stale grant/email-onboarding row |
| RustChain bounty economics | `Scottcjn/Rustchain` commit `552fbb3294a855e3828990ebc6e11735abd6cccd`; observed `2026-08-28T04:01:36.284Z`; `https://rustchain.org/payouts.json` SHA-256 `1d69d737dc022e589cd819cb2de3953839d47b5bfa3f48086ab2b3e43394b6e1`; `https://rustchain.org/api/tokenomics` SHA-256 `05adf8f916fc848925d9ced65922c6829829e6c2455702cb09f4e1aef2fafa6b`; `https://api.dexscreener.com/latest/dex/pairs/solana/8CF2Q8nSCxRacDShbtF86XTSrYjueBMKmfdR3MLdnYzb` SHA-256 `0e12e3cf1f8c126c765429b2a14d2e51d50a238aec4bfee2a9e61beb2298fa9e` | 73,930.1 RTC/3,902 confirmed-or-pending founder-wallet transfers, internal 0.15-USD reference, premine/team/emission provenance, and no current DEX pair |
| Boss.dev payout bundle | Observed `2026-08-28T04:02:05.030Z`; `https://www.boss.dev/static/js/main.aca2b448.chunk.js`; SHA-256 `20dc980e2285d21d297d6b169d30c241d99f3ccbf4e84656428b9e860819d580` | GitHub OAuth plus Stripe Connect, government/tax ID, and bank payout requirements |
| Closed or pivoted bounty surfaces | `https://app.onlydust.com` SHA-256 `33ea0cf1eb030879c132eb0d30fe70e6bc605892a8a533df3530987d47fa2d33`; `https://openq.dev` SHA-256 `48febe215d796153f40a22957c69e55b5a5d55de932d464627485caac10b3392` | OnlyDust closure notice and OpenQ OSS-observability pivot; neither supplies current bounty inventory |
| `bounty.new` reachability | Observed `2026-08-28T04:02:05.030Z`; `https://bounty.new`; DNS A/AAAA answers empty; curl resolver error 6 / HTTP 000 | No current readable surface; capability and inventory remain unknown |
| BountyBook docs and public state | Observed `2026-08-28T04:24:30.047Z`; `https://www.bountybook.ai/llms.txt` SHA-256 `8591e24e791a0be450ca09eaabf31d551d49eb091a815e2a92b22976eb706133`; `/stats` `7e49884daf90563e5319cd49d35e7fd96d31f1820af5fbc313feeb1bd40becb7`; `/leaderboard` `56343f93d963da84f527505856e9f0213f055262ba2a5f2c20b066b89cde1143`; open pages `5dc00d4b589dc57b47d4045f686feee510b3c7830571e3d13378e7c35fa9e238` and `6728e80a57bccdc5e3f9073a2dc265ddc3eab57950982a43ebde3b8e58879b15`; EventBus detail `47316207a6061b1ba79e506421bf8852f38170ab187b3a546e2976720d857859`; verified jobs `c2553449f6b093a3bd097b2e94120c250ec7d5472669f1f1de62a40a94e9a1a1`; refunded jobs `fcc3ef7720557359ea8075b5ba0fd116c35e340479c6be149a3571ed1b0148ab`; x402 manifest `439a48f7b7a9ffd8239036859e9028b6668543243cc65c701c1e4062a9300680` | Wallet-only identity, free agent actions, 126 open rows, EventBus attempts/oracle state, payout/refund coverage, and treasury address |
| BountyBook verified payout chain join | Observed `2026-08-28T04:25:39.493Z`; Base RPC `https://mainnet.base.org`; wrapper SHA-256 `28cdc05e37cbb7841fc6200bd4e52f7ca7579cc634bf61c561191bd5125dc5e9` | 28/28 status-1 treasury-to-executor canonical-USDC receipts totaling 55,881,600 atomic, matching 96% of 58.21 USDC budget |
| BountyBook EventBus solvency join | Observed `2026-08-28T04:26:08.269Z`; Base RPC and public open pages; wrapper SHA-256 `361d3bb93be8e9c483290932d6f514f0013bf23232c0209fa7ce0070a47c15d0` | Treasury 813,400 atomic USDC, 126 open rows/611.01 USDC displayed budget, zero poster-to-current-treasury 5-USDC Transfer in recorded creation-time blocks `43730043–43740041`, and only one 0.01-USDC open outcome inside treasury balance |

All live observations are evidence snapshots, not promises of future inventory, revenue, uptime, or
profit. No claim, signature, transaction, account creation, registration, purchase, or publication
was performed during this research slice.

## Olas aggregation reproduction

For each `chain` in `gnosis base polygon optimism`, POST the complete current-population query to
`https://api.subgraph.autonolas.tech/api/proxy/marketplace-$chain`:

```graphql
{
  global(id: "") { totalRequests totalDeliveries }
  meches(first: 1000, orderBy: receivedRequests, orderDirection: desc) {
    id address owner receivedRequests totalDeliveriesTransactions
    selfDeliveredFromReceived deliveredByOthersFromReceived maxDeliveryRate paymentType
  }
  _meta { hasIndexingErrors block { number timestamp } }
}
```

The exact 24-hour request-window query uses cutoff `1787792952`:

```graphql
{
  requests(first: 1000, skip: 0,
    where: {blockTimestamp_gte: "1787792952"},
    orderBy: blockTimestamp, orderDirection: asc) {
    id blockNumber blockTimestamp transactionHash feeUSD finalFeeUSD
    mech deliveredByMech isDelivered
  }
  _meta { hasIndexingErrors block { number timestamp } }
}
```

Repeat with `skip` increased by 1000 until fewer than 1000 rows return. Convert numeric strings,
group rows by `mech`, and calculate request count, delivered count, unique Mechs, sum of
`finalFeeUSD // feeUSD`, and the top-five request share. The population aggregation concatenates
all four `meches` arrays, sorts numeric `receivedRequests` descending, and calculates total, zero,
less-than-ten, and top-five/top-ten shares. Reject any response with `_meta.hasIndexingErrors=true`.
