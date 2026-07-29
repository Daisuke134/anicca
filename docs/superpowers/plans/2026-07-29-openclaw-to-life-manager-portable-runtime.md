# OpenClaw to Life Manager Portable Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move every retained OpenClaw, launchd, Profitable Claude, and legacy-repository loop into one Life Manager runtime, prove it locally with OpenClaw unavailable, then run the same release as a monthly-subscription multi-tenant cloud service.

**Architecture:** A provider-neutral job protocol separates schedules, loop business logic, external effects, and deployment. Local mode runs the API, scheduler, PostgreSQL, object store, and workers through one self-hosted bundle; cloud mode runs the same release contracts with managed adapters and tenant isolation. Exactly one deployment owns a tenant's scheduler lease, and every external effect is idempotent and reconciled before retry.

**Tech Stack:** Node.js 20.19+, PostgreSQL, existing Life Manager scheduler and Inngest functions, Docker Compose, Railway, Stripe Billing, Telegram Bot API, macOS launchd only as a temporary local boot mechanism.

## Global Constraints

- Canonical repository is `Daisuke134/life-manager`, repository ID `1248111245`.
- Local migration completes before cloud migration begins.
- No retained runtime may read or execute from `~/.openclaw`, `/Users/anicca/profitable-claude`, `/Users/anicca/anicca`, or `life-manager-v0`.
- Local and cloud use the same source, schemas, job protocol, and release hash.
- One scheduler-owner lease prevents local/cloud or OpenClaw/Life Manager double execution.
- Unknown external-effect results are reconciled before retry; blind repost, resend, or repay is forbidden.
- Cloud access requires a monthly Stripe entitlement; local self-hosting does not require the managed-cloud subscription.
- No numeric subscription price is introduced by this plan.
- No legacy scheduler is disabled until its replacement has real non-dry receipts and a signed rollback record.

---

### Task 1: Freeze the complete runtime inventory

**Files:**
- Modify: `skills/self/openclaw-migrate/migration_gate.py`
- Modify: `skills/self/openclaw-migrate/tests/test_migration_gate.py`
- Create: `apps/life-manager/scripts/inventory-legacy-jobs.js`
- Create: `apps/life-manager/scripts/inventory-legacy-jobs.test.js`
- Create: `docs/migrations/openclaw/runtime-inventory.json`

**Interfaces:**
- Consumes: OpenClaw cron JSON export, `~/Library/LaunchAgents/*.plist`, canonical repository root, known legacy roots.
- Produces: `inventoryLegacyJobs({ cronRows, launchAgents, loadedLabels }) -> { jobs, summary }`, where each job has `legacy_id`, `scheduler`, redacted `command`, `command_fingerprint`, `source_boundary`, `cadence`, `enabled`, `loaded`, `latest_receipt`, and initially unclassified migration fields.
- Privacy: committed inventory replaces usernames, emails, chat/phone identifiers, connector account IDs, tokens, keys, passwords, and secret URL query parameters with non-reversible redaction markers.

- [x] **Step 1: Extend the migration-gate test**

Add cases proving that only `migrate`, `replace`, and `retire` are valid final dispositions and that a final disposition requires owner, effect class, verification command, and rollback action. The inventory stage may emit `unclassified`; every retained row must be classified before Task 6 migrates its scheduler ownership. Task 2 does not mutate schedulers.

- [x] **Step 2: Run the focused tests and verify RED**

Run:

```bash
python3 skills/self/openclaw-migrate/tests/test_migration_gate.py
node --test apps/life-manager/scripts/inventory-legacy-jobs.test.js
```

Expected: the Python test fails on the new disposition API and Node reports the inventory module is missing.

- [x] **Step 3: Implement inventory normalization and validation**

Implement pure normalization in `inventory-legacy-jobs.js`; keep plist reading and OpenClaw export capture in the CLI entrypoint. Historical jobs remain present even when disabled so the manifest is auditable.

- [x] **Step 4: Capture the real machine inventory**

Run the new script against the actual cron export and LaunchAgents directory. Preserve enabled, disabled, loaded, and unloaded rows. Record the exact `unclassified` count as the input to Task 2; do not guess a disposition and do not mutate a scheduler.

- [x] **Step 5: Verify GREEN and commit**

Run both focused tests, validate `runtime-inventory.json` with `jq empty`, scan the committed file for unredacted private identifiers, then commit only the scoped files.

