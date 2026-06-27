# SPEC — B1: accelerate the Akash deploy (provider-services, no-human) — VSDD contract

Date: 2026-06-26 · Feature: `akash-provider-services-acceleration` · Mode: strict (real money/cloud) · Lang: bash
Builder = main agent (me). Adversary = fresh `vcsdd:vcsdd-adversary` (zero builder context).

## DECISION (searched the Akash docs first, per META-RULE)
- ✗ **Console Managed Wallet API = REJECTED**: docs verbatim "Payment: Credit card (USD)" → Dais's money = a HUMAN in
  the loop → breaks Anicca's self-funding. Anicca is no-human by definition, so a credit-card path has no meaning.
- ✓ **provider-services + own crypto wallet = the no-human lane**. Accelerate THAT, not swap to a managed API.

## SCOPE CLARIFICATION (2026-06-27, Dais)
- This is the **REAL Akash mainnet** deploy — Anicca spawning itself on a real decentralized cloud, paid in its own
  crypto (AKT/ACT), no credit card = no human. We HAVE hosted on real Akash before; it just took **~15 min** (mostly
  the ACT mint + a per-spawn swap). GOAL of B1 = same real deploy, **~15 min → ~3 min** by moving mint/swap OFF the
  per-spawn path. `sandbox-2` testnet is used ONLY as a free 1-shot check that the code boots a container + that
  mint credits uact — NOT the destination. The destination is mainnet.

## CORRECTION (2026-06-27 — AEP-76 + REAL sandbox-2 E2E; SUPERSEDES the earlier uakt pricing)
The real chain (post AEP-76 / ACT upgrade) proved two things the fake + a stale-knowledge adversary (FIND-006) got wrong:
1. **Escrow denom = `uact` (ACT, USD-pegged) — REQUIRED, not `uakt`.** AEP-76 DESIGN.md: "Every escrow account must
   hold `Balance.Denom == uact`"; "uact = 1e-6 USD". `uakt` is gas/staking only. Live proof: a uakt deploy → on-chain
   `Deposit invalid` / `Mismatched denominations (uact != uakt)`. → **SDL pricing + `--deposit` = `uact`; gas stays `uakt`.**
2. **ACT is non-transferable + lives in a separate ledger** (AEP-76: "bank SendCoins disabled for uact";
   `actKeeper.Credit` → non-transferable ledger). → **verify ACT via the act/bme ledger, NOT `bank balances`** (my
   "mint reverted" call was a wrong-place query).
3. **Getting uact** (RESOLVED on real sandbox-2 — see `.vcsdd/.../evidence/2026-06-27-real-sandbox2-e2e.md`):
   `akash tx bme mint-act <X>uakt`. The mint CANCELS (`cancel_reason 6` = BMCancelReasonMinimumMint) unless its output
   ≥ `bme params.min_mint` = **10,000,000 uact**; at P_mint≈0.66 a sub-16-AKT mint falls below 10M uact → refunded.
   **25 AKT → 16,578,449 uact EXECUTED.** Verify via `akash query bme ledger --owner <addr>` (status=executed). So the
   treasury (B1.3) mints in chunks ≥ min_mint, OFF the per-spawn path. (`x/market` may also auto-top-up via MsgMintACT.)

