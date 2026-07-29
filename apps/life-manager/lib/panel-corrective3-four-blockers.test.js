"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { chromium } = require("playwright");

const auth = require("./panel-auth.js");
const panelApi = require("./panel-api.js");
const { executeUserCommand } = require("./user-command.js");
const { renderPanelPage } = require("./panel-ui.js");

const DAY_MS = 24 * 60 * 60 * 1000;
const secret = (byte) => Buffer.alloc(32, byte).toString("base64url");
const hash = (value) => crypto.createHash("sha256").update(String(value)).digest("hex");
const jsonResponse = (body, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: async () => body,
});

async function listen(handler) {
  const server = http.createServer((req, res) => Promise.resolve(handler(req, res)).catch((error) => {
    if (!res.headersSent) res.writeHead(500, { "content-type": "text/plain" });
    if (!res.writableEnded) res.end(error.stack || error.message);
  }));
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  return {
    base: `http://127.0.0.1:${server.address().port}`,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

function controlCenterFixture() {
  const state = { call_language: "en", call_time_zone: "UTC", wake_policy: "travel-only" };
  const receipts = new Map();
  const commands = [];
  const store = {
    async assertCurrentScope(scope) { return scope.uid === "browser-u1" && scope.chatId === "101"; },
    async readUser() {
      return {
        uid: "browser-u1", name: "Browser User", telegram_chat_id: "101", phone: "+810000000000",
        calendar_provider: null, payout_destination: null, call_language: state.call_language,
        wake_policy: state.wake_policy,
      };
    },
    async readPreferences() {
      return {
        call_enabled: true, notifications_enabled: true, daily_automation_enabled: true,
        call_time_zone: state.call_time_zone,
      };
    },
    async readLocation() { return null; },
    async readReceipt(_scope, key) { return receipts.get(key) || null; },
    async claimReceipt(_scope, key, value) {
      if (receipts.has(key)) return false;
      receipts.set(key, value);
      return true;
    },
    async finishReceipt(_scope, key, value) { receipts.set(key, value); },
    async patchUser(_scope, patch) { Object.assign(state, patch); return { ...state }; },
    async patchPreferences(_scope, patch) { Object.assign(state, patch); return { ...state }; },
  };
  return { state, store, commands };
}

test("blocker 1: native selects perform real desktop/mobile DOM changes through the shared handler and scoped readback", async () => {
  const fixture = controlCenterFixture();
  let base = "";
  const server = await listen(async (req, res) => {
    const pathname = new URL(req.url, "http://panel.local").pathname;
    if (pathname === "/panel") {
      res.writeHead(200, { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" });
      res.end(renderPanelPage({ csrf: "browser-csrf" }));
      return;
    }
    if (pathname === "/api/panel/control-center" || pathname === "/api/panel/commands") {
      await panelApi.handlePanelApiRequest(req, res, {
        panelOrigin: base,
        sessionScopeImpl: async () => ({ uid: "browser-u1", chatId: "101", csrf: "browser-csrf" }),
        commandStore: fixture.store,
        calendarStatus: async () => "MISSING",
        executeCommandImpl: async (scope, command, deps) => {
          fixture.commands.push(JSON.parse(JSON.stringify(command)));
          return executeUserCommand(scope, command, deps);
        },
      });
      return;
    }
    if (pathname.startsWith("/api/panel/")) {
      res.writeHead(200, { "content-type": "application/json", "cache-control": "no-store" });
      res.end("{}");
      return;
    }
    res.writeHead(404); res.end();
  });
  base = server.base;

  const browser = await chromium.launch({ headless: true, executablePath: chromium.executablePath() });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
    await page.goto(`${base}/panel`);
    const settings = [
      ["call_language", "en", "ja", ["en", "ja"]],
      ["call_time_zone", "UTC", "Asia/Tokyo", ["Asia/Tokyo", "UTC", "Europe/London", "America/New_York", "America/Los_Angeles"]],
      ["wake_policy", "travel-only", "all-events", ["travel-only", "all-events"]],
    ];

    for (const [name, current, , options] of settings) {
      const control = page.locator(`select[data-setting="${name}"]`);
      await control.waitFor({ state: "visible", timeout: 2_000 });
      assert.equal(await control.inputValue(), current);
      assert.deepEqual(await control.locator("option").evaluateAll((nodes) => nodes.map((node) => node.value)), options);
      assert.equal(await control.isEnabled(), true);
      assert.ok((await control.boundingBox()).height >= 44);
    }

    await page.setViewportSize({ width: 375, height: 760 });
    for (const [name, , next] of settings) {
      const selector = `select[data-setting="${name}"]`;
      const responsePromise = page.waitForResponse((response) => response.url().endsWith("/api/panel/commands") && response.request().method() === "POST", { timeout: 2_000 });
      await page.locator(selector).selectOption(next);
      const response = await responsePromise;
      assert.equal(response.status(), 200);
      await page.waitForFunction(({ selector: valueSelector, expected }) => document.querySelector(valueSelector)?.value === expected, { selector, expected: next });
      const control = page.locator(selector);
      assert.equal(await control.isVisible(), true);
      assert.ok((await control.boundingBox()).height >= 44);
    }

    assert.deepEqual(fixture.commands, settings.map(([setting, , value]) => ({ type: "setting.set", setting, value })));
    assert.deepEqual(fixture.state, { call_language: "ja", call_time_zone: "Asia/Tokyo", wake_policy: "all-events" });

    await page.reload();
    for (const [name, , expected] of settings) {
      const control = page.locator(`select[data-setting="${name}"]`);
      await control.waitFor({ state: "visible", timeout: 2_000 });
      assert.equal(await control.inputValue(), expected);
    }
  } finally {
    await browser.close();
    await server.close();
  }
});

function concurrentRotationMachine(oldRaw) {
  const oldHash = hash(oldRaw);
  const rows = new Map([[oldHash, { hash: oldHash, uid: "u1", chatId: "101", familyId: "family-1", active: true, createdAt: -DAY_MS }]]);
  const calls = [];
  const responseOrder = [];
  let acceptedChildHash = "";
  let acceptedChildSeed = "";
  let releaseFirst;

  const responseRow = () => [{
    uid: "u1",
    chat_id: "101",
    family_id: "family-1",
    rotated: true,
    accepted_child_hash: acceptedChildHash,
    accepted_child_seed: acceptedChildSeed || null,
    cookie_max_age: 2_591_991,
  }];

  const fetchImpl = async (_url, init = {}) => {
    const body = JSON.parse(init.body);
    const index = calls.length;
    calls.push(body);
    const row = rows.get(body.p_session_hash);
    if (!row || !row.active) {
      if (body.p_session_hash === oldHash && acceptedChildHash) {
        const result = jsonResponse(responseRow());
        if (index === 0) {
          return new Promise((resolve) => { releaseFirst = () => { responseOrder.push(index); resolve(result); }; });
        }
        responseOrder.push(index);
        if (index === 5) setImmediate(releaseFirst);
        return result;
      }
      return jsonResponse([]);
    }
    if (body.p_session_hash !== oldHash) {
      return jsonResponse([{
        uid: row.uid, chat_id: row.chatId, family_id: row.familyId, rotated: false,
        accepted_child_hash: null, accepted_child_seed: null, cookie_max_age: 2_591_991,
      }]);
    }

    acceptedChildHash = body.p_child_hash;
    acceptedChildSeed = body.p_child_seed || "";
    row.active = false;
    rows.set(acceptedChildHash, { hash: acceptedChildHash, uid: row.uid, chatId: row.chatId, familyId: row.familyId, active: true, createdAt: 0 });
    return new Promise((resolve) => { releaseFirst = () => { responseOrder.push(index); resolve(jsonResponse(responseRow())); }; });
  };

  return { calls, fetchImpl, responseOrder, rows };
}

test("blocker 2: six distinct out-of-order pre-rotation requests converge on one live hash-only child", async () => {
  const old = secret(30);
  const machine = concurrentRotationMachine(old);
  let generated = 0;
  const opts = {
    supaUrl: "https://db.example",
    supaKey: "stable-rotation-secret",
    fetchImpl: machine.fetchImpl,
    randomBytes: () => Buffer.alloc(32, 31 + generated++),
  };

  const scopes = await Promise.all(Array.from({ length: 6 }, () => auth.resolvePanelSession(old, opts)));
  assert.deepEqual(machine.responseOrder, [1, 2, 3, 4, 5, 0]);
  assert.equal(scopes.every(Boolean), true);
  assert.equal(scopes.every((scope) => scope.replacement), true);
  assert.equal(new Set(scopes.map((scope) => scope.replacement)).size, 1);

  for (const scope of scopes) {
    const resolved = await auth.resolvePanelSession(scope.replacement, opts);
    assert.equal(resolved && resolved.uid, "u1", "every response replacement must resolve to the one active child");
  }
  assert.equal([...machine.rows.values()].filter((row) => row.active).length, 1);
  for (const call of machine.calls.slice(0, 6)) {
    assert.doesNotMatch(JSON.stringify(call), new RegExp(old));
  }

  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-07-22-lm-panel-durable-sessions.sql"), "utf8");
  assert.match(sql, /pending_child_seed/i);
  assert.doesNotMatch(sql, /DELETE FROM public\.lm_panel_sessions WHERE session_hash = s\.pending_child_hash/i);
});

function slidingSessionMachine(activeRaw, idleRaw) {
  const rows = new Map();
  const seed = (raw) => rows.set(hash(raw), { uid: raw === activeRaw ? "active-u" : "idle-u", chatId: raw === activeRaw ? "101" : "202", familyId: hash(raw).slice(0, 32), idleExpiresAt: 30 * DAY_MS, revoked: false });
  seed(activeRaw); seed(idleRaw);
  let nowMs = 0;
  const cookieMaxAge = 30 * 24 * 60 * 60 - 9;
  const fetchImpl = async (_url, init = {}) => {
    const body = JSON.parse(init.body);
    const row = rows.get(body.p_session_hash);
    if (!row || row.revoked) return jsonResponse([]);
    if (row.idleExpiresAt <= nowMs) {
      for (const candidate of rows.values()) if (candidate.familyId === row.familyId) candidate.revoked = true;
      return jsonResponse([]);
    }
    row.idleExpiresAt = nowMs + cookieMaxAge * 1000;
    return jsonResponse([{
      uid: row.uid,
      chat_id: row.chatId,
      family_id: row.familyId,
      rotated: false,
      accepted_child_hash: null,
      accepted_child_seed: null,
      cookie_max_age: cookieMaxAge,
    }]);
  };
  return { rows, fetchImpl, cookieMaxAge, setNow(value) { nowMs = value; } };
}

test("blocker 3: periodic activity survives days 30/180 with server Max-Age while a truly idle family is revoked", async () => {
  const active = secret(50), idle = secret(51);
  const machine = slidingSessionMachine(active, idle);
  const server = await listen((req, res) => auth.handlePanelRequest(req, res, {
    supaUrl: "https://db.example",
    supaKey: "service",
    fetchImpl: machine.fetchImpl,
    randomBytes: () => Buffer.alloc(32, 52),
  }));
  try {
    for (const day of [20, 40, 60, 80, 100, 120, 140, 160, 180, 200]) {
      machine.setNow(day * DAY_MS);
      const response = await fetch(`${server.base}/panel`, { headers: { cookie: `lm_panel_session=${active}` } });
      assert.equal(response.status, 200);
      const html = await response.text();
      assert.match(html, /<h1>Life Manager<\/h1>/);
      assert.doesNotMatch(html, /\bAnicca\b/i);
      assert.match(response.headers.get("set-cookie") || "", new RegExp(`__Host-lm_panel_session=${active}; Max-Age=${machine.cookieMaxAge}`));
    }

    machine.setNow(31 * DAY_MS);
    const expired = await fetch(`${server.base}/panel`, { headers: { cookie: `lm_panel_session=${idle}` } });
    assert.equal(expired.status, 200);
    assert.match(await expired.text(), /Get a new dashboard link/);
    assert.equal(machine.rows.get(hash(idle)).revoked, true);
  } finally {
    await server.close();
  }

  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-07-22-lm-panel-durable-sessions.sql"), "utf8");
  assert.match(sql, /idle_expires_at\s*=\s*now\(\)\s*\+\s*interval '30 days'/i);
  assert.doesNotMatch(sql, /s\.absolute_expires_at\s*<=\s*now\(\)/i);
});

test("blocker 4: production batch fails closed for every malformed preferences body but preserves parsed empty-array defaults", async () => {
  const oldUrl = process.env.SUPABASE_URL;
  const oldKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const oldFetch = global.fetch;
  process.env.SUPABASE_URL = "https://db.example";
  process.env.SUPABASE_SERVICE_ROLE_KEY = "service";
  delete require.cache[require.resolve("../scheduler.js")];
  const { listPaidUsers } = require("../scheduler.js");
  let preferencesBody;
  global.fetch = async (url) => {
    if (String(url).includes("/lm_users?")) return jsonResponse([{ uid: "u1" }, { uid: "u2" }]);
    if (preferencesBody instanceof Error) return { ok: true, status: 200, json: async () => { throw preferencesBody; } };
    return jsonResponse(preferencesBody);
  };

  try {
    for (const malformed of [{ error: "bad shape" }, null, "not-an-array", new Error("malformed json")]) {
      preferencesBody = malformed;
      const users = await listPaidUsers();
      assert.equal(users.length, 2);
      for (const user of users) {
        assert.equal(user.call_enabled, false);
        assert.equal(user.notifications_enabled, false);
        assert.equal(user.daily_automation_enabled, false);
      }
    }

    preferencesBody = [];
    const defaulted = await listPaidUsers();
    assert.equal(defaulted.length, 2);
    for (const user of defaulted) {
      assert.equal(user.call_enabled, true);
      assert.equal(user.notifications_enabled, true);
      assert.equal(user.daily_automation_enabled, true);
    }
  } finally {
    global.fetch = oldFetch;
    if (oldUrl === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = oldUrl;
    if (oldKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = oldKey;
    delete require.cache[require.resolve("../scheduler.js")];
  }
});
