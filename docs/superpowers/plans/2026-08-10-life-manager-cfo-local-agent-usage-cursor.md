# CFO-2a2a.3 — Append-only Local Usage Cursor Plan

Status: COMPLETE

## Goal

Read only newly appended complete JSONL rows while proving the previously accepted prefix has not been truncated or
rewritten. A source defect returns coverage evidence and preserves the previous committed state.

## Ponytail gate

- Add only `apps/life-call/lib/cfo-local-agent-usage-cursor.js` and its `.test.js`.
- Reuse Node Buffer/crypto, the shared exact/freeze helpers, and `normalizeLocalAgentUsageEvent`.
- Add no watcher, launchd job, filesystem writer, database, migration, scheduler, price logic, OTel, retry loop, or
  external dependency.
- Soft target: production 65 LOC, tests 35 LOC, total <=100 additions. Stop and re-plan before 100.

## Task 1 — RED

Add compact contracts for `scanLocalAgentUsageAppend`:

1. initial Buffer with two valid newline-terminated rows returns two pairs with exact source refs derived from byte
   offsets, one frozen state at EOF, and no coverage exception. The first row contains multibyte UTF-8; the second
   ref is calculated from the raw Buffer's first LF index plus one, so a character-offset implementation fails;
2. rescanning unchanged bytes from that state returns zero pairs and the identical state;
3. an append returns only the new row; a partial tail returns preceding complete rows, stops before the tail, and
   emits `partial_tail`;
4. prior-size shrink and committed-prefix rewrite return no pairs, preserve the exact prior state, and emit their
   fixed exception;
5. malformed JSON and a separate well-formed/schema-invalid complete row are each transactional: zero pairs,
   unchanged prior state, exact `coverage_exceptions=["invalid_source_row"]`, and no hostile text in output/error;
6. invalid source/state/Buffer, unsafe offsets, sparse or extra state fields, Proxy input, and source mismatch throw
   only `cfo_local_agent_usage_cursor_invalid:<fixed_reason>`.

Record the expected missing-module RED.

## Task 2 — GREEN

Implement the smallest pure cursor:

- accept only the two fixed source IDs, a real Buffer, and null or one exact state;
- reject `types.isProxy(bytes)` before `Buffer.isBuffer`, `.length`, or `.subarray` is accessed;
- use initial state `{schema_version:1, source_id, byte_offset:0,
  prefix_sha256:sha256(empty), observed_file_size:0}`;
- validate non-negative safe integer sizes, `byte_offset <= observed_file_size`, exact source match, and lowercase
  64-hex prefix hash;
- define `byte_offset` as the byte after the last accepted LF, `prefix_sha256` as SHA-256 of exactly
  `bytes.subarray(0, byte_offset)`, and `observed_file_size` as the whole snapshot length including partial tail;
- treat null as the fixed empty effective prior state; on truncate/rewrite/invalid, return a new frozen state equal in
  value to that prior state without mutating or freezing the caller's state object;
- before scanning, classify `bytes.length < previous.observed_file_size` as `source_truncated`, then compare SHA-256
  of `bytes.subarray(0, byte_offset)` for `source_rewritten`;
- scan only byte indexes from `byte_offset`; a newline ends a complete row and the next byte is the next offset;
- derive `source_row_ref = sha256("cfo-local-agent-row-v1\0" + sourceId + "\0" + decimal start offset)`;
- parse and validate every complete new row with `normalizeLocalAgentUsageEvent(input,
  {source_row_ref, financial_unit_id:null})` before returning its pair;
- if any complete row is invalid, discard every pair from this call and return the unchanged prior state;
- otherwise advance state only through the last newline, set `observed_file_size=bytes.length`, and emit
  `partial_tail` iff bytes remain;
- deep-freeze the exact three-key result and keep every error/exception content-free.

Evaluate source defects in this order: truncate, rewrite, invalid complete row, partial tail. These return exactly one
nonthrowing fixed `coverage_exceptions` value. Only invalid arguments throw the cursor error prefix.

Run focused tests, syntax, `git diff --check`, and the 2-file/100-LOC gate.

## Task 3 — Real evidence and close

Read both real ledgers into memory without modifying them. For each source, prove:

- initial scan pairs equal the count of complete JSONL rows; call `reduceLocalAgentUsageEvents(scan.pairs)` directly
  and assert `receipt.counts.discovered_rows === scan.pairs.length === completeRowCount` without token mismatch;
- unchanged rescan returns zero pairs;
- in-memory append returns exactly one synthetic row;
- in-memory truncation, rewrite, partial tail, and invalid complete row return exact exception/state behavior;
- result, state, pairs, contexts, and normalized nested values are deeply frozen;
- stdout contains only counts and the four fixed exception names, never rows, paths, prompts, responses, accounts, or
  credentials.

Fresh Sol review checks correctness, byte identity, state atomicity, privacy, and YAGNI. Sol independently reruns focused,
CFO, full, syntax, diff, and real read-only E2E, then updates specs, commits, pushes, and starts 2a2a.4.

## Completion evidence

- RED: missing module; GREEN: focused cursor tests 5/5.
- Scope: 2 new files, 78 total added lines, no dependency or runtime change.
- Gates: syntax, whitespace, CFO suite, and full `npm test` exit 0; fresh Sol review `ship`.
- Real read-only E2E: Life Manager 1,102/1,102 and Anicca 3,847/3,847 complete/discovered rows;
  unchanged rescans returned 0 and in-memory appends returned 1 for both sources.
- Coverage remains truthful: 12 and 261 missing-usage rows plus 6 and 430 runner-ID collision groups were preserved;
  truncate, rewrite, invalid-row, and partial-tail probes returned only their fixed exception names.
