# CFO-2a2b.2 — Pure Attempt/Completion Reconciliation Plan

> **For Luna:** use Superpowers test-driven-development and verification-before-completion. Luna owns production/test
> edits; Sol owns plan, review, final verification, state, commit, and push.

**Status:** READY FOR LUNA — fresh Sol plan review: ship

**Goal:** Join validated write-ahead attempts to normalized usage completions by their shared 24-hex ID and return one
exact frozen counts receipt. Missing persistence becomes a coverage gap, never zero usage or zero cost.

**Architecture:** Add one pure CommonJS module and one focused test. The function receives a fixed source ID, parsed
attempt rows, and the existing immutable usage-chain result. It reads no file, clock, env, DB, network, OTel,
Moneytree, Telegram, or provider and writes nothing.

**Ponytail full:** Reuse `createCfoSupabaseRpc` validation/freeze helpers, the completed usage-chain event shape, native
maps/sets, and the producer's shared ID. Add no scanner, persistence, retry, service, agent, price, percentage, or UI.

**Hard scope gate:** exactly three files and <=95 gross added LOC:

- `apps/life-call/lib/cfo-local-agent-capture-reconciliation.js`
- `apps/life-call/lib/cfo-local-agent-capture-reconciliation.test.js`
- `apps/life-call/package.json` — append only the new test path to `test:cfo`

## Exact contract

Export `reconcileLocalAgentCapture(sourceId, attemptRows, usageChain)` and return exactly:

```json
{"schema_version":1,"source_id":"anicca_agent_usage","status":"partial","cutover_at":"2026-08-11T01:00:00.000000+00:00","attempted_rows":4,"success_rows":1,"failed_rows":1,"missing_completion_rows":2,"unmatched_completion_rows":2,"duplicate_attempt_rows":0,"conflicting_attempt_rows":0,"ambiguous_completion_rows":0,"coverage_exceptions":["missing_completion","unmatched_completion","usage_chain_incomplete"]}
```

- Sources are exactly `life_manager_agent_usage` or `anicca_agent_usage`.
- `attemptRows` is an ordinary dense array of exact eight-key producer rows. Validate version 1, 24 lowercase hex ID,
  RFC3339 timestamp with UTC zone (`Z` or `+00:00`), nonempty trimmed strings, and safe integer attempt >=1.
- `usageChain` is an exact six-key `readLocalAgentUsageChain` receipt. Validate status, counts/state containers,
  coverage array, and each event's exact existing keys; require its source ledger, 24-hex runner ID, timestamp, and
  `run.status` (`success|failed`). A ready chain must have `source_state.source_id === sourceId`; an empty chain must
  have null state. Reject proxy/accessor/sparse/extra-key input with fixed redacted
  `cfo_local_agent_capture_invalid:<reason>` errors before reading any hostile value.
- Cutover is the earliest valid attempt instant; ties use the lexically smallest timestamp. Completions before cutover
  are historical and excluded. Empty attempts return `status=empty`, null cutover, zero counts, and only
  `capture_not_started`; historical completion is never called covered.
- Identical attempt rows count once and add `group size - 1` duplicates. If one ID has multiple canonical values,
  exclude that group; count every row as conflicting and zero duplicates for the group (`A,A,B` => conflict 3).
- For one nonconflicting attempt: one matching completion classifies the existing run status; zero is missing; more
  than one remains missing and counts every matching completion as ambiguous. A post-cutover completion matching no
  nonconflicting attempt is unmatched. Compare `Date.parse` millisecond instants because normalized completions retain
  millisecond precision. Equality at that precision matches; an earlier millisecond does not. A same-ID earlier
  completion leaves the attempt missing and that post-cutover completion unmatched. Never sum, copy, price, print, or
  coerce token/cost values.
- Require `success + failed + missing = attempted`. `complete` requires every capture count exception to be zero and
  an otherwise clean ready usage chain. A nonempty upstream chain coverage array adds `usage_chain_incomplete` so a
  truncated/re-written/missing-usage chain can never yield a complete total.
- Sorted unique exceptions are exactly `ambiguous_completion`, `conflicting_attempt`, `duplicate_attempt`,
  `missing_completion`, `unmatched_completion`, `usage_chain_incomplete`, or `capture_not_started`.

## TDD order

1. RED `normal rows reconcile exactly`: module missing. Use attempts at 01:00 success, 01:01 failed, 01:02 missing,
   and 01:03 with a same-ID 01:02:30 completion. Add one historical 00:59 completion, one unrelated 01:04 completion,
   and upstream `missing_usage`. Assert exact equality to the 13-key literal above, its algebra, and deep freeze. Add a
   same-millisecond case where attempt fractional precision exceeds three digits and the normalized completion is equal.
2. GREEN: implement boundary validation plus the direct map/set join; no helper file or class. Append the new test path
   to the existing explicit `test:cfo` list so every future CFO gate executes it; change no other package script.
3. RED then GREEN in the same test file: compact subtests for empty capture; identical duplicate; `A,A,B` conflict;
   multiple completions; cross-source ready chain (`source_state.source_id` and events); sparse/proxy/accessor/extra-key
   attempt; and extra prompt on an event. Every
   rejection must equal the fixed prefix and exclude the `HOSTILE_SECRET` sentinel.

Core implementation shape:

```javascript
const groups = new Map();
for (const row of attemptRows) {
  const signature = canonicalJson(row);
  const group = groups.get(row.event_id) || new Map();
  group.set(signature, (group.get(signature) || 0) + 1);
  groups.set(row.event_id, group);
}
const completions = usageChain.events.filter(event => Date.parse(event.occurred_at) >= Date.parse(cutover_at));
```

## Verify / state

- [ ] Luna runs `node --test apps/life-call/lib/cfo-local-agent-capture-reconciliation.test.js`, existing local usage
  normalizer/chain tests, `npm run test:cfo`, full `npm test`, `node --check` on both files, `git diff --check`, and
  `git diff --numstat`; exactly three files and <=95 gross additions. The focused command and `test:cfo` must both
  execute the new test; full `npm test` remains a separate regression gate. No docs, commit, push, or live state.
- [ ] Fresh Sol review checks count truth, historical cutover, upstream coverage, algebra, redaction, and scope. Luna
  fixes only required issues in the same files.
- [ ] Sol independently reruns gates, updates specs, commits/pushes, and advances only to CFO-2a2b.3.
