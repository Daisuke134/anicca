// VCSDD spawn-funding-swap Phase 2a (sprint-2, RED). PROP-049 (Tier 0, structural) — this sprint's own
// extension of the Test-Money Safety Rule (lib/__tests__/test-money-safety-scan.test.mjs's own PROP-021,
// scoped to lib/__tests__/, does NOT traverse this NEW directory): no file under
// lib/real-clients/__tests__/ contains a real Skip API / CoinGecko / Base RPC / Akash RPC endpoint
// literal outside a documented comment. This scan runs over THIS SUITE ITSELF right now and is expected
// to PASS even in the RED phase (a property of the test files, not of the not-yet-existing
// implementation).
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
const REAL_ENDPOINT_PATTERNS = [/api\.skip\.build/, /api\.coingecko\.com/, /mainnet\.base\.org/, /\.rpc\.akt\.dev/, /raw\.githubusercontent\.com\/akash-network/];

function listTestSourceFiles(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  return entries.flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return listTestSourceFiles(full);
    if (entry.isFile() && entry.name.endsWith(".mjs") && entry.name !== path.basename(fileURLToPath(import.meta.url))) return [full];
    return [];
  });
}

function stripLineComments(source) {
  return source
    .split("\n")
    .map((line) => {
      const idx = line.indexOf("//");
      return idx === -1 ? line : line.slice(0, idx);
    })
    .join("\n");
}

test("PROP-049: no file under lib/real-clients/__tests__/ contains a real Skip/CoinGecko/Base-RPC/Akash-RPC endpoint literal outside a comment", () => {
  const files = listTestSourceFiles(TEST_DIR);
  const violations = [];
  for (const file of files) {
    const codeOnly = stripLineComments(fs.readFileSync(file, "utf8"));
    for (const pattern of REAL_ENDPOINT_PATTERNS) {
      if (pattern.test(codeOnly)) violations.push(`${file}: matched real-endpoint pattern ${pattern} outside a comment`);
    }
  }
  assert.deepEqual(violations, [], `real-endpoint-literal violations found:\n${violations.join("\n")}`);
});

test("PROP-049 sanity: this scan itself has something to scan (non-empty test directory)", () => {
  const files = listTestSourceFiles(TEST_DIR);
  assert.ok(files.length > 0);
});
