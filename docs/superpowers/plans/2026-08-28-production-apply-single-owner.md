# Production Apply Single Owner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject simultaneous or stale immutable-release applies before any production launchd plist changes.

**Architecture:** Keep `runtime/loop/lm_loop.py::apply_live` as the only mutation boundary. It takes one non-blocking host-wide `fcntl` lock, verifies the requested release is the exact target of `~/loops/current`, and repeats that comparison before every label swap. Rollback first moves `current`, then uses the same apply path.

**Tech Stack:** Python standard library (`fcntl`, `pathlib`), unittest, macOS launchd through the existing `launchctl-safe` wrapper.

## Global Constraints

- No new daemon, database, dependency, registry, or second apply command.
- A rejected apply performs zero plist writes and zero launchctl mutations.
- Production release code is immutable; loop state remains outside releases.
- Tests use temporary paths and no real launchd mutation.

---

### Task 1: Fence the shared apply boundary

**Files:**
- Modify: `runtime/loop/lm_loop.py`
- Modify: `bin/cut-loop-release.sh`
- Test: `runtime/loop/tests/test_lm_loop_apply.py`

**Interfaces:**
- Consumes: `apply_live(release_root, agents_dir, launchctl_safe, target=None)` and the `~/loops/current` symlink.
- Produces: `apply_live(..., current=None, lock_path=None)` with zero-mutation rejection for a busy owner or a non-current release, plus `activate_current(current, release_root, lock_path)` using the same lock.

- [ ] **Step 1: Write the failing tests**

Add one test that holds an exclusive lock and asserts `apply_live` raises `RuntimeError("production apply is already owned")` before its launchctl recorder receives a call. Add one test with `current -> release-b` and requested `release-a` that asserts `RuntimeError("apply release is not current")`, no plist file, and no launchctl call. Add a positive current-release apply proving the recorder observes launchctl. Add a busy-lock activation test proving `current` stays unchanged.

- [ ] **Step 2: Run tests to verify RED**

Run: `python3 -m unittest runtime.loop.tests.test_lm_loop_apply`

Expected: FAIL because `apply_live` does not accept `current` or `lock_path` and does not reject either condition.

- [ ] **Step 3: Write the minimal implementation**

In `apply_live`, open `lock_path` with mode `0600`, acquire `fcntl.LOCK_EX | fcntl.LOCK_NB`, and raise the exact busy-owner error on `BlockingIOError`. Resolve `current` strictly and compare it with `release_root.resolve()` before planning and immediately before each `install_one`; raise the exact non-current error on mismatch. Keep the file handle open until every readback completes. Add `activate_current` using the same lock and `os.replace`; call it from `cut-loop-release.sh` instead of direct `ln`/`mv`.

- [ ] **Step 4: Run focused and adjacent tests**

Run: `python3 -m unittest runtime.loop.tests.test_lm_loop_apply runtime.loop.tests.test_loop_cleanup runtime.loop.tests.test_macos_loop_registry`

Expected: PASS with zero warnings or errors.

- [ ] **Step 5: Run isolated behavior verification**

Use temporary release/current/LaunchAgents paths and a launchctl recorder. Prove busy lock and stale release both return nonzero and leave the target directory byte-empty; prove current release follows the existing successful apply path.

- [ ] **Step 6: Commit and push**

```bash
git fetch origin
git add runtime/loop/lm_loop.py runtime/loop/tests/test_lm_loop_apply.py bin/cut-loop-release.sh docs/superpowers/plans/2026-08-28-production-apply-single-owner.md
git commit -m "fix(loop-control): fence production apply owner"
git push origin HEAD
```

### Task 2: Retire the legacy installer bypass

**Files:**
- Modify: `bin/loop-install.sh`
- Create: `runtime/loop/tests/test_legacy_loop_install.py`

**Interfaces:**
- Consumes: any legacy `bin/loop-install.sh LABEL` invocation.
- Produces: exit 64 with an instruction to run `bin/lm-loop apply`; zero plist or launchctl mutation.

- [ ] **Step 1: Write and verify the RED test**

Execute `loop-install.sh` with temporary HOME and fake `launchctl-safe`; assert the old script attempts preflight. Then change the expected contract to exit 64, mention `lm-loop apply`, and leave the fake launchctl call ledger absent.

- [ ] **Step 2: Replace the legacy mutation implementation**

Keep `loop-install.sh` as a compatibility tombstone containing only the migration message and exit 64. Do not forward label arguments because the registry loop IDs and launchd labels are different namespaces.

- [ ] **Step 3: Verify**

Run: `python3 -m unittest runtime.loop.tests.test_legacy_loop_install`

Expected: PASS; fake launchctl calls remain zero.

- [ ] **Step 4: Commit and push**

```bash
git fetch origin
git add bin/loop-install.sh runtime/loop/tests/test_legacy_loop_install.py
git commit -m "chore(loop-control): retire legacy installer"
git push origin HEAD
```

### Task 3: Record measured production state

**Files:**
- Modify: `docs/superpowers/specs/2026-08-27-x-tweeter-chinese-hourly-design.md`

**Interfaces:**
- Consumes: merged commit SHA, focused test output, installed plist SHA readback.
- Produces: one current status section and ordered remaining TODOs without claiming runtime completion from tests alone.

- [ ] **Step 1: Update the canonical spec**

Record the single-owner/CAS contract as implemented. Keep live 3-lane publication, replay-zero, healthcheck closure, and 60-minute view sampling open until their official receipts exist.

- [ ] **Step 2: Self-review the spec**

Run: `rg -n 'TBD|TODO|c50e98ff|8377ba1b|production apply owner' docs/superpowers/specs/2026-08-27-x-tweeter-chinese-hourly-design.md`

Expected: no placeholders or stale assertion that all six jobs currently run one unchanging SHA.

- [ ] **Step 3: Commit, push, and merge through main**

```bash
git fetch origin
git add docs/superpowers/specs/2026-08-27-x-tweeter-chinese-hourly-design.md
git commit -m "docs(x): record fenced apply ownership"
git push origin HEAD
```
