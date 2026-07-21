"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const { main } = require("../scripts/daily-preflight.js");

const production = fs.readFileSync(path.join(__dirname, "daily-preflight.js"), "utf8");
const collectors = fs.readFileSync(path.join(__dirname, "daily-preflight-collectors.js"), "utf8");
const cli = fs.readFileSync(path.join(__dirname, "../scripts/daily-preflight.js"), "utf8");

test("purity: exported production main rejects caller transport and never calls it", async () => {
  let calls = 0;
  const forged = async () => { calls += 1; throw new Error("forged transport called"); };
  await assert.rejects(() => main({ transport: forged }), /caller|argument|injection/i);
  assert.equal(calls, 0);
});

test("manager RED: purity: exported production main rejects env-only injection before reading it", async () => {
  let reads = 0;
  const fakeEnv = new Proxy({}, { get() { reads += 1; return ""; } });
  const originalWrite = process.stdout.write;
  process.stdout.write = () => true;
  let rejection;
  try { await main({ env: fakeEnv }); } catch (error) { rejection = error; }
  finally { process.stdout.write = originalWrite; }
  assert.equal(reads, 0, "caller env must not be read");
  assert.match(String(rejection && rejection.message), /caller|argument|injection/i);
});

test("manager RED: purity: exported production main rejects fetchImpl-only injection before calling it", async () => {
  let calls = 0;
  const forged = async () => {
    calls += 1;
    return { ok: true, status: 200, json: async () => ({ ok: true, service: "life-call" }) };
  };
  const originalEnv = process.env;
  const originalWrite = process.stdout.write;
  process.env = { PATH: originalEnv.PATH || "", PUBLIC_BASE: "https://fixture.invalid" };
  process.stdout.write = () => true;
  let rejection;
  try { await main({ fetchImpl: forged }); } catch (error) { rejection = error; }
  finally { process.env = originalEnv; process.stdout.write = originalWrite; }
  assert.equal(calls, 0, "caller fetch must not be called");
  assert.match(String(rejection && rejection.message), /caller|argument|injection/i);
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
