# Gate 14 Mature Performance Write-back Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convert mature, comparable attribution snapshots into idempotent hook/tactic/renderer performance memory while refusing to learn from young, missing, or tiny cohorts.

**Architecture:** A pure scorer groups the latest experiment-attribution snapshots by product, platform, renderer, and checkpoint. It selects the deepest common attributable metric, requires ten mature real experiments, normalizes within the cohort, and appends an immutable decision row. Only a scored cohort may update hook EWMA, tactic status, and renderer results. Every run—including insufficient data—writes a truthful `hook-perf.jsonl` receipt.

**Tech Stack:** Python 3 standard library, JSONL ledgers, existing hook/playbook schemas, existing `lm` CLI.

---

### Task 1: Lock score and mutation invariants

**Files:**
- Create: `skills/earn/marketing-engine/brain/performance_writeback.py`
- Create: `skills/earn/marketing-engine/brain/test_performance_writeback.py`
- Create: `skills/earn/marketing-engine/schemas/hook-performance.schema.json`

Write RED tests for young snapshot, fewer than ten comparable experiments, deepest-common-metric selection, unknown/null exclusion, deterministic IDs, and exact replay. Implement the pure decision record until GREEN.

### Task 2: Implement safe state updates

**Files:**
- Modify: `skills/earn/marketing-engine/brain/performance_writeback.py`
- Modify: `skills/earn/marketing-engine/brain/test_performance_writeback.py`

Write RED tests for EWMA (`alpha=0.3`), winner/loser status, minimum three observations before hook retirement, 20% exploration preservation, tactic lookup through an exact experiment plan, missing tactic mapping, and atomic rollback. Implement only after the tests fail correctly.

### Task 3: Add CLI and current production receipt

**Files:**
- Modify: `skills/earn/marketing-engine/bin/lm`
- Create at run: `skills/earn/marketing-engine/state/hook-perf.jsonl`
- Create: `skills/earn/marketing-engine/evidence/writeback/gate14/current-run.json`

Add `lm measure writeback`. Run it on production attribution. The current 15-minute experiment must append one `insufficient_data` receipt, perform zero hook/tactic/renderer mutations, and name the missing maturity/cohort/tactic-plan evidence explicitly.

### Task 4: Verify and close only on real mature evidence

**Files:**
- Create: `skills/earn/marketing-engine/brain/verify_gate14.py`
- Modify: `specs/27-MARKETING-ENGINE-END-TO-END.md`
- Modify: `specs/26-MOBILE-APP-EBOOK-10K-LOOPS.md`

Run focused and full suites. Gate 14 remains evidence-incomplete until at least ten comparable mature, exactly plan-mapped production experiments exist and one real winner/loser decision updates canonical state. The Gate 12 preview lacks an exact tactic plan, stays reference-only, and does not reduce the ten new experiments required. Do not bypass this with fixtures, legacy uninstrumented posts, retroactive tactic guesses, or reduced cohort size.

Before generating the ten production treatments, add an immutable cohort-treatment manifest that binds the fixed body template, voice/rate, clip set, renderer/template version, caption style, CTA, target duration band, script hash and asset hash. Only `hook_id` and hook text may vary. Reject any asset outside the fixed duration band or without the complete treatment identity. The initial 7.698-second local item-001 draft is explicit rejected evidence and must never be posted.

Verified 2026-08-02: manifest/schema and Japanese kinsoku tests are green. Final v3 accepted items 001–010 are rendered, visually checked, and frozen with 10 unique experiments/hooks. The final two hooks came from bounded live competitor ingests with exact transcript/media/judgment evidence; no generated hook entered the observed-hook SSOT. All ten passed campaign, approval, intent, shadow, live Postiz upload/draft/promote and provider readback, and are queued daily at 20:15 JST from August 2 through August 11. Queue verification passes ten unique keys/tokens/schedules, 10/10 selected asset hashes and provider IDs, state `reconciled_provider`, and zero premature native receipts. Next collect each native receipt and 24-hour outcome, then run the real write-back.
