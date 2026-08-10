# CFO-2a2a.5b2a — Immutable Local Usage Chain Reader Plan

Status: COMPLETE

> **Execution:** Sol owns plan/verification. Luna owns production code and tests.

## Goal

Read one source's immutable batch directory, accept only one contiguous history, and return the last durable cursor plus
deduplicated normalized token events. Missing storage means first run; corrupt or forked storage never silently resets.

## Ponytail gate

- Create only `apps/life-call/lib/cfo-local-agent-usage-chain.js` and its `.test.js`; edit only `package.json` test:cfo.
- Reuse Node `fs/path/crypto`, `createCfoSupabaseRpc`, and the exact 5b1 record format. Add no writer changes, runner,
  launchd, OTel, pricing, report, recovery loop, DB, or dependency.
- Soft target: production 55 LOC, tests 40 LOC, package +1/-1; hard gate: 3 files and <=100 additions.

## Contract

`readLocalAgentUsageChain(stateRoot, sourceId)` returns a deeply frozen exact result.

No source directory returns:

```text
status=empty, source_state=null, record_count=0, events=[],
counts=<eight zeros>, coverage_exceptions=[]
```

This means “first collection is required,” never “coverage is complete.” A non-empty directory returns the same keys
with `status=ready`, the last accepted `source_state`, unique accepted-record count, deduplicated events sorted by
`source_event_id`, cumulative counts, and current coverage exceptions.

Validate canonical absolute non-root `stateRoot` and the two fixed source IDs before I/O. Discover only exact
`<64 lowercase hex>.json` finals; ignore dot-prefixed `.tmp` remnants; any other entry fails closed. For every final:

- read bytes once and require SHA-256(bytes) to equal its filename;
- require the exact eight-key 5b1 record, schema 1, valid timestamp/mapping, exact null-or-cursor prior state, exact
  current cursor state for this source, an events array, exact eight non-negative delta counts, and sorted fixed
  exceptions;
- require event count/count algebra to agree with the record. Every event must have the exact normalized top-level
  key set, exact `run` and `tokens` key sets, no accessors/extra content keys, canonical
  `local_agent_usage:<64 hex>` identity, and valid primitive values for the fields emitted by the existing normalizer.

Before chain comparison, dedupe byte-equivalent transitions excluding only `collected_at`; this makes an ambiguous
successful retry with a new timestamp idempotent. Build order from cursor linkage, not hashes or timestamps. Starting
from null, at each state accept its zero-delta prior=current observations in parsed-time/record-ID order, then require
at most one advancing record whose prior equals that state. Two distinct advancing records are a fork; any unconsumed
record is a gap. This also handles a valid parent and child with the same timestamp. Only self-loop observation order
uses `collected_at`, and only the latest accepted record contributes current source-defect status.

Byte-equivalent transitions are removed before counting. Across the remaining accepted transitions, any repeated
`source_event_id` fails closed; legitimate cursor offsets cannot produce it. Cumulative
`discovered|duplicate|conflicting` are sums of unique record deltas.
`accepted|missing|runner-collision|attributed|unattributed` are recomputed from unique canonical events. The permanent
exceptions derive from cumulative conflicting rows and current event facts; only the latest record contributes
`partial_tail|invalid_source_row|source_rewritten|source_truncated`.

Argument errors are exactly `cfo_local_agent_usage_chain_invalid:invalid_state_root|invalid_source`. Any existing
directory/read/hash/schema/chain/event failure is exactly `cfo_local_agent_usage_chain_invalid:read_failed`; dynamic
paths, record bytes, event content, and errno never escape.

## Task 1 — RED, GREEN, gates

Luna writes three compact tests:

1. Missing source directory returns the exact frozen empty result; temp remnants remain ignored.
2. Use 5b1 to publish an initial batch, an identical-transition retry with a later timestamp, one zero-delta
   observation, and one real append sharing its parent's timestamp. Reader orders by linkage and returns one contiguous
   state, three unique accepted records, sorted unique events, recomputed cumulative counts/exceptions, exact event
   shapes, and never mutates stored data.
3. A table proves exact redacted failures for bad arguments, hash/content corruption, unknown files, broken prior
   state, fork, the same event ID repeated across distinct transitions with either identical or different content,
   and a re-hashed event carrying an extra `prompt: "HOSTILE_SECRET"` key.

Run missing-module RED, implement only the reader, register the test, then run focused reader; store+reader; all local
usage focused tests; `npm run test:cfo`; `npm test`; syntax; `git diff --check`; and the 3-file/100-line gate.

## Task 2 — Real isolated evidence and close

Sol publishes one real batch per source under `mktemp`, reads both chains, and proves event/count/cursor equality with
the writer receipts. Fresh Sol review must return ship before commit/push. Then 2a2a.5b2b becomes the sole active item:
read both source files once, resume from these cursors, and publish the next immutable batches in one local runner.

## Completion evidence

- Missing-module RED; reader focused 4/4 and complete local-usage focused suite 15/15.
- Scope: 53 production lines + 46 test lines + one suite entry = 3 files and exactly 100 additions; lockfile unchanged.
- CFO suite and full `npm test` have zero failures; syntax/diff checks pass; fresh Sol review returned `ship` after the
  deterministic duplicate-transition representative fix.
- Real isolated writer→reader E2E reconciled two chains and 4,987/4,987 accepted events: 3,917 attributed,
  1,070 unattributed, 279 missing-usage rows, and 437 runner-collision groups. Temporary state was removed; live state
  and launchd were untouched.
- Tests prove same-timestamp causal ordering, ambiguous-retry dedupe, clean/defect self-loop determinism, exact event
  privacy shape, fork/gap/hash failure, and same event ID rejection across distinct transitions.
