# Job Hunter One Application Per Wake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make each 30-minute Workday wake pursue one truthful, legally feasible application instead of accepting an all-rejected shortlist.

**Architecture:** Keep the existing model-owned fit decision, browser owner, effect fence, Ledger, receipts, and replay protection. Change only the right-altitude qualification and ranking instructions; deterministic code continues to validate schemas, state, and duplicate effects without judging job fit.

**Tech Stack:** Python 3.14, `unittest`, existing Job Hunter agent runner and launchd control plane.

## Global Constraints

- One real submitted application is the acquisition target for every `StartInterval=1800` wake.
- Reject only a missing role, unsupported legal work path, impossible mandatory physical presence, or a materially false required answer.
- Experience gaps, seniority, competition, and imperfect fit guide positioning but cannot justify an all-rejected wake.
- Never weaken submit fences, authoritative receipt truth, Telegram ACK, or replay-zero.
- Do not add regex, keyword judgment, a second scheduler, provider-specific fallback, dependency, or schema.

---

### Task 1: Align Workday model judgment with the acquisition objective

**Files:**
- Modify: `apps/job-search-loop/job_search_loop/workday_qualification.py`
- Modify: `apps/job-search-loop/job_search_loop/workday_search_loop.py`
- Test: `apps/job-search-loop/tests/test_workday_qualification.py`

**Interfaces:**
- Consumes: `qualify_one(..., run_model: Callable[[str], dict])` and `rank_candidates(..., rank_chunk)`.
- Produces: unchanged fit-decision and shortlist schemas; only their natural-language objective changes.

- [ ] **Step 1: Write the failing prompt-contract test**

Capture the prompt passed by `qualify_one` and assert it says the wake must select the best truthfully and legally feasible application, names the four hard blockers, and says experience gaps or imperfect fit are positioning inputs rather than blanket rejection reasons. Read `workday_search_loop.py` and assert the shortlist prompt prioritizes an actionable candidate for this wake.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd apps/job-search-loop
python3 -m unittest tests.test_workday_qualification.WorkdayQualificationTests.test_fit_and_shortlist_prompts_require_one_feasible_application_per_wake -v
```

Expected: `FAIL` because the current prompts optimize realistic interview fit and allow the whole shortlist to be rejected.

- [ ] **Step 3: Apply the minimum prompt change**

In `workday_qualification.py`, instruct the model to qualify the best available role unless one of the four hard blockers is evidenced. In `workday_search_loop.py`, rank candidates by actionability for the current wake while preferring fewer prior submit attempts and diverse companies. Preserve evidence grounding and prohibit invented candidate facts.

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
