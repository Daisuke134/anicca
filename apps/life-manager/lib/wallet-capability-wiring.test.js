"use strict";
// AE-ZERO-START-1 §4.6 — the capabilities are actually registered.
//
// An adapter nobody can reach is the failure this file exists to catch: the modules can be perfect and
// the tenant still never gets a wallet because the manifest entry is missing, the factory name is
// misspelled, or the worker never builds services for it. So these assertions go through the REAL
// registry and the REAL createWorkerHandlers rather than a stub, and the last one reads runtime-up.js to
// prove the scheduler sweep — the only enqueue point — is wired to a timer and torn down again.

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const { createConfiguredLoopAdapterRegistry } = require("./loop-adapter-registry.js");
const { createWorkerHandlers } = require("../scripts/runtime-up.js");
const zeroStart = require("./zero-start-job-adapter.js");
const inflow = require("./wallet-inflow-job-adapter.js");

const MANIFEST = JSON.parse(fs.readFileSync(path.join(__dirname, "../config/loop-adapters.json"), "utf8"));
const RUNTIME_UP = fs.readFileSync(path.join(__dirname, "../scripts/runtime-up.js"), "utf8");

const WORKER_ENV = {
  LM_RUNTIME_TENANT_ID: "tenant-a",
  SUPABASE_URL: "https://db.example",
  SUPABASE_SERVICE_ROLE_KEY: "service-role-test-only",
  LM_TELEGRAM_BOT_TOKEN: "123456:test-only-not-a-real-bot-token",
  LM_DATA_ROOT: "/tmp/lm-wallet-wiring-test",
};

test("both capabilities are declared in the adapter manifest with the right contracts", () => {
  const byCapability = new Map(MANIFEST.adapters.map((entry) => [entry.capability, entry]));

  const zero = byCapability.get(zeroStart.CAPABILITY);
  assert.ok(zero, "wallet.zero-start must be declared");
  assert.equal(zero.adapter_id, "tenant-zero-start");
  assert.equal(zero.loop_id, zeroStart.LOOP_ID);
  assert.deepEqual(zero.effect_classes, ["message"]);
  assert.equal(zero.module_ref, "lib/zero-start-job-adapter.js");
  assert.equal(zero.factory_export, "createZeroStartLoopAdapter");
  assert.equal(typeof zeroStart[zero.factory_export], "function", "the named factory must exist");

  const watch = byCapability.get(inflow.CAPABILITY);
  assert.ok(watch, "wallet.inflow.watch must be declared");
  assert.equal(watch.adapter_id, "tenant-wallet-inflow");
  assert.equal(watch.loop_id, inflow.LOOP_ID);
  // Observing changes nothing outside the process, and the schema requires a null effect_key for 'none'.
  assert.deepEqual(watch.effect_classes, ["none"]);
  assert.equal(watch.module_ref, "lib/wallet-inflow-job-adapter.js");
  assert.equal(watch.factory_export, "createWalletInflowLoopAdapter");
  assert.equal(typeof inflow[watch.factory_export], "function");
});

test("the real registry loads both adapters and exposes them by capability and loop id", () => {
  const registry = createConfiguredLoopAdapterRegistry({});
  for (const module of [zeroStart, inflow]) {
    assert.equal(registry.hasCapability(module.CAPABILITY), true, `${module.CAPABILITY} must be reachable`);
    const adapter = registry.getByCapability(module.CAPABILITY);
    for (const method of ["plan", "execute", "reconcile", "verify", "report"]) {
      assert.equal(typeof adapter[method], "function");
    }
    assert.equal(registry.getByLoopId(module.LOOP_ID), adapter, "the loop id must resolve to the same adapter");
  }
  // Registration must not have disturbed what was already there.
  assert.equal(registry.hasCapability("report.financial.telegram"), true);
  assert.equal(registry.hasCapability("marketing.observation.collect"), true);
});

