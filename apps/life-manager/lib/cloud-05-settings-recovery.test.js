"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const {
  validateCommand,
  executeUserCommand,
  parseUserCommand,
} = require("./user-command.js");

function commandStore(user = {}) {
  const current = {
    uid: "tenant-a",
    telegram_chat_id: "101",
    home_address: "Old home",
    phone: "+819012345678",
    ...user,
  };
  const preferences = { call_enabled: true };
  const receipts = new Map();
  const mutations = [];
  return {
    current,
    preferences,
    receipts,
    mutations,
    async readUser(scope) {
      return scope.uid === current.uid && scope.chatId === current.telegram_chat_id ? { ...current } : null;
    },
    async assertCurrentScope(scope) {
      return scope.uid === current.uid && scope.chatId === current.telegram_chat_id;
    },
    async readReceipt(scope, key) { return receipts.get(`${scope.uid}:${scope.chatId}:${key}`) || null; },
    async claimReceipt(scope, key, receipt) {
      const id = `${scope.uid}:${scope.chatId}:${key}`;
      if (receipts.has(id)) return false;
      receipts.set(id, receipt);
      return true;
    },
    async finishReceipt(scope, key, receipt) {
      receipts.set(`${scope.uid}:${scope.chatId}:${key}`, receipt);
    },
    async mutateUser(scope, patch) {
      if (!(await this.assertCurrentScope(scope))) throw new Error("scope_mismatch");
      mutations.push({ scope: { ...scope }, patch: { ...patch } });
      if (Object.prototype.hasOwnProperty.call(patch, "home_address")) current.home_address = patch.home_address;
      if (Object.prototype.hasOwnProperty.call(patch, "phone")) {
        current.phone = patch.phone;
        if (patch.phone === null) preferences.call_enabled = false;
      }
      return { ...current };
    },
  };
}

const SCOPE = Object.freeze({ uid: "tenant-a", chatId: "101" });

test("CLOUD-05 profile commands normalize home and phone and reject unsafe values", () => {
  assert.deepEqual(
    validateCommand({ type: "profile.set", field: "home_address", value: "  Shinjuku, Tokyo  " }),
    { type: "profile.set", field: "home_address", value: "Shinjuku, Tokyo" },
  );
  assert.deepEqual(
    validateCommand({ type: "profile.set", field: "phone", value: "090-1234-5678" }),
    { type: "profile.set", field: "phone", value: "+819012345678" },
  );
  assert.deepEqual(
    validateCommand({ type: "profile.set", field: "phone", value: null }),
    { type: "profile.set", field: "phone", value: null },
  );
  for (const bad of [
    { type: "profile.set", field: "home_address", value: "   " },
    { type: "profile.set", field: "home_address", value: "x".repeat(241) },
    { type: "profile.set", field: "phone", value: "not-a-phone" },
    { type: "profile.set", field: "uid", value: "someone-else" },
    { type: "profile.set", field: "phone", value: null, uid: "someone-else" },
  ]) assert.throws(() => validateCommand(bad), /invalid_action/);
});

test("CLOUD-05 Telegram natural language maps home/phone edits onto the existing command path", () => {
  assert.deepEqual(parseUserCommand("set home Shinjuku, Tokyo"), {
    kind: "command",
    command: { type: "profile.set", field: "home_address", value: "Shinjuku, Tokyo" },
  });
  assert.deepEqual(parseUserCommand("自宅を 新宿区西新宿 にして"), {
    kind: "command",
    command: { type: "profile.set", field: "home_address", value: "新宿区西新宿" },
  });
  assert.deepEqual(parseUserCommand("set phone 090-1234-5678"), {
    kind: "command",
    command: { type: "profile.set", field: "phone", value: "+819012345678" },
  });
  assert.deepEqual(parseUserCommand("電話番号を削除"), {
    kind: "command",
    command: { type: "profile.set", field: "phone", value: null },
  });
  assert.ok(parseUserCommand("help me").availableActions.some((value) => /home|自宅/.test(value)));
  assert.ok(parseUserCommand("help me").availableActions.some((value) => /phone|電話番号/.test(value)));
});

test("CLOUD-05 profile mutation is tenant-scoped, idempotent, and phone removal disables calls", async () => {
  const store = commandStore();
  const home = await executeUserCommand(
    SCOPE,
    { type: "profile.set", field: "home_address", value: "  New base  " },
    { store, idempotencyKey: "profile-home-0001" },
  );
  assert.equal(home.ok, true);
  assert.equal(home.message, "Profile updated");
  assert.deepEqual(store.mutations[0], { scope: SCOPE, patch: { home_address: "New base" } });

  const removed = await executeUserCommand(
    SCOPE,
    { type: "profile.set", field: "phone", value: null },
    { store, idempotencyKey: "profile-phone-0001" },
  );
  const replay = await executeUserCommand(
    SCOPE,
    { type: "profile.set", field: "phone", value: null },
    { store, idempotencyKey: "profile-phone-0001" },
  );
  assert.deepEqual(replay, removed);
  assert.equal(store.preferences.call_enabled, false);
  assert.equal(store.mutations.filter((item) => Object.prototype.hasOwnProperty.call(item.patch, "phone")).length, 1);

  await assert.rejects(
    executeUserCommand(
      { uid: "tenant-a", chatId: "202" },
      { type: "profile.set", field: "home_address", value: "Foreign" },
      { store, idempotencyKey: "profile-cross-0001" },
    ),
    /scope_mismatch/,
  );
});

test("CLOUD-05 existing profile RPC extends keys without changing its row-shaped return contract", () => {
  const migration = path.join(__dirname, "../migrations/2026-09-06-lm-cloud-settings-recovery.sql");
  assert.equal(fs.existsSync(migration), true, "CLOUD-05 migration must exist");
  const sql = fs.readFileSync(migration, "utf8");
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.mutate_lm_panel_user\s*\(/i);
  assert.match(sql, /uid\s*=\s*p_uid[\s\S]*telegram_chat_id::text\s*=\s*p_chat_id[\s\S]*FOR UPDATE/i);
  assert.match(sql, /jsonb_object_keys\(p_patch\)/i);
  assert.match(sql, /home_address/i);
  assert.match(sql, /phone/i);
  assert.match(sql, /call_enabled\s*=\s*false/i);
  assert.match(sql, /to_jsonb\(lm_users\.\*\)/i);
  assert.match(sql, /REVOKE ALL ON FUNCTION public\.mutate_lm_panel_user[\s\S]*FROM PUBLIC, anon, authenticated/i);
  assert.match(sql, /GRANT EXECUTE ON FUNCTION public\.mutate_lm_panel_user[\s\S]*TO service_role/i);
});
