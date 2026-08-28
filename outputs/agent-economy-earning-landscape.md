# Agent Economy earning landscape

## Decision

Use a **live opportunity scout**, not a preferred marketplace. Immunefi, Agent Bounties, Olas,
uGig, Code4rena, Sherlock, and Cantina are candidate inventory only. The scout selects a provider
only after program-level payout, policy, competition, credential, and expected-net checks. No side
effect is authorized merely because a listing exists.

No candidate is yet proven to provide constant income. Constant earning requires a portfolio of
(1) funded work inventory, (2) a repeatable marketplace service, and (3) direct paid endpoints,
all reconciled by canonical settlement rather than platform status.

## Current evidence

| Candidate | Verified earning mechanism | Demand evidence | Entry friction | Decision |
|---|---|---|---|---|
| Agent Bounties | Base-USDC escrow, refundable claim bond, deterministic verification, canonical `BountySettled` payout | One outside-funded 1.00-USDC bounty, but its history is 7 claims / 7 submissions / 7 expirations / 0 settlements | EIP-3009 claim signature, separate EIP-712 submission signature, public artifact/evidence, and an unproven live two-verifier quorum | **Blocked candidate** pending verifier and artifact-path proof |
| Olas Mech Marketplace | List an off-chain service and earn when another agent hires it | Active on-chain demand exists, but recent Gnosis requests are 93.2% concentrated in five Mechs; Base has four requests in the observed day | Python/Poetry/Docker, on-chain Mech deployment, metadata publication, continuous service | Monitor; do not deploy without a pre-identified buyer/use case |
| Immunefi | Continuous authorized Web3 bug-bounty programs with project-funded crypto rewards | 186 listed programs; recent program updates; current audit competition inventory; program pages expose max/min reward, vault, KYC and paid history | Account and program-specific policy; some require KYC or non-refundable pay-to-submit; findings are rare and competitive | **Largest observed standing-inventory candidate**; profitability unproven |
| Agentic Bug Hunter | Scope→recon/source audit→validation→report engine | 4,472 stars, 805 forks, 709 local tests pass at the pinned commit | Upstream requires human approval before submission and permits authorized targets only | Reuse analysis engine; add separate policy/effect adapter, never remove scope fence |
| uGig | Agent-first gig and bounty API with crypto payout code | Live API: 50 hiring gigs from seven posters, 27 from one poster and 24 exact repeats across three titles; 12 open bounties from three creators | Positive-budget gig upper-bound median $5 with 363 applications; open-bounty median $0.50; payment receipt not yet proven for a selected job | Monitor only; reject as primary income |
| Code4rena / Sherlock / Cantina | Competitive smart-contract audits with USDC pools | Large historical payouts, but no currently open Code4rena audit and no currently active Sherlock contest in the observed pages; Cantina requires KYC | Highly competitive; split rewards; specialist source audit; account/KYC rules | Opportunistic inventory, not constant work |
| Masumi / Sokosumi | List an agent in a marketplace; Masumi supplies registry, payment, refund, and x402 rails | Public marketplace and seller documentation exist | Hosted endpoint, registration/account flow and credits; self-hosted payment service uses API keys and wallet infrastructure | Later distribution/payment adapter |
| Nevermined | Meter paid APIs, plans, x402, subscriptions, and USDC settlement | Public seller SDK and documentation exist | Builder account/API key and buyer acquisition remain necessary | Later direct paid-endpoint adapter |
| Franklin Market | Browse and hire paid BlockRun skills | Franklin v3.32.0 implements a buyer surface | No seller publication path in Franklin; catalog host is presently not resolvable | Learn the guarded-spend pattern; reject as earning lane |
| Virtuals ACP | USDC-escrowed jobs and seller offerings | OSS client exposes provider/client job lifecycle | Privy/browser signer approval and platform identity conflict with the no-human-credential core proof | Architecture reference only |
| Algora | GitHub bounties with claim and payout lifecycle | Established OSS bounty product | Stripe Connect and GitHub OAuth identity conflict with the core proof | Reject for AC-12 |
| Bittensor/Ridges | Continuous subnet mining rewards | Active OSS miner/validator ecosystem | TAO exposure, hotkey/coldkey, registration/stake and specialized scoring; not direct Base-USDC cash | Long-term research only |

## Agent Bounties blocked candidate

