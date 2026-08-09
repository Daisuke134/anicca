# Life Manager CFO Reliable Daily Run Implementation Plan

> **For the Sol controller:** Use Superpowers subagent-driven-development. Sol owns this plan and state; only a Luna
> implementer writes production code, tests, SQL, or performs live migration/E2E.

**Goal:** Close CFO-1g2 with one stable owner-local daily run and one append-only Telegram delivery receipt identity.

**Design:** `docs/superpowers/specs/2026-08-09-life-manager-cfo-reliable-run-design.md`.

**Status:** ACTIVE — Task 1 next.

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

- [ ] RED: assert immutable table, unique owner/date and owner/date/run, non-zero UUID, `pg_timezone_names` validation,
  preference read inside the RPC, existing-snapshot backfill, composite snapshot FK, RLS/service-role grants,
  UPDATE/DELETE trigger, exact five-key receipt, same-date retry, fixed search path, and no UID in receipt.
- [ ] GREEN: implement `lm_cfo_daily_runs` and
  `lm_claim_cfo_daily_run(text) => jsonb`. Backfill existing snapshot run IDs before adding the FK. The RPC reads and
  validates the current preference and derives the date transactionally; `ON CONFLICT DO NOTHING`, then returns the
  existing row. No UPDATE branch.
- [ ] Verify from `apps/life-call`: `node --test lib/cfo-daily-run-migration.test.js` (RED then PASS),
  `npm run test:cfo` (PASS), `wc -l` (targets), `git diff --check` (exit 0), and a key-name privacy scan (no match).
- [ ] Commit/push `feat(cfo): claim stable daily runs`; write the ignored Task 1 report.

### Task 2: Owner timezone and run-context client

**Files:**
- Create `apps/life-call/lib/cfo-daily-run.js`
- Create `apps/life-call/lib/cfo-daily-run.test.js`
- Modify `apps/life-call/package.json`

**Interface:** `resolveCfoDailyRun({ uid }, { supaUrl, supaKey, fetchImpl })`.

- [ ] RED: exact input, one claim RPC and no preference GET, closed frozen five-key receipt, valid returned timezone
  and date, Proxy/accessor/custom errors, no retry/log/leakage.
- [ ] GREEN: call only `lm_claim_cfo_daily_run`; PostgreSQL owns timezone/date derivation.
- [ ] Verify from `apps/life-call`: `node --test lib/cfo-daily-run.test.js`, `npm run test:cfo`, `wc -l
  lib/cfo-daily-run.js lib/cfo-daily-run.test.js`, and `git diff --check`; all exit 0, production ≤100/tests ≤180.
- [ ] Commit/push `feat(cfo): resolve owner daily runs`; write report and obtain fresh Sol review.

### Task 3: Append-only Telegram delivery ledger

**Files:**
- Create `apps/life-call/migrations/2026-08-09-cfo-telegram-deliveries.sql`
- Create `apps/life-call/lib/cfo-telegram-delivery-migration.test.js`
- Modify `apps/life-call/package.json`

- [ ] RED: assert composite snapshot linkage, immutable claim/receipt tables, one delivery key, positive provider
  message ID, service-only RLS/grants, exact claim decisions, exact retry/conflict, fixed search path, and no sensitive
  columns.
- [ ] GREEN: implement claims/receipts plus RPCs
  `lm_claim_cfo_telegram_delivery(text,uuid,text,date,integer)` and
  `lm_record_cfo_telegram_delivery(uuid,bigint)`. Fresh insert=`send`; existing with receipt=`sent`; existing without
  receipt=`reconcile`. No UPDATE/DELETE.
- [ ] Verify from `apps/life-call`: `node --test lib/cfo-telegram-delivery-migration.test.js`, `npm run test:cfo`,
  `wc -l` for both files, and `git diff --check`; all exit 0. SQL ≤180 LOC or report the indivisible transaction.
- [ ] Commit/push `feat(cfo): add telegram delivery ledger`; write report and obtain fresh Sol review.

### Task 4: Real PostgreSQL concurrency and permission proof

**Files:**
- Create `apps/life-call/test/postgres/cfo-reliable-run-postgres.integration.sh`
- Modify `apps/life-call/package.json`

- [ ] RED then GREEN with `npm run test:cfo-reliable-run:postgres` in isolated local PostgreSQL 18 or ephemeral
  `postgres:18-alpine` only.
- [ ] Prove: concurrent run claims one row/run; concurrent delivery claims one `send`; unreceipted retry=`reconcile`;
  receipt makes retry=`sent`; exact receipt retry; changed ID conflict; composite cross-tenant/date/revision rejection;
  direct invalid rows; role denials; UPDATE/DELETE trigger rejection; tenant separation.
- [ ] Final stdout exactly `cfo-reliable-run-postgres: PASS`; also run `npm run test:cfo` and `git diff --check`.
- [ ] Commit/push `test(cfo): prove reliable run concurrency`; write report and obtain fresh Sol review.

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
  both files, and `git diff --check`; all exit 0, production ≤130/tests ≤200.
- [ ] Commit/push `feat(cfo): persist telegram delivery receipts`; write report and obtain fresh Sol review.

### Task 6: Live migration, no-send E2E, and closure

**Files:**
- Modify parent/design/plan docs only after evidence is complete.

- [ ] Luna runs from `apps/life-call`: `npm ci --no-audit --no-fund`; both focused Node test commands;
  `npm run test:cfo`; `npm run test:cfo-reliable-run:postgres`; `npm test`; and `git diff --check`. All exit 0.
- [ ] Luna applies both additive migrations once and reloads PostgREST schema without outputting private values.
- [ ] The formal migration path is the existing Supabase Management API database-query endpoint followed by
  `NOTIFY pgrst, 'reload schema'`; Luna outputs HTTP success booleans only.
- [ ] Luna proves against the existing live snapshot: owner timezone resolves, daily-run retry is stable, and snapshot
  `(uid, reporting_date, run_id)` equals its run claim. It creates no live delivery claim/receipt and does not call
  Telegram. Delivery claim/receipt behavior is proven only in isolated PostgreSQL until CFO-1h sends for real.
- [ ] Fresh Sol final review returns no Critical/Important findings.
- [ ] Sol marks `CFO-1g2 COMPLETE — CFO-1g3 NEXT`, records boolean/count evidence, commits/pushes
  `docs(cfo): close reliable daily run`, and sends a separate development milestone notification.

## Completion boundary

CFO-1g2 closes after live stable-run/FK proof plus isolated delivery-dedupe proof. The first real Telegram financial
report remains 7/7. CFO-1h must detect `reconcile` as a durable delivery-unknown blocker and provide redacted operator
reconciliation before any resend; no development milestone may be described as the finance report.
