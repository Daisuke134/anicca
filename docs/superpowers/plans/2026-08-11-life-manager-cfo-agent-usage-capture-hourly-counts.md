# CFO-2a2b.3b — Exact Hourly Capture Counts Plan

> **For Luna:** use Superpowers test-driven-development and verification-before-completion. Luna owns only the three
> implementation files below; Sol owns this plan, review, final verification, state, commit, and push.

**Status:** COMPLETE — implementation `1370b19`; fresh Sol review: ship

**Goal:** Add one truthful capture-count envelope to the existing hourly local usage receipt and its existing local
OTel span. Exact attempt/success/failure/missing counts are visible; an unreadable source makes every aggregate count
`null`, never a partial subtotal or zero.

**Ponytail full:** reuse `reconcileLocalAgentCapture`, the 3a post-write reads, the current immutable runner receipt,
the current span sink, and native safe-integer addition. Add no per-source public envelope, helper module, dependency,
file, DB, price, token/cost field, retry, scheduler, launchd change, Telegram copy, or cloud path.

**Soft target / hard gate:** exactly three existing files, target 65 gross added LOC, hard maximum 100:

- `apps/life-call/lib/cfo-local-agent-usage-runner.js` — retain pure receipts internally and build one aggregate
- `apps/life-call/lib/cfo-local-agent-usage-runner.test.js` — exact numeric/null/algebra/span regressions
- `apps/life-call/lib/cfo-local-agent-usage-span.js` — validate the envelope and emit existing local span attributes

The unregistered real-E2E script still asserts the four-key 3a receipt; updating and running it is explicitly
CFO-2a2b.4, not hidden inside this slice.

## Exact receipt contract

The runner changes from four to exactly five enumerable keys by adding `capture_counts`:

```json
{
  "status":"partial",
  "collected_at":"2026-08-11T01:02:03.000Z",
  "sources":[
    {"source_id":"life_manager_agent_usage","status":"published","record_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","byte_offset":5,"event_count":1,"mapping_id":"local_agent_usage_v1","coverage_exceptions":[]},
    {"source_id":"anicca_agent_usage","status":"published","record_id":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","byte_offset":5,"event_count":1,"mapping_id":"local_agent_usage_v1","coverage_exceptions":[]}
  ],
  "capture_counts":{
    "status":"partial",
    "source_count":2,
    "reconciled_source_count":2,
    "attempted_rows":2,
    "success_rows":1,
    "failed_rows":0,
    "missing_completion_rows":1,
    "unmatched_completion_rows":0,
    "duplicate_attempt_rows":0,
    "conflicting_attempt_rows":0,
    "ambiguous_completion_rows":0,
    "coverage_exceptions":["missing_completion"]
  },
  "coverage_exceptions":["missing_completion"]
}
```

- The nested object has exactly the twelve keys shown, is recursively frozen, and contains no event, ID, path,
  prompt, output, provider, model, token, cost, credential, owner, or raw error.
- `source_count` is always 2. `reconciled_source_count` is a safe integer from 0 through 2.
- If both sources return valid pure reconciliation receipts, sum each of the eight existing safe-integer counts with
  checked addition. Status is `complete` only when both pure receipts are complete and capture exceptions are empty;
  otherwise it is `partial`. All eight totals remain numeric, including honest zero. Require
  `success_rows + failed_rows + missing_completion_rows === attempted_rows`.
- If either source read/parse/chain/reconciliation cannot produce a valid pure receipt, or any aggregate exceeds the
  safe-integer range, status is `unavailable`; all eight totals are `null`; no known-source subtotal is published.
  Preserve the exact sorted unique capture exception union, adding only the already-allowed `local_state_failure` for
  overflow. `reconciled_source_count` still reports how many exact source receipts existed.
