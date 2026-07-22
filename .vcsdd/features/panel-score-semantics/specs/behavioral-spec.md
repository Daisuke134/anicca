# PANEL 8g Outcome Score Semantics — Behavioral Specification

## Scope and authority

This feature implements only §10 row 8g of `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md` and the score rules in §9.9. The canonical planning spec is read-only here. Existing canonical `/panel` authentication, Telegram Mini App exchange, browser device-code exchange, durable sessions, tenant isolation, connections, settings, and command behavior remain unchanged.

## Requirements

### REQ-001: Complete four-organ response
**EARS**: WHEN an authenticated panel session successfully requests `GET /api/panel/scores` THE SYSTEM SHALL return HTTP 200 with exactly `daily`, `physical`, `mental`, and `financial`, each with the closed field and type contract below.
**Edge Cases**:
- Unknown outcome kinds: exclude them and explain the excluded count without throwing.
- Missing source table: return HTTP 503 with exactly `{ "error": "score_data_unavailable", "reason": "source_table_unavailable" }`; the four-organ envelope is absent and UI shows a loading error, never insufficient data.
- Source snapshot safety limit exceeded: return HTTP 503 with the same `error` and `reason=source_outcome_limit`; do not score a partial set.
- Timezone period cannot be resolved under REQ-002: return HTTP 503 with the same `error` and `reason=period_resolution_failed`; the four-organ envelope is absent and UI shows a loading error.
**Acceptance Criteria**:
- The real authenticated endpoint, not a detached calculator, satisfies the closed response schema.
- Existing request-supplied UID values never affect the session UID scope.

#### Closed successful-organ schema

- `status`: exactly `measured`, `insufficient_data`, or `invalid_data`.
- `value`: integer `0..100` only for `measured`; `null` otherwise.
- `period`: exactly `{ kind, start_at, end_at }`, with `kind` one of `rolling_7_days`, `rolling_30_days`, `calendar_month` and timestamps as UTC ISO-8601 strings.
- `numerator`, `denominator`: non-negative safe integers for `measured`; exactly `0,0` for `insufficient_data`; exactly `null,null` for `invalid_data`.
- `reason`: non-empty human-readable string without raw JSON or internal/provider identifiers.
- `source_outcome_ids`: unique strings shaped `outcome:<uuid>`, lexicographically sorted. Membership is every deduplicated supported row reflected in numerator, denominator, or a displayed component; unknown/invalid/cross-tenant rows are excluded.
- `components`: a JSON object with common `timezone` (non-empty string) and `excluded_unknown_count` (non-negative safe integer), plus exactly:
  - DAILY: `eligible_events`, `resolved_events`, `required_succeeded`, `required_failed`, `required_pending`, `context_unnecessary`, `optional_ignored`; every value is a non-negative safe integer and never null.
  - PHYSICAL: `detected_needs`, `confirmed_booking`, `confirmed_completion`, `unresolved_needs`, `search_candidate_unconfirmed`; every value is a non-negative safe integer and never null.
  - MENTAL: `deduplicated_triggers`, `delivered_within_cap`, `suppression_honored`, `correction_persisted`, `cap_overflow`, `unresolved_triggers`; every value is a non-negative safe integer and never null.
  - FINANCIAL: `currency` is an uppercase three-letter string for one valid currency or `null`; `gross_income_minor`, `realized_loss_minor`, `fee_minor`, and `user_transfer_minor` are non-negative safe integers for `measured`/`insufficient_data` and exactly null for `invalid_data`; `excluded_rows` is always a non-negative safe integer; `net_clamped` is always boolean.

