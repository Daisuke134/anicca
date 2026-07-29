"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const {
  inventoryLegacyJobs,
  loadLaunchAgents,
  redactCommand,
  sourceBoundary,
} = require("./inventory-legacy-jobs.js");

test("inventoryLegacyJobs keeps enabled and disabled jobs without mutating inputs", () => {
  const cronRows = [
    {
      id: "cron-disabled",
      name: "disabled history",
      enabled: false,
      schedule: { kind: "cron", expr: "0 5 * * *", tz: "Asia/Tokyo" },
      payload: { message: "Use exec to run: /Users/operator/.openclaw/disabled.sh" },
      state: {},
    },
    {
      id: "cron-live",
      name: "live cron",
      enabled: true,
      schedule: { kind: "every", everyMs: 60000 },
      payload: { message: "Use exec to run: /Users/operator/profitable-claude/live.sh" },
      state: { lastRunAtMs: 1234, lastStatus: "ok" },
    },
  ];
  const launchAgents = [
    {
      Label: "ai.anicca.life-manager-daily",
      ProgramArguments: ["/bin/bash", "/Users/operator/Projects/life-manager-main/run.sh"],
      StartCalendarInterval: { Hour: 10, Minute: 15 },
    },
  ];
  const loaded = {
    "ai.anicca.life-manager-daily": { pid: 456, lastExitStatus: 0 },
  };
  const before = JSON.stringify({ cronRows, launchAgents, loaded });

  const result = inventoryLegacyJobs({ cronRows, launchAgents, loadedLabels: loaded });

  assert.equal(JSON.stringify({ cronRows, launchAgents, loaded }), before);
  assert.equal(result.jobs.length, 3);
  assert.deepEqual(result.jobs.map((job) => job.legacy_id), [
    "ai.anicca.life-manager-daily",
    "cron-disabled",
    "cron-live",
  ]);
  assert.deepEqual(result.summary.schedulers, { launchd: 1, openclaw: 2 });
  assert.equal(result.summary.enabled_or_loaded, 2);
  assert.equal(result.summary.unclassified, 3);
  assert.equal(result.jobs[0].loaded, true);
  assert.equal(result.jobs[1].enabled, false);
  assert.equal(result.jobs[2].latest_receipt.status, "ok");
});

test("inventoryLegacyJobs preserves relevant loaded labels with no plist", () => {
  const result = inventoryLegacyJobs({
    cronRows: [],
    launchAgents: [],
    loadedLabels: {
      "com.anicca.daemon": { pid: "123", lastExitStatus: "0" },
      "com.apple.system": { pid: "456", lastExitStatus: "0" },
    },
  });

  assert.equal(result.jobs.length, 1);
  assert.equal(result.jobs[0].legacy_id, "com.anicca.daemon");
  assert.equal(result.jobs[0].loaded, true);
  assert.match(result.jobs[0].parse_error, /no user LaunchAgent plist/);
});

test("redactCommand removes credentials, personal identifiers, account ids, and host username", () => {
  const raw = [
    "TELEGRAM_BOT_TOKEN=secret-token",
    "/Users/operator/.openclaw/run.sh",
    "--target", "0000000000",
    "--tt", "cmnit95mg015rrm0ye5vm8dhl",
    "--email", "owner@example.com",
    "https://example.com/run?token=secret-query&api_key=secret-key",
  ].join(" ");

  const redacted = redactCommand(raw);

  for (const secret of [
    "secret-token",
    "0000000000",
    "cmnit95mg015rrm0ye5vm8dhl",
    "owner@example.com",
    "secret-query",
    "secret-key",
    "/Users/operator",
  ]) {
    assert.equal(redacted.includes(secret), false, `must remove ${secret}`);
  }
  assert.match(redacted, /\$HOME/);
  assert.match(redacted, /\[REDACTED_TOKEN\]/);
  assert.match(redacted, /\[REDACTED_TARGET\]/);
  assert.match(redacted, /\[REDACTED_ACCOUNT\]/);
  assert.match(redacted, /\[REDACTED_EMAIL\]/);
});

test("inventory stores only redacted commands and stable fingerprints", () => {
  const cronRows = [{
    id: "private-cron-1745866079164",
    name: "private",
    enabled: true,
    schedule: { kind: "cron", expr: "5 * * * *", tz: "Asia/Tokyo" },
    payload: {
      message: "TOKEN=abc123 /Users/operator/.openclaw/run.sh --target 0000000000",
    },
    state: {},
  }];

  const first = inventoryLegacyJobs({ cronRows, launchAgents: [], loadedLabels: {} });
  const second = inventoryLegacyJobs({ cronRows, launchAgents: [], loadedLabels: {} });

  assert.equal(first.jobs[0].command.includes("abc123"), false);
  assert.equal(first.jobs[0].command.includes("0000000000"), false);
  assert.equal(first.jobs[0].legacy_id.includes("1745866079164"), false);
  assert.match(first.jobs[0].legacy_id, /\[REDACTED_NUMBER_[a-p]{8}\]/);
  assert.match(first.jobs[0].command_fingerprint, /^[a-p]{16}$/);
  assert.equal(first.jobs[0].command_fingerprint, second.jobs[0].command_fingerprint);
});

test("redactCommand removes connector account ids even when passed positionally", () => {
  const redacted = redactCommand(
    "/bin/bash publish.sh jp morning cmo5s4edx00vgn10ygnu34a0n",
  );

  assert.equal(redacted.includes("cmo5s4edx00vgn10ygnu34a0n"), false);
  assert.match(redacted, /\[REDACTED_ACCOUNT\]/);
});

test("loadLaunchAgents preserves a malformed plist under its real launchd label", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "lm-launchagents-"));
  fs.writeFileSync(path.join(directory, "ai.anicca.cfo-daily.plist"), "malformed");

  const rows = loadLaunchAgents(directory, () => ({
    status: 1,
    stdout: "",
    stderr: "plutil failed",
  }));

  assert.equal(rows.length, 1);
  assert.equal(rows[0].__fallbackLabel, "ai.anicca.cfo-daily");
  assert.equal(rows[0].Disabled, false);
  assert.equal(rows[0].__parseError, "plutil failed");
});

test("sourceBoundary classifies canonical and legacy execution roots", () => {
  assert.equal(
    sourceBoundary("/Users/operator/Projects/life-manager-main/apps/life-manager/server.js"),
    "canonical_life_manager",
  );
  assert.equal(sourceBoundary("/Users/operator/.openclaw/skills/x/run.sh"), "openclaw");
  assert.equal(sourceBoundary("/Users/operator/profitable-claude/run.sh"), "profitable_claude");
  assert.equal(sourceBoundary("/Users/operator/anicca/skills/x/run.sh"), "anicca_legacy");
  assert.equal(sourceBoundary("/usr/bin/true"), "system_or_other");
});