// Captures what the REAL createWorkerHandlers builds, so these are probes of the shipped wiring rather
// than of a hand-written stand-in.
function captureServices(env, capabilities, dependencies = {}) {
  let captured = null;
  createWorkerHandlers(env, capabilities, {
    ...dependencies,
    createRegistry({ servicesByAdapter }) {
      captured = servicesByAdapter;
      return { hasCapability: () => false, getByCapability: () => ({}) };
    },
  });
  return captured;
}

test("§9.1 BLOCKER: a worker pinned to one tenant still resolves the bot token for another", async () => {
  // The measured defect: the shared worker claims jobs for EVERY tenant, but the zero-start service was
  // built once around a provider bound to LM_RUNTIME_TENANT_ID, so every other tenant's job died with
  // "environment secret tenant scope mismatch". This is that exact hostile call.
  const services = captureServices(WORKER_ENV, [zeroStart.CAPABILITY]);
  const provider = services["tenant-zero-start"].secretProvider;

  assert.equal(WORKER_ENV.LM_RUNTIME_TENANT_ID, "tenant-a", "the worker is pinned to tenant-a");
  for (const tenantId of ["tenant-a", "tenant-b", "lm_550e8400-e29b-41d4-a716-446655440000"]) {
    assert.equal(
      await provider.get(tenantId, "secret://telegram/bot-token"),
      WORKER_ENV.LM_TELEGRAM_BOT_TOKEN,
      `${tenantId} must be able to be told about its own wallets`,
    );
  }
  assert.equal((await provider.health()).scope, "colony");
});

test("§9.1: the colony provider cannot be used to read another tenant's wallet key", async () => {
  const services = captureServices(WORKER_ENV, [zeroStart.CAPABILITY]);
  const provider = services["tenant-zero-start"].secretProvider;
  // Dropping the tenant binding is only safe because key material is unreachable here. Hostile payloads:
  for (const ref of [
    "secret://lm-agent-wallet/tenant-a/base",
    "secret://lm-agent-wallet/tenant-b/solana",
    "secret://postiz/api-key",
  ]) {
    await assert.rejects(provider.get("tenant-a", ref), /reference/i, `${ref} must be refused`);
  }
});

test("§9.1: the tenant-scoped provider is untouched and still binds", async () => {
  // Other adapters must keep the gate. The financial report adapter is the live example.
  const services = captureServices(WORKER_ENV, ["report.financial.telegram"]);
  const provider = services["financial-report-telegram"].secretProvider;
  assert.equal(await provider.get("tenant-a", "secret://telegram/bot-token"), WORKER_ENV.LM_TELEGRAM_BOT_TOKEN);
  await assert.rejects(provider.get("tenant-b", "secret://telegram/bot-token"), /tenant/i);
});

test("§10 MAJOR-5: a worker reports the adapter's own error code instead of flattening it", () => {
  const { adapterErrorCode } = require("../scripts/runtime-up.js");
  assert.equal(adapterErrorCode(Object.assign(new Error("no chat"), { code: "BLOCKED_NO_CHAT" })), "BLOCKED_NO_CHAT");
  assert.equal(adapterErrorCode(Object.assign(new Error("x"), { code: "WALLET_KEY_ADDRESS_MISMATCH" })), "WALLET_KEY_ADDRESS_MISMATCH");
  // Hostile payloads: anything free-form could carry secret material into last_error_code.
  for (const code of [
    undefined,
    "",
    "lowercase",
    "has space",
    "0xac0ffee",
    "AB",
    "A".repeat(200),
    "TOKEN=123456:AAH-secret",
    { toString: () => "OBJECT_CODE" },
  ]) {
    assert.equal(
      adapterErrorCode(Object.assign(new Error("x"), { code })),
      "CAPABILITY_EXECUTION_FAILED",
      `${String(code)} must not reach the error code column`,
    );
  }
});

test("a worker asked for wallet.zero-start gets a handler for it", () => {
  const handlers = createWorkerHandlers(WORKER_ENV, [zeroStart.CAPABILITY]);
  assert.equal(typeof handlers[zeroStart.CAPABILITY], "function");
  // And it does not silently pick up capabilities it was not asked for.
  assert.equal(handlers[inflow.CAPABILITY], undefined);
});

