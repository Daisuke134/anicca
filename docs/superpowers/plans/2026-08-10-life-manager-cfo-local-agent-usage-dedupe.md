# CFO-2a2a.2 — Local Agent Usage Dedupe Plan

Status: IN PROGRESS

## Goal

Count one opaque source-row observation once, reject a changed value under the same source-row identity, and expose
reused runner IDs without deleting distinct real attempts.

## Ponytail gate

- Extend only `apps/life-call/lib/ledger.js` and `apps/life-call/lib/ledger.test.js`.
- Reuse `canonicalJson` from `cfo-registry.js` and the shared recursive freeze helper.
- Add no scanner, state file, database, migration, scheduler, price calculation, or OTel exporter.
- Soft target: production 35 LOC, tests 30 LOC, total <=65 added LOC. Stop and re-plan before 70.

## Task 1 — RED

Add compact focused contracts for `reduceLocalAgentUsageEvents` using exact `{input, context}` pairs:

1. two identical normalized rows with one `source_event_id` yield one accepted event, one duplicate, zero conflicts,
   and covered status;
2. one unique source-row ID plus multiple values for another source-row ID keeps only the unique event and moves every
   changed row into `conflicting_rows`, independent of input order;
3. distinct source-row IDs sharing one `runner_event_id` remain accepted while incrementing a runner-collision
   coverage count;
4. missing-usage rows remain accepted but increment `missing_usage_rows`; the receipt returns sorted unique
   `coverage_exceptions` without collapsing multiple defects into one status;
5. one mixed fixture proves duplicates do not increment missing/collision counts and conflicting source IDs are
   excluded from both populations;
6. the receipt obeys discovered = accepted + duplicate + conflicting, is deeply frozen, and invalid/hostile input
   fails with `cfo_local_agent_usage_invalid:<fixed_reason>` without echoed content.

Run the focused test and record the expected missing-export failure.

## Task 2 — GREEN

Implement and export the smallest pure reducer:

- accept a dense array of exact plain `{input, context}` pairs and call `normalizeLocalAgentUsageEvent` for every pair;
- do not accept caller-supplied normalized events or copy pair extras into output;
- compare exact canonical JSON using the existing `canonicalJson` helper;
- retain one event for an all-identical ID;
- when an ID conflicts, remove its accepted event and reclassify every seen row for that ID as conflicting;
- emit one exact deeply frozen receipt:

```text
events
counts: discovered_rows, accepted_rows, duplicate_rows, conflicting_rows, missing_usage_rows,
        runner_collision_groups
coverage_exceptions: missing_usage | runner_identity_collision | conflicting_usage
```

- count `missing_usage_rows` only among final accepted events;
- count `runner_collision_groups` only among final accepted events, grouping runner IDs with at least two distinct
  accepted source IDs; duplicates add nothing and conflicting source IDs are excluded from both counts;
- sort events by `source_event_id` and exceptions lexicographically as
  `conflicting_usage, missing_usage, runner_identity_collision`;
- never sum token values, select a winning conflicting value, or include source content in errors.

Run focused, `npm run test:cfo`, `npm test`, syntax, `git diff --check`, and the 2-file/70-LOC gate.

## Task 3 — Real evidence and close

Derive verification-only source refs using the spec formula, fixed source IDs `life_manager_agent_usage` and
`anicca_agent_usage`, and each complete line's zero-based starting byte offset encoded as decimal ASCII. Then reduce
both real local ledgers read-only. Print counts only and assert:

- every source row belongs to accepted, duplicate, or conflicting;
- no conflicting ID remains accepted;
- distinct rows with reused runner IDs remain accepted and the collision count matches the read-only source audit;
- missing-usage count matches the source ledger and appears in `coverage_exceptions`;
- input order reversal produces the identical receipt;
- no prompt, response, path, raw payload, or secret is emitted.

Fresh Sol review checks only correctness, evidence truth, redaction, determinism, and YAGNI. Sol then updates the child
status, commits, pushes, and starts 2a2a.3.