### Task 2: Establish Life Manager-owned runtime paths and secrets

**Files:**
- Create: `apps/life-manager/lib/runtime-paths.js`
- Create: `apps/life-manager/lib/runtime-paths.test.js`
- Create: `apps/life-manager/lib/secret-provider.js`
- Create: `apps/life-manager/lib/secret-provider.test.js`
- Create: `apps/life-manager/.env.example`

**Interfaces:**
- Consumes: `LM_MODE=local|cloud`, `LM_DATA_DIR`, `LM_CACHE_DIR`, local keychain adapter, cloud vault adapter.
- Produces: `resolveRuntimePaths(env) -> { dataDir, cacheDir, objectDir, receiptDir, logDir }` and `createSecretProvider({ mode, keychain, vault }) -> { get(tenantId, ref), health() }`.

- [x] **Step 1: Write path-denial tests**

Tests must reject resolved paths beneath `.openclaw`, `profitable-claude`, `anicca`, or `life-manager-v0`; relative paths and an unset mode also fail closed.

- [x] **Step 2: Write secret-boundary tests**

Assert that job payloads contain secret references only, local mode delegates to keychain, cloud mode delegates to the tenant vault, and neither provider logs secret values.

- [x] **Step 3: Run tests and verify RED**

```bash
cd apps/life-manager
node --test lib/runtime-paths.test.js lib/secret-provider.test.js
```

- [x] **Step 4: Implement the minimal providers**

Do not import legacy `.env` files. Existing environment variables may be used only by a one-time migration command that writes references into the new provider.

- [x] **Step 5: Run GREEN, scan dependencies, and commit**

Run the two tests plus:

```bash
rg -n '(require|import|readFile|writeFile|exec|spawn).*(\.openclaw|profitable-claude|/Users/[^/]+/anicca|life-manager-v0)' \
  apps/life-manager/lib/runtime-paths.js apps/life-manager/lib/secret-provider.js
```

Expected: no runtime dependency match. Legacy names may appear only in
`runtime-paths.js` deny-list validation and its behavior tests.

### Task 3: Add the durable generic job and receipt protocol

**Files:**
- Create: `apps/life-manager/migrations/20260729_runtime_jobs.sql`
- Create: `apps/life-manager/lib/runtime-job-store.js`
- Create: `apps/life-manager/lib/runtime-job-store.test.js`
- Create: `apps/life-manager/lib/effect-reconciler.js`
- Create: `apps/life-manager/lib/effect-reconciler.test.js`
- Create: `apps/life-manager/test/postgres/runtime-job-protocol.integration.sh`
- Modify: `apps/life-manager/package.json`

**Interfaces:**
- Consumes: PostgreSQL client and jobs containing `job_id`, `tenant_id`, `loop_id`, `capability`, `effect_class`, `input_refs`, `max_attempts`.
- Produces: `enqueueJob`, `claimJobs`, `heartbeatJob`, `completeJob`, `failJob`, `reconcileUnknownEffect`, and immutable receipt rows keyed by `job_id + attempt`.

- [x] **Step 1: Write contract tests**

Cover idempotent enqueue, capability filtering, lease expiry, one claimant, bounded retry, dead-letter, tenant scoping, immutable receipts, and unknown-effect reconciliation.

- [x] **Step 2: Run tests and verify RED**

```bash
cd apps/life-manager
node --test lib/runtime-job-store.test.js lib/effect-reconciler.test.js
```

- [x] **Step 3: Add the SQL schema**

Use unique constraints for `job_id` and external-effect idempotency keys. Claims use one atomic `UPDATE ... WHERE ... RETURNING`; do not use PostgreSQL advisory locks through a connection pool.

- [x] **Step 4: Implement store and reconciler**

`publish`, `message`, and `money` effects enter `reconciling` after an unknown response. They may retry only when the adapter proves the first attempt did not occur.

- [x] **Step 5: Verify restart semantics and commit**

Run the focused tests twice against the same temporary database and prove the second pass creates no duplicate receipt or effect.

