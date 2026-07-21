# Verification Architecture: Life Manager Daily Preflight

## Verification strategy

The proof architecture separates deterministic logic (L1), fixed decision/eval behavior (L2), and real controlled production effects (L3). No layer substitutes for another. Phase 1 defines future tests and evidence contracts only; it does not claim RED, GREEN, provider execution, or proof completion.

The production source snapshot under review is the `apps/life-call/` tree at `58846034b4505f585bd8b4ea3fbcaa04c38e31bc`. Every Phase 2 command must first pass `git diff --exit-code 58846034b4505f585bd8b4ea3fbcaa04c38e31bc -- apps/life-call` and record `git rev-parse HEAD` plus `git rev-parse 58846034b4505f585bd8b4ea3fbcaa04c38e31bc:apps/life-call` in `.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/source-snapshot.txt`. Any intended production change after RED must record its new commit and tree hash in the same file; output without that binding is inadmissible.

## Purity boundary map

| Boundary | Allowed inputs | Allowed outputs | Forbidden |
|---|---|---|---|
| Pure receipt parser | provider date string | finite closed interval or `null` | environment, network, caller precision assertions |
| Pure email validator | owned identities, provider/message IDs, exact nonce equality, send/now instants, parser-derived bounds | typed internal observation or closed failure enum | raw provider payload serialization, inferred dates |
| Pure Telegram validator | IDs/times, exact webhook facts, required updates, backlog samples | typed internal observation or closed failure enum | raw token/chat/message text |
| Final serializer | validated nine-dependency success and internal observations | only the closed REQ-013 success schema | arbitrary strings, raw classifications, failure diagnostics, unknown keys |
| Failure diagnostic channel | fixed dependency enum, UTC time, closed safe failure enum | non-final ephemeral diagnostic | success artifact write, raw provider data, arbitrary strings |
| Production shell | fixed env-derived clients and identities | curated observations | injected collectors/transports/proofs/test doubles |
| Test shell | deterministic fakes and fixtures | assertions only | accidental real provider fallback |

## L1 deterministic proof obligations

### PROP-001 — Nine-dependency closure (Tier 1, required)

Property tests shall prove exact dependency membership, order-independent aggregation, timeout/missing/failure closure, and PASS iff all nine current-run results pass. Traces: REQ-001, REQ-002, REQ-014, REQ-015.

### PROP-002 — Minute interval boundaries (Tier 1, required)

Boundary tests shall cover minute start, `+59,999`, send inside the same minute, send immediately before the next-minute bucket, next-minute lower bound, previous minute, and intervals wholly before send. Traces: REQ-007, REQ-010, REQ-017.

### PROP-003 — Exact timestamps and impossible dates (Tier 1, required)

Table tests shall cover exact millisecond equality, one millisecond before/after send, `Z`, positive/negative offsets, leap-day validity, invalid month/day/hour/minute/second, and unknown formats. Traces: REQ-008, REQ-009.

### PROP-004 — Freshness invariants (Tier 1, required)

Boundary tests shall cover send/receipt at exactly the 15-minute limit, one millisecond stale, future send, future lower bound, current-minute upper bound beyond now, reversed/missing/NaN/infinite bounds. Traces: REQ-002, REQ-010.

### PROP-005 — Exact correlation and ownership (Tier 1, required)

Tests shall independently mutate recipient, receive identity, allowlist, provider ID, message ID, nonce, received nonce, Telegram peer/reply ordering, webhook URL, allowed updates, error state, and backlog final count; each mutation must fail closed. Traces: REQ-003, REQ-004, REQ-005.

### PROP-006 — Poll boundaries, one-shot budgets, and no phone (Tier 1, required)

Future RED boundary tests shall prove: Telegram reply attempts `1..6`, delay `2,000 ms`, and no attempt 7; Telegram webhook attempts `1..3`, delay `2,000 ms`, and no attempt 4; email inbox attempts `1..6`, delay `3,000 ms`, and no attempt 7. Separate cases shall prove the final allowed attempt can succeed, the first disallowed attempt never occurs, timeout after an authorized send terminates, Telegram/email send counts remain exactly one, and phone calls remain zero.

Every Telegram Bot API, sidecar, Resend, and gog provider call shall have a 15,000 ms timeout. Hard deadlines shall be Telegram `179,000 ms`, email `120,000 ms`, and parallel controlled collection `179,000 ms`. Current production source implements attempt/delay bounds, 15,000 ms sidecar timeout, and 30,000 ms gog timeout, but lacks Bot API/Resend timeouts and hard collector deadlines. The exact Phase 2 RED cases are `bot API call times out at 15,000 ms after one Telegram send`, `Resend call times out at 15,000 ms without inbox polling`, `gog call is aborted at tightened 15,000 ms after one email send`, `Telegram collector stops at 179,000 ms`, `email collector stops at 120,000 ms`, and `parallel collector stops at 179,000 ms`, with zero duplicate sends. Traces: REQ-006, REQ-015.

### PROP-007 — Closed final schema and security closure (Tier 2, required)

