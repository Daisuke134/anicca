"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { createConnectorActionCache } = require("./connector-action-cache.js");

function temporaryCache() {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connector-action-cache-"));
  return { directory, file: path.join(directory, "workflow-actions.json") };
}

function verifiedRepair(overrides = {}) {
  return {
    provider: "luma",
    workflowVersion: "luma-registration-v1",
    pageState: "registration_form",
    expectedEffect: "registered_or_pending",
    providerState: { status: "registered" },
    observedAt: "2026-08-07T03:00:00.000Z",
    actions: [
      { purpose: "fill", method: "ax_fill", control: "required_text" },
      { purpose: "submit", method: "ax_click", control: "registration_submit" },
    ],
    ...overrides,
  };
}

test("verified repaired actions persist privately and read back by exact workflow version", () => {
  const { directory, file } = temporaryCache();
  try {
    const cache = createConnectorActionCache({ path: file });
    const saved = cache.saveVerifiedRepair(verifiedRepair());

    assert.equal(saved.status, "saved");
    assert.match(saved.cache_entry_id, /^connector-action-cache:[0-9a-f]{64}$/);
    assert.equal(fs.statSync(file).mode & 0o777, 0o600);
    assert.deepEqual(cache.read({
      provider: "luma",
      workflowVersion: "luma-registration-v1",
      pageState: "registration_form",
      expectedEffect: "registered_or_pending",
    }).actions, verifiedRepair().actions);
    const bytes = fs.readFileSync(file, "utf8");
    assert.equal(bytes.includes('"status":"registered"'), false);
    assert.equal(bytes.includes("provider_receipt_id"), false);
    assert.equal(bytes.includes("example.com"), false);
    assert.equal(bytes.includes("owner-token"), false);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("unverified effects and unsafe agent actions never enter the cache", () => {
  const cases = [
    verifiedRepair({ providerState: { status: "absent" } }),
    verifiedRepair({ actions: [{ purpose: "submit", method: "browser_close", control: "registration_submit" }] }),
    verifiedRepair({ actions: [{ purpose: "fill", method: "ax_fill", control: "person@example.com" }] }),
    verifiedRepair({ actions: [{ purpose: "fill", method: "ax_fill", control: "raw prompt answer" }] }),
  ];
  for (const input of cases) {
    const { directory, file } = temporaryCache();
    try {
      const cache = createConnectorActionCache({ path: file });
      assert.throws(() => cache.saveVerifiedRepair(input), /Connector action cache invalid/);
      assert.equal(fs.existsSync(file), false);
    } finally {
      fs.rmSync(directory, { recursive: true, force: true });
    }
  }
});

test("repair replaces only the exact provider workflow and page-state entry", () => {
  const { directory, file } = temporaryCache();
  try {
    const cache = createConnectorActionCache({ path: file });
    cache.saveVerifiedRepair(verifiedRepair());
    cache.saveVerifiedRepair(verifiedRepair({
      provider: "connpass",
      workflowVersion: "connpass-registration-v1",
      pageState: "registration_form",
      actions: [{ purpose: "submit", method: "ax_click", control: "event_apply" }],
    }));
    cache.saveVerifiedRepair(verifiedRepair({
      observedAt: "2026-08-07T03:05:00.000Z",
      actions: [{ purpose: "submit", method: "coordinate_click", control: "registration_submit" }],
    }));

    assert.deepEqual(cache.read({
      provider: "luma", workflowVersion: "luma-registration-v1",
      pageState: "registration_form", expectedEffect: "registered_or_pending",
    }).actions, [{ purpose: "submit", method: "coordinate_click", control: "registration_submit" }]);
    assert.deepEqual(cache.read({
      provider: "connpass", workflowVersion: "connpass-registration-v1",
      pageState: "registration_form", expectedEffect: "registered_or_pending",
    }).actions, [{ purpose: "submit", method: "ax_click", control: "event_apply" }]);
    assert.equal(JSON.parse(fs.readFileSync(file, "utf8")).entries.length, 2);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("cached replay uses no agent and succeeds only after parent readback", async () => {
  const { directory, file } = temporaryCache();
  try {
    const cache = createConnectorActionCache({ path: file });
    cache.saveVerifiedRepair(verifiedRepair());
    const calls = [];
    const result = await cache.replay({
      provider: "luma",
      workflowVersion: "luma-registration-v1",
      pageState: "registration_form",
      expectedEffect: "registered_or_pending",
      page: Object.freeze({ page_id: "owned-page" }),
      async performAction(input) {
        calls.push(["perform", input.action]);
        return { status: "success" };
      },
      async readExpectedState() {
        calls.push(["readback"]);
        return { status: "pending", provider_receipt_id: "receipt-2" };
      },
    });

    assert.equal(result.status, "completed");
    assert.equal(result.provider_state.status, "pending");
    assert.equal(calls.filter(([name]) => name === "perform").length, 2);
    assert.equal(calls.filter(([name]) => name === "readback").length, 1);
    assert.equal(calls.some(([name]) => name === "agent"), false);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
