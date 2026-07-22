# PANEL 8g Outcome Score Semantics — Verification Architecture

## Purity Boundary Map

- **Pure Core**: `apps/life-call/lib/panel-score-semantics.js`
  - `buildScorePeriods(nowMs, timeZone)` resolves timezone-aware half-open periods.
  - `computePanelScores(rowsByOrgan, periods, timeZone)` normalizes, deduplicates, aggregates, clamps, explains, and selects privacy-safe references.
  - No environment reads, network, database, filesystem, clock, random value, or mutation.
- **Effectful Query Shell**: `apps/life-call/lib/panel-api.js`
  - Authenticated session UID and explicit clock enter the shell.
  - Preferences supply the effective timezone.
  - One read-only `lm_panel_score_outcome_snapshot(p_uid, p_periods)` PostgREST RPC executes one SQL statement snapshot, scopes `WHERE uid = p_uid`, applies each organ's inclusive start/exclusive end, and returns all supported source columns grouped by organ.
  - The SQL function's fixed contract limit is 20,000 total eligible revisions. Its result is either the complete row set or `{overflow:true}`; it never returns a truncated array. Overflow fails HTTP 503 `source_outcome_limit`.
  - A missing source table fails HTTP 503 `source_table_unavailable`; it never becomes an empty organ.
  - Only selected typed columns enter the core. Score reads perform no write or provider call.
- **Persistence Shell**: `apps/life-call/migrations/2026-07-22-panel-score-outcomes.sql`
  - Additive normalized outcome ledger with RLS, service-role-only access, typed checks, retry-dedup uniqueness, and query indexes.
- **Presentation Shell**: `apps/life-call/lib/panel-ui.js`
  - Renders the closed API model into four human-readable cards; never recomputes score semantics.
- **Release/L3 Shell**: authenticated production browser/API readback, independent service-role database query and pure-core recomputation, private screenshots/evidence.

## Source Outcome Contract

The score source is `public.lm_score_outcomes`, not `lm_wake_log`, `lm_api_cost`, notification counts, retry rows, or other activity ledgers.

| Column | Contract |
|---|---|
| `id` | internal identity; never selected by the browser API |
| `public_ref` | opaque UUID, unique, browser-safe audit reference |
| `uid` | non-null tenant key |
| `organ` | `daily`, `physical`, `mental`, or `financial` |
| `entity_key` | stable tenant-local source entity key used for semantic dedupe |
| `outcome_kind` | typed handling/need/trigger/financial fact |
| `outcome_status` | typed semantic state interpreted by the pure core |
| `occurred_at` | source outcome time used for period inclusion |
| `resolved_at` | deterministic precedence/order time when applicable |
| `recorded_at` | database insertion time used for immutable snapshot/keyset traversal |
| `amount_minor` | financial-only integer in `0..9007199254740991`; sums use `BigInt` until safe JSON conversion |
| `currency` | uppercase three-letter currency for financial rows only |
| `components` | privacy-safe structured facts needed to validate the state |

Unique `(uid, organ, entity_key, outcome_kind, outcome_status)` prevents same-status retry persistence from creating extra score facts. State changes append immutable revisions; a database trigger rejects UPDATE/DELETE. The pure core applies REQ-008's organ-specific slot/winner rules: DAILY per entity/kind latest; PHYSICAL terminal confirmation precedence then latest; MENTAL and FINANCIAL per entity latest. Latest means greatest `recorded_at`, then lexicographically greatest `public_ref`. These rules are input-order invariant; `resolved_at` is used only for exact MENTAL delivery validation/order.

### Typed kinds and states

