// node:test — build-bundle.mjs: the esbuild-based single-file bundler that eliminates the
// npm-install-at-runtime risk (this repo has never observed npm-registry egress working from a
// Nosana job container). Runs the REAL esbuild build to a temp file (esbuild itself is not
// mocked — a fake bundler proves nothing about whether the real one produces a working artifact)
// and sanity-checks the real output.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { buildEntrypointBundle } from "../build-bundle.mjs";

test("buildEntrypointBundle: produces a real, non-trivial, self-contained .mjs file", async () => {
  const outfile = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "bundle-test-")), "out.mjs");
  try {
    const result = await buildEntrypointBundle({ outfile });
    assert.equal(result.outfile, outfile);
    assert.ok(fs.existsSync(outfile));
    // A real bundle inlining @solana/web3.js + bs58 + tweetnacl + this repo's own modules is
    // firmly in the hundreds-of-KB range — a suspiciously small file would mean bundling silently
    // failed to inline something (e.g. left an external `import "@solana/web3.js"` in place,
    // which would then need npm install after all, defeating the whole point).
    assert.ok(result.bytes > 100_000, `expected a substantial bundle, got ${result.bytes} bytes`);
  } finally {
    fs.rmSync(path.dirname(outfile), { recursive: true, force: true });
  }
});

test("buildEntrypointBundle: the output has NO remaining top-level import statements for our real npm deps (fully inlined, not just re-listed) — only Node built-ins remain", async () => {
  const outfile = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "bundle-test2-")), "out.mjs");
  try {
    await buildEntrypointBundle({ outfile });
    const text = fs.readFileSync(outfile, "utf8");
    // Real `import` STATEMENTS only ever appear at the start of a line in esbuild's ESM output —
    // checking full lines (not a substring/regex over the whole file) avoids false-positiving on
    // @solana/web3.js's own vendored JSDoc comments that mention the package name as prose.
    const importLines = text.split("\n").filter((line) => line.startsWith("import "));
    assert.ok(importLines.length > 0, "sanity: the bundle must still import SOMETHING (the node: builtins shim)");
    for (const line of importLines) {
      assert.ok(!line.includes('"@solana/web3.js"') && !line.includes("'@solana/web3.js'"), `unexpected external import: ${line}`);
      assert.ok(!line.includes('"bs58"') && !line.includes("'bs58'"), `unexpected external import: ${line}`);
      assert.ok(!line.includes('"tweetnacl"') && !line.includes("'tweetnacl'"), `unexpected external import: ${line}`);
      // Every remaining import must be a Node built-in (bare "crypto"/"module" or "node:"-prefixed).
      const spec = line.match(/from\s+["']([^"']+)["']/);
      if (spec) {
        assert.ok(
          spec[1].startsWith("node:") || ["crypto", "module", "fs", "path", "os", "buffer", "url"].includes(spec[1]),
          `remaining import "${spec[1]}" is not a recognized Node built-in — bundling may have left an external dependency`,
        );
      }
    }
  } finally {
    fs.rmSync(path.dirname(outfile), { recursive: true, force: true });
  }
});

test("buildEntrypointBundle: the output actually RUNS standalone with plain `node`, with no node_modules in scope — proving it is truly dependency-free, not merely comment-clean", async () => {
  const { execFileSync } = await import("node:child_process");
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "bundle-run-test-"));
  const outfile = path.join(tmpDir, "entrypoint.bundle.mjs");
  try {
    await buildEntrypointBundle({ outfile });
    // Run it from an isolated tmp directory (no ancestor node_modules) with NOSANA_TREASURY_ADDRESS
    // deliberately unset — if @solana/web3.js/bs58/tweetnacl were NOT truly inlined, this would
    // fail with a module-resolution error (e.g. ERR_MODULE_NOT_FOUND) BEFORE ever reaching our own
    // business-logic check. Getting our own, expected error instead is proof the bundle resolved
    // every external dependency by itself.
    let stderr = "";
    let threw = false;
    try {
      execFileSync("node", [outfile], { cwd: tmpDir, env: { PATH: process.env.PATH }, encoding: "utf8" });
    } catch (err) {
      threw = true;
      stderr = String(err.stderr || "");
    }
    assert.equal(threw, true, "expected a non-zero exit (missing NOSANA_TREASURY_ADDRESS)");
    assert.match(stderr, /NOSANA_TREASURY_ADDRESS is not set/, `expected our own business-logic error, got: ${stderr}`);
    assert.ok(!/Cannot find module|MODULE_NOT_FOUND|ERR_MODULE_NOT_FOUND/.test(stderr), `bundle is missing a real dependency: ${stderr}`);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test("buildEntrypointBundle: never embeds this Mac's real treasury secret file path as a string literal (defense in depth)", async () => {
  const outfile = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "bundle-test3-")), "out.mjs");
  try {
    await buildEntrypointBundle({ outfile });
    const text = fs.readFileSync(outfile, "utf8");
    assert.ok(!text.includes(".solana-session"), "the bundle must never reference the treasury secret's filename");
    assert.ok(!text.includes("resolve-identity"), "the bundle must never pull in the identity-resolution module");
  } finally {
    fs.rmSync(path.dirname(outfile), { recursive: true, force: true });
  }
});
