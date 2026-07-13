// reality-verdict-schema.single-source.test.mjs — PROP-047 static-check test: the "ONE module,
// TWO callers" architecture (spec: .vcsdd/features/reality-gate/specs/behavioral-spec.md
// REQ-014's "no duplicated provenance logic" acceptance criterion) can be silently defeated by a
// shadow implementation living in a CALLER instead of the shared module. This test mechanically
// asserts that the definitions (never mere CALLS/imports) of enforceVerdict,
// validateArtifactProvenance, canonicalizeUrl, computeRowHmac/verifyRowHmac, and the
// httpStatus-2xx-range comparison logic exist in EXACTLY ONE place: reality-verdict-schema.mjs.
//
// Both current callers are covered: (i) the VCSDD gate script named by REQ-008 (`/vcsdd-reality`)
// does not exist yet anywhere in this repo (verified by grep below — this test also asserts that
// absence stays visible rather than silently assumed) — when it IS added, this test's repo-wide
// scan already covers it with no further changes needed; (ii) the runtime path,
// skills/self/reality-verify-spawn.sh, which never touches JS logic directly and instead calls
// skills/self/scripts/reality-enforce-cli.mjs, a thin adapter that must ONLY import these symbols.
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, "../../../../"); // .../skills/self/lib/__tests__ -> repo root
const SCHEMA_REL = "skills/self/lib/reality-verdict-schema.mjs";
const SCHEMA_ABS = path.join(REPO_ROOT, SCHEMA_REL);

const GUARDED_SYMBOLS = [
  "enforceVerdict",
  "validateArtifactProvenance",
  "canonicalizeUrl",
  "computeRowHmac",
  "verifyRowHmac",
];

function findAllMjsFiles() {
  const out = execFileSync(
    "find",
    [".", "-name", "*.mjs", "-not", "-path", "*/node_modules/*"],
    { cwd: REPO_ROOT, encoding: "utf8" }
  );
  return out
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((rel) => rel.replace(/^\.\//, ""));
}

function definesSymbolLocally(source, symbol) {
  // A DEFINITION: `function <symbol>(`, `const <symbol> =`, `let <symbol> =`, `var <symbol> =`
  // (optionally `export`-prefixed). A CALL (`enforceVerdict(...)`) or an IMPORT
  // (`import { enforceVerdict } from ...`) never matches these patterns.
  const defRe = new RegExp(
    `(^|[^.\\w])(export\\s+)?(async\\s+)?function\\s+${symbol}\\s*\\(|(^|[^.\\w])(export\\s+)?(const|let|var)\\s+${symbol}\\s*=`,
    "m"
  );
  return defRe.test(source);
}

test("reality-verdict-schema.mjs IS the canonical source: it defines every guarded symbol", () => {
  const source = readFileSync(SCHEMA_ABS, "utf8");
  for (const symbol of GUARDED_SYMBOLS) {
    assert.equal(
      definesSymbolLocally(source, symbol),
      true,
      `expected reality-verdict-schema.mjs to define ${symbol}`
    );
  }
});

test("PROP-047: no .mjs file outside reality-verdict-schema.mjs redefines any guarded symbol", () => {
  const files = findAllMjsFiles();
  assert.ok(files.includes(SCHEMA_REL), "sanity: file scan must include the schema file itself");

  const violations = [];
  for (const rel of files) {
    if (rel === SCHEMA_REL) continue; // the canonical source itself, excluded by construction
    const abs = path.join(REPO_ROOT, rel);
    const source = readFileSync(abs, "utf8");
    for (const symbol of GUARDED_SYMBOLS) {
      if (definesSymbolLocally(source, symbol)) {
        violations.push(`${rel}: redefines ${symbol}`);
      }
    }
  }
  assert.deepEqual(violations, [], `found shadow definitions outside ${SCHEMA_REL}:\n${violations.join("\n")}`);
});

test("PROP-047: no .mjs file outside reality-verdict-schema.mjs re-implements the httpStatus 2xx-range comparison", () => {
  const files = findAllMjsFiles();
  const httpRangeRe = /httpStatus\s*<\s*200[\s\S]{0,40}httpStatus\s*>=\s*300|httpStatus\s*>=\s*300[\s\S]{0,40}httpStatus\s*<\s*200/;
  const violations = [];
  for (const rel of files) {
    if (rel === SCHEMA_REL) continue;
    const abs = path.join(REPO_ROOT, rel);
    const source = readFileSync(abs, "utf8");
    if (httpRangeRe.test(source)) {
      violations.push(rel);
    }
  }
  assert.deepEqual(violations, [], `found a re-implemented httpStatus 2xx-range check outside ${SCHEMA_REL}: ${violations.join(", ")}`);
});

test("caller (ii), reality-enforce-cli.mjs, IMPORTS every guarded symbol it uses — it never redefines them", () => {
  const callerPath = path.join(REPO_ROOT, "skills/self/scripts/reality-enforce-cli.mjs");
  const source = readFileSync(callerPath, "utf8");
  assert.match(source, /from\s+["'].*reality-verdict-schema\.mjs["']/, "must import from reality-verdict-schema.mjs");
  for (const symbol of ["enforceVerdict"]) {
    assert.equal(definesSymbolLocally(source, symbol), false, `caller must not redefine ${symbol}`);
    assert.match(source, new RegExp(`\\b${symbol}\\b`), `caller must reference ${symbol}`);
  }
});

test("caller (i), the VCSDD gate script named by REQ-008, does not exist yet in this repo (documents the current scan boundary honestly)", () => {
  let found = "";
  try {
    found = execFileSync("grep", ["-rl", "vcsdd-reality", "--include=*.md", "--include=*.mjs", "--include=*.sh", "."], {
      cwd: REPO_ROOT,
      encoding: "utf8",
    });
  } catch {
    found = ""; // grep exits non-zero when nothing matches — that IS the expected, asserted state
  }
  const hits = found
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .filter((f) => !f.includes(".vcsdd/features/reality"))
    .filter((f) => !f.includes("reality-verdict-schema.single-source.test.mjs"));
  assert.deepEqual(hits, [], "if this fails, the gate script now exists — extend GUARDED_SYMBOLS coverage to name it explicitly as caller (i)");
});
