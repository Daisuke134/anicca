"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const { main } = require("../scripts/daily-preflight.js");

const production = fs.readFileSync(path.join(__dirname, "daily-preflight.js"), "utf8");
const collectors = fs.readFileSync(path.join(__dirname, "daily-preflight-collectors.js"), "utf8");
const cli = fs.readFileSync(path.join(__dirname, "../scripts/daily-preflight.js"), "utf8");

test("purity: exported production main rejects caller env/fetch/transport and never calls forged transport", async () => {
  let calls = 0;
  const forged = async () => { calls += 1; throw new Error("forged transport called"); };
  await assert.rejects(() => main({ argv: ["--mode", "read-only"], env: {}, fetchImpl: forged, transport: forged }), /caller|argument|injection/i);
  assert.equal(calls, 0);
});

test("purity: production collectors retain zero injected transport surface", () => {
  assert.doesNotMatch(collectors, /collectProductionControlledL3\s*\([^)]/);
});

test("purity: runRef is derived from current internal correlation", () => {
  assert.match(production, /runRef:\s*hashedRef\(runCorrelation\)/);
});

test("purity: raw run correlation is excluded from serialization", () => {
  assert.match(production, /delete\s+\w+\.runCorrelation|\{\s*runCorrelation\s*,\s*\.\.\./);
});

test("purity: successful report uses temp-file fsync rename atomic publication", () => {
  assert.match(cli, /mkdtemp|\.tmp/); assert.match(cli, /fsync/); assert.match(cli, /rename/);
});

test("purity: failed publication removes temporary output and leaves no final artifact", () => {
  assert.match(cli, /unlink/); assert.match(cli, /finally|catch/);
});