### REQ-002: User-timezone half-open periods
**EARS**: WHEN scores are computed THE SYSTEM SHALL derive period boundaries from the authenticated user's configured IANA timezone and include source rows only in the half-open interval `[start_at,end_at)`.
**Edge Cases**:
- DAILY and MENTAL: the preceding seven local wall-clock days ending at the evaluation instant.
- PHYSICAL: the preceding thirty local wall-clock days ending at the evaluation instant.
- FINANCIAL: local calendar-month start through the evaluation instant.
- Invalid configured timezone: use UTC and state the effective timezone in `components`.
- DST spring-forward, DST fall-back, month boundary, a row exactly at `start_at`, and a row exactly at `end_at`.
- For a target local wall time that occurs twice, choose the earlier instant. For a nonexistent local wall time, add the exact offset gap while preserving minutes/seconds: New York `2026-03-08 02:30` resolves to `2026-03-08 03:30` (`2026-03-08T07:30:00.000Z`), not `03:00`; New York repeated `2026-11-01 01:30` selects `2026-11-01T05:30:00.000Z`. Fail period construction with the exact REQ-001 `period_resolution_failed` response if overlap/gap resolution cannot be established within 180 minutes.
**Acceptance Criteria**:
- `start_at` is inclusive and `end_at` is exclusive in both query filters and pure aggregation.
- Period calculations are deterministic for a supplied clock.

### REQ-003: DAILY event outcomes
**EARS**: WHEN DAILY outcomes occur inside the rolling seven-day period THE SYSTEM SHALL count one denominator unit per deduplicated event that needs any travel, call, or late handling, and one numerator unit only when every required handling for that event is succeeded or proven unnecessary by context.
**Edge Cases**:
- Multiple handling facts, retries, API rows, call rows, notifications, and duplicate source rows for one event never create extra denominator or numerator units.
- Optional or not-applicable handling never blocks success and never creates a denominator by itself.
- Mixed required/optional handling and context-proven-unnecessary handling.
- A required handling that is pending, failed, or unconfirmed keeps the event out of the numerator.
**Acceptance Criteria**:
- After REQ-008 winner selection, an event enters the denominator iff at least one handling winner is `required_succeeded`, `required_failed`, `required_pending`, or `context_unnecessary`; `optional` alone is ineligible. An eligible event enters the numerator iff every non-optional handling winner is `required_succeeded` or `context_unnecessary`.
- Reason/components state resolved events over eligible events and explain required handling states.

### REQ-004: PHYSICAL need outcomes
**EARS**: WHEN PHYSICAL outcomes occur inside the rolling thirty-day period THE SYSTEM SHALL count one denominator unit per deduplicated detected overdue need and one numerator unit only for a confirmed booking or confirmed completion.
**Edge Cases**:
- Search, candidate display, unconfirmed request, retry, and duplicate rows never add numerator units.
- Multiple resolution rows for one need count once, with confirmed completion or booking taking precedence.
**Acceptance Criteria**:
- Reason/components distinguish confirmed resolutions from unresolved detected needs.

### REQ-005: MENTAL trigger outcomes
**EARS**: WHEN MENTAL outcomes occur inside the rolling seven-day period THE SYSTEM SHALL count one denominator unit per deduplicated context trigger and one numerator unit when the trigger has a valid intervention delivered within the three-per-local-day delivery cap, correctly honored suppression with zero send, or a user correction persisted to context.
**Edge Cases**:
- Duplicate trigger rows count once.
- Only the first three otherwise-valid deliveries per local delivery day may add points; cap overflow does not. A delivery `resolved_at` is valid only when it is a parseable instant, is greater than or equal to `occurred_at`, and is strictly before the score period `end_at`. If `resolved_at` is absent/null, delivery day/order use `occurred_at`. If a present value is invalid, before `occurred_at`, or at/after `end_at`, that trigger remains in the denominator but cannot add a point and is counted unresolved. Valid deliveries order by effective delivery instant ascending, then `public_ref` lexicographically ascending.
- Suppression with any send is not honored.
- Correction without durable context persistence does not add points.
**Acceptance Criteria**:
- Reason/components show delivered-within-cap, suppression-honored, correction-persisted, overflow, and unresolved counts.

