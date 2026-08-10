# CFO-2a2b.4 — Real Local Capture E2E Plan

> **For Luna:** use Superpowers test-driven-development and verification-before-completion. Luna owns only the one
> E2E file below; Sol owns this plan, review, final verification, state, commit, and push.

**Status:** COMPLETE — implementation `7e79c33`; fresh Sol review: ship

**Goal:** Update the existing isolated E2E to prove the current local truth after 3b: both real usage ledgers are
published without mutation, while absent real attempt ledgers produce exact numeric zero counts plus
`capture_not_started`. This is not a claim that the active producers are cut over.

**Measured precondition:** the two real `agent-usage.jsonl` files exist as `0600`; both adjacent
`agent-usage-attempts.jsonl` files are absent. The currently active `/Users/anicca/profitable-claude` runner does not
contain the attempt-ledger implementation; the reviewed feature worktree does. Therefore active-producer cutover is
the next mandatory slice, CFO-2a2b.5.

**Ponytail full:** edit the existing E2E only. Reuse its real-ledger prefix snapshots, isolated temp root, real runner,
real chain reader, real local OTel sink, and fixed one-line result. Add no production code, package script, dependency,
fixture framework, provider call, database, service, scheduler, launchd edit, Telegram send, or cloud path.

**Soft target / hard gate:** exactly one existing file, target 18 gross added LOC, hard maximum 35:

- `apps/life-call/test/cfo-local-agent-usage-real-e2e.js`

## Exact current-state contract

The isolated root copies only the two real usage-ledger snapshots. It does not invent attempt rows. The exact immutable
receipt has exactly `status`, `collected_at`, `sources`, `capture_counts`, and `coverage_exceptions`. `collected_at` is
the fixed `2026-08-11T01:02:03.000Z`; `sources` is the existing two exact `published` receipts in fixed
Life-Manager/Anicca order, with each real snapshot's record ID, byte offset, event count, mapping ID, and empty source
exceptions. The remaining exact values are:

```json
{
  "status":"partial",
  "capture_counts":{
    "status":"partial",
    "source_count":2,
    "reconciled_source_count":2,
    "attempted_rows":0,
    "success_rows":0,
    "failed_rows":0,
    "missing_completion_rows":0,
    "unmatched_completion_rows":0,
    "duplicate_attempt_rows":0,
    "conflicting_attempt_rows":0,
    "ambiguous_completion_rows":0,
    "coverage_exceptions":["capture_not_started"]
  },
  "coverage_exceptions":["capture_not_started"]
}
```

- Both source-publication receipts remain `published`; this proves historical usage ingestion, not attempt coverage.
- Require `success + failed + missing === attempted` and recursively frozen `capture_counts`.
- The single span has exact `status_code=2` and `error.type=collection_partial`. Its attributes are deep-equal to the
  exact 30-key object: five collection base attributes; collection exception array; five capture metadata attributes
  (`status`, `source_count`, `reconciled_source_count`, `coverage_exception_count`, `coverage_exceptions`); all eight
  numeric zero capture-count attributes; ten existing source-publication attributes; and `error.type`.
- The span and stdout remain content-free: no token values, prompt, response, path, provider/model, credential, owner,
  or raw error.
- Before and after the run, require both real usage ledgers to remain regular `0600` files and both adjacent real
  attempt ledgers to remain absent. Re-read each usage ledger's starting byte prefix and require its hash unchanged;
  a valid concurrent suffix append is allowed, but prefix rewrite, truncation, removal, or chmod is not.
- Success stdout is exactly one line:
  `cfo-local-agent-usage-real-e2e: PASS sources=2 discovered=<n> accepted=<n> missing=<n> coverage_exceptions=<n> spans=1 capture_status=partial attempted=0 success=0 failed=0 missing_completion=0`.
  Failure stdout remains exactly `cfo-local-agent-usage-real-e2e: FAIL`. Counts are observed current-state values,
  never a readiness claim.

## TDD / verify order

1. In `apps/life-call`, run `npm ci`, then RED with
   `node test/cfo-local-agent-usage-real-e2e.js`; observe fixed `FAIL` from the old four-key/complete expectation.
2. GREEN: change only the exact receipt/span/PASS assertions above. Do not weaken the real-ledger, permissions,
   append-only-prefix, privacy, one-span, cleanup, or no-console checks.
3. In `/Users/anicca/profitable-claude/.worktrees/cfo-agent-usage-capture`, run the producer boundary twice:
   - `python3 -m unittest discover -s skills/gig-work/tests -p test_agent_runner.py -k test_attempt_row_is_visible_before_launch_and_completion_reuses_id`
   - `python3 -m unittest discover -s skills/gig-work/tests -p test_agent_runner.py -k test_usage_completion_failure_leaves_durable_unmatched_attempt`
   They use the existing isolated fake executable, exercise the real runner implementation without a paid provider,
   and their rows never enter the CFO real-state receipt.
4. In `apps/life-call`, run GREEN twice with `node test/cfo-local-agent-usage-real-e2e.js`, then
   `node --test lib/cfo-local-agent-usage-runner.test.js lib/cfo-local-agent-capture-reconciliation.test.js lib/cfo-local-agent-usage-chain.test.js`,
   `npm run test:cfo`, `npm test`, and `node --check test/cfo-local-agent-usage-real-e2e.js`.
5. From the Life Manager worktree root, run `git diff --check`; require
   `git diff --name-only -- apps/life-call` to equal only
   `apps/life-call/test/cfo-local-agent-usage-real-e2e.js`; sum that path's added column from `git diff --numstat` and
   require at most 35.
6. Fresh Sol verifies current truth, no fake readiness, real-prefix immutability, content privacy, and Ponytail scope.
   Luna fixes only required issues in the same file.
7. Sol updates state, commits/pushes, sends one real Telegram milestone, and advances to CFO-2a2b.5 local producer
   cutover. This slice does not trigger or repoint any live loop.

## Completion evidence

- Real E2E passed twice with `discovered=5104`, `accepted=5104`, historical missing usage `351`, six historical
  coverage exceptions, one span, and exact pre-cutover capture counts `attempted=0/success=0/failed=0/missing=0`.
- Both isolated producer boundary tests passed; no paid provider or real ledger was used by those tests.
- Related 20/20, CFO 302/302, full `npm test`, syntax, diff, and one-file `+7/-6` scope gates passed.
- Both real usage ledgers remained regular `0600` files with unchanged starting prefixes; both real attempt ledgers
  remained absent. Telegram milestone was delivered by the real Life Manager bot as message `603`. Active producer
  cutover is still required and is CFO-2a2b.5.
