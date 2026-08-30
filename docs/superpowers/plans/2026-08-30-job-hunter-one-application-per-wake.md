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

#### Task 1D: Include unfinished Ledger rows in the ranking pool — active

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/workday_search_loop.py`
- Modify focused checks in: `apps/job-search-loop/tests/test_workday_qualification.py`

Run `daily-20260830-085920` proves ranking input has zero Japan rows although the official snapshot has 44. Ledger has all 44 URLs: 25 are unfinished `materials_ready` rows with absent fit and no submit intent; 19 are rejected. `snapshot_candidates()` must include official rows when the matching Ledger application is `materials_ready` and its fit is absent or hold, while continuing to exclude rejected, qualified, attempted and submitted rows. Do not reopen rejected history in this atom.

#### Task 1E: Drain unfinished rows before ranking fresh rows — completed in PR #3178

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/workday_search_loop.py`
- Modify focused checks in: `apps/job-search-loop/tests/test_workday_qualification.py`

Run `daily-20260830-091914` ranks 188 unfinished official rows plus roughly 646 fresh rows, requiring four model calls and exhausting disk before first fit. When the current official snapshot contains any unfinished rankable Ledger rows, return only that unfinished pool from `snapshot_candidates()`; return fresh unseen rows only when the unfinished pool is empty. Preserve official snapshot validation and all rejected/attempted/submitted exclusions. This is deterministic durable-work ordering, not job-fit judgment.

Deployment state: main-derived sparse release `bd274627` is loaded explicitly by all five Job Hunting labels; the shared production current was restored for other loops. Mercor and Mercor-browser remain unloaded until Workday 10P3 completes. Red Hat is verified and persisted as source 33.

#### Task 1F: Mix fresh companies into the one-call backlog batch — active

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/workday_search_loop.py`
- Modify focused checks in: `apps/job-search-loop/tests/test_workday_qualification.py`

Red Hat official CXS adds 27 Japan-AI results, but unfinished-only batching would hide every fresh source until all 188 backlog rows drain. Build a maximum 400-row ranking batch: keep every unfinished official row first, then fill remaining slots with fresh rows after company interleaving. If unfinished rows already reach 400, rank them in the existing chunk contract; never discard unfinished work. This is context-capacity bookkeeping, not job-fit judgment.

#### Task 1G: Send the model's focused source query to Workday CXS — completed

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/workday_discovery.py`
- Modify focused checks in: `apps/job-search-loop/tests/test_workday_discovery.py`

Every validated source includes `search_text`, but `_fetch_jobs()` currently sends an empty Workday search. Use the exact source `search_text` in every paginated CXS request. Preserve payload validation, total consistency, pagination, URL identity and source-level fail-closed behavior. Verify Red Hat-style source requests carry `Tokyo Japan AI ...` rather than an empty query.

PR #3210 merges this repair. Release `f3921299` is loaded by all five Job Hunting owners. Production run `daily-20260830-105938` proves Red Hat and Guidewire now enter the official snapshot and that a rejected fit advances to the next candidate in the same wake. It does not prove an application: 15 fit decisions reject, one is interrupted during an intentional provider-conflict stop, and qualified/submitted/Gmail receipt remain zero.

