"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  runBrowserMatrixProductionE2E,
  OUTPUT_KEYS,
} = require("./browser-matrix-production-e2e.js");

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

function fakeDependencies(overrides = {}) {
  const rows = new Map();
  const calls = [];
  return {
    calls,
    deps: {
      durableQueue: {
        async enqueue(input) {
          calls.push(["enqueue", input]);
          const id = `job-${input.category}`;
          const origin = new URL(input.url).origin;
          rows.set(id, {
            id,
            uid: "tenant-a",
            status: "completed",
            receipt: {
              session_id: `steel-${input.category}`,
              selected_origin: origin,
              selected_url: `${origin}/confirmed`,
              provider_receipt: {
                confirmed: true,
                status: `${input.category}_confirmed`,
                confirmation_id: `${input.category}-public-id`,
                current_url: `${origin}/confirmed`,
                handoff_required: false,
                handoff_reason: null,
              },
              evidence_message_id: String(700 + CATEGORIES.indexOf(input.category)),
              steel_released: true,
            },
          });
          return { id };
        },
        async read({ id }) {
          const row = structuredClone(rows.get(id));
          return overrides.mutateRow ? overrides.mutateRow(row, id) : row;
        },
      },
      executor: {
        async run({ jobId }) {
          calls.push(["execute", jobId]);
          return { trace_id: jobId };
        },
      },
    },
  };
}

test("runs booking inquiry and application through distinct durable provider jobs", async () => {
  const { deps, calls } = fakeDependencies();
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
  assert.equal(calls.filter(([name]) => name === "enqueue").length, 3);
  assert.equal(calls.filter(([name]) => name === "execute").length, 3);
  assert.doesNotMatch(JSON.stringify(result), /runtime-owner|example\.test@|telegram-runtime|gemini-runtime/i);
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

test("possibly-completed unreleased or unconfirmed durable rows fail closed", async () => {
  const mutations = [
    (row) => ({ ...row, status: "possibly_completed" }),
    (row) => ({ ...row, receipt: { ...row.receipt, steel_released: false } }),
    (row) => ({
      ...row,
      receipt: {
        ...row.receipt,
        provider_receipt: { ...row.receipt.provider_receipt, confirmed: false },
      },
    }),
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
