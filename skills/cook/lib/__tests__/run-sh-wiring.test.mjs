// VCSDD: the regression is a BASH parameter-expansion bug, so it must be asserted at the SHELL layer —
// a pure-JS test of resolveQuery cannot catch a reintroduction of `${ANICCA_ARGS:-{}}` in run.sh.
// These tests drive real bash + the actual run.sh wiring.
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const DIR = path.dirname(fileURLToPath(import.meta.url));
const COOK = path.resolve(DIR, "../..");           // skills/cook
const RUNSH = path.join(COOK, "run.sh");

const bash = (script) => execFileSync("bash", ["-c", script], { encoding: "utf8" }).trim();

test("ROOT CAUSE proof: the OLD idiom ${ANICCA_ARGS:-{}} corrupts a set arg with a stray }", () => {
  const out = bash(`ANICCA_ARGS='{"query":"X"}'; printf '%s' "\${ANICCA_ARGS:-{}}"`);
  assert.equal(out, '{"query":"X"}}', "empirical: bash closes ${...} at the first } → stray } appended");
});

test("the CORRECT idiom ${ANICCA_ARGS:-} returns the arg verbatim", () => {
  const out = bash(`ANICCA_ARGS='{"query":"X"}'; printf '%s' "\${ANICCA_ARGS:-}"`);
  assert.equal(out, '{"query":"X"}');
});

test("end-to-end through the CLI exactly as run.sh calls it: model query SURVIVES the shell", () => {
  const out = bash(`ANICCA_ARGS='{"query":"SHELLTEST unique"}'; node '${path.join(COOK, "lib/resolve-query.mjs")}' "\${ANICCA_ARGS:-}"`);
  assert.equal(out, "SHELLTEST unique");
});

test("GUARD: run.sh must NOT contain the buggy ${ANICCA_ARGS:-{}} in a live (non-comment) line", () => {
  const live = fs.readFileSync(RUNSH, "utf8").split("\n").filter((l) => !l.trimStart().startsWith("#"));
  const offenders = live.filter((l) => l.includes("${ANICCA_ARGS:-{}}"));
  assert.equal(offenders.length, 0, `run.sh re-introduced the brace bug: ${offenders.join(" | ")}`);
});

test("GUARD: run.sh records via an EXISTING record.mjs path (no dead _shared path)", () => {
  const src = fs.readFileSync(RUNSH, "utf8");
  assert.doesNotMatch(src, /_shared\/lib\/record\.mjs/, "dead _shared/lib/record.mjs path must be gone");
  assert.ok(fs.existsSync(path.join(COOK, "../earn/lib/record.mjs")), "earn/lib/record.mjs must exist");
});
