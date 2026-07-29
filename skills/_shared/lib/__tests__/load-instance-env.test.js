// node:test — _shared/lib/load-instance-env.sh: the ONE shared implementation of the
// ANICCA_HOME-preservation fix (anicca-spawn-identity-resolution-fix, 2026-07-09). Every skill
// run.sh that needs shared per-user secrets ($HOME/.hermes/.env, $HOME/.local/state/life-manager/.env) sources THIS
// file instead of hand-copying the preamble — this is the direct, root-level regression test for that
// one implementation, independent of which caller sources it.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const HELPER_PATH = path.resolve(__dirname, "../load-instance-env.sh");

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "anicca-load-instance-env-"));
}

function runHelperAndPrintEnv(env) {
  // Sources the real helper, then prints the vars we care about. Mirrors how a real run.sh would
  // source it (". $HELPER_PATH") followed by its own subsequent logic.
  const script = `. "${HELPER_PATH}"\necho "ANICCA_HOME=$ANICCA_HOME"\necho "AKASH_KEY_NAME=$AKASH_KEY_NAME"\necho "SOME_HERMES_SECRET=$SOME_HERMES_SECRET"\n`;
  return spawnSync("bash", ["-c", script], { env, encoding: "utf8" });
}

test("load-instance-env.sh preserves the caller's ANICCA_HOME across $HOME/.local/state/life-manager/.env sourcing", () => {
  const home = tmpDir();
  const callerAniccaHome = path.join(home, ".blockrun");
  fs.mkdirSync(callerAniccaHome, { recursive: true });
  const openclawDir = path.join(home, ".openclaw");
  fs.mkdirSync(openclawDir, { recursive: true });
  fs.writeFileSync(path.join(openclawDir, ".env"), `ANICCA_HOME=${openclawDir}\nAKASH_KEY_NAME=test-akash-key\n`);

  const result = runHelperAndPrintEnv({ HOME: home, ANICCA_HOME: callerAniccaHome, PATH: process.env.PATH });

  assert.equal(result.status, 0, `helper should exit 0; stderr: ${result.stderr}`);
  assert.match(result.stdout, new RegExp(`^ANICCA_HOME=${callerAniccaHome.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`, "m"));
  assert.match(result.stdout, /^AKASH_KEY_NAME=test-akash-key$/m);

  fs.rmSync(home, { recursive: true, force: true });
});

test("load-instance-env.sh preserves the caller's ANICCA_HOME across $HOME/.hermes/.env sourcing, and passes through its other vars", () => {
  const home = tmpDir();
  const callerAniccaHome = path.join(home, ".blockrun");
  fs.mkdirSync(callerAniccaHome, { recursive: true });
  const hermesDir = path.join(home, ".hermes");
  fs.mkdirSync(hermesDir, { recursive: true });
  fs.writeFileSync(path.join(hermesDir, ".env"), `ANICCA_HOME=${hermesDir}\nSOME_HERMES_SECRET=test-hermes-secret\n`);

  const result = runHelperAndPrintEnv({ HOME: home, ANICCA_HOME: callerAniccaHome, PATH: process.env.PATH });

  assert.equal(result.status, 0, `helper should exit 0; stderr: ${result.stderr}`);
  assert.match(result.stdout, new RegExp(`^ANICCA_HOME=${callerAniccaHome.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`, "m"));
  assert.match(result.stdout, /^SOME_HERMES_SECRET=test-hermes-secret$/m);

  fs.rmSync(home, { recursive: true, force: true });
});

test("load-instance-env.sh is a no-op pass-through when the caller never set ANICCA_HOME (documented edge case, REQ-001)", () => {
  const home = tmpDir();
  const openclawDir = path.join(home, ".openclaw");
  fs.mkdirSync(openclawDir, { recursive: true });
  fs.writeFileSync(path.join(openclawDir, ".env"), `ANICCA_HOME=${openclawDir}\n`);

  const env = { HOME: home, PATH: process.env.PATH };
  delete env.ANICCA_HOME;
  const result = runHelperAndPrintEnv(env);

  assert.equal(result.status, 0, `helper should exit 0; stderr: ${result.stderr}`);
  // No caller ANICCA_HOME was set -- whatever .openclaw/.env sets passes through unchanged (matches
  // pre-fix behavior for this specific edge case, per behavioral-spec.md REQ-001's own documented
  // exception).
  assert.match(result.stdout, new RegExp(`^ANICCA_HOME=${openclawDir.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`, "m"));

  fs.rmSync(home, { recursive: true, force: true });
});

test("load-instance-env.sh is a no-op when neither .hermes/.env nor .openclaw/.env exists", () => {
  const home = tmpDir();
  const callerAniccaHome = path.join(home, ".blockrun");

  const result = runHelperAndPrintEnv({ HOME: home, ANICCA_HOME: callerAniccaHome, PATH: process.env.PATH });

  assert.equal(result.status, 0, `helper should exit 0; stderr: ${result.stderr}`);
  assert.match(result.stdout, new RegExp(`^ANICCA_HOME=${callerAniccaHome.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`, "m"));

  fs.rmSync(home, { recursive: true, force: true });
});