#### Task 1H: Retrieve broad Japan-feasible work and guarantee one truthful stretch handoff — active

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/workday_source_discovery.py`
- Modify: `apps/job-search-loop/job_search_loop/workday_search_loop.py`
- Modify: `apps/job-search-loop/job_search_loop/workday_qualification.py`
- Modify: `apps/job-search-loop/job_search_loop/ledger.py`
- Modify focused checks: `apps/job-search-loop/tests/test_workday_qualification.py`

Use concise Workday-native source queries rather than long sentence-like keyword bundles that collapse a verified 27-result Japan-AI source into three unrelated senior results. Rank evidence-supported roles first, but do not treat missing preferred years, title seniority, or an imperfect stack match as an automatic veto. If a wake contains any posting that is legal to work from Japan, geographically feasible, truthful to apply to, and lacks an objective hard blocker, at least one best stretch candidate must become qualified and enter the existing browser queue. Hard blockers remain false attestation, impossible work authorization/location, an explicit credential the candidate does not hold, or compensation below the configured floor when the posting states it. Never fabricate experience. Verify with one natural existing-owner wake and the full screenshot + Gmail + Ledger + Telegram + replay-zero receipt chain.

PRs #3221/#3224/#3229/#3236 close query length, stretch fit, old-policy rejection reopening, invalid escalation metadata, queued-row latency and routine health Telegram spam. Kyndryl is now v3-qualified and the browser reaches its official URL. The active blocker is transport durability under host disk exhaustion: the next browser wait fails before any submit intent with SQLite disk I/O. Do not call its navigation screenshot an application. Resume the same row only with stable headroom and require both the Workday completion screenshot and Gmail employer receipt before marking this task completed.

**No-voluntary-skip v5 design:** Applying is free, so interview-likelihood pessimism is not an application veto. The source model searches for Japan-feasible early/mid-career individual-contributor work and avoids senior leadership scope. The ranking model places every adequate non-senior role before senior or foreign work. The fit model must qualify a Japan-feasible role when every form answer can be truthful and the candidate has adjacent grounded evidence for any core work; missing preferred years, exact stack, perfect title match or published compensation remains an honest gap, never a reject/hold reason. The user's title boundary is explicit: a posting titled Senior/Lead/Principal/Director/Head/VP/Chief or an equivalent unambiguous senior-level title is outside target even when adjacent IC responsibilities exist; continue same-wake. Ambiguous titles are judged from full responsibilities. Reject is otherwise reserved for an objective hard blocker. No deterministic title regex, keyword score or job-fit gate is permitted.

Policy changes from `interview-chance-v3` through the live-corrected `no-voluntary-skip-v5`. A no-intent decision under an older policy, including `qualified`, is reconsidered exactly once. `qualified_queue_ids` admits only the current policy so Kyndryl cannot bypass v5 merely because v4 qualified it. When the rolling deficit is positive, `search_until_qualified` targets exactly one new qualification per wake even when another qualified row is waiting for account email, CAPTCHA or other checkpoint recovery. Existing queue work remains first in browser order, but an external wait cannot stop discovery and admission of a new adequate row behind it. Twenty-four attempts remain the bounded same-wake search ceiling, but exhausting them without a qualified row is a failed wake and the durable cursor continues next wake; it is never reported as a successful skip-only pass.

**Focused verification:** one test proves an old-policy qualified no-intent row is reconsidered and can become rejected; one test proves only current-policy qualified rows enter the browser queue; existing zero-target and same-wake reject/hold/qualified continuation checks remain unchanged. Run only those focused tests plus `git diff --check`.

**New-company Workday tenant contract (part of Task 1H):** Account setup is inside the same autonomous loop. Workday identity is tenant-scoped, not company-name-scoped. For a new tenant, the runtime first creates and stores one private tenant credential, attempts visible Sign In once, follows visible Create Account only after exact account-not-found/wrong-credential evidence, fills the account/profile fields, and records `create_submitted`. If Workday requires activation or password recovery, the existing inbox owner consumes the authoritative tenant email once and the next daily wake resumes the same application ID. The daily owner then uploads the routed resume, fills every required and employer-specific field from grounded candidate facts, reaches Review, and invokes the one-shot Submit fence. A reused tenant signs in with the existing credential/session and skips account creation. Neither credential creation nor account creation counts as an application.

The current Kyndryl tenant is `credential_only`: the private tenant credential exists, but the candidate account has not yet been proved created. Its blank navigation screenshot, `materials_ready` state, and absent submit intent are not progress beyond queue handoff.

**Browser-owner readiness contract:** A loaded/running browser LaunchAgent is not yet
proof that CDP `:9222` accepts connections. The daily owner must boundedly poll the
existing CDP owner before writing `browser-owner.json` and starting the browser agent.
A first-probe `connection refused` is startup latency, not a row outcome and not a
reason to emit `transport_failed`, reject, skip, or consume the application. If the
bounded wait expires, the wake fails visibly with the row still `materials_ready`; it
never records exit 0 as an application. Production run `daily-20260830-180908`
qualified a new row but reproduced this race: its one `observe` failed before any
browser action because the evidence file had frozen the first refused connection.
The focused repair preserves immediate `probe_cdp()` for diagnostics and makes the
daily CLI wait up to 30 seconds at 0.5-second intervals for `ready`.

**Long-form continuation contract:** A model pass ending `in_progress` is not a
successful wake when both `submitted` and `submit_unknown` are empty. If every
runtime command completed successfully, the existing bounded orchestrator must
invoke one continuation from the durable row checkpoint in the same wake. It must
not retry after a real nonzero runtime command, a recorded submission, or an
uncertain submit effect. Production run `daily-20260830-181801` reached a new HPE
non-senior application, signed in, uploaded the resume, completed personal details,
education, and 37 sequential form actions, then returned `in_progress` on required
screening questions with no submit intent. That is resumable execution-budget
exhaustion, not a skip, rejection, provider blocker, or application receipt.

**Remaining execution order (fixed):**

1. Restore the removed stable Rust toolchain, then retain enough measured disk headroom for browser/SQLite evidence writes.
2. Reload the sole `ai.anicca.job-search-daily` owner, read back its main-derived release, `RunAtLoad`, and `StartInterval=1800`, and boundedly confirm CDP `:9222` is ready before the browser agent starts; do not create another executor.
3. Reconsider the existing Kyndryl application ID under v4 before any browser effect; because it is a Senior role, continue to the next adequate non-senior row unless the full posting proves otherwise.
4. Attempt tenant Sign In once. If the visible provider proves the account absent, complete Create Account with the stored tenant credential; never create a second account.
5. If activation/reset email is required, checkpoint the same row, let `job-search-inbox` consume the exact authoritative one-time email, then resume that same row on the next daily wake.
6. Fill and re-read the complete Workday application, including resume, profile, work history, source, employer questions, legal attestations and validation errors; continue until final Review.
7. Invoke the one-shot Submit fence once. After an ambiguous effect, reconcile first and never click Submit again.
8. Accept completion only when the post-submit Workday screenshot and authoritative Gmail employer receipt bind the same tenant, company, role, application ID and post-submit time; then require Ledger `submitted`, Telegram ACK and immediate replay duplicate 0.
9. Observe the next natural 30-minute wake select a different eligible application/company and repeat the tenant create-or-reuse path without human intervention.
10. Accumulate at least 48 distinct Gmail-confirmed applications in the rolling 24-hour window. Only then start Ashby, followed by Greenhouse, Lever and generic ATS in the existing fixed spec order; README loop/competitor documentation remains after live proof.

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
