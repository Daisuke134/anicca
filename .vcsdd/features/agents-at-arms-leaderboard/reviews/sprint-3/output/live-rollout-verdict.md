# VCSDD Sprint-3 — LIVE PRODUCTION ROLLOUT Verdict (fresh-context adversary)

- Feature: `agents-at-arms-leaderboard` (lean)
- Scope: sprint-3 only (S3.1–S3.6). Sprint-1/2 spec+impl are NOT re-litigated; only new
  regressions / rollout-safety defects introduced by sprint-3 are in scope.
- Timestamp reviewed: 2026-07-04

## Test execution honesty
This session's tool list is **Read/Write/Edit/Grep/Glob only — no Bash tool is available to me**.
I could NOT execute `node --test` myself and could NOT re-run `verify-live-migration.mjs` against
production. Per HONESTY Rule 4, I am not claiming a fresh run. Instead I did a full statement-trace
of every assertion in `schema.additive.test.js` against `telemetry-schema.js`, and hand-traced
`verify-live-migration.mjs`'s logic against the live-row shape documented in the evidence log
(`.../evidence/sprint-3-live-rollout.log`). The evidence log's own claimed counts (76/76 unit tests,
S3.1–S3.6 all green) are taken as reported evidence, not independently re-executed by me this round.

## Overall verdict: **FAIL**

| Dimension | Verdict |
|---|---|
| Spec Fidelity | FAIL |
| Edge Case Coverage | FAIL |
| Implementation Correctness | FAIL |
| Structural Integrity | PASS |
| Verification Readiness | FAIL |

## Findings

### S3-FIND-001 (Implementation Correctness + Edge Case Coverage, MAJOR)
`telemetry-schema.js`'s optional-additive-field checks all gate on `!== undefined`
(lines 17, 20, 23, 30 for `tags`, `revenue_today_usd`, `revenue_by_source`, `log_feed`). But
Supabase/PostgREST returns an **explicit JSON `null`** for every unset column on a pre-migration
row — it never omits the key. `null !== undefined` is `true`, so `validate()` falls into each
optional-field branch and then rejects the row: `Array.isArray(null)` is `false` →
`tags:null` is rejected; `typeof null === "object"` is true but `s === null` short-circuits →
`revenue_by_source:null` is rejected; `log_feed:null` likewise rejected via `Array.isArray(null)`.

`verify-live-migration.mjs:104-107` papers over exactly this by manually stripping every `null`
key to `undefined` **before** calling `validate()`:
```js
const cleaned = {};
for (const [k, v] of Object.entries(row)) if (v !== null) cleaned[k] = v;
const v = validate(cleaned);
```
This means S3.4's claim ("every pre-migration row SHALL still validate under
`_lib/telemetry-schema.validate`") is only true of the *script-massaged* input, not of the
`validate()` function itself operating on a real Supabase row. This is precisely the edge case
S3.4 exists to prove is handled — and it is not handled by the function under test, only by an
ad-hoc preprocessing step that lives outside the reviewed unit (`telemetry-schema.js`). Today the
blast radius is contained (grep confirms `validate()` is only called from `telemetry-verify.js` on
freshly client-signed JSON, which never contains `null`, and from this one script), but any future
caller that validates a raw Supabase row directly (e.g. a consistency job, an admin tool, a second
verify script) will silently reject legitimate legacy rows. The fix belongs in
`telemetry-schema.js` (treat `null` as absent for optional fields, `v == null` not `v !== undefined`),
not in each call site.
- Evidence: `apps/landing/scripts/verify-live-migration.mjs:100-109`,
  `apps/landing/netlify/functions/_lib/telemetry-schema.js:17-32`.
- routeToPhase: 2b

