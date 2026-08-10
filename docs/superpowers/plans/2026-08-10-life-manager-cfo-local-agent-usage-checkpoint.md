# CFO-2a2a.5b1 — Local Usage Checkpoint Plan

Status: READY

## Goal

Atomically replace one small checkpoint per source after a collector batch succeeds. Persist cursor/count/coverage
facts only; never duplicate normalized events or raw agent-runner rows.

## Ponytail gate

- Add only `apps/life-call/lib/cfo-local-agent-usage-checkpoint.js` and its `.test.js`; edit only the existing
  `apps/life-call/package.json` `test:cfo` command to register the test.
- Reuse Node `fs/path`, the collector's closed receipt, and the established Life Manager state root convention. Add
  no reader/resume wiring, launchd change, second event ledger, DB, OTel, lock service, retry loop, or history index.
- Production target 55 LOC, tests 40 LOC, package +1/-1; total <=100 additions. Stop before 100 or a fourth file.

## Contract

`writeLocalAgentUsageCheckpoint(stateRoot, collectedAt, batch, options)` writes exactly:

```text
stateRoot/cfo/local-agent-usage/<source_id>.json
```

The JSON object has only `schema_version=1`, `collected_at`, `mapping_id`, `source_state`, `counts`, and
`coverage_exceptions`. It never contains `events`, input rows, prompts, responses, account data, paths, tokens, or
credentials. `source_state.source_id` chooses the fixed filename; path input cannot choose it.

`options` is omitted or exact `{fsyncImpl}`; the default is `fs.fsyncSync`. A supplied implementation must be a
non-Proxy function. Unknown keys, accessors, and Proxies are rejected before `mkdir`. The writer requires an absolute `stateRoot`, a valid RFC3339 `collectedAt`, an exact collector
five-key batch, `mapping_id=local_agent_usage_v1`, a non-null exact cursor state, and non-negative safe integers under exactly `discovered_rows|accepted_rows|duplicate_rows|
conflicting_rows|missing_usage_rows|runner_collision_groups|attributed_rows|unattributed_rows`. Exceptions must be
unique lexicographically sorted values from `conflicting_usage|incomplete_tail|invalid_source_row|missing_usage|
runner_identity_collision|source_rewritten|source_truncated|unattributed_usage`.

Require `discovered=accepted+duplicate+conflicting`, `accepted=attributed+unattributed`, `missing<=accepted`,
`runner_collision_groups<=floor(accepted/2)`, and `source_state.discovered_rows>=discovered`. The four count-derived
exceptions `conflicting_usage|missing_usage|runner_identity_collision|unattributed_usage` exist iff their count is
positive. At most one scanner exception may coexist. `source_truncated|source_rewritten|invalid_source_row` requires
`counts.discovered_rows=0`. Invalid input throws only fixed
`cfo_local_agent_checkpoint_invalid:invalid_state_root|invalid_collected_at|invalid_batch|invalid_options` before
filesystem mutation. Every filesystem failure becomes `cfo_local_agent_checkpoint_invalid:write_failed`; paths,
errno, and messages never escape.

Create or force the checkpoint directory to `0700`; create a unique same-directory temp file with `wx` and `0600`; write one
canonical JSON line, `fsync`, close, then `rename` over the prior checkpoint. On pre-rename failure, close/unlink the
temp and preserve the prior final file. Return exact frozen
`{source_id, byte_offset, discovered_rows, mapping_id}` without returning a filesystem path.

## Task 1 — RED/GREEN

Using a temporary state root, prove first write and replacement, exact file content/modes, fixed filename, no event or
secret sentinel, no residual temp, and frozen redacted receipt. Start from an existing broader-mode directory and
prove it becomes `0700`. Inject an `fsync` failure to prove the prior final file remains byte-identical and the temp is
removed. Invalid/hostile inputs create nothing and expose only the five fixed reasons.
An inconsistent non-empty batch carrying a terminal scanner defect fails `invalid_batch` without changing the prior
checkpoint.
Record missing-module RED, implement only the writer, register the test, and run focused, CFO, full, syntax, diff, and
3-file/100-added-LOC gates.

## Task 2 — Isolated real-shape evidence and close

Collect each real ledger once, write both resulting batches below a `mktemp` state root, read the two JSON files back,
and assert their cursor/count/coverage values reconcile while no events or raw rows are present. Do not touch the live
state root or launchd loop in this slice. Fresh Sol review then closes 2a2a.5b1 before reader/resume wiring 2a2a.5b2.