### REQ-006: FINANCIAL verified net outcome
**EARS**: WHEN FINANCIAL outcomes occur in the user's current calendar month THE SYSTEM SHALL sum verified external gross income into the denominator and compute the numerator in the same minor currency unit as `max(0, gross - realized loss - fee)`.
**Edge Cases**:
- Confirmed user transfers are displayed separately in reason/components and are not subtracted from the numerator.
- Self-funding, deposits, internal wallet moves, and unverified amounts count as neither gross nor user transfer.
- Duplicate transaction outcomes count once.
- A negative pre-clamp net returns numerator zero.
- More than one currency among otherwise eligible monthly financial rows returns exact `invalid_data` with null value/numerator/denominator, null currency, per-currency diagnostics only in private logs, and the plain reason `Financial outcomes use more than one currency.`
- Any per-row amount or aggregate outside JavaScript's non-negative safe-integer range returns exact `invalid_data` with the plain reason `Financial outcome amount is outside the supported range.`
**Acceptance Criteria**:
- Reason/components show currency, gross, realized loss, fee, user transfer, excluded amount counts, and the clamp when applied.

### REQ-007: Ratio and exact non-measured states
**EARS**: WHEN a valid denominator is positive THE SYSTEM SHALL set `status=measured` and `value` to `round(numerator / denominator * 100)` clamped to `0..100`; WHEN no eligible denominator exists THE SYSTEM SHALL return exactly `status=insufficient_data`, `value=null`, `numerator=0`, and `denominator=0`; WHEN typed source data cannot be combined safely THE SYSTEM SHALL return exactly `status=invalid_data`, `value=null`, `numerator=null`, and `denominator=null` with a specific reason.
**Edge Cases**:
- No production fixture, fallback percentage, activity count, or magic number may replace missing outcomes.
**Acceptance Criteria**:
- All four organs cover success, partial, and denominator-zero cases in the fixed matrix.

### REQ-008: Outcome ledger and inflation resistance
**EARS**: WHEN source outcomes are persisted THE SYSTEM SHALL append an immutable semantic revision retaining tenant, organ, stable entity key, typed outcome kind/status, occurred/resolved/recorded timestamps, optional minor-unit amount/currency, structured components, and an opaque browser-safe reference under a database uniqueness contract that prevents same-status retries from inflating scores.
**Edge Cases**:
- Production rows are source outcomes; request/activity/log counts are not score outcomes.
- Test fixture IDs, Dais-specific values, and production magic numbers are prohibited in production code or migrations.
- Financial `amount_minor` is an integer in `0..9007199254740991`; aggregation uses integer-safe arithmetic and fails to `invalid_data` before JSON number conversion if the sum exceeds that limit.
- Same-status retries are unique on `(uid, organ, entity_key, outcome_kind, outcome_status)`. A legitimate state transition appends a different-status revision; UPDATE/DELETE are rejected. DAILY selects the greatest `recorded_at`, then lexicographically greatest `public_ref`, per event/handling kind. PHYSICAL selects one need revision by `confirmed_completion > confirmed_booking > all other states`, then greatest `recorded_at`, then greatest `public_ref`. MENTAL and FINANCIAL select one trigger/transaction revision per entity by greatest `recorded_at`, then greatest `public_ref`. These exact semantic winners alone drive components and source references.
**Acceptance Criteria**:
- The additive migration has explicit checks, uniqueness, indexes, RLS, and no anon/authenticated table grants.
- Raw internal database IDs or source-provider IDs are not exposed to the browser.

### REQ-009: Tenant isolation and read-only behavior
**EARS**: WHEN scores are requested THE SYSTEM SHALL obtain all four organ row sets through one read-only database RPC transaction bound to the authenticated session UID and four specific periods, and SHALL perform zero database mutation, provider call, notification, call, email, post, wallet action, or other-tenant effect.
**Edge Cases**:
- Cross-tenant rows sharing entity keys or timestamps are ignored.
- PostgreSQL statement-snapshot semantics define membership: rows visible when the single RPC statement begins are eligible; concurrent commits after that snapshot are excluded. The RPC returns either every eligible row or an overflow marker, never a paginated partial set.
- Forged, stale, replayed, logged-out, or path-invalid sessions preserve all existing zero-mutation auth behavior.
**Acceptance Criteria**:
- Integration tests inspect every score query for `uid=eq.<session uid>`, `organ=eq.<organ>`, inclusive start, and exclusive end.

