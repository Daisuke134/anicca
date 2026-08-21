import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import test from "node:test";

const ROOT = new URL("../", import.meta.url).pathname;
const SCRIPT = join(ROOT, "skills", "agent-economy", "retire-legacy-jobs.sh");

test("legacy job retirement is explicit and disabled by default", async () => {
  const source = await readFile(SCRIPT, "utf8");
  for (const label of [
    "ai.anicca.citizen-refill",
    "ai.anicca.x402-acquisition-controller",
    "ai.anicca.x402-experiment-franklin1",
  ]) assert.match(source, new RegExp(label.replaceAll(".", "\\."), "u"));
  assert.match(source, /AGENT_ECONOMY_RETIRE_LEGACY/u);

  const result = spawnSync("bash", [SCRIPT], {
    cwd: ROOT,
    encoding: "utf8",
    env: { ...process.env, AGENT_ECONOMY_RETIRE_LEGACY: "0", LIFE_MANAGER_REPO: ROOT },
  });
  assert.equal(result.status, 2);
  assert.match(result.stderr, /disabled/u);
});