- DAILY kinds: `daily_travel`, `daily_call`, `daily_late`; states: `required_succeeded`, `required_failed`, `required_pending`, `context_unnecessary`, `optional`.
- PHYSICAL kind: `physical_need`; states: `detected`, `candidate`, `search`, `unconfirmed_request`, `confirmed_booking`, `confirmed_completion`, `unresolved`.
- MENTAL kind: `mental_trigger`; states: `delivered`, `suppression_honored`, `correction_persisted`, `cap_overflow`, `unresolved`. Delivered requires `components.intervention_valid=true`; suppression requires `components.send_count=0`; correction requires `components.context_persisted=true`.
- FINANCIAL kinds/states: `financial_external_income/verified`, `financial_realized_loss/realized`, `financial_fee/charged`, `financial_user_transfer/confirmed`, and `financial_self_funding|financial_deposit|financial_internal_move|financial_unverified/excluded`.

Rows with invalid kind/state pairings are rejected by migration checks. Multiple currencies or an aggregate over `9007199254740991` produce the exact REQ-006/007 `invalid_data` payload and never a percentage.

## Period Algorithm

- The shell supplies one fixed `nowMs`; all organ `end_at` values equal that instant.
- DAILY and MENTAL start at the same local wall-clock time seven local calendar days earlier.
- PHYSICAL starts at the same local wall-clock time thirty local calendar days earlier.
- FINANCIAL starts at local midnight on day one of the current calendar month.
- Local wall-clock parts are resolved with `Intl.DateTimeFormat(..., { timeZone }).formatToParts()`. Candidate instants are enumerated across observed offsets: an overlap selects the earlier instant; a gap adds the offset delta and preserves minute/second (`02:30 -> 03:30` for a one-hour gap); no resolution within 180 minutes produces HTTP 503 `period_resolution_failed`. Invalid timezones normalize to UTC.
- Query and core inclusion are both `occurred_at >= start_at && occurred_at < end_at`.

## Fixed Dataset Matrix

`apps/life-call/eval/score-semantics-cases.json` is the closed fixture source and `npm run eval:score` is the deterministic command. Fixture values are synthetic `.invalid`/opaque values and never enter production code.

| Group | Required cases |
|---|---|
| Envelope | four organs present; field/schema closure; privacy-safe refs |
| DAILY | success; partial; zero; mixed required/optional; context unnecessary; failed/pending; duplicate/retry/activity inflation |
| PHYSICAL | success; partial; zero; booking/completion; search/candidate/unconfirmed exclusion; duplicate precedence |
| MENTAL | success; partial; zero; trigger dedupe; valid delivery; suppression with zero send; invalid suppression with send; persisted correction; invalid correction; three/day cap; deterministic overflow exclusion |
| FINANCIAL | success; partial/net; zero; verified external; self/deposit/internal/unverified exclusion; realized loss; fee; confirmed transfer separate; duplicate; negative-net clamp; mixed-currency invalid; per-row and aggregate safe-integer boundaries |
| Time | valid/invalid timezone; New York spring gap shift; New York fall overlap earlier-instant selection; calendar-month boundary; exact start included; exact end excluded |
| Failure/schema | unknown kind exclusion; missing-table 503; period-resolution 503; pagination sentinel/limit 503; malformed organ UI load error |
| Snapshot/query | immutable revision winner direction; null/invalid MENTAL resolved times; one-RPC statement snapshot includes pre-snapshot commits, excludes later commits, and returns complete-or-overflow |
| Security/audit | cross-tenant row excluded; reason/components match numerator/denominator; lexically ordered contributing privacy-safe refs only |

## L2 Integration Strategy

- `apps/life-call/lib/panel-score-semantics.test.js`: fixed and bounded property tests for the pure core.
- `apps/life-call/lib/panel-api-score-semantics.test.js`: real `handlePanelApi` session/query path, closed response, four tenant/organ/time filters, cross-tenant resistance, no mutation.
- The endpoint suite exercises exact RPC arguments/scope, a 20,000-row complete marker, a 20,001-row overflow marker, and a transaction-snapshot concurrency fixture without allocating production-sized payloads in one response.
- `apps/life-call/lib/panel-ui.test.js`: four-card rendering contract, insufficient-data copy, reasons/components, mobile layout, legacy activity-score removal.
- `apps/life-call/lib/panel-score-migration.test.js`: static migration contract for checks, uniqueness, RLS, grants, and indexes.
- Focused regression: panel API/UI/auth/control plus `test/tenant-isolation.test.js`.
- Full regression: `npm test`.
- Existing + score evals: `npm run eval`, including `npm run eval:score`.

