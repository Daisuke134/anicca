"use strict";

const test = require("node:test");
const assert = require("node:assert");
const crypto = require("crypto");
const http = require("http");
const fs = require("fs");
const path = require("path");

const { sendPanelLink, handlePanelRequest } = require("./panel-auth.js");
const { isPanelCommand } = require("./telegram.js");

async function withPanelServer(opts, run) {
  const server = http.createServer((req, res) => {
    Promise.resolve().then(() => handlePanelRequest(req, res, opts)).catch((error) => {
      res.writeHead(500);
      res.end(error.message);
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const { port } = server.address();
    return await run(`http://127.0.0.1:${port}`);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

test("PANEL-1: a legacy ?t= URL is stripped without claiming or creating a session", async () => {
  const rawToken = Buffer.alloc(32, 0x11).toString("base64url");
  const calls = [];

  await withPanelServer({
    supaUrl: "https://db.example",
    supaKey: "service-key",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      throw new Error(`legacy panel URL must not call ${url}`);
    },
  }, async (base) => {
    const response = await fetch(`${base}/panel?t=${rawToken}`, { redirect: "manual" });
    assert.equal(response.status, 303);
    assert.equal(response.headers.get("location"), "/panel");
    assert.equal(response.headers.get("set-cookie"), null);
    assert.equal(response.headers.get("cache-control"), "no-store");
    assert.equal(response.headers.get("referrer-policy"), "no-referrer");
  });

  assert.equal(calls.length, 0);
});

test("LM-33a/33c: /panel with a live session renders the authenticated mirror without leaking uid", async () => {
  const session = Buffer.alloc(32, 0x33).toString("base64url");
  let lookupUrl = "";
  await withPanelServer({
    supaUrl: "https://db.example",
    supaKey: "service-key",
    now: () => new Date("2026-07-21T00:00:00.000Z"),
    randomBytes: () => Buffer.alloc(32, 0x34),
    fetchImpl: async (url, init) => {
      lookupUrl = url;
      assert.equal(JSON.parse(init.body).p_session_hash, crypto.createHash("sha256").update(session).digest("hex"));
      return { ok: true, status: 200, json: async () => [{ uid: "lm_u1", chat_id: "123", rotated: false }] };
    },
  }, async (base) => {
    const response = await fetch(`${base}/panel`, {
      headers: { Cookie: `other=x; lm_panel_session=${session}` },
    });
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("cache-control"), "no-store");
    const html = await response.text();
    assert.match(html, /<h1>Life Manager<\/h1>/);
    assert.doesNotMatch(html, /\bAnicca\b/i);
    for (const section of ["timeline", "scores", "ledger", "gates", "settings"]) {
      assert.match(html, new RegExp(`data-panel-section="${section}"`));
    }
    assert.doesNotMatch(html, /lm_u1/);
  });
  const lookup = new URL(lookupUrl);
  assert.equal(lookup.pathname, "/rest/v1/rpc/resolve_lm_panel_session");
});

test("LM-33a negative: /panel without a session returns human login HTML", async () => {
  await withPanelServer({
    supaUrl: "https://db.example",
    supaKey: "service-key",
    randomBytes: () => Buffer.alloc(32, 0x70),
    fetchImpl: async (url, init) => {
      assert.match(url, /\/rest\/v1\/lm_panel_device_challenges$/);
      assert.equal(init.method, "POST");
      return { ok: true, status: 201 };
    },
  }, async (base) => {
    const response = await fetch(`${base}/panel`);
    assert.equal(response.status, 200);
    assert.match(response.headers.get("content-type"), /text\/html/);
  });
});

test("LM-33a: Telegram recognizes only the /panel command", () => {
  assert.equal(isPanelCommand("/panel"), true);
  assert.equal(isPanelCommand(" /PANEL@LifeManagerBotbot "), true);
  assert.equal(isPanelCommand("/panel please"), true);
  assert.equal(isPanelCommand("/panelx"), false);
  assert.equal(isPanelCommand("show /panel"), false);
});

test("PANEL-1: Telegram /panel sends one canonical web_app button with zero token-table mutation", async () => {
  const sent = [];
  const dbCalls = [];
  const result = await sendPanelLink({ uid: "lm_u1", chatId: "123" }, {
    token: "telegram-token",
    supaUrl: "https://db.example",
    supaKey: "service-key",
    panelBaseUrl: "https://life.example/",
    fetchImpl: async (...args) => { dbCalls.push(args); return { ok: true, status: 201 }; },
    sendMessage: async (...args) => { sent.push(args); return { ok: true }; },
  });
  assert.deepEqual(result, { url: "https://life.example/panel" });
  assert.equal(dbCalls.length, 0);
  assert.equal(sent.length, 1);
  assert.equal(sent[0][0], "telegram-token");
  assert.equal(sent[0][1], "123");
  assert.doesNotMatch(sent[0][2], /expires|temporary|token|\?t=/i);
  const button = sent[0][3].reply_markup.inline_keyboard[0][0];
  assert.deepEqual(button.web_app, { url: "https://life.example/panel" });
  assert.equal(Object.hasOwn(button, "url"), false);
  const buttonUrl = new URL(button.web_app.url);
  assert.equal(buttonUrl.pathname, "/panel");
  assert.equal(buttonUrl.search, "");
  assert.equal(buttonUrl.hash, "");
});

test("PANEL-1: Telegram /panel fails closed when the canonical web_app button is rejected", async () => {
  const dbCalls = [];
  await assert.rejects(() => sendPanelLink({ uid: "lm_u1", chatId: "123" }, {
    token: "telegram-token",
    supaUrl: "https://db.example",
    supaKey: "service-key",
    panelBaseUrl: "https://life.example/",
    fetchImpl: async (...args) => { dbCalls.push(args); return { ok: true, status: 201 }; },
    sendMessage: async () => ({ ok: false, error_code: 400 }),
  }), /panel web app button send failed/);
  assert.equal(dbCalls.length, 0);
});

test("PANEL-0: live session resolves immutable uid + telegram chat", async () => {
  const { sessionScope } = require("./panel-auth.js");
  const session = Buffer.alloc(32, 0x7a).toString("base64url");
  const scope = await sessionScope(session, { supaUrl: "https://db.example", supaKey: "key", randomBytes: () => Buffer.alloc(32, 0x7b), fetchImpl: async (url, init) => {
    assert.match(url, /rpc\/resolve_lm_panel_session$/);
    assert.equal(JSON.parse(init.body).p_session_hash, crypto.createHash("sha256").update(session).digest("hex"));
    return { ok: true, json: async () => [{ uid: "u-a", chat_id: "101", rotated: false }] };
  } });
  assert.deepEqual(scope, { uid: "u-a", chatId: "101", replacement: null, csrf: require("./panel-auth.js").csrfToken(session) });
});

test("LM-33a: additive migration stores token/session hashes and atomically claims once before expiry", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-07-21-lm33a-panel-auth.sql"), "utf8");
  assert.match(sql, /CREATE TABLE IF NOT EXISTS public\.lm_panel_tokens/i);
  assert.match(sql, /token_hash\s+text\s+PRIMARY KEY/i);
  assert.match(sql, /uid\s+text\s+NOT NULL/i);
  assert.match(sql, /chat_id\s+text\s+NOT NULL/i);
  assert.match(sql, /expires_at\s+timestamptz\s+NOT NULL/i);
  assert.match(sql, /used_at\s+timestamptz/i);
  assert.match(sql, /CREATE TABLE IF NOT EXISTS public\.lm_panel_sessions/i);
  assert.match(sql, /session_hash\s+text\s+PRIMARY KEY/i);
  assert.match(sql, /UPDATE public\.lm_panel_tokens[\s\S]*used_at\s+IS\s+NULL[\s\S]*expires_at\s*>\s*now\(\)[\s\S]*RETURNING/i);
  assert.match(sql, /GRANT EXECUTE ON FUNCTION public\.claim_lm_panel_token\(text\) TO service_role/i);
});

test("LM-33a: life-call wires GET /panel and Telegram /panel without changing /lm onboarding", () => {
  const source = fs.readFileSync(path.join(__dirname, "../server.js"), "utf8");
  assert.match(source, /isPanelCommand/);
  assert.match(source, /sendPanelLink/);
  assert.match(source, /handlePanelRequest/);
  assert.match(source, /path === "\/panel"/);
  assert.match(source, /if \(isPanelCommand\(u\.text\) \|\| isPanelDeepLink\(u\.text\)/);

  const telegramSource = fs.readFileSync(path.join(__dirname, "telegram.js"), "utf8");
  assert.match(telegramSource, /return `\$\{root\}\/lm\?tg=/, "the /lm?tg onboarding handoff must remain");
});
