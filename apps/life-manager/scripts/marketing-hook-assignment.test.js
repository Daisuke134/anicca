"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { importContentObject } = require("../lib/content-object-store.js");
const { LANES, buildHookAssignment, persistHookAssignments } = require("./marketing-hook-assignment.js");

function pack(productId, formatId, locale, prefix) {
  return { schema_version: 1, product_id: productId, format_id: formatId, form: formatId === "reelclaw" ? "relationship-confession" : "nudge-card", locale, title: "test", hashtags: [], hooks: [{ id: `${prefix}-001`, text: "baseline hook", status: "active", prior_used_at: null }, { id: `${prefix}-002`, text: "challenger hook", status: "active", prior_used_at: null }] };
}

test("hook assignments isolate each product/locale lane and choose one baseline plus challenger", () => {
  const values = [
    buildHookAssignment(LANES[0], pack("honne-ai", "reelclaw", "en", "HEN"), "2026-08-28T00:00:00.000Z"),
    buildHookAssignment(LANES[1], pack("honne-ai", "reelclaw", "ja", "HJA"), "2026-08-28T00:00:00.000Z"),
    buildHookAssignment(LANES[2], pack("anicca-ios", "reelclaw-card", "ja", "AJ"), "2026-08-28T00:00:00.000Z"),
  ];
  assert.deepEqual(values.map(({ product_id, locale, account_id }) => [product_id, locale, account_id]), [["honne-ai", "en", "@honne_reveal"], ["honne-ai", "ja", "@honnevideo"], ["anicca-ios", "ja", "@anicca.jp"]]);
  assert.equal(new Set(values.map(({ assignment_id }) => assignment_id)).size, 3);
  for (const value of values) {
    assert.equal(value.baseline.variant, "baseline");
    assert.equal(value.challenger.variant, "challenger");
    assert.notEqual(value.baseline.hook_id, value.challenger.hook_id);
    assert.deepEqual(value.allocation, { baseline: 0.5, challenger: 0.5 });
  }
});

test("hook assignments persist immutably and replay without a second object", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-hook-assignment-"));
  const objectDir = path.join(dataDir, "objects");
  const refs = [pack("honne-ai", "reelclaw", "en", "HEN"), pack("honne-ai", "reelclaw", "ja", "HJA"), pack("anicca-ios", "reelclaw-card", "ja", "AJ")].map((value, index) => {
    const file = path.join(dataDir, `pack-${index}.json`); fs.writeFileSync(file, JSON.stringify(value)); return importContentObject(file, { objectDir }).ref;
  });
  const env = { LM_DATA_DIR: dataDir, LM_RUNTIME_TENANT_ID: "dais-local", LM_HONNE_EN_PACK_REF: refs[0], LM_HONNE_JA_PACK_REF: refs[1], LM_ANICCA_MAIN_PACK_REF: refs[2] };
  const first = persistHookAssignments({ dataDir, env, observedAt: "2026-08-28T00:00:00.000Z" });
  const replay = persistHookAssignments({ dataDir, env, observedAt: "2026-08-28T01:00:00.000Z" });
  assert.equal(first.created, true);
  assert.equal(first.assignments.length, 3);
  assert.equal(replay.created, false);
  assert.equal(replay.snapshot_ref, first.snapshot_ref);
  assert.equal(fs.statSync(first.pointer).mode & 0o777, 0o600);
});
