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
