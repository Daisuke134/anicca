# Life Manager Gig Economy Loop Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the existing Coconala commerce kernel with a policy-gated Upwork path, then add
additional markets and bounded revenue learning without creating a second harness.

**Architecture:** `skills/earn/gig/` remains the only local commerce engine. Provider adapters own
transport and official readback; the shared kernel owns intent, receipts, work, QA, finance and
learning. Unknown permissions fail closed. Only one task below is active at a time.

**Tech Stack:** Python 3.13+, JSON/JSONL, existing launchd release system, approved provider APIs,
pytest with plugin autoload disabled, existing Life Manager receipt/ledger contracts.

**Design:** `docs/superpowers/specs/2026-08-22-life-manager-gig-economy-loop-design.md`

**Current-state SSOT:** `skills/earn/gig/TODO.md`. Finish its active production cursor independently;
this plan must not edit, restart or reschedule the current lanes merely to begin global expansion.

## Execution rules

- Execute tasks in order. A later marketplace is not active until the previous gate has a real
  provider receipt.
- Begin each task by re-reading current provider terms and storing URL, retrieved timestamp, content
  hash, jurisdiction and allowed action. A changed rule invalidates the cached capability.
- Each implementation slice changes at most three files and 100 production/test LOC. Split before
  coding if the target is exceeded.
- Use one normal-path test plus the smallest regression preventing duplicate effect, money error,
  data loss or secret leakage.
- Tests and local fixtures never count as business success. External gates close only from official
  provider readback.
- No new runtime dependency or abstraction until the first real consumer requires it.

### Task 0: Preserve continuity and establish development headroom

**Files:**
- Read: `skills/earn/gig/TODO.md`
- Read: `skills/earn/gig/scripts/gig_disk_guard.py`
- Test: `skills/earn/gig/tests/test_gig_disk_guard.py`

- [ ] Record current `origin/main`, deployed release SHA and the active Coconala TODO cursor without
      changing runtime state.
- [ ] Run `df -k /` and the existing disk guard in observation mode.
- [ ] If below the existing safe development threshold, invoke the existing disk-cleanup procedure;
      do not create a new cleaner and do not delete protected runtime evidence.
- [ ] Run
      `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q skills/earn/gig/tests/test_gig_disk_guard.py`.
- [ ] Acceptance: the current Coconala release/cursor is unchanged and tests can write durable
      evidence without disk failure.

### Task 1: Add the action-level policy receipt contract

**Files:**
- Create: `skills/earn/gig/config/marketplace-capabilities.json`
- Create: `skills/earn/gig/scripts/marketplace_policy.py`
- Create: `skills/earn/gig/tests/test_marketplace_policy.py`

- [ ] Write a failing test: missing provider/action, expired evidence and mismatched content hash
      return `unknown` and deny mutation.
- [ ] Add the minimum schema-less loader for
      `(provider, account, action, jurisdiction, terms_version, evidence_url, evidence_sha256,
      retrieved_at, state)`.
- [ ] Add only the five states from the design and make `approved_api` / `approved_browser` the only
      mutation-authorizing states.
- [ ] Seed public provider templates with `unknown`; keep account IDs and private proof outside repo.
- [ ] Run the focused test and `python3 -m json.tool` on the config.
- [ ] Acceptance: an unknown Upwork `submit_proposal` is mechanically unable to reach an effect.

### Task 2: Bind policy receipts to the existing effect fence

**Files:**
- Modify: `skills/earn/gig/scripts/application_effect_fence.py`
- Modify: `skills/earn/gig/scripts/project_ledger.py`
- Create: `skills/earn/gig/tests/test_marketplace_policy_fence.py`

- [ ] Write a failing test showing that an otherwise-valid intent is rejected without a matching
      capability receipt.
- [ ] Add capability evidence hash to the existing intent/effect identity without weakening legacy
      Coconala replay identity.
- [ ] Prove a changed or revoked capability cannot reuse an old mutation authorization.
- [ ] Prove existing Coconala fixtures retain their current effect keys and duplicate fences.
- [ ] Run the focused policy/fence tests plus existing application reconcile tests.
- [ ] Acceptance: policy is a persisted prerequisite of every new-provider mutation, not a prompt.

