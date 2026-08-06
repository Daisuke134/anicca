# Job Hunter Self-Healing Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the installed Job Hunter detect, repair, verify, release, and resume a failed application without the main development session.

**Architecture:** Extend the existing allowlisted OpenTelemetry index and Guardian instead of adding another scheduler or business-state store. Guardian creates immutable Repair Cases; an isolated Codex repair executor produces a tested release; a no-send canary and verifier gate promotion; the resident application lane resumes from durable state.

**Tech Stack:** Python 3.12, SQLite, OpenTelemetry 1.44.0, native Collector 0.158.0, Codex CLI/SDK, launchd, existing immutable release and Telegram outbox.

## Global Constraints

- Ledger receipts, not telemetry or model prose, are application truth.
- Only the installed resident application lane may perform ATS/Gmail side effects.
- Repair, verification, and canary processes have zero external-send authority.
- Terra is the sole routine self-healing model for diagnosis, RED/GREEN repair, and
  retry. Sol is never a resident or polling model.
- Invoke at most one fresh read-only Sol verification per candidate, and only after
  RED, GREEN, focused, full-suite, privacy, and release-build receipts all pass.
- Reject failed executable gates back to Terra without invoking Sol.
- Agents SDK does not replace launchd scheduling, Ledger truth, Guardian policy, or
  the ChatGPT-authenticated Codex runtime.
- Unknown post-send effects are observed and never replayed automatically.
- Private profile values, form answers, raw HTML/URLs, email bodies, cookies, tokens, and screenshot bytes never enter traces, Repair Cases, repository files, or model output.
- Each task closes with focused tests, the complete Job Hunter suite, SSOT update, commit, and push.

---

### Task 1: Close the joined observability proof (`L-49K0C2O6`)

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/telemetry.py`
- Modify: `apps/job-search-loop/job_search_loop/trace_index.py`
- Modify: `apps/job-search-loop/tests/test_trace_index.py`
- Modify: `docs/superpowers/plans/2026-08-02-job-hunter-local-completion.md`

**Interfaces:**
- Consumes: Collector JSONL spans and existing resource attributes.
- Produces: `TraceIndex.timeline(application_id=...)` joined by trace ID with release, lane, actor, application, route, failure, evidence, and confirmation fields.

- [ ] **Step 1: Write the failing joined-timeline test**

```python
def test_timeline_joins_resource_and_span_identity_without_private_values(self):
    # Write one hourly_pass/candidate/route/form/confirmation trace with resource
    # service.version, job_hunter.lane and resident actor, plus an injected email key.
    # Assert timeline returns the safe joined identifiers and excludes the email.