test("a worker asked for wallet.inflow.watch gets a handler and a cursor store", () => {
  const queries = [];
  const handlers = createWorkerHandlers(WORKER_ENV, [inflow.CAPABILITY], {
    async query(sql, params) {
      queries.push({ sql, params });
      return { rows: [] };
    },
  });
  assert.equal(typeof handlers[inflow.CAPABILITY], "function");

  // The cursor has nowhere durable to live without a receipt store, so the wiring must refuse rather
  // than start up and silently re-scan the same window forever.
  assert.throws(() => createWorkerHandlers(WORKER_ENV, [inflow.CAPABILITY]), /cursor store/i);
});

test("the cursor is read back from this capability's own completed receipts", () => {
  // Reading another capability's receipts, or an uncompleted attempt, would resume from a window that
  // was never actually finished.
  assert.match(RUNTIME_UP, /r\.receipt->>'kind' = 'tenant_wallet_inflow'/);
  assert.match(RUNTIME_UP, /AND r\.outcome = 'completed'/);
  assert.match(RUNTIME_UP, /AND j\.capability = \$2/);
  assert.match(RUNTIME_UP, /WHERE r\.tenant_id = \$1/);
  assert.match(RUNTIME_UP, /ORDER BY r\.created_at DESC\s*\n\s*LIMIT 1/);
});

test("§9.3: the scheduler feeds the sweep a least-recently-watched ordering", () => {
  // Without this the per-pass cap re-serves the same first 50 uids forever and the tail never gets watched.
  assert.match(RUNTIME_UP, /readInflowWatchedAt/);
  assert.match(RUNTIME_UP, /max\(r\.created_at\) AS watched_at/);
  assert.match(RUNTIME_UP, /GROUP BY j\.tenant_id/);
  assert.match(RUNTIME_UP, /r\.receipt->>'kind' = 'tenant_wallet_inflow'/);
  // It must be the watch's OWN receipts: another capability's timestamps would order by the wrong event.
  assert.match(RUNTIME_UP, /WHERE j\.capability = \$1\s*\n\s*AND r\.outcome = 'completed'/);
});

