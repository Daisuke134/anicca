import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const INSTALLER = join(REPO_ROOT, "install.sh");

function run(args) {
  const root = mkdtempSync(join(tmpdir(), "mr-bot-coconala-dispatch-"));
  const home = join(root, "home");
  const runtime = join(root, "runtime");
  const result = spawnSync("bash", [INSTALLER, ...args], {
    cwd: REPO_ROOT,
    encoding: "utf8",
    env: {
      ...process.env,
      HOME: home,
      MR_BOT_HOME: runtime,
      MR_BOT_INSTALL_DAEMON: "0",
      MR_BOT_INSTALL_DEPS: "0",
    },
    timeout: 120_000,
  });
  return { result, runtime };
}

test("coconala subcommand enters Gig installer before generic effects", () => {
  const { result, runtime } = run(["coconala", "--help"]);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Create one private, read-only capability receipt/);
  assert.equal(existsSync(runtime), false);
});

test("unknown product fails closed before generic effects", () => {
  const { result, runtime } = run(["unknown-product"]);
  assert.equal(result.status, 2);
  assert.equal(existsSync(runtime), false);
});
