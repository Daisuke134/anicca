"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { classifyFinalAudit } = require("./marketing-final-audit.js");

test("final audit stays not_ready with concrete cadence, experiment, and ownership gaps", () => {
  const result = classifyFinalAudit({ selected_healthy: true, selected_count: 15, cadence: { published: 0, pending: 39, missed: 0, duplicate: 0 }, daily_accounts: 13, weekly_message_length: 1754, decisions: { total: 3, decided: 0 }, proofs: { total: 3, proved: 0 }, ownership: { status: "not_ready", conflicts: 10 } });
  assert.equal(result.status, "not_ready");
  assert.deepEqual(result.blockers, ["cadence_not_complete", "hook_decisions_pending", "hook_consumption_pending", "legacy_owner_conflicts"]);
});

test("final audit is ready only when every declared completion gate is true", () => {
  const result = classifyFinalAudit({ selected_healthy: true, selected_count: 15, cadence: { published: 39, pending: 0, missed: 0, duplicate: 0 }, daily_accounts: 13, weekly_message_length: 1754, decisions: { total: 3, decided: 3 }, proofs: { total: 3, proved: 3 }, ownership: { status: "ready", conflicts: 0 } });
  assert.equal(result.status, "ready");
  assert.deepEqual(result.blockers, []);
});
