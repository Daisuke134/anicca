# Agent Economy earning landscape

## Decision

Evaluate **Agent Bounties as the first canary candidate**, then evaluate **Olas Mech Marketplace**
as the recurring service lane. Agent Bounties is not authorized for a claim yet: its current bounty
has seven claims, seven submissions, seven expirations, and zero settlements, so live verifier
quorum and the expiry cause must be established first.

This is not a claim that Agent Bounties provides constant income. It is the strongest currently
identified funded candidate for one new outside-funded Base-USDC settlement. Constant
earning requires a portfolio of (1) funded work inventory, (2) a repeatable marketplace service,
and (3) direct paid endpoints, all reconciled by canonical settlement rather than platform status.

## Current evidence

| Candidate | Verified earning mechanism | Demand evidence | Entry friction | Decision |
|---|---|---|---|---|
| Agent Bounties | Base-USDC escrow, refundable claim bond, deterministic verification, canonical `BountySettled` payout | One outside-funded 1.00-USDC bounty, but its history is 7 claims / 7 submissions / 7 expirations / 0 settlements | EIP-3009 claim signature, separate EIP-712 submission signature, public artifact/evidence, and an unproven live two-verifier quorum | **Blocked candidate** pending verifier and artifact-path proof |
| Olas Mech Marketplace | List an off-chain service and earn when another agent hires it | Olas reports $108,339 marketplace turnover and a cited agent with 57 paid requests | Python/Poetry/Docker, on-chain Mech deployment, metadata publication, continuous service | **Second lane** after the current bounty |
| Masumi / Sokosumi | List an agent in a marketplace; Masumi supplies registry, payment, refund, and x402 rails | Public marketplace and seller documentation exist | Hosted endpoint, registration/account flow and credits; self-hosted payment service uses API keys and wallet infrastructure | Later distribution/payment adapter |
| Nevermined | Meter paid APIs, plans, x402, subscriptions, and USDC settlement | Public seller SDK and documentation exist | Builder account/API key and buyer acquisition remain necessary | Later direct paid-endpoint adapter |
| Franklin Market | Browse and hire paid BlockRun skills | Franklin v3.32.0 implements a buyer surface | No seller publication path in Franklin; catalog host is presently not resolvable | Learn the guarded-spend pattern; reject as earning lane |
| Virtuals ACP | USDC-escrowed jobs and seller offerings | OSS client exposes provider/client job lifecycle | Privy/browser signer approval and platform identity conflict with the no-human-credential core proof | Architecture reference only |
| Algora | GitHub bounties with claim and payout lifecycle | Established OSS bounty product | Stripe Connect and GitHub OAuth identity conflict with the core proof | Reject for AC-12 |
| Bittensor/Ridges | Continuous subnet mining rewards | Active OSS miner/validator ecosystem | TAO exposure, hotkey/coldkey, registration/stake and specialized scoring; not direct Base-USDC cash | Long-term research only |

## Why Agent Bounties is first

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
6. **Use several demand surfaces.** Funded bounties solve the immediate cold start; Olas supplies a
   service marketplace; Nevermined/Masumi can meter endpoints after a service has demonstrated
   demand.

## Immediate canary

No side-effecting claim is authorized yet. First: explain the seven expiration cycles from
canonical evidence; prove both verifier addresses can complete the current two-of-two quorum; prove
a no-human-credential public Git artifact path; and add the minimal Life Manager adapter with an
intent/effect fence and claim→submission→settlement state machine. Only then may the natural loop
attempt one sponsored claim with a 0.10-USDC cap and narrow allowlists.

The accounting must record `+0.10 sponsor subsidy liability → -0.10 claim-bond escrow → +0.10
returned non-revenue principal + 1.00 revenue` on a passing settlement. Rejection or claim expiry
without submission records the lost 0.10 subsidy principal as cost/loss; a verifier timeout after
submission returns it. After a claim the loop runs the pinned benchmark,
makes a separate bounded EIP-712 submission signature, publishes the artifact/evidence without
human credentials, and waits for `BountySettled`. Only the 1.00 reward is revenue.

## Primary sources

- [Agent Bounties repository](https://github.com/NSPG13/agent-bounties) and [live Base feed](https://api.agentbounties.app/v1/base/autonomous-bounties/feed?network=base-mainnet&claimable_only=true)
- [Olas Mech Marketplace](https://olas.network/mech-marketplace) and [seller quickstart](https://build.olas.network/monetize)
- [Masumi Payment Service](https://github.com/masumi-network/masumi-payment-service) and [Sokosumi documentation](https://www.masumi.network/dev/sokosumi/documentation)
- [Nevermined payments-py](https://github.com/nevermined-io/payments-py) and [documentation](https://nevermined.ai/docs/getting-started/overview)
- [Franklin release v3.32.0](https://github.com/BlockRunAI/Franklin/releases/tag/v3.32.0)
- [Virtuals ACP CLI](https://github.com/Virtual-Protocol/acp-cli), [Algora](https://github.com/algora-io/algora), and [Ridges](https://github.com/ridgesai/ridges)
