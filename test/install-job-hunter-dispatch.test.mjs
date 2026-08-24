import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const INSTALLER = join(REPO_ROOT, "install.sh");
const BOOTSTRAP = join(REPO_ROOT, "scripts", "bootstrap-job-hunter.sh");

function run(args) {
  const root = mkdtempSync(join(tmpdir(), "life-manager-job-hunter-dispatch-"));
  const home = join(root, "home");
  const runtime = join(root, "runtime");
  const result = spawnSync("bash", [INSTALLER, ...args], {
    cwd: REPO_ROOT,
    encoding: "utf8",
    env: {
      ...process.env,
      HOME: home,
      LIFE_MANAGER_HOME: runtime,
      LIFE_MANAGER_INSTALL_DAEMON: "0",
      LIFE_MANAGER_INSTALL_DEPS: "0",
    },
  });
  return { result, runtime };
}

test("job-hunter subcommand enters its installer before generic effects", () => {
  const { result, runtime } = run(["job-hunter", "status"]);
  assert.equal(result.status, 2);
  assert.equal(JSON.parse(result.stdout).status, "uninitialized");
  assert.equal(existsSync(runtime), false);
});

test("unknown product fails closed before generic effects", () => {
  const { result, runtime } = run(["unknown-product"]);
  assert.equal(result.status, 2);
  assert.equal(existsSync(runtime), false);
});

test("bootstrap rejects a non-Git checkout target before mutation", () => {
  const root = mkdtempSync(join(tmpdir(), "life-manager-job-hunter-bootstrap-"));
  const target = join(root, "life-manager");
  writeFileSync(target, "owner file", "utf8");
  const result = spawnSync("bash", [BOOTSTRAP], {
    cwd: REPO_ROOT,
    encoding: "utf8",
    env: { ...process.env, LIFE_MANAGER_CHECKOUT: target },
  });
  assert.equal(result.status, 2);
  assert.match(result.stderr, /exists but is not a Git checkout/);
  assert.equal(existsSync(target), true);
});
