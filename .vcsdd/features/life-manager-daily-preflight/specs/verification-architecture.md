# Verification Architecture: Life Manager Daily Preflight

## Verification strategy

The proof architecture separates deterministic logic (L1), fixed decision/eval behavior (L2), and real controlled production effects (L3). No layer substitutes for another. Phase 1 describes obligations only; it does not claim they are currently proved.

## Purity boundary map

| Boundary | Allowed inputs | Allowed outputs | Forbidden |
|---|---|---|---|
| Pure receipt parser | provider date string | finite closed interval or `null` | environment, network, caller precision assertions |
| Pure email validator | owned identities, provider/message IDs, exact nonce equality, send/now instants, parser-derived bounds | sanitized immutable proof or closed failure class | raw provider payload serialization, inferred dates |
| Pure Telegram validator | IDs/times, exact webhook facts, required updates, backlog samples | sanitized immutable proof or closed failure class | raw token/chat/message text |
| Preflight core | nine curated dependency results | deterministic overall result and sanitized report | historical PASS substitution |
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

### PROP-006 — One-shot budgets and no phone (Tier 1, required)

Success, rejection, timeout, malformed response, and polling exhaustion tests shall count calls and prove Telegram sends `<=1`, email sends `<=1`, phone calls `==0`, including failure paths. Traces: REQ-006, REQ-015.

### PROP-007 — Sanitizer and security closure (Tier 2, required)

Allowlist/denylist tests and scans shall prove reports/errors contain no raw nonce, address, provider/message ID, body, subject, provider response/error, token, secret, phone, location, URL, host, or path; safe references must be one-way hashes. Traces: REQ-013.

### PROP-008 — Production provenance and purity (Tier 2, required)

Static export/import assertions and executable wiring tests shall prove the public CLI rejects supplied proofs, production collection takes no injected collector/transport, parser-derived bounds originate only in the production parser, and test support cannot fall through to real executables/providers. Traces: REQ-011, REQ-012, REQ-017.

### PROP-009 — Historical immutability (Tier 2, required)

Pre/post SHA-256 and POSIX mode assertions shall prove both historical evidence files remain byte-identical and `0600`; staging review shall reject either file if included as modified. Traces: REQ-016.

### PROP-010 — Process-state honesty (Tier 2, required)

State/schema/runtime checks shall prove strict mode, legal `init→1a→1b` history, no 1c verdict/approval, no sprint start, no later-phase gate, and an unapproved draft contract. Traces: REQ-018.

## L2 proof obligations

### PROP-011 — Fixed eval regression (Tier 2, required)

The canonical fixed eval dataset shall run without provider access and retain its declared 33/33 expected decisions. Any changed expected label requires a reviewed spec change, not an implementation-only rewrite. Traces: REQ-014, REQ-017.

L2 does not adjudicate delivery. It verifies fixed decision behavior only; L3 remains required for current production truth.

## L3 proof obligations

### PROP-012 — Controlled production preflight (Tier 3, required)

After Phase 1c approval and Phase 2 adjudication, one authorized controlled invocation shall prove all nine dependencies in one generated report, with Telegram=1 send maximum, email=1 send maximum, phone=0, exact same-run correlations, and sanitized artifact output. It must stop without a success artifact on any failure. Traces: REQ-001 through REQ-006, REQ-013 through REQ-015.

No L3 action is authorized by this Phase 1 repair.

## RED/GREEN evidence contract for Phase 2

- Phase 2a must create a fresh `evidence/sprint-1-red-phase.log` after entering 2a.
- It must contain the VCSDD markers `new-feature-tests: FAIL` and `regression-baseline: PASS`, the exact command, exit code, test counts, and raw relevant failing output.
- Existing external logs may be investigated for provenance but are not copied, relabeled, touched, or accepted as Phase 2 evidence automatically.
- Phase 2b/2c must create/refresh `evidence/sprint-1-green-phase.log` after the respective phase transition with `target-feature-tests: PASS` and `regression-baseline: PASS`, exact commands/exits/counts, final focused/full/eval/boundary results, and post-refactor freshness.
- A command wrapper failure is not a product RED or GREEN result. Evidence must bind the test output to the intended source snapshot.

## Verification command classes

| Layer | Required class | Acceptance |
|---|---|---|
| L1 focused | receipt, collector, provenance, production-wiring, CLI tests | deterministic pass plus explicit boundary cases |
| L1 regression | full life-call suite | zero failures; count recorded |
| L2 | canonical eval | 33/33 |
| Boundary audit | fixed temporal/provenance assertions | 10/10 |
| Coverage | changed production modules | line/function threshold declared by contract |
| Security | secret/PII pattern scan and sanitizer tests | zero unsafe matches in staged artifacts; counts only |
| Purity | exports/imports/production wiring scan | no production injection path |
| Process | state schema, runtime verifier, contract schema, diff check | all exit 0 |

## Controlled side-effect budget

| Effect | Phase 1 budget | Future L3 maximum per authorized invocation |
|---|---:|---:|
| Telegram send | 0 | 1 |
| Email send | 0 | 1 |
| Phone call | 0 | 0 |
| Provider/inbox read | 0 | bounded as implementation contract |
| Production evidence write | 0 | 1 only after all gates and all-nine result |

## Final artifact review obligations

Before commit, review only the staged feature process artifacts and canonical spec diff; verify historical evidence hashes/modes again; validate state and contract schemas; run the installed runtime verifiers; run `git diff --check`; scan staged content for secrets/PII using safe counts without printing matched values; confirm no source/test/evidence JSON is staged; and confirm Phase 1c has no verdict or human approval.
