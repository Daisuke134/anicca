# CFO-2a2a.3 — Local Usage Source Cursor Plan

Status: READY

## Goal

Read each append-only local usage ledger exactly once, derive stable source-row refs from byte offsets, and expose
truncation, rewrite, malformed-row, and partial-tail coverage without losing the last trusted state.

## Ponytail gate

- Add exactly `apps/life-call/lib/cfo-local-agent-usage-source.js` and its `.test.js`.
- Reuse Node `crypto`, the existing strict/freeze helper, and the 2a2a source-ref formula.
- Add no dependency, filesystem watcher, scheduler, database, OTel exporter, retry loop, or business mapping.
- Soft target: production 50 LOC, tests 45 LOC, total <=95 additions. Stop and re-plan before 100.

## Task 1 — RED

Test one pure `scanLocalAgentUsageSource(data, options)` contract:

1. initial scan of two complete real-shaped JSONL rows emits exactly
   `{pairs, state, coverage_exceptions}`; `state` has only
   `{source_id, byte_offset, prefix_sha256, discovered_rows}` and each pair is exactly
   `{input, context:{source_row_ref}}`;
2. the first row contains multibyte UTF-8; literal expected hashes and the second row's literal byte offset/ref prove
   offsets and prefix hashing use bytes, not JavaScript character indices;
3. rescanning unchanged bytes emits zero pairs; appending one complete row emits only that row;
4. a shorter file or changed trusted prefix emits zero pairs, returns prior state unchanged, and reports
   `source_truncated` or `source_rewritten`;
5. complete rows before a partial tail advance safely and report `incomplete_tail`; a valid complete row followed by
   a malformed complete row atomically returns `pairs=[]`, a cloned/frozen prior state unchanged, and
   `invalid_source_row` without freezing or mutating either input;
6. invalid source IDs, bytes, or prior states fail with `cfo_local_agent_source_invalid:<fixed_reason>` without echo.

Run the focused test and record the missing-module/export RED.

## Task 2 — GREEN

Implement the smallest synchronous pure scanner:

- accept a Buffer and exact plain `{source_id, prior_state}` options; source ID is exactly
  `life_manager_agent_usage|anicca_agent_usage`;
- prior state is null or exactly `{source_id, byte_offset, prefix_sha256, discovered_rows}`: source IDs match,
  offset/count are non-negative safe integers, offset is zero or immediately after LF, the 64-hex hash matches the
  trusted prefix, and discovered count matches its complete non-empty rows; semantic violations throw fixed
  `invalid_prior_state`, while only `data.length < byte_offset` returns `source_truncated`;
- verify length and SHA-256 of the previously trusted prefix before parsing new bytes;
- parse only newline-terminated non-empty rows from the prior offset;
- derive `source_row_ref = sha256("cfo-local-agent-row-v1\\0" + source_id + "\\0" + decimal_start_offset)`;
- return exactly `{pairs, state, coverage_exceptions}`; exceptions are unique lexicographically sorted values from
  `incomplete_tail|invalid_source_row|source_rewritten|source_truncated`; clone and deeply freeze output without
  freezing or mutating input;
- never expose file paths, line text, JSON content, or hashes in errors.

Malformed complete rows and rewrite/truncate are coverage receipts, not thrown input errors. Run focused, CFO, full,
syntax, `git diff --check`, and the 2-file/100-LOC gate.

## Task 3 — Real evidence and close

Read each actual local ledger into one Buffer snapshot exactly once. For each fixed snapshot, scan from null state,
resume unchanged, then feed emitted pairs to the completed reducer; also reverse the pair order for deterministic
receipt proof. Print counts only. Assert source/ref uniqueness, byte watermark/hash consistency, zero reread rows,
exact reducer counts, and no content/secret output. Fresh Sol review then closes 2a2a.3 before 2a2a.4 begins.
