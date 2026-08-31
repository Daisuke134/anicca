"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { buildGoalWorkItem } = require("./goal-work-item.js");
const { createGeneralAgentWorkLoopAdapter } = require("./general-agent-work-adapter.js");

const NOW_MS = Date.parse("2026-08-28T13:45:00Z");

function goal() {
  return {
    id: "hosted-goal-1",
    uid: "tenant-a",
    kind: "explicit_goal",
    statement: "Find and execute the best next action",
    provenance: { source: "telegram_reply", evidence: "private-message", observedAt: "2026-08-28T13:44:00Z" },
    confidenceTier: "explicit",
    confidence: 1,
    expiresAt: null,
    status: "active",
    supersedes: null,
  };
}

function job() {
  return buildGoalWorkItem(goal(), NOW_MS);
}

function receipt(overrides = {}) {
  return {
    kind: "general_agent_work",
    status: "planned",
    tenant_id: "tenant-a",
    job_id: "goal:hosted-goal-1",
    goal_ref: "intent-entry://tenant-a/hosted-goal-1",
    execution_id: "bounded-execution-1",
    next_job_refs: ["runtime-job://tenant-a/next-job-1"],
    ...overrides,
  };
}

test("adapter runs one bounded specialist with references and returns a verified receipt", async () => {
  const calls = [];
  const adapter = createGeneralAgentWorkLoopAdapter({
    async runBoundedSpecialist(input) {
      calls.push(input);
      return receipt();
    },
  });

  const result = await adapter.execute(job());
  assert.deepEqual(calls, [{
    tenant_id: "tenant-a",
    job_id: "goal:hosted-goal-1",
    goal_ref: "intent-entry://tenant-a/hosted-goal-1",
  }]);
  assert.deepEqual(result, { receipt: receipt() });
  assert.equal(adapter.verify(result.receipt, job()), true);
  assert.deepEqual(adapter.report(result.receipt), {
    status: "planned",
    execution_id: "bounded-execution-1",
    next_job_count: 1,
  });
  assert.deepEqual(await adapter.reconcile({}), { state: "unknown" });
  assert.doesNotMatch(JSON.stringify([calls, result]), /Find and execute|private-message|secret|chat/i);
});

test("adapter rejects missing specialists and malformed or overbroad receipts", async () => {
  await assert.rejects(createGeneralAgentWorkLoopAdapter().execute(job()), /specialist/i);
  for (const malformed of [
    receipt({ tenant_id: "tenant-b" }),
    receipt({ job_id: "goal:other" }),
    receipt({ goal_ref: "intent-entry://tenant-a/other" }),
    receipt({ next_job_refs: ["https://private.example/job"] }),
    receipt({ goal_statement: "raw goal must not escape" }),
  ]) {
    const adapter = createGeneralAgentWorkLoopAdapter({
      async runBoundedSpecialist() { return malformed; },
    });
    await assert.rejects(adapter.execute(job()), /receipt/i);
    assert.equal(adapter.verify(malformed, job()), false);
  }
});
