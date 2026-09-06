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
const {
  parseSlashCommand,
  slashAliasText,
  handleSlashCommand,
} = require("./slash-command.js");

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
    async mutateProfile(scope, patch) {
      if (!(await this.assertCurrentScope(scope))) throw new Error("scope_mismatch");
      mutations.push({ scope: { ...scope }, patch: { ...patch } });
      if (Object.prototype.hasOwnProperty.call(patch, "home_address")) current.home_address = patch.home_address;
      if (Object.prototype.hasOwnProperty.call(patch, "phone")) {
        current.phone = patch.phone;
        if (patch.phone === null) preferences.call_enabled = false;
      }
      return {
        homeConfigured: Boolean(current.home_address),
        phoneConfigured: Boolean(current.phone),
        callEnabled: preferences.call_enabled,
      };
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

test("CLOUD-05 profile mutation is tenant-scoped, idempotent, and phone removal disables calls", async () => {
  const store = commandStore();
  const home = await executeUserCommand(
    SCOPE,
    { type: "profile.set", field: "home_address", value: "  New base  " },
    { store, idempotencyKey: "profile-home-0001" },
  );
  assert.equal(home.ok, true);
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

test("CLOUD-05 Telegram keeps profile editing and support in the product surface without echoing PII", async () => {
  const home = parseSlashCommand("/home  Shinjuku, Tokyo ");
  assert.equal(slashAliasText(home), "set home Shinjuku, Tokyo");
  assert.deepEqual(parseUserCommand(slashAliasText(home)), {
    kind: "command",
    command: { type: "profile.set", field: "home_address", value: "Shinjuku, Tokyo" },
  });

  const phone = parseSlashCommand("/phone 090-1234-5678");
  assert.equal(slashAliasText(phone), "set phone 090-1234-5678");
  assert.deepEqual(parseUserCommand(slashAliasText(phone)), {
    kind: "command",
    command: { type: "profile.set", field: "phone", value: "+819012345678" },
  });

  const remove = parseSlashCommand("/phone off");
  assert.equal(slashAliasText(remove), "remove phone");
  assert.deepEqual(parseUserCommand(slashAliasText(remove)), {
    kind: "command",
    command: { type: "profile.set", field: "phone", value: null },
  });

  const sent = [];
  const deps = { token: "t", chatId: "101", send: async (_token, _chatId, text) => { sent.push(text); return { ok: true }; } };
  const row = { uid: "tenant-a", telegram_chat_id: "101" };
  const noHome = await handleSlashCommand(parseSlashCommand("/home"), row, deps);
  const noPhone = await handleSlashCommand(parseSlashCommand("/phone"), row, deps);
  const support = await handleSlashCommand(parseSlashCommand("/support"), null, deps);
  assert.equal(noHome.reason, "value_required");
  assert.equal(noPhone.reason, "value_required");
  assert.equal(support.ok, true);
  assert.match(sent.join("\n"), /\/home <new home\/base address>/);
  assert.match(sent.join("\n"), /\/phone <new number>/);
  assert.match(sent.join("\n"), /https:\/\/aniccaai\.com\/support/);
  assert.match(sent.join("\n"), /data deletion|データ削除/i);
  assert.doesNotMatch(sent.join("\n"), /Shinjuku, Tokyo|090-1234-5678|819012345678/);

  const helpSent = [];
  await handleSlashCommand(parseSlashCommand("/help"), null, { ...deps, send: async (_t, _c, text) => { helpSent.push(text); return { ok: true }; } });
  assert.match(helpSent[0], /\/home/);
  assert.match(helpSent[0], /\/phone/);
  assert.match(helpSent[0], /\/support/);
});

test("CLOUD-05 profile RPC is service-role-only, scope locked, and phone removal atomically disables calls", () => {
  const migration = path.join(__dirname, "../migrations/2026-09-06-lm-cloud-settings-recovery.sql");
  assert.equal(fs.existsSync(migration), true, "CLOUD-05 migration must exist");
  const sql = fs.readFileSync(migration, "utf8");
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.mutate_lm_panel_profile\s*\(/i);
  assert.match(sql, /uid\s*=\s*p_uid[\s\S]*telegram_chat_id::text\s*=\s*p_chat_id[\s\S]*FOR UPDATE/i);
  assert.match(sql, /jsonb_object_keys\(p_patch\)/i);
  assert.match(sql, /call_enabled\s*=\s*false/i);
  assert.match(sql, /REVOKE ALL ON FUNCTION public\.mutate_lm_panel_profile[\s\S]*FROM PUBLIC, anon, authenticated/i);
  assert.match(sql, /GRANT EXECUTE ON FUNCTION public\.mutate_lm_panel_profile[\s\S]*TO service_role/i);
});
