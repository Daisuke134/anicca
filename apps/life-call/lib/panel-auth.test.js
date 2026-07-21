"use strict";

const test = require("node:test");
const assert = require("node:assert");
const crypto = require("crypto");
const http = require("http");
const fs = require("fs");
const path = require("path");

const { createPanelToken, sendPanelLink, handlePanelRequest } = require("./panel-auth.js");
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

test("LM-33a: /panel token is 256-bit opaque, hash-only at rest, and expires in five minutes", async () => {
  const calls = [];
  const now = new Date("2026-07-21T00:00:00.000Z");
  const rawBytes = Buffer.alloc(32, 0xab);

  const result = await createPanelToken({ uid: "lm_u1", chatId: "123" }, {
    supaUrl: "https://db.example",
    supaKey: "service-key",
    panelBaseUrl: "https://life.example",
    now: () => now,
    randomBytes: (size) => {
      assert.equal(size, 32);
      return rawBytes;
    },
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return { ok: true, status: 201 };
    },
  });

  const token = rawBytes.toString("base64url");
  assert.equal(result.url, `https://life.example/panel?t=${token}`);
  assert.equal(result.token, token);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "https://db.example/rest/v1/lm_panel_tokens");
  const stored = JSON.parse(calls[0].init.body);
  assert.deepEqual(stored, {
    token_hash: crypto.createHash("sha256").update(token).digest("hex"),
    uid: "lm_u1",
    chat_id: "123",
    expires_at: "2026-07-21T00:05:00.000Z",
  });
  assert.doesNotMatch(calls[0].init.body, new RegExp(token));
});

test("LM-33a: a valid one-time token is burned and exchanged for a separate 24-hour session", async () => {
  const rawToken = Buffer.alloc(32, 0x11).toString("base64url");
  const sessionBytes = Buffer.alloc(32, 0x22);
  const calls = [];

  await withPanelServer({
    supaUrl: "https://db.example",
    supaKey: "service-key",
    now: () => new Date("2026-07-21T00:00:00.000Z"),
    randomBytes: (size) => {
      assert.equal(size, 32);
      return sessionBytes;
    },
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      if (url.endsWith("/rpc/claim_lm_panel_token")) {
        assert.deepEqual(JSON.parse(init.body), { p_token_hash: crypto.createHash("sha256").update(rawToken).digest("hex") });
        return { ok: true, status: 200, json: async () => [{ uid: "lm_u1", chat_id: "123" }] };
      }
      if (url.endsWith("/lm_panel_sessions")) return { ok: true, status: 201 };
      throw new Error(`unexpected URL ${url}`);
    },
  }, async (base) => {
    const response = await fetch(`${base}/panel?t=${rawToken}`, { redirect: "manual" });
    assert.equal(response.status, 303);
    assert.equal(response.headers.get("location"), "/panel");
    assert.equal(
      response.headers.get("set-cookie"),
      `lm_panel_session=${sessionBytes.toString("base64url")}; Max-Age=86400; Path=/; HttpOnly; Secure; SameSite=Lax`,
    );
    assert.equal(response.headers.get("cache-control"), "no-store");
    assert.equal(response.headers.get("referrer-policy"), "no-referrer");
  });

  assert.equal(calls.length, 2);
  const storedSession = JSON.parse(calls[1].init.body);
  assert.deepEqual(storedSession, {
    session_hash: crypto.createHash("sha256").update(sessionBytes.toString("base64url")).digest("hex"),
    uid: "lm_u1",
    chat_id: "123",
    expires_at: "2026-07-22T00:00:00.000Z",
  });
  assert.doesNotMatch(calls[1].init.body, new RegExp(sessionBytes.toString("base64url")));
});

test("LM-33a/33c: /panel with a live session renders the authenticated mirror without leaking uid", async () => {
  const session = Buffer.alloc(32, 0x33).toString("base64url");
  let lookupUrl = "";
  await withPanelServer({
    supaUrl: "https://db.example",
    supaKey: "service-key",
    now: () => new Date("2026-07-21T00:00:00.000Z"),
    fetchImpl: async (url) => {
      lookupUrl = url;
      return { ok: true, status: 200, json: async () => [{ uid: "lm_u1" }] };
    },
  }, async (base) => {
    const response = await fetch(`${base}/panel`, {
      headers: { Cookie: `other=x; lm_panel_session=${session}` },
    });
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("cache-control"), "no-store");
    const html = await response.text();
    assert.match(html, /<h1>Anicca Life Manager<\/h1>/);
    for (const section of ["timeline", "scores", "ledger", "gates", "settings"]) {
      assert.match(html, new RegExp(`data-panel-section="${section}"`));
    }
    assert.doesNotMatch(html, /lm_u1/);
  });
  const lookup = new URL(lookupUrl);
  assert.equal(lookup.pathname, "/rest/v1/lm_panel_sessions");
  assert.equal(lookup.searchParams.get("session_hash"), `eq.${crypto.createHash("sha256").update(session).digest("hex")}`);
  assert.equal(lookup.searchParams.get("expires_at"), "gt.2026-07-21T00:00:00.000Z");
  assert.equal(lookup.searchParams.get("select"), "uid");
  assert.equal(lookup.searchParams.get("limit"), "1");
});

