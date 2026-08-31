#!/usr/bin/env node
"use strict";

const assert = require("node:assert");
const crypto = require("node:crypto");
const http = require("node:http");
const { handlePanelApiRequest } = require("../lib/panel-api.js");

const NOW = Date.parse("2026-07-21T12:00:00.000Z");
const SESSION = Buffer.alloc(32, 0x99).toString("base64url");
const SESSION_HASH = crypto.createHash("sha256").update(SESSION).digest("hex");

function response(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

async function fixtureFetch(input, init = {}) {
  const url = new URL(input);
  if (url.pathname.endsWith("/rpc/resolve_lm_panel_session")) {
    return response(JSON.parse(init.body).p_session_hash === SESSION_HASH ? [{ uid: "fixture-u1", chat_id: "101", rotated: false }] : []);
  }
  if (url.pathname.endsWith("/lm_panel_sessions")) {
    return response(url.searchParams.get("session_hash") === `eq.${SESSION_HASH}` ? [{ uid: "fixture-u1", chat_id: "101" }] : []);
  }
  assert.equal(url.searchParams.get("uid"), "eq.fixture-u1", `tenant filter missing: ${url}`);
  if (url.pathname.endsWith("/lm_users")) return response([{
    uid: "fixture-u1", call_language: "ja", wake_policy: "travel-only",
    calendar_provider: "composio_gcal", gmail_account_id: null,
    telegram_chat_id: "101", payout_destination: null,
  }]);
  if (url.pathname.endsWith("/lm_panel_preferences")) return response([{ call_time_zone: "UTC" }]);
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
  if (url.pathname.endsWith("/lm_financial_report_receipts")) return response([]);
  throw new Error(`unexpected fixture URL ${url}`);
}

const calendar = {
  listEventsRaw: async (uid) => {
    assert.equal(uid, "fixture-u1");
    return [{
      id: "fixture-event", summary: "Fixture appointment", location: "Fixture clinic",
      start: { dateTime: "2026-07-21T14:00:00.000Z", timeZone: "UTC" },
      end: { dateTime: "2026-07-21T15:00:00.000Z", timeZone: "UTC" },
    }];
  },
};

async function main() {
  const server = http.createServer((req, res) => {
    handlePanelApiRequest(req, res, {
      supaUrl: "https://fixture-db.local",
      supaKey: "fixture-service-key",
      fetchImpl: fixtureFetch,
      calendar,
      nowMs: NOW,
      timeZone: "UTC",
    }).catch((error) => {
      res.writeHead(500, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: error.message }));
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const base = `http://127.0.0.1:${server.address().port}`;
    const endpoints = ["timeline", "scores", "ledger", "gates", "settings"];
    for (const endpoint of endpoints) {
      const result = await fetch(`${base}/api/panel/${endpoint}?uid=foreign-u2`, {
        headers: { Cookie: `lm_panel_session=${SESSION}` },
      });
      const body = await result.json();
      assert.equal(result.status, 200, `${endpoint}: ${JSON.stringify(body)}`);
      assert.doesNotMatch(JSON.stringify(body), /foreign-u2|secret-u2/);
      console.log(`${endpoint}: HTTP ${result.status}`);
    }
    console.log("panel fixture smoke: 5/5 endpoints HTTP 200");
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
