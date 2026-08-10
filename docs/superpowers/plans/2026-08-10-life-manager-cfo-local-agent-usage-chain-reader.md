# CFO-2a2a.5b2a — Immutable Local Usage Chain Reader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** IN PROGRESS — boundary-hardening delta remains

**Goal:** Read one source's immutable batches, accept exactly one contiguous history, and return its last durable cursor plus deduplicated normalized events.

**Architecture:** Validate content-addressed records at the filesystem boundary, reuse the existing event normalizer as the canonical event validator, then derive order only from prior→current cursor linkage. Missing storage is first run; corrupt, forked, or gapped storage fails closed.

**Tech stack:** Node.js CommonJS, `node:fs`, `node:path`, `node:crypto`, `node:test`, existing CFO validators/normalizer; no dependency changes.

## Global constraints

- Local Mac first. Sol owns plan, review, real E2E, spec update, commit, and push; Luna owns production/test edits and implementation commands only.
- Create only `apps/life-call/lib/cfo-local-agent-usage-chain.js` and its test; modify only `apps/life-call/package.json` to register the test.
- Soft target: production +55, tests +40, package +1/-1; hard stop before >100 additions or a fourth file.
- Ponytail full: reuse the exact 5b1 record, `createCfoSupabaseRpc`, and `normalizeLocalAgentUsageEvent`; add no writer change, runner, launchd, OTel, pricing, report, recovery loop, DB, migration, or dependency.
- No result, error, or test log may expose a path, record bytes, event content, prompt, response, credential, or errno.
- Test first. Luna does not commit or push.

### Task 1 — RED, GREEN, and implementation gates

#### Required contract

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

- open with `O_RDONLY|O_NOFOLLOW`, then use that same descriptor for `fstat` and one read; require a regular file with
  no group/other mode bits and SHA-256(bytes) equal to its filename;
- require the exact eight-key 5b1 record, schema 1, valid timestamp/mapping, exact null-or-cursor prior state, exact
  current cursor state for this source, an events array, exact eight non-negative delta counts, and sorted fixed
  exceptions;
- require event count/count algebra to agree with the record. Every event must have the exact normalized top-level
  key set, exact `run` and `tokens` key sets, no accessors/extra content keys, canonical
  `local_agent_usage:<64 hex>` identity, and valid primitive values. Reconstruct only the raw fields accepted by
  `normalizeLocalAgentUsageEvent`, normalize with the stored source-row/financial-unit identity, and require the
  resulting canonical event to equal the stored event exactly. Do not create a second event schema implementation.

Before chain comparison, dedupe byte-equivalent transitions excluding only `collected_at`; retain the smallest
`collected_at,record_id` pair deterministically. This makes an ambiguous successful retry with a new timestamp
idempotent. Build order from cursor linkage, not hashes or timestamps. Starting
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

#### Files and interface

**Files:**
- Create: `apps/life-call/lib/cfo-local-agent-usage-chain.js`
- Create: `apps/life-call/lib/cfo-local-agent-usage-chain.test.js`
- Modify: `apps/life-call/package.json`

**Interface:** `readLocalAgentUsageChain(stateRoot, sourceId)` returns a deeply frozen exact six-key result and performs no writes.

- [ ] **Step 1: Write missing-module RED**

Create the test/import first. Run from `apps/life-call`:

```bash
node --test lib/cfo-local-agent-usage-chain.test.js
```

Expected RED: `MODULE_NOT_FOUND` for the chain module. Record it before production code exists.

- [ ] **Step 2: Implement only record validation and chain derivation**

Use the Contract verbatim. One directory listing, one fd-bound read per final, no write/recovery behavior. Return exact keys in this order:

```text
status, source_state, record_count, events, counts, coverage_exceptions
```

`counts` uses the existing eight collector count keys. Clone/deep-freeze the result; never freeze caller or parsed temporary inputs.

- [ ] **Step 3: Prove the three observable behaviors**

Luna writes three compact tests:

1. Missing source directory returns the exact frozen empty result; temp remnants remain ignored.
2. Use 5b1 to publish an initial batch, an identical-transition retry with a later timestamp, one zero-delta
   observation, and one real append sharing its parent's timestamp. Reader orders by linkage and returns one contiguous
   state, three unique accepted records, sorted unique events, recomputed cumulative counts/exceptions, exact event
   shapes, and never mutates stored data.
3. A table proves exact redacted failures for bad arguments, hash/content corruption, unknown files, broken prior
   state, fork, the same event ID repeated across distinct transitions with either identical or different content,
   and a re-hashed event carrying an extra `prompt: "HOSTILE_SECRET"` key.

- [ ] **Step 4: Run GREEN and Ponytail gates**

Run from `apps/life-call`:

```bash
node --test lib/cfo-local-agent-usage-chain.test.js
node --test lib/cfo-local-agent-usage-batch-store.test.js lib/cfo-local-agent-usage-chain.test.js
node --test lib/cfo-local-agent-usage-cursor.test.js lib/cfo-local-agent-usage-attribution.test.js lib/cfo-local-agent-usage-collector.test.js lib/cfo-local-agent-usage-batch-store.test.js lib/cfo-local-agent-usage-chain.test.js
npm run test:cfo
npm test
node --check lib/cfo-local-agent-usage-chain.js
node --check lib/cfo-local-agent-usage-chain.test.js
```

From the worktree root run `git diff --check`, `git diff --name-only`, and `git diff --numstat`. Expected: every command exits `0`; exactly three owned files; <=100 additions. Write the detailed SDD report; do not commit or push.

### Task 2 — Sol real isolated evidence and close

- [ ] Sol publishes one real batch per source under `mktemp`, reads both chains, and proves event/count/cursor equality with
the writer receipts. Fresh Sol review must return ship before commit/push. Then 2a2a.5b2b becomes the sole active item:
read both source files once, resume from these cursors, and publish the next immutable batches in one local runner.

## Preliminary evidence (must be rerun after boundary hardening)

- Missing-module RED; reader focused 4/4 and complete local-usage focused suite 15/15.
- Scope: 53 production lines + 46 test lines + one suite entry = 3 files and exactly 100 additions; lockfile unchanged.
- CFO suite and full `npm test` had zero failures; syntax/diff checks passed. A later remote-plan reconciliation added
  fd-bound no-follow reading and canonical normalizer reuse, so the prior ship verdict is superseded until those gates
  pass on the reconciled implementation.
- Real isolated writer→reader E2E reconciled two chains and 4,987/4,987 accepted events: 3,917 attributed,
  1,070 unattributed, 279 missing-usage rows, and 437 runner-collision groups. Temporary state was removed; live state
  and launchd were untouched.
- Tests prove same-timestamp causal ordering, ambiguous-retry dedupe, clean/defect self-loop determinism, exact event
  privacy shape, fork/gap/hash failure, and same event ID rejection across distinct transitions.
