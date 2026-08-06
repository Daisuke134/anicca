# Job Hunter handover

SSOT: `/Users/anicca/anicca-project/.worktrees/job-hunter-spec-20260805/docs/superpowers/plans/2026-08-02-job-hunter-local-completion.md`, section 12, especially `L-49K2C1` onward.

Repository state: `/Users/anicca/anicca-project/.worktrees/job-hunter-spec-20260805`, branch `docs/job-hunter-spec-20260805`, upstream `origin/docs/job-hunter-spec-20260805`. Implementation checkpoint `3e8a9a4e8` is pushed. Do not touch or switch the shared `/Users/anicca/anicca-project` worktree. Check the handover commit and dirty state before editing.

Current item: `L-49K2C1` is open. Checkpoint adds `job_search_loop/ashby_apply.py` plus focused tests and reconciles the atomic SSOT order. It provides inspect/fill, exact-question answer mapping, current `data-field-path` re-resolution, fill/select/check/upload, grounded receipts, and closes only its page.

Verified evidence: RED caught the missing module and Ashby's Yes/No-versus-internal-checkbox misclassification. Focused Ashby suites pass 23/23. Read-only inspection of OpenAI's live Ashby application extracted 12 fields; the current phone field UUID differs from run 57's stale UUID, Yes/No groups classify as select, and the standalone attestation classifies as check. No application was submitted by this development session.

Unfinished/blockers: the isolated real-control fill E2E was interrupted before producing a receipt, so `L-49K2C1` must not be marked done. The full suite runs 498 tests with 4 failures and 4 errors in old `run-daily.sh` assertions expecting the superseded Browser Worker/Terra-plan topology; determine whether to update those contracts under the relevant later item, without hiding them. The CLI is 244 LOC versus a 180-LOC soft target; simplify only if it preserves the verified boundary. Resident launchd `ai.anicca.job-search-daily` is not running (`runs=59`); CloakBrowser CDP is live on `127.0.0.1:9222`. There is still no new authoritative Ashby Submit receipt from this work.

External state: do not retry any ledger row already `submitted` or `submit_unknown`. Do not treat prior validation-page screenshots or generic historical submissions as a current Ashby success. User explicitly wants chat-only handover; no Gmail handover was sent.

First safe resume action: fetch and verify checkpoint/dirty/runtime; run the isolated local-DOM CloakBrowser E2E for all four actions without `browser.close()`, re-run the 23 focused tests, inspect the diff, then either record a complete C1 receipt or keep it open with the exact failure. Next is `L-49K2C2`, which must make the resident Terra call the CLI instead of writing Playwright.

The exact validated restart goal is stored beside this file as `2026-08-06_1953_job-hunter-resume.goal.txt`.
