// VCSDD spawn-funding-swap Phase 2a (RED). PROP-017 (Tier 0, structural) — the pure-module import
// boundary: no file under lib/pure/** may import node:fs, node:child_process, node:http(s), or reference
// fetch. This is a static source scan, deliberately requiring NO implementation to exist yet to run
// (it scans whatever files ARE present); it is listed here so the boundary is enforced from the very
// first Phase 2b commit onward, and so this suite's own module-not-found RED failures (every other test
// file in this directory) are the dominant signal for "no implementation yet" rather than this file
// silently reporting a false pass on an empty lib/pure/ directory.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PURE_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "pure");
const FORBIDDEN_PATTERNS = [/require\(\s*["']node:fs["']\s*\)/, /from\s+["']node:fs["']/, /from\s+["']fs["']/, /require\(\s*["']fs["']\s*\)/, /node:child_process/, /require\(\s*["']child_process["']\s*\)/, /node:https?\b/, /\bfetch\s*\(/];

function listMjsFilesRecursive(dir) {
  if (!fs.existsSync(dir)) return [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  return entries.flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return listMjsFilesRecursive(full);
    if (entry.isFile() && (entry.name.endsWith(".mjs") || entry.name.endsWith(".js"))) return [full];
    return [];
  });
}

test("PROP-017: every file under lib/pure/** exists at all (this feature MUST define its pure core here) — fails until Phase 2b populates lib/pure/", () => {
  const files = listMjsFilesRecursive(PURE_DIR);
  assert.ok(files.length > 0, "lib/pure/ must contain the pure-core modules named in the Purity Boundary Map (Phase 2b)");
});

test("PROP-017: no file under lib/pure/** imports node:fs, node:child_process, node:http(s), or references fetch", () => {
  const files = listMjsFilesRecursive(PURE_DIR);
  const violations = [];
  for (const file of files) {
    const source = fs.readFileSync(file, "utf8");
    for (const pattern of FORBIDDEN_PATTERNS) {
      if (pattern.test(source)) violations.push(`${file}: matched ${pattern}`);
    }
  }
  assert.deepEqual(violations, [], `pure-module import-boundary violations found:\n${violations.join("\n")}`);
});
