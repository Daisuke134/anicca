"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  dispatchParsedControl,
  executeUserCommand,
  parseUserCommand,
  validateCommand,
} = require("./user-command.js");

const DELEGATION_COMMAND = {
  type: "setting.set",
  setting: "delegation_enabled",
  value: true,
};

test("delegation ON/OFF chat phrases report the unavailable runtime directly", () => {
  const outcomes = [
    parseUserCommand("turn delegation on"),
    parseUserCommand("turn delegation off"),
    parseUserCommand("委任をオン"),
    parseUserCommand("委任をオフ"),
  ];

  assert.deepEqual(outcomes.map((outcome) => outcome.kind), [
    "unavailable",
    "unavailable",
    "unavailable",
    "unavailable",
  ]);
  for (const outcome of outcomes) {
    assert.match(outcome.message, /safe delegated-action runtime|安全な委任アクション実行基盤/);
    assert.doesNotMatch(outcome.message, /[?？]|approv|permission|許可|承認/i);
    assert.equal("command" in outcome, false);
  }
});

test("available actions do not advertise delegation as executable", () => {
  const help = parseUserCommand("settings");
  assert.equal(help.kind, "help");
  assert.doesNotMatch(help.availableActions.join("\n"), /delegation|委任/i);
});

test("direct delegation setting commands are rejected by the API allowlist", () => {
  assert.throws(() => validateCommand(DELEGATION_COMMAND), /invalid_action/);
  assert.throws(() => validateCommand({ ...DELEGATION_COMMAND, value: false }), /invalid_action/);
});

test("direct delegation execution cannot mutate preferences or create a succeeded receipt", async () => {
  const calls = { claims: 0, finishes: 0, mutations: 0 };
  const store = {
    async readUser() { return { uid: "u-a", telegram_chat_id: "101" }; },
    async readReceipt() { return null; },
    async claimReceipt() { calls.claims += 1; return true; },
    async assertCurrentScope() { return true; },
    async mutatePreferences() {
      calls.mutations += 1;
      return { call_enabled: true, notifications_enabled: true, daily_automation_enabled: true };
    },
    async finishReceipt(_scope, _key, receipt) {
      calls.finishes += 1;
      if (receipt.status === "succeeded") calls.succeeded = true;
    },
  };

  await assert.rejects(
    executeUserCommand(
      { uid: "u-a", chatId: "101" },
      DELEGATION_COMMAND,
      { store, idempotencyKey: "delegation-direct-placeholder-1" },
    ),
    /invalid_action/,
  );
  assert.deepEqual(calls, { claims: 0, finishes: 0, mutations: 0 });
});

test("Telegram dispatch returns the honest status without executing a command", async () => {
  assert.equal(typeof dispatchParsedControl, "function");
  let executeCalls = 0;
  const outcome = await dispatchParsedControl(parseUserCommand("turn delegation on"), {
    executeCommand: async () => {
      executeCalls += 1;
      return { ok: true, message: "Setting updated" };
    },
    scope: { uid: "u-a", chatId: "101" },
    commandDeps: {},
  });

  assert.equal(outcome.handled, true);
  assert.match(outcome.message, /safe delegated-action runtime/i);
  assert.equal(outcome.result, undefined);
  assert.equal(executeCalls, 0);
});
