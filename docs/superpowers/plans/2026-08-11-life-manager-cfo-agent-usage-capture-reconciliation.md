# CFO-2a2b.2 — Pure Attempt/Completion Reconciliation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use Superpowers test-driven-development and
> verification-before-completion. Luna owns production/test edits; Sol owns this plan, review, final verification,
> state, commit, and push.

**Status:** COMPLETE — implementation `88f5c50f8`; fresh review `ship — Spec ✅`

**Goal:** Join validated write-ahead attempts to existing normalized usage completions by the shared 24-hex ID and
return one exact frozen counts receipt. Missing persistence becomes an integer coverage gap, never zero usage/cost.

**Architecture:** Add one pure CommonJS module and one focused test in `apps/life-call/lib`. The function receives one
fixed source ID, parsed attempt rows, and the existing immutable usage-chain result. It reads no file, clock, env, DB,
network, OTel, Moneytree, Telegram, or provider and writes nothing.

**Ponytail full decision:** Reuse the completed usage-chain event schema, `createCfoSupabaseRpc` validation/freeze
helpers, Node collections, and the producer's shared ID. Add no scanner, persistence layer, retry, service, new agent,
pricing, percentage, or report UI in this slice.

**Soft target:** two new files and <=95 added LOC total:

- `apps/life-call/lib/cfo-local-agent-capture-reconciliation.js`
- `apps/life-call/lib/cfo-local-agent-capture-reconciliation.test.js`

## Exact receipt

```json
{"schema_version":1,"source_id":"anicca_agent_usage","status":"partial","cutover_at":"<ISO>","attempted_rows":3,"success_rows":1,"failed_rows":1,"missing_completion_rows":1,"unmatched_completion_rows":0,"duplicate_attempt_rows":0,"conflicting_attempt_rows":0,"ambiguous_completion_rows":0,"coverage_exceptions":["missing_completion"]}
```

- Allowed sources are exactly `life_manager_agent_usage` and `anicca_agent_usage`.
- Attempt input is a dense array of exact producer rows. Each row has the eight-key schema from the child spec,
  valid UTC timestamp, nonempty trimmed strings, attempt integer >=1, and 24 lowercase hex ID. Malformed/hostile input
  throws one fixed redacted `cfo_local_agent_capture_invalid:<reason>` error.
- The usage-chain input is the exact frozen-compatible chain shape already produced by
  `readLocalAgentUsageChain`; only its validated normalized events are joined. Events earlier than `cutover_at` are
  historical and excluded from capture coverage. `cutover_at` is the earliest valid attempt timestamp.
- An empty attempt array returns `status=empty`, null cutover, zero counts, and
  `coverage_exceptions=["capture_not_started"]`; historical usage is not called covered.
- Identical repeated attempt rows count once plus `duplicate_attempt_rows = group rows - 1`. Same ID with more than one
  canonical attempt value is excluded and `conflicting_attempt_rows` counts every row in that group; conflict takes
  precedence, so an `A,A,B` group contributes conflict `3` and duplicate `0`.
- Exactly one completion for one nonconflicting attempt classifies its existing `run.status` as success or failed.
  Zero completions increments missing. More than one leaves that attempt missing and
  `ambiguous_completion_rows` counts every completion row in that multi-row group, not the number of attempts.
- A completion at/after cutover whose ID matches no nonconflicting attempt increments unmatched. No token or cost value
  is summed, priced, coerced, copied, or printed.
- `status=complete` only when all exception counts are zero; otherwise `partial`. The sorted unique exception names are
  exactly: `ambiguous_completion`, `conflicting_attempt`, `duplicate_attempt`, `missing_completion`,
  `unmatched_completion`, or `capture_not_started`. Always require
  `success_rows + failed_rows + missing_completion_rows = attempted_rows`.

## RED / GREEN / VERIFY / STATE

- [x] RED: one compact table/subtest proves normal success+failure+missing, historical completion exclusion,
  post-cutover unmatched completion, exact duplicate/conflict/ambiguity counts, empty cutover, exact frozen keys, and
  fixed redacted rejection of malformed/proxy/sparse/extra-key inputs. Record the genuine current-module-missing RED.
- [x] GREEN: implement only the pure function and export it. Normalize attempt signatures in fixed field order; do not
  trust object insertion order. Derive the exact receipt and algebra once, then deep-freeze it.
- [x] Luna runs focused tests, existing usage ledger/collector/chain tests, CFO suite, full npm test, syntax, diff check,
  and reports exact counts/diffstat. No docs, commit, push, or live state.
- [x] Fresh Sol review checks truth, historical cutover, algebra, redaction, and Ponytail scope. Luna fixes only required
  issues in the same two files. Sol independently reruns gates, updates specs, commits/pushes, and advances only to
  CFO-2a2b.3.

## Completion evidence

- Genuine RED: the focused test failed because the reconciliation module did not exist.
- Final scope: exactly two new files, 86 added LOC total (47 production + 39 test), with no dependency or runtime
  mutation.
- Sol verification: focused 5/5, relevant usage/CFO tests 38/38, registered CFO suite 297/297, full `npm test` exit 0,
  syntax and `git diff --check` pass.
- Fresh review fix round 1 closed derived-chain validation and accessor evaluation; both findings are ADDRESSED, no new
  breakage, final verdict `ship — Spec ✅`.
- Controller fix round 2 registered the five reconciliation tests in `test:cfo` exactly once. RED proved the prior CFO
  suite contained zero of their exact names; GREEN proved all five run inside the 297/297 suite. Fresh scoped review
  again returned `ship — Spec ✅`.
- This slice reads and writes no ledger, publishes no OTel span, computes no price, and sends no Telegram message.
