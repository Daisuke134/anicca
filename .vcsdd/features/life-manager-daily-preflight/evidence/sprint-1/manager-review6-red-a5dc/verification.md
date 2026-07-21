# Fresh verification commands and outcomes

All commands run from the repository root unless a command includes `cd apps/life-call`.

## Entry gate

| Command | Exit | Outcome |
|---|---:|---|
| `git fetch` + `git rev-parse HEAD '@{upstream}'` + `git status --porcelain=v1` | 0 | clean; both SHAs `a5dc8df8b23776e1a2877a30bbcb32e7cfeae4dc` |
| full seven-file manager bundle recorded in prior verification | 0 | 137 tests, 137 pass, 0 fail |
| recorded old name selection | 0 | 75 tests, 75 pass, 0 fail |
| focused collector/production/provenance/mail command | 0 | 52 tests, 52 pass, 0 fail |
| `cd apps/life-call && npm test` | 0 | aggregate 372 tests, 372 pass, 0 fail |
| `cd apps/life-call && npm run eval` | 0 | calendar 21/21; late 12/12; total 33/33 |
| recorded four-module coverage command | 0 | 147/147; module lines/functions `92.68/96.00`, `90.08/90.91`, `99.06/100.00`, `95.40/100.00` |
| installed state validator | 0 | `verify-vcsdd-state: OK` |
| installed runtime validator | 0 | `verify-vcsdd-runtime: OK` |
| `verify-phase2-process.mjs schemas ...` | 0 | PASS |
| `verify-phase2-process.mjs trace ...` | 0 | PASS |
| recorded tracked `scope` | 1 | reproduced |
| recorded tracked `coverage` | 1 | reproduced |
| recorded tracked controlled-L3 gate | 1 | reproduced without running controlled L3 |

## RED suite

Command:

```text
node --test --test-concurrency=1 apps/life-call/lib/daily-preflight-final-schema.test.js apps/life-call/lib/daily-preflight-poll-boundaries.test.js apps/life-call/lib/daily-preflight-provenance.test.js apps/life-call/lib/daily-preflight-purity-contract.test.js apps/life-call/lib/transport/mail-gog-receipt.test.js apps/life-call/lib/daily-preflight-abort-lineage.test.js .vcsdd/features/life-manager-daily-preflight/tests/verifier-contracts.test.mjs
```

Exit `1`: `142 total / 136 pass / 6 fail / 0 skipped`.

Exact failing names:

1. `review6 RED: tracked closure binds the implementation tree and permits only descendant evidence commits`
2. `review6 RED: serialized validation requires explicit same-invocation provenance in current and fresh processes`
3. `review6 RED: deadline harness preserves non-cooperative timer semantics after abort`
4. `review6 RED: receipt boundary: one millisecond before the actual send is rejected without rewriting sentAtMs`
5. `review6 RED: schema discovery honors an explicitly injected installed plugin root`
6. `review6 RED: architecture-approved recursive privacy scope succeeds and reports its measured path count`

Each failure is an assertion failure against reviewed runtime behavior, not a syntax/load error.

## Corrected false test contracts

- Before: `manager RED: receipt: one-millisecond stale remains stale through the runtime harness`. It compared against the harness-rewritten timestamp. After: the review6 receipt name above observes the actual send with a test clock seam and expects the actual-send-minus-1ms receipt to fail.
- Before: the six existing `timeout:` / `deadline:` tests used a non-cooperative timer and depended on harness deletion. After: the same six stable names use an abort listener, clear their own timer, reject from the signal, and pass `6/6`. A separate review6 RED proves test support still deletes a genuinely non-cooperative timer.

## Fresh controls after RED

| Command | Exit | Outcome |
|---|---:|---|
| old selection | 0 | 75/75 |
| focused selection | 0 | 52/52 |
| `npm test` | 0 | 372/372 |
| `npm run eval` | 0 | 33/33 |
| corrected signal-aware timeout/deadline selection | 0 | 6/6 |
| installed state/runtime validators | 0/0 | PASS/PASS |
| schema/trace validators | 0/0 | PASS/PASS |
| official new finding schema + reciprocal-link audit | 0 | 101 GREEN, 6 RED, 11 RESOLVED, 6 OPEN, links PASS |
| exact production/verifier/test-support diff from `a5dc8df8b...` | 0 | no diff |
| approved recursive privacy command | 1 | reproduced; no matched content printed |

The recursive scan's relevant failing paths are recorded separately. Its top-level command emits only `verification failed`; no secret or PII match content is written to evidence.