## REAL E2E PARSE TRUTHS (2026-06-27, verified on sandbox-2 — these define the impl)
- dseq = `events[]|select(.type=="akash.deployment.v1.EventDeploymentCreated")|.attributes[]|select(.key=="id")|(.value|fromjson).dseq` (the `id` attribute value is a JSON string).
- bid_id = `.bids[].bid.id` `{owner,dseq,gseq,oseq,provider,bseq}` (NOT `.bid.bid_id`); `.bid.state=="open"`; price denom uact.
- lease = `.leases[].lease.state == "active"`.
- send-manifest returns 400 from sandbox test-providers (they bid but don't host) → container-boot proof = MAINNET (B1.5).
Sources: aep-76 DESIGN.md (akash-network/website) · `akash query deployment params` (min_deposits uact+uakt) ·
`akash tx bme mint-act` docs · the live `Deposit invalid` error.

## PROBLEM (current `skills/self/spawn/scripts/deploy-akash.sh`)
1. **BROKEN**: it only runs `akash tx deployment create` + returns dseq. No cert, no bid query, no lease, no
   send-manifest → the container NEVER boots (the child does not actually run on Akash).
2. **SLOW (~3 min)**: per-spawn `USDC→AKT swap` (60-180s) + `--gas auto` simulation + a would-be fixed 30s bid sleep.

## GOAL
A COMPLETE, ~20-30s, 100%-no-human Akash deploy via provider-services, with funding moved OFF the per-spawn path.

## DOCS-FOUND FIXES (each cited)
| fix | source |
|---|---|
| `provider-services` official CLI (scripting/automation) | docs/developers/deployment/cli |
| FULL flow = deployment create → query bids → lease create → send-manifest | cli/common-tasks |
| fast RPC + chain id from the network's own `meta.json` | cli/configuration |
| fixed gas: `AKASH_GAS_PRICES=0.025uakt`, `AKASH_GAS_ADJUSTMENT=1.5` | cli/configuration |
| one-time client cert (`tx cert generate/publish client`), reused by every deploy | cli (cert) |
| pre-mint ACT off-path (`akash tx bme mint-act`) + batch USDC→AKT only when low | cli/act-mint-burn |
| POLL bids (break on first bid) instead of a fixed 30s sleep | common-tasks |

## FILES IN SCOPE (absolute)
- `/Users/operator/anicca/skills/self/spawn/scripts/deploy-akash.sh`  (rewrite: complete provider-services flow)
- `/Users/operator/anicca/skills/self/spawn/scripts/akt-treasury.sh`  (NEW: off-path AKT/ACT top-up)
- `/Users/operator/anicca/skills/self/spawn/scripts/test-deploy-akash.sh`  (NEW: the VSDD oracle)

## ENV CONTRACT (defaults)
| env | meaning | default |
|---|---|---|
| `AKASH_KEY_NAME` | keyring key name that signs (own wallet) | (required, fail-closed) |
| `AKASH_META_URL` | network meta.json (rpc+chain id) | mainnet meta.json |
| `AKASH_NODE` / `AKASH_CHAIN_ID` | override if set, else from meta.json | from meta.json |
| `AKASH_GAS_PRICES` / `AKASH_GAS_ADJUSTMENT` | gas | `0.025uakt` / `1.5` |
| `PROVIDER_SERVICES` | CLI binary (test seam) | `provider-services` |
| `AKASH_PRICE_DENOM` / `AKASH_DEPOSIT` | SDL pricing + deposit denom (AEP-76 escrow) | `uact` / `5000000uact` |
| `AKT_BUFFER_UAKT` / `ACT_BUFFER_UACT` | treasury low-watermarks (AKT for gas + ACT for escrow) | `5000000` / `5000000` |

## INVARIANTS (the test oracle)
- **INV-1 no-human**: no `console-api.akash.network`, no "credit card", no Console managed wallet anywhere in the path;
  every tx is signed by the OWN keyring key (`--from $AKASH_KEY_NAME`).
- **INV-2 complete flow**: deploy-akash.sh runs ALL of {ensure-cert, deployment create, bid poll, lease create,
  send-manifest} — grep proves each command is present and ordered.
- **INV-3 bid poll, no fixed sleep**: no `sleep 30`; bids are polled in a loop that breaks on the first bid.
- **INV-4 cert is one-time**: cert is created only if `query cert list` shows none (idempotent, reused).
- **INV-5 funding off-path**: deploy-akash.sh contains NO `bme mint-act` and NO USDC→AKT swap — those live only in
  akt-treasury.sh (so the per-spawn critical path never swaps/mints).
- **INV-6 fail-closed**: missing CLI / missing AKASH_KEY_NAME / no dseq / no bid / failed lease/manifest → exit !=0,
  NO fake dseq printed (HARD 0.24).

## EDGE CASES
no bid within the poll window → fail-closed; cert already published → skip; meta.json fetch fails → fail-closed.

## NO-MOCK E2E (strict — real cloud)
1. **sandbox-2 testnet** (free testnet AKT from faucet): run deploy-akash.sh → assert a real dseq + an active lease
   + `lease-status` shows the service up → close. (No real money.)
2. **mainnet** (the ~5 AKT Dais seeded): one real deploy of the automaton image → child boots + appears earning →
   verify on-chain lease + the dashboard row. Then the colony spawn can use it.

## DONE = 4-D convergence
spec ✓ (this file) · test ✓ (test-deploy-akash.sh: static INV-1..6 + a fake-provider-services behavioral run) ·
impl ✓ · verification ✓ (fresh `vcsdd:vcsdd-adversary` binary PASS all dimensions + sandbox-2 real-deploy E2E).
