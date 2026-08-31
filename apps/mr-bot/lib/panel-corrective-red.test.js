"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { EventEmitter } = require("node:events");
const {
  executeUserCommand,
  buildControlCenter,
} = require("./user-command.js");
const {
  readJson,
  composioCalendarStatus,
  composioCalendarDisconnect,
  handlePanelOAuthCallback,
  createSupabaseCommandStore,
} = require("./panel-api.js");
const { tick, travelTick, askTickAll, discoveryTick } = require("../scheduler.js");

function response(items) { return { ok: true, json: async () => ({ items }) }; }
function owned(uid, extra = {}) { return { id: "ca-1", user_id: uid, toolkit: { slug: "googlecalendar" }, status: "ACTIVE", is_disabled: false, enabled: true, ...extra }; }

test("FIND-001 unsupported delegation is honest and has no success action", async () => {
  const store = {
    readUser: async () => ({ uid: "u1", telegram_chat_id: "c1", phone: "+1" }),
    readPreferences: async () => ({ delegation_enabled: true }), readLocation: async () => null,
  };
  const model = await buildControlCenter({ uid: "u1", chatId: "c1" }, { store });
  assert.deepEqual(model.controls.delegation, { state: "unavailable", reason: "No safe delegated-action runtime is available" });
  assert.equal("delegation_enabled" in model.settings, false);
});

test("FIND-001 runtime OFF blocks call/DAILY/notification per user and ON permits peers", async () => {
  const old = { c: process.env.COMPOSIO_API_KEY, m: process.env.LIFE_MAPS_KEY, s: process.env.SUPABASE_URL, g: process.env.GEMINI_API_KEY, k: process.env.SUPABASE_SERVICE_ROLE_KEY, t: process.env.LM_TELEGRAM_BOT_TOKEN };
  Object.assign(process.env, { COMPOSIO_API_KEY: "fixture", LIFE_MAPS_KEY: "fixture", SUPABASE_URL: "https://fixture.invalid", SUPABASE_SERVICE_ROLE_KEY: "fixture", GEMINI_API_KEY: "fixture", LM_TELEGRAM_BOT_TOKEN: "fixture" });
  const users = [{ uid: "off", call_enabled: false, daily_automation_enabled: false, notifications_enabled: false }, { uid: "on", call_enabled: true, daily_automation_enabled: true, notifications_enabled: true }];
  const seen = { wake: [], travel: [], ask: [], discovery: [] };
  await tick({ listUsers: async () => users, wake: async u => seen.wake.push(u.uid), now: 1 });
  await travelTick({ listUsers: async () => users, travel: async u => seen.travel.push(u.uid) });
  await askTickAll({ listUsers: async () => users, ask: async u => seen.ask.push(u.uid) });
  await discoveryTick({ listUsers: async () => users, discover: async u => seen.discovery.push(u.uid), now: 1 });
  assert.deepEqual(seen, { wake: ["on"], travel: ["on"], ask: ["on"], discovery: ["on"] });
  for (const [key, value] of Object.entries({ COMPOSIO_API_KEY: old.c, LIFE_MAPS_KEY: old.m, SUPABASE_URL: old.s, GEMINI_API_KEY: old.g, SUPABASE_SERVICE_ROLE_KEY: old.k, LM_TELEGRAM_BOT_TOKEN: old.t })) value === undefined ? delete process.env[key] : process.env[key] = value;
});

test("FIND-002 pending and concurrent duplicate executes one mutation", async () => {
  let receipt = null, mutations = 0;
  const store = {
    readUser: async () => ({ uid: "u1", telegram_chat_id: "c1" }),
    readReceipt: async () => receipt,
    claimReceipt: async (_s, _k, value) => { if (receipt) return false; receipt = value; return true; },
    finishReceipt: async (_s, _k, value) => { receipt = value; },
    patchPreferences: async () => { mutations++; await new Promise(r => setTimeout(r, 20)); return {}; },
  };
  const args = [{ uid: "u1", chatId: "c1" }, { type: "setting.set", setting: "call_enabled", value: false }, { store, idempotencyKey: "same-key-0001" }];
  const results = await Promise.allSettled([executeUserCommand(...args), executeUserCommand(...args)]);
  assert.equal(mutations, 1);
  assert.equal(results.filter(x => x.status === "rejected" && x.reason.status === 409).length, 1);
});

