# Job ATS Resilience 10A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the local job loop recognize usable Ashby and Workday application surfaces after navigation commit, replay the observed shapes deterministically, and fail closed before any submission side effect.

**Architecture:** A small standard-library Python module classifies the ATS hostname and evaluates a redacted browser snapshot. The browser agent remains the only component that connects to CDP or performs form actions; it must persist and evaluate a snapshot before claiming a submission slot.

**Tech Stack:** Python 3 standard library, `unittest`, JSON fixtures, Markdown prompt contract.

## Global Constraints

- Never bypass CAPTCHA or infer nationality, work authorization, phone, address, experience, demographics, or other missing profile facts.
- The evaluator is pre-submit and side-effect free: no clicks, uploads, ledger claims, network requests, or browser ownership.
- Navigation readiness uses `wait_until=commit` plus user-facing controls.
- Main-frame controls are evaluated before attached frames.
- Order 10 remains `in_progress` until one real confirmed Ashby application and one real confirmed Workday application exist.

---

### Task 1: Replayable ATS readiness evaluator

**Files:**
- Create: `apps/job-search-loop/job_search_loop/ats.py`
- Create: `apps/job-search-loop/tests/test_ats.py`
- Create: `apps/job-search-loop/tests/fixtures/ats/ashby-application-surface.json`
- Create: `apps/job-search-loop/tests/fixtures/ats/workday-job-surface.json`
- Create: `apps/job-search-loop/tests/fixtures/ats/committed-without-surface.json`

**Interfaces:**
- Consumes: snapshot object with `version`, `url`, `navigation_committed`, and ordered `frames[].controls[]`.
- Produces: `detect_provider(url: str) -> str` and `evaluate_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]`.

- [ ] **Step 1: Write failing provider and fixture replay tests**

  Add literal expectations showing that Ashby and Workday hostnames classify correctly, both real surface fixtures return `ready=true` with `wait_until=commit`, and the committed empty fixture returns `ready=false`.

- [ ] **Step 2: Verify RED**

  Run:

  ```bash
  PYTHONPATH=apps/job-search-loop python3 -m unittest apps/job-search-loop/tests/test_ats.py -v
  ```

  Expected: import failure because `job_search_loop.ats` does not exist.

- [ ] **Step 3: Implement the minimal evaluator**

  Implement hostname suffix matching, strict snapshot shape checks, normalized control text, main-frame-first scanning, Ashby application readiness, Workday job/application readiness, and JSON CLI input/output. Return blockers instead of raising for a structurally valid but unusable page; raise `ValueError` for malformed snapshots.

- [ ] **Step 4: Verify GREEN and mutation boundaries**

  Run the Task 1 test command. Confirm the tests fail if `navigation_committed` is ignored, if Ashby no longer requires email/resume/submit, or if Workday no longer requires an Apply/application control.

- [ ] **Step 5: Commit and push**

  ```bash
  git add apps/job-search-loop/job_search_loop/ats.py apps/job-search-loop/tests
  git commit -m "feat(job-loop): add replayable ATS readiness"
  git push -u origin feat/job-ats-resilience-1
  ```

### Task 2: Require the evaluator in the live browser contract

**Files:**
- Modify: `apps/job-search-loop/prompts/daily-pass.md`
- Test: `apps/job-search-loop/tests/test_ats.py`

**Interfaces:**
- Consumes: the evaluator from Task 1 and the existing CDP owner evidence path.
- Produces: a mode-0600 ATS snapshot and evaluator result before `Ledger.claim_submission`.

- [ ] **Step 1: Write a failing consumer-behavior test**

  Run a controlled prompt-contract helper that must produce the exact pre-submit sequence: connect to the existing CDP owner, navigate with `wait_until=commit`, capture ordered frame/control metadata, persist mode 0600, run `python -m job_search_loop.ats`, require `ready=true`, then claim the ledger slot.

- [ ] **Step 2: Verify RED**

  Run the Task 1 test command and confirm failure because the current daily prompt does not expose the 10A contract.

- [ ] **Step 3: Add the minimal live prompt contract**

  Replace the generic navigation instruction with the exact 10A sequence. Preserve the existing immutable intent, fencing, CAPTCHA, legal-fact, and `submit_unknown` rules.

- [ ] **Step 4: Verify GREEN**

  Run the focused ATS test and the complete job-loop suite:

  ```bash
  PYTHONPATH=apps/job-search-loop python3 -m unittest apps/job-search-loop/tests/test_ats.py -v
  PYTHONPATH=apps/job-search-loop python3 -m unittest discover -s apps/job-search-loop/tests -p 'test_*.py'
  ```

- [ ] **Step 5: Commit and push**

  ```bash
  git add apps/job-search-loop/prompts/daily-pass.md apps/job-search-loop/tests/test_ats.py
  git commit -m "fix(job-loop): require commit-first ATS readiness"
  git push
  ```

### Task 3: Evidence, verification, and GitHub completion

**Files:**
- Modify: `docs/superpowers/specs/2026-07-28-job-search-loop-design.md`
- Modify: `docs/superpowers/plans/2026-07-29-job-ats-resilience-10a.md`
- Create: `docs/evidence/job-search-loop/2026-07-29-ats-resilience-10a.json`

**Interfaces:**
- Consumes: focused/full test outputs and a read-only existing-CDP probe.
- Produces: redacted evidence that distinguishes 10A completion from full order-10 completion.

- [ ] **Step 1: Run a read-only real-CDP probe**

  Against the existing browser owner, open one new page per public ATS URL, navigate with `wait_until=commit`, capture only provider, title, frame count, and normalized control kinds, then close only those pages. Do not fill or submit.

- [ ] **Step 2: Run fresh verification**

  Run focused ATS tests, the 114-test baseline plus new tests, `scripts/healthcheck.sh`, JSON parsing for every new fixture/evidence file, and `git diff --check`.

- [ ] **Step 3: Update state**

  Mark every completed plan checkbox. Keep backlog order 10 as `in_progress`, and record the exact test count, live probe result, branch head, and CI run in the evidence file.

- [ ] **Step 4: Commit, push, and merge**

  ```bash
  git add docs
  git commit -m "docs(job-loop): record ATS resilience 10A"
  git push
  gh pr create --repo Daisuke134/life-manager --base main --head feat/job-ats-resilience-1
  gh pr checks --watch
  gh pr merge --squash --delete-branch
  ```

  Completion requires the merged commit to be an ancestor of GitHub `main`.
