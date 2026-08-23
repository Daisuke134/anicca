# Job Hunter Summary v2 Restoration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore a current `summary.v2.json` projection from the one live Ledger and update it atomically after every daily and inbox transition.

**Architecture:** Restore the event-replay implementation from fixed repository commit `e84a6916b`, including exact funnel cohorts and privacy-safe ATS counts. Add an application-event high-water rowid and emit legacy `summary.v1.json` from the same in-memory Ledger snapshot; do not read or write another database.

**Tech Stack:** SQLite, Python `unittest`, atomic JSON replace, existing launchd scripts.

**Spec:** `docs/superpowers/specs/2026-07-28-job-search-loop-design.md` (48bx)

## Global Constraints

- `ledger.sqlite3` is the only application state SSOT.
- Event chains are replayed and validated; projection generation fails closed on a broken origin, discontinuity, invalid transition, or unproved late confirmation.
- No company, role, URL, contact, credential, or resume content enters `summary.v2`.
- `summary.v2` and compatibility `summary.v1` are written mode 0600 from one Ledger read.
- No new database, daemon, dependency, or side-effect owner is added.

---

### Task 1: Restore event-replayed summary v2

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/ledger.py`
- Modify: `apps/job-search-loop/job_search_loop/summary.py`
- Test: `apps/job-search-loop/tests/test_summary.py`

- [x] **Step 1: Write RED for v2 fields and event high-water**

Require version 2, current state/owner/ATS counts, exact funnel numerator/denominator/rate, `event_high_water`, deterministic `projection_sha256`, mode 0600, and absence of private application values.

- [x] **Step 2: Restore `Ledger.event_summary_rows()` from `e84a6916b`**

Replay immutable events in rowid order, validate the origin and every transition, preserve external-import and late-confirmation evidence gates, and return only privacy-safe application identity/state flags needed for projection.

- [x] **Step 3: Restore and extend `build_summary_v2()`**

Copy the fixed upstream implementation, add `event_high_water`, include it in the projection hash, and keep all cohort subset checks.

- [x] **Step 4: Emit v2 plus compatibility v1 from one snapshot**

Add `--compat-output`; read `event_summary_rows()` and max event rowid once, write v2 to `--output`, then derive v1 from the same rows and write it to the compatibility path.

### Task 2: Wire every resident transition

**Files:**
- Modify: `apps/job-search-loop/scripts/run-daily.sh`
- Modify: `apps/job-search-loop/scripts/run-inbox.sh`
- Test: `apps/job-search-loop/tests/test_canonical_runtime.py`
- Test: `apps/job-search-loop/tests/test_submission_confirmation.py`

- [x] **Step 1: Write RED for both projection files**

Require daily success and runner-failure paths plus inbox pre-scan/post-model paths to call summary with `summary.v2.json` and `--compat-output summary.v1.json`.

- [x] **Step 2: Update the shared summary calls**

Change only output arguments; keep the existing pre-scan and post-run ordering.

- [x] **Step 3: Verify restart consistency**

Run the CLI twice against a reopened Ledger and require byte-identical output and unchanged high-water.

- [ ] **Step 4: Full regression, immutable release, and live readback**

Require all Job Hunter/runner tests, release checksum/read-only verification, a scheduled wake, mode-0600 current `summary.v2`, and exact equality between its Workday counts/high-water and independent Ledger queries.

- [ ] **Step 5: Update spec and commit/push**

Record RED/GREEN counts, release SHA-256, run ID, event high-water, Workday counts, and next 10P dedupe gate.