test("FIND-003 every API scope is rebound to current uid and chat", async () => {
  const urls = [];
  const store = createSupabaseCommandStore({ supaUrl: "https://db.test", supaKey: "k", fetchImpl: async url => {
    urls.push(String(url)); return { ok: true, json: async () => [] };
  }});
  await store.assertCurrentScope({ uid: "u1", chatId: "new-chat" });
  assert.match(urls[0], /telegram_chat_id=eq.new-chat/);
});

test("FIND-004 receipts bind uid chat_id and idempotency key", async () => {
  const urls = [];
  const store = createSupabaseCommandStore({ supaUrl: "https://db.test", supaKey: "k", fetchImpl: async (url, init = {}) => {
    urls.push({ url: String(url), init }); return { ok: true, json: async () => [] };
  }});
  await store.readReceipt({ uid: "u1", chatId: "c2" }, "receipt-0001");
  await store.finishReceipt({ uid: "u1", chatId: "c2" }, "receipt-0001", { status: "failed", result: null });
  assert.ok(urls.every(x => /chat_id=eq.c2/.test(x.url)));
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-07-21-lm-panel-control-center.sql"), "utf8");
  assert.match(sql, /PRIMARY KEY\s*\(uid,\s*chat_id,\s*idempotency_key\)/i);
});

test("FIND-005 calendar selection rejects foreign, missing identity, and ambiguity", async () => {
  for (const items of [[owned("foreign")], [{ id: "ca-1", status: "ACTIVE" }], [owned("u1"), owned("u1", { id: "ca-2" })]]) {
    await assert.rejects(composioCalendarStatus({ uid: "u1", chatId: "c1" }, { composioKey: "k", fetchImpl: async () => response(items) }), /provider_(ownership|ambiguous)/);
  }
});

test("FIND-006 disconnect verifies same account and rolls back exact account", async () => {
  const calls = [];
  const sequence = [response([owned("u1")]), { ok: true, json: async () => ({}) }, response([owned("u1", { id: "other", status: "INACTIVE" })]), { ok: true, json: async () => ({}) }, response([owned("u1")])];
  await assert.rejects(composioCalendarDisconnect({ uid: "u1", chatId: "c1" }, { composioKey: "k", fetchImpl: async (url, init = {}) => { calls.push({ url: String(url), init }); return sequence.shift(); } }), /provider_readback_failed/);
  assert.deepEqual(JSON.parse(calls[3].init.body), { enabled: true });
  assert.match(calls[3].url, /ca-1\/status$/);
});

test("FIND-007 OAuth callback requires exact owned ACTIVE provider readback", async () => {
  const req = { method: "GET", url: "/panel/oauth/calendar?state=" + "a".repeat(43), headers: { cookie: "lm_panel_session=s" } };
  let status;
  const res = { writeHead: code => { status = code; }, end() {} };
  await handlePanelOAuthCallback(req, res, { sessionScopeImpl: async () => ({ uid: "u1", chatId: "c1" }), commandStore: { claimOAuthState: async () => true }, composioKey: "k", fetchImpl: async () => response([owned("foreign")]) });
  assert.equal(status, 403);
});

test("FIND-008 connection model distinguishes connect reconnect disconnect", async () => {
  const store = { readUser: async () => ({ uid: "u1", telegram_chat_id: "c1" }), readPreferences: async () => ({}), readLocation: async () => null };
  const scope = { uid: "u1", chatId: "c1" };
  const missing = await buildControlCenter(scope, { store, calendarStatus: async () => "MISSING" });
  const disabled = await buildControlCenter(scope, { store, calendarStatus: async () => "DISABLED" });
  assert.equal(missing.connections.calendar.actionLabel, "Connect Calendar");
  assert.equal(disabled.connections.calendar.actionLabel, "Reconnect calendar");
});

test("FIND-009 request body stops retaining bytes and settles once after 32 KiB", async () => {
  const req = new EventEmitter(); let settled = 0;
  const pending = readJson(req).then(() => settled++, () => settled++);
  req.emit("data", Buffer.alloc(32 * 1024 + 1));
  for (let i = 0; i < 100; i++) req.emit("data", Buffer.alloc(4096));
  req.emit("end"); await pending;
  assert.equal(settled, 1);
  assert.equal(req.listenerCount("data"), 0);
});

test("FIND-010 corrective evidence remains pending fresh review", () => {
  const spec = fs.readFileSync(path.resolve(__dirname, "../../../docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md"), "utf8");
  assert.match(spec, /8d\.1[^\n]*\| pending — corrective local GREEN \/ fresh reviews required \|/);
});