## Proof Obligations

| ID | Description | Tier | Required | Tool / artifact |
|---|---|---:|:---:|---|
| PROP-001 | Across count pairs `0..256`, safe-integer boundary pairs, and 10,000 seeded generated safe pairs, denominator zero has the exact insufficient state; otherwise integer-safe ratio output is rounded/clamped and `0 <= numerator <= denominator` for non-financial organs. | 1 | true | bounded property Node harness in `verification/proof-harnesses/ratio-invariants.js` |
| PROP-002 | For 500 seeded row sets (seed `0x8A17C0DE`), each containing 1..7 entities and 1..4 revisions drawn across every organ kind/state with timestamp/public-ref ties, baseline output is invariant under reverse, rotate, and 21 seeded Fisher-Yates permutations; fixed literal fixtures independently establish the expected winner/output. | 1 | true | 12,000-case bounded permutation harness in `verification/proof-harnesses/dedup-invariants.js` |
| PROP-003 | Period calculation and inclusion preserve `[start,end)` across UTC, invalid timezone fallback, DST spring/fall, and month edges. | 1 | true | boundary harness in `verification/proof-harnesses/period-invariants.js` |
| PROP-004 | The browser score endpoint is GET-only; its sole database outcome request is the read-only snapshot RPC with the authenticated tenant and all four exact periods, and the SQL function scopes every row by `uid` and period without mutation. | 1 | true | endpoint/RPC/migration integration tests plus captured security result |
| PROP-005 | The migration enforces typed outcome rows, retry uniqueness, RLS, service-only grants, and bounded query indexes. | 1 | true | migration contract test and production postflight readback |
| PROP-006 | Rendered reason/components/source references agree with the core numerator/denominator without raw internal/provider identifiers. | 1 | true | fixed matrix + UI semantic assertions + L3 equality |

## Formal Hardening Strategy

### Tier 0

- Existing permanent panel auth/session/control behavior is regression-tested without modification.
- DOM CSS/layout details remain under focused semantic tests and production screenshots.

### Tier 1

- Run all six required obligations with deterministic bounded Node harnesses and fixed clocks.
- Capture commands, counts, exit codes, and SHA-256 under `verification/` after entering Phase 5.
- Run project-appropriate source/migration secret and unsafe-identifier scans; capture raw result under `verification/security-results/`.

### Tier 2/3

- No cryptographic primitive or unbounded financial transfer logic is introduced. Tier 2/3 tools are not required; production database postflight and L3 equality remain mandatory release evidence.

## Production L3 Verification

1. Confirm origin/main exact SHA, Railway deployment exact SHA/SUCCESS, and health HTTP 200.
2. Reuse an already-valid safe authenticated Dais `/panel`; never create a temporary URL or print auth material.
3. Read the authenticated score API and four rendered cards once.
4. Query only `lm_score_outcomes` rows for the same Dais UID and the four exact periods through a service-role environment supplied outside argv/stdout.
5. Recompute with `apps/life-call/scripts/independent-panel-score-readback.js`, a spec-derived oracle that must not import `panel-score-semantics.js`, `panel-api.js`, or any production scorer helper. Its own contract tests run the closed fixture matrix against literal expected results, and a source scan enforces the import ban. Compare its aggregates/references to API and UI; record only aggregates and opaque refs.
6. Capture desktop/mobile private screenshots and record side-effect counters/deltas as zero.
7. Write mode-0600 `/Users/anicca/.codex/evidence/panel-8g-score-semantics-production-l3.json`, hash it and screenshots, then remove temporary profiles/runners/logs containing auth material.

## Review Gate

Fresh `gpt-5.6-sol` contexts receive only manifests and paths on disk. They may block for material semantic, tenant/security, migration, regression, or release-evidence defects. Cosmetic observations are recorded without expanding §10 row 8g.
