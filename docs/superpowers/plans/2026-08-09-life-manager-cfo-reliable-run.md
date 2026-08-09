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

- [ ] RED: assert immutable table, unique owner/date, non-zero UUID, IANA-zone text bounds, RLS/service-role grants,
  UPDATE/DELETE trigger, exact five-key receipt, same-date retry, fixed search path, and no UID in receipt.
- [ ] GREEN: implement `lm_cfo_daily_runs` and
  `lm_claim_cfo_daily_run(text,date,text) => jsonb`. `ON CONFLICT DO NOTHING`, then return the existing row. Stored
  timezone wins on retry; no UPDATE branch.
- [ ] Verify focused test, `npm run test:cfo`, LOC, privacy scan, `git diff --check`.
- [ ] Commit/push `feat(cfo): claim stable daily runs`; write the ignored Task 1 report.

### Task 2: Owner timezone and run-context client

**Files:**
- Create `apps/life-call/lib/cfo-daily-run.js`
- Create `apps/life-call/lib/cfo-daily-run.test.js`
- Modify `apps/life-call/package.json`

**Interface:** `resolveCfoDailyRun({ uid, nowMs }, { supaUrl, supaKey, fetchImpl })`.

- [ ] RED: exact input, one scoped preference GET, valid IANA zone, Tokyo/DST/date-boundary fixtures, one claim RPC,
  closed frozen five-key receipt, response echoes, Proxy/accessor/custom errors, no retry/log/leakage.
- [ ] GREEN: copy and narrow the proven `Intl.DateTimeFormat(...).formatToParts()` date logic; fail closed on missing
  or invalid preference; call only `lm_claim_cfo_daily_run`.
- [ ] Verify focused/CFO tests, production ≤100 LOC, tests ≤180 LOC, diff check.
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
- [ ] Verify focused/CFO tests, SQL ≤180 LOC or document the indivisible transaction reason, diff check.
- [ ] Commit/push `feat(cfo): add telegram delivery ledger`; write report and obtain fresh Sol review.

### Task 4: Real PostgreSQL concurrency and permission proof

**Files:**
- Create `apps/life-call/test/postgres/cfo-reliable-run-postgres.integration.sh`
- Modify `apps/life-call/package.json`

- [ ] RED then GREEN in isolated local PostgreSQL 18 or ephemeral `postgres:18-alpine` only.
- [ ] Prove: concurrent run claims one row/run; concurrent delivery claims one `send`; unreceipted retry=`reconcile`;
  receipt makes retry=`sent`; exact receipt retry; changed ID conflict; composite cross-tenant/date/revision rejection;
  direct invalid rows; role denials; UPDATE/DELETE trigger rejection; tenant separation.
- [ ] Final stdout exactly `cfo-reliable-run-postgres: PASS`; run CFO tests and diff check.
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
- [ ] Verify focused/CFO tests, production ≤130 LOC, tests ≤200 LOC, diff check.
- [ ] Commit/push `feat(cfo): persist telegram delivery receipts`; write report and obtain fresh Sol review.

### Task 6: Live migration, no-send E2E, and closure

**Files:**
- Modify parent/design/plan docs only after evidence is complete.

- [ ] Luna runs dependency-clean focused/CFO/PostgreSQL/full tests.
- [ ] Luna applies both additive migrations once and reloads PostgREST schema without outputting private values.
- [ ] Luna uses the existing live CFO snapshot to prove: owner timezone resolved, daily run stable across retry, one
  synthetic delivery claim returns `send`, second returns `reconcile`, synthetic provider receipt records once, third
  returns `sent`, and database claim/receipt counts are one. It does not call Telegram.
- [ ] Fresh Sol final review returns no Critical/Important findings.
- [ ] Sol marks `CFO-1g2 COMPLETE — CFO-1g3 NEXT`, records boolean/count evidence, commits/pushes
  `docs(cfo): close reliable daily run`, and sends a separate development milestone notification.

## Completion boundary

CFO-1g2 closes only after live stable-run and no-send delivery-dedupe proof. The first real Telegram financial report
remains 7/7; no development milestone may be described as that report.
