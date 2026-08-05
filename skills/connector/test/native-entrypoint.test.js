"use strict";

const assert = require("node:assert/strict");
const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { runNativePass } = require("../native-pass.js");
const {
  acquireLock,
  heartbeat,
  readHealth,
  releaseLock,
} = require("../lib/native-state.js");

const REPO_ROOT = path.resolve(__dirname, "../../..");
const HEALTHCHECK = path.join(REPO_ROOT, "skills/connector/healthcheck.sh");
const RENDERER = path.join(REPO_ROOT, "skills/connector/render-launchd.sh");

const OWNER_TOKEN = "native-pass-test-owner-123456";

function temporaryDirectory() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "connector-native-entrypoint-"));
}

test("native-pass invokes the direct runtime and keeps open coverage as a continuation", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  const observed = [];
  try {
    const result = await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir,
      ownerToken: OWNER_TOKEN,
      config: {
        tenantId: "dais-local",
        timeZone: "Asia/Tokyo",
        now: "2026-08-02T01:00:00.000Z",
        evidenceDir: path.join(directory, "evidence"),
        calendarAccount: "dais@example.test",
      },
      runRuntime: async (input) => {
        observed.push(input);
        return {
          status: "incomplete",
          coverage: { counts: { open: 21 } },
          continuation: { status: "continue" },
        };
      },
    });

    assert.equal(result.exitCode, 1);
    assert.equal(observed.length, 1);
    assert.equal(observed[0].config.tenantId, "dais-local");
    assert.deepEqual(JSON.parse(fs.readFileSync(
      path.join(stateDir, "continuation.json"), "utf8",
    )), {
      reason: "runtime_incomplete",
      status: "pending",
    });
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(stateDir, "last-result.json"), "utf8")), {
      status: "incomplete",
      coverage_counts: { open: 21, covered_existing: 0, covered_new: 0, unavailable: 0 },
      write: null,
    });
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("native-pass forwards the complete launchd-owned Connector loop configuration", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  let observed;
  try {
    await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir,
      ownerToken: OWNER_TOKEN,
      env: {
        GOG_ACCOUNT: "dais@example.test",
        LM_CONNECTOR_PROFILE_PATH: path.join(REPO_ROOT, "apps/life-manager/config/connector/dais-local.json"),
        LM_CONNECTOR_TELEGRAM_TARGET: "123456",
        LM_CONNECTOR_CALENDAR_ID: "primary",
        LM_CONNECTOR_CALENDAR_COVERAGE_URL: "https://calendar.google.com/calendar/u/0/r",
        LIFE_HOME_ADDRESS: "Tokyo home",
        GOOGLE_API_KEY_DIRECTIONS: "maps-secret",
      },
      runRuntime: async (input) => {
        observed = input.config;
        return { status: "incomplete", coverage: { counts: { open: 21 } }, continuation: { status: "continue" } };
      },
    });
    assert.equal(observed.profilePath.endsWith("config/connector/dais-local.json"), true);
    assert.equal(observed.lunaEvidenceDir, path.join(stateDir, "luna"));
    assert.equal(observed.telegramTarget, "123456");
    assert.equal(observed.calendarId, "primary");
    assert.equal(observed.homeLocation, "Tokyo home");
    assert.equal(observed.mapsKey, "maps-secret");
    assert.equal(observed.repoRoot, REPO_ROOT);
    assert.equal(observed.lumaEmail, "dais@example.test");
    assert.equal(observed.lumaName, "Dais");
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("native-pass forwards validated delivery history for coverage restoration", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  fs.mkdirSync(stateDir, { recursive: true });
  fs.writeFileSync(path.join(stateDir, "delivery-receipts.jsonl"), `${JSON.stringify({
    event_ref: "luma-event://event/verified-one",
    calendar_event_ref: `calendar-evidence://google/event/${"a".repeat(64)}`,
    telegram_provider_id: "7372",
  })}\n`);
  let observed;
  try {
    await runNativePass({
      repoRoot: REPO_ROOT, stateDir, ownerToken: OWNER_TOKEN,
      env: {
        GOG_ACCOUNT: "dais@example.test", LM_CONNECTOR_TELEGRAM_TARGET: "123456",
        LIFE_HOME_ADDRESS: "Tokyo", GOOGLE_API_KEY_DIRECTIONS: "maps-secret",
      },
      runRuntime: async (input) => {
        observed = input.config.deliveredReceipts;
        return { status: "incomplete", coverage: { counts: { open: 20 } }, continuation: { status: "continue" } };
      },
    });
    assert.equal(observed.length, 1);
    assert.equal(observed[0].event_ref, "luma-event://event/verified-one");
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test("native-pass keeps successful Calendar and Telegram receipts in append-only deduped history", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  const runtimeResult = {
    status: "incomplete",
    coverage: { counts: { open: 20 } },
    continuation: { status: "continue" },
    write: {
      status: "incomplete", outcome: "open_coverage", event_ref: "luma-event://event/verified-one",
      calendar_sync: { calendar_event_ref: `calendar-evidence://google/event/${"a".repeat(64)}` },
      telegram: { provider_id: "7372" },
    },
  };
  try {
    for (let count = 0; count < 2; count += 1) {
      await runNativePass({
        repoRoot: REPO_ROOT, stateDir, ownerToken: OWNER_TOKEN,
        config: { tenantId: "dais-local" }, runRuntime: async () => runtimeResult,
      });
    }
    const lines = fs.readFileSync(path.join(stateDir, "delivery-receipts.jsonl"), "utf8").trim().split("\n");
    assert.equal(lines.length, 1);
    assert.deepEqual(JSON.parse(lines[0]), {
      event_ref: "luma-event://event/verified-one",
      calendar_event_ref: `calendar-evidence://google/event/${"a".repeat(64)}`,
      telegram_provider_id: "7372",
    });
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test("native-pass migrates the previous successful last result before the next runtime", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  fs.mkdirSync(stateDir, { recursive: true });
  fs.writeFileSync(path.join(stateDir, "last-result.json"), JSON.stringify({
    status: "incomplete",
    write: {
      status: "incomplete", outcome: "open_coverage", event_ref: "luma-event://event/pending-one",
      calendar_event_ref: `calendar-evidence://google/event/${"b".repeat(64)}`,
      telegram_provider_id: "7372",
    },
  }));
  try {
    await runNativePass({
      repoRoot: REPO_ROOT, stateDir, ownerToken: OWNER_TOKEN,
      config: { tenantId: "dais-local" },
      runRuntime: async () => ({
        status: "incomplete", coverage: { counts: { open: 21 } }, continuation: { status: "continue" },
      }),
    });
    const receipt = JSON.parse(fs.readFileSync(path.join(stateDir, "delivery-receipts.jsonl"), "utf8"));
    assert.equal(receipt.telegram_provider_id, "7372");
    assert.equal(receipt.event_ref, "luma-event://event/pending-one");
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test("launchd run script restores Connector credentials and Telegram owner without a manual env file", () => {
  const source = fs.readFileSync(path.join(REPO_ROOT, "skills/connector/run.sh"), "utf8");
  assert.match(source, /\.openclaw\/\.env/);
  assert.match(source, /telegram-default-allowFrom\.json/);
  assert.match(source, /LM_CONNECTOR_TELEGRAM_TARGET/);
});

test("launchd run script uses an allowlisted Connector env reader instead of the legacy-root-rejecting loader", () => {
  const source = fs.readFileSync(path.join(REPO_ROOT, "skills/connector/run.sh"), "utf8");
  assert.match(source, /load-connector-env\.js/);
  assert.doesNotMatch(source, /lm_load_env_file "\$LM_CONNECTOR_SHARED_ENV_FILE"/);
});

test("native-pass ignores CONNECTOR_NATIVE_WORKER_BIN and still invokes the direct runtime", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  const ignoredWorker = path.join(directory, "ignored-worker");
  fs.writeFileSync(ignoredWorker, "this file must never be executed\n", { mode: 0o600 });
  const observed = [];
  try {
    const result = await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir,
      ownerToken: OWNER_TOKEN,
      env: { CONNECTOR_NATIVE_WORKER_BIN: ignoredWorker },
      config: {
        tenantId: "dais-local",
        timeZone: "Asia/Tokyo",
        now: "2026-08-02T01:00:00.000Z",
        evidenceDir: path.join(directory, "evidence"),
        calendarAccount: "dais@example.test",
      },
      runRuntime: async () => {
        observed.push(true);
        return {
          status: "incomplete",
          coverage: { counts: { open: 21 } },
          continuation: { status: "continue" },
        };
      },
    });

    assert.equal(result.exitCode, 1);
    assert.deepEqual(observed, [true]);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("native-pass exits zero only for verified open-zero coverage", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  try {
    const result = await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir,
      ownerToken: OWNER_TOKEN,
      config: {
        tenantId: "dais-local",
        timeZone: "Asia/Tokyo",
        now: "2026-08-02T01:00:00.000Z",
        evidenceDir: path.join(directory, "evidence"),
        calendarAccount: "dais@example.test",
      },
      runRuntime: async () => ({
        status: "complete",
        coverage: { counts: { open: 0 } },
        continuation: { status: "complete" },
      }),
    });

    assert.deepEqual(result, { exitCode: 0, status: "complete" });
    assert.equal(fs.existsSync(path.join(stateDir, "continuation.json")), false);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("native-pass records only an allowlisted runtime failure stage", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  try {
    const result = await runNativePass({
      repoRoot: REPO_ROOT, stateDir, ownerToken: OWNER_TOKEN,
      config: { tenantId: "dais-local" },
      runRuntime: async () => {
        const error = new Error("private failure");
        error.code = "CONNECTOR_NATIVE_LUNA_FAILED";
        throw error;
      },
    });
    assert.equal(result.status, "failed");
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(stateDir, "continuation.json"), "utf8")), {
      reason: "connector_native_luna_failed", status: "pending",
    });
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test("native-pass CLI terminates its bounded process after durable state is written", () => {
  const source = fs.readFileSync(path.join(REPO_ROOT, "skills/connector/native-pass.js"), "utf8");
  assert.match(source, /process\.exit\(result\.exitCode\)/);
  assert.doesNotMatch(source, /process\.exitCode = result\.exitCode/);
});

test("rendered native templates contain only canonical launch paths", () => {
  const directory = temporaryDirectory();
  try {
    const outputDir = path.join(directory, "rendered");
    const result = spawnSync("bash", [
      RENDERER,
      "--output-dir", outputDir,
      "--repo-root", REPO_ROOT,
      "--life-manager-home", path.join(directory, "life-manager-home"),
    ], { encoding: "utf8", env: { ...process.env, HOME: directory } });

    assert.equal(result.status, 0, result.stderr);
    const nativePass = fs.readFileSync(
      path.join(outputDir, "ai.anicca.life-manager-connector-native.plist"),
      "utf8",
    );
    const healthcheck = fs.readFileSync(
      path.join(outputDir, "ai.anicca.life-manager-connector-native-healthcheck.plist"),
      "utf8",
    );
    assert.equal(nativePass.includes(path.join(REPO_ROOT, "skills/connector/run.sh")), true);
    assert.equal(healthcheck.includes(path.join(REPO_ROOT, "skills/connector/healthcheck.sh")), true);
    assert.doesNotMatch(`${nativePass}\n${healthcheck}`, /docker|host\.docker\.internal|connector-host-bridge|profitable-claude/i);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("renderer rejects the live LaunchAgents directory after path normalization", () => {
  const directory = temporaryDirectory();
  try {
    const liveOutput = `${path.join(directory, "Library", "LaunchAgents")}/`;
    const result = spawnSync("bash", [
      RENDERER,
      "--output-dir", liveOutput,
      "--repo-root", REPO_ROOT,
      "--life-manager-home", path.join(directory, "life-manager-home"),
    ], { encoding: "utf8", env: { ...process.env, HOME: directory } });

    assert.equal(result.status, 2, result.stderr);
    assert.equal(fs.existsSync(liveOutput), false);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("healthcheck rejects a stale heartbeat without a recovery command", () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  try {
    const gog = path.join(directory, "gog");
    const probe = path.join(directory, "healthy-browser-probe");
    const probeCount = path.join(directory, "probe-count");
    fs.writeFileSync(gog, "#!/usr/bin/env bash\nexit 0\n", { mode: 0o700 });
    fs.writeFileSync(probe, [
      "#!/usr/bin/env bash",
      "set -eu",
      `printf '1\\n' >> ${JSON.stringify(probeCount)}`,
      "exit 0",
    ].join("\n"), { mode: 0o700 });
    assert.deepEqual(acquireLock({
      stateDir,
      token: "health-owner-token-123456",
      pid: process.pid,
      now: "2026-08-02T00:00:00.000Z",
      staleMs: 60_000,
    }), { status: "acquired" });
    assert.deepEqual(heartbeat({
      stateDir,
      token: "health-owner-token-123456",
      stage: "worker_started",
      now: "2026-08-02T00:00:00.000Z",
    }), { status: "updated" });
    assert.deepEqual(releaseLock({ stateDir, token: "health-owner-token-123456" }), { status: "released" });

    const result = spawnSync("bash", [HEALTHCHECK], {
      encoding: "utf8",
      env: {
        ...process.env,
        HOME: directory,
        LM_CONNECTOR_STATE_DIR: stateDir,
        LM_CONNECTOR_HEARTBEAT_STALE_MS: "1",
        GOG_BIN: gog,
        CONNECTOR_NATIVE_HEALTH_PROBE_BIN: probe,
      },
    });
    assert.equal(result.status, 1, result.stderr);
    assert.equal(fs.existsSync(probeCount), false);
    assert.equal(fs.readFileSync(HEALTHCHECK, "utf8").includes("launchctl"), false);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("healthcheck reports healthy only after fresh state and read-only dependencies succeed", () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  try {
    const gog = path.join(directory, "gog");
    const probe = path.join(directory, "healthy-browser-probe");
    const probeCount = path.join(directory, "probe-count");
    fs.writeFileSync(gog, "#!/usr/bin/env bash\nexit 0\n", { mode: 0o700 });
    fs.writeFileSync(probe, [
      "#!/usr/bin/env bash",
      "set -eu",
      `printf '1\\n' >> ${JSON.stringify(probeCount)}`,
      "exit 0",
    ].join("\n"), { mode: 0o700 });
    const token = "fresh-health-owner-token-123456";
    const now = new Date().toISOString();
    assert.deepEqual(acquireLock({
      stateDir,
      token,
      pid: process.pid,
      now,
      staleMs: 60_000,
    }), { status: "acquired" });
    assert.deepEqual(heartbeat({
      stateDir,
      token,
      stage: "worker_finished",
      now,
    }), { status: "updated" });
    assert.deepEqual(releaseLock({ stateDir, token }), { status: "released" });

    const result = spawnSync("bash", [HEALTHCHECK], {
      encoding: "utf8",
      env: {
        ...process.env,
        HOME: directory,
        LM_CONNECTOR_STATE_DIR: stateDir,
        LM_CONNECTOR_HEARTBEAT_STALE_MS: "60000",
        GOG_BIN: gog,
        CONNECTOR_NATIVE_HEALTH_PROBE_BIN: probe,
      },
    });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(fs.readFileSync(probeCount, "utf8"), "1\n");
    assert.equal(result.stdout, '{"status":"healthy"}\n');
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("healthcheck restores the Homebrew PATH under a launchd-like minimal environment", () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  try {
    const probe = path.join(directory, "healthy-browser-probe");
    const probeCount = path.join(directory, "probe-count");
    fs.writeFileSync(probe, [
      "#!/usr/bin/env bash",
      "set -eu",
      `printf '1\\n' >> ${JSON.stringify(probeCount)}`,
      "exit 0",
    ].join("\n"), { mode: 0o700 });
    const token = "launchd-path-owner-token-123456";
    const now = new Date().toISOString();
    assert.deepEqual(acquireLock({
      stateDir,
      token,
      pid: process.pid,
      now,
      staleMs: 60_000,
    }), { status: "acquired" });
    assert.deepEqual(heartbeat({
      stateDir,
      token,
      stage: "worker_finished",
      now,
    }), { status: "updated" });
    assert.deepEqual(releaseLock({ stateDir, token }), { status: "released" });

    const result = spawnSync("/bin/bash", [HEALTHCHECK], {
      encoding: "utf8",
      env: {
        ...process.env,
        HOME: directory,
        PATH: "/usr/bin:/bin",
        LM_CONNECTOR_STATE_DIR: stateDir,
        LM_CONNECTOR_HEARTBEAT_STALE_MS: "60000",
        CONNECTOR_NATIVE_HEALTH_PROBE_BIN: probe,
      },
    });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(fs.readFileSync(probeCount, "utf8"), "1\n");
    assert.equal(result.stdout, '{"status":"healthy"}\n');
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
