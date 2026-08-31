"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const {
  runBrowserMatrixProductionE2E,
  makeProductionDeps,
  OUTPUT_KEYS,
} = require("./browser-matrix-production-e2e.js");

const MODULE_PATH = path.join(__dirname, "browser-matrix-production-e2e.js");
const CATEGORIES = ["booking", "inquiry", "application"];
const URLS = Object.freeze({
  booking: "https://cal.example.test/agent/meeting",
  inquiry: "https://forms.example.test/agent/inquiry",
  application: "https://apply.example.test/agent/application",
});

function environment(overrides = {}) {
  return {
    BROWSER_MATRIX_BOOKING_URL: URLS.booking,
    BROWSER_MATRIX_INQUIRY_URL: URLS.inquiry,
    BROWSER_MATRIX_APPLICATION_URL: URLS.application,
    BROWSER_MATRIX_TENANT_UID: "tenant-a",
    BROWSER_MATRIX_TELEGRAM_CHAT_ID: "42",
    LM_FEEDBACK_DATABASE_URL: "postgres://runtime-only",
    LM_TELEGRAM_BOT_TOKEN: "telegram-runtime-only",
    GEMINI_API_KEY: "gemini-runtime-only",
    LM_AGENT_BROWSER_EMAIL: "runtime-owner@example.test",
    LM_AGENT_BROWSER_NAME: "Runtime Owner",
    ...overrides,
  };
}

function completedRow(id, category, origin) {
  return {
    id,
    uid: "tenant-a",
    status: "completed",
    receipt: {
      session_id: `steel-${category}`,
      selected_origin: origin,
      selected_url: `${origin}/confirmed`,
      provider_receipt: {
        confirmed: true,
        status: `${category}_confirmed`,
        confirmation_id: `${category}-public-id`,
        current_url: `${origin}/confirmed`,
        handoff_required: false,
        handoff_reason: null,
      },
      evidence_message_id: String(700 + CATEGORIES.indexOf(category)),
      steel_released: true,
    },
  };
}

function forbidden(name) {
  return () => {
    throw new Error(`${name} dependency must not be reachable from the verifier`);
  };
}

function fakeDependencies(overrides = {}) {
  const rows = new Map();
  const calls = [];
  const attempts = new Map();
  const clock = { current: 0 };
  const pendingReads = Number.isInteger(overrides.pendingReads) ? overrides.pendingReads : 0;
  const pendingStatus = overrides.pendingStatus || "queued";

  const deps = {
    durableQueue: {
      async enqueue(input) {
        calls.push(["enqueue", input]);
        const id = `job-${input.category}`;
        rows.set(id, completedRow(id, input.category, new URL(input.url).origin));
        return { id };
      },
      async read({ id }) {
        calls.push(["read", id]);
        const attempt = (attempts.get(id) || 0) + 1;
        attempts.set(id, attempt);
        if (overrides.neverTerminal || attempt <= pendingReads) {
          return { id, uid: "tenant-a", status: pendingStatus, receipt: null };
        }
        const row = structuredClone(rows.get(id));
        return overrides.mutateRow ? overrides.mutateRow(row, id) : row;
      },
    },
    clock: {
      async sleep(ms) {
        calls.push(["sleep", ms]);
        clock.current += ms;
      },
      now() {
        return clock.current;
      },
    },
  };
  for (const name of ["executor", "driver", "store", "runtime"]) {
    Object.defineProperty(deps, name, {
      get: forbidden(name),
      enumerable: false,
      configurable: true,
    });
  }
  return { calls, deps, clock };
}

test("production dependencies expose only the enqueue read and clock boundaries", () => {
  const deps = makeProductionDeps(environment(), { query: async () => ({ rows: [] }) });
  assert.deepEqual(Object.keys(deps), ["durableQueue", "clock"]);
  assert.deepEqual(Object.keys(deps.durableQueue), ["enqueue", "read"]);
  assert.deepEqual(Object.keys(deps.clock), ["sleep", "now"]);
  assert.equal(deps.executor, undefined);
  assert.equal(deps.driver, undefined);
});

test("verifier module never references the executor runtime or a claim function", () => {
  const source = readFileSync(MODULE_PATH, "utf8");
  assert.doesNotMatch(source, /browser-job-runtime/);
  assert.doesNotMatch(source, /runNextBrowserJob/);
  assert.doesNotMatch(source, /claimBrowserJob/);
  assert.doesNotMatch(source, /\bdriver\b/);
  assert.doesNotMatch(source, /\bexecutor\b/);
});

test("enqueues three durable jobs and polls until each row is terminal", async () => {
  const { deps, calls } = fakeDependencies({ pendingReads: 2 });
  const result = await runBrowserMatrixProductionE2E({ env: environment(), deps });

  assert.deepEqual(Object.keys(result), OUTPUT_KEYS);
  assert.deepEqual(result.categories, CATEGORIES);
  assert.deepEqual(result.job_ids, CATEGORIES.map((value) => `job-${value}`));
  assert.deepEqual(result.provider_origins, [
    "https://cal.example.test",
    "https://forms.example.test",
    "https://apply.example.test",
  ]);
  assert.deepEqual(result.steel_session_ids, CATEGORIES.map((value) => `steel-${value}`));
  assert.deepEqual(result.telegram_evidence_ids, ["700", "701", "702"]);
  assert.equal(result.provider_receipt_hashes.length, 3);
  assert.equal(new Set(result.provider_receipt_hashes).size, 3);
  assert.ok(result.provider_receipt_hashes.every((value) => /^[a-f0-9]{64}$/.test(value)));
  assert.equal(result.released, true);

  const names = calls.map(([name]) => name);
  assert.equal(names.filter((name) => name === "enqueue").length, 3);
  assert.equal(names.filter((name) => name === "execute").length, 0);
  assert.equal(names.filter((name) => name === "read").length, 9);
  assert.ok(names.filter((name) => name === "sleep").length >= 2);
  assert.equal(names.indexOf("read") > names.lastIndexOf("enqueue"), true);
  assert.doesNotMatch(JSON.stringify(result), /runtime-owner|telegram-runtime|gemini-runtime/i);
});

