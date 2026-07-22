"use strict";

const test = require("node:test");
const assert = require("node:assert");
const crypto = require("crypto");
const http = require("http");
const fs = require("fs");
const path = require("path");

const panelAuth = require("./panel-auth.js");

function response(status, body = null) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => typeof body === "string" ? body : JSON.stringify(body),
  };
}

async function withPanelServer(opts, run) {
  const server = http.createServer((req, res) => {
    Promise.resolve().then(() => panelAuth.handlePanelRequest(req, res, opts)).catch((error) => {
      res.writeHead(500, { "content-type": "text/plain" });
      res.end(error.message);
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    return await run(`http://127.0.0.1:${server.address().port}`);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

function signedInitData(botToken, { userId = 123, authDate = 1784678400, queryId = "fixture-query" } = {}) {
  const fields = {
    auth_date: String(authDate),
    query_id: queryId,
    user: JSON.stringify({ id: userId, first_name: "Fixture" }),
  };
  const dataCheckString = Object.keys(fields).sort().map((key) => `${key}=${fields[key]}`).join("\n");
  const secret = crypto.createHmac("sha256", "WebAppData").update(botToken).digest();
  const hash = crypto.createHmac("sha256", secret).update(dataCheckString).digest("hex");
  return new URLSearchParams({ ...fields, hash }).toString();
}

function telegramFixture() {
  const state = { replayHashes: new Set(), dbMutations: 0, sessionInserts: 0, providerMutations: 0 };
  return {
    state,
    fetchImpl: async (input, init = {}) => {
      const url = new URL(String(input));
      const body = JSON.parse(init.body || "{}");
      if (url.pathname.endsWith("/rpc/claim_lm_panel_telegram_init")) {
        assert.deepEqual(Object.keys(body).sort(), ["p_actor_id", "p_init_hash"]);
        assert.match(body.p_init_hash, /^[a-f0-9]{64}$/);
        if (body.p_actor_id !== "123") return response(200, [{ status: "unknown_actor" }]);
        if (state.replayHashes.has(body.p_init_hash)) return response(200, [{ status: "replayed" }]);
        state.replayHashes.add(body.p_init_hash);
        state.dbMutations++;
        return response(200, [{ status: "claimed", uid: "lm_u1", chat_id: "123" }]);
      }
      if (url.pathname.endsWith("/rest/v1/lm_panel_sessions")) {
        state.dbMutations++;
        state.sessionInserts++;
        return response(201);
      }
      throw new Error(`unexpected fixture URL ${url.pathname}`);
    },
  };
}

async function postTelegram(base, initData) {
  return fetch(`${base}/api/panel/session/telegram`, {
    method: "POST",
    redirect: "manual",
    headers: { Origin: "https://life.example", "Content-Type": "application/json" },
    body: JSON.stringify(initData === undefined ? {} : { initData }),
  });
}

test("PANEL-1: actual Telegram session endpoint rejects missing/forged/stale/wrong-bot/wrong-user without mutation", async (t) => {
  const botToken = "123456:expected-fixture-bot-token";
  const nowMs = 1784678400 * 1000;
  const cases = [
    ["missing", undefined, 400],
    ["forged", (() => { const p = new URLSearchParams(signedInitData(botToken)); p.set("user", JSON.stringify({ id: 999 })); return p.toString(); })(), 401],
    ["stale", signedInitData(botToken, { authDate: 1784677800 }), 401],
    ["wrong-bot", signedInitData("999999:other-fixture-bot-token"), 401],
    ["wrong-user", signedInitData(botToken, { userId: 999 }), 403],
  ];

  for (const [name, initData, expectedStatus] of cases) {
    await t.test(name, async () => {
      const fixture = telegramFixture();
      await withPanelServer({
        supaUrl: "https://db.example", supaKey: "service-key", token: botToken,
        panelOrigin: "https://life.example", panelBaseUrl: "https://life.example",
        now: () => new Date(nowMs), randomBytes: () => Buffer.alloc(32, 0x81), fetchImpl: fixture.fetchImpl,
      }, async (base) => {
        const result = await postTelegram(base, initData);
        assert.equal(result.status, expectedStatus);
        assert.equal(result.headers.get("set-cookie"), null);
      });
      assert.equal(fixture.state.dbMutations, 0);
      assert.equal(fixture.state.sessionInserts, 0);
      assert.equal(fixture.state.providerMutations, 0);
    });
  }
});

test("PANEL-1: valid initData binds one Telegram actor, returns canonical /panel, and replay mutates zero", async () => {
  const botToken = "123456:expected-fixture-bot-token";
  const fixture = telegramFixture();
  const initData = signedInitData(botToken);
  await withPanelServer({
    supaUrl: "https://db.example", supaKey: "service-key", token: botToken,
    panelOrigin: "https://life.example", panelBaseUrl: "https://life.example",
    now: () => new Date(1784678400 * 1000), randomBytes: () => Buffer.alloc(32, 0x82), fetchImpl: fixture.fetchImpl,
  }, async (base) => {
    const accepted = await postTelegram(base, initData);
    assert.equal(accepted.status, 200);
    assert.deepEqual(await accepted.json(), { redirect: "/panel" });
    assert.match(accepted.headers.get("set-cookie"), /^__Host-lm_panel_session=[A-Za-z0-9_-]{43};/);
    assert.equal(fixture.state.sessionInserts, 1);

    const beforeReplay = { ...fixture.state };
    const replayed = await postTelegram(base, initData);
    assert.equal(replayed.status, 409);
    assert.equal(replayed.headers.get("set-cookie"), null);
    assert.equal(fixture.state.dbMutations, beforeReplay.dbMutations);
    assert.equal(fixture.state.sessionInserts, beforeReplay.sessionInserts);
    assert.equal(fixture.state.providerMutations, 0);
  });
});

test("PANEL-1: semantically identical reordered initData is the same one-time replay", async () => {
  const botToken = "123456:expected-fixture-bot-token";
  const fixture = telegramFixture();
  const initData = signedInitData(botToken);
  const reorderedInitData = new URLSearchParams([...new URLSearchParams(initData).entries()].reverse()).toString();
  assert.notEqual(reorderedInitData, initData);

  await withPanelServer({
    supaUrl: "https://db.example", supaKey: "service-key", token: botToken,
    panelOrigin: "https://life.example", panelBaseUrl: "https://life.example",
    now: () => new Date(1784678400 * 1000), randomBytes: () => Buffer.alloc(32, 0x82), fetchImpl: fixture.fetchImpl,
  }, async (base) => {
    assert.equal((await postTelegram(base, initData)).status, 200);
    const afterClaim = { ...fixture.state };
    const replayed = await postTelegram(base, reorderedInitData);
    assert.equal(replayed.status, 409);
    assert.equal(replayed.headers.get("set-cookie"), null);
    assert.equal(fixture.state.dbMutations, afterClaim.dbMutations);
    assert.equal(fixture.state.sessionInserts, afterClaim.sessionInserts);
    assert.equal(fixture.state.providerMutations, 0);
  });
});

function deviceFixture() {
  const state = {
    row: null, confirmed: false, exchanged: false,
    dbMutations: 0, sessionInserts: 0, providerMutations: 0,
  };
  return {
    state,
    fetchImpl: async (input, init = {}) => {
      const url = new URL(String(input));
      const body = JSON.parse(init.body || "{}");
      if (url.pathname.endsWith("/rest/v1/lm_panel_device_challenges")) {
        assert.equal(init.method, "POST");
        state.row = { ...body };
        state.dbMutations++;
        return response(201);
      }
      if (url.pathname.endsWith("/rpc/claim_lm_panel_device_code")) {
        if (!state.row || body.p_code_hash !== state.row.code_hash) return response(200, [{ status: "not_found" }]);
        if (Date.parse(state.row.expires_at) <= Date.parse("2026-07-22T00:00:00.000Z")) return response(200, [{ status: "expired" }]);
        if (body.p_uid !== "lm_u1" || body.p_chat_id !== "123") return response(200, [{ status: "scope_mismatch" }]);
        if (state.confirmed) return response(200, [{ status: "replayed" }]);
        state.confirmed = true;
        state.row.uid = body.p_uid;
        state.row.chat_id = body.p_chat_id;
        state.dbMutations++;
        return response(200, [{ status: "claimed", uid: body.p_uid, chat_id: body.p_chat_id }]);
      }
      if (url.pathname.endsWith("/rpc/exchange_lm_panel_device_challenge")) {
        if (!state.row || body.p_challenge_hash !== state.row.challenge_hash) return response(200, [{ status: "not_found" }]);
        if (!state.confirmed) return response(200, [{ status: "pending" }]);
        if (state.exchanged) return response(200, [{ status: "replayed" }]);
        state.exchanged = true;
        state.dbMutations++;
        return response(200, [{ status: "claimed", uid: state.row.uid, chat_id: state.row.chat_id }]);
      }
      if (url.pathname.endsWith("/rest/v1/lm_panel_sessions")) {
        state.dbMutations++;
        state.sessionInserts++;
        return response(201);
      }
      throw new Error(`unexpected fixture URL ${url.pathname}`);
    },
  };
}

async function openFreshPanel(base, fixture) {
  const result = await fetch(`${base}/panel`);
  assert.equal(result.status, 200);
  assert.equal(result.url, `${base}/panel`);
  const html = await result.text();
  const code = /data-device-code="([A-Z0-9-]+)"/.exec(html)?.[1] || "";
  const challenge = /__Host-lm_panel_challenge=([^;]+)/.exec(result.headers.get("set-cookie") || "")?.[1] || "";
  assert.match(code, /^[A-Z0-9-]{6,16}$/);
  assert.match(challenge, /^[A-Za-z0-9_-]{43}$/);
  assert.match(html, /Open (?:this panel )?inside Telegram/i);
  assert.match(html, /send|enter|type/i);
  assert.doesNotMatch(html, /dashboard (?:link )?expires|new dashboard link/i);
  assert.doesNotMatch(html, new RegExp(`href="[^"]*${code}`));
  assert.match(html, /Telegram\.WebApp\.initData/);
  assert.match(html, /\/api\/panel\/session\/telegram/);
  assert.match(html, /\/api\/panel\/session\/device/);
  assert.equal(fixture.state.dbMutations, 1);
  assert.match(fixture.state.row.challenge_hash, /^[a-f0-9]{64}$/);
  assert.match(fixture.state.row.code_hash, /^[a-f0-9]{64}$/);
  assert.equal(Object.hasOwn(fixture.state.row, "challenge"), false);
  assert.equal(Object.hasOwn(fixture.state.row, "code"), false);
  assert.doesNotMatch(JSON.stringify(fixture.state.row), new RegExp(challenge));
  assert.doesNotMatch(JSON.stringify(fixture.state.row), new RegExp(code));
  return { code, challenge };
}

test("PANEL-1: fresh canonical /panel renders a hash-only device challenge code, never an auth link", async () => {
  const fixture = deviceFixture();
  await withPanelServer({
    supaUrl: "https://db.example", supaKey: "service-key", token: "fixture-token",
    panelOrigin: "https://life.example", panelBaseUrl: "https://life.example",
    now: () => new Date("2026-07-22T00:00:00.000Z"), randomBytes: () => Buffer.alloc(32, 0x83), fetchImpl: fixture.fetchImpl,
  }, async (base) => { await openFreshPanel(base, fixture); });
});

test("PANEL-1: exact Telegram actor confirms a device code once; expired/replayed/cross-user attempts mutate zero", async () => {
  assert.equal(typeof panelAuth.confirmPanelDeviceCode, "function", "production Telegram code confirmation must exist");
  if (typeof panelAuth.confirmPanelDeviceCode !== "function") return;
  const fixture = deviceFixture();
  const opts = {
    supaUrl: "https://db.example", supaKey: "service-key",
    now: () => new Date("2026-07-22T00:00:00.000Z"), fetchImpl: fixture.fetchImpl,
  };
  await withPanelServer({ ...opts, token: "fixture-token", panelOrigin: "https://life.example", panelBaseUrl: "https://life.example", randomBytes: () => Buffer.alloc(32, 0x84) }, async (base) => {
    const { code } = await openFreshPanel(base, fixture);
    assert.equal(await panelAuth.confirmPanelDeviceCode({ uid: "lm_u1", chatId: "123", actorId: "123", code }, opts), true);
    const afterClaim = fixture.state.dbMutations;
    assert.equal(await panelAuth.confirmPanelDeviceCode({ uid: "lm_u2", chatId: "456", actorId: "456", code }, opts), false);
    assert.equal(await panelAuth.confirmPanelDeviceCode({ uid: "lm_u1", chatId: "123", actorId: "999", code }, opts), false);
    assert.equal(fixture.state.dbMutations, afterClaim);
  });

  const expired = deviceFixture();
  await withPanelServer({ ...opts, token: "fixture-token", panelOrigin: "https://life.example", panelBaseUrl: "https://life.example", randomBytes: () => Buffer.alloc(32, 0x85), fetchImpl: expired.fetchImpl }, async (base) => {
    const { code } = await openFreshPanel(base, expired);
    expired.state.row.expires_at = "2026-07-21T23:59:59.000Z";
    const before = expired.state.dbMutations;
    assert.equal(await panelAuth.confirmPanelDeviceCode({ uid: "lm_u1", chatId: "123", actorId: "123", code }, { ...opts, fetchImpl: expired.fetchImpl }), false);
    assert.equal(expired.state.dbMutations, before);
  });
});

test("PANEL-1: confirmed browser challenge exchanges once into the existing secure panel cookie", async () => {
  assert.equal(typeof panelAuth.confirmPanelDeviceCode, "function", "production Telegram code confirmation must exist");
  if (typeof panelAuth.confirmPanelDeviceCode !== "function") return;
  const fixture = deviceFixture();
  const opts = {
    supaUrl: "https://db.example", supaKey: "service-key", token: "fixture-token",
    panelOrigin: "https://life.example", panelBaseUrl: "https://life.example",
    now: () => new Date("2026-07-22T00:00:00.000Z"), randomBytes: () => Buffer.alloc(32, 0x86), fetchImpl: fixture.fetchImpl,
  };
  await withPanelServer(opts, async (base) => {
    const { code, challenge } = await openFreshPanel(base, fixture);
    const pending = await fetch(`${base}/api/panel/session/device`, {
      method: "POST", headers: { Origin: "https://life.example", Cookie: `__Host-lm_panel_challenge=${challenge}` },
    });
    assert.equal(pending.status, 202);
    assert.equal(fixture.state.sessionInserts, 0);

    assert.equal(await panelAuth.confirmPanelDeviceCode({ uid: "lm_u1", chatId: "123", actorId: "123", code }, opts), true);
    const exchanged = await fetch(`${base}/api/panel/session/device`, {
      method: "POST", headers: { Origin: "https://life.example", Cookie: `__Host-lm_panel_challenge=${challenge}` },
    });
    assert.equal(exchanged.status, 200);
    assert.deepEqual(await exchanged.json(), { redirect: "/panel" });
    assert.match(exchanged.headers.get("set-cookie"), /__Host-lm_panel_session=[A-Za-z0-9_-]{43};/);
    assert.equal(fixture.state.sessionInserts, 1);

    const afterExchange = fixture.state.dbMutations;
    const replay = await fetch(`${base}/api/panel/session/device`, {
      method: "POST", headers: { Origin: "https://life.example", Cookie: `__Host-lm_panel_challenge=${challenge}` },
    });
    assert.equal(replay.status, 409);
    assert.equal(fixture.state.dbMutations, afterExchange);

    const crossBrowser = await fetch(`${base}/api/panel/session/device`, {
      method: "POST", headers: { Origin: "https://life.example", Cookie: `__Host-lm_panel_challenge=${Buffer.alloc(32, 0x99).toString("base64url")}` },
    });
    assert.equal(crossBrowser.status, 401);
    assert.equal(fixture.state.dbMutations, afterExchange);
    assert.equal(fixture.state.providerMutations, 0);
  });
});

test("PANEL-1: additive zero-link migration is hash-only, RLS enabled, and service-role only", () => {
  const migration = path.join(__dirname, "../migrations/2026-07-22-panel-zero-link-auth.sql");
  assert.equal(fs.existsSync(migration), true, "additive zero-link auth migration must exist");
  if (!fs.existsSync(migration)) return;
  const sql = fs.readFileSync(migration, "utf8");
  assert.match(sql, /CREATE TABLE IF NOT EXISTS public\.lm_panel_telegram_replays/i);
  assert.match(sql, /CREATE TABLE IF NOT EXISTS public\.lm_panel_device_challenges/i);
  assert.match(sql, /init_hash\s+text/i);
  assert.match(sql, /challenge_hash\s+text/i);
  assert.match(sql, /code_hash\s+text/i);
  assert.doesNotMatch(sql, /\b(raw_init_data|raw_code|raw_challenge|token)\b/i);
  assert.match(sql, /ENABLE ROW LEVEL SECURITY/gi);
  for (const fn of ["claim_lm_panel_telegram_init", "claim_lm_panel_device_code", "exchange_lm_panel_device_challenge"]) {
    assert.match(sql, new RegExp(`REVOKE ALL ON FUNCTION public\\.${fn}[^;]+ FROM PUBLIC, anon, authenticated`, "i"));
    assert.match(sql, new RegExp(`GRANT EXECUTE ON FUNCTION public\\.${fn}[^;]+ TO service_role`, "i"));
  }
});

test("PANEL-1: production server wires both narrow session endpoints and Telegram /panel <code>", () => {
  const source = fs.readFileSync(path.join(__dirname, "../server.js"), "utf8");
  assert.match(source, /\/api\/panel\/session\/telegram/);
  assert.match(source, /\/api\/panel\/session\/device/);
  assert.match(source, /confirmPanelDeviceCode/);
  assert.match(source, /actorId:\s*u\.userId/);
});