The live feed at
[`/v1/base/autonomous-bounties/feed`](https://api.agentbounties.app/v1/base/autonomous-bounties/feed?network=base-mainnet&claimable_only=true)
shows contract `0x22cec92c195a6dc0f7aeaf850e7f2cacb3b6de33`, funded by an address different
from the Life Manager wallet. The creator escrow contains 1.00 USDC for the solver and 0.10 USDC
for verifiers. A separate 0.10-USDC claim bond must come from the solver or sponsor. The committed
benchmark runs `python /benchmark/check.py` in a pinned Docker image. Passing settlement or a
post-submission verifier timeout returns the bond; rejection or claim expiry without submission
can consume it. Only `BountyClaimed` proves ownership and only
`BountySettled` proves earnings.

However, `verification_ready=true` proves that the indexed configuration is supported; it does not
prove that both named verifiers are currently operating. Until the seven expiration cycles and
current quorum liveness are independently explained, this is a funded opportunity, not a verified
path to payment.

The repository's `AtomicClaimSponsor` offers a bounded first-bond acquisition path: one lifetime
grant per wallet, exact bounty/bond/terms binding, atomic sponsor-and-claim execution, daily caps,
and replay-protected nonces. The initial claim request itself reserves hosted candidate state, so it
must not be used as a read-only probe. Life Manager should request sponsorship with one stable
idempotency key, verify the returned Base/native-USDC EIP-3009 request, sign once, and proceed only
after the canonical claim event. If sponsorship is unavailable, stop; do not silently use the
1.697-USDC bootstrap liability as earned spending power.

## Patterns to copy

1. **Inventory before capability.** A working payment rail without funded demand does not earn.
2. **Escrow before work.** Check canonical funding, terms, deadline, and verifier readiness before
   reserving or spending.
3. **One intent and idempotency key; one signature per bounded effect.** Reconcile canonical state before every retry.
4. **Settlement is the receipt.** A listing, claim, submission, transaction hash, or platform
   `completed` flag is not cash.
5. **Separate principal, revenue, and cost.** A returned 0.10-USDC bond is principal; only the
   1.00-USDC solver reward is revenue; gas/compute are costs.
6. **Use several demand surfaces.** A scout ranks current funded work; no marketplace receives a
   permanent priority merely because it has cumulative volume.

## Liquidity correction

Olas is active but concentrated. Across the current Gnosis, Base, Polygon, and Optimism marketplace
subgraphs there are 133 Mechs; 44 have zero requests and 59 have fewer than ten. The cumulative top
five receive 91.7% of Mech-attributed requests. In the observed 24-hour window, Gnosis has 6,168
requests across 18 Mechs, 4,224 already delivered, about $40.06 in task fees, and 93.2% of requests
assigned to the top five. Base has four requests served by one Mech. This proves real traffic but
does not support deploying a generic new Mech as a recurring-income plan.

Immunefi has materially deeper standing inventory: 186 programs with public scope and reward
fields. A program page can also prove whether KYC is required, whether a non-refundable submission
fee applies, the minimum/maximum payout, reward asset, vault balance, prior paid amount, PoC rules,
and prohibited activity. The scout must reject pay-to-submit, non-public source, missing safe
harbor, unclear automation policy, or any identity flow that needs a recurring personal
OAuth/browser session. One-time legal entity KYC is acceptable only when the program permits it and
the recurring loop owns a scoped credential plus official payout readback. A high advertised
maximum is not expected revenue.

Agentic Bug Hunter at commit `0826b137b4d03f9bd848940427dc4e4e1454c4c2` is reusable rather than
reimplemented. Its 709 tests pass locally. The first use is offline smart-contract/source analysis
with Ollama and deterministic scope/policy input. Credential attack, password spray, DoS, social
engineering, destructive methods, real-user-data access, and out-of-scope requests stay disabled.
Upstream requires human approval for report submission, so a no-human submission is blocked until
the exact platform and program explicitly allow an agent-operated legal account and an independent
verifier approves the report under a standing policy.

## Current cursor

No provider-specific side effect is authorized. First build the read-only scout and select exactly
one opportunity using current program-level evidence. If Agent Bounties wins that gate, it must then
explain the seven expiration cycles, prove both verifier addresses can complete the two-of-two
quorum, and prove a no-human-credential public Git artifact path before any claim.

If Agent Bounties later wins the gate, its accounting records `+0.10 sponsor subsidy liability →
-0.10 claim-bond escrow → +0.10 returned non-revenue principal + 1.00 revenue` on a passing
settlement. Rejection or claim expiry without submission records the lost subsidy principal as
cost/loss; a verifier timeout after submission returns it. Only canonical `BountySettled` proves
the 1.00 reward.

## Primary sources

- [Agent Bounties repository](https://github.com/NSPG13/agent-bounties) and [live Base feed](https://api.agentbounties.app/v1/base/autonomous-bounties/feed?network=base-mainnet&claimable_only=true)
- [Olas Mech Marketplace](https://olas.network/mech-marketplace) and [seller quickstart](https://build.olas.network/monetize)
- [Masumi Payment Service](https://github.com/masumi-network/masumi-payment-service) and [Sokosumi documentation](https://www.masumi.network/dev/sokosumi/documentation)
- [Nevermined payments-py](https://github.com/nevermined-io/payments-py) and [documentation](https://nevermined.ai/docs/getting-started/overview)
- [Franklin release v3.32.0](https://github.com/BlockRunAI/Franklin/releases/tag/v3.32.0)
- [Virtuals ACP CLI](https://github.com/Virtual-Protocol/acp-cli), [Algora](https://github.com/algora-io/algora), and [Ridges](https://github.com/ridgesai/ridges)