test("missing unsafe or duplicate runtime targets fail before enqueue", async () => {
  const cases = [
    environment({ BROWSER_MATRIX_BOOKING_URL: "" }),
    environment({ BROWSER_MATRIX_BOOKING_URL: "http://cal.example.test/meeting" }),
    environment({ BROWSER_MATRIX_BOOKING_URL: "https://127.0.0.1/meeting" }),
    environment({ BROWSER_MATRIX_INQUIRY_URL: URLS.booking }),
  ];
  for (const env of cases) {
    const { deps, calls } = fakeDependencies();
    await assert.rejects(
      runBrowserMatrixProductionE2E({ env, deps }),
      /browser matrix|missing required/i,
    );
    assert.equal(calls.length, 0);
  }
});

test("invalid poll overrides fail before enqueue", async () => {
  const cases = [
    environment({ BROWSER_MATRIX_POLL_TIMEOUT_MS: "0" }),
    environment({ BROWSER_MATRIX_POLL_TIMEOUT_MS: "-1" }),
    environment({ BROWSER_MATRIX_POLL_TIMEOUT_MS: "12.5" }),
    environment({ BROWSER_MATRIX_POLL_TIMEOUT_MS: "many" }),
    environment({ BROWSER_MATRIX_POLL_TIMEOUT_MS: "99999999" }),
    environment({ BROWSER_MATRIX_POLL_INTERVAL_MS: "0" }),
    environment({ BROWSER_MATRIX_POLL_INTERVAL_MS: "999999" }),
    environment({ BROWSER_MATRIX_POLL_TIMEOUT_MS: "100", BROWSER_MATRIX_POLL_INTERVAL_MS: "200" }),
  ];
  for (const env of cases) {
    const { deps, calls } = fakeDependencies();
    await assert.rejects(
      runBrowserMatrixProductionE2E({ env, deps }),
      /browser matrix poll/i,
    );
    assert.equal(calls.length, 0);
  }
});

test("a bounded poll deadline fails closed instead of waiting forever", async () => {
  const { deps, calls } = fakeDependencies({ neverTerminal: true, pendingStatus: "running" });
  await assert.rejects(
    runBrowserMatrixProductionE2E({
      env: environment({
        BROWSER_MATRIX_POLL_TIMEOUT_MS: "50",
        BROWSER_MATRIX_POLL_INTERVAL_MS: "10",
      }),
      deps,
    }),
    /browser matrix production E2E failed/i,
  );
  const names = calls.map(([name]) => name);
  assert.equal(names.filter((name) => name === "enqueue").length, 3);
  assert.ok(names.filter((name) => name === "read").length <= 24);
  assert.ok(names.filter((name) => name === "sleep").length <= 6);
});

test("terminal statuses other than completed fail closed", async () => {
  for (const status of ["possibly_completed", "handoff_required", "failed"]) {
    const { deps } = fakeDependencies({ mutateRow: (row) => ({ ...row, status }) });
    await assert.rejects(
      runBrowserMatrixProductionE2E({
        env: environment({
          BROWSER_MATRIX_POLL_TIMEOUT_MS: "50",
          BROWSER_MATRIX_POLL_INTERVAL_MS: "10",
        }),
        deps,
      }),
      /browser matrix production E2E failed/i,
    );
  }
});

test("unreleased or unconfirmed durable rows fail closed", async () => {
  const mutations = [
    (row) => ({ ...row, receipt: { ...row.receipt, steel_released: false } }),
    (row) => ({
      ...row,
      receipt: {
        ...row.receipt,
        provider_receipt: { ...row.receipt.provider_receipt, confirmed: false },
      },
    }),
    (row) => ({ ...row, receipt: { ...row.receipt, evidence_message_id: "" } }),
    (row) => ({ ...row, receipt: { ...row.receipt, selected_origin: "https://other.example.test" } }),
    (row) => ({ ...row, uid: "tenant-b" }),
  ];
  for (const mutateRow of mutations) {
    const { deps } = fakeDependencies({ mutateRow });
    await assert.rejects(
      runBrowserMatrixProductionE2E({ env: environment(), deps }),
      /browser matrix production E2E failed/i,
    );
  }
});

test("unexpected provider receipt fields are rejected instead of hashed", async () => {
  const { deps } = fakeDependencies({
    mutateRow(row) {
      row.receipt.provider_receipt.email = "must-not-cross-boundary@example.test";
      return row;
    },
  });
  await assert.rejects(
    runBrowserMatrixProductionE2E({ env: environment(), deps }),
    /browser matrix production E2E failed/i,
  );
});
