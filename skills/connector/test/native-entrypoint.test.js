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
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
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
    assert.match(nativePass, /\/Users\/anicca\/Projects\/life-manager-main\/skills\/connector\/run\.sh/);
    assert.match(healthcheck, /\/Users\/anicca\/Projects\/life-manager-main\/skills\/connector\/healthcheck\.sh/);
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
