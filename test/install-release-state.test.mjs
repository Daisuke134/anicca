import assert from "node:assert/strict";
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, statSync, writeFileSync, cpSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

const REPO_ROOT = new URL("../", import.meta.url).pathname;

test("installer restores a writable runtime slot root when the source is an immutable release", () => {
  const root = mkdtempSync(join(tmpdir(), "life-manager-release-install-"));
  const fixture = join(root, "release");
  const home = join(root, "home");
  const runtime = join(root, "runtime");
  mkdirSync(join(fixture, "skills", "_shared"), { recursive: true });
  mkdirSync(join(fixture, "skills", "agent-economy"), { recursive: true });
  mkdirSync(join(fixture, "identity"), { recursive: true });
  cpSync(join(REPO_ROOT, "install.sh"), join(fixture, "install.sh"));
  writeFileSync(join(fixture, ".env.example"), "FUEL=fixture\n");
  writeFileSync(join(fixture, "identity", "genesis.md"), "fixture genesis\n");
  writeFileSync(join(fixture, "skills", "_shared", "README"), "shared\n");
  writeFileSync(join(fixture, "skills", "agent-economy", "run.sh"), "#!/bin/sh\n");
  writeFileSync(join(fixture, "skills", "registry.json"), JSON.stringify({ slots: {
    "agent-economy": { dir: "skills/agent-economy", entrypoint: "run.sh", status: "dormant" },
  }}));
  chmodSync(join(fixture, "skills", "agent-economy"), 0o555);

  const result = spawnSync("bash", [join(fixture, "install.sh")], {
    cwd: fixture,
    encoding: "utf8",
    env: {
      ...process.env,
      HOME: home,
      LIFE_MANAGER_HOME: runtime,
      LIFE_MANAGER_INSTALL_DAEMON: "0",
      LIFE_MANAGER_INSTALL_DEPS: "0",
    },
  });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  const state = join(runtime, "skills", "agent-economy", "state");
  assert.equal(statSync(state).isDirectory(), true);
  assert.notEqual(statSync(join(runtime, "skills", "agent-economy")).mode & 0o200, 0);
  assert.equal(readFileSync(join(runtime, "skills", "agent-economy", "run.sh"), "utf8"), "#!/bin/sh\n");
});