### Task 3: Implement an Upwork approved-auth capability probe

**Files:**
- Create: `skills/earn/gig/scripts/upwork_adapter.py`
- Create: `skills/earn/gig/tests/test_upwork_adapter.py`
- Modify: `skills/earn/gig/config/marketplace-capabilities.json`

- [ ] Re-read the official Upwork automation page and current API documentation; record exact
      approved endpoints for this account outside the repository.
- [ ] Request/use an official API key through the provider's supported process; do not derive auth
      from browser cookies.
- [ ] Write a failing transport-contract test for authenticated read-only identity/capability
      response and redacted errors.
- [ ] Implement only authentication, bounded timeout and response normalization.
- [ ] Run a real read-only probe and store a redacted receipt outside repo.
- [ ] Acceptance: G1 closes only if the exact account/action matrix is authoritative. If proposal
      mutation is absent, record `unknown`/denied and stop Tasks 5–6 without blocking Task 4.

### Task 4: Normalize one Upwork opportunity read-only

**Files:**
- Modify: `skills/earn/gig/scripts/upwork_adapter.py`
- Create: `skills/earn/gig/schemas/marketplace_opportunity.schema.json`
- Modify: `skills/earn/gig/tests/test_upwork_adapter.py`

- [ ] Write a failing fixture test for provider ID, title, full scope, currency, budget, client
      evidence, skills, timestamp and source URL.
- [ ] Reject partial or synthetic rows; preserve raw evidence hash outside the normalized record.
- [ ] Implement one bounded official query using the approved API.
- [ ] Run one live read-only discovery with zero proposal/message effects.
- [ ] Acceptance: one official opportunity validates and repeated discovery yields the same identity.

### Task 5: Reuse existing qualification and fulfillment preflight

**Files:**
- Modify: `skills/earn/gig/scripts/application_eligibility.py`
- Modify: `skills/earn/gig/scripts/application_planner.py`
- Create: `skills/earn/gig/tests/test_upwork_application_preflight.py`

- [ ] Write a failing test proving an Upwork job is ineligible when an installed skill, deadline,
      revision capacity, data permission or observed fee is missing.
- [ ] Normalize the new opportunity into the existing planner input; do not create an Upwork-only
      planner or scoring model.
- [ ] Rank eligible rows by projected net after observed fee/cost, preserving stable source order.
- [ ] Generate a tailored proposal from quoted buyer evidence with no unsupported claims.
- [ ] Acceptance: planner output is valid, deliverable and profitable, while an unfulfillable job
      cannot create an intent.

### Task 6: Submit one bounded Upwork proposal with official readback

**Prerequisite:** Task 3 proves `submit_proposal=approved_api` for the exact account and endpoint.

**Files:**
- Modify: `skills/earn/gig/scripts/upwork_adapter.py`
- Modify: `skills/earn/gig/scripts/application_direct.py`
- Create: `skills/earn/gig/tests/test_upwork_application_effect.py`

- [ ] Write a failing crash-recovery test: persisted intent plus unknown response performs read-only
      reconcile and never blindly resubmits.
- [ ] Route exactly one qualified proposal through the existing application effect fence.
- [ ] Persist intent before the call and require official application/proposal ID afterward.
- [ ] Replay the same tick and assert zero additional effects.
- [ ] Execute one real proposal, then read it through the official API independently.
- [ ] Acceptance: G3 closes with one intent, one provider effect, one official ID and replay zero.

### Task 7: Add Upwork conversation and contract readback

**Files:**
- Modify: `skills/earn/gig/scripts/upwork_adapter.py`
- Modify: `skills/earn/gig/scripts/reply_action.py`
- Create: `skills/earn/gig/tests/test_upwork_sales_readback.py`

- [ ] Write a failing test for stable message identity, changed-head detection and contract terms.
- [ ] Reuse the existing reply composition and near-duplicate gates.
- [ ] Permit message effects only if Task 3 proves the exact approved messaging capability.
- [ ] Normalize official offer/contract state; an email or model statement is not a contract.
- [ ] Replay a recorded conversation and prove no duplicate reply.
- [ ] Acceptance: one real buyer event reaches a truthful official disposition and any contract uses
      an official external ID.