- Capture status is closed as follows:
  - `complete`: reconciled source count is 2; all eight totals are safe integers; capture exceptions are empty.
  - `partial`: reconciled source count is 2; all eight totals are safe integers; the nonempty exception array contains
    only pure-reconciliation exceptions (`ambiguous_completion`, `capture_not_started`, `conflicting_attempt`,
    `duplicate_attempt`, `missing_completion`, `unmatched_completion`, `usage_chain_incomplete`).
  - `unavailable`: all eight totals are null and capture exceptions are nonempty. If reconciled source count is below
    2, the array contains at least one source-boundary failure (`attempt_source_invalid`,
    `attempt_source_unreadable`, or `local_state_failure`). If reconciled source count is 2, checked-add overflow is
    the only possible reason and `local_state_failure` is required.
- Top `coverage_exceptions` remains the sorted unique union of source-publication and capture exceptions. Top status is
  complete only when both usage sources published and `capture_counts.status === "complete"`.

## Exact span contract

- Accept old exact four-key receipts for compatibility and emit no capture attributes for them.
- Accept the new exact five-key receipt only when the nested envelope satisfies its status/nullability/algebra rules
  and `union(source exceptions, capture_counts.coverage_exceptions) === top coverage_exceptions`.
- For a new receipt always emit:
  - `cfo.usage.capture.status`
  - `cfo.usage.capture.source_count`
  - `cfo.usage.capture.reconciled_source_count`
  - `cfo.usage.capture.coverage_exception_count`
  - `cfo.usage.capture.coverage_exceptions` only when nonempty
- Emit the eight `cfo.usage.capture.<count_name>` attributes only when the envelope counts are numeric. An unavailable
  envelope omits every count attribute; OTel receives no fake zero or null.
- Keep the existing span name, kind, status, content-free record, fixed errors, file permissions, and finance isolation.

## TDD order

1. RED: update the runner clean and one-missing-completion fixtures to require the exact frozen five-key receipt.
   Clean totals are `attempted=2, success=2`; the gap fixture is `attempted=2, success=1, missing=1`. Require algebra
   and absence of token/cost/private strings.
2. RED: make one attempt source unreadable while the other reconciles. Require `status=unavailable`,
   `reconciled_source_count=1`, every aggregate count exactly `null`, and no subtotal. Do not add a reconciler option,
   internal mock, or test-only export to fabricate runner overflow: two dense-array-derived source receipts cannot reach
   the safe-integer limit in this boundary.
3. GREEN runner: have the existing capture pass return either its exact pure receipt or a fixed failure; reduce once
   into the twelve-key envelope with checked addition; expose no per-source capture object.
4. RED/GREEN span in the existing runner test: exact complete, partial, and unavailable new receipts emit the fixed
   attribute set; old four-key receipt still works. Reject mixed null/numeric counts, bad algebra, wrong source count,
   extra keys, accessor/proxy, and a synthetic unsafe integer. Add one table row for each status violation: complete
   with an exception, partial without a pure exception, unavailable with a numeric count, unavailable with reconciled
   count below 2 but no source-boundary failure, and unavailable with reconciled count 2 but no
   `local_state_failure`. The synthetic unsafe value only proves span rejection; fresh Sol review inspects the runner's
   checked-add/all-null/`local_state_failure` branch. Keep the table compact.

## Verify / state

- [x] Luna observed the intended RED, then ran runner focused, reconciliation+chain+runner, `npm run test:cfo`, full
  `npm test`, syntax for all three files, `git diff --check`, and the exact three-path numstat/status gate. No docs,
  commit, push, live ledger, OTel configuration, launchd, or Telegram.
- [x] Fresh Sol checked null-not-zero truth, safe addition, algebra, exact union, old receipt compatibility, OTel omission
  on unavailable, privacy, finance isolation, and Ponytail scope. Luna fixes only required issues in the same files.
- [x] Sol reran focused 20/20, CFO 302/302, full `npm test`, syntax, diff, and three-file/42-addition gates.
  Implementation commit: `1370b19`. Next: CFO-2a2b.4 real local E2E.
