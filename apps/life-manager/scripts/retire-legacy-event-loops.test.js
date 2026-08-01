"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  CRON_TARGETS,
  LAUNCHD_TARGETS,
  buildRetirementPlan,
  verifyRetiredState,
} = require("./retire-legacy-event-loops.js");

function state(overrides = {}) {
  return {
    uid: 501,
    launchd: LAUNCHD_TARGETS.map((target) => ({
      ...target,
      loaded: true,
      plist: "active",
    })),
    cron: CRON_TARGETS.map((target) => ({
      ...target,
      enabled: true,
    })),
    ...overrides,
  };
}

test("exact allowlistだけをreversibleな退役operationへ変換する", () => {
  const plan = buildRetirementPlan(state());

  assert.equal(plan.length, LAUNCHD_TARGETS.length * 2 + CRON_TARGETS.length);
  assert.deepEqual(plan.slice(0, 2), [
    { kind: "launchd_bootout", label: LAUNCHD_TARGETS[0].label, uid: 501 },
    { kind: "plist_retire", label: LAUNCHD_TARGETS[0].label },
  ]);
  assert.deepEqual(
    plan.filter(({ kind }) => kind === "cron_disable").map(({ id }) => id),
    CRON_TARGETS.map(({ id }) => id),
  );
});

test("cron name drift、target欠落、plist衝突はfail closedする", () => {
  const wrongName = state();
  wrongName.cron[0].name = "lookalike";
  assert.throws(() => buildRetirementPlan(wrongName), /legacy event retirement state invalid/);

  const missing = state({ cron: state().cron.slice(1) });
  assert.throws(() => buildRetirementPlan(missing), /legacy event retirement state invalid/);

  const conflict = state();
  conflict.launchd[0].plist = "conflict";
  assert.throws(() => buildRetirementPlan(conflict), /legacy event retirement state invalid/);
});

test("既に退役済みならoperation 0でpostconditionを満たす", () => {
  const retired = state({
    launchd: LAUNCHD_TARGETS.map((target) => ({
      ...target,
      loaded: false,
      plist: "retired",
    })),
    cron: CRON_TARGETS.map((target) => ({
      ...target,
      enabled: false,
    })),
  });

  assert.deepEqual(buildRetirementPlan(retired), []);
  assert.deepEqual(verifyRetiredState(retired), {
    launchd_retired: 2,
    cron_disabled: 6,
  });
});

test("loaded launchd、active plist、enabled cronはpostconditionにならない", () => {
  assert.throws(() => verifyRetiredState(state()), /legacy event retirement incomplete/);
});
