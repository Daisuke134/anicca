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

### Other added candidates

- CodeHawks exposes a nominally live BattleChain page, but its dated contest has results and the
  directory marks rewards as KYC; reject.
- Dework advertises wallet payments and public bounties, but current public readback does not prove
  selected-job escrow, payout, or zero-human signup/recovery; reject.
- OpenBounty did not yield a verifiable current official inventory or OSS path; reject as unknown.
