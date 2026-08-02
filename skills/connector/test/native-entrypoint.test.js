"use strict";

const assert = require("node:assert/strict");
const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  acquireLock,
  heartbeat,
  readHealth,
  releaseLock,
} = require("../lib/native-state.js");

const REPO_ROOT = path.resolve(__dirname, "../../..");
const ENTRYPOINT = path.join(REPO_ROOT, "skills/connector/run.sh");
const HEALTHCHECK = path.join(REPO_ROOT, "skills/connector/healthcheck.sh");
const RENDERER = path.join(REPO_ROOT, "skills/connector/render-launchd.sh");

function temporaryDirectory() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "connector-native-entrypoint-"));
}

function fixtureWorker(directory, exitCode = 0) {
  const worker = path.join(directory, "bounded-worker.sh");
  const counter = path.join(directory, "worker-count");
  const observedRoot = path.join(directory, "worker-repo-root");
  fs.writeFileSync(worker, [
    "#!/usr/bin/env bash",
    "set -eu",
    `printf '%s' \"\${CONNECTOR_NATIVE_REPO_ROOT}\" > ${JSON.stringify(observedRoot)}`,
    `printf '1\\n' >> ${JSON.stringify(counter)}`,
    `exit ${exitCode}`,
  ].join("\n"), { mode: 0o700 });
  return { counter, observedRoot, worker };
}

function runEntrypoint(directory, worker, extra = {}) {
  const stateDir = path.join(directory, "state");
  const envFile = path.join(directory, "connector.env");
  fs.writeFileSync(envFile, "CONNECTOR_NATIVE_TEST_SECRET=not-for-stdout\n", { mode: 0o600 });
  return spawnSync("bash", [ENTRYPOINT], {
    cwd: directory,
    encoding: "utf8",
    env: {
      ...process.env,
      HOME: directory,
      LM_CONNECTOR_ENV_FILE: envFile,
      LM_CONNECTOR_STATE_DIR: stateDir,
      CONNECTOR_NATIVE_WORKER_BIN: worker,
      CONNECTOR_NATIVE_WORKER_TIMEOUT_MS: "1000",
      ...extra,
    },
  });
}

test("run.sh resolves the canonical repository, runs one bounded worker, and releases its lock", () => {
  const directory = temporaryDirectory();
  try {
    const fixture = fixtureWorker(directory);
    const result = runEntrypoint(directory, fixture.worker);

    assert.equal(result.status, 0, result.stderr);
    assert.equal(fs.readFileSync(fixture.counter, "utf8"), "1\n");
    assert.equal(fs.readFileSync(fixture.observedRoot, "utf8"), REPO_ROOT);
    assert.equal(result.stdout.includes("not-for-stdout"), false);
    assert.deepEqual(readHealth({
      stateDir: path.join(directory, "state"),
      now: new Date().toISOString(),
      staleMs: 60_000,
    }).lock, { status: "idle" });
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("a live lock skips the worker and exits without declaring coverage complete", () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  try {
    const fixture = fixtureWorker(directory);
    assert.deepEqual(acquireLock({
      stateDir,
      token: "other-owner-token-123456",
      pid: process.pid,
      now: new Date().toISOString(),
      staleMs: 60_000,
    }), { status: "acquired" });

    const result = runEntrypoint(directory, fixture.worker);
    assert.equal(result.status, 75, result.stderr);
    assert.equal(fs.existsSync(fixture.counter), false);
    assert.equal(/complete/i.test(result.stdout), false);
  } finally {
    releaseLock({ stateDir, token: "other-owner-token-123456" });
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("a failed bounded worker persists continuation and keeps a nonzero exit", () => {
  const directory = temporaryDirectory();
  try {
    const fixture = fixtureWorker(directory, 7);
    const result = runEntrypoint(directory, fixture.worker);

    assert.equal(result.status, 7, result.stderr);
    assert.deepEqual(JSON.parse(fs.readFileSync(
      path.join(directory, "state", "continuation.json"), "utf8",
    )), {
      reason: "worker_failed",
      status: "pending",
    });
    assert.deepEqual(readHealth({
      stateDir: path.join(directory, "state"),
      now: new Date().toISOString(),
      staleMs: 60_000,
    }).heartbeat, { status: "fresh", stage: "worker_failed" });
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
