# Job Hunter Direct Wake Reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Send every Job Hunter application result and every completed 30-minute wake through the direct fenced Telegram transport with a positive provider message ID.

**Architecture:** Reuse `job_search_loop.telegram.send_once` and the existing SQLite outbox. Remove the remaining OpenClaw CLI call and stale `executable=` callers. Add one application-reporting wake command that derives company, role, outcome, reason, and next action from the run summary, Workday queue receipt, and Ledger, then invoke it once from the daily exit path.

**Tech Stack:** Python `unittest`, SQLite outbox, Telegram Bot API, zsh launchd entrypoints.

**Spec:** `docs/superpowers/specs/2026-07-28-job-search-loop-design.md` (48bw)

## Global Constraints

- The existing 30-minute launchd owner remains the only acquisition executor.
- Application resume and receipt-bound outcome events stay separately at-most-once.
- A `send_started` event is never blindly retried.
- Every final wake message starts with `Codex:::` and contains company, role, outcome, exact reason, and next action.
- No bot token, chat ID, credential, form answer, or resume content enters evidence or repo.
- No new dependency, queue, executor, browser, or Telegram bot is added.

---

### Task 1: Finish the direct Telegram migration

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/learning.py`
- Modify: `apps/job-search-loop/scripts/run-learning.sh`
- Test: `apps/job-search-loop/tests/test_learning_pass.py`
- Test: `apps/job-search-loop/tests/test_application_reporting.py`
- Test: `apps/job-search-loop/tests/test_operations.py`

**Interfaces:**
- Consumes: `send_once(..., requester=...)` and `send_document_once(..., requester=...)`.
- Produces: direct Bot API tests and callers with no removed `executable` argument.

- [x] **Step 1: Make the current eight-test baseline failures explicit**

Run the full Job Hunter suite and retain the exact failing test names in the spec.

- [x] **Step 2: Write RED tests for direct request injection**

Replace fake OpenClaw executables with a fake `requester(**kwargs)` returning `{"ok": true, "result": {"message_id": 901}}`. Assert a repeated event calls the requester once and returns the same message ID.

- [x] **Step 3: Remove stale executable plumbing**

Make learning delivery accept/inject `requester`; remove `--telegram-executable` from the resident script. Update stale message-shape expectations to the current enriched candidate envelope without weakening production validation.

- [x] **Step 4: Reconcile and deliver before inbox model scan**

Move the existing idempotent `submission_confirmation reconcile` and `application_reporting deliver` calls before `job_search_loop.inbox scan`; keep the post-model reconciliation for messages discovered by that scan.

- [x] **Step 5: Verify the restored direct-transport contracts**

Run the focused application-reporting, learning, operations, submission-confirmation, and Telegram suites. Expected: all PASS.

### Task 2: Emit one final report for every model wake

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/application_reporting.py`
- Modify: `apps/job-search-loop/scripts/run-daily.sh`
- Test: `apps/job-search-loop/tests/test_application_reporting.py`
- Test: `apps/job-search-loop/tests/test_canonical_runtime.py`

**Interfaces:**
- Consumes: run ID, Japan day, runner summary JSON, Workday discovery JSON, Ledger, and Telegram outbox.
- Produces: mode-0600 `wake-report.json` with `status`, `message_id`, and `event_key`.

- [x] **Step 1: Write RED for a quota-failed queued Workday wake**

Create a temporary Ledger row for one Workday company/role and a runner summary with `error_class=transient_quota`. Assert the report text includes `Codex:::`, company, role, `failed`, `transient_quota`, and `next_action=retry_with_available_provider_capacity`.

- [x] **Step 2: Implement the smallest wake-report builder and CLI**

Read only allowlisted fields from the run artifacts, bind a queued application ID to Ledger company/role, call `send_daily_report`, and atomically write its receipt. Missing or invalid artifacts become an explicit `unknown` reason, never a success.

- [x] **Step 3: Replace the OpenClaw pre-model block**

Delete the inline OpenClaw command and receipt parser. Register one exit handler after evidence creation; it preserves the original exit code and invokes the wake-report command once after summary refresh.

- [x] **Step 4: Verify failure, success, and dedupe paths**

Run fake-runner daily tests for nonzero and zero exit, assert one wake-report command each, and assert no `openclaw message send` remains in `run-daily.sh`.

- [ ] **Step 5: Full regression, immutable release, and live ACK**

Run all Job Hunter and runner tests with independent exit-code checks. Build/check/install a commit-pinned release, wait for the existing 30-minute owner, and require a positive provider message ID in the new wake evidence before closing 48bw.

- [ ] **Step 6: Update spec and commit/push**

Record RED/GREEN counts, release SHA-256, run ID, exact outcome, Telegram message ID, and next TODO 48bx.

### Task 3: Restore the assessment isolation regression gate

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/assessment_workflow.py`
- Test: `apps/job-search-loop/tests/test_assessment_workflow.py`

**Interfaces:**
- Consumes: the existing macOS `sandbox-exec` profile.
- Produces: the same home/network/write isolation while allowing the Xcode Python shim to redirect diagnostics to `/dev/null`.

- [x] **Step 1: Preserve the current RED evidence**

Run the two isolated-runner tests. Expected pre-fix result: `execution_failed`, rc 72, with `/dev/null: Operation not permitted` from the system Python shim.

- [x] **Step 2: Add the single required sandbox exception**

Add `(allow file-write* (literal "/dev/null"))` after the global write deny. Do not allow another device, directory, home path, or network operation.

- [x] **Step 3: Verify isolation remains enforced**

Run both tests and confirm the ordinary fixture completes while the second fixture still proves the outside-home secret and network connection are denied.

- [x] **Step 4: Re-run the entire Job Hunter and runner suites**

Require independent zero exit codes and zero failures before the 48bw immutable release is built.