test("the scheduler owns the sweep, runs it on a timer, and clears it on shutdown", () => {
  assert.match(RUNTIME_UP, /require\("\.\.\/lib\/wallet-sweep\.js"\)/);
  assert.match(RUNTIME_UP, /sweepWalletJobs\(/);
  assert.match(RUNTIME_UP, /walletSweepTimer = setInterval\(/);
  assert.match(RUNTIME_UP, /if \(walletSweepTimer\) clearInterval\(walletSweepTimer\)/);
  // The sweep lives in runSchedulerOwner, not in the worker: two sweepers would double the queue writes.
  const schedulerBody = RUNTIME_UP.slice(RUNTIME_UP.indexOf("async function runSchedulerOwner"));
  assert.ok(schedulerBody.includes("sweepWallets"), "the sweep must be started by the scheduler owner");
  const workerBody = RUNTIME_UP.slice(
    RUNTIME_UP.indexOf("async function runCapabilityWorker"),
    RUNTIME_UP.indexOf("async function runSchedulerOwner"),
  );
  assert.ok(!workerBody.includes("sweepWallets"), "a worker must not sweep");
});

test("the onboarding function is deliberately left with no queue access", () => {
  // §4.4: the runtime queue is the local Postgres and a Netlify function has no path to it; exposing
  // lm_runtime_jobs through PostgREST would put the queue's write surface on the public internet.
  const onboard = fs.readFileSync(
    path.join(__dirname, "../../landing/netlify/functions/lm-onboard.js"),
    "utf8",
  );
  for (const forbidden of ["lm_runtime_jobs", "LM_RUNTIME_DATABASE_URL", "zero-start", "runtime-job-store"]) {
    assert.ok(!onboard.includes(forbidden), `lm-onboard.js must not reference ${forbidden}`);
  }
  // A new tenant row is created with the wallet columns absent, which is exactly what the sweep looks for.
  const { needsZeroStart } = require("./wallet-sweep.js");
  assert.match(onboard, /upsertUser\(\{ uid \}\)/);
  assert.equal(needsZeroStart({ uid: "lm_new-tenant" }), true);
});

test("§10 MINOR-8: neither adapter offers a second way into the job queue", () => {
  // §4.4 rules the scheduler sweep the ONLY enqueue point. A CLI entrypoint is a second write surface into
  // the queue, which is precisely what that ruling excluded — so the modules must not expose one at all.
  for (const [name, module] of [["zero-start", zeroStart], ["wallet-inflow", inflow]]) {
    for (const removed of ["enqueueZeroStartJob", "enqueueWalletInflowJob", "parseEnqueueArgs"]) {
      assert.equal(module[removed], undefined, `${name} must not export ${removed}`);
    }
  }
  for (const file of ["zero-start-job-adapter.js", "wallet-inflow-job-adapter.js"]) {
    const source = fs.readFileSync(path.join(__dirname, file), "utf8");
    assert.ok(!source.includes("require.main === module"), `${file} must have no CLI entrypoint`);
    assert.ok(!source.includes("process.argv"), `${file} must not read argv`);
    // And no direct queue-write import that could grow one back.
    assert.ok(!/require\("\.\/runtime-job-store\.js"\)[\s\S]{0,80}enqueueJob/.test(source), `${file} must not import enqueueJob`);
  }
  // The sweep remains the one place that writes.
  assert.equal(typeof require("./wallet-sweep.js").sweepWalletJobs, "function");
});

test("§10 MINOR-11: the tenant keychain is kept on purpose and says so honestly", () => {
  // Deliberate exception to the delete-unused-code rule. The comment must NOT claim it guards a live path.
  const source = fs.readFileSync(path.join(__dirname, "tenant-wallet-store.js"), "utf8");
  assert.match(source, /NOTHING in the running path calls this today/);
  assert.match(source, /AE-X402-TENANT-ROUTING-1/);
  assert.ok(
    !/single check that stops one tenant's worker reading another's key/.test(source),
    "the old comment overclaimed that it protects a running path",
  );
  // It is still real, tested code — kept, not commented out.
  assert.equal(typeof require("./tenant-wallet-store.js").createTenantWalletKeychain, "function");
});

test("§11.5: the scheduler decides by ANNOUNCEMENT receipts, not by wallet columns", () => {
  assert.match(RUNTIME_UP, /readAnnouncedTenants/);
  assert.match(RUNTIME_UP, /r\.receipt->>'status' = 'started'/);
  assert.match(RUNTIME_UP, /r\.receipt->>'kind' = 'tenant_zero_start'/);
  // A blocked receipt must NOT count as an announcement, so the status filter is load-bearing.
  assert.ok(!/receipt->>'status' = 'blocked_no_chat'/.test(RUNTIME_UP));
});

test("§11.3: the reap is status re-activation preserving attempt — the only one the schema allows", () => {
  // Measured in real PostgreSQL 18: a generation-suffixed job_id violates UNIQUE (tenant_id, effect_key);
  // DELETE violates the receipts FK and then the immutability trigger; resetting attempt collides with the
  // receipt PK (job_id, attempt). These assertions pin the surviving option so a future edit cannot
  // silently reintroduce one of the impossible ones.
  assert.match(RUNTIME_UP, /SET status = 'queued'/);
  assert.match(RUNTIME_UP, /AND attempt < max_attempts/);
  assert.match(RUNTIME_UP, /AND status IN \('completed', 'dead_letter'\)/);
  // Never touches attempt, never deletes, never widens the budget.
  const reap = RUNTIME_UP.slice(RUNTIME_UP.indexOf("async reapZeroStartJob"), RUNTIME_UP.indexOf("async readInflowWatchedAt"));
  assert.ok(!/attempt\s*=/.test(reap), "attempt must be preserved, not reset");
  assert.ok(!/DELETE/i.test(reap), "a DELETE is refused by the receipts foreign key");
  assert.ok(!/max_attempts\s*=/.test(reap), "max_attempts is CHECK-capped at 20 and must not be rewritten");
  // And it reports exhaustion instead of forcing a run it has no budget for.
  assert.match(reap, /reason: "exhausted"/);
});
