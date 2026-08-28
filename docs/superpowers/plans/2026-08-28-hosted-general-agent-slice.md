# GA-11A Hosted Tenant Ingress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect one authenticated paid hosted tenant to the existing general-agent runtime queue and cloud vault boundary without rebuilding onboarding, billing, scheduling, or storage.

**Architecture:** Existing Telegram/Web onboarding remains the tenant authority and Stripe webhook remains the only writer of `lm_users.paid`. A thin ingress loads the server-owned tenant row, verifies paid entitlement and cloud-vault health, builds the existing reference-only Goal WorkItem, and enqueues it into `runtime-job-store.js`.

**Tech Stack:** Node.js built-ins, existing `goal-work-item.js`, `runtime-job-store.js`, `secret-provider.js`, loop adapter registry, Node test runner.

**Spec:** `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md` (GA-11), reusing `docs/superpowers/specs/2026-08-26-life-manager-cloud-on-time-core-design.md` for hosted tenant and payment authority.

## Global Constraints

- No new framework, scheduler, database table, vault, billing state, browser, or provider-specific brain.
- The model owns goal judgment; deterministic code owns tenant scope, entitlement, references, enqueue identity, receipt shape, and replay.
- Raw goal text, secret values, phone, Telegram chat ID, and credentials never enter the runtime job or returned receipt.
- Unpaid, cross-tenant, unauthenticated, or unhealthy-vault input produces enqueue count zero.
- Normal slice target: at most three production/test files and 100 production LOC per task.

---

### Task 1: Hosted tenant ingress

**Files:**
- Create: `apps/life-manager/lib/hosted-goal-ingress.js`
- Test: `apps/life-manager/lib/hosted-goal-ingress.test.js`

**Interfaces:**
- Consumes: `buildGoalWorkItem(goal, nowMs)`, injected `loadTenant(tenantId)`, `secretProvider.health()`, and `enqueueJob(input)`.
- Produces: `enqueueHostedGoal({scope, goal, nowMs}, deps) -> {created, tenant_id, job_id, job_ref, vault_provider}`.

- [x] **Step 1: Write the failing ingress tests**

Test a paid same-tenant row with healthy `{mode:"cloud", provider:"vault"}` health. Assert first enqueue creates one exact reference-only job, replay returns `created:false`, and neither result/job JSON contains goal statement, chat ID, phone, or a secret value. Add a second test where unpaid, cross-tenant chat, mismatched goal uid, and unhealthy vault each reject before enqueue.

- [x] **Step 2: Run the RED test**

Run:

```bash
node --test apps/life-manager/lib/hosted-goal-ingress.test.js
```

Expected: FAIL because `hosted-goal-ingress.js` does not exist.

- [x] **Step 3: Implement the minimum ingress**

Implement `enqueueHostedGoal` with these exact checks and mapping:

```js
const job = buildGoalWorkItem(input.goal, input.nowMs);
const tenant = await deps.loadTenant(scope.tenantId);
if (!tenant || tenant.uid !== scope.tenantId || String(tenant.telegram_chat_id) !== scope.chatId) throw new Error("hosted tenant scope mismatch");
if (tenant.paid !== true) throw new Error("hosted tenant entitlement required");
const vault = await deps.secretProvider.health();
if (!vault?.ok || vault.mode !== "cloud" || vault.provider !== "vault") throw new Error("hosted tenant vault unavailable");
const queued = await deps.enqueueJob({
  jobId: job.job_id, tenantId: job.tenant_id, loopId: job.loop_id,
  capability: job.capability, effectClass: job.effect_class,
  effectKey: job.effect_key, inputRefs: job.input_refs, maxAttempts: job.max_attempts,
});
```

Return only safe identities and `created`.

- [x] **Step 4: Run GREEN and adjacent tests**

```bash
node --test \
  apps/life-manager/lib/hosted-goal-ingress.test.js \
  apps/life-manager/lib/goal-work-item.test.js \
  apps/life-manager/lib/secret-provider.test.js \
  apps/life-manager/lib/runtime-job-store.test.js
```

- [ ] **Step 5: Commit and push Task 1**

```bash
git add apps/life-manager/lib/hosted-goal-ingress.js apps/life-manager/lib/hosted-goal-ingress.test.js
git commit -m "feat: enqueue hosted tenant goals"
git push origin docs/general-agent-simple-scope-20260828
```
