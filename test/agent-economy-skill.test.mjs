import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import test from "node:test";

const ROOT = new URL("../", import.meta.url).pathname;

test("agent-economy is a thin, read-first public skill", async () => {
  const skill = await readFile(join(ROOT, "skills", "agent-economy", "SKILL.md"), "utf8");
  const run = await readFile(join(ROOT, "skills", "agent-economy", "run.sh"), "utf8");
  assert.match(skill, /^---\nname: agent-economy\n/m);
  assert.match(skill, /receipt-reconciliations\.jsonl/u);
  assert.match(skill, /TaskMarket/u);
  assert.match(skill, /OpenRouter/u);
  assert.match(run, /reconcile-receipts\.mjs/u);
  assert.match(run, /ANICCA_HOME/u);
  assert.doesNotMatch(run, /PRIVATE_KEY|SECRET_KEY|WALLET_KEY/u);
});

