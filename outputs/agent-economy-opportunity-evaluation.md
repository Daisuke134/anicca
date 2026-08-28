# Agent Economy opportunity evaluation

## Evidence boundary

This is the Life Manager model's read-only normalization of opportunity-scout manifest
`aacac47727e2b796914f0f542f9381593d688ffbdfce8d731d0e17a15f09cbb5`, observed from 11/11
successful public requests with zero raw-response hash mismatches. The raw files remain under the
isolated instance state root. `unknown` means the snapshot cannot prove the field; it is not a
negative guess. No account, application, report, claim, signature, payment, reservation, or
broadcast occurred.

## Normalized evaluation

| Market | Scope | Funding | Recent payout | Competition | Signup identity | Payout rail | Deadline | Expected compute | Official receipt | 5A.2 result |
|---|---|---|---|---|---|---|---|---|---|---|
| Agent Bounties | not applicable: claimable feed is empty | not applicable: no current job | unknown: no current settlement row | not applicable | unknown: no signup evidence in empty feed | unknown from this empty snapshot | not applicable | not applicable | unknown from this empty snapshot | reject: zero inventory |
| Immunefi | unknown until one of 186 programs is selected and its exact assets/impacts are read | directory exposes max reward/vault fields, but no selected program funding proof | directory exposes some total-paid fields; no selected-program current payout proof | unknown from directory | incompatible/unknown: mixed KYC flags and no proof of a self-created zero-human account/submission path | varies by program | continuous directory; program deadline unknown | unknown until source/PoC requirements are read | unknown for a selected payout | reject: program-level zero-human and net evidence missing |
| uGig | descriptions exist for 50 active hiring rows and 12 open bounty rows; exact contract scope is unverified | unknown: listing budget is not escrow or payment proof | unknown: snapshot contains no selected official payout receipt | 343 applications across current gigs; per-row counts are visible | unknown: public inventory does not prove autonomous signup/recovery | listings advertise USDC/SOL; settlement proof is missing | mixed or absent in inventory | unknown; several rows advertise $5 while new rows advertise $40-$80 | unknown from this inventory snapshot | reject: funding, identity, and receipt proof missing |
| Code4rena | unknown: no current open audit scope established by snapshot | historical USDC pools are visible; no current open funded pool established | historical rewards visible; no selected current payout | unknown for a current contest | unknown: no self-created zero-human account proof | historical USDC | no current open deadline established; page shows report in progress/history | unknown until a current codebase exists | unknown for current inventory | reject: no current open opportunity proved |
| Sherlock | unknown: snapshot does not establish one selectable current contest scope | unknown for a selected current contest | historical reward surface only | unknown | unknown: no self-created zero-human account proof | historical USDC/other contest assets | headings include Active/Upcoming/Finished, but no current selectable deadline is proved | unknown | unknown for current inventory | reject: current job and identity evidence missing |
| Cantina | program-specific scope not selected | aggregate opportunity surface is not selected-job funding | official page reports aggregate paid totals, not a selected recent payout | unknown | incompatible: official researcher docs require KYC | Ethereum mainnet USDC after KYC | unknown for a selected competition | unknown | platform payout after KYC is outside AC-12 | reject: KYC is a hard zero-human failure |
| Olas Mech | tool/service scope is unknown until a buyer/use-case is identified | on-chain request and fee fields are present; no buyer is committed to a new Life Manager Mech | unknown: snapshot does not prove claimed earnings or a new-Mech payout | Mech/request counts are present; Gnosis latest page is truncated and therefore current demand coverage is unknown | unknown: snapshot does not prove self-created end-to-end identity/recovery | payment-type and fee fields are present; settlement into a selected seller wallet is unknown | continuous listing surface; no bounded job deadline is present | unknown until tool/API/runtime are chosen | request/delivery fields are present; selected payout receipt is unknown | reject: no pre-identified buyer and incomplete net economics |

## Judgment

No current market passes 5A.2. This snapshot shows the largest directory count at Immunefi, the
largest set of individual current listing rows at uGig, and on-chain request fields at Olas; each
still lacks at least one hard requirement. The next action is another public-evidence pass that
searches program-level candidates and exact zero-human account/submission terms. It must not create
an identity until one candidate passes the public gate.

## 5A.2 additional public-gate evidence

### Superteam Earn

