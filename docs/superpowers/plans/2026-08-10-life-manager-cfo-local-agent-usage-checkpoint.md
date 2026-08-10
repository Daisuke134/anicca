# CFO-2a2a.5b1 — Immutable Local Usage Batch Plan

Status: READY FOR LUNA

> **Execution:** Sol owns plan/verification. Luna owns production code and tests.

## Goal

Durably couple each collector cursor advance with the exact content-free normalized events it produced. A cursor is
never published without its events, so resume cannot permanently skip token usage.

## Architecture

The sole canonical local-usage evidence store is a fixed per-source directory of immutable batch JSON files. One file
contains the prior/current cursor states, normalized events, mapping version, delta counts, collection time, and
coverage exceptions. There is no separate checkpoint, JSONL repair path, SQLite database, or duplicate event store.
The next slice derives resume state by replaying only a contiguous validated file chain.

## Ponytail gate

- Create only `apps/life-call/lib/cfo-local-agent-usage-batch-store.js` and its `.test.js`; edit only
  `apps/life-call/package.json` `test:cfo`.
- Reuse Node `fs/path/crypto`, `createCfoSupabaseRpc`, and `collectLocalAgentUsageBatch`. Add no reader, scheduler, DB, RPC,
  OTel, retry loop, pricing, or report code.
- Soft target: production 55 LOC, tests 40 LOC, package +1/-1; hard gate: 3 files and <=100 added lines from this
  plan's commit.

## Contract

`collectAndWriteLocalAgentUsageBatch(stateRoot, collectedAt, sourceId, bytes, priorSourceState, options = {})` calls
the canonical collector exactly once, then publishes:

```text
stateRoot/cfo/local-agent-usage/<source_id>/<record_id>.json
```

The canonical one-line record has exactly:

```text
schema_version=1, collected_at, mapping_id, prior_source_state,
source_state, events, delta_counts, coverage_exceptions
```

`record_id` is SHA-256 of those exact JSON bytes and is used only as the fixed filename/return identity. The record
contains normalized content-free events, but never raw rows, prompts, responses, account data, filesystem paths, or
credentials. Counts are explicitly deltas; no slice calls them cumulative or aggregate.

Validate before filesystem mutation:

- absolute `stateRoot` and RFC3339 `collectedAt`;
- empty options or exact `{fsyncImpl}`, where the function defaults to `fs.fsyncSync`;
- then pass `sourceId`, `bytes`, and `priorSourceState` unchanged to `collectLocalAgentUsageBatch`; do not recreate or
  trust a caller-supplied batch. The collector is the single validator for source/state/events/count reconciliation.

Store input errors throw only `cfo_local_agent_usage_batch_store_invalid:invalid_state_root|invalid_collected_at|
invalid_options`. Canonical collector errors pass through unchanged before mutation. Filesystem failures throw only
`cfo_local_agent_usage_batch_store_invalid:write_failed`.

Create/force the fixed directories to `0700`. Write a unique same-directory temp using `wx`/`0600`, fsync and close,
rename to the content-addressed final path, then fsync the source directory. A byte-identical existing final file is an
idempotent retry and must also directory-fsync before success. A pre-rename failure closes/unlinks the temp and leaves
all prior receipts byte-identical. Return the frozen content-free receipt
`{record_id, source_id, byte_offset, event_count, mapping_id}`.

Design basis: existing `scripts/daily-preflight.js`, Node
[`fs.fsyncSync`](https://nodejs.org/api/fs.html#fsfsyncsyncfd), Node
[`fs.renameSync`](https://nodejs.org/api/fs.html#fsrenamesyncoldpath-newpath), and POSIX
[`rename`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/rename.html).

## Task 1 — RED, GREEN, gates

Luna writes three compact tests:

1. Real two-row bytes publish one exact immutable record; a later append publishes a second prior→current record.
   Serialized output contains normalized events/cursor states but no raw/secret sentinel. Repeating identical input
   returns the same identity and creates no duplicate.
2. Injected file-fsync failure leaves prior receipts byte-identical and no temp. Injected directory-fsync failure
   occurs after final publication; the same-input retry converges to that one byte-identical final record.
3. One table covers the three store input errors plus redacted canonical collector errors before any directory exists.

Run missing-module RED, implement only the store, register the test, then run its focused test; cursor + attribution +
collector + store tests; `npm run test:cfo`; `npm test`; both `node --check` commands; `git diff --check`; and the
3-file/100-added-line gate.

## Task 2 — Isolated real-shape evidence and close

Sol reads each real ledger once and writes both batches below one `mktemp` root. Read the two immutable records back
and prove exact current cursor/delta/event reconciliation, zero raw rows/secrets/paths, and no mutation of real state.
Fresh Sol review must return ship before commit/push. Then 2a2a.5b2 becomes the sole active item: validate the
prior→current chain, dedupe `source_event_id`, recompute event-derived coverage, accumulate unique delta audit counts,
and resume from the last accepted record.
