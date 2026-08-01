# Capafy P3 Portfolio Quality Implementation Plan

> **Execution rule:** Use `executing-plans`, TDD, and verification-before-completion. Complete one task, update the parent living spec, commit, and then continue. No human approval or elapsed-day warmup gate.

**Goal:** Audit and govern all 31 Capafy products so only evidence-backed, economically coherent products receive Builder or Marketer effort.

**Design:** [`../specs/2026-08-02-capafy-p3-portfolio-quality-design.md`](../specs/2026-08-02-capafy-p3-portfolio-quality-design.md)

### Task 1: Deterministic portfolio snapshot and schema

**Files:** create `capafy_portfolio.py`, schema, and tests; consume P2 projection plus fresh inventory.

- [x] Write RED tests for 31-row preservation, `sales=null` preservation, money precision, evidence URLs, enum validation, and atomic/idempotent writes.
- [x] Implement `snapshot` and `validate` commands without business judgment.
- [x] Kickstart against production and require 31 validated records with no fabricated decisions.
- [x] Update living spec and commit.

### Task 2: Evidence-backed agent audit

**Files:** create audit prompt/runner contract, result validator, and tests; reuse the shared agent runner and evidence directory.

- [x] Write RED tests proving deterministic code cannot supply target, recurring mechanism, purchase model, price, or decision.
- [x] Require cited source URL/timestamp/claim/confidence and explicit unknowns.
- [x] Run one bounded agent audit over all current products; reject partial or placeholder output.
- [x] Validate all 31 records and update the living spec.

### Task 3: Selection and single-experiment enforcement

**Files:** modify listing selector/controller and tests.

- [ ] Refuse unaudited, paused, retire-candidate, non-owned, or already-active-conflicting products.
- [ ] Require previous experiment measurement before replacement.
- [ ] Select from evidence without hardcoded niche/product rankings.
- [ ] Prove failure releases browser ownership and emits no success event.

### Task 4: Draft, rejected, and overlap cleanup queue

**Files:** create portfolio decision queue and tests; no destructive remote deletion.

- [ ] Identify the two review items, one draft, one rejected item, and overlapping offers from the registry.
- [ ] Let the agent choose one repair/reposition attempt or `retire_candidate`, with evidence and stop condition.
- [ ] Exclude paused/retire-candidate items from Builder and Marketer immediately.
- [ ] Remotely verify any submitted repair and record its public/review URL.

### Task 5: Packaging and unit-economics experiment

**Files:** add purchase-model/value-metric experiment contract and event types/tests.

- [ ] Support `subscription`, `usage`, `one_time`, and `hybrid` proposals without hardcoded price points.
- [ ] Require renewal reason for subscription, metered unit for usage, bounded deliverable for one-time, and both for hybrid.
- [ ] Calculate projected and observed contribution after platform fees and recorded model/tool cost.
- [ ] Activate one highest-evidence bounded experiment and record success/stop observables.

### Task 6: Verified handoff, reporting, and P3 production closure

**Files:** extend the event projection, Telegram renderer, company dashboard, production contract, and living spec.

- [ ] Builder remotely verifies the chosen product change and hands the real URL to Marketer.
- [ ] Marketer uses the immediate owner-verified publication path; no warmup or duplicate publication.
- [ ] Telegram and `/company/` show the same active experiment and projection ID.
- [ ] Seed one failed registry/experiment write and prove autonomous repair and exactly-once closure.
- [ ] Run the full P0-P3 suite and runtime parity audit; write a mode-`0600` verification artifact.
- [ ] Update status to `P0-P3 verified; P4 active` and commit closure.
