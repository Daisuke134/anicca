#!/usr/bin/env node
"use strict";

const assert = require("node:assert");
const crypto = require("node:crypto");
const http = require("node:http");
const { handlePanelRequest } = require("../lib/panel-auth.js");
const { handlePanelApiRequest } = require("../lib/panel-api.js");

const NOW = Date.parse("2026-07-21T12:00:00.000Z");
const SESSION = Buffer.alloc(32, 0x7c).toString("base64url");
const SESSION_HASH = crypto.createHash("sha256").update(SESSION).digest("hex");

function response(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

async function fixtureFetch(input) {
  const url = new URL(input);
  if (url.pathname.endsWith("/lm_panel_sessions")) {
    return response(url.searchParams.get("session_hash") === `eq.${SESSION_HASH}` ? [{ uid: "fixture-u1" }] : []);
  }
  assert.equal(url.searchParams.get("uid"), "eq.fixture-u1", `tenant filter missing: ${url}`);
  if (url.pathname.endsWith("/lm_users")) return response([{
    uid: "fixture-u1", call_language: "ja", wake_policy: "travel-only",
    calendar_provider: "composio_gcal", gmail_account_id: null,
    telegram_chat_id: "101", payout_destination: null,
  }]);
  if (url.pathname.endsWith("/lm_user_locations")) return response([{
    uid: "fixture-u1", observed_at: "2026-07-21T11:00:00.000Z", expires_at: "2026-07-21T13:00:00.000Z",
  }]);
  if (url.pathname.endsWith("/lm_wake_log")) return response([{
    uid: "fixture-u1", event_key: "fixture-event|10",
    called_at: "2026-07-21T08:50:00.000Z", answered_at: "2026-07-21T08:50:10.000Z",
  }]);
  if (url.pathname.endsWith("/lm_api_cost")) return response([{
    uid: "fixture-u1", ts: "2026-07-21T08:50:00.000Z",
    kind: "telnyx_call", quantity: 60, unit: "seconds", est_usd: 0.12,
  }]);
  if (url.pathname.endsWith("/lm_financial_ledger")) return response({ code: "PGRST205" }, 404);
  throw new Error(`unexpected fixture URL ${url}`);
}

const calendar = {
  listEventsRaw: async (uid) => {
    assert.equal(uid, "fixture-u1");
    return [{
      id: "fixture-event", summary: "プロダクト定例", location: "渋谷",
      start: { dateTime: "2026-07-21T14:00:00.000Z", timeZone: "UTC" },
      end: { dateTime: "2026-07-21T15:00:00.000Z", timeZone: "UTC" },
    }];
  },
};

function createFixtureServer() {
  return http.createServer((req, res) => {
    const pathname = new URL(req.url || "/", "http://fixture.local").pathname;
    if (pathname === "/fixture-session") {
      res.writeHead(303, {
        Location: "/panel",
        "Set-Cookie": `lm_panel_session=${SESSION}; Path=/; HttpOnly; SameSite=Lax`,
        "Cache-Control": "no-store",
      });
      res.end();
      return;
    }

    const opts = {
      supaUrl: "https://fixture-db.local",
      supaKey: "fixture-service-key",
      fetchImpl: fixtureFetch,
      calendar,
      now: () => new Date(NOW),
      nowMs: NOW,
      timeZone: "UTC",
    };
    const handler = pathname.startsWith("/api/panel/") ? handlePanelApiRequest
      : pathname === "/panel" ? handlePanelRequest : null;
    if (!handler) {
      res.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
      res.end("not found");
      return;
    }
    Promise.resolve(handler(req, res, opts)).catch((error) => {
      if (!res.headersSent) res.writeHead(500, { "content-type": "text/plain; charset=utf-8" });
      res.end(error.message);
    });
  });
}

async function listen(server) {
  const requestedPort = Number(process.env.PANEL_FIXTURE_PORT || 0);
  await new Promise((resolve) => server.listen(requestedPort, "127.0.0.1", resolve));
  return `http://127.0.0.1:${server.address().port}`;
}

async function assertShell(base) {
  const result = await fetch(`${base}/panel`, { headers: { Cookie: `lm_panel_session=${SESSION}` } });
  assert.equal(result.status, 200);
  const html = await result.text();
  const sections = ["timeline", "scores", "ledger", "gates", "settings"];
  let previous = -1;
  for (const section of sections) {
    const position = html.indexOf(`data-panel-section="${section}"`);
    assert.ok(position > previous, `${section} missing or out of order`);
    previous = position;
    console.log(`DOM ${section}: present`);
  }
  assert.doesNotMatch(html, /<(?:form|input|button|select|textarea)\b/i);
  console.log("panel DOM assert: 5/5 sections present in spec order; read-only controls 0");
}

async function main() {
  const server = createFixtureServer();
  const base = await listen(server);
  if (process.argv.includes("--serve")) {
    console.log(`panel fixture server: ${base}/fixture-session`);
    const close = () => server.close(() => process.exit(0));
    process.on("SIGINT", close);
    process.on("SIGTERM", close);
    return;
  }
  try {
    await assertShell(base);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