The schema harness shall accept one exact 9/9 artifact and reject one fixture for each of these forbidden fields/classes: arbitrary string, raw classification, path, host, URL, provider response, provider error, provider ID, message ID, nonce, address, email, phone, location, subject, body, token, secret, credential, authorization data, unknown root key, unknown dependency key, unknown effects key, and nested unknown key. It shall also reject wrong schema/version/run/dependency/status enums, non-UTC timestamps, stale freshness intervals, invalid hashes, duplicate/missing dependencies, and out-of-range counts. Every object shall be closed. The failure-channel harness shall accept only its closed safe enum and prove that no failure field can be copied into a success artifact. Traces: REQ-013.

### PROP-008 — Production provenance and purity (Tier 2, required)

Static export/import assertions and executable wiring tests shall prove the public CLI rejects supplied proofs, production collection takes no injected collector/transport, parser-derived bounds originate only in the production parser, and test support cannot fall through to real executables/providers. Traces: REQ-011, REQ-012, REQ-017.

### PROP-009 — Historical immutability (Tier 2, required)

Pre/post SHA-256 and POSIX mode assertions shall prove both historical evidence files remain byte-identical and `0600`; staging review shall reject either file if included as modified. Traces: REQ-016.

### PROP-010 — Process-state honesty (Tier 2, required)

State/schema/runtime checks shall prove the iteration-1 FAIL was recorded at legal `currentPhase=1c` with `humanApproved=false`, then routed through atomic VCSDD state APIs to `1a`, corrected through legal `1a→1b`, and stopped at `currentPhase=1b` with `sprintCount=0`, the iteration-1 verdict preserved, no iteration-2 verdict, no later-phase gate, and the contract still `status: draft`. On the next review, the legal state is `currentPhase=1c` with the fresh adversary verdict recorded and `humanApproved=false`; `2a` remains blocked unless adversary PASS and explicit human/orchestrator PASS are both recorded. Traces: REQ-018.

## L2 proof obligations

### PROP-011 — Fixed eval regression (Tier 2, required)

The canonical fixed eval dataset shall run without provider access and retain exactly calendar `21/21` plus late `12/12`, total `33/33`. Any changed expected label requires a reviewed spec change. Traces: REQ-014, REQ-017.

## L3 proof obligations

### PROP-012 — Controlled production preflight (Tier 3, required)

Only after Phase 1c adversary PASS, explicit human/orchestrator PASS, and Phase 2 adjudication, one authorized controlled invocation shall prove all nine dependencies in one generated REQ-013 report, with Telegram send `1`, email send `1`, phone call `0`, exact same-run correlations, exact polling/deadline bounds, and no final artifact on any failure. No L3 action is authorized by this Phase 1 correction. Traces: REQ-001 through REQ-006, REQ-013 through REQ-015.

## Exact Phase 2 command matrix

All commands run from repository root with network/provider credentials absent except the separately authorized L3 command, and write only the named future evidence paths.

