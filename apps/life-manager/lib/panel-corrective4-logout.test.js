"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const http = require("node:http");

const auth = require("./panel-auth.js");

const secret = (byte) => Buffer.alloc(32, byte).toString("base64url");
const hash = (value) => crypto.createHash("sha256").update(value).digest("hex");
const jsonResponse = (body, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: async () => body,
});

async function withServer(handler, run) {
  const server = http.createServer((req, res) => Promise.resolve(handler(req, res)).catch((error) => {
    if (!res.headersSent) res.writeHead(error.status || 500, { "content-type": "text/plain" });
    if (!res.writableEnded) res.end(error.message);
  }));
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  try { return await run(`http://127.0.0.1:${server.address().port}`); }
  finally { await new Promise((resolve) => server.close(resolve)); }
}

test("corrective4: rendered family CSRF logs out the resolved session family and rejects forged requests", async () => {
  const raw = secret(41);
  const sibling = secret(42);
  const familyId = "00000000-0000-4000-8000-000000000041";
  const activeFamily = new Set([hash(raw), hash(sibling)]);
  const revokes = [];

  const fetchImpl = async (url, init = {}) => {
    const rpc = String(url).split("/rpc/")[1] || "";
    const body = init.body ? JSON.parse(init.body) : {};
    if (rpc === "resolve_lm_panel_session") {
      if (!activeFamily.has(body.p_session_hash)) return jsonResponse([]);
      return jsonResponse([{
        uid: "u1",
        chat_id: "101",
        family_id: familyId,
        rotated: false,
        accepted_child_hash: null,
        accepted_child_seed: null,
        cookie_max_age: 2592000,
      }]);
    }
    if (rpc === "revoke_lm_panel_session") {
      revokes.push(body);
      activeFamily.clear();
      return jsonResponse(true);
    }
    throw new Error(`unexpected request ${url}`);
  };

  await withServer((req, res) => auth.handlePanelRequest(req, res, {
    panelOrigin: "https://life.example",
    supaUrl: "https://db.example",
    supaKey: "service",
    fetchImpl,
  }), async (base) => {
    const cookie = `__Host-lm_panel_session=${raw}`;
    const page = await fetch(`${base}/panel`, { headers: { cookie } });
    assert.equal(page.status, 200);
    const html = await page.text();
    const renderedCsrf = html.match(/controlCsrf \|\| "([a-f0-9]{64})"/)?.[1] || "";
    assert.equal(renderedCsrf, auth.sha256(`${familyId}:panel-family-csrf`));
    assert.notEqual(renderedCsrf, auth.csrfToken(raw));

    const wrongOrigin = await fetch(`${base}/panel/logout`, {
      method: "POST",
      headers: { cookie, origin: "https://evil.example", "x-lm-csrf": renderedCsrf },
      redirect: "manual",
    });
    assert.equal(wrongOrigin.status, 403);
    assert.equal(revokes.length, 0);

    const wrongCsrf = await fetch(`${base}/panel/logout`, {
      method: "POST",
      headers: { cookie, origin: "https://life.example", "x-lm-csrf": "0".repeat(64) },
      redirect: "manual",
    });
    assert.equal(wrongCsrf.status, 403);
    assert.equal(revokes.length, 0);

    const logout = await fetch(`${base}/panel/logout`, {
      method: "POST",
      headers: { cookie, origin: "https://life.example", "x-lm-csrf": renderedCsrf },
      redirect: "manual",
    });
    assert.deepEqual({ status: logout.status, revokes: revokes.length }, { status: 303, revokes: 1 });
    assert.equal(logout.headers.get("location"), "/panel");
    const clearedCookies = logout.headers.get("set-cookie") || "";
    assert.match(clearedCookies, /__Host-lm_panel_session=; Max-Age=0/);
    assert.match(clearedCookies, /(?:^|[,\n]\s*)lm_panel_session=; Max-Age=0/);
    assert.deepEqual(revokes, [{ p_session_hash: hash(raw) }]);
    assert.equal(activeFamily.size, 0);

    const revisit = await fetch(`${base}/panel`, { headers: { cookie } });
    assert.equal(revisit.status, 200);
    assert.match(await revisit.text(), /Get a new dashboard link/);
  });
});
