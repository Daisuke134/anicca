# CFO-2a2a.5a — Local Usage Collector Plan

Status: READY

## Goal

Compose the completed source scanner, versioned attribution resolver, and reducer into one pure batch receipt. Never
return an advanced cursor unless every emitted row normalized and reduced successfully.

## Ponytail gate

- Add only `apps/life-call/lib/cfo-local-agent-usage-collector.js` and its `.test.js`; edit only the existing
  `apps/life-call/package.json` `test:cfo` command to register the test.
- Reuse the three completed modules and shared freeze helper. Add no second raw ledger, filesystem I/O, state writer,
  DB/RPC/migration, OTel, retry, scheduler, price logic, or new mapping.
- Production target 45 LOC, tests 45 LOC, package +1/-1; total <=95 additions. Stop before 100 or a fourth file.

## Contract

`collectLocalAgentUsageBatch(data, {source_id, prior_state})` returns exact deeply frozen:

```text
events
source_state
mapping_id = local_agent_usage_v1
counts = reducer counts + attributed_rows + unattributed_rows
coverage_exceptions
```

The collector calls the scanner once, resolves every scanned row, adds only `financial_unit_id` to its source context,
then calls the reducer once. `events` are the reducer's canonical sorted events and `source_state` is the scanner state.
Counts satisfy `accepted_rows = attributed_rows + unattributed_rows`; all reducer count equations remain unchanged.

`coverage_exceptions` is the unique lexicographic union of scanner and reducer exceptions plus
`unattributed_usage` iff an accepted event is unattributed. Missing usage, runner identity collision, conflicts,
rewrite, committed-prefix truncation, invalid source rows, and incomplete tails remain visible under their existing
fixed names. The collector never reads event content into errors and throws only fixed
`cfo_local_agent_collector_invalid:invalid_batch` for an unexpected composition failure. Existing scanner input errors
keep their own fixed prefix.

## Task 1 — RED/GREEN

Test a mixed valid batch containing one attributed provider-reported row and one unattributed unavailable row. Assert
exact events/state/mapping/counts/exceptions, deterministic order, deep freeze, no input mutation, and reducer success
before state exposure. Also prove scanner truncate/rewrite/partial receipts pass through, and a schema-invalid complete
row throws without any receipt/state. Record missing-module RED; implement only the composer; run focused, CFO, full,
syntax, diff, and 3-file/95-added-LOC gates.

## Task 2 — Real evidence and close

Read both actual ledgers once each, collect from null state, resume each fixed snapshot, and print counts only. Assert
all snapshot rows reconcile across accepted/attributed/unattributed and the second pass emits zero events. Fresh Sol
review then closes 2a2a.5a before planning checkpoint persistence 2a2a.5b.
