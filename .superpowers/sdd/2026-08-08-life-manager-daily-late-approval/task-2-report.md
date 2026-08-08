# Task 2 report — Durable Late Approval State Machine

STATUS: DONE

## Scope

Only the assigned files changed:

- `apps/life-manager/lib/late-approval.js`
- `apps/life-manager/lib/late-approval.test.js`
- `apps/life-manager/migrations/2026-08-08-lm-late-approval.sql`
- this append-only report

The implementation keeps the mail transport out of this slice. `late-notice.js` still has its
pre-existing direct-send path; removing that path is Task 3 and was not changed here.

## RED

The required test file was written before the production module and the focused command was run:

```text
cd apps/life-manager && node --test lib/late-approval.test.js
```

Exact initial failure:

```text
Error: Cannot find module './late-approval.js'
Require stack:
- .../apps/life-manager/lib/late-approval.test.js
ℹ tests 1
ℹ pass 0
ℹ fail 1
```

This was the intended missing-module RED, not a syntax or assertion failure.

## GREEN

Focused state/migration suite:

```text
cd apps/life-manager && node --test lib/late-approval.test.js
```

Result: **8 tests, 8 pass, 0 fail**.

Relevant regression suite:

```text
cd apps/life-manager && node --test lib/late-approval.test.js lib/late-recipient-resolver.test.js lib/late-notice.test.js
```

Result: **47 tests, 47 pass, 0 fail**.

Additional checks:

```text
cd apps/life-manager && node --check lib/late-approval.js
cd apps/life-manager && node --check lib/late-approval.test.js
git diff --check
```

All exited 0. The focused tests cover immutable snapshots and `(uid,event_key)` idempotency,
double-tap send, conflicting decisions, permanent `do_not_send`, missing/ambiguous recipients,
two workers, same-worker interruption retry, expired-claim takeover, provider receipt idempotency,
and Supabase RPC failure propagation.

## State-machine implementation

- `createLateDraft` deep-copies recipient/evidence/body/ETA snapshots. A resolved row is
  `awaiting_decision`; missing and ambiguous rows are terminal and have no sendable decision.
- `decideLateDraft` records exactly one terminal decision. A duplicate same decision returns the
  original row; a conflicting decision raises `decision_conflict`.
- `claimApprovedDelivery` is the only transition into `send_claimed`. One active worker owns the
  claim token; the same worker may retry, and an expired lease can be recovered by another worker.
- `recordLateDelivery` is the only transition into `sent`. A provider receipt is immutable and a
  repeated same provider id returns the original row; a different id is rejected.
- `createSupabaseLateApprovalStore` calls only the four SECURITY DEFINER RPCs. No mail, Telegram, or
  provider transport is imported or invoked by this module.

## Staging migration apply and read-back

Production Supabase was deliberately not touched. The life-call staging and production apps share
`cycgdwndgfgdbnndithc.supabase.co`, so using the app's Supabase credentials would mutate production.
The isolated schema-only target was guarded in every command with all three IDs:

```text
project     f9c524cb-ba4a-43bb-9639-ff736afd9ec1
environment 0437b714-7f05-44d7-9c46-9409a6e3a99c
service     a8a0a844-4cde-4a86-8902-63fc2ad58cf8 (Postgres)
```

The first guarded attempt used the private `DATABASE_URL` and failed honestly because the local
runner cannot resolve Railway's private host:

```text
psql: error: could not translate host name "postgres.railway.internal" to address:
nodename nor servname provided, or not known
```

The safe alternative `DATABASE_PUBLIC_URL`, with the same three-ID guard, applied successfully:

```text
psql apps/life-manager/migrations/2026-08-08-lm-late-approval.sql
exit_code=0
```

The migration was re-applied after the recovery-flag/RLS correction and remained idempotent:
`CREATE TABLE`/`CREATE FUNCTION`/`ALTER TABLE`/`DO`, exit 0; existing relations were reported as
`already exists, skipping` where expected.

Schema/RPC read-back from that isolated database:

