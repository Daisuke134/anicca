# Agent Economy Completion Implementation Plan

> **For Codex:** Execute this plan with subagent-driven-development. Only one task is active at a time. Implementers may edit only the production and test files named by their task brief; the primary owns this plan, the design spec, state, live evidence, and completion decisions.

**Goal:** Turn the existing Life Manager agent-economy skeleton into a release-backed, evidence-gated system that can prove external revenue, pay for its own compute and shelter, graduate after 30 verified days, and spawn an isolated child without human-funded inference.

**Architecture:** One provider-neutral receipt journal is the financial truth boundary. Revenue lanes project verified receipts into that journal; compute and shelter adapters consume only unencumbered verified proceeds under the shared treasury policy. Immutable namespaced releases run the resident loop. Status, publication, and child admission read the same receipts and never infer success from process liveness or model output.

**Tech Stack:** Node.js ESM and `node:test`, Python 3 where an existing provider lane is Python, shell launch/release scripts, viem for EVM verification, Cloudflare Worker for the edge seller, append-only JSONL/SQLite sources already owned by each lane.

## Global Constraints

- The only repository is Life Manager. Do not create a Profitable Cloud, Franklin, Agora, or other sibling repository.
- Runtime code must come from an immutable release under `~/loops/life-manager/releases/<release-id>` with atomic `current` and rollback. A source checkout or `.worktrees` path is never a production target.
- Instance private keys come only from the instance wallet file. Generic environment wallet overrides are rejected for agent-economy execution and never copied to logs, receipts, plans, or tests.
- Revenue is accepted only from official provider or chain evidence. Drafts, views, likes, self-payments, swaps, test payments, inferred revenue, and unverified rows contribute zero.
- Every accepted receipt has a canonical idempotency key. Replaying the same source produces zero new journal rows and zero additional balance.
- Net is signed `gross - fee - refund`; refunds and chargebacks may reduce balance. Amount, asset, payer, recipient, provider state, and settlement proof must agree.
- Spending is authorized only against verified proceeds minus reserve and committed liabilities, with per-session and daily caps. A local PASS cannot authorize spend.
- External effects require durable intent, provider execution, official readback, and terminal receipt. Unknown state is not success.
- Live provider credentials remain in the private credential SSOT. Fixtures use synthetic addresses and identifiers.
- Public claims remain build-log language until all AC-1 through AC-9 evidence joins pass. “World's first” is never emitted by code without separately verified comparative evidence.

## Task 1: P0 Verified Revenue Receipt and Signed-Net Journal — complete

**Files:**
- Create: `skills/agent-economy/lib/revenue-receipt.mjs`
- Create: `skills/agent-economy/lib/revenue-receipt.test.mjs`
- Modify: `skills/_shared/lib/verify-tx.mjs`
- Modify: `skills/agent-economy/lib/money-truth.mjs`
- Modify: `skills/agent-economy/lib/money-truth.test.mjs`

**Behavior:**

Define a versioned `RevenueReceipt` normalizer with provider, payer, recipient, gross, fee, refund, signed net, asset, chain/provider proof, terminal state, occurred-at, and canonical idempotency key. Extend EVM verification to bind a successful receipt to the expected chain, contract, recipient, payer when known, transfer amount, and log index. Reconciliation accepts only normalized terminal receipts, appends one canonical row, and includes negative corrections while rejecting malformed arithmetic and duplicates.

**TDD:**

1. Add failing tests for a real external transfer, duplicate replay, wrong recipient, wrong asset, successful transaction without matching transfer log, fee mismatch, refund/chargeback, self-payment, and unverified provider receipt.
2. Run `node --test skills/agent-economy/lib/revenue-receipt.test.mjs skills/agent-economy/lib/money-truth.test.mjs` and capture RED.
3. Implement the smallest normalizer and verifier changes.
4. Run the same command and require pristine GREEN.
5. Run `node --test runtime/loop/__tests__/money-truth-wire.test.mjs` to prove the loop still reconciles before planning.

**Acceptance:** Duplicate replay adds no row; a correction can lower net; an EVM `status=success` without the expected transfer is rejected; no secret enters output.

## Task 2: P0 Identity Isolation, Status Configuration, and Release Dependency Provenance — complete

**Files:**
- Modify: `skills/earn/lib/resolve-identity.mjs`
- Modify: `runtime/compute-proxy/proxy.mjs`
- Modify: `runtime/compute-proxy/force-frontier-proxy.mjs`
- Modify: `runtime/loop/__tests__/resolve-identity.test.mjs`
- Modify: `skills/agent-economy/status.mjs`
- Modify: `skills/agent-economy/status.test.mjs`
- Modify: `bin/cut-loop-release.sh`
- Modify: `test/agent-economy-control-plane.test.mjs`