### Task 8: Route one paid Upwork job through the existing fulfillment pipeline

**Files:**
- Modify: `skills/earn/gig/scripts/paid_intake_gate.py`
- Modify: `skills/earn/gig/scripts/delivery_attempt.py`
- Create: `skills/earn/gig/tests/test_upwork_paid_delivery.py`

- [ ] Write a failing test that rejects a job without full official scope, source files, deadline,
      revision terms and permitted data handling.
- [ ] Map the official contract into the existing project workspace; do not copy the Coconala DOM
      adapter or create a second builder.
- [ ] Require independent reviewer PASS bound to artifact hash.
- [ ] Persist delivery intent, execute once and require official delivery readback.
- [ ] Replay and assert zero new delivery effect.
- [ ] Acceptance: one real paid artifact is delivered and read back through the common kernel.

### Task 9: Record received Upwork net revenue

**Files:**
- Modify: `skills/earn/gig/scripts/revenue_collector.py`
- Modify: `skills/earn/gig/scripts/kpi_reconciler.py`
- Create: `skills/earn/gig/tests/test_upwork_revenue.py`

- [ ] Write failing tests for received gross, actual provider fee, refund, AI/subcontract cost,
      recurring-vs-one-off and source completeness.
- [ ] Normalize official transaction and fee IDs; prevent one receipt from belonging to two periods
      or payout batches.
- [ ] Keep missing source data `unknown`; never coerce an empty API result to zero without a complete
      source receipt.
- [ ] Reconcile the first real payment and match it to contract and delivery IDs.
- [ ] Acceptance: G4 closes only with received money and observed cost; proposal value remains funnel.

### Task 10: Prove three-job repeatability before widening markets

**Files:**
- Modify: `skills/earn/gig/scripts/kpi_readback_audit.py`
- Modify: `skills/earn/gig/scripts/lane_productivity.py`
- Create: `skills/earn/gig/tests/test_marketplace_repeatability_gate.py`

- [ ] Write a failing gate test for three independent contract IDs, complete receipts, zero duplicate
      effects, capacity consumption and refund/revision costs.
- [ ] Add a read-only portfolio projection; do not add another scheduler.
- [ ] Run three natural paid paths and reconcile each from provider source.
- [ ] Acceptance: G5 closes from official receipts, or remains open with the exact failing entity.

### Task 11: Probe Fiverr as the second-market candidate

**Files:**
- Create: `skills/earn/gig/scripts/fiverr_adapter.py`
- Create: `skills/earn/gig/tests/test_fiverr_adapter.py`
- Modify: `skills/earn/gig/config/marketplace-capabilities.json`

- [ ] Re-read Fiverr automation, AI, account and seller policies and record action-level evidence.
- [ ] Compare Fiverr's permitted inbound demand and measured expected net with current Lancers and
      Freelancer evidence; record why Fiverr remains or ceases to be the single candidate.
- [ ] Implement only Fiverr's read-only capability/auth/catalogue probe.
- [ ] If no approved machine interface exists, keep Fiverr discovery-only and stop Task 12. Write a
      replacement design before selecting another provider; do not silently substitute one here.
- [ ] Acceptance: one Fiverr official read receipt, zero mutation, and a recorded adopt or reject
      decision.

### Task 12: Carry Fiverr to first payment

**Prerequisite:** Task 11 proves the required Fiverr actions are permitted for the exact account.

**Files:**
- Modify: `skills/earn/gig/scripts/fiverr_adapter.py`
- Modify: `skills/earn/gig/scripts/reply_action.py`
- Create: `skills/earn/gig/tests/test_fiverr_order_effect.py`

- [ ] Reuse Tasks 4–9 in order: discovery, eligibility, effect/readback, sales, fulfillment, payment.
- [ ] Stop at each receipt gate; do not build later lanes before the prior real receipt exists.
- [ ] Prove Fiverr adds no provider branch to the builder, reviewer or finance arithmetic.
- [ ] Acceptance: G6 closes with one verified net payment and replay zero.

