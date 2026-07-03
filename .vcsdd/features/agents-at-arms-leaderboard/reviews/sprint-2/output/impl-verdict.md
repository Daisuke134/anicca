# Sprint-2 Implementation Adversary Verdict — agents-at-arms-leaderboard

**Feature**: agents-at-arms-leaderboard
**Scope**: S7, S9, S11 only (sprint-1 R1-R12 not re-litigated; regression checked only)
**Overall verdict**: **FAIL**
**Iteration**: 1
**Timestamp**: 2026-07-04T00:00:00Z

## Test execution disclosure (honesty rule)

No `Bash` tool was available in this review session (tool list = Read/Write/Edit/Grep/Glob only) so
the suite was **not executed by me**; this is disclosed rather than fabricated. In its place I did a
full manual statement-by-statement trace of every assertion in `schema-migration.test.js`,
`spawn-register.test.js`, and `render-dashboard.test.js` against the actual implementation and its
transitive ground-truth deps (`telemetry-verify.js`, `telemetry-schema.js`, `telemetry-store.js`,
`telemetry-aggregate.js`, `enrich.js`, `leaderboard-constants.js`), and cross-checked against
`.vcsdd/features/agents-at-arms-leaderboard/evidence/sprint-2-{red,green}-phase.log` (16/16 new,
68/68 total claimed). All 16 sprint-2 assertions trace to green as claimed *for the code paths they
actually exercise*. The critical defect below (S2-IMPL-FIND-001) is in a code path **no test
exercises at all** — a green suite cannot surface it, which is itself the finding.

## Dimension verdicts

| Dimension | Verdict | Findings |
|---|---|---|
| spec_fidelity | FAIL | S2-IMPL-FIND-001 (S11.1's own text requires the production/CLI path, which is broken) |
| edge_case_coverage | FAIL | S2-IMPL-FIND-002, S2-IMPL-FIND-004 |
| implementation_correctness | FAIL | S2-IMPL-FIND-001 |
| structural_integrity | FAIL | S2-IMPL-FIND-003 |
| verification_readiness | FAIL | S2-IMPL-FIND-002 |

## Positive evidence (what actually holds up)

- `apps/landing/supabase/2026-07-instances-leaderboard.sql:12-19` — all 6 additive columns +
  GIN index, every DDL statement `IF NOT EXISTS`, no `DROP`/`SET NOT NULL`. Traced against all 8
  schema-migration.test.js regexes: all match. S7.1/S7.2 hold.
- `spawn-register.js:12` builds `canonicalMessage(payload)` via the SAME imported function
  `telemetry-verify.js` uses server-side (not a re-implementation) — cross-language/byte-identity
  risk from a divergent re-serializer is structurally impossible here.
- `spawn-register.js:16-19` correctly lowercases both sides before comparing signer to `payload.id`
  (verified against the upper-case-id test case), and throws + never calls `upsertInstance` on
  mismatch (traced test 3, `stub.calls.length === 0`).
- `spawn-register.js:24-25` stamps `last_heartbeat` from the injected clock, independent of
  `telemetry-store.js`'s own wall-clock `updated_at` — traced test 4, both ISO-parseable and
  distinct fields.
- `render-dashboard.mjs:24-41` `mergeIntoExisting`/`renderDashboard` correctly route through
  `enrichOnChain(reader)` → `aggregate()` (never raw rows), preserve all pre-existing top-level keys
  via `{...existing, ...}`, and correctly overwrite self-reported `net_worth_usd`/`revenue_mo_usd`
  with chain-derived figures (traced S11.1's "self-report liar" fixture: 0xa2's real $88 chain inflow
  correctly outranks 0xa1's fabricated `net_worth_usd:999999`).
- S11.2 broken-reader fixture traced: both `net_worth_src` and `earn_src` become `'unverified'` for
  every row when the reader throws — no fabricated figures.

## Must-fix (blocking)

1. **`apps/landing/scripts/render-dashboard.mjs:103`** — `if (import.meta.url === \`file://${process.argv[1]}\`)`
   silently never fires `main()` when the script is invoked with a relative path (`node
   apps/landing/scripts/render-dashboard.mjs` from repo root, or any GH Action/cron using a repo-root
   cwd — the normal invocation shape). `process.argv[1]` is not guaranteed absolute; Node's own ESM
   docs recommend resolving it first. Result: exit 0, zero output, dashboard.json never touched — a
   silent no-op that looks identical to success. This is the exact "production" path S11.1 names.
   **Fix**: `if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) { await main(); }`.
2. **Zero test coverage of `main()`/the CLI branch** (S2-IMPL-FIND-002) — add a real child-process
   spawn test against a stub HTTP server so this class of bug cannot ship green again.
3. **Missing malformed-additive-field integration test for `registerSpawn`** (S2-IMPL-FIND-004) —
   nothing proves the S9 call site itself (not just the shared schema module) rejects a bad `tags`/
   `revenue_today_usd`/`revenue_by_source` before touching the store.
4. Non-blocking cleanup: de-duplicate the signer==id check in `spawn-register.js:16-22`
   (S2-IMPL-FIND-003) — the same invariant is independently re-derived twice.

## Regression check (sprint-1)

No sprint-2 file touches `telemetry-schema.js`, `telemetry-aggregate.js`, `telemetry-verify.js`,
`enrich.js`, `leaderboard-constants.js`, `dashboard-sync.js`, or `instances.sql` — the additive SQL,
`spawn-register.js`, and `render-dashboard.mjs` are net-new files that only *call* the ground truth.
No regression risk identified by static diff.

## Convergence signals

- findingCount: 4
- allCriteriaEvaluated: true
- evaluatedCriteria: ["S7", "S9", "S11"]
- duplicateFindings: []