The official public API currently returns 33 open listings and explicitly marks three as
`AGENT_ALLOWED`: Streamflow, ZNS, and Mermail, each with a 500-USDC pool. The official agent skill
supports autonomous registration, discovery, comments, and submission. It also explicitly says an
agent does not complete wallet signing/KYC and **a human operator must claim the winning agent for
payout eligibility**. That claimant would act on behalf of the instance, so every Superteam listing
fails AC-12 even though work submission is agent-native. Evidence hashes: listings
`6cb7f3ceb971e1b4e4525bb2337f2dad07ac3bfb10a695dd3fef9f55a0b0c37d`; official skill
`44745026273c267572762b1851c46bda58d52a55a28cf54d7c1a72b76a6bb350`.

### Hats Finance

Hats has promising wallet-native mechanics: official documentation states permissionless,
anonymous bug bounties, on-chain hash submission, and wallet rewards without KYC. Whether the
platform/program explicitly permits a non-human agent to submit is still unknown. Current registry
readback shows 19 Ethereum, 14 Arbitrum, and 8 Optimism vaults; only one Ethereum and one Arbitrum
vault have nonzero assets. The Arbitrum `Hats security staking` vault is visible, committee-ready,
has zero claim fee, holds `766104.695275975445328750 HAT`, caps the bounty at 10%, and publishes a
machine-readable scope at current source commit `25a3811453ab7f80df0200c4f5eb8eb957ada142`.
However, its vault-specific claims manager has no committee `SubmitClaim` acceptance or
`ApproveClaim` payout event. Researcher `LogClaim` events occur at the shared registry and cannot be
attributed to this vault from the inspected event alone, so researcher submission history remains
unknown. The vault lacks recent-payout proof and explicit agent-operated permission; it is a
promising wallet-native protocol candidate, not a selected opportunity.

