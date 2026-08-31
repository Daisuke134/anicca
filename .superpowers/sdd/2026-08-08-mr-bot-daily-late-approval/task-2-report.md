# Task 2 report — Durable Late Approval State Machine

STATUS: DONE

## Scope

Only the assigned files changed:

- `apps/mr-bot/lib/late-approval.js`
- `apps/mr-bot/lib/late-approval.test.js`
- `apps/mr-bot/migrations/2026-08-08-lm-late-approval.sql`
- this append-only report

The implementation keeps the mail transport out of this slice. `late-notice.js` still has its
pre-existing direct-send path; removing that path is Task 3 and was not changed here.

## RED

The required test file was written before the production module and the focused command was run:

```text
cd apps/mr-bot && node --test lib/late-approval.test.js
```

Exact initial failure:

```text
Error: Cannot find module './late-approval.js'
Require stack:
- .../apps/mr-bot/lib/late-approval.test.js
ℹ tests 1
ℹ pass 0
ℹ fail 1
```

This was the intended missing-module RED, not a syntax or assertion failure.

## GREEN

Focused state/migration suite:

```text
cd apps/mr-bot && node --test lib/late-approval.test.js
```

Result: **8 tests, 8 pass, 0 fail**.

Relevant regression suite:

```text
cd apps/mr-bot && node --test lib/late-approval.test.js lib/late-recipient-resolver.test.js lib/late-notice.test.js
```

Result: **47 tests, 47 pass, 0 fail**.

Additional checks:

```text
cd apps/mr-bot && node --check lib/late-approval.js
cd apps/mr-bot && node --check lib/late-approval.test.js
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
psql apps/mr-bot/migrations/2026-08-08-lm-late-approval.sql
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
cd apps/mr-bot && npm test
```

The suite stopped before completion with the existing environment dependency failure:

```text
Error: Cannot find module 'viem'
Require stack:
- .../apps/mr-bot/lib/base-usdc-payout.js
- .../apps/mr-bot/lib/taskmarket-award-handoff.js
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

- Implementation commit: `35d9cb35b` — `feat(mr-bot): add durable late approval state machine`.
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

## Post-commit receipt

- The report body was committed and pushed as `5c46a565c`; this append-only receipt is the final
  report amendment for the task.

## Review-fix addendum (2026-08-08)

The review identified three contract defects and one validation gap: SECURITY DEFINER RPCs still
had PostgreSQL's default PUBLIC execute privilege, receipt recording did not require tenant/current
claim identity, recovery claims did not carry a stable provider idempotency key, and the isolated
staging target had no Supabase-compatible roles. The following evidence is the strict regression
cycle for those fixes. The earlier report counts above describe the pre-review implementation;
these addendum counts supersede them for the final state.

### Review-fix RED

Tests were changed first, while the pre-fix implementation and migration remained untouched:

```text
cd apps/mr-bot && node --test lib/late-approval.test.js
```

Exact result: **9 tests, 6 pass, 3 fail**. The three expected failures were:

```text
The input did not match /provider_idempotency_key\s+text\s+NOT NULL/i
The "string" argument must be of type string. Received type undefined
Missing expected rejection.
```

The first was the missing migration key/privilege contract, the second was the missing stable key
on a created draft, and the third showed that a receipt without the new required identity was
accepted by the old in-memory transition.

### Review-fix GREEN

Focused state-machine suite after the minimal JS/SQL changes:

```text
cd apps/mr-bot && node --test lib/late-approval.test.js
```

Result: **9 tests, 9 pass, 0 fail**.

Required regression suite:

```text
cd apps/mr-bot && node --test lib/late-approval.test.js lib/late-recipient-resolver.test.js lib/late-notice.test.js
```

Result: **48 tests, 48 pass, 0 fail**.

Syntax and full-range whitespace checks:

```text
cd apps/mr-bot && node --check lib/late-approval.js
cd apps/mr-bot && node --check lib/late-approval.test.js
git diff --check
```

All exited 0. The public receipt interface now requires `uid`, `claimToken`, and `workerId`; the
transition rejects missing identity, wrong uid, wrong token, wrong worker, and an old token after
lease recovery. Draft creation generates a 64-hex-character value from `randomBytes(32)`, exposes
it as `providerIdempotencyKey`, and claim recovery preserves it. The SQL record RPC has the exact
six-argument identity-bound signature and locks by `draft_id AND uid`.

### Isolated staging role and migration evidence

The shared Supabase URL was not used. Every Railway command asserted these exact IDs before opening
`DATABASE_PUBLIC_URL`:

```text
project     f9c524cb-ba4a-43bb-9639-ff736afd9ec1
environment 0437b714-7f05-44d7-9c46-9409-a6e3a99c
service     a8a0a844-4cde-4a86-8902-63fc2ad58cf8 (Postgres)
```

The role preflight created or enforced `NOLOGIN` for `anon`, `authenticated`, and `service_role`.
Read-back was:

```text
    rolname    | rolcanlogin
---------------+-------------
 anon          | f
 authenticated | f
 service_role  | f
