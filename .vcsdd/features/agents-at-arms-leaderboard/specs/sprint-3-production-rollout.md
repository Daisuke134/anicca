# Sprint-3 Production Rollout Spec — apply the leaderboard migration to LIVE Supabase

Sprint-1 built the no-fake engine; sprint-2 wired schema/spawn/render; both passed sonnet-5
adversary + 74 unit tests + browser E2E. Sprint-3 flips the production switch: **the additive
migration is executed against the real Supabase project so a real agent that calls
`registerSpawn(...)` with tags:["agent-hackathon"] actually lands in the served
aniccaai.com/dashboard leaderboard**. No mocks in this sprint's verification.

## Ground truth (live)

- Project ref: `cycgdwndgfgdbnndithc` (Supabase host `cycgdwndgfgdbnndithc.supabase.co`).
- Auth: `SUPABASE_ACCESS_TOKEN` (starts `sbp_`) for Management API SQL; `SUPABASE_SERVICE_ROLE_KEY`
  for PostgREST reads (already wired in Netlify env).
- Migration file: `apps/landing/supabase/2026-07-instances-leaderboard.sql` (sprint-2 GREEN,
  sonnet-5 impl-adversary PASS round 2).

## S3 requirements (EARS)

- **S3.1 (idempotent apply)** The migration SHALL be applied to the live project via
  `POST https://api.supabase.com/v1/projects/{ref}/database/query` with the SUPABASE_ACCESS_TOKEN
  bearer. The response SHALL be logged verbatim as evidence. Running the migration a second time
  SHALL succeed with no schema drift (every `alter table … add column if not exists` and the
  `create index if not exists idx_instances_tags_gin` are already idempotent per sprint-2 spec S7).
- **S3.2 (live schema probe)** A live-verify script SHALL, on demand, query the live project and
  assert that every one of the seven new columns exists in `information_schema.columns` for the
  `instances` table (`tags text[]`, `revenue_today_usd double precision`,
  `revenue_by_source jsonb`, `net_worth_src text`, `earn_src text`, `last_heartbeat timestamptz`,
  `log_feed jsonb`), and that the GIN index `idx_instances_tags_gin` exists in `pg_indexes`.
  Before apply: SHALL FAIL with the missing-column list. After apply: SHALL PASS.
- **S3.3 (row preservation)** The `instances` row count SHALL NOT change across the migration
  (additive only). The verify script SHALL take a pre-count and post-count and assert equality.
- **S3.4 (back-compat)** Every pre-migration row SHALL still validate under
  `_lib/telemetry-schema.validate`. The verify script SHALL fetch all rows via the SERVICE ROLE
  key and run `validate` locally; every row SHALL come back `{ ok:true }`.
- **S3.5 (endpoint smoke)** After the migration is applied, the deployed Netlify function
  `/.netlify/functions/dashboard-sync` (or the aniccaai.com equivalent) SHALL still respond 200
  with a JSON body containing a `leaderboard` array. This proves sprint-2 R12 still holds against
  the newly-migrated table. No mocks.

## Verification architecture

| Req  | Test                                      | Real target                                   |
|------|-------------------------------------------|-----------------------------------------------|
| S3.1 | apply POST → 2xx; response saved to evidence | live Supabase Management API                 |
| S3.2 | information_schema query lists 7 columns; pg_indexes lists idx_instances_tags_gin | live Supabase DB |
| S3.3 | `select count(*)` before/after equal      | live Supabase DB                              |
| S3.4 | fetch all rows via PostgREST, run local `validate` | live PostgREST + local `telemetry-schema.js` |
| S3.5 | curl the deployed `/dashboard-sync`, assert `200 ∧ body.leaderboard :: array` | live Netlify function |

## Done

1. Evidence log at `.vcsdd/features/agents-at-arms-leaderboard/evidence/sprint-3-live-rollout.log`
   containing the apply response, the post-apply schema probe result, pre/post row counts, the
   validate-all-rows result, and the endpoint smoke response status + `leaderboard` shape.
2. `scripts/verify-live-migration.mjs` on disk and re-runnable.
3. Fresh-context sonnet-5 adversary PASS on the spec + the applied evidence + the verify script.
4. NO row was dropped, NO existing row failed validation.

## Scope (out)

- The scheduled render (`render-dashboard.mjs` on a cron / GH Action) = A3, next sprint.
- The `SUPABASE_DB_URL` direct-psql path (not used — we route through Management API to avoid
  keeping a DB password in local env).