| Obligation | Exact executable command | Expected contract | Future evidence path |
|---|---|---|---|
| Source snapshot | `git diff --exit-code 58846034b4505f585bd8b4ea3fbcaa04c38e31bc -- apps/life-call && { git rev-parse HEAD; git rev-parse 58846034b4505f585bd8b4ea3fbcaa04c38e31bc:apps/life-call; } > .vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/source-snapshot.txt` | exit 0 before RED; exactly 2 hash lines | `evidence/sprint-1/source-snapshot.txt` |
| Focused L1 | `cd apps/life-call && node --test lib/transport/mail-gog-receipt.test.js lib/daily-preflight-collectors.test.js lib/daily-preflight-production-wiring.test.js lib/daily-preflight-provenance.test.js > ../../.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/focused.tap 2>&1` | exit 0; tests `51`, pass `51`, fail `0`, skipped `0` on bound baseline; future tests update the declared count before GREEN | `evidence/sprint-1/focused.tap` |
| Full regression | `cd apps/life-call && npm test > ../../.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/full-regression.log 2>&1` | exit 0; pass `371`, fail `0` on bound baseline | `evidence/sprint-1/full-regression.log` |
| Eval | `cd apps/life-call && npm run eval > ../../.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/eval.log 2>&1` | exit 0; calendar `21/21`, late `12/12`, total `33/33` | `evidence/sprint-1/eval.log` |
| Temporal boundary | `cd apps/life-call && node --test --test-name-pattern='minute-precision|next minute|previous minute|second/timezone|impossible exact calendar|same-minute interval|later minute interval|future, malformed|exact timestamps strictly|nonce mismatch and stale' lib/transport/mail-gog-receipt.test.js lib/daily-preflight-collectors.test.js > ../../.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/temporal-boundary.tap 2>&1` | exit 0; tests `10`, pass `10`, fail `0`, skipped `0` | `evidence/sprint-1/temporal-boundary.tap` |
| Poll/deadline boundary | `cd apps/life-call && node --test lib/daily-preflight-poll-boundaries.test.js > ../../.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/poll-boundary.tap 2>&1` | Phase 2 initial RED: exit 1 with the six named timeout/deadline gaps; GREEN: exit 0, tests `12`, pass `12`, fail `0`; send counts TG=`1`, email=`1`, phone=`0` | `evidence/sprint-1/poll-boundary.tap` |
| Final schema/security | `cd apps/life-call && node --test lib/daily-preflight-final-schema.test.js > ../../.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/final-schema.tap 2>&1` | Phase 2 initial RED; GREEN exit 0 with one positive and `36` negative cases, tests `37`, pass `37`, fail `0`; all forbidden classes and nested unknown key covered | `evidence/sprint-1/final-schema.tap` |
| Purity/provenance | `cd apps/life-call && node --test lib/daily-preflight-provenance.test.js > ../../.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/purity-provenance.tap 2>&1` | exit 0; tests `26`, pass `26`, fail `0`, skipped `0`; zero real-provider fallback and zero production injection path | `evidence/sprint-1/purity-provenance.tap` |
| Per-module coverage | `cd apps/life-call && rm -rf ../../.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/coverage-raw && mkdir -p ../../.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/coverage-raw/collectors ../../.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/coverage-raw/mail-gog && NODE_V8_COVERAGE=../../.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/coverage-raw/collectors node --test --experimental-test-coverage --test-coverage-lines=90 --test-coverage-functions=90 --test-coverage-include=lib/daily-preflight-collectors.js lib/daily-preflight-collectors.test.js lib/daily-preflight-production-wiring.test.js lib/daily-preflight-provenance.test.js > ../../.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/coverage-collectors.log 2>&1 && NODE_V8_COVERAGE=../../.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/coverage-raw/mail-gog node --test --experimental-test-coverage --test-coverage-lines=90 --test-coverage-functions=90 --test-coverage-include=lib/transport/mail-gog.js lib/transport/mail-gog-receipt.test.js > ../../.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/coverage-mail-gog.log 2>&1` | exit 0 only if each changed production module independently has lines `>=90.00%` and functions `>=90.00%`; combined average is inadmissible; V8 JSON exists in each raw directory | `evidence/sprint-1/coverage-*.log`, `evidence/sprint-1/coverage-raw/{collectors,mail-gog}/*.json` |
| Phase/process validation | `node /Users/anicca/.codex/plugins/cache/vcsdd-claude-code/vcsdd/1.0.0/scripts/verify-vcsdd-state.js > .vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/vcsdd-state.log 2>&1 && node /Users/anicca/.codex/plugins/cache/vcsdd-claude-code/vcsdd/1.0.0/scripts/verify-vcsdd-runtime.js > .vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/vcsdd-runtime.log 2>&1` | both exit 0 | `evidence/sprint-1/vcsdd-{state,runtime}.log` |

The future schema test count is `37`: one accepted canonical artifact plus 24 forbidden-field/class cases (including nested unknown), 8 type/enum/format/count cases, 3 dependency-set cases, and 1 failure-channel separation case. No test bead or RED/GREEN evidence is created during Phase 1.

## Coverage acceptance

Every changed production module is judged independently. `apps/life-call/lib/daily-preflight-collectors.js` and `apps/life-call/lib/transport/mail-gog.js` must each achieve at least `90.00%` line coverage and `90.00%` function coverage in its own exact include-filtered command. Branch coverage is recorded but is not a replacement for either required threshold. A combined average cannot mask a module below either threshold.

## RED/GREEN evidence contract for Phase 2

- Phase 2a creates `evidence/sprint-1-red-phase.log` only after entering `2a`; it records exact commands, exits, counts, bound source hashes, and the expected polling/schema RED failures while the full regression baseline remains PASS.
- Phase 2b/2c creates or refreshes `evidence/sprint-1-green-phase.log` after the respective legal transition and records focused/full/eval/boundary/schema/security/purity/coverage results from the bound snapshot.
- Existing external logs remain provenance only. No Phase 1 artifact claims RED/GREEN.
- A wrapper failure, missing future test file, stale output, or output from another source tree is inadmissible.

## Final Phase 1 checklist

- Iteration-1 verdict and FIND-001..004 remain byte-for-byte unchanged.
- Historical evidence JSON hashes are `6e69dd13086dfeb485ba1dd59e397b490ca187c072b153454603afbd92a455b4` and `a44cdc897eee741ac2ea6477b19e11c7e7281cbf7b240fd0723c1d63886243ac`, both mode `0600`.
- Current corrective stop is `currentPhase=1b`, `adversaryVerdict=FAIL` for iteration 1, `humanApproved=false`, `sprintCount=0`, contract `status: draft`, and no iteration-2 verdict.
- The next fresh review legally transitions to `currentPhase=1c`, records the iteration-2 adversary verdict there, retains `humanApproved=false` pending explicit approval, and cannot enter `2a` unless both strict gates PASS.
- State/runtime/artifact/contract schemas, Phase-1 REQ→PROP→CRIT traceability, `git diff --check`, safe secret/PII counts, staged scope, source snapshot, and historical hash/mode checks all pass before commit.
