import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";

const REPO_ROOT = new URL("../", import.meta.url).pathname;

function parsePlist(path) {
  const result = spawnSync("python3", ["-c", [
    "import json, plistlib, sys",
    "print(json.dumps(plistlib.loads(open(sys.argv[1], 'rb').read())))",
  ].join(";"), path], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

test("agent-economy launchd declaration uses the immutable release and continuous contract", () => {
  const root = mkdtempSync(join(tmpdir(), "agent-economy-plist-"));
  const home = join(root, "home");
  const out = join(root, "launchagents");
  const current = join(home, "loops", "current");
  const logs = join(home, "loops", "logs");

  try {
    const generated = spawnSync("python3", [
      join(REPO_ROOT, "bin", "plistgen.py"),
      "--loops-dir", join(REPO_ROOT, "loops"),
      "--out-dir", out,
      "--home", home,
      "--current", current,
      "--logs", logs,
      "--only", "agent-economy",
    ], { cwd: REPO_ROOT, encoding: "utf8" });
    assert.equal(generated.status, 0, `${generated.stdout}\n${generated.stderr}`);

    const plist = parsePlist(join(out, "ai.anicca.agent-economy-loop.plist"));
    assert.deepEqual(plist.ProgramArguments, [
      "/bin/bash",
      join(current, "skills", "agent-economy", "launch.sh"),
    ]);
    assert.equal(plist.KeepAlive, true);
    assert.equal(plist.RunAtLoad, true);
    assert.equal(plist.StartInterval, undefined);
    assert.equal(plist.StartCalendarInterval, undefined);
    assert.equal(plist.EnvironmentVariables.ANICCA_REPO, current);
    assert.equal(plist.EnvironmentVariables.ANICCA_HOME, join(home, "loops", "agent-economy"));
    assert.deepEqual(plist.EnvironmentVariables.ANICCA_SLOT_ALLOWLIST.split(","), [
      "earn/taskmarket", "x402_sell", "report", "cook",
    ]);
    assert.equal(plist.EnvironmentVariables.ANICCA_ECONOMY_RECONCILE, "1");
    assert.equal(plist.ProgramArguments.join(" ").includes(".worktrees"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
