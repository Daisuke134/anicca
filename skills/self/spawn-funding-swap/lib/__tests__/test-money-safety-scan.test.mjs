// VCSDD spawn-funding-swap Phase 2a (RED). PROP-021 (Tier 0, structural) — the Test-Money Safety Rule's
// falsifiable counterpart: no file under this feature's test directories imports the CONCRETE
// SkipApiClient/ChainReader/BaseSigner/AkashSigner-subprocess/PriceOracle implementation modules (only
// the fake/mock modules under ./fakes/ are permitted), and no test file contains the literal string
// "api.skip.build" or a real RPC endpoint URL outside a documented fixture-comment. This scan runs over
// THIS SUITE ITSELF right now — it is expected to PASS even in the RED phase (it is a property of the
// test files we just wrote, not of the not-yet-existing implementation), proving from the very first
// commit that no test in this suite ever touches real money/network.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));

// The concrete implementation modules a test file must NEVER import directly (only the fakes under
// ./fakes/ may stand in for these). Matches an import specifier ending in one of these basenames,
// OUTSIDE the ./fakes/ directory itself.
const FORBIDDEN_CONCRETE_IMPORT_BASENAMES = ["skip-api-client.mjs", "chain-reader.mjs", "base-signer.mjs", "akash-signer.mjs", "price-oracle.mjs"];

// A real endpoint literal is only ever permitted inside a documented fixture-comment (a line containing
// "fixture-comment" or appearing as a JS comment `//`); this scan below only flags the string appearing
// in NON-comment source (a crude but effective heuristic: strip // line comments before searching).
const REAL_ENDPOINT_PATTERNS = [/api\.skip\.build/, /https?:\/\/rpc\./, /\.rpc\.akt\.dev/];

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

test("PROP-021: no file under this feature's test directories imports a concrete SkipApiClient/ChainReader/BaseSigner/AkashSigner/PriceOracle implementation module", () => {
  const files = listTestSourceFiles(TEST_DIR);
  const violations = [];
  for (const file of files) {
    if (file.includes(`${path.sep}fakes${path.sep}`)) continue; // fakes are the permitted stand-ins themselves
    const source = fs.readFileSync(file, "utf8");
    for (const basename of FORBIDDEN_CONCRETE_IMPORT_BASENAMES) {
      if (source.includes(basename)) violations.push(`${file}: references forbidden concrete module '${basename}'`);
    }
  }
  assert.deepEqual(violations, [], `test-file concrete-implementation-import violations found:\n${violations.join("\n")}`);
});

test("PROP-021: no test file contains a real Skip API / RPC endpoint literal outside a documented fixture-comment", () => {
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

test("PROP-021 sanity: this scan itself has something to scan (non-empty test directory)", () => {
  const files = listTestSourceFiles(TEST_DIR);
  assert.ok(files.length > 0);
});