### Task 13: Activate bounded strategy evaluation

**Files:**
- Modify: `skills/earn/gig/scripts/experiment_evaluator.py`
- Modify: `skills/earn/gig/scripts/category_bandit.py`
- Create: `skills/earn/gig/tests/test_portfolio_evaluator.py`

- [ ] Write a failing test for incomplete outcome windows, one-variable mutation, guardrail failure,
      holdout identity and automatic revert.
- [ ] Feed only received net contribution, retention, revision/refund cost, quality and account-health
      evidence into the existing evaluator.
- [ ] Return `insufficient_evidence` until a complete comparison exists.
- [ ] Make policy, effect identity, receipt validation and accounting fields non-mutable inputs.
- [ ] Run one bounded live experiment and preserve before/after strategy receipts.
- [ ] Acceptance: G7 closes with an evidence-backed keep or revert, not a model opinion.

### Task 14: Add discovery-only human-work opportunity cards

**Files:**
- Create: `skills/earn/gig/config/human-work-platforms.json`
- Create: `skills/earn/gig/scripts/human_work_opportunities.py`
- Create: `skills/earn/gig/tests/test_human_work_opportunities.py`

- [ ] Encode Mercor, Prolific, Outlier, TELUS, uTest, Welocalize, Babel and LinkedIn as
      `human_work_only`, `owner_ceremony` or `unknown` from current evidence.
- [ ] Write a failing test proving the output has no apply, interview, task, message or delivery
      effect method.
- [ ] Emit owner-visible opportunity cards with source, compensation claim status, ceremony and
      expiry; label anecdotal earnings unverified.
- [ ] Acceptance: these sites can inform an owner without masquerading as autonomous revenue lanes.

### Task 15: Publish the portable installer without private state

**Files:**
- Modify: `install.sh`
- Modify: `skills/earn/gig/README.md`
- Create: `skills/earn/gig/tests/test_marketplace_public_package.py`

- [ ] Extend the guided setup to collect owner facts and run ceremonies before effect enablement.
- [ ] Default every provider action to effect-off until a valid local capability receipt exists.
- [ ] Test a clean temporary home for zero credentials, customer content, payout IDs, operator paths
      and live account identifiers.
- [ ] Run secret scanning, exact archive tests and one clean third-device setup.
- [ ] Acceptance: G10 closes only when a new owner can reach one permitted official receipt without
      copying the original operator's private state.

### Task 16: Close the USD 10,000 and JPY 10,000,000 portfolio gates

**Files:**
- Modify: `skills/earn/gig/scripts/daily_gig_report.py`
- Modify: `skills/earn/gig/scripts/kpi_reconciler.py`
- Create: `skills/earn/gig/tests/test_portfolio_revenue_gates.py`

- [ ] Write failing tests separating recurring, repeat one-off and first-time one-off received net.
- [ ] Require complete provider source receipts, recorded FX, actual costs and matched payout/bank
      reconciliation for the period.
- [ ] Display application, contract, delivery, payment and retention funnels separately.
- [ ] Close G8 only from at least USD 10,000 verified monthly net.
- [ ] Continue capacity-safe acquisition and close G9 only from at least JPY 10,000,000 verified
      monthly net; never convert a plan or balance into revenue.
- [ ] Acceptance: the report is reproducible from immutable receipts and returns `unknown` for every
      incomplete source.

## Final verification

- [ ] `git diff --check`
- [ ] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q skills/earn/gig/tests`
- [ ] `python3 -m compileall -q skills/earn/gig`
- [ ] Secret/PII scan returns zero tracked private values.
- [ ] Every provider mutation has capability → intent → effect → official readback → receipt.
- [ ] Every crash replay performs zero blind duplicate effects.
- [ ] Coconala remains on its verified release and current TODO order throughout expansion.
- [ ] A clean-device archive proves local installation without original operator state.
- [ ] Revenue report reconciles to provider and bank evidence; unknown remains visible.

Implementation is intentionally not started by this planning change.
