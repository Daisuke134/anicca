# Life Manager CFO Reliable Daily Run Implementation Plan

> **For the Sol controller:** Use Superpowers subagent-driven-development. Sol owns this plan and state; only a Luna
> implementer writes production code, tests, SQL, or performs live migration/E2E.

**Goal:** Close CFO-1g2 with one stable owner-local daily run and one append-only Telegram delivery receipt identity.

**Design:** `docs/superpowers/specs/2026-08-09-life-manager-cfo-reliable-run-design.md`.

**Status:** ACTIVE — Tasks 1/1b/2/3/4 complete; Task 4 PostgreSQL concurrency/permission proof awaits fresh Sol review before Task 5.

## Global constraints

- One task at a time: RED → minimum GREEN → focused/full tests → push → fresh Sol review.
- No Moneytree read, report render, Telegram send, scheduler, correction, or self-repair in CFO-1g2.
- No raw financial payload, amount, UID, chat ID, token, provider response body, or message text in reports/errors.
- At most three changed files per task. Above 100 production LOC is split unless SQL atomicity makes one function
  indivisible and the plan records why.

### Task 1: Durable owner-local run claim

**Files:**
- Create `apps/life-call/migrations/2026-08-09-cfo-daily-runs.sql`
- Create `apps/life-call/lib/cfo-daily-run-migration.test.js`
- Modify `apps/life-call/package.json`

- [x] RED: assert immutable table, unique owner/date and owner/date/run, non-zero UUID, `pg_timezone_names` validation,
  preference read inside the RPC, existing-snapshot backfill, composite snapshot FK, RLS/service-role grants,
  UPDATE/DELETE trigger, exact five-key receipt, same-date retry, fixed search path, no UID in receipt, and private
  date-helper EXECUTE revoked from all app roles. Backfill must abort when an existing owner preference is absent or
  invalid and record `time_zone_source="migration_preference"`; new claims record `owner_preference`.
- [x] GREEN: implement `lm_cfo_daily_runs` and
  `lm_claim_cfo_daily_run(text) => jsonb`. Backfill existing snapshot run IDs before adding the FK. The RPC reads and
  validates the current preference and derives the date transactionally; `ON CONFLICT DO NOTHING`, then returns the
  existing row. No UPDATE branch.
- [x] Verify from `apps/life-call`: `node --test lib/cfo-daily-run-migration.test.js` (RED then PASS),
  `npm run test:cfo` (PASS),
  `wc -l migrations/2026-08-09-cfo-daily-runs.sql lib/cfo-daily-run-migration.test.js` (targets), and
  `git diff --check` (exit 0). The tests, not a regex scan, prove the closed receipt has no UID/private keys.
- [x] Commit/push `feat(cfo): claim stable daily runs`; write the ignored Task 1 report.

### Task 1b: Reproducible PostgreSQL proof for the daily-run claim

**Files:**
- Create `apps/life-call/test/postgres/cfo-daily-run-postgres.integration.sh`
- Modify `apps/life-call/package.json`

- [x] RED then GREEN with `npm run test:cfo-daily-run:postgres` in isolated local PostgreSQL 18 or ephemeral
  `postgres:18-alpine`. Copy only the lifecycle/cleanup pattern from the existing CFO snapshot PostgreSQL test.
- [x] Prove migration-wide rollback for an existing snapshot owner with missing and invalid timezone; exact original
  `run_id` plus `migration_preference` backfill; composite FK rejection; service-role claim/retry and two concurrent
  claims returning one row/run; PUBLIC/anon/authenticated/service_role rejection for the private date helper;
  UPDATE/DELETE trigger rejection; and exact five-key no-UID JSON receipt.
- [x] Final stdout is exactly `cfo-daily-run-postgres: PASS`; then run `npm run test:cfo` and `git diff --check`.
- [x] Commit/push `test(cfo): prove stable daily runs`; append RED/GREEN evidence to the Task 1 report and obtain a
  fresh scoped Sol re-review before Task 3.

### Task 2: Owner timezone and run-context client

**Files:**
- Create `apps/life-call/lib/cfo-daily-run.js`
- Create `apps/life-call/lib/cfo-daily-run.test.js`
- Modify `apps/life-call/package.json`

**Interface:** `resolveCfoDailyRun({ uid }, { supaUrl, supaKey, fetchImpl })`.

