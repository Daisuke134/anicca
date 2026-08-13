# O2-05A1 report — GREEN

## Scope

The focused regression in `apps/job-search-loop/tests/test_route_executor.py`
now seeds two distinct, non-hard-coded legacy outreach applications. Each has
the full `discovered -> qualified -> materials_ready -> submit_claimed ->
submitted -> email_sent` chain, an immutable delivered `recruiting_outreach`
route with `outreach_only` acceptance, and a `confirmed_application` outcome
created through the old application-accepting projection. The test was run
before the O2-05A1 production correction; pre-existing O2-05A outreach edits
were preserved.

## Initial RED characterization (partial implementation)

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

This was not a strict pre-code RED: the shared worktree already contained the
O2-05A outreach reconciler before this test was recorded. It is retained as a
partial-implementation characterization showing the generalized reconciler had
not yet been paired with a generalized Guardian predicate. Company pause, real
ledger/profile, launchd, browser, and Telegram state remain out of scope.

## Earlier boundary characterization

The focused boundary regression also ran before its production correction:

```text
cd apps/job-search-loop
python3 -m unittest tests.test_route_executor.RouteExecutorTests.test_reconciliation_rejects_unbound_legacy_email_sent_event
```

Observed result: `Ran 1 test`, `FAILED`; reconciliation incorrectly returned
`outreach_correction_count=1` for an `email_sent` event with no route/provider
binding. This characterized the optional preceding-event check before it was
made strict.

## Review-driven RED — isolated authoritative histories

At HEAD `5907588fb`, the two isolated authoritative-history regressions were
added and run before production changes:

```text
cd apps/job-search-loop
python3 -m unittest \
  tests.test_route_executor.RouteExecutorTests.test_reconciliation_preserves_authoritative_submission_before_outreach \
  tests.test_route_executor.RouteExecutorTests.test_reconciliation_preserves_authoritative_submission_after_outreach_correction
```

Observed result: `Ran 2 tests`, `FAILED (failures=2)`.

- `test_reconciliation_preserves_authoritative_submission_before_outreach`
  observed `outreach_correction_count=1` instead of `0`; a Gmail-confirmed
  `submit_unknown -> submitted` event immediately before a separately delivered
  outreach route was demoted to `submit_unknown`.
- `test_reconciliation_preserves_authoritative_submission_after_outreach_correction`
  observed `ever_submitted=False` after a later Gmail-confirmed
  `submit_unknown -> submitted` event; the application-global correction flag
  suppressed the real submission.

These are the review-driven RED tests for the two authoritative-history
boundaries. Production correction begins only after this RED was observed.

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
match. Before an `email_sent` correction, an authoritative Gmail/Ashby
`submitted` event immediately before the outreach event blocks correction and
preserves the real submission. `ever_submitted` is paired per exact submitted
event/correction, so a genuine submission before or after an unrelated correction
remains true. The reconciler appends only `email_sent -> submit_unknown`, updates
mutable state/slot/projection data, and leaves immutable events and route receipts
alone. Guardian uses the same predicate and accepts the older
`submit_unknown -> submitted -> submit_unknown` correction shape.

Focused commands and observed results:

```text
cd apps/job-search-loop
python3 -m unittest tests.test_route_executor
Ran 15 tests ... OK

python3 -m unittest \
  tests.test_route_executor.RouteExecutorTests.test_reconciliation_repairs_every_legacy_outreach_chain_append_only \
  tests.test_route_executor.RouteExecutorTests.test_reconciliation_rejects_unbound_legacy_email_sent_event
Ran 2 tests ... OK
```

The focused suite proves two non-hard-coded application IDs, false
`confirmed_application` projection exclusion, `submit_unknown` current state and
daily slot, append-only route/event counts, idempotent replay, and fail-closed
unbound evidence. The authoritative-history regressions prove zero correction and
fail-closed health for a real submission before outreach, plus `ever_submitted=true`
for a real submission after an earlier correction. The focused route suite passed
`15/15`; the complete Job Hunter suite passed `568/568`; the complete
`runtime/agent-runner` suite passed `18/18`; and `git diff --check` passed. The
production diff is 88 net lines across ledger and Guardian.

O2-05 remains unchecked. Real-ledger repair, Gmail audit, release activation,
LaunchAgent loading, Guardian runtime gates, and a real canonical cycle remain
pending. No real ledger/profile/current/launchd/browser/Telegram state was touched.
