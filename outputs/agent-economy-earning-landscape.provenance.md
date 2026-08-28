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
| `algora-io/algora` | `74a49d7728400152f5d640ac8d461e6664b7c2eb` | GitHub bounty flow and Stripe Connect payout dependency |
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