```

The migration was then reapplied to that isolated database with the same three-ID guard and
`psql "$DATABASE_PUBLIC_URL" -v ON_ERROR_STOP=1 -X -f -` fed from
`apps/mr-bot/migrations/2026-08-08-lm-late-approval.sql`; it exited 0. The rerun reported
expected `already exists, skipping` notices for prior relations, and completed `ALTER TABLE`,
`CREATE FUNCTION`, `REVOKE`, and conditional service-role grant statements successfully. No
production Railway environment and no Supabase endpoint was contacted.

Schema and RPC read-back from the isolated database:

- `provider_idempotency_key` is `text NOT NULL DEFAULT encode(gen_random_bytes(32), 'hex')` and
  has a unique index; the key format is 64 lowercase hex characters.
- The record RPC identity is
  `p_uid text, p_draft_id text, p_provider_message_id text, p_delivered_at timestamp with time zone,
  p_claim_token text, p_worker_id text`.
- All four transition RPCs have `prosecdef=t` and
  `proconfig={"search_path=public, pg_temp"}`. The record definition read-back contains
  `WHERE draft_id = p_draft_id AND uid = p_uid FOR UPDATE`.
- The four LM tables have `relrowsecurity=t` and `relforcerowsecurity=t`; no application role has a
  direct table grant (`information_schema.role_table_grants` returned 0 rows).
- Function privilege matrix was 12 rows: `create`, `decide`, `claim`, and `record` were each
  `anon=false`, `authenticated=false`, `service_role=true`.
- Each function ACL read back as
  `{postgres=X/postgres,service_role=X/postgres}` with no PUBLIC `=X` entry. The SQL migration
  unconditionally revokes exact function signatures from `PUBLIC, anon, authenticated` and
  conditionally grants `EXECUTE` only to `service_role`.

Actual role calls matched the matrix. Each of these eight calls exited `rc=1` with permission
denied, and none changed state:

```text
anon create rejected (rc=1)
anon decide rejected (rc=1)
anon claim rejected (rc=1)
anon record rejected (rc=1)
authenticated create rejected (rc=1)
authenticated decide rejected (rc=1)
authenticated claim rejected (rc=1)
authenticated record rejected (rc=1)
```

With `SET LOCAL ROLE service_role`, a transaction executed and then rolled back all four required
transitions. Exact read-back notice:

```text
staging transitions: awaiting_decision -> send_claimed -> sent; stable provider key=<derived-key-redacted>; duplicate receipt=true
```

A second transaction used a one-second lease and recovery worker. It proved the first token was
rejected after recovery, wrong uid and worker were rejected, NULL uid/token/worker were rejected,
the provider key remained stable, and the recovered worker could record the receipt:

```text
staging recovery: old token rejected, wrong uid/worker rejected, required identity enforced, stable provider key=<derived-key-redacted>
```

These are isolated PostgreSQL role/SQL validations, not staging app/PostgREST E2E: the isolated
Railway service has no Mr.bot app credentials or Supabase PostgREST topology. The plan's
staging wording should be narrowed by the controller to this honest validation boundary; the plan
file was not edited by this task.

### Review-fix mutation reasoning and self-review

- Removing `REVOKE ... FROM PUBLIC, anon, authenticated` restores the default ACL and is caught by
  the migration contract test plus the isolated `proacl`/role-call matrix.
- Making uid/token/worker optional lets a draft ID alone reach `sent`; the RED receipt test,
  required-input checks, SQL tenant predicate, and recovery probes catch that mutation.
- Generating the provider key per claim instead of per draft changes it across recovery; the
  recovery test and both staging notices catch that mutation.
- Removing the unique receipt constraints still permits a second provider id or draft receipt;
  existing receipt conflict/idempotency tests and schema read-back retain both uniqueness guards.
- The provider key is surfaced on the claim row for the callback-owned provider call in the later
  transport slice; this Task 2 module still performs no mail, Telegram, or provider I/O.

The known full-suite dependency failure remains outside the owned files (`viem` is missing through
`base-usdc-payout.js`); no unrelated dependency or Task 3 file was changed. No Telegram was sent.

### Review-fix commits

- Code/test/migration fix: `7a6b07bf8` — `fix(mr-bot): close late approval delivery boundaries`.
- Report addendum commit: `ff9413b89` — `docs(mr-bot): record late approval review fixes`.

### Review-fix push receipt

After the required fetch, the Task 2 branch was pushed successfully:

```text
git fetch canonical
git push canonical HEAD:feat/lm-daily-late-approval
dc91d9e96..ff9413b89  HEAD -> feat/lm-daily-late-approval
remote: ff9413b890937b79199acda66a74f2bd72f32b2d refs/heads/feat/lm-daily-late-approval
```

The only remaining worktree modifications are another agent's uncommitted Task 3 files
`apps/mr-bot/lib/late-notice.js` and `apps/mr-bot/lib/late-notice.test.js`; they were
not staged, committed, reverted, or otherwise touched by this task.

The receipt append itself was the report-only commit `4f7248b9a` and was pushed after a fresh
`git fetch canonical`; the final remote verification returned
`4f7248b9acade169a73aa23846ff3591bc2929c9` for `feat/lm-daily-late-approval`.