Policy clarification is open at
[`hats-finance/hats-contracts#593`](https://github.com/hats-finance/hats-contracts/issues/593).
The issue asks whether source/local-fork-only autonomous work, encrypted/on-chain submission, and
direct wallet payout are permitted without any human claimant, KYC, account, OAuth, approval, or
payout intermediary. Until the maintainer answers affirmatively with the authoritative current
path, no identity, audit, disclosure, claim, or transaction is allowed for this candidate.

### Agentic Market x402 inputs

The public Agentic Market API currently exposes 2,423 services with endpoint-level 30-day paid-call
and unique-payer counters. An independent fixed-commit collector snapshot reports 283,405 calls and
about 9,450 USDC gross after excluding the extreme-price outlier, while labor marketplaces in the
same measurement remain nearly empty. This supports the architectural lesson from BlockRun: sell a
small machine-readable input repeatedly instead of waiting for a human-shaped job.

The current `isNew=true` catalog subset does not pass the public gate; the flag's definition and
listing ages are unknown. Only three services carry the flag and two have zero calls. Otto AI has
5,729 calls, 116 maximum endpoint-level payers, and an
endpoint-price-times-calls estimate of 22.961 USDC. Its gross is concentrated: tweet search alone is
about 13.995 USDC from 2,799 calls and 13 payers, while image generation, Exa search, Gemini research,
and other endpoint descriptions name upstream services. It is an inference, not yet primary-source
proof, that operating those endpoints needs paid capacity or credentials; only human-provided
credentials would violate the instance's identity boundary.
Self-hostable/keyless examples such as DNS, RDAP, public-chain, weather, and public-market-data
endpoints demonstrate demand but do not independently prove the roughly 13 USDC/month fixed-cost
floor. A self-hosted SearXNG search/content service is therefore a valid experiment hypothesis, not
a positive-expected-net selected opportunity. No service registration, wallet, deployment, or paid
call is authorized from this evidence alone.

### Lightning Bounties

Lightning Bounties is an active wallet-native rail rather than an empty directory. Its public feed
currently contains 85 distinct rows: 62 have a winner and `claimed_at`, while 23 are unclaimed with
320,937 displayed sats in aggregate. GitHub readback reduces those 23 to 13 still-open issues, nine
closed issues, and one repository with issues disabled. The frontend and official documentation
show GitHub OAuth, an API reward-claim call after a merged PR, an internal sats balance, and
withdrawal by submitting a BOLT-11 invoice. The documentation says anyone with a GitHub account can
participate globally without banking restrictions, but it does not explicitly authorize a
non-human agent or prove API-only signup, claim, recovery, and withdrawal with an instance-created
identity and Lightning wallet.

No exact current row passes the remaining gate. The Primal translation issues offer 50,010 sats on
iOS and 50,000 sats each on Android and web, but they have
multiple existing PRs; the web issue's bounty poster explicitly asked new contributors to wait for
maintainer direction. The 20,000-sat LNbits BOLT12 issue already has competing substantial PRs. The
Branta design row displays 21,052 total sats but only 4,286 unexpired sats, already has two detailed
feedback submissions without maintainer acceptance, and has no winner. The public feed also leaves
some resolved GitHub issues marked unclaimed, so `claimed_at=null` is not current-inventory proof.
Historical claimed rows prove platform-side winner accounting, not a completed Lightning withdrawal
receipt for the new instance.

Policy and machine-readable inventory clarification is open at
[`Lightning-Bounties/lb-next#99`](https://github.com/Lightning-Bounties/lb-next/issues/99). Until an
authoritative answer permits the complete agent-operated path and one non-duplicate candidate proves
current escrow, scope, acceptance readiness, expected net, and withdrawal readback, no GitHub
identity, PR, claim, invoice, wallet funding, or withdrawal is allowed.

### Other added candidates

- CodeHawks exposes a nominally live BattleChain page, but its dated contest has results and the
  directory marks rewards as KYC; reject.
- Dework advertises wallet payments and public bounties, but current public readback does not prove
  selected-job escrow, payout, or zero-human signup/recovery; reject.
- OpenBounty did not yield a verifiable current official inventory or OSS path; reject as unknown.
- Bountycaster reports 2,967 lifetime bounties and 1.5 million dollars posted, but its current
  public `open` and `in-progress` APIs both return empty arrays. Its FAQ says payout is peer to peer,
  Bountycaster only facilitates, only the original poster marks completion, and submission normally
  occurs through Farcaster or X. Reject: cumulative history is not inventory and no escrowed current
  payout exists.
- ClaudeLance has a verified Celo-mainnet escrow and explicitly models AI workers, but its own README
  classifies adoption as pre-organic and all reported mainnet activity as one operator's validation.
  Direct reads of all 261 v3 bounties find 250 resolved and 11 status-open but expired; zero are both
  open and before deadline. Claiming also requires an ERC-8004 identity and a poster-defined nonzero
  stake. Reject: no current outside-funded opportunity and pay-to-submit violates 5A.2.
- CashClaw contains a useful autonomous task loop around Moltlaunch, but the required
  `@moltlaunch/cli` package returns npm 404, the public API times out, registration can remain pending
  admin approval, and its LLM setup expects a provider API key. Reject: no working public inventory
  or zero-human operating path.
- Bountic has one real current candidate: `skndash96/bountic#12` is OPEN and its official API records
  one anonymous 10-USDC funding event as `SUCCESS`. A maintainer choosing/merging a winner and
  authorizing payout is an independent customer's accept/pay decision, not a human acting for the
  instance. The candidate still fails the public gate: its title requests multi-contributor payout
  distribution while its body asks an unrelated Medusa cart-inventory question; 18 competing PRs
  remain open, some for four months; winner, approval, payout transaction, and paid timestamp are
  null; and the platform-wide PAID feed is empty. The issue label provides an authorized OSS
  contribution surface, but no deadline is stated. A worker identity would require a self-created
  GitHub account and fresh-session automation proof, which remain unknown. The code exposes
  wallet-tag payout through Locus and a nullable transaction hash, but no completed official wallet
  payout proves that rail. Expected compute and positive expected net are unknown because the scope
  is contradictory and 18 submissions already compete for 10 USDC. Reject this exact candidate for
  contradictory scope, unproved identity/payout receipt, and unproved expected net—not because
  external maintainer acceptance is human-in-loop.
- MergeOS exposes 989 nominal open tasks, but current health says
  `payment_mode=not-configured`, rewards are internal MRG credits, login uses email/GitHub/Google,
  and owner/admin acceptance gates internal credit. Reject as an official-cash and identity failure.
- Algora remains an active GitHub bounty/contract implementation, but developer signup uses GitHub
  OAuth and payout requires a Stripe Connect account tied to the country where the worker or
  business legally operates. Official product text says Algora handles compliance and 1099s.
  Reject: KYC/tax/legal identity and Stripe payout are hard AC-12 failures regardless of inventory.
