# REPORT-1 Shared Financial Rollup Implementation Plan

> Execute in order with RED → GREEN tests. Do not mark REPORT-1 done until the
> panel and Telegram receipts can be recomputed from the same persisted rows.

**Goal:** `done="daily/weekly Telegram と authenticated panel が同じ
lm_agent_earnings + lm_api_cost + Base balance snapshot を表示し、同一 period
の数値差が 0、7 日連続 daily と weekly 1 通の provider receipt が残る"`

**Architecture:** Keep `lm_agent_earnings` as the append-only money SSOT. Add a
tenant-to-agent-wallet binding on `lm_users`, then build one pure
`financial-report-snapshot` projection. The panel and the report runner call the
same projection; neither owns arithmetic. A receipt table deduplicates scheduled
delivery by `(uid, report_kind, period_key)`.

**Truth rules**

| Field | Source | Rule |
|---|---|---|
| balance | Base USDC `balanceOf(agent_wallet)` | A failed chain read makes the snapshot unavailable; never substitute zero |
| gross | `financial_external_income` | seed/deposit/internal/unverified rows remain excluded |
| trading/rail cost | realized loss + financial fee | integer USD minor units |
| compute/API cost | `lm_api_cost.est_usd` | convert to integer USD micros; never binary-float-sum |
| operating net | gross − realized loss − fee − API cost | negative values remain negative |
| distributable | payout policy over all-time verified rows, accrued API cost, measured balance, and $35 reserve | user transfer is distribution, not revenue |
| self-funded ratio | positive verified net / measured API+compute cost | `null` when the denominator is unmeasured/zero and net is positive; `0%` is valid when net is non-positive |
| stop reason | explicit deterministic snapshot state | `negative_net`, `no_external_income`, `reserve_floor`, or `running` |

**Scheduling:** A five-minute launchd tick checks the user timezone. Daily is due
after 20:00 local time; weekly is due Sunday after 20:05. Notification opt-out is
honoured. The runner claims a unique receipt before calling Telegram and records
the returned provider message id after success.

**External precedents**

- Telegram Bot API, https://core.telegram.org/bots/api#sendmessage — “On
  success, the sent Message is returned.” The provider message id is therefore
  persisted as the delivery receipt.
- PostgreSQL Constraints,
  https://www.postgresql.org/docs/current/ddl-constraints.html — “Adding a
  unique constraint will automatically create a unique B-tree index.” The
  period dedup is enforced in PostgreSQL, not process memory.
- Supabase Row Level Security,
  https://supabase.com/docs/guides/database/postgres/row-level-security —
  “RLS must always be enabled on any tables stored in an exposed schema.” The
  new receipt table is service-role only and RLS-enabled.

## Task 1: Pure shared snapshot

**Files**

- Create: `apps/life-manager/lib/financial-report-snapshot.js`
- Create: `apps/life-manager/lib/financial-report-snapshot.test.js`
- Modify: `apps/life-manager/lib/payout-policy.js`
- Modify: `apps/life-manager/lib/payout-policy.test.js`

Write failing tests for timezone half-open periods, seed exclusion, exact
micro-dollar cost arithmetic, negative net, rail grouping, self-funded
honesty, and payout/API-cost alignment. Implement only enough to pass.

## Task 2: Tenant binding and receipt schema

**Files**

- Create: `apps/life-manager/migrations/2026-07-27-lm-financial-reports.sql`
- Create: `apps/life-manager/lib/financial-report-migration.test.js`

Add nullable `lm_users.agent_wallet_address`, a unique partial index, and
`lm_financial_report_receipts` with a unique period key, RLS, service-role
grants, and no public access.

## Task 3: Runtime readers and Telegram delivery

**Files**

- Create: `apps/life-manager/lib/financial-report-runtime.js`
- Create: `apps/life-manager/lib/financial-report-runtime.test.js`
- Create: `apps/life-manager/scripts/run-financial-reports.js`
- Create: `apps/life-manager/scripts/run-financial-reports.test.js`

Read the tenant binding, preferences, ledger rows, cost rows, and Base balance.
Build daily and weekly snapshots through the pure module. Render factual
messages, claim the period receipt, send through the existing Telegram adapter,
and persist the provider id.

## Task 4: Panel connection

**Files**

- Modify: `apps/life-manager/lib/panel-api.js`
- Modify: `apps/life-manager/lib/panel-api.test.js`
- Modify: `apps/life-manager/lib/panel-presentation.js`
- Modify: `apps/life-manager/lib/panel-ui.js`
- Modify: corresponding panel tests

Replace the nonexistent `lm_financial_ledger` read with the real wallet-bound
ledger and shared daily/weekly snapshots. Keep raw evidence rows and add the
same snapshot ids and integer values rendered by Telegram.

## Task 5: launchd and installation

**Files**

- Create: `apps/life-manager/launchd/ai.anicca.life-manager-financial-report.plist.template`
- Create: `apps/life-manager/scripts/financial-report-boot.sh`
- Create: `apps/life-manager/scripts/install-financial-report-launchd.sh`
- Add launchd contract tests

Install one bounded five-minute tick. No second executor and no in-memory
schedule authority.

## Task 6: Verification and production alignment

Run focused tests, the existing FIN/panel suite, full Life Manager tests, and
changed-path secret scans. Apply the additive migration, bind the production
tenant to the existing public agent wallet, install/kickstart the launchd job,
read back the first real Telegram provider receipt and authenticated panel
snapshot, and compare canonical integer fields.

## Task 7: Evidence and SSOT

Create bounded evidence under `docs/evidence/agent-economy/`, update the §0.4.6
cursor and REPORT-1 row honestly. A first daily/weekly receipt starts the
cadence; only seven distinct daily period keys plus one weekly receipt close
REPORT-1.
