# Job Hunting 48-per-Rolling-Day Implementation Plan

**Goal:** Keep the existing 30-minute Job Hunting owner continuously filling a rolling minimum of 48 authoritative applications while selecting Japan-feasible, current-scope work and keeping rejected candidates private.

**Architecture:** Reuse the existing Workday discovery, model qualification, browser row queue, Ledger, Gmail reconciliation and Telegram outbox. The search loop computes the rolling deficit from `submission_confirmations.received_at`, qualifies multiple rows when behind, and passes all qualified rows to the existing sequential browser queue. No second scheduler, browser owner, dependency, provider-specific fast path, or deterministic job-fit classifier is added.

**Tech Stack:** Python 3.14, SQLite, existing Workday model lane, browser-agent queue, launchd `StartInterval=1800`.

## Global Constraints

- Count only distinct authoritative Gmail-confirmed `submitted` applications received inside the preceding rolling 24 hours.
- Target at least 48; a deficit remains visible and carries into the next wake.
- Preserve truthful qualification, one-shot submit fences, `submit_unknown` reconciliation and replay zero.
- Prioritize Japan employment feasibility, demonstrated current career scope, then compensation ambition.
- Reject/hold decisions remain private evidence and send no Telegram message.
- Visible messages use `[Job Hunting]`; no harness prefix or `:::` is allowed.
- Existing five LaunchAgents remain the only owners; daily cadence stays 1,800 seconds.

---

### Task 1: Rank feasible roles before senior foreign roles — completed in PR #3132

**Files:**
- `apps/job-search-loop/job_search_loop/workday_search_loop.py`
- `apps/job-search-loop/tests/test_workday_qualification.py`

The merged shortlist prompt orders Japan employment feasibility, demonstrated current scope and compensation ambition. Qualification and every effect fence remain unchanged.

#### Task 1B: Carry model shortlist order into qualification — active production repair

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/workday_qualification.py`
- Modify: `apps/job-search-loop/job_search_loop/workday_search_loop.py`
- Modify focused checks in: `apps/job-search-loop/tests/test_workday_qualification.py`

`qualify_one()` accepts the ordered model-selected canonical URLs and orders pending eligible Workday rows by that list before choosing one. Rows absent from the current shortlist remain behind every preferred row; failed preferred IDs still use the existing wake-local skip cursor. This is deterministic ordering of model output, not a title/location/skill classifier. Run `daily-20260830-082055` is the failing production example: the shortlist exists, but six initial qualification calls consume old Principal/Director/foreign backlog because current `qualify_one()` uses Ledger insertion order.

#### Task 1C: Make Japan employment feasibility an actual ranking gate — active

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/workday_search_loop.py`
- Modify focused expectation in: `apps/job-search-loop/tests/test_workday_qualification.py`

Run `daily-20260830-083836` has 44 Tokyo/Japan jobs in an 874-job snapshot but ranks Omnissa Korea first. Strengthen the model instruction, not deterministic code: when any posting supports employment in Japan, all such rows precede roles tied to another country; `remote` or an EOR for another country does not establish employment from Japan. Include two canonical examples showing Japan imperfect fit before foreign strong fit and Korea-remote/EOR as non-Japan. Compensation remains third after location feasibility and demonstrated scope.

---

### Task 2: Make Job Hunting notifications quiet and product-owned

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/application_reporting.py`
- Modify: `apps/job-search-loop/job_search_loop/browser_agent/outcome_reporting.py`
- Modify focused expectations in: `apps/job-search-loop/tests/test_application_reporting.py`

**Required behavior:**

1. `deliver_fit_decision()` returns a durable suppressed result for `rejected`, `hold`, and pre-submit `qualified` decisions without calling Telegram.
2. Authoritative submitted outcomes begin `[Job Hunting] 応募完了` and include company, role and evidence class.
3. The daily outbox message begins `[Job Hunting] 24時間レポート` and reports authoritative rolling submissions, distinct companies, interviews, human-only blockers and duplicate effects without model/provider/harness labels.
4. Existing event keys and send uncertainty fencing remain unchanged.
5. Run only the focused application-reporting module and `git diff --check`; commit and push.

---

### Task 3: Fill the rolling 48-application deficit

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/workday_search_loop.py`
- Modify: `apps/job-search-loop/job_search_loop/browser_agent/queue.py`
- Modify focused checks in: `apps/job-search-loop/tests/test_workday_qualification.py`
- Modify focused checks in: `apps/job-search-loop/tests/test_browser_agent_queue.py`

**Required behavior:**

1. Query distinct `submission_confirmations.intent_id` joined to `submit_intents` where `received_at` is within `now - 24 hours`; compute `deficit = max(0, 48 - confirmed_count)`.
2. `search_until_qualified()` continues until it has qualified `min(deficit, max_candidates)` distinct rows or exhausts the bounded candidate budget. It returns every newly qualified application ID in stable order.
3. `queued_application_ids` contains all newly qualified IDs followed by previously qualified queued IDs, deduplicated in stable order.
4. `RowQueueSupervisor.collect()` may sort the preferred ID first but never truncates the remaining qualified Workday rows.
5. A zero deficit performs no new application effect; an unfinished deficit is persisted in the run receipt and retried by the next existing wake.
6. Run the two focused modules and `git diff --check`; commit and push.

---

### Task 4: Merge, release and verify production

1. Fetch, rebase, push, create/update the focused PR and run `gh pr merge --admin`; if the server rejects it, record the exact required check and retry only after it passes.
2. Build an immutable release from merged `origin/main`; never release from the worktree branch.
3. Require `launchctl-safe preflight` status `pass` and `mutation_allowed=true`, then apply the release to the existing browser, daily, inbox, learning and health labels.
4. Read back exact `ProgramArguments`, release SHA and daily `StartInterval=1800` for all owners.
5. Kickstart only `ai.anicca.job-search-daily` and watch the real launchd-owned run.
6. Verify shortlist ordering, multiple queued rows when deficit is greater than one, no per-reject Telegram sends, approved `[Job Hunting]` messages, row-local failure continuation and replay zero.
7. Keep 10P3 open until a rolling 24-hour window contains at least 48 distinct Gmail-confirmed applications with matching completion evidence, Ledger `submitted`, Telegram ACK and duplicate effects zero.

---

### Task 5: Publish the proven Job Hunting experience

Start only after Task 4 is live-proven. Update the public README with the resident-loop list, Job Hunting lifecycle from resume onboarding through confirmed start, and a source-cited comparison against relevant open-source job-search repositories. Claims must match current production evidence; incomplete ATS lanes remain visibly incomplete.
