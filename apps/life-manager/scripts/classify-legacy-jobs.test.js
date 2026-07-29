"use strict";

// Order 2 validation: the checked-in runtime inventory must carry one final
// disposition per row, with owners and rollback actions, and must leave the
// three pre-classified Order 1 rows untouched.

const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const {
  ADAPTER_VERIFY_COMMAND,
  PROTECTED_ROWS,
  classifyInventory,
  loadExistingAdapterIds,
} = require("./classify-legacy-jobs.js");

const INVENTORY_PATH = path.join(
  __dirname, "..", "..", "..",
  "docs", "migrations", "openclaw", "runtime-inventory.json",
);

const ALLOWED_DISPOSITIONS = new Set([
  "migrate", "replace", "retire", "retain-external",
]);

function loadInventory() {
  return JSON.parse(fs.readFileSync(INVENTORY_PATH, "utf8"));
}

test("inventory covers exactly 399 captured rows", () => {
  const inventory = loadInventory();
  assert.equal(inventory.jobs.length, 399);
  assert.equal(inventory.summary.total, 399);
});

test("zero rows remain unclassified", () => {
  const inventory = loadInventory();
  const unclassified =
    inventory.jobs.filter((job) => job.disposition === "unclassified");
  assert.equal(unclassified.length, 0);
  assert.equal(inventory.summary.unclassified, 0);
});

test("every disposition is migrate, replace, retire, or retain-external", () => {
  const inventory = loadInventory();
  for (const job of inventory.jobs) {
    assert.ok(
      ALLOWED_DISPOSITIONS.has(job.disposition),
      `unexpected disposition ${job.disposition} on ${job.legacy_id}`,
    );
  }
});

test("every enabled-or-loaded row has a non-null owner", () => {
  const inventory = loadInventory();
  for (const job of inventory.jobs) {
    if (job.enabled || job.loaded) {
      assert.ok(
        typeof job.owner === "string" && job.owner.length > 0,
        `enabled/loaded row without owner: ${job.legacy_id || job.display_name}`,
      );
    }
  }
});

test("the three protected Order 1 rows keep their exact target adapters", () => {
  const inventory = loadInventory();
  const expected = {
    "ai.anicca.life-manager-daily": "marketing-life-manager-daily",
    "ai.anicca.life-manager-financial-report": "financial-report-telegram",
    "ai.anicca.reelclaw-honne-ja": "marketing-video-generation",
  };
  assert.deepEqual(expected, { ...PROTECTED_ROWS });
  for (const [legacyId, adapter] of Object.entries(expected)) {
    const row = inventory.jobs.find((job) => job.legacy_id === legacyId);
    assert.ok(row, `protected row missing: ${legacyId}`);
    assert.equal(row.disposition, "migrate");
    assert.equal(row.target_adapter, adapter);
  }
});

test("every migrate/replace row has a rollback action", () => {
  const inventory = loadInventory();
  for (const job of inventory.jobs) {
    if (job.disposition === "migrate" || job.disposition === "replace") {
      assert.ok(
        typeof job.rollback_action === "string" && job.rollback_action.length > 0,
        `migrate/replace row without rollback: ${job.legacy_id}`,
      );
    }
  }
});

test("verify commands are only assigned for adapters that exist", () => {
  const inventory = loadInventory();
  const existing = loadExistingAdapterIds();
  for (const job of inventory.jobs) {
    if (Object.prototype.hasOwnProperty.call(PROTECTED_ROWS, job.legacy_id)) {
      continue; // Order 1 rows carry their own verify commands
    }
    if (job.verify_command !== null) {
      assert.equal(job.verify_command, ADAPTER_VERIFY_COMMAND);
      assert.ok(
        existing.has(job.target_adapter),
        `verify_command invented for missing adapter ${job.target_adapter}`,
      );
    }
  }
});

test("classification is deterministic: re-running changes nothing", () => {
  const inventory = loadInventory();
  const reclassified = classifyInventory(inventory, loadExistingAdapterIds());
  assert.deepEqual(reclassified, inventory);
});

test("summary disposition counts match the rows", () => {
  const inventory = loadInventory();
  const counted = {};
  for (const job of inventory.jobs) {
    counted[job.disposition] = (counted[job.disposition] || 0) + 1;
  }
  assert.deepEqual(inventory.summary.dispositions, counted);
});
