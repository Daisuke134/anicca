"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { buildGoalWorkItem } = require("./goal-work-item.js");

const NOW_MS = Date.parse("2026-08-28T00:00:00.000Z");

function goal(overrides = {}) {
  return {
    id: "goal-1",
    uid: "tenant-1",
    kind: "explicit_goal",
    statement: "Apply to one permitted paid opportunity",
    provenance: {
      source: "user_message",
      evidence: "private-message-ref",
      observedAt: "2026-08-27T00:00:00.000Z",
    },
    confidenceTier: "explicit",
    confidence: 0.9,
    expiresAt: null,
    status: "active",
    supersedes: null,
    ...overrides,
  };
}

test("one active explicit goal becomes one reference-only effect-free WorkItem", () => {
  const workItem = buildGoalWorkItem(goal(), NOW_MS);
  assert.deepEqual(workItem, {
    job_id: "goal:goal-1",
    tenant_id: "tenant-1",
    loop_id: "mr-bot.manager",
    capability: "general-agent.work",
    effect_class: "none",
    effect_key: null,
    input_refs: { goal_ref: "intent-entry://tenant-1/goal-1" },
    max_attempts: 1,
  });
  assert.equal(Object.isFrozen(workItem), true);
  assert.doesNotMatch(JSON.stringify(workItem), /permitted paid opportunity|private-message-ref/);
});

test("inactive or non-goal entries cannot become WorkItems", () => {
  assert.throws(() => buildGoalWorkItem(goal(), undefined), /observation time/i);
  assert.throws(
    () => buildGoalWorkItem(goal({ expiresAt: "2026-08-27T00:00:00.000Z" }), NOW_MS),
    /active explicit goal/i,
  );
  assert.throws(
    () => buildGoalWorkItem(goal({ kind: "repeated_preference" }), NOW_MS),
    /active explicit goal/i,
  );
});
