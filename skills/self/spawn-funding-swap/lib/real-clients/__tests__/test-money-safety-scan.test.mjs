// VCSDD spawn-funding-swap Phase 2a/2b (sprint-2). PROP-049 (Tier 0, structural) — this sprint's own
// extension of the Test-Money Safety Rule (lib/__tests__/test-money-safety-scan.test.mjs's own PROP-021,
// scoped to lib/__tests__/, does NOT traverse this NEW directory): (1) no file under
// lib/real-clients/__tests__/ contains a real Skip API / CoinGecko / Base RPC / Akash RPC endpoint
// literal outside a documented comment, AND (2) no file under lib/real-clients/__tests__/ constructs a
// `createRealXxx(...)` client WITHOUT injecting at least one transport seam (`fetchImpl`/`execFileImpl`)
// in the same call's argument object.
//
// FIND-007 fix (impl review iter1): check (2) did NOT previously exist -- verification-architecture.md's
// PROP-049 description already claimed it ("never a bare createRealXxx() with no transport override"),
// but the scan only ever implemented check (1), so the claim overclaimed what was actually enforced (two
// base-signer.test.mjs call sites and two relay-poller.test.mjs call sites were, in fact, bare -- safe by
// construction in THIS implementation, since neither exercised code path reaches the network, but nothing
// would have caught a FUTURE test that added a bare call on a path that DOES). Check (2) is now real: it
// requires `fetchImpl:`/`execFileImpl:` to appear as a key inside the balanced-paren argument text of
// every `createReal[A-Za-z]+(...)` call in this directory (every one of this feature's five real-client
// factories accepts `fetchImpl`, and chain-reader additionally accepts `execFileImpl`, so this is always
// satisfiable without any marker/exception mechanism -- see base-signer.test.mjs's/relay-poller.test.mjs's
// own NEVER_CALLED_FETCH fix for the two previously-bare call sites each).
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
const REAL_ENDPOINT_PATTERNS = [/api\.skip\.build/, /api\.coingecko\.com/, /mainnet\.base\.org/, /\.rpc\.akt\.dev/, /raw\.githubusercontent\.com\/akash-network/];
const TRANSPORT_SEAM_KEYS = ["fetchImpl", "execFileImpl"];
const CREATE_REAL_CALL_PATTERN = /createReal[A-Za-z]+\s*\(/g;

function listTestSourceFiles(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  return entries.flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return listTestSourceFiles(full);
    if (entry.isFile() && entry.name.endsWith(".mjs") && entry.name !== path.basename(fileURLToPath(import.meta.url))) return [full];
    return [];
  });
}

/**
 * stripLineComments — string-literal-aware `//` comment stripper. FIND-007 fix (impl review iter1,
 * discovered while implementing the bare-call scan below): the ORIGINAL naive `line.indexOf("//")`
 * implementation truncated ANY line containing a `//` substring inside a STRING LITERAL (e.g.
 * `AKASH_NODE: "https://fake-node.example:443"` in chain-reader.test.mjs), silently chopping off the
 * rest of that line/statement -- harmless for the endpoint-literal scan (over-stripping can only miss a
 * potential match, never fabricate one), but a genuine FALSE POSITIVE for the new bare-createRealXxx()
 * scan below (it truncated a call's argument text mid-object-literal, before its own `execFileImpl:` key,
 * making a fully-transport-injected call look bare). Now tracks string-literal boundaries (', ", `) and
 * only treats `//` as a comment start when NOT inside one.
 */
function stripLineComments(source) {
  let result = "";
  let quote = null;
  for (let i = 0; i < source.length; i += 1) {
    const ch = source[i];
    if (quote) {
      result += ch;
      if (ch === "\\" && i + 1 < source.length) {
        result += source[i + 1];
        i += 1;
        continue;
      }
      if (ch === quote) quote = null;
      continue;
    }
    if (ch === '"' || ch === "'" || ch === "`") {
      quote = ch;
      result += ch;
      continue;
    }
    if (ch === "/" && source[i + 1] === "/") {
      while (i < source.length && source[i] !== "\n") i += 1;
      result += "\n";
      continue;
    }
    result += ch;
  }
  return result;
}

/**
 * extractBalancedArgs — given source text and the index of the opening `(` of a call, returns the text
 * between that `(` and its matching `)` (balanced paren-depth walk, so nested object literals/arrow
 * functions inside the call's arguments don't terminate the scan early).
 */
function extractBalancedArgs(source, openParenIdx) {
  let depth = 0;
  for (let i = openParenIdx; i < source.length; i += 1) {
    if (source[i] === "(") depth += 1;
    else if (source[i] === ")") {
      depth -= 1;
      if (depth === 0) return source.slice(openParenIdx + 1, i);
    }
  }
  return source.slice(openParenIdx + 1); // unterminated (shouldn't happen in valid source) -- best effort
}

/**
 * findBareCreateRealCalls — returns a list of violation strings, one per `createReal[A-Za-z]+(...)` call
 * in `codeOnly` (comment-stripped source) whose argument text contains NEITHER `fetchImpl` NOR
 * `execFileImpl` as a key.
 */
function findBareCreateRealCalls(codeOnly, filePath) {
  const violations = [];
  for (const match of codeOnly.matchAll(CREATE_REAL_CALL_PATTERN)) {
    const openParenIdx = match.index + match[0].length - 1;
    const argsText = extractBalancedArgs(codeOnly, openParenIdx);
    // Matches BOTH explicit `fetchImpl: someValue` AND ES6 object-shorthand `{ fetchImpl }` (the
    // dominant style in this suite: `const fetchImpl = makeFetchMock(...); createRealXxx({ ..., fetchImpl })`).
    const hasSeam = TRANSPORT_SEAM_KEYS.some((key) => new RegExp(`\\b${key}\\b`).test(argsText));
    if (!hasSeam) {
      const lineNumber = codeOnly.slice(0, match.index).split("\n").length;
      violations.push(`${filePath}:${lineNumber}: ${match[0]}...) has no fetchImpl/execFileImpl transport seam in its argument object`);
    }
  }
  return violations;
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

test("PROP-049: no file under lib/real-clients/__tests__/ constructs a bare createRealXxx() with no injected fetchImpl/execFileImpl transport seam (FIND-007 fix)", () => {
  const files = listTestSourceFiles(TEST_DIR);
  const violations = files.flatMap((file) => findBareCreateRealCalls(stripLineComments(fs.readFileSync(file, "utf8")), file));
  assert.deepEqual(violations, [], `bare createRealXxx() violations found:\n${violations.join("\n")}`);
});

test("PROP-049 (self-check): the bare-call detector itself actually flags a deliberately bare fixture snippet", () => {
  const violations = findBareCreateRealCalls('const x = createRealBaseSigner({ env: { ANICCA_HOME: home } });', "fixture.mjs");
  assert.equal(violations.length, 1, "the detector must flag a createRealXxx() call with no fetchImpl/execFileImpl key");
});

test("PROP-049 sanity: this scan itself has something to scan (non-empty test directory)", () => {
  const files = listTestSourceFiles(TEST_DIR);
  assert.ok(files.length > 0);
});