- [x] RED: exact input, one claim RPC and no preference GET, closed frozen five-key receipt, valid returned timezone
  and date, Proxy/accessor/custom errors, no retry/log/leakage.
- [x] GREEN: call only `lm_claim_cfo_daily_run`; PostgreSQL owns timezone/date derivation.
- [x] Verify from `apps/life-call`: `node --test lib/cfo-daily-run.test.js`, `npm run test:cfo`, `wc -l
  lib/cfo-daily-run.js lib/cfo-daily-run.test.js`, and `git diff --check`; all exit 0, production ≤100/tests ≤180.
- [x] Commit/push `feat(cfo): resolve owner daily runs`; write report and obtain fresh Sol review.

### Task 3: Append-only Telegram delivery ledger

**Files:**
- Create `apps/life-call/migrations/2026-08-09-cfo-telegram-deliveries.sql`
- Create `apps/life-call/lib/cfo-telegram-delivery-migration.test.js`
- Modify `apps/life-call/package.json`

- [x] RED: assert composite snapshot linkage, immutable claim/receipt tables, one delivery key, positive provider
  message ID, service-only RLS/grants, exact claim decisions, exact retry/conflict, fixed search path, and no sensitive
  columns.
- [x] GREEN: implement claims/receipts plus RPCs
  `lm_claim_cfo_telegram_delivery(text,uuid,text,date,integer)` and
  `lm_record_cfo_telegram_delivery(uuid,bigint)`. Fresh insert=`send`; existing with receipt=`sent`; existing without
  receipt=`reconcile`. No UPDATE/DELETE.
- [x] Verify from `apps/life-call`: `node --test lib/cfo-telegram-delivery-migration.test.js`, `npm run test:cfo`,
  `wc -l migrations/2026-08-09-cfo-telegram-deliveries.sql lib/cfo-telegram-delivery-migration.test.js`, and
  `git diff --check`; all exit 0. SQL ≤180 LOC or report the indivisible transaction.
- [x] Commit/push `feat(cfo): add telegram delivery ledger`; write report and obtain fresh Sol review.

### Task 4: Real PostgreSQL concurrency and permission proof

**Files:**
- Create `apps/life-call/test/postgres/cfo-reliable-run-postgres.integration.sh`
- Modify `apps/life-call/package.json`

- [x] RED then GREEN with `npm run test:cfo-reliable-run:postgres` in isolated local PostgreSQL 18 or ephemeral
  `postgres:18-alpine` only. Call the private date helper as superuser with fixed DST/date-boundary instants; prove
  application roles cannot execute it. The public RPC has no clock parameter and uses database time.
- [x] Prove: concurrent run claims one row/run; concurrent delivery claims one `send`; unreceipted retry=`reconcile`;
  receipt makes retry=`sent`; exact receipt retry; changed ID conflict; composite cross-tenant/date/revision rejection;
  direct invalid rows; role denials; UPDATE/DELETE trigger rejection; tenant separation.
- [x] Final stdout exactly `cfo-reliable-run-postgres: PASS`; also run `npm run test:cfo` and `git diff --check`.
- [x] Commit/push `test(cfo): prove reliable run concurrency`; write report and obtain fresh Sol review.

### Task 5: Telegram delivery client

**Files:**
- Create `apps/life-call/lib/cfo-telegram-delivery.js`
- Create `apps/life-call/lib/cfo-telegram-delivery.test.js`
- Modify `apps/life-call/package.json`

**Interfaces:** `claimCfoTelegramDelivery(input, opts)` and `recordCfoTelegramDelivery(input, opts)`.

- [ ] RED: one RPC per operation, closed exact input/receipt, only `assets_liabilities`, positive revision/message ID,
  `send|sent|reconcile`, clone/freeze, no retry/direct table/log, hostile response/error redaction, exact echo checks.
- [ ] GREEN: built-in fetch only; stable redacted errors; never accept `send` unless the RPC says this call inserted.
- [ ] Verify from `apps/life-call`: `node --test lib/cfo-telegram-delivery.test.js`, `npm run test:cfo`, `wc -l` for
  both files with `wc -l lib/cfo-telegram-delivery.js lib/cfo-telegram-delivery.test.js`, and `git diff --check`;
  all exit 0, production ≤130/tests ≤200.
- [ ] Commit/push `feat(cfo): persist telegram delivery receipts`; write report and obtain fresh Sol review.

### Task 6: Live migration, no-send E2E, and closure

**Files:**
- Modify parent/design/plan docs only after evidence is complete.

