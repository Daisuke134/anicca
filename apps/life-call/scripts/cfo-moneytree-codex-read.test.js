"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const { readMoneytreeViaCodex } = require("./cfo-moneytree-codex-read.js");

const OBSERVED_AT = "2026-08-10T01:02:03.000Z";
const REFERENCE_KEY = "synthetic-lm-uid-secret-32-bytes-long";
const SENTINEL = "unrelated-secret-sentinel-should-not-propagate";
const CFO_CWD = path.resolve(__dirname, "..");
const ACCOUNTS = {
  type: "accounts",
  data: {
    baseCurrency: "JPY",
    accountGroups: {
      banks: [{
        institutionKey: "mufg_bank",
        accounts: [{ id: 42, account_subtype: "savings", current_balance: 123456, currency: "JPY" }],
      }],
    },
  },
};

function transcript(content = ACCOUNTS) {
  return [
    JSON.stringify({ type: "response.output_text.delta", delta: "balance 123456 prose that is not data" }),
    JSON.stringify({ type: "item.completed", item: { type: "mcp_tool_call", result: { structured_content: content } } }),
    JSON.stringify({ type: "response.completed", response: { output_text: "stderr/raw provider should be ignored" } }),
  ].join("\n");
}

function options(stdout, calls, overrides = {}) {
  return {
    now: () => new Date(OBSERVED_AT),
    env: {
      HOME: "/tmp/cfo-home",
      PATH: "/usr/bin:/bin",
      USER: "anicca",
      LOGNAME: "anicca",
      SHELL: "/bin/zsh",
      TMPDIR: "/tmp",
      LANG: "ja_JP.UTF-8",
      CODEX_HOME: "/tmp/codex-home",
      LM_UID_SECRET: REFERENCE_KEY,
      UNRELATED_SECRET_SENTINEL: SENTINEL,
    },
    execFileImpl: (file, args, childOptions, callback) => {
      const child = { endCalls: 0, stdin: { end: () => { child.endCalls += 1; } } };
      calls.push({ file, args, childOptions, child });
      callback(null, stdout, "model prose stderr secret: " + SENTINEL);
      return child;
    },
    ...overrides,
  };
}

function frozenDeep(value, seen = new Set()) {
  if (value === null || typeof value !== "object" || seen.has(value)) return true;
  seen.add(value);
  return Object.isFrozen(value) && Object.values(value).every((child) => frozenDeep(child, seen));
}

test("reads exactly one raw accounts MCP result with a shell-free read-only Luna call", async () => {
  const calls = [];
  const result = await readMoneytreeViaCodex(options(transcript(), calls));
  assert.equal(calls.length, 1);
  assert.equal(calls[0].child.endCalls, 1);
  assert.equal(calls[0].file, "codex");
  assert.equal(calls[0].childOptions.shell, false);
  assert.equal(calls[0].childOptions.timeout, 120000);
  assert.equal(calls[0].childOptions.maxBuffer, 2 * 1024 * 1024);
  assert.ok(calls[0].args.includes("exec"));
  assert.ok(calls[0].args.includes("--ephemeral"));
  assert.ok(calls[0].args.includes("--json"));
  assert.ok(calls[0].args.includes("gpt-5.6-luna"));
  assert.ok(calls[0].args.includes("read-only"));
  assert.ok(calls[0].args.includes(CFO_CWD));
  assert.equal(calls[0].childOptions.cwd, CFO_CWD);
  assert.equal(result.source.sourceId, "moneytree_mufg");
  assert.equal(result.source.accounts.length, 1);
  assert.equal(result.source.accounts[0].balanceMinor, 123456);
  assert.equal(result.source.asOf, OBSERVED_AT);
  assert.equal(result.state.aggregationStatus, "unknown");
  assert.equal(result.state.liabilityCoverage, "unknown");
  assert.equal(result.state.partial, true);
  assert.equal(frozenDeep(result), true);
});

