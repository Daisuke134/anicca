# Job Hunter Stale Workday Cursor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent one stale or transiently failing Workday row from consuming a wake, preserve row-scoped failure evidence, and continue to the next live job in the same wake.

**Architecture:** The current official snapshot is authoritative only for sources fetched successfully in the wake. Deterministic bookkeeping rejects pre-submit rows absent from those successful source snapshots. Qualification returns structured row-scoped fetch failures and keeps a wake-local skip set, while the model retains all fit judgment.

**Tech Stack:** Python standard library, SQLite Ledger, `unittest`, Workday CXS JSON.

## Global Constraints

- Workday remains the only active application provider; Ashby stays parked.
- `submit_unknown` is never retried or clicked again.
- A listing, Telegram message, screenshot, or Ledger row is not an application receipt.
- Deterministic code owns listing identity, failure evidence, wake-local cursor, and dedupe; the model owns fit judgment.
- Production changes stay within two files and 100 production LOC where possible; no new dependency or service.

---

### Task 1: Advance qualification after a stale or failed row

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/workday_search_loop.py`
- Modify: `apps/job-search-loop/job_search_loop/workday_qualification.py`
- Test: `apps/job-search-loop/tests/test_workday_qualification.py`

**Interfaces:**
- Consumes: successful per-source job snapshots already stored in `jobs_by_source`, `Ledger.pending_materials_ready_applications()`, and the existing `fetch_official_description()` callable.
- Produces: `reject_stale_workday_rows(ledger_path, jobs_by_source) -> tuple[dict[str, str], ...]`; `qualify_one(..., excluded_application_ids: frozenset[str] = frozenset()) -> dict[str, Any]`; structured `qualification_retryable_failure` rows with `application_id`, `company`, `title`, `canonical_url`, `error`, `http_status`, `provider_error_code`, and `provider_message`.

- [ ] **Step 1: Write the stale-row and same-wake-advance regressions**

```python
def test_fresh_snapshot_rejects_only_absent_pre_submit_workday_row():
    with tempfile.TemporaryDirectory() as directory:
        ledger_path = Path(directory) / "ledger.sqlite3"
        ledger = Ledger(ledger_path)
        stale = ledger.add_application(
            "Example", "Expired", "https://example.wd1.myworkdayjobs.com/Careers/job/Japan/Expired_R1"
        )
        current = ledger.add_application(
            "Example", "Current", "https://example.wd1.myworkdayjobs.com/Careers/job/Japan/Current_R2"
        )
        for application_id in (stale, current):
            ledger.transition(application_id, "qualified")
            ledger.transition(application_id, "materials_ready")
        ledger.close()
        source = {
            "company": "Example", "host": "example.wd1.myworkdayjobs.com",
            "tenant": "example", "site": "Careers",
        }
        jobs = {
            json.dumps(source, sort_keys=True): [
                {"title": "Current", "externalPath": "/job/Japan/Current_R2"}
            ]
        }
        receipt = reject_stale_workday_rows(ledger_path, jobs)
        ledger = Ledger(ledger_path)
        self.assertEqual(receipt[0]["application_id"], stale)
        self.assertEqual(receipt[0]["reason"], "official_listing_absent")
        self.assertEqual(ledger.current_state(stale), "rejected")
        self.assertEqual(ledger.current_state(current), "materials_ready")
        ledger.close()

def test_http_failure_receipt_skips_row_and_next_live_row_qualifies_same_wake():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        ledger_path, first, memory = self._row(root)
        ledger = Ledger(ledger_path)
        second = ledger.add_application(
            "Second", "Live", "https://second.wd1.myworkdayjobs.com/Careers/job/Japan/Live_R2"
        )
        ledger.transition(second, "qualified")
        ledger.transition(second, "materials_ready")
        ledger.close()
        error = HTTPError(
            "https://example.invalid", 403, "Forbidden", {},
            io.BytesIO(b'{"errorCode":"S22","message":"permission denied"}'),
        )
        failure = qualify_one(
            ledger_path=ledger_path,
            candidate_memory_path=memory,
            fetch_description=lambda _url: (_ for _ in ()).throw(error),
            run_model=lambda _prompt: self.fail("model must not run for failed fetch"),
        )
        self.assertEqual(failure["application_id"], first)
        self.assertEqual(failure["http_status"], 403)
        self.assertEqual(failure["provider_error_code"], "S22")
        success = qualify_one(
            ledger_path=ledger_path,
            candidate_memory_path=memory,
            excluded_application_ids=frozenset({first}),
            fetch_description=lambda _url: "Applied AI customer role in Tokyo",
            run_model=lambda _prompt: {
                "decision": "qualified",
                "mandatory_evidence": ["Grounded experience matches"],
                "unsupported_gaps": [],
                "interview_thesis": "Credible applied AI interview case",
                "location_feasibility": "Tokyo onsite is feasible",
                "compensation_thesis": "Unpublished and uncertain",
                "compensation_uncertain": True,
                "resume_variant": "business",
            },
        )
        self.assertEqual(success["application_id"], second)
        self.assertEqual(success["decision"], "qualified")
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd apps/job-search-loop
python3 -m unittest \
  tests.test_workday_qualification.WorkdayQualificationTests.test_fresh_snapshot_rejects_only_absent_pre_submit_workday_row \
  tests.test_workday_qualification.WorkdayQualificationTests.test_http_failure_receipt_skips_row_and_next_live_row_qualifies_same_wake -v
```

Expected: FAIL because stale snapshot reconciliation, excluded application IDs, and structured HTTP failure receipts do not exist.

- [ ] **Step 3: Implement the minimum bookkeeping boundary**

```python
# workday_search_loop.py
stale_rows = reject_stale_workday_rows(args.ledger, jobs_by_source)
wake_failed_ids: set[str] = set()

# workday_qualification.py
# Exclude wake_failed_ids during deterministic queue selection. Catch HTTPError
# around description fetch, parse only fixed Workday JSON fields, and return a
# structured failure receipt. Do not call the model and do not create Submit intent.
```

- [ ] **Step 4: Run GREEN and the focused package tests**

Run:

```bash
cd apps/job-search-loop
python3 -m unittest tests.test_workday_qualification tests.test_workday_discovery tests.test_model_browser_loop -v
git diff --check
```

Expected: all tests PASS; stale rows are terminal pre-submit, transient failures are skipped only for the wake, and the next live row is evaluated.

- [ ] **Step 5: Verify production evidence**

```text
merge pushed main -> immutable release -> apply Job Hunter labels only -> natural wake
```

Require: installed SHA readback; stale Visa attempted at most once or reconciled before fetch; failure receipt contains row and HTTP evidence; a later HTTP-200 row reaches model fit; one qualified new-company row reaches browser; any Submit is accepted only with completion UI, exact Gmail receipt, Ledger `submitted`, Telegram ACK, and next-wake duplicate zero.