```

- [ ] **Step 2: Run RED**

Run: `cd apps/job-search-loop && python3 -m unittest tests.test_trace_index.TraceIndexTests.test_timeline_joins_resource_and_span_identity_without_private_values -v`

Expected: FAIL because resource identity and joined timeline are not stored.

- [ ] **Step 3: Implement the minimal indexed projection**

Add only safe columns and parse resource attributes independently from span attributes. Preserve `ALLOWED_ATTRIBUTES`; add no private key.

- [ ] **Step 4: Run GREEN and complete suite**

Run: `cd apps/job-search-loop && python3 -m unittest tests.test_trace_index tests.test_telemetry -v && python3 -m unittest discover -s tests -v`

Expected: PASS with zero failures.

- [ ] **Step 5: Ingest the current resident trace and verify O6**

Query the private trace index for the current application. Record an honest gap if a required span was not emitted; never synthesize it.

- [ ] **Step 6: Update SSOT, commit, and push**

```bash
git add apps/job-search-loop/job_search_loop/telemetry.py apps/job-search-loop/job_search_loop/trace_index.py apps/job-search-loop/tests/test_trace_index.py docs/superpowers/plans/2026-08-02-job-hunter-local-completion.md
git commit -m "feat(job-hunter): join resident observability timeline"
git push canonical HEAD:docs/job-hunter-spec-20260805
```

### Task 2: Build content-addressed Repair Cases (`L-66A`, `L-66B`)

**Files:**
- Create: `apps/job-search-loop/job_search_loop/repair_case.py`
- Create: `apps/job-search-loop/tests/test_repair_case.py`
- Modify: `apps/job-search-loop/job_search_loop/guardian_recovery.py`
- Modify: `docs/superpowers/plans/2026-08-02-job-hunter-local-completion.md`

**Interfaces:**
- Consumes: one sanitized indexed failure and immutable receipt paths/hashes.
- Produces: `build_repair_case(...) -> {case_id, case_path, status}` and mode-0600 canonical JSON.

- [ ] **Step 1: Write RED for content addressing, dedupe, and privacy rejection**

```python
def test_same_sanitized_failure_returns_same_private_case(self): ...
def test_case_rejects_raw_url_email_answer_and_unknown_post_send(self): ...
```

- [ ] **Step 2: Run RED**

Run: `cd apps/job-search-loop && python3 -m unittest tests.test_repair_case -v`

Expected: FAIL because `repair_case` does not exist.

- [ ] **Step 3: Implement canonical case builder**

Canonicalize the allowlisted payload, hash it for `case_id`, atomically write mode
0600, and return the existing case on exact replay. Encode allowed edit roots and the
exact no-send reproduction command. Reject uncertain post-send boundaries.

- [ ] **Step 4: Connect Guardian without changing existing bounded recovery**

Guardian creates a case only for an unrecovered repairable fault. Existing permission
and stale pre-send deterministic repairs remain local and bounded.

- [ ] **Step 5: Verify and commit**

Run focused Guardian/Repair Case tests, then the complete suite. Update L-66A/B and commit `feat(job-hunter): create immutable repair cases`.

### Task 3: Run isolated Terra repair with executable gates (`L-66C`)

**Files:**
- Create: `apps/job-search-loop/job_search_loop/repair_executor.py`
- Create: `apps/job-search-loop/tests/test_repair_executor.py`
- Create: `apps/job-search-loop/prompts/repair-agent.md`
- Modify: `runtime/agent-runner/config.json`
- Modify: `docs/superpowers/plans/2026-08-02-job-hunter-local-completion.md`

**Interfaces:**
- Consumes: Repair Case path and failing release SHA.
- Produces: structured repair receipt containing worktree, commit, RED/GREEN/focused/full/privacy results, diff hash, candidate archive, and no external-action audit.

- [ ] **Step 1: Write RED for authority and gate ordering**

```python
def test_executor_rejects_send_tools_and_requires_red_before_patch(self): ...
def test_executor_requires_focused_full_privacy_and_release_receipts(self): ...
```

- [ ] **Step 2: Run RED**

Run: `cd apps/job-search-loop && python3 -m unittest tests.test_repair_executor -v`

- [ ] **Step 3: Implement isolated worktree executor**

Create one worktree under the Job Hunter repair root, invoke Terra with Apps, Browser,
Gmail, Telegram, Calendar, and live submit disabled, and validate structured receipts
rather than agent prose.

- [ ] **Step 4: Verify a harmless injected regression**

Use a fixture fault that requires a one-line production repair. Prove the executor
observes RED before GREEN and builds a content-addressed candidate release.

- [ ] **Step 5: Run full verification, update SSOT, commit, and push**

Commit `feat(job-hunter): execute isolated agent repairs` only after all executable gates pass.

### Task 4: Add independent Sol falsification and no-send canary (`L-66C`, `L-66D`)

**Files:**
- Create: `apps/job-search-loop/job_search_loop/repair_verifier.py`
- Create: `apps/job-search-loop/job_search_loop/repair_canary.py`
- Create: `apps/job-search-loop/tests/test_repair_verifier.py`
- Create: `apps/job-search-loop/tests/test_repair_canary.py`
- Create: `apps/job-search-loop/prompts/repair-verifier.md`

**Interfaces:**
- Consumes: Repair Case and repair receipt.
- Produces: verifier receipt and canary receipt; neither may mutate production state.

- [ ] **Step 1: Write RED for unresolved finding rejection and transport audit**

```python
def test_verifier_finding_blocks_candidate(self): ...
def test_canary_fails_if_any_external_transport_is_called(self): ...
```

- [ ] **Step 2: Implement fresh read-only Sol verifier**

Require a new thread/context. Validate the executable evidence again and reject any
unresolved structured finding. Enforce one Sol invocation per candidate hash and
reject the invocation before model startup unless all Terra executable-gate receipts
are present and passing.

- [ ] **Step 3: Implement exact no-send reproduction canary**

Run the Repair Case command against isolated state. Capture the original failure
absence, external transport call count zero, and confirmation classifier regression
checks.

- [ ] **Step 4: Verify, update SSOT, commit, and push**

Run focused plus full suite. Commit `feat(job-hunter): gate repairs with no-send canary`.

### Task 5: Promote, roll back, and resume the same application (`L-66D`, `L-66E`)

**Files:**
- Create: `apps/job-search-loop/job_search_loop/repair_release.py`
- Create: `apps/job-search-loop/tests/test_repair_release.py`
- Modify: `apps/job-search-loop/job_search_loop/release_activation.py`
- Modify: `apps/job-search-loop/scripts/run-daily.sh`

**Interfaces:**
- Consumes: approved verifier/canary receipts and candidate release.
- Produces: promotion/rollback receipt and one durable resume signal bound to application ID/thread ID.

- [ ] **Step 1: Write RED for promotion gates and exact-once resume**

```python
def test_promotion_requires_matching_case_verifier_canary_and_release_hashes(self): ...
def test_same_resume_signal_is_consumed_once(self): ...
def test_unknown_post_send_never_creates_resume_signal(self): ...
```

- [ ] **Step 2: Implement atomic promotion and rollback**

Reuse `release_activation.activate`; do not add a second symlink controller. Preserve
the previous release and atomically record the promotion receipt.

- [ ] **Step 3: Implement durable same-application signal**

Before Temporal migration, store and consume one Ledger/thread-bound resume signal.
Keep Workflow/Activity fields null. `L-49K0D2` later maps the same interface to a
Temporal signal.

- [ ] **Step 4: Verify, update SSOT, commit, and push**

Commit `feat(job-hunter): promote repairs and resume applications`.

### Task 6: Telegram repair receipt and installed harness E2E (`L-66F`)

**Files:**
- Create: `apps/job-search-loop/job_search_loop/repair_reporting.py`
- Create: `apps/job-search-loop/tests/test_repair_reporting.py`
- Create: `apps/job-search-loop/scripts/run-repair.sh`
- Create: `apps/job-search-loop/launchd/ai.anicca.job-search-repair.plist`
- Modify: `apps/job-search-loop/scripts/install-launchagents.sh`
- Modify: `docs/superpowers/plans/2026-08-02-job-hunter-local-completion.md`

**Interfaces:**
- Consumes: full repair/promotion/resume evidence chain.
- Produces: one deduplicated Telegram provider message ID and installed repair-lane receipt.

- [ ] **Step 1: Write RED for complete natural-language receipt and dedupe**

```python
def test_report_contains_fault_tests_releases_canary_resume_and_outcome(self): ...
def test_identical_repair_report_reuses_provider_message_id(self): ...
```

- [ ] **Step 2: Implement reporting and the dedicated launchd lane**

The lane monitors indexed failures, not a second application executor. It may create
and repair cases but has no live ATS/Gmail/Calendar authority.

- [ ] **Step 3: Run installed no-send self-healing E2E**

Inject the measured stale-ATS/page-not-found reproduction. Verify one case, one patch,
one verifier, one canary, one release decision, one same-application resume signal,
and one Telegram receipt. Replay the same failure and verify dedupe.

- [ ] **Step 4: Final verification and completion**

Run the complete suite, privacy scan, launchd health checks, release Guardian, Ledger
integrity, trace join, Telegram provider ID, and worktree cleanliness. Update all
L-66A–F receipts, commit `feat(job-hunter): run autonomous self-healing harness`, and push.