test("scrubs secrets from the child environment and keeps only runtime keys", async () => {
  const calls = [];
  await readMoneytreeViaCodex(options(transcript(), calls));
  const childEnv = calls[0].childOptions.env;
  assert.equal(Object.hasOwn(childEnv, "LM_UID_SECRET"), false);
  assert.equal(Object.hasOwn(childEnv, "UNRELATED_SECRET_SENTINEL"), false);
  assert.deepEqual(Object.keys(childEnv).sort(), ["CODEX_HOME", "CODEX_INTERNAL_ORIGINATOR_OVERRIDE", "HOME", "LANG", "LOGNAME", "PATH", "SHELL", "TMPDIR", "USER"]);
  assert.doesNotMatch(JSON.stringify(childEnv), /secret|sentinel/i);
});

test("adds only the fixed Codex originator override and never inherits parent session fields", async () => {
  const calls = [];
  const configured = options(transcript(), calls, {
    env: {
      ...options(transcript(), []).env,
      CODEX_INTERNAL_ORIGINATOR_OVERRIDE: "parent-originator-must-not-inherit",
      CODEX_THREAD_ID: "thread-secret-must-not-inherit",
      CODEX_CI: "1",
      CODEX_SHELL: "shell-secret-must-not-inherit",
    },
  });
  await readMoneytreeViaCodex(configured);
  const childEnv = calls[0].childOptions.env;
  assert.equal(childEnv.CODEX_INTERNAL_ORIGINATOR_OVERRIDE, "codex_exec");
  for (const key of ["LM_UID_SECRET", "UNRELATED_SECRET_SENTINEL", "CODEX_THREAD_ID", "CODEX_CI", "CODEX_SHELL"]) {
    assert.equal(Object.hasOwn(childEnv, key), false, `unexpected inherited ${key}`);
  }
  assert.doesNotMatch(JSON.stringify(childEnv), /parent-originator|thread-secret|shell-secret|sentinel/i);
});

test("fails closed when the Codex child has no usable stdin", async () => {
  for (const child of [{}, { stdin: {} }, { stdin: { end: null } }]) {
    const configured = options(transcript(), [], {
      execFileImpl: (file, args, childOptions, callback) => {
        callback(null, transcript(), "raw stderr");
        return child;
      },
    });
    await assert.rejects(
      () => readMoneytreeViaCodex(configured),
      (error) => error instanceof Error && error.message === "cfo_moneytree_codex_read_failed:unavailable",
    );
  }
});

test("ignores model prose, stderr, balances, and raw fields on failure", async () => {
  const calls = [];
  const malformed = [
    JSON.stringify({ type: "response.output_text.done", text: "balance 999999 raw provider secret" }),
    JSON.stringify({ type: "item.completed", item: { type: "mcp_tool_call", result: { structured_content: { type: "not_accounts", raw_provider_secret: SENTINEL } } } }),
  ].join("\n");
  await assert.rejects(
    () => readMoneytreeViaCodex(options(malformed, calls)),
    (error) => error instanceof Error
      && error.message === "cfo_moneytree_codex_read_failed:unavailable"
      && !/999999|raw_provider|sentinel|stderr|secret/i.test(error.message),
  );
});

test("rejects missing and duplicate completed accounts MCP results with one fixed error", async () => {
  const cases = [
    ["missing", JSON.stringify({ type: "response.completed" })],
    ["duplicate", [JSON.stringify({ type: "item.completed", item: { type: "mcp_tool_call", result: { structured_content: ACCOUNTS } } }), JSON.stringify({ type: "item.completed", item: { type: "mcp_tool_call", result: { structured_content: ACCOUNTS } } })].join("\n")],
  ];
  for (const [, stdout] of cases) {
    await assert.rejects(
      () => readMoneytreeViaCodex(options(stdout, [])),
      (error) => error instanceof Error && error.message === "cfo_moneytree_codex_read_failed:unavailable",
    );
  }
});

test("registers the reader in the focused CFO suite", () => {
  const packageJson = JSON.parse(fs.readFileSync(path.resolve(__dirname, "../package.json"), "utf8"));
  assert.match(packageJson.scripts["test:cfo"], /scripts\/cfo-moneytree-codex-read\.test\.js/);
});