test("LM-33a negative: reusing a burned token returns 403", async () => {
  const token = Buffer.alloc(32, 0x44).toString("base64url");
  let claims = 0;
  await withPanelServer({
    supaUrl: "https://db.example",
    supaKey: "service-key",
    randomBytes: () => Buffer.alloc(32, 0x45),
    fetchImpl: async (url) => {
      if (url.endsWith("/rpc/claim_lm_panel_token")) {
        claims++;
        return { ok: true, status: 200, json: async () => claims === 1 ? [{ uid: "lm_u1", chat_id: "123" }] : [] };
      }
      if (url.endsWith("/lm_panel_sessions")) return { ok: true, status: 201 };
      throw new Error(`unexpected URL ${url}`);
    },
  }, async (base) => {
    assert.equal((await fetch(`${base}/panel?t=${token}`, { redirect: "manual" })).status, 303);
    assert.equal((await fetch(`${base}/panel?t=${token}`, { redirect: "manual" })).status, 403);
  });
  assert.equal(claims, 2);
});

test("LM-33a negative: an expired token returns 403", async () => {
  const token = Buffer.alloc(32, 0x55).toString("base64url");
  await withPanelServer({
    supaUrl: "https://db.example",
    supaKey: "service-key",
    fetchImpl: async (url) => {
      assert.match(url, /\/rpc\/claim_lm_panel_token$/);
      // The atomic database claim returns no row when expires_at <= now().
      return { ok: true, status: 200, json: async () => [] };
    },
  }, async (base) => {
    const response = await fetch(`${base}/panel?t=${token}`, { redirect: "manual" });
    assert.equal(response.status, 403);
  });
});

test("LM-33a negative: a tampered token returns 403", async () => {
  const original = Buffer.alloc(32, 0x66).toString("base64url");
  const tampered = `${original.slice(0, -1)}${original.endsWith("A") ? "B" : "A"}`;
  const originalHash = crypto.createHash("sha256").update(original).digest("hex");
  await withPanelServer({
    supaUrl: "https://db.example",
    supaKey: "service-key",
    fetchImpl: async (_url, init) => {
      const { p_token_hash: hash } = JSON.parse(init.body);
      return { ok: true, status: 200, json: async () => hash === originalHash ? [{ uid: "lm_u1", chat_id: "123" }] : [] };
    },
  }, async (base) => {
    const response = await fetch(`${base}/panel?t=${tampered}`, { redirect: "manual" });
    assert.equal(response.status, 403);
  });
});

test("LM-33a negative: /panel without a session returns 401", async () => {
  await withPanelServer({
    fetchImpl: async () => { throw new Error("must not query for a missing cookie"); },
  }, async (base) => {
    const response = await fetch(`${base}/panel`);
    assert.equal(response.status, 401);
  });
});

test("LM-33a: Telegram recognizes only the /panel command", () => {
  assert.equal(isPanelCommand("/panel"), true);
  assert.equal(isPanelCommand(" /PANEL@LifeManagerBotbot "), true);
  assert.equal(isPanelCommand("/panel please"), true);
  assert.equal(isPanelCommand("/panelx"), false);
  assert.equal(isPanelCommand("show /panel"), false);
});

test("LM-33a: Telegram /panel sends the generated single-use URL", async () => {
  const sent = [];
  const token = Buffer.alloc(32, 0x77).toString("base64url");
  const result = await sendPanelLink({ uid: "lm_u1", chatId: "123" }, {
    token: "telegram-token",
    supaUrl: "https://db.example",
    supaKey: "service-key",
    panelBaseUrl: "https://life.example/",
    randomBytes: () => Buffer.alloc(32, 0x77),
    fetchImpl: async () => ({ ok: true, status: 201 }),
    sendMessage: async (...args) => { sent.push(args); return { ok: true }; },
  });
  assert.equal(result.url, `https://life.example/panel?t=${token}`);
  assert.equal(sent.length, 1);
  assert.deepEqual(sent[0], [
    "telegram-token",
    "123",
    `Open your Anicca Life Manager panel (this link expires in 5 minutes and works once):\n${result.url}`,
  ]);
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
  assert.match(source, /if \(isPanelCommand\(u\.text\)\)/);

  const telegramSource = fs.readFileSync(path.join(__dirname, "telegram.js"), "utf8");
  assert.match(telegramSource, /return `\$\{root\}\/lm\?tg=/, "the /lm?tg onboarding handoff must remain");
});
