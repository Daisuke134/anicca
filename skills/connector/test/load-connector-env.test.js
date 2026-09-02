"use strict";

const assert = require("node:assert/strict");
const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { loadConnectorEnv } = require("../lib/load-connector-env.js");

const ENTRYPOINT = path.resolve(__dirname, "..", "run.sh");

function fixture(source) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-env-"));
  const file = path.join(dir, "env");
  fs.writeFileSync(file, source, { mode: 0o600 });
  return { dir, file };
}

test("loads the private attendee name and Telegram bot token through the allowlist", () => {
  const f = fixture("GOG_ACCOUNT=private-account\nDAIS_LEGAL_NAME_ROMAJI=Daisuke Example\nTELEGRAM_BOT_TOKEN=fixture-telegram-token\nUNKNOWN_SECRET=hidden\u000bvalue\nUNKNOWN_DEL=hidden\u007fvalue\n");
  try {
    assert.deepEqual(loadConnectorEnv(f.file), { GOG_ACCOUNT: "private-account", DAIS_LEGAL_NAME_ROMAJI: "Daisuke Example", TELEGRAM_BOT_TOKEN: "fixture-telegram-token" });
    assert.equal(fs.statSync(f.file).mode & 0o777, 0o600);
  } finally { fs.rmSync(f.dir, { recursive: true, force: true }); }
});

test("loads the ranking key only through the connector allowlist", () => {
  const f = fixture("GEMINI_API_KEY=fixture-ranking-key\nUNKNOWN_SECRET=hidden\n");
  try {
    assert.deepEqual(loadConnectorEnv(f.file), { GEMINI_API_KEY: "fixture-ranking-key" });
  } finally { fs.rmSync(f.dir, { recursive: true, force: true }); }
});

test("loads the connpass API key without reflecting unknown secrets", () => {
  const f = fixture("CONNPASS_API_KEY=fixture-connpass-api-key-0000\nUNKNOWN_SECRET=hidden\n");
  try {
    assert.deepEqual(loadConnectorEnv(f.file), { CONNPASS_API_KEY: "fixture-connpass-api-key-0000" });
  } finally { fs.rmSync(f.dir, { recursive: true, force: true }); }
});

test("loads the explicit Connpass submit opt-in through the connector allowlist", () => {
  const f = fixture("LM_CONNECTOR_CONNPASS_AUTOMATED_SUBMIT_ALLOWED=true\n");
  try {
    assert.deepEqual(loadConnectorEnv(f.file), { LM_CONNECTOR_CONNPASS_AUTOMATED_SUBMIT_ALLOWED: "true" });
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

test("official entrypoint uses the portable state-home default while retaining an explicit env override", () => {
  const source = fs.readFileSync(ENTRYPOINT, "utf8");
  assert.match(source, /LIFE_MANAGER_STATE_HOME=.*XDG_STATE_HOME/);
  assert.match(source, /LM_CONNECTOR_SHARED_ENV_FILE=.*LIFE_MANAGER_STATE_HOME\/\.env/);
  assert.match(source, /LM_CONNECTOR_STATE_DIR:-\$LIFE_MANAGER_STATE_HOME\/connector-native/);
  assert.match(source, /LM_CONNECTOR_SHARED_ENV_FILE=\"\$\{LM_CONNECTOR_SHARED_ENV_FILE:-/);
  assert.doesNotMatch(source, /\.openclaw\/\.env/);
});

test("official entrypoint fails before native wake when the rendered env file is absent", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connector-prestart-"));
  try {
    const stateHome = path.join(directory, "state-home");
    const result = spawnSync("bash", [ENTRYPOINT], {
      encoding: "utf8",
      env: {
        ...process.env,
        HOME: directory,
        LIFE_MANAGER_STATE_HOME: stateHome,
        LM_CONNECTOR_SHARED_ENV_FILE: path.join(directory, "missing.env"),
        LM_CONNECTOR_STATE_DIR: path.join(directory, "connector-state"),
        NODE_BIN: process.execPath,
      },
    });
    assert.equal(result.status, 2);
    assert.match(result.stderr, /Connector env unavailable/);
    assert.equal(fs.existsSync(path.join(directory, "connector-state", "lock")), false);
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});