- 4 tables: `lm_late_approval_drafts`, `lm_late_approval_decisions`,
  `lm_late_approval_claims`, `lm_late_approval_receipts`.
- Draft columns include `uid`, `event_key`, `recipient_snapshot`, `evidence_snapshot`,
  `body_snapshot`, `eta_evidence_snapshot`, `decision`, `claim_token`, `claim_worker_id`,
  `claim_expires_at`, `provider_message_id`, and `delivered_at`.
- Constraint read-back includes `lm_late_approval_drafts_uid_event_key_key`, decision/status
  checks, and receipt/claim uniqueness constraints.
- 3 append-only/snapshot triggers were present on the decisions, claims, and receipts ledgers plus
  the immutable draft snapshot guard.
- RPC read-back found exactly 4 transition functions. Each had `prosecdef=t`,
  `proconfig={"search_path=public, pg_temp"}`, and `FOR UPDATE` in its definition.
- All four late-approval tables read back `relrowsecurity=t` and `relforcerowsecurity=t`.
- The isolated Postgres has no Supabase roles or existing LM tables; therefore this was schema-only
  validation, not staging app E2E. The role-conditional grants keep the migration portable without
  pretending that this database is the production Supabase topology.

Behavior read-back ran in transactions and rolled every probe back:

```text
resolved create       -> awaiting_decision
same send retry       -> duplicate=true
worker A claim        -> claimed=true
worker B claim        -> reason=claimed_by_other_worker
provider receipt      -> sent
same receipt retry    -> duplicate=true
expired lease retry   -> recovered=true; new worker owns send_claimed
missing recipient     -> recipient_missing; claim reason=recipient_missing
snapshot update       -> NOTICE snapshot_guard=PASS; stored body remained "Immutable body"
post-rollback rows    -> 0
```

No Supabase URL, production Railway environment, mail provider, Telegram provider, or real user data
was used by the staging probes.

## Full-suite result / concerns

```text
cd apps/life-manager && npm test
```

The suite stopped before completion with the existing environment dependency failure:

```text
Error: Cannot find module 'viem'
Require stack:
- .../apps/life-manager/lib/base-usdc-payout.js
- .../apps/life-manager/lib/taskmarket-award-handoff.js
```

The failure is outside the four assigned files; the focused 47/47 suite and all syntax/diff checks
are green. No dependency installation or unrelated file change was made to hide the baseline issue.

## Mutation reasoning

- Removing the unique `(uid,event_key)` gate or snapshot collision check makes the duplicate-draft
  test create/reuse the wrong row.
- Removing deep-copy/immutable snapshot protection lets a caller mutate evidence/body after card
  creation; the snapshot test and staging trigger probe catch that.
- Letting a second decision overwrite the first breaks the double-tap/conflicting-decision tests.
- Letting a second active worker claim breaks the two-worker test; removing lease recovery breaks the
  interruption/takeover test.
- Recording a provider id before `send_claimed`, or accepting a different provider id after `sent`,
  breaks the receipt state/duplicate-receipt tests.
- Returning a sendable claim for `recipient_missing` or `recipient_ambiguous` breaks the permanent
  no-send test and the SQL status checks.
- Removing the SQL `FOR UPDATE` row locks would permit concurrent RPC decisions/claims to race;
  the migration structure test and the staging function read-back pin that boundary.

## Commit and push

- Implementation commit: `35d9cb35b` — `feat(life-manager): add durable late approval state machine`.
- Push: **PASS** — `canonical/feat/lm-daily-late-approval` advanced from `7f6cdca6a` to
  `35d9cb35b`.
- Report commit: created immediately after this report and pushed to the same branch; the exact
  report commit is recorded in the task handoff (`git log -2` on the branch).

## Self-review

The assigned surface now has a durable approval ledger, no transport dependency, one decision
winner, one active delivery claimant, recovery after interruption, permanent no-send, immutable
evidence/body snapshots, and provider receipt persistence. The only intentionally remaining safety
gap is the old tick-time direct send in `late-notice.js`; Task 3 owns its removal and this task did
not touch that file.
