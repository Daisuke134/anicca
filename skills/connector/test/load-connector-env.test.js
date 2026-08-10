"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { loadConnectorEnv } = require("../lib/load-connector-env.js");

function fixture(source) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-env-"));
  const file = path.join(dir, "env");
  fs.writeFileSync(file, source, { mode: 0o600 });
  return { dir, file };
}

test("loads the private attendee name with existing Calendar config only", () => {
  const f = fixture("GOG_ACCOUNT=private-account\nDAIS_LEGAL_NAME_ROMAJI=Daisuke Example\nUNKNOWN_SECRET=hidden\u000bvalue\nUNKNOWN_DEL=hidden\u007fvalue\n");
  try {
    assert.deepEqual(loadConnectorEnv(f.file), { GOG_ACCOUNT: "private-account", DAIS_LEGAL_NAME_ROMAJI: "Daisuke Example" });
    assert.equal(fs.statSync(f.file).mode & 0o777, 0o600);
  } finally { fs.rmSync(f.dir, { recursive: true, force: true }); }
});

test("fails closed for blank/control values, oversized files, and directories", () => {
  for (const value of ["", " \t", "\0", "\r", "\u000b", "Alpha\u000bBeta", "Alpha\u007fBeta"]) {
    const f = fixture(`DAIS_LEGAL_NAME_ROMAJI=${value}`);
    try { assert.throws(() => loadConnectorEnv(f.file), /Connector env unavailable/); } finally { fs.rmSync(f.dir, { recursive: true, force: true }); }
  }
  const large = fixture(`DAIS_LEGAL_NAME_ROMAJI=${"x".repeat(128 * 1024)}`);
  assert.throws(() => loadConnectorEnv(large.file), /Connector env unavailable/);
  fs.rmSync(large.dir, { recursive: true, force: true });
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connector-env-dir-"));
  try { assert.throws(() => loadConnectorEnv(directory), /Connector env unavailable/); } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});
