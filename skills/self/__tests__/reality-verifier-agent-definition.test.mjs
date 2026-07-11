// VCSDD Phase 2a (RED) / Phase 5 PROP-006, PROP-007: static content assertions on the
// reality-verifier subagent definition. This is a Tier 0 check (documentation/definition
// artifact, not an algorithm) per verification-architecture.md — we assert required
// frontmatter shape and required prompt substrings, not runtime LLM behavior.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
// skills/self/__tests__/ -> repo root is 3 levels up
const repoRoot = join(here, "..", "..", "..");
const agentPath = join(repoRoot, ".claude", "agents", "reality-verifier.md");

function readAgentDefinition() {
  return readFileSync(agentPath, "utf8");
}

function parseFrontmatter(content) {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  assert.ok(match, "reality-verifier.md must start with a YAML frontmatter block");
  return match[1];
}

test("reality-verifier.md exists and is non-empty", () => {
  const content = readAgentDefinition();
  assert.ok(content.trim().length > 0);
});

test("PROP-006: frontmatter declares name: reality-verifier", () => {
  const fm = parseFrontmatter(readAgentDefinition());
  assert.match(fm, /name:\s*reality-verifier/);
});

test("PROP-006: frontmatter tools array is exactly Read, Grep, Glob, Bash (no Write/Edit)", () => {
  const fm = parseFrontmatter(readAgentDefinition());
  const toolsLine = fm.match(/tools:\s*(\[[^\]]*\])/);
  assert.ok(toolsLine, "frontmatter must declare a tools: [...] array");
  const tools = JSON.parse(toolsLine[1].replace(/'/g, '"'));
  assert.deepEqual([...tools].sort(), ["Bash", "Glob", "Grep", "Read"]);
  assert.ok(!tools.includes("Write"), "reality-verifier MUST NOT be granted Write (REQ-002)");
  assert.ok(!tools.includes("Edit"), "reality-verifier MUST NOT be granted Edit (REQ-002)");
});

test("PROP-006: frontmatter declares a model", () => {
  const fm = parseFrontmatter(readAgentDefinition());
  assert.match(fm, /model:\s*\S+/);
});

test("PROP-007: prompt states the DETERMINISTIC-vs-AGENTIC role boundary (REQ-003)", () => {
  const content = readAgentDefinition();
  assert.match(content, /DETERMINISTIC/);
  assert.match(content, /AGENTIC/);
  // must explicitly disclaim declaring "money moved" as its own determination
  assert.match(content, /money moved|did money move/i);
});

test("PROP-007: prompt states the fresh-context / no-self-eval instruction (REQ-004)", () => {
  const content = readAgentDefinition();
  assert.match(content, /do not trust|never trust/i);
  assert.match(content, /independent(ly)?/i);
});

test("PROP-007: prompt enumerates all 6 REQ-005 finding categories verbatim", () => {
  const content = readAgentDefinition();
  const categories = [
    "report_ledger_mismatch",
    "report_onchain_mismatch",
    "internal_transfer_mislabeled",
    "mock_marker_in_success_path",
    "narrate_only_claim",
    "unhealthy_strategy",
  ];
  for (const category of categories) {
    assert.ok(content.includes(category), `missing category marker: ${category}`);
  }
});

test("PROP-007: prompt states the read-only RPC allow-list and forbids signing/sending (REQ-007)", () => {
  const content = readAgentDefinition();
  assert.match(content, /eth_getBalance/);
  assert.match(content, /sendTransaction|signTransaction/i);
  assert.match(content, /never|forbid|MUST NOT/i);
});

test("PROP-007: prompt states the money-safety no-mutation constraint (REQ-007)", () => {
  const content = readAgentDefinition();
  assert.match(content, /read-only/i);
});
