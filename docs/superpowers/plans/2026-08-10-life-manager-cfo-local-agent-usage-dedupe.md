# CFO-2a2a.2 — Local Agent Usage Dedupe Plan

Status: READY

## Goal

Count an identical deterministic event once and exclude every version of a conflicting ID, so a source rewrite can
never silently change a CFO token total.

## Ponytail gate

- Extend only `apps/life-call/lib/ledger.js` and `apps/life-call/lib/ledger.test.js`.
- Reuse `canonicalJson` from `cfo-registry.js` and the shared recursive freeze helper.
- Add no scanner, state file, database, migration, scheduler, price calculation, or OTel exporter.
- Soft target: production 35 LOC, tests 30 LOC, total <=65 added LOC. Stop and re-plan before 70.

## Task 1 — RED

Add compact focused contracts for `reduceLocalAgentUsageEvents`:

1. two identical normalized rows yield one accepted event, one duplicate, zero conflicts, and covered status;
2. one unique ID plus multiple values for another ID keeps only the unique event and moves every row for the changed
   ID into `conflicting_rows`, independent of input order;
3. the receipt obeys discovered = accepted + duplicate + conflicting, is deeply frozen, and invalid/hostile input
   fails with `cfo_local_agent_usage_invalid:<fixed_reason>` without echoed content.

Run the focused test and record the expected missing-export failure.

## Task 2 — GREEN

Implement and export the smallest pure reducer:

- accept an array of plain normalized events with valid `agent_usage:<24 hex>` IDs;
- compare exact canonical JSON using the existing `canonicalJson` helper;
- retain one event for an all-identical ID;
- when an ID conflicts, remove its accepted event and reclassify every seen row for that ID as conflicting;
- emit sorted accepted events plus frozen integer counts and `covered|conflicting_usage`;
- never sum token values, select a winning conflicting value, or include source content in errors.

Run focused, `npm run test:cfo`, `npm test`, syntax, `git diff --check`, and the 2-file/70-LOC gate.

## Task 3 — Real evidence and close

Normalize and reduce both real local ledgers read-only. Print counts only and assert:

- every source row belongs to accepted, duplicate, or conflicting;
- no conflicting ID remains accepted;
- input order reversal produces the identical receipt;
- no prompt, response, path, raw payload, or secret is emitted.

Fresh Sol review checks only correctness, evidence truth, redaction, determinism, and YAGNI. Sol then updates the child
status, commits, pushes, and starts 2a2a.3.
