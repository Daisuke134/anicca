# Job Search Portable Local 12A Implementation Plan

> **For agentic workers:** Use Superpowers executing-plans and
> test-driven-development. Complete each checkbox in order and keep the job-search
> design spec synchronized in the same commit series.

**Goal:** Install the job-search loop into a clean user HOME with private XDG state,
provider-owned subscription authentication, and macOS/Linux user scheduling, without
embedding Daisuke-specific identity, credentials, or absolute paths.

**Architecture:** Add a pure Python setup module for profile validation, XDG path
resolution, provider preflight, and an atomic mode-0600 install receipt. Add one shell
dispatcher that invokes the setup module and delegates to the existing launchd
renderer or a new systemd user-unit renderer. Runtime paths consume only the selected
provider name from the private receipt.

**Tech Stack:** Python 3 standard library, zsh, launchd plistlib, systemd user units,
`unittest`.

---

### Task 1: Define the portable setup contract with failing tests

**Files:**
- Create: `apps/job-search-loop/tests/test_local_setup.py`
- Modify: `apps/job-search-loop/tests/test_canonical_runtime.py`

- [x] **Step 1: Add RED profile/XDG tests**

  Require absolute XDG roots, a valid user-supplied profile, exact private modes,
  atomic receipt creation, and no implicit overwrite.

- [x] **Step 2: Add RED provider tests**

  Fake authenticated/unauthenticated Codex and Claude executables. Verify
  deterministic `auto` selection and fail-closed missing auth without reading or
  copying credentials.

- [x] **Step 3: Add RED runtime selection test**

  Source `runtime-paths.sh` against the generated receipt and require
  `AGENT_RUNNER_PROVIDER` to equal the selected provider.

### Task 2: Implement private bootstrap and BYO provider selection

**Files:**
- Create: `apps/job-search-loop/job_search_loop/local_setup.py`
- Modify: `apps/job-search-loop/scripts/runtime-paths.sh`

- [x] **Step 1: Implement the smallest GREEN Python module**

  Validate through the existing `validate_profile`, copy atomically, enforce modes,
  run provider-owned status commands, and write a redacted receipt.

- [x] **Step 2: Load only the provider name at runtime**

  Read `install.json` with the existing Python interpreter. Reject unexpected
  provider names and never source the file as shell.

- [x] **Step 3: Run focused tests**

  ```bash
  PYTHONPATH=apps/job-search-loop python3 -m unittest \
    apps/job-search-loop/tests/test_local_setup.py \
    apps/job-search-loop/tests/test_canonical_runtime.py -v
  ```

### Task 3: Add macOS/Linux scheduler dispatch

**Files:**
- Create: `apps/job-search-loop/scripts/install-local.sh`
- Create: `apps/job-search-loop/scripts/install-systemd.sh`
- Create: `apps/job-search-loop/systemd/ai.anicca.job-search-daily.service`
- Create: `apps/job-search-loop/systemd/ai.anicca.job-search-daily.timer`
- Create: `apps/job-search-loop/systemd/ai.anicca.job-search-inbox.service`
- Create: `apps/job-search-loop/systemd/ai.anicca.job-search-inbox.timer`
- Modify: `apps/job-search-loop/tests/test_canonical_runtime.py`

- [x] **Step 1: Add RED rendered-unit tests**

  Assert absolute ExecStart paths, daily/inbox schedules, persistent daily catch-up,
  and no `/Users/anicca` or legacy checkout names.

- [x] **Step 2: Implement systemd renderer and dispatcher**

  Render private user units, validate them when `systemd-analyze` exists, then call
  only `systemctl --user daemon-reload` and `enable --now` for the two timers.
  `none` performs setup without scheduler side effects.

- [x] **Step 3: Verify fake scheduler adapters**

  Exercise Darwin and Linux dispatch with fake launchctl/systemctl adapters and
  assert the exact activation calls.

### Task 4: E2E, documentation, GitHub, and live safety

**Files:**
- Modify: `apps/job-search-loop/README.md`
- Modify: `docs/superpowers/specs/2026-07-28-job-search-loop-design.md`
- Modify: this plan
- Create: `docs/evidence/job-search-loop/2026-07-29-portable-local-12a.json`

- [x] **Step 1: Run a clean-HOME E2E**

  Use a temporary valid synthetic profile, fake authenticated provider, explicit
  `none` scheduler, and verify paths, modes, receipt, and overwrite protection.

- [x] **Step 2: Run full verification**

  Run focused tests, full job-loop tests, agent-runner tests, shell syntax,
  `git diff --check`, and JSON parsing.

- [x] **Step 3: Record redacted evidence and push**

  Update the plan/spec/README, write durable evidence, commit, and push.

- [ ] **Step 4: Merge and reflect canonical main**

  Create a PR, wait for every CI gate, squash merge, fast-forward the canonical
  checkout, and rerun the existing live healthcheck without reinstalling or
  duplicating LaunchAgents.
