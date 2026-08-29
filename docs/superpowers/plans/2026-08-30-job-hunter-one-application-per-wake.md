# Job Hunter One Application Per Wake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make each 30-minute Workday wake pursue one truthful, legally feasible application instead of accepting an all-rejected shortlist.

**Architecture:** Keep the existing model-owned fit decision, browser owner, effect fence, Ledger, receipts, and replay protection. Change only the shortlist ranking instruction: Japan employment feasibility first, demonstrated current scope second, compensation ambition third. Deterministic code continues to validate schemas, state, and duplicate effects without judging job fit.

**Tech Stack:** Python 3.14, `unittest`, existing Job Hunter agent runner and launchd control plane.

## Global Constraints

- One real submitted application is the acquisition target for every `StartInterval=1800` wake.
- Preserve truthful qualification. Do not force an application when the official description is unsupported.
- Do not spend the 24-row wake budget on Principal/Lead/Senior or foreign-location roles while the same snapshot contains Japan-feasible roles closer to demonstrated current scope.
- Never weaken submit fences, authoritative receipt truth, Telegram ACK, or replay-zero.
- Do not add regex, keyword judgment, a second scheduler, provider-specific fallback, dependency, or schema.

---

### Task 1: Align Workday shortlist with the acquisition objective

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/workday_search_loop.py`
- Test: `apps/job-search-loop/tests/test_workday_qualification.py`

**Interfaces:**
- Consumes: `qualify_one(..., run_model: Callable[[str], dict])` and `rank_candidates(..., rank_chunk)`.
- Produces: unchanged fit-decision and shortlist schemas; only their natural-language objective changes.

- [ ] **Step 1: Write the failing prompt-contract test**

Assert that the shortlist prompt orders Japan employment feasibility before demonstrated current scope and compensation ambition, and explicitly avoids consuming the bounded shortlist with senior foreign roles when closer Japan-feasible work exists. Do not change the qualification prompt.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd apps/job-search-loop
python3 -m unittest tests.test_workday_qualification.WorkdayQualificationTests.test_fit_and_shortlist_prompts_require_one_feasible_application_per_wake -v
```

Expected: `FAIL` because the current shortlist leads with interview chance plus salary ambition but does not state the required feasibility/scope ordering.

- [ ] **Step 3: Apply the minimum prompt change**

In `workday_search_loop.py`, rank Japan-feasible roles first, demonstrated current scope second, and compensation ambition third, while retaining fewer prior submit attempts and company diversity. Preserve evidence grounding and prohibit invented candidate facts. Leave `workday_qualification.py` unchanged.

- [ ] **Step 4: Verify GREEN and the existing row-safety regression**

Run:

```bash
cd apps/job-search-loop
python3 -m unittest \
  tests.test_workday_qualification.WorkdayQualificationTests.test_fit_and_shortlist_prompts_require_one_feasible_application_per_wake \
  tests.test_workday_qualification.WorkdayQualificationTests.test_http_failure_receipt_skips_row_and_next_live_row_qualifies_same_wake \
  tests.test_workday_qualification.WorkdayQualificationTests.test_rejected_model_decision_never_enters_browser_queue -v
git diff --check
```

Expected: three tests pass and `git diff --check` is clean.

- [ ] **Step 5: Merge, release, and prove the production outcome**

Commit and push the branch, open and admin-merge the PR, cut an immutable release from merged `origin/main`, then targeted-apply it to the five Job Hunter owners after `launchctl-safe preflight` returns `status=pass` and `mutation_allowed=true`. Read back exact argv and daily `StartInterval=1800`; kickstart only `ai.anicca.job-search-daily`. Completion requires a different-company Workday completion screenshot, Gmail receipt, Ledger `submitted`, company/role Telegram ACK, and immediate replay with zero duplicate external effect.
