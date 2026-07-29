# Job Workday Surface 10B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replay Workday Apply-choice and account-gate surfaces, distinguish navigation readiness from submission-claim readiness, and keep every pre-application step outside the quota fence.

**Architecture:** Extend the existing pure snapshot evaluator with a `claim_ready` result and two Workday surface detectors. Keep Workday progression in the browser prompt; keep the Ledger provider-neutral by accepting only evaluator results with `claim_ready=true`.

**Tech Stack:** Python 3 standard library, `unittest`, sanitized JSON replay fixtures, Markdown browser contract.

## Global Constraints

- Use only the existing `ai.anicca.job-search-daily` CDP owner for live probes.
- Live verification may click public `Apply` and `Apply Manually` navigation controls, but must not enter identity data, create an account, upload a file, claim a slot, or submit.
- Never infer nationality, citizenship, visa, or work authorization.
- Surface detection uses user-facing role/text plus stable input types; generated CSS classes are excluded.
- Order 10 remains `in_progress` until real confirmed Ashby and Workday applications exist.

---

### Task 1: Workday surface state machine

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/ats.py`
- Modify: `apps/job-search-loop/tests/test_ats.py`
- Create: `apps/job-search-loop/tests/fixtures/ats/workday-apply-choice-surface.json`
- Create: `apps/job-search-loop/tests/fixtures/ats/workday-create-account-surface.json`

**Interfaces:**
- Consumes: existing version-1 redacted snapshots.
- Produces: evaluator output with `claim_ready: bool` and surfaces `workday_apply_choice` / `workday_account_create`.

- [ ] **Step 1: Add failing literal replay tests**

  Add real-shape sanitized fixtures. Assert exact outputs for the choice and account surfaces, update existing Ashby/Workday expectations with literal `claim_ready` values, and assert a missing password-verification control does not classify as account creation.

- [ ] **Step 2: Verify RED**

  ```bash
  PYTHONPATH=apps/job-search-loop python3 -m unittest apps/job-search-loop/tests/test_ats.py -v
  ```

  Expected: failures because `claim_ready` and both new surfaces are absent.

- [ ] **Step 3: Implement the minimal evaluator extension**

  Detect the three-choice modal by visible semantic text; detect Create Account by email, two password inputs, consent checkbox, and Create Account action. Return `claim_ready=true` only for `ashby_application`, `workday_application`, or `generic_application`.

- [ ] **Step 4: Verify GREEN**

  Run the focused ATS tests and mutate each required control to confirm the corresponding fixture fails closed.

- [ ] **Step 5: Commit and push**

  ```bash
  git add apps/job-search-loop/job_search_loop/ats.py apps/job-search-loop/tests
  git commit -m "feat(job-loop): model Workday pre-application surfaces"
  git push -u origin feat/job-workday-surface-10b
  ```

### Task 2: Provider-neutral claim gate and live prompt progression

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/ledger.py`
- Modify: `apps/job-search-loop/prompts/daily-pass.md`
- Modify: `apps/job-search-loop/tests/test_ledger.py`

**Interfaces:**
- Consumes: evaluator `claim_ready`.
- Produces: a Ledger claim boundary that rejects all `claim_ready=false` snapshots and a browser contract that advances Workday one semantic surface at a time.

- [ ] **Step 1: Add a failing ready-but-not-claimable Ledger table test**

  Replay `workday_job`, `workday_apply_choice`, and `workday_account_create`; assert each raises `ATS snapshot is not claim-ready` and leaves the daily slot count at zero.

- [ ] **Step 2: Verify RED**

  Run the focused Ledger test. Expected: the new choice/account fixtures are accepted or produce the old provider-specific behavior.

- [ ] **Step 3: Implement the minimal claim and prompt changes**

  Replace the Workday surface-name special case with `if not snapshot_evaluation["claim_ready"]`. Update the prompt to click Apply, prefer Apply Manually, recapture/evaluate after every surface transition, and stop at account create/sign-in unless the private credential path is present.

- [ ] **Step 4: Verify GREEN and the full suite**

  ```bash
  PYTHONPATH=apps/job-search-loop python3 -m unittest apps/job-search-loop/tests/test_ledger.py -v
  PYTHONPATH=apps/job-search-loop python3 -m unittest discover -s apps/job-search-loop/tests -p 'test_*.py'
  ```

- [ ] **Step 5: Commit and push**

  ```bash
  git add apps/job-search-loop/job_search_loop/ledger.py apps/job-search-loop/prompts/daily-pass.md apps/job-search-loop/tests/test_ledger.py
  git commit -m "fix(job-loop): gate claims on application surfaces"
  git push
  ```

### Task 3: Real replay, evidence, CI, and merge

**Files:**
- Modify: `docs/superpowers/specs/2026-07-28-job-search-loop-design.md`
- Modify: `docs/superpowers/plans/2026-07-29-job-workday-surface-10b.md`
- Create: `docs/evidence/job-search-loop/2026-07-29-workday-surface-10b.json`

**Interfaces:**
- Consumes: local test outputs and the existing-CDP read-only Workday flow.
- Produces: redacted durable evidence and an updated order-10 status.

- [ ] **Step 1: Replay the real Workday progression**

  Connect to the existing CDP owner, navigate with commit, click Apply, capture choice metadata, click Apply Manually, wait for Create Account semantic controls, capture metadata, and close only the created page.

- [ ] **Step 2: Verify no side effects and full health**

  Confirm zero field fills, accounts, uploads, claims, and submits; run focused/full tests, runner tests, JSON parsing, `git diff --check`, and job-loop healthcheck.

- [ ] **Step 3: Record evidence and push**

  Update this plan and the SSOT spec, write redacted evidence, commit, and push.

- [ ] **Step 4: Merge through GitHub**

  Create a PR to `main`, wait for all five CI gates, squash merge, update the canonical checkout, kickstart the existing daily/inbox LaunchAgents, and verify both exit zero plus ledger integrity.
