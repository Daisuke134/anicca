# O2-05A1 report — RED

## Scope

The focused regression in `apps/job-search-loop/tests/test_route_executor.py`
now seeds two distinct, non-hard-coded legacy outreach applications. Each has
the full `discovered -> qualified -> materials_ready -> submit_claimed ->
submitted -> email_sent` chain, an immutable delivered `recruiting_outreach`
route with `outreach_only` acceptance, and a `confirmed_application` outcome
created through the old application-accepting projection. The test was run
before the O2-05A1 production correction; pre-existing O2-05A outreach edits
were preserved.

## RED evidence

Command:

```text
cd apps/job-search-loop
python3 -m unittest tests.test_route_executor.RouteExecutorTests.test_reconciliation_repairs_every_legacy_outreach_chain_append_only
```

Observed result: `Ran 1 test`, `FAILED`.

- Reconciliation did find both rows and returned `outreach_correction_count=2`;
  the false outcomes and route receipts remained present.
- The test failed at the Guardian assertion because `ledger_health()` returned
  `status=unhealthy` with `reasons=['event_projection_mismatch']` for the two
  generalized application IDs. The remaining hard-coded run-74 Guardian
  predicate rejects the otherwise evidence-bound corrections.

This is the expected feature-missing RED for O2-05A1. Production correction may
now begin. Company pause, real ledger/profile, launchd, browser, and Telegram
state remain out of scope.

## RED — strict preceding-event binding

The focused boundary regression also ran before its production correction:

```text
cd apps/job-search-loop
python3 -m unittest tests.test_route_executor.RouteExecutorTests.test_reconciliation_rejects_unbound_legacy_email_sent_event
```

Observed result: `Ran 1 test`, `FAILED`; reconciliation incorrectly returned
`outreach_correction_count=1` for an `email_sent` event with no route/provider
binding. This proves the optional preceding-event check was too permissive.

## Scope correction

The initial shared worktree contained an O2-05A company-pause implementation and
test. Per the O2-05A1 brief, that work is excluded from this slice and was removed
from the owned production/test/spec changes. Company pause remains a later task.
Only application-agnostic outreach correction and its focused evidence remain.

## GREEN evidence

Production changes were limited to the owned ledger/Guardian path. The correction
predicate is now application-agnostic and requires the immediately preceding
legacy event to bind the exact route, provider, outreach channel, and delivery
hash where present, plus an immutable delivered route event/provider/evidence
match. The reconciler appends only `email_sent -> submit_unknown`, updates mutable
state/slot/projection data, and leaves immutable events and route receipts alone.
Guardian uses the same predicate and accepts the older
`submit_unknown -> submitted -> submit_unknown` correction shape.

Focused commands and observed results:

```text
cd apps/job-search-loop
python3 -m unittest tests.test_route_executor
Ran 13 tests ... OK

python3 -m unittest \
  tests.test_route_executor.RouteExecutorTests.test_reconciliation_repairs_every_legacy_outreach_chain_append_only \
  tests.test_route_executor.RouteExecutorTests.test_reconciliation_rejects_unbound_legacy_email_sent_event
Ran 2 tests ... OK
```

The focused suite proves two non-hard-coded application IDs, false
`confirmed_application` projection exclusion, `submit_unknown` current state and
daily slot, append-only route/event counts, idempotent replay, and fail-closed
unbound evidence. The full Job Hunter suite passed `566/566`; the full
`runtime/agent-runner` suite passed `18/18`; `git diff --check` passed. The
production diff is 73 net lines across ledger and Guardian.

O2-05 remains unchecked. Real-ledger repair, Gmail audit, release activation,
LaunchAgent loading, Guardian runtime gates, and a real canonical cycle remain
pending. No real ledger/profile/current/launchd/browser/Telegram state was touched.
