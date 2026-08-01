#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const LAUNCHD_TARGETS = Object.freeze([
  Object.freeze({ label: "ai.anicca.connector-fill-gaps" }),
  Object.freeze({ label: "ai.anicca.connector-daily-report" }),
]);

const CRON_TARGETS = Object.freeze([
  Object.freeze({
    id: "anicca-meetup-discover-daily-1777976530000",
    name: "anicca-meetup-discover-daily",
  }),
  Object.freeze({
    id: "anicca-meetup-apply-tokyo-weekly-1777976530000",
    name: "anicca-meetup-apply-tokyo-weekly",
  }),
  Object.freeze({
    id: "anicca-meetup-apply-sf-monthly-1777976530000",
    name: "anicca-meetup-apply-sf-monthly",
  }),
  Object.freeze({
    id: "anicca-meetup-accept-watch-6h-1777976530000",
    name: "anicca-meetup-accept-watch-6h",
  }),
  Object.freeze({
    id: "connpass-lt-apply-daily-1779342348769",
    name: "connpass-lt-apply-daily",
  }),
  Object.freeze({
    id: "bf0432ba-3795-4de4-bf1b-6bc6566309d7",
    name: "anicca-night-fill",
  }),
]);

function invalid() {
  throw new Error("legacy event retirement state invalid");
}

function indexedState(state) {
  if (!state || !Number.isInteger(state.uid) || state.uid < 1) invalid();
  if (!Array.isArray(state.launchd) || !Array.isArray(state.cron)) invalid();
  if (state.launchd.length !== LAUNCHD_TARGETS.length) invalid();
  if (state.cron.length !== CRON_TARGETS.length) invalid();
  const launchd = new Map(state.launchd.map((item) => [item && item.label, item]));
  const cron = new Map(state.cron.map((item) => [item && item.id, item]));
  if (launchd.size !== LAUNCHD_TARGETS.length || cron.size !== CRON_TARGETS.length) invalid();
  for (const target of LAUNCHD_TARGETS) {
    const item = launchd.get(target.label);
    if (
      !item
      || typeof item.loaded !== "boolean"
      || !["active", "retired"].includes(item.plist)
    ) invalid();
  }
  for (const target of CRON_TARGETS) {
    const item = cron.get(target.id);
    if (!item || item.name !== target.name || typeof item.enabled !== "boolean") invalid();
  }
  return { launchd, cron };
}

function buildRetirementPlan(state) {
  const { launchd, cron } = indexedState(state);
  const operations = [];
  for (const target of LAUNCHD_TARGETS) {
    const item = launchd.get(target.label);
    if (item.loaded) {
      operations.push(Object.freeze({
        kind: "launchd_bootout",
        label: target.label,
        uid: state.uid,
      }));
    }
    if (item.plist === "active") {
      operations.push(Object.freeze({ kind: "plist_retire", label: target.label }));
    }
  }
  for (const target of CRON_TARGETS) {
    if (cron.get(target.id).enabled) {
      operations.push(Object.freeze({ kind: "cron_disable", id: target.id }));
    }
  }
  return Object.freeze(operations);
}

function verifyRetiredState(state) {
  const { launchd, cron } = indexedState(state);
  const launchdRetired = LAUNCHD_TARGETS.filter((target) => {
    const item = launchd.get(target.label);
    return item.loaded === false && item.plist === "retired";
  }).length;
  const cronDisabled = CRON_TARGETS.filter((target) => (
    cron.get(target.id).enabled === false
  )).length;
  if (
    launchdRetired !== LAUNCHD_TARGETS.length
    || cronDisabled !== CRON_TARGETS.length
  ) {
    throw new Error("legacy event retirement incomplete");
  }
  return Object.freeze({
    launchd_retired: launchdRetired,
    cron_disabled: cronDisabled,
  });
}

function run(command, args, options = {}) {
  return spawnSync(command, args, {
    encoding: "utf8",
    timeout: 30_000,
    ...options,
  });
}

function plistPaths(baseDir, label) {
  const active = path.join(baseDir, `${label}.plist`);
  return { active, retired: `${active}.retired` };
}

function collectLiveState(boundaries = {}) {
  const runCommand = boundaries.run || run;
  const exists = boundaries.exists || fs.existsSync;
  const uid = boundaries.uid == null ? process.getuid() : boundaries.uid;
  const launchAgentsDir = boundaries.launchAgentsDir || path.join(os.homedir(), "Library/LaunchAgents");
  const launchd = LAUNCHD_TARGETS.map((target) => {
    const service = runCommand("launchctl", ["print", `gui/${uid}/${target.label}`]);
    const paths = plistPaths(launchAgentsDir, target.label);
    const active = exists(paths.active);
    const retired = exists(paths.retired);
    if (active === retired) invalid();
    return {
      ...target,
      loaded: service.status === 0,
      plist: active ? "active" : "retired",
    };
  });
  const cron = CRON_TARGETS.map((target) => {
    const result = runCommand("openclaw", ["cron", "get", target.id]);
    if (result.status !== 0) invalid();
    let record;
    try {
      record = JSON.parse(result.stdout);
    } catch {
      invalid();
    }
    return {
      id: record.id,
      name: record.name,
      enabled: record.enabled,
    };
  });
  return { uid, launchd, cron };
}

function applyRetirement(plan, boundaries = {}) {
  const runCommand = boundaries.run || run;
  const rename = boundaries.rename || fs.renameSync;
  const launchAgentsDir = boundaries.launchAgentsDir || path.join(os.homedir(), "Library/LaunchAgents");
  for (const operation of plan) {
    if (operation.kind === "launchd_bootout") {
      const result = runCommand("launchctl", [
        "bootout",
        `gui/${operation.uid}/${operation.label}`,
      ]);
      if (result.status !== 0) throw new Error("legacy event retirement apply failed");
      continue;
    }
    if (operation.kind === "plist_retire") {
      const paths = plistPaths(launchAgentsDir, operation.label);
      rename(paths.active, paths.retired);
      continue;
    }
    if (operation.kind === "cron_disable") {
      const result = runCommand("openclaw", ["cron", "disable", operation.id]);
      if (result.status !== 0) throw new Error("legacy event retirement apply failed");
      continue;
    }
    throw new Error("legacy event retirement operation invalid");
  }
}

function main() {
  try {
    const apply = process.argv.slice(2).includes("--apply");
    const before = collectLiveState();
    const plan = buildRetirementPlan(before);
    if (apply) applyRetirement(plan);
    const result = apply ? verifyRetiredState(collectLiveState()) : null;
    process.stdout.write(`${JSON.stringify({
      status: apply ? "retired" : "dry_run",
      operation_count: plan.length,
      result,
    })}\n`);
  } catch {
    process.stderr.write("Legacy event retirement failed\n");
    process.exitCode = 1;
  }
}

if (require.main === module) main();

module.exports = {
  CRON_TARGETS,
  LAUNCHD_TARGETS,
  applyRetirement,
  buildRetirementPlan,
  collectLiveState,
  verifyRetiredState,
};
