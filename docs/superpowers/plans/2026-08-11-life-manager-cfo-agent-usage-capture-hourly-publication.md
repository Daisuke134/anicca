# CFO-2a2b.3a — Hourly Named Capture-Gap Publication Plan

> **For Luna:** use Superpowers test-driven-development and verification-before-completion. Luna owns the three
> implementation files; Sol owns plan, review, verification, state, commit, and push.

**Status:** COMPLETE — implementation `75d699597`; fresh Sol implementation review: ship

**Goal:** Make the existing hourly local usage run name attempt/completion gaps in its existing immutable receipt and
existing OTel span. A forced completion-persistence failure must become `missing_completion`, never a complete run or
zero usage/cost.

**Architecture:** After each existing usage-batch attempt, the runner reads that source's adjacent write-ahead attempt
JSONL, re-reads the normalized chain, and calls `reconcileLocalAgentCapture`. It publishes only sorted fixed exception
names through the existing four-key runner receipt. The existing span already transports that top-level exception
array/count; extend only its validator to accept the closed capture exception set. Exact capture counts/envelopes are
deferred to 2a2b.3b.

**Ponytail full:** reuse the runner's sources/readFile/readChain seams, pure reconciler, four-key receipt, current span
sink and attributes. Add no module, dependency, persistence, retry, daemon, launchd label, DB, price, Telegram copy,
token/cost attribute, or cloud path.

**Hard scope gate:** exactly three existing files and <=100 gross added LOC:

- `apps/life-call/lib/cfo-local-agent-usage-runner.js`
- `apps/life-call/lib/cfo-local-agent-usage-runner.test.js`
- `apps/life-call/lib/cfo-local-agent-usage-span.js`

## Exact behavior

- Fixed source order remains Life Manager then Anicca. Derive only `agent-usage-attempts.jsonl` beside each existing
  usage source path. The producer override is not guessed by the hourly consumer.
- Run the capture pass after all existing batch attempts. Re-read each chain so a successful completion publication is
  visible and a failed completion remains unmatched.
- Parse only a Buffer containing zero or more nonempty LF-terminated JSON rows. `ENOENT` means empty attempts and the
  pure `capture_not_started` result. Non-ENOENT read failure => `attempt_source_unreadable`; malformed JSON, interior
  empty row, non-Buffer, or missing final LF => `attempt_source_invalid`; chain/reconciler failure =>
  `local_state_failure`. Never expose thrown text, path, row, ID, prompt, token, cost, credential, or owner.
- For a valid pure receipt, union its `coverage_exceptions`; a complete pure receipt adds none. Top-level exceptions are
  the sorted unique union of existing usage-publication exceptions plus both capture results. Top status is `complete`
  only when both usage sources published and the union is empty; otherwise `partial`.
- Runner output keeps exactly `status`, `collected_at`, `sources`, `coverage_exceptions`. Per-source publication objects
  remain unchanged. This slice intentionally does not expose or aggregate capture counts.
- Span receipt validation accepts only these additional sorted top-level names:
  `ambiguous_completion`, `capture_not_started`, `conflicting_attempt`, `duplicate_attempt`, `missing_completion`,
  `unmatched_completion`, `usage_chain_incomplete`, `attempt_source_invalid`, `attempt_source_unreadable`.
  `local_state_failure` is also allowed as either an existing source exception or a capture-only top-level exception.
  Existing source exceptions must remain a subset of the sorted unique top union; the difference may contain only the
  nine names above plus `local_state_failure`. A missing source exception, unknown extra, duplicate, or unsorted array
  fails closed.
- The span keeps its existing attributes. A partial capture therefore emits `collection_partial`, plus exact
  `cfo.usage.collection.coverage_exceptions` and `coverage_exception_count`. Add no new attribute key.
- Usage/capture partial or failure remains isolated from the financial Moneytree/Telegram lane; this slice triggers no
  live loop and sends no report.

## TDD order

1. RED in the existing runner test: exact four-key receipt with both clean capture sources remains complete. Model a
   producer completion-persistence failure as one durable attempt, no same-ID producer completion, successful hourly
   `writeBatch`, and an empty post-write chain; require partial with exactly `missing_completion`. Do not inject failure
   into the hourly `writeBatch`: that distinct fault correctly adds `local_state_failure`. Zero/token/cost keys are
   absent.
2. RED source-boundary table: zero-byte Buffer and attempt `ENOENT` => `capture_not_started`; Buffer `"\n"`, interior
   empty row, malformed JSON, missing final LF, and non-Buffer => `attempt_source_invalid`; non-ENOENT throw =>
   `attempt_source_unreadable`; post-chain/reconciler rejection => `local_state_failure`. Assert both exact derived
   attempt paths and the call order: every usage `writeBatch` attempt completes before the first attempt-ledger read,
   and each attempt read precedes its post-write `readChain`. Sentinel text never appears. The intended RED is missing
   capture exceptions, not fixture or dependency failure.
3. GREEN runner: retain each source path internally, perform the post-write pass, parse the attempt file with the
   closed rules, call `reconcileLocalAgentCapture`, and build one sorted union. Do not add a helper module or option.
4. GREEN span compatibility in the same runner test file: use `captureLocalAgentUsageCollection` with compact
   synthetic four-key receipts covering old complete, old source-partial, capture-only `local_state_failure`, and mixed
   source + `missing_completion`. Require one content-free local span per accepted case whose existing exception
   array/count are exact and contain no token/cost/private key. Also reject a missing source exception, unknown capture
   name, duplicate, and unsorted array. This proves production compatibility without editing the large hourly test
   file.

## Verify / state

- [x] Before Luna starts, Sol records `git status --porcelain` as the baseline containing only this plan/spec work.
  Luna runs runner focused test, reconciler+chain+runner tests, `npm run test:cfo`, full `npm test`, syntax for all three
  implementation files, and `git diff --check`. Scope is measured only from the three named implementation paths with
  `git diff --numstat -- <three paths>` and status delta from that baseline: exactly those three paths, <=100 gross
  additions. No docs, commit, push, launchd, live ledger, OTel configuration, or Telegram.
- [x] Fresh Sol review checks post-write ordering, forced gap truth, ENOENT distinction, fixed redaction, span acceptance,
  finance isolation, and Ponytail scope. Luna fixes only required issues in the same files.
- [x] Sol reruns gates: focused 8/8, reconciliation+chain+runner 19/19, CFO 301/301, full `npm test` exit 0,
  syntax/diff/scope pass. Implementation is exactly three files and 45 gross added LOC. Advance only to CFO-2a2b.3b.