### S3-FIND-002 (Spec Fidelity, MAJOR)
The spec's own framing ("sprint-3 flips the production switch: the additive migration is executed
… so a real agent … actually lands in the served aniccaai.com/dashboard leaderboard",
`sprint-3-production-rollout.md:5-7`) is not true today. The live evidence itself says so
(`sprint-3-live-rollout.log:33-35`): the deployed `/dashboard-sync` on `main` runs an OLDER,
un-enriched version — `is_ours`/`earn_src`/`net_worth_src` are all `null` on the live response. A
real agent registering right now would show up on aniccaai.com with **no** no-fake enrichment,
indistinguishable from a pre-sprint-1 row. The disclosure in the evidence log's "FOLLOW-UPS" (line
62: "Merge feature/clip-rewards → main…") is honest, but disclosure does not satisfy the
requirement — the spec's "Scope (out)" section (`sprint-3-production-rollout.md:59-64`) never
mentions this merge dependency at all, so a reader of the spec alone (without the evidence log)
would believe S3.5 proves the full rollout, when it only proves the schema-level contract, not the
application-level one. The numbered "Done" bullets are satisfied, but the sprint's stated top-line
outcome is not — this should be a named, numbered scope-out item in the spec, not something first
surfaced in the evidence log after the fact.
- Evidence: `sprint-3-production-rollout.md:5-7,59-64`; `sprint-3-live-rollout.log:30-35,61-66`.
- routeToPhase: 2b (spec correction) + 4 (feedback routing: block "sprint-3 = production rollout
  done" framing until the merge lands)

### S3-FIND-003 (Verification Readiness, MODERATE)
`verify-live-migration.mjs` runs S3.1 (apply — a real, irreversible-in-effect write against
production) unconditionally, and only *afterward* runs S3.2–S3.4 as a post-hoc report. There is no
pre-apply dry check and no automated rollback path if S3.4 discovers a real back-compat break
after the migration has already landed on production — `main()` only sets the process exit code
(`summary.ok ? 0 : 1`); nothing un-does the `alter table` that already ran. For this specific
additive-only migration the residual risk is low (no `DROP`/`SET NOT NULL`), but the script's
structure conflates "apply" and "verify" as one unconditional sequence rather than "verify
preconditions → apply → verify postconditions with a documented revert step" — worth hardening
before this pattern is reused for a less-trivially-additive future migration.
- Evidence: `apps/landing/scripts/verify-live-migration.mjs:65-115` (no revert path anywhere in file).
- routeToPhase: 2b

### S3-FIND-004 (Edge Case Coverage, MINOR/informational)
`REQUIRED_COLUMNS` in the verify script asserts exact-string equality on
`information_schema.columns.data_type` / `udt_name` (`double precision`, `jsonb`,
`timestamp with time zone`, `ARRAY`/`_text`). These SQL-standard type-name strings are stable
across supported Postgres major versions, so this is low real-world risk, but the check is
brittle-by-construction (a case difference or a future Postgres/Supabase display-name change would
silently flip S3.2 to FAIL with a confusing diff rather than a normalized/tolerant comparison). Not
blocking on its own; flagged for completeness per the mandatory edge-case hunt.
- Evidence: `apps/landing/scripts/verify-live-migration.mjs:55-63`.
- routeToPhase: 4

## What genuinely holds (positive evidence, not re-litigated)
- Migration file is additive-only, every DDL statement uses `IF NOT EXISTS` (`2026-07-instances-leaderboard.sql:12-20`) — idempotent, no `DROP`, no `SET NOT NULL`, consistent with sprint-1 R9's back-compat invariant.
- The negative-PnL fix itself (`telemetry-schema.js:23-29`) is correct as far as it goes: `Number.isFinite` correctly accepts real losses and correctly rejects `NaN`/`Infinity`/strings — `schema.additive.test.js:19-27` traces cleanly against it.
- `revenue_by_source`/`tags`/`log_feed` are never consumed downstream in `aggregate`/`enrich`/`dashboard-sync` for arithmetic, so the null-handling defect in S3-FIND-001 cannot silently corrupt a rendered total today — it can only cause a spurious *rejection* of a legacy row if `validate()` is ever called directly on a raw Supabase row outside this one script.
- No `aniccaai.com`-served-json write guardrail violation: the live-verify script and the S3.6 local-render proof are read-only against Supabase/Base RPC; the Management-API apply (S3.1) is an ops action against the DB, not a write to `apps/landing/public/dashboard.json` — consistent with the "Anicca instances don't write served json" boundary.

## Must-fix
1. Fix `telemetry-schema.js` to treat `null` as absent for every optional additive field (or add an
   explicit, tested, reusable normalization helper used by every call site) — S3-FIND-001.
2. Add the main-branch-merge dependency as a named, numbered scope-out item in
   `sprint-3-production-rollout.md`, and stop describing sprint-3 as delivering "a real agent…
   appears correctly on the live leaderboard" until that merge is verified live — S3-FIND-002.
3. Harden `verify-live-migration.mjs` with a documented revert step (or at minimum a pre-apply
   shadow-verify) before this apply-then-verify pattern is reused for a non-trivially-additive
   migration — S3-FIND-003.
