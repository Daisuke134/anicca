# JOB-CANONICAL-MERGE-1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `Daisuke134/life-manager` the only versioned source of the
already-live local job-search loop while preserving its private state, schedules,
idempotency, and actual side effects.

**Architecture:** Import the deterministic Python application into
`apps/job-search-loop` and extract its minimal model execution dependency into
`runtime/agent-runner`. Shell entrypoints derive `APP_ROOT`, repository root,
runner path, and XDG private paths instead of naming legacy checkouts. Launchd
files are rendered at install time so the source templates remain portable. The
Mac remains the only executor; cloud deployment is not part of this change.

**Tech Stack:** Python 3.12 standard library, zsh/bash, macOS launchd, SQLite,
existing CloakBrowser/Chrome CDP, `gog`, Telegram HTTP transport, unittest.

## Global Constraints

- Design SSOT:
  `docs/superpowers/specs/2026-07-28-job-search-loop-design.md`.
- Preserve all existing files under `~/.config/anicca/job-search`,
  `~/.local/state/anicca/job-search`, and
  `~/.local/share/anicca/job-search`.
- Do not unload the current LaunchAgents until the canonical checkout passes
  its complete test suite and healthcheck.
- Do not commit candidate contact data, credentials, cookies, `.env` content,
  generated resumes, application answers, or private evidence.
- Do not retry a `submit_unknown` application or duplicate an already-sent
  Telegram event during cutover verification.
- Keep the legacy source checkouts intact as rollback inputs until the
  canonical forced daily and inbox passes both succeed.
- No cloud service, Life Manager UI, or paid-user workflow is introduced.

---

### Task 1: Import the proven loop and establish migration RED

**Files:**

- Create: `apps/job-search-loop/**`
- Modify: `apps/job-search-loop/tests/test_launchd.py`
- Create: `apps/job-search-loop/tests/test_canonical_runtime.py`
- Modify:
  `docs/superpowers/specs/2026-07-28-job-search-loop-design.md`

- [x] Import the exact tracked tree from legacy commit
  `d86adf4d5f1422b28f6675ac7ffa08f3b9c7e987`.
- [x] Preserve and run the legacy baseline: 107 tests pass in 4.916 seconds.
- [x] Add behavior tests that install plists into a temporary home and assert
  both programs resolve inside a Life Manager checkout.
- [x] Add a behavior test that resolves each shell entrypoint's shared runtime
  contract and proves
  the runner/workdir arguments and proves neither legacy checkout is required.
- [x] Run only the new tests and observe failure caused by hard-coded legacy
  paths.
- [x] Update the spec backlog evidence with the RED command and failure.

### Task 2: Vendor the minimal model runner

**Files:**

- Create: `runtime/agent-runner/agent_runner.py`
- Create: `runtime/agent-runner/token_budget.py`
- Create: `runtime/agent-runner/config.json`
- Create: `runtime/agent-runner/tests/test_prompt_fail_closed.py`
- Create: `runtime/agent-runner/tests/test_token_budget.py`
- Modify: `apps/job-search-loop/job_search_loop/agent_runner.py`
- Modify: `apps/job-search-loop/tests/test_agent_runner.py`

- [x] Import runner behavior from profitable-claude commit
  `191b205c03ae37d32b0125da4a1892924d585205`.
- [x] Reduce the configuration to job-loop task classes and provider routes;
  remove personal account fields and unrelated candidate profiles.
- [x] Run the imported runner tests before adaptation and record the two
  expected failures caused by the legacy tests omitting required `daily_scope`.
- [x] Make the job-loop adapter resolve the in-repository runner by default
  while retaining explicit dependency injection for tests.
- [x] Run runner and adapter tests to GREEN.
- [x] Update the spec with file provenance and test evidence.

### Task 3: Make runtime and launchd paths canonical and portable

**Files:**

- Modify: `apps/job-search-loop/scripts/run-daily.sh`
- Modify: `apps/job-search-loop/scripts/run-inbox.sh`
- Modify: `apps/job-search-loop/scripts/install-launchd.sh`
- Modify: `apps/job-search-loop/scripts/healthcheck.sh`
- Modify: `apps/job-search-loop/scripts/multi-source-search.sh`
- Modify: `apps/job-search-loop/scripts/firecrawl-search.sh`
- Modify: `apps/job-search-loop/prompts/daily-pass.md`
- Modify: `apps/job-search-loop/launchd/*.plist`
- Modify: `apps/job-search-loop/job_search_loop/discovery.py`
- Modify: `apps/job-search-loop/README.md`
- Modify: path and launchd tests under `apps/job-search-loop/tests/`

- [x] Derive repository paths from each script location and derive private
  paths from XDG variables with current paths as defaults.
- [x] Replace checked-in absolute launchd files with renderable templates and
  make the installer support temporary `HOME` and `DESTDIR`-style test roots.
- [x] Stop sourcing the complete OpenClaw env; import only the allowlisted
  transport/provider variables required by the loop.
- [x] Keep the upstream framework as a pinned, replaceable cache under the
  private data root.
- [x] Run the new canonical runtime tests to GREEN.
- [x] Run all job-loop and runner tests fresh: 112 job-loop tests and 7 runner
  tests pass.

### Task 4: Shadow-verify and cut over the real local loop

**Files:**

- Modify:
  `docs/superpowers/specs/2026-07-28-job-search-loop-verification.md`
- Modify:
  `docs/superpowers/specs/2026-07-28-job-search-loop-design.md`
- Create:
  `docs/evidence/job-search-loop/2026-07-29-canonical-migration.json`

- [ ] Run the canonical healthcheck against existing private state while the
  legacy agents remain loaded.
- [ ] Verify SQLite integrity, current daily quota, outbox state, and current
  LaunchAgent targets; store only redacted evidence.
- [ ] Render and lint replacement plists, then atomically bootstrap both
  canonical agents.
- [ ] Confirm `launchctl print` shows daily 08:30 JST and inbox 900 seconds with
  canonical program paths.
- [ ] Kickstart the daily agent and verify a successful quota-safe/no-duplicate
  result.
- [ ] Kickstart the inbox agent and verify a successful reconciliation/prep
  result.
- [ ] Rerun healthcheck and verify installed paths resolve to a checkout whose
  Git origin is `Daisuke134/life-manager`.
- [ ] If any cutover check fails, reinstall the preserved legacy plists and
  record the rollback result before fixing forward.

### Task 5: Close the spec and publish the canonical source

**Files:**

- Modify:
  `docs/superpowers/specs/2026-07-28-job-search-loop-design.md`
- Modify:
  `docs/superpowers/plans/2026-07-29-job-canonical-merge.md`
- Modify:
  `docs/superpowers/specs/2026-07-28-job-search-loop-verification.md`

- [ ] Run the complete job-loop and runner suites from a clean command.
- [ ] Run secret and legacy-path scans over every added tracked file.
- [ ] Record exact commit, test counts, plist schedules, launchd exit status,
  ledger integrity, and redacted runtime receipt IDs in the spec.
- [ ] Change backlog order 0 to `completed` only after every acceptance
  criterion is evidenced.
- [ ] Fetch, commit, push the feature branch, merge through the repository's
  normal GitHub path, and confirm the remote canonical commit contains the
  implementation.
- [ ] Keep the runtime checkout and legacy rollback inputs until at least the
  next naturally scheduled daily and inbox executions are healthy.