- [ ] Luna runs from `apps/life-call`: `npm ci --no-audit --no-fund`;
  `node --test lib/cfo-daily-run-migration.test.js lib/cfo-daily-run.test.js lib/cfo-telegram-delivery-migration.test.js lib/cfo-telegram-delivery.test.js`;
  `npm run test:cfo`; `npm run test:cfo-reliable-run:postgres`; `npm test`; and `git diff --check`. All exit 0.
- [ ] Luna applies both additive migrations once and reloads PostgREST schema without outputting private values.
- [ ] The formal migration path is the existing Supabase Management API database-query endpoint followed by
  `NOTIFY pgrst, 'reload schema'`. Luna creates an ignored no-echo runner at
  `.superpowers/sdd/2026-08-09-life-manager-cfo-reliable-run/live-close.js` from the worktree root. Required private
  environment names are exactly `SUPABASE_ACCESS_TOKEN`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY`. The
  Management request uses `Authorization: Bearer <SUPABASE_ACCESS_TOKEN>` and `Content-Type: application/json`; live
  PostgREST reads/RPCs use both `apikey: <SUPABASE_SERVICE_ROLE_KEY>` and
  `Authorization: Bearer <SUPABASE_SERVICE_ROLE_KEY>`. The runner derives the project ref from `SUPABASE_URL`, POSTs
  each SQL file as `{query: sql}` to `https://api.supabase.com/v1/projects/<ref>/database/query`, then POSTs
  `{query: "NOTIFY pgrst, 'reload schema';"}`. After the tests above, run `cd ../..` and then
  `node .superpowers/sdd/2026-08-09-life-manager-cfo-reliable-run/live-close.js`; every HTTP response must have
  `ok === true`, and stdout is only one JSON object of named booleans/counts.
- [ ] The no-echo runner makes these exact PostgREST calls with the service-role headers above and never prints a URL,
  query value, body, or response:
  1. `GET /rest/v1/lm_users?telegram_chat_id=not.is.null&select=uid&limit=2`, no body, expect HTTP 200 and exactly one
     row for the current Dais-first live scope; keep its UID private or fail closed.
  2. `POST /rest/v1/rpc/lm_claim_cfo_daily_run`, JSON body `{p_uid:<private uid>}`, expect HTTP 200 and an exact
     five-key object `public_ref,reporting_date,run_id,time_zone,created_at`.
  3. Repeat call 2 with the identical private body; expect HTTP 200 and the exact same five values.
  4. `GET /rest/v1/lm_cfo_daily_snapshots?uid=eq.<encoded-private-uid>&reporting_date=eq.<encoded-date>&select=public_ref,run_id&limit=1`,
     no body, expect HTTP 200 and one row whose `run_id` equals the claim. Keep both refs private.
  5. `GET /rest/v1/lm_cfo_telegram_delivery_claims?snapshot_public_ref=eq.<encoded-private-snapshot-ref>&select=public_ref`,
     no body, expect HTTP 200 and `[]`. The receipt table cannot contain a row without its claim FK.
- [ ] Luna proves against the existing live snapshot: owner timezone resolves, daily-run retry is stable, and snapshot
  `(uid, reporting_date, run_id)` equals its run claim. It creates no live delivery claim/receipt and does not call
  Telegram. Delivery claim/receipt behavior is proven only in isolated PostgreSQL until CFO-1h sends for real.
- [ ] The live runner's exact stdout keys are `runMigrationSuccess`, `deliveryMigrationSuccess`,
  `schemaReloadSuccess`, `ownerTimezoneResolved`, `retrySameRun`, `snapshotRunMatches`, `liveDeliveryRowsCreated`,
  and `payloadPrivacy`; all booleans are true except `liveDeliveryRowsCreated`, which is the integer `0`.
- [ ] Fresh Sol final review returns no Critical/Important findings.
- [ ] Sol marks `CFO-1g2 COMPLETE — CFO-1g3 NEXT`, records boolean/count evidence, commits/pushes
  `docs(cfo): close reliable daily run`, and sends a separate development milestone notification.

## Completion boundary

CFO-1g2 closes after live stable-run/FK proof plus isolated delivery-dedupe proof. The first real Telegram financial
report remains 7/7. CFO-1h must detect `reconcile` as a durable delivery-unknown blocker and provide redacted operator
reconciliation before any resend; no development milestone may be described as the finance report.
