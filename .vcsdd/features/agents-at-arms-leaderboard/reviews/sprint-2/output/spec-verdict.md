# VCSDD Sprint-2 Spec-Review Verdict — agents-at-arms-leaderboard

- Reviewer: fresh-context adversary (disk-only, zero builder context)
- Artifact under judgment: `.vcsdd/features/agents-at-arms-leaderboard/specs/sprint-2-behavioral-spec.md`
- Cross-checked against: `apps/landing/supabase/instances.sql`, `_lib/{telemetry-schema,telemetry-verify,telemetry-store,telemetry-aggregate,enrich,chain-reader,leaderboard-constants}.js`, `netlify/functions/dashboard-sync.js`, `app/dashboard/page.tsx`, `components/site/AgentLeaderboard.tsx`, and the pre-existing RED tests (`schema-migration.test.js`, `spawn-register.test.js`, `render-dashboard.test.js`, `verify.additive.test.js`).

## Overall verdict: **FAIL**

| Dimension | Verdict | Findings |
|---|---|---|
| 1. Spec Fidelity | FAIL | S2-SPEC-FIND-001 |
| 2. Edge Case Coverage | FAIL | S2-SPEC-FIND-003, S2-SPEC-FIND-005 |
| 3. Impl Correctness (testability) | FAIL | S2-SPEC-FIND-002 |
| 4. Structural Integrity | PASS | (see notes) |
| 5. Verification Readiness | FAIL | S2-SPEC-FIND-004 |

## Must-fix (blocking)

1. **S7.1 migration is missing `log_feed`** — validated (`telemetry-schema.js:27-29`) and signed
   (`telemetry-verify.js:18`) since sprint-1, but never given a column. `telemetry-store.js:18`
   spreads the whole payload into the PostgREST insert body, so any real payload carrying
   `log_feed` will hit an unknown-column error and silently break heartbeat registration.
2. **S9.1's call signature is under-specified vs. the RED test already on disk** —
   `spawn-register.test.js:42` calls `registerSpawn({privateKey, payload, storeDeps, now})`
   (options object + undocumented `now` clock + an unspecified `{message, signature}` return),
   while 1a text says `(privateKey, payload, storeDeps)`. Two builders reading only 1a would diverge.
3. **S11's effectful disk-write path has zero 1b proof** — no requirement covers (a) missing
   `SUPABASE_URL`/service key in prod silently emitting `rows=[]` and overwriting a good
   `leaderboard` with `[]`, or (b) a non-atomic write racing `page.tsx:29-31`'s synchronous
   `fs.readFile`+`JSON.parse`, whose catch (`page.tsx:31,36`) blanks the ENTIRE `/dashboard` page,
   not just the leaderboard, on any parse failure.
4. **S9.2's RED assertion is near-tautological** — `/signer|mismatch|id/i`
   (`spawn-register.test.js:64`) matches almost any thrown error text; it doesn't prove the throw
   is caused by the signer≠id invariant specifically.

Minor: pre-migration rows read back through Supabase have additive columns as explicit `null`
(present, not absent); `render-dashboard.test.js` fixtures never model that shape (S2-SPEC-FIND-005).

## Structural Integrity notes (not blocking)
S9.2's "same invariant as the netlify verifier, applied pre-upload" is intentional
defense-in-depth, not a genuine duplication/contradiction. The `apps/landing/scripts/render-dashboard.mjs`
placement and the aniccaai.com write-guardrail (Anicca never writes the served json; only its own
Supabase row) are consistent with the live architecture in `dashboard-sync.js` and `page.tsx`.

## Recommendation
Do not proceed to Phase 2 GREEN until findings 1-4 are resolved in the spec text (and, since RED
tests already exist on disk, findings 1/2/4 require editing those test files too, not just prose).
