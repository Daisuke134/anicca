# Agent Economy Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a release-backed, restart-safe launchd job for the agent-economy loop.

**Architecture:** Reuse `bin/cut-loop-release.sh`, `~/loops/current`, and `bin/plistgen.py`. A TOML declaration supplies the continuous daemon entrypoint and stable environment paths; the generated plist never points at a checkout worktree.

**Tech Stack:** Python 3 `plistlib`/`tomllib`, POSIX shell, Node.js `node:test`.

**Spec:** `docs/superpowers/specs/2026-08-21-agent-economy-design.md`

## Global Constraints

- Launchd runs only from an immutable release selected by `~/loops/current`.
- Loop state lives outside releases under `~/loops/agent-economy`.
- No private key, credential, or user-specific wallet is committed.
- Existing generated jobs must retain their current behavior.
- The plist generator must support either interval/calendar jobs or a continuous KeepAlive job, never both.

---

### Task 1: Declare and verify the continuous agent-economy job

**Files:**
- Create: `loops/agent-economy/loop.toml`
- Modify: `bin/plistgen.py`
- Test: `test/agent-economy-control-plane.test.mjs`

**Interfaces:**
- Consumes: `bin/plistgen.py --loops-dir loops --out-dir <dir> --home <home> --current <current> --only agent-economy`.
- Produces: `ai.anicca.agent-economy-loop.plist` with `ProgramArguments=["/bin/bash", "<home>/loops/current/skills/agent-economy/launch.sh"]`, `KeepAlive=true`, `RunAtLoad=true`, `ANICCA_REPO=<home>/loops/current`, `ANICCA_HOME=<home>/loops/agent-economy`, and no `StartInterval` or `StartCalendarInterval`.

- [ ] **Step 1: Write the failing test**

  The test invokes the real generator into a temporary directory, parses the generated plist with Python `plistlib`, and asserts the exact stable path and continuous-job contract.

- [ ] **Step 2: Run the test to verify it fails**

  Run: `node --test test/agent-economy-control-plane.test.mjs`
  Expected: FAIL because `loops/agent-economy/loop.toml` does not exist and the generator cannot render a continuous job.

- [ ] **Step 3: Implement the minimal declaration and generator support**

  Add the TOML declaration, expand `~` in declared environment values using the already-existing `expand()` helper, and add `keep_alive`/`run_at_load` fields to generated plists. Reject a declaration that combines continuous mode with interval/calendar cadence.

- [ ] **Step 4: Run the focused test to verify it passes**

  Run: `node --test test/agent-economy-control-plane.test.mjs`
  Expected: PASS with zero failures.

- [ ] **Step 5: Run neighboring generator and installation checks**

  Run: `npm run test:install` and `npm run test:oss`.
  Expected: both commands exit 0; existing generated jobs remain valid.

- [ ] **Step 6: Commit and push**

  Run: `git add loops/agent-economy/loop.toml bin/plistgen.py test/agent-economy-control-plane.test.mjs docs/superpowers/specs/2026-08-21-agent-economy-design.md docs/superpowers/plans/2026-08-21-agent-economy-control-plane.md && git commit -m "fix: anchor agent economy loop to immutable release" && git push -u origin feat/agent-economy-implementation`

