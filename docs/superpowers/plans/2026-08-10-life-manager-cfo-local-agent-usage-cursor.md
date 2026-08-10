# CFO-2a2a.3 — Append-only Local Usage Cursor Plan

Status: IN PROGRESS — implementation reviewed; normal-suite registration remains

## Goal

Read each newly appended complete JSONL row once, derive its identity from the source byte offset, and expose a
trusted-prefix rewrite, truncation, invalid complete row, or partial tail without inventing usage.

## Ponytail gate

- Add `apps/life-call/lib/cfo-local-agent-usage-source.js` and its `.test.js`; edit only the existing
  `apps/life-call/package.json` `test:cfo` command to register the test.
- Reuse Node Buffer/crypto and the shared exact/freeze helpers. Schema validation/dedupe remains in the completed
  `reduceLocalAgentUsageEvents`; the caller persists cursor state only after that reducer succeeds.
- Add no dependency, watcher, launchd job, I/O owner, database, scheduler, OTel, retry, price logic, or mapping.
- Measured target: production 48 LOC, test 47 LOC, package command +1/-1; total +96/-1 across three files. Stop before
  100 additions or a fourth file.

## Task 1 — RED/GREEN evidence

`scanLocalAgentUsageSource(data, {source_id, prior_state})` has one pure contract:

1. exact result `{pairs, state, coverage_exceptions}`; exact state
   `{source_id, byte_offset, prefix_sha256, discovered_rows}`; exact pairs
   `{input, context:{source_row_ref}}`;
2. the two source IDs are closed; byte offsets and refs remain correct after multibyte UTF-8;
3. unchanged resume returns zero rows and an append returns only new complete rows;
4. shorter trusted data returns `source_truncated`; changed trusted prefix returns `source_rewritten`;
5. a partial tail remains unparsed as `incomplete_tail`; any malformed complete row atomically returns no pairs and
   preserves prior state as `invalid_source_row`;
6. invalid arguments throw only `cfo_local_agent_source_invalid:<fixed_reason>`; output is cloned/deep-frozen and
   input is neither mutated nor frozen.

The missing-module RED and focused 3/3 GREEN are recorded. Fresh Sol review found and Luna fixed trusted-terminal-LF
rewrite precedence. Re-review returned `ship — Spec ✅`. Implementation plus test is 95 additions.

## Task 2 — Normal-suite registration

Append only `lib/cfo-local-agent-usage-source.test.js` to the existing `test:cfo` command. Do not edit the lockfile.
Prove `npm run test:cfo` and `npm test` both execute the three named cursor cases, then run syntax and
`git diff --check` and confirm the exact three-file +96/-1 gate.

## Task 3 — Real evidence and close

Read each real ledger into one Buffer exactly once. On each fixed snapshot prove initial scan, unchanged resume,
source-ref uniqueness, byte watermark/hash, direct reducer acceptance, and reverse-order deterministic receipt. Print
counts only. Fresh Sol review then marks 2a2a.3 complete and starts 2a2a.4.