**Behavior:**

Add an agent-economy identity mode that rejects generic private-key environment overrides and resolves only the instance wallet. Make status discover explicit paths or `ANICCA_HOME`, otherwise exit 2 with a non-secret diagnostic. During release cutting, perform lockfile-fixed dependency installation inside the release and record lock/dpendency digests and runtime versions in `RELEASE.json` before sealing.

**TDD command:**

`node --test runtime/loop/__tests__/resolve-identity.test.mjs skills/agent-economy/status.test.mjs test/agent-economy-control-plane.test.mjs runtime/compute-proxy/__tests__/ensure-wallet.test.mjs`

**Acceptance:** A poisoned environment cannot change the public address; a sealed release imports viem without source `node_modules`; missing configuration fails before reading an undefined path.

## Task 3: P1 Namespaced Immutable Control Plane — complete

**Files:**
- Modify: `bin/plistgen.py`
- Modify: `bin/cut-loop-release.sh`
- Modify: `loops/agent-economy/loop.toml`
- Modify: `skills/agent-economy/launch.sh`
- Modify: `test/agent-economy-control-plane.test.mjs`
- Modify: `install.sh`

**Behavior:**

Move the code release root to `~/loops/life-manager`, keep mutable agent-economy state in its existing instance namespace, reject worktree/source targets at plist generation time, and preserve atomic current/previous rollback. Installer and plist read back the same sealed release metadata.

**TDD command:**

`node --test test/agent-economy-control-plane.test.mjs test/install-agent-economy.test.mjs`

**Acceptance:** Generated launchd arguments contain only the namespaced immutable release; an explicit `.worktrees` input exits nonzero and writes no plist; rollback restores the exact previous release; natural launchd readback matches the installed release.

## Task 4: P2 Revenue Lane Adapters and Replay-Zero Projection — complete

**Files:**
- Create: `skills/agent-economy/lib/revenue-adapters.mjs`
- Create: `skills/agent-economy/lib/revenue-adapters.test.mjs`
- Modify: `skills/earn/gig/scripts/sync_gig_revenue_events.py`
- Modify: `skills/earn/x402-sell/serve-v2.mjs`
- Modify: `skills/earn/taskmarket/taskmarket-work.mjs`
- Modify: `skills/writer-agent/scripts/writer_stripe_sync.py`
- Modify: `skills/earn/lancers/scripts/work_sync.py`

**Behavior:**

Add thin source-to-`RevenueReceipt` adapters for Coconala, Lancers, TaskMarket, x402 seller, and Writer/Stripe. Do not change lane executors. Sources lacking payout/settlement evidence emit a durable rejection, not revenue. Project accepted receipts one way into the shared journal.

**TDD:** Provider fixtures cover settled revenue, pending state, fee, refund, self-payment, duplicate, malformed currency, and missing proof. Run focused lane tests plus `node --test skills/agent-economy/lib/revenue-adapters.test.mjs`.

**Acceptance:** One verified external receipt from the target instance is reproducible from official readback; a second sync is replay-zero; all five lanes fail closed when their required proof is absent.

**Live evidence:** Base USDC transaction `0x36deb1f3921a399d2b2b1d8db90821ac5d6d785a74689b056f6d12d5ec06135c`,
chain `8453`, transfer log `503`, outside payer, recipient-bound amount `3000` atomic units. First
projection accepts one row; second projection accepts zero and reports one duplicate.
The resident resolver now returns the same recipient. Of the wallet's `1.7` USDC balance, only this
`0.003` USDC receipt is accepted revenue; the other `1.697` USDC is non-revenue seed/top-up and is
ineligible to satisfy the P3 funding-provenance gate.

## Task 5: P3 Self-Funded BlockRun Compute Receipt

**Files:**
- Create: `runtime/compute-proxy/compute-receipt.mjs`
- Create: `runtime/compute-proxy/__tests__/compute-receipt.test.mjs`
- Modify: `runtime/compute-proxy/proxy.mjs`
- Modify: `skills/agent-economy/lib/treasury-policy.mjs`
- Modify: `skills/agent-economy/lib/treasury-policy.test.mjs`

**Behavior:**

Require accepted revenue receipt ids as funding provenance. Bind pre-balance, authorization, BlockRun request, settlement, response, cost, and post-balance into one idempotent compute receipt. Reject balance non-conservation, payer mismatch, human-funded provenance, missing output, and settlement ambiguity. Use an instance-specific proxy port.