### REQ-010: Human-readable score cards
**EARS**: WHEN the panel renders score data THE SYSTEM SHALL render four organ cards with measured percentage or visible `insufficient data`, the period, numerator/denominator, plain-language reason, and meaningful components rather than an unexplained color or bare percentage.
**Edge Cases**:
- A well-formed `insufficient_data` organ renders insufficient data. Missing/malformed organ data marks the score section as a load error without `NaN`, raw JSON, internal identifiers, stack traces, or secrets.
- Mobile and desktop layouts remain readable and preserve existing panel controls.
**Acceptance Criteria**:
- MENTAL is present in both API and UI.
- The old `score/no_data/calls/answered/ledger_entries` activity-count contract is removed from score rendering.

### REQ-011: Deterministic fixed-dataset evaluation
**EARS**: WHEN the fixed score evaluation command runs THE SYSTEM SHALL execute a closed fixture matrix and report 100% only if every required semantic case passes.
**Edge Cases**:
- Matrix covers all four organs success/partial/zero, duplicate/retry inflation, DAILY mixed handling, PHYSICAL exclusions, MENTAL dedup/suppression/correction/cap/timestamp ties, FINANCIAL inclusions/exclusions/clamp/transfer/mixed-currency/safe-integer overflow, timezone/DST disambiguation/month/[start,end) edges, cross-tenant exclusion, unknown kinds, missing-table/period/source-limit 503s, concurrent snapshot membership, malformed UI payloads, and reason/source-linkage agreement.
**Acceptance Criteria**:
- The command is deterministic, network-free, provider-free, and has genuine RED then GREEN evidence.

### REQ-012: L2 regression preservation
**EARS**: WHEN implementation is ready for review THE SYSTEM SHALL pass the real score endpoint/query tests, focused panel/API/tenant tests, full Life Call tests, and all existing evals while preserving permanent panel authentication and controls.
**Acceptance Criteria**:
- A fresh artifact-only review blocks only material correctness, security, or release issues.

### REQ-013: Production L3 readback
**EARS**: WHEN the exact merged main commit is deployed successfully THE SYSTEM SHALL perform one read-only production L3 using Dais's already-valid permanent `/panel`, compare the four rendered cards and authenticated API against an independent tenant/period source-outcome recomputation, and record equality or fail closed.
**Edge Cases**:
- An organ with no outcomes visibly reports insufficient data rather than zero percent.
- No temporary panel URL, credential, raw PII, raw database row, secret, prompt, stack trace, or provider log is captured.
**Acceptance Criteria**:
- Desktop and mobile private screenshots show value/status and reasons.
- All prohibited side-effect counts are zero.
- Evidence JSON is mode 0600 and includes commands/counts, review, commits/PRs/deploy, per-organ recomputation, hashes, and zero-side-effect assertions.

## Purity boundary analysis

- **Pure core**: timezone-aware period construction, row normalization/deduplication, per-organ numerator/denominator aggregation, ratio state, reason/components, and privacy-safe source-reference selection. Inputs are explicit rows, timezone, and clock; outputs are deterministic values.
- **Effectful shell**: panel session validation, preference lookup, tenant/organ/period PostgREST reads, HTTP serialization, DOM rendering, migration application, deployment checks, authenticated browser readback, production database readback, screenshot capture, and evidence writing.
- The shell may supply facts to the core but may not derive scores from call/activity/log counts or mutate any source during score reads.

## Non-functional constraints

- Security: deny cross-tenant access; RLS on the source ledger; service-role-only database access; no browser exposure of raw internal/provider identifiers.
- Privacy: private production evidence only, mode 0600, no credentials or raw PII.
- Determinism: fixed clock, IANA timezone, stable ordering and dedupe precedence.
- Compatibility: CommonJS/Node conventions in `apps/life-call`; no changes to §9.11 copy or existing auth/control contracts.
- Performance: four bounded tenant/organ/period reads; no unbounded table scan; indexed UID/organ/time and UID/organ/entity paths.

## Reused external patterns

- PostgreSQL documents that a multi-column unique constraint makes the column combination unique, which supports retry-resistant `(uid, organ, entity_key, outcome_kind)` storage: https://www.postgresql.org/docs/current/ddl-constraints.html
- Existing public code uses `source_outcome_ids` as an explicit audit-linkage response field rather than substituting activity counts: https://github.com/Gonyak-cell/law-firm-os/blob/main/packages/dms/src/service.js
