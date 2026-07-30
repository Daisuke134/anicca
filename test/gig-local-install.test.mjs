import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { execFileSync, spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  realpathSync,
  readdirSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const INSTALLER = join(REPO_ROOT, "skills", "earn", "gig", "install-local.sh");
const EXPECTED_LABELS = [
  "ai.anicca.hf-gig-auditor",
  "ai.anicca.hf-gig-browser",
  "ai.anicca.hf-gig-core-healthcheck",
  "ai.anicca.hf-gig-daily-report",
  "ai.anicca.hf-gig-gmail-watch",
  "ai.anicca.hf-gig-pass",
  "ai.anicca.hf-gig-reply-detector",
  "ai.anicca.hf-gig-reply-push",
  "ai.anicca.hf-gig-selfimprove-verify",
  "ai.anicca.hf-gig-weekly-report",
];

function fixture() {
  const root = mkdtempSync(join(tmpdir(), "life-manager-gig-install-"));
  const home = join(root, "home");
  const runtime = join(root, "runtime");
  mkdirSync(home, { recursive: true });
  return { root, home, runtime };
}

function install({ home, runtime, scheduler, extraEnv = {} }) {
  const result = spawnSync(
    "bash",
    [INSTALLER, "--scheduler", scheduler, "--no-enable"],
    {
      cwd: REPO_ROOT,
      encoding: "utf8",
      env: {
        ...process.env,
        HOME: home,
        LIFE_MANAGER_HOME: runtime,
        LIFE_MANAGER_INSTALL_DEPS: "0",
        GIG_LAUNCH_AGENT_DIR: join(home, "Library", "LaunchAgents"),
        XDG_CONFIG_HOME: join(home, ".config"),
        ...extraEnv,
      },
      timeout: 30_000,
    },
  );
  assert.equal(
    result.status,
    0,
    `Gig installer failed\nstdout=${result.stdout}\nstderr=${result.stderr}`,
  );
  return JSON.parse(result.stdout.trim().split("\n").at(-1));
}

function plistJson(path) {
  return JSON.parse(
    execFileSync("plutil", ["-convert", "json", "-o", "-", path], {
      encoding: "utf8",
    }),
  );
}

function digest(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

test("fresh macOS install renders all launchd units and is idempotent", () => {
  const { home, runtime } = fixture();
  const first = install({ home, runtime, scheduler: "launchd" });
  const launchAgents = join(home, "Library", "LaunchAgents");
  const state = realpathSync(join(runtime, "state", "gig"));

  assert.equal(first.state_dir, state);
  assert.equal(first.adopted_legacy_state, false);
  assert.deepEqual(first.units.sort(), EXPECTED_LABELS);
  assert.equal(existsSync(state), true);

  const installed = readdirSync(launchAgents)
    .filter((name) => name.endsWith(".plist"))
    .sort();
  assert.deepEqual(
    installed,
    EXPECTED_LABELS.map((label) => `${label}.plist`).sort(),
  );

  const before = new Map();
  for (const name of installed) {
    const path = join(launchAgents, name);
    const text = readFileSync(path, "utf8");
    const value = plistJson(path);
    assert.equal(text.includes("__LIFE_MANAGER_"), false);
    assert.equal(text.includes("__HOME__"), false);
    assert.equal(text.includes("__GIG_STATE_DIR__"), false);
    assert.equal(value.EnvironmentVariables.LIFE_MANAGER_REPO, REPO_ROOT);
    assert.equal(value.EnvironmentVariables.LIFE_MANAGER_HOME, realpathSync(runtime));
    assert.equal(value.EnvironmentVariables.GIG_STATE_DIR, state);
    assert.equal(
      value.ProgramArguments.some((arg) => arg.includes("profitable-claude")),
      false,
    );
    assert.equal(
      value.ProgramArguments.some((arg) => arg.includes(REPO_ROOT)),
      true,
      `${name} must execute canonical Life Manager source`,
    );
    before.set(name, digest(path));
  }

  const second = install({ home, runtime, scheduler: "launchd" });
  assert.equal(second.state_dir, state);
  for (const name of installed) {
    assert.equal(digest(join(launchAgents, name)), before.get(name));
  }
});

test("existing HOME/gig state is adopted in place without copying or mutation", () => {
  const { home, runtime } = fixture();
  const legacy = join(home, "gig");
  mkdirSync(legacy, { recursive: true });
  const ledger = join(legacy, "applied.jsonl");
  const database = join(legacy, "outbox.sqlite3");
  writeFileSync(ledger, '{"request_id":"fixture-1","status":"applied"}\n');
  writeFileSync(database, Buffer.from([0x53, 0x51, 0x4c, 0x69, 0x74, 0x65]));
  const ledgerHash = digest(ledger);
  const databaseHash = digest(database);

  const first = install({ home, runtime, scheduler: "none" });
  const second = install({ home, runtime, scheduler: "none" });

  assert.equal(first.state_dir, realpathSync(legacy));
  assert.equal(first.adopted_legacy_state, true);
  assert.equal(second.state_dir, realpathSync(legacy));
  assert.equal(digest(ledger), ledgerHash);
  assert.equal(digest(database), databaseHash);
  assert.equal(readFileSync(ledger, "utf8").trim().split("\n").length, 1);
  assert.equal(existsSync(join(runtime, "state", "gig", "applied.jsonl")), false);

  const receipt = JSON.parse(
    readFileSync(join(runtime, "state", "gig-install.json"), "utf8"),
  );
  assert.equal(receipt.state_dir, realpathSync(legacy));
  assert.equal(receipt.adopted_legacy_state, true);
});

test("Linux install derives services and timers from the launchd templates", () => {
  const { home, runtime } = fixture();
  const result = install({ home, runtime, scheduler: "systemd" });
  const unitDir = join(home, ".config", "systemd", "user");
  const files = readdirSync(unitDir).sort();
  const services = files.filter((name) => name.endsWith(".service"));
  const timers = files.filter((name) => name.endsWith(".timer"));

  assert.deepEqual(
    services,
    EXPECTED_LABELS.map((label) => `${label}.service`).sort(),
  );
  assert.equal(timers.length, 7);
  assert.deepEqual(result.units.sort(), EXPECTED_LABELS);

  for (const name of files) {
    const text = readFileSync(join(unitDir, name), "utf8");
    assert.equal(text.includes("__LIFE_MANAGER_"), false);
    assert.equal(text.includes("__HOME__"), false);
    assert.equal(text.includes("__GIG_STATE_DIR__"), false);
    assert.equal(text.includes("profitable-claude"), false);
    if (name.endsWith(".service")) {
      assert.match(text, new RegExp(`Environment="LIFE_MANAGER_REPO=${REPO_ROOT}`));
      assert.match(text, /Environment="GIG_STATE_DIR=.*runtime\/state\/gig"/);
      assert.equal(text.includes(`ExecStart=`), true);
      assert.equal(text.includes(REPO_ROOT), true);
    }
  }
});