**TDD command:**

`node --test runtime/compute-proxy/__tests__/compute-receipt.test.mjs skills/agent-economy/lib/treasury-policy.test.mjs runtime/compute-proxy/__tests__/ensure-wallet.test.mjs`

**Acceptance:** A capped live canary pays BlockRun from the target instance's verified external proceeds; chain balance and provider settlement reconcile; replay does not pay twice.

## Task 6: P4 Provider-Neutral Shelter Lifecycle

**Files:**
- Create: `skills/self/spawn/lib/shelter-provider.mjs`
- Create: `skills/self/spawn/lib/shelter-provider.test.mjs`
- Modify: `skills/self/spawn/lib/cloud-target.mjs`
- Modify: `skills/self/spawn/lib/spawn-orchestrator.mjs`

**Behavior:**

Define `quote`, `provision`, `health`, and `terminate` receipts. Add Conway and Nodexo adapters behind the same provenance, solvency, and spend-cap contract; retain Clore/Nosana/Akash/x402Compute only as measured alternatives. A failed health check triggers bounded terminate/readback and never records shelter success.

**TDD command:** `node --test skills/self/spawn/lib/shelter-provider.test.mjs skills/self/spawn/lib/spawn-orchestrator.test.mjs`

**Acceptance:** Two independently authorized provider canaries complete quote-to-terminate with official receipts; cost is journaled once; leaked or unknown resources fail the gate.

## Task 7: P5 Cloudflare Edge Sale and Phone-Only Readback

**Files:**
- Modify: `services/x402-worker/index.ts`
- Modify: `services/x402-worker/wrangler.toml`
- Modify: `services/x402-worker/deploy.sh`
- Create: `services/x402-worker/revenue-receipt.test.ts`
- Create: `skills/agent-economy/claim-manifest.mjs`
- Create: `skills/agent-economy/claim-manifest.test.mjs`

**Behavior:**

Resolve per-instance `payTo`, settle via the configured x402 facilitator/chain, append an instance-attributed receipt, and expose a secret-free health/status readback suitable for a phone. Deployment metadata records Worker version, KV namespace, billing liability, and rollback target. The claim manifest joins every dashboard/public metric to receipt ids.

**Acceptance:** A live edge purchase independently reconciles on chain and in the shared journal; nonce and receipt replay are zero; the phone readback exposes no key/token; Worker rollback restores the previous version.

## Task 8: P6 Graduation, Publication Gate, and Isolated Child Admission

**Files:**
- Create: `skills/agent-economy/status-collector.mjs`
- Create: `skills/agent-economy/status-collector.test.mjs`
- Create: `skills/agent-economy/child-admission.mjs`
- Create: `skills/agent-economy/child-admission.test.mjs`
- Modify: `skills/agent-economy/status.mjs`
- Modify: `skills/self/spawn/lib/spawn-orchestrator.mjs`
- Modify: `scripts/verify-fresh-clone.sh`
- Modify: `scripts/verify-oss-self-contained.mjs`

**Behavior:**

Collect liquid balance, liabilities, compute/shelter costs, and human-paid inference from verified receipts for a rolling 30-day snapshot. Gate publication and child admission on all design ACs, 1.5x coverage, 30-day runway, zero human-paid inference, clean fresh clone, rollback proof, and claim-to-evidence audit. Record seed capital as a parent liability and child non-revenue. Give the child an isolated home, wallet, proxy port, and cost journal; stop it automatically when evidence becomes invalid.

**TDD:** Add fixtures for day-window boundaries, refund after graduation, liability omission, human-paid inference, duplicate receipt, parent-key access, port collision, seed misclassification, and child auto-stop.

**Acceptance:** Thirty real consecutive days satisfy the gate; the public skill installs cleanly; every published number resolves to evidence; one child is spawned with isolation and stops fail-closed when its gate is revoked.

## Final Verification and Live Evidence Order

1. `npm ci --no-audit --no-fund` with at least 3 GiB free.
2. `npm run test:agent-economy`, `npm run test:install`, and `npm run test:oss` with pristine output.
3. Cut a sealed release, install it, and verify loaded launchd arguments and natural-run receipts.
4. Produce one external revenue receipt and replay-zero proof.
5. Run capped BlockRun compute, then shelter provider canaries, then Cloudflare edge sale.
6. Keep 30 consecutive daily snapshots; no shortened or synthetic interval closes graduation.
7. Run fresh-clone install, rollback, claim audit, and isolated child canary.
8. Only after all evidence passes, publish the factual case study and enable the public agent-economy skill.
