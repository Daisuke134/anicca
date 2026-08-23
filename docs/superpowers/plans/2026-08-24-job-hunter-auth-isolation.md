# Job Hunter Auth Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent another Life Manager or interactive Codex process from changing the authentication target used by the 30-minute Job Hunter owner.

**Architecture:** Keep the existing runner and its fail-closed source/target identity check. Use a private Job Hunter automation home and make the installer atomically bind the active `CODEX_HOME/auth.json` to a stable private Job Hunter alias without copying credential bytes. The runner reads only that alias, so another Life Manager loop cannot change its target and a user can select the intended authenticated Codex account at install time.

**Tech Stack:** JSON, Python `unittest`, existing Life Manager agent runner.

**Spec:** `docs/superpowers/specs/2026-07-28-job-search-loop-design.md` (48bv)

## Global Constraints

- `ai.anicca.job-search-daily` remains the only acquisition owner.
- `StartInterval=1800` remains unchanged.
- The runner reads `~/.config/anicca/job-search/codex-auth.json`; the installer binds it to the selected `CODEX_HOME/auth.json` by symlink, and credential bytes are never copied into repo, logs, evidence, or Telegram.
- No second executor, browser, profile, credential store, or dependency is added.
- A scheduled launchd wake, not a direct `run-daily.sh` invocation, is the production E2E gate.

---

### Task 1: Isolate the Codex automation home

**Files:**
- Modify: `runtime/agent-runner/config.json`
- Test: `apps/job-search-loop/tests/test_canonical_runtime.py`
- Update after E2E: `docs/superpowers/specs/2026-07-28-job-search-loop-design.md`

**Interfaces:**
- Consumes: runner provider config keys `automation_home` and `auth_file`.
- Produces: `CODEX_HOME=~/.local/state/anicca/job-search/codex-runner`, whose `auth.json` target resolves through the install-selected private alias.

- [x] **Step 1: Write the failing test**

```python
def test_runner_codex_home_is_job_search_owned(self):
    config_path = REPO_ROOT / "runtime" / "agent-runner" / "config.json"
    provider = json.loads(config_path.read_text(encoding="utf-8"))["providers"]["codex"]

    self.assertEqual(
        provider["automation_home"],
        "~/.local/state/anicca/job-search/codex-runner",
    )
    self.assertEqual(
        provider["auth_file"],
        "~/.config/anicca/job-search/codex-auth.json",
    )
```

- [x] **Step 2: Run the test and verify RED**

Run: `python3 -m unittest apps.job-search-loop.tests.test_canonical_runtime.CanonicalRuntimeTests.test_runner_codex_home_is_job_search_owned -v`

Expected: FAIL because the current value is `~/.local/state/life-manager/codex-runner`.

- [x] **Step 3: Apply the minimal configuration change**

```json
"automation_home": "~/.local/state/anicca/job-search/codex-runner",
"auth_file": "~/.config/anicca/job-search/codex-auth.json"
```

- [x] **Step 4: Verify GREEN and focused regression**

Run: `python3 -m unittest apps.job-search-loop.tests.test_canonical_runtime runtime.agent-runner.tests.test_terra_default -v`

Expected: all tests PASS.

- [x] **Step 5: Build and activate the immutable release**

Run the existing Job Hunter release/install path. Verify the installed runner config contains the job-search-owned automation home and that the source/target paths resolve identically without printing credential contents.

- [x] **Step 6: Trigger and verify production through the existing owner**

While the owner is idle, use `launchctl kickstart -k` for `ai.anicca.job-search-daily`. Verify Luna starts for queued JR2008507, the old auth mismatch is absent, and all application effects remain fenced.

- [x] **Step 7: Update the spec and commit/push**

Record RED, GREEN, release, launchd E2E, Telegram receipt, Ledger state, and the next ordered TODO in 48bv. Commit only owned files and push the existing remote job-search branch.