**Verification:** focused contract suite passed twice (`9/9` each);
the disposable PostgreSQL 18 gate passed two idempotent enqueue passes plus
tenant isolation, one-claimant concurrency, non-effect lease recovery,
bounded retry/dead-letter, external-effect quarantine/reconciliation, and
receipt immutability. A regression test first exposed and then closed the
commit-acknowledgement gap: repeating the same provider proof now returns the
same receipt outcome without creating another receipt. The complete
`apps/life-manager` test command passed with the new suite wired into `npm test`.

**Implementation basis:**
- [PostgreSQL `SELECT`](https://www.postgresql.org/docs/current/sql-select.html):
  “SKIP LOCKED” can avoid lock contention for multiple consumers of a
  queue-like table.
- [PostgreSQL `INSERT`](https://www.postgresql.org/docs/current/sql-insert.html):
  `ON CONFLICT DO UPDATE` guarantees an atomic insert-or-update outcome under
  concurrency.
- [PostgreSQL `RETURNING`](https://www.postgresql.org/docs/current/dml-returning.html):
  `RETURNING` avoids a second query to identify modified rows reliably.

### Task 4: Build the reproducible local deployment

**Files:**
- Create: `deploy/local/compose.yaml`
- Create: `deploy/local/.env.example`
- Create: `apps/life-manager/Dockerfile.runtime`
- Create: `apps/life-manager/.dockerignore`
- Create: `apps/life-manager/migrations/20260729_runtime_scheduler_lease.sql`
- Create: `apps/life-manager/scripts/runtime-up.js`
- Create: `apps/life-manager/scripts/runtime-up.test.js`
- Modify: `apps/life-manager/lib/maybe-start-loops.js`
- Modify: `apps/life-manager/lib/maybe-start-loops.test.js`
- Modify: `apps/life-manager/package.json`
- Modify: `apps/life-manager/package-lock.json`

**Interfaces:**
- Consumes: one Life Manager release and local runtime configuration.
- Produces: `life-manager runtime up --mode local`, starting API/panel, scheduler, PostgreSQL, object storage, and capability workers with a single scheduler owner.

- [x] **Step 1: Write topology and single-writer tests**

Assert that the Compose model contains health checks, persistent database/object volumes, distinct scheduler and worker services, and one scheduler-owner identity.

- [x] **Step 2: Run tests and verify RED**

```bash
cd apps/life-manager
node --test scripts/runtime-up.test.js lib/maybe-start-loops.test.js
```

- [x] **Step 3: Implement the local bundle**

Replace the existing OpenClaw-owner wording in `maybe-start-loops.js` with deployment-owner semantics. OpenClaw is not a supported owner or fallback.

- [x] **Step 4: Start the real local stack**

```bash
docker compose -f deploy/local/compose.yaml up -d --build
docker compose -f deploy/local/compose.yaml ps
```

Expected: all required services report healthy and the scheduler has exactly one owner lease.

- [x] **Step 5: Restart verification and commit**

Restart scheduler and workers during queued work; verify leases recover and no duplicate external effect is emitted.

**Verification:** the focused topology/single-writer suite passed `17/17`.
The rendered Compose JSON had one scheduler service with owner
`local-primary`, one capability worker, health checks, and three persistent
volumes. The real Colima/Docker stack built and brought PostgreSQL 18, the
migration job, MinIO, API/panel, scheduler, and worker up without any legacy
directory mounted. API, PostgreSQL, MinIO, scheduler, and worker reported
healthy. Restarting worker and scheduler changed the process-unique scheduler
holder token while the active database lease remained exactly
`1:local-primary:true`. A no-effect smoke job remained `completed:1:1`; an
unknown external-effect job remained `reconciling:1:0` across restart, proving
no blind retry and no duplicate receipt. The runtime image excludes repository
tests and legacy boot scripts. The complete `apps/life-manager` test command
passed with the Task 4 suite wired into `npm test`.

**Implementation basis:**
- [Docker Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/):
  Compose waits for dependencies marked `service_healthy`, while
  `service_completed_successfully` gates one-shot migrations.
- [Docker volumes](https://docs.docker.com/engine/storage/volumes/):
  volumes persist data beyond an individual container lifecycle.
- [Docker Compose healthcheck](https://docs.docker.com/reference/compose-file/services/#healthcheck):
  service health is declared in the Compose model and used by dependency
  conditions.

### Task 5: Move Telegram and the current financial report first

**Files:**
- Modify: `apps/life-manager/lib/telegram.js`
- Modify: `apps/life-manager/lib/financial-report-runtime.js`
- Modify: `apps/life-manager/lib/financial-report-runtime.test.js`
- Modify: `apps/life-manager/scripts/financial-report-boot.sh`
- Create: `apps/life-manager/lib/report-job-adapter.js`
- Create: `apps/life-manager/lib/report-job-adapter.test.js`

**Interfaces:**
- Consumes: tenant-scoped Telegram secret reference, existing financial snapshot inputs, runtime job.
- Produces: a Telegram effect receipt with `chat_id_hash`, `message_id`, `snapshot_hash`, `sent_at`, and explicit source freshness.

- [ ] **Step 1: Write equivalence and secret-denial tests**

Fixture the existing report inputs and assert the new adapter produces the same snapshot hash and rendered body without reading `~/.openclaw/.env`.

- [ ] **Step 2: Run tests and verify RED**

```bash
cd apps/life-manager
node --test lib/report-job-adapter.test.js lib/financial-report-runtime.test.js
```

- [ ] **Step 3: Route reports through runtime jobs**

The boot script becomes a compatibility entrypoint that enqueues a Life Manager job. It must not own cadence or load secrets from a legacy path.

- [ ] **Step 4: Trigger one real local report**

Use the real local scheduler, not a substitute executor. Verify the Telegram message ID, snapshot hash, and receipt row.

- [ ] **Step 5: Commit with the real receipt reference**

### Task 6: Migrate every retained loop through adapters

**Files:**
- Create: `apps/life-manager/lib/loop-adapter-registry.js`
- Create: `apps/life-manager/lib/loop-adapter-registry.test.js`
- Create: `apps/life-manager/config/loop-adapters.json`
- Modify: canonical loop implementations under `skills/` and `apps/life-manager/`
- Update: `docs/migrations/openclaw/runtime-inventory.json`

**Interfaces:**
- Consumes: `loop_id`, tenant/product configuration, immutable input refs, secret refs.
- Produces: adapters implementing `plan(context)`, `execute(job, services)`, `reconcile(effect)`, `verify(receipt)`, and `report(receipt)`.

- [ ] **Step 1: Write registry contract tests**

Reject adapters that omit reconciliation or machine verification. Forbid product credentials and absolute user paths in registry configuration.

- [ ] **Step 2: Implement the registry**

Register the report adapter first, then migrate in this order: Life Manager daily, Larry/ReelClaw, Capafy, clipping, writer, gig, bounty, finance, then remaining retained jobs.

- [ ] **Step 3: Migrate one adapter at a time**

For each adapter: add a failing equivalence test, import only required code/assets, run a real bounded job, verify the external effect, record rollback, then change its inventory disposition to migrated.

- [ ] **Step 4: Keep legacy scheduler active until receipt parity**

After seven expected replacement runs, disable only that adapter's legacy job. Do not batch-disable unrelated jobs.

- [ ] **Step 5: Prove every retained inventory row is closed**

The inventory gate fails if any loaded/enabled job is unowned or any migrated adapter still reads a legacy root.

### Task 7: Prove OpenClaw-free local and package self-hosting

**Files:**
- Create: `apps/life-manager/scripts/verify-openclaw-free-local.sh`
- Create: `apps/life-manager/scripts/verify-openclaw-free-local.test.js`
- Create: `docs/migrations/openclaw/local-cutover-evidence.md`
- Modify: `install.sh`
- Modify: `uninstall.sh`

**Interfaces:**
- Consumes: signed scheduler inventory, local deployment, expected-run calendar.
- Produces: a seven-cycle evidence report covering expected jobs, receipts, duplicates, failures, and forbidden-path access.

- [ ] **Step 1: Write the negative dependency test**

The harness supplies an unreadable fake `.openclaw` path and no OpenClaw executable. Any attempted access fails the run.

- [ ] **Step 2: Verify RED while a known legacy dependency remains**

- [ ] **Step 3: Remove the final dependency and verify GREEN**

- [ ] **Step 4: Stop the real OpenClaw gateway**

Capture rollback state first, stop the gateway, run seven expected local cycles, and reconcile every real effect.

- [ ] **Step 5: Test clean-machine install, upgrade, backup/restore, and uninstall**

No operation may mutate or delete user-owned data outside the configured Life Manager data root.

### Task 8: Deploy the identical release to cloud

**Files:**
- Create: `deploy/railway/api.toml`
- Create: `deploy/railway/scheduler.toml`
- Create: `deploy/railway/worker.toml`
- Create: `apps/life-manager/lib/deployment-contract.test.js`
- Modify: `apps/life-manager/railway.toml`

**Interfaces:**
- Consumes: the same release image, managed PostgreSQL/object/vault adapters, deployment capability configuration.
- Produces: API/panel, scheduler, and independently scalable worker pools reporting one `release_sha`.

- [ ] **Step 1: Write local/cloud contract parity tests**

Assert identical job schema versions, adapter manifests, receipt schema, and release SHA across both deployment profiles.

- [ ] **Step 2: Run tests and verify RED**

- [ ] **Step 3: Add Railway service configuration**

Cron services enqueue bounded work and terminate; long jobs run in workers. Browser and media workers scale separately from API/report workers.

- [ ] **Step 4: Deploy the saved release and verify service health**

Verify Railway deployment commit SHA, database migrations, worker registration, and one scheduler owner.

- [ ] **Step 5: Replay duplicate-safe jobs and compare hashes**

### Task 9: Enforce multi-tenancy and monthly cloud entitlement

**Files:**
- Modify: `apps/life-manager/lib/billing.js`
- Modify: `apps/life-manager/lib/billing.test.js`
- Modify: `apps/life-manager/test/tenant-isolation.test.js`
- Create: `apps/life-manager/lib/cloud-entitlement.js`
- Create: `apps/life-manager/lib/cloud-entitlement.test.js`

**Interfaces:**
- Consumes: authenticated tenant, Stripe webhook-derived subscription state, requested worker capability.
- Produces: `authorizeCloudJob({ tenantId, capability, entitlement, quota }) -> { allowed, reason, limits }`.

- [ ] **Step 1: Write entitlement tests**

`active`, `trialing`, and documented `past_due` grace may enqueue within quota; canceled, unpaid, incomplete, missing, stale, or cross-tenant entitlement fails closed.

- [ ] **Step 2: Write noisy-neighbor tests**

One tenant exhausting browser/render quota must not block another tenant's API/report work.

- [ ] **Step 3: Implement webhook-derived authorization**

Checkout redirect state never authorizes work. Only the durable Stripe event projection used by `billing.js` changes entitlement.

- [ ] **Step 4: Verify cancellation, export, and local independence**

Cancellation stops future cloud schedules after policy grace without deleting exportable tenant data. Local mode does not call `authorizeCloudJob`.

- [ ] **Step 5: Run focused tests and commit**

```bash
cd apps/life-manager
node --test lib/billing.test.js lib/cloud-entitlement.test.js test/tenant-isolation.test.js
```

### Task 10: Shadow, canary, and cloud cutover

**Files:**
- Create: `apps/life-manager/lib/scheduler-owner-lease.js`
- Create: `apps/life-manager/lib/scheduler-owner-lease.test.js`
- Create: `apps/life-manager/scripts/reconcile-local-cloud.js`
- Create: `apps/life-manager/scripts/reconcile-local-cloud.test.js`
- Create: `docs/migrations/openclaw/cloud-cutover-evidence.md`

**Interfaces:**
- Consumes: local/cloud receipt streams and tenant scheduler-owner lease.
- Produces: parity report by `job_id`, `artifact_hash`, `snapshot_hash`, `effect_id`, and `decision_hash`; atomic ownership transfer.

- [ ] **Step 1: Write lease and parity tests**

Cover concurrent acquisition, lease expiry, ownership transfer, missing receipt, hash mismatch, and unknown external effect.

- [ ] **Step 2: Shadow cloud in read-only or duplicate-safe mode**

Cloud must match local decisions and artifacts without publishing, messaging, or paying twice.

- [ ] **Step 3: Canary Dais**

Transfer one tenant's scheduler lease to cloud. Verify real retained posts, reports, raw platform URLs, and Telegram receipts.

- [ ] **Step 4: Power off the Mac Mini for seven expected cycles**

Cloud must continue without missed or duplicate effects. Any mismatch returns scheduler ownership to local using the signed rollback record.

- [ ] **Step 5: Close the migration release**

Mark Orders 0–26 complete only when repository, local, cloud, tenancy, billing, and availability evidence all pass. Orders 27–38 remain feature-frozen until this point.
