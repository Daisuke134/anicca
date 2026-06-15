// ask-handler.test.js — integration tests for the life-ask Netlify handler.
//
// Covers both action=question and action=reply flows.
// Uses node:test + node:assert. Mocks `fetch` globally per test.
// Pattern mirrors travel-handler.test.js (proven template).
//
// Run: node --test apps/landing/netlify/functions/_lib/__tests__/ask-handler.test.js

"use strict";

const { test, beforeEach, afterEach } = require("node:test");
const assert = require("node:assert");
const path = require("path");

// ── Module cache helpers ───────────────────────────────────────────────────────

function clearCache(...ids) {
  for (const id of ids) {
    try {
      delete require.cache[require.resolve(id)];
    } catch (_) {}
  }
}

const HANDLER_PATH = "../../life-ask";
const GCAL_TOKEN_PATH = "../gcal-token";
const ASK_LOGIC_PATH = "../ask-logic";

let originalFetch;
let originalEnv;

beforeEach(() => {
  originalFetch = globalThis.fetch;
  originalEnv = { ...process.env };
  clearCache(HANDLER_PATH, GCAL_TOKEN_PATH, ASK_LOGIC_PATH);
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  process.env = { ...originalEnv };
  clearCache(HANDLER_PATH, GCAL_TOKEN_PATH, ASK_LOGIC_PATH);
});

// ── Helpers ────────────────────────────────────────────────────────────────────

function makeEvent(id, summary, overrides = {}) {
  return {
    id,
    summary,
    start: { dateTime: "2026-06-17T10:00:00+09:00" },
    end: { dateTime: "2026-06-17T11:00:00+09:00" },
    ...overrides,
  };
}

function buildEvent(httpMethod = "POST", queryAction, bodyAction) {
  const qsp = queryAction ? { action: queryAction } : {};
  return {
    httpMethod,
    queryStringParameters: qsp,
    body: bodyAction ? JSON.stringify({ action: bodyAction }) : null,
  };
}

function buildReplyEvent(replyBody) {
  return {
    httpMethod: "POST",
    queryStringParameters: { action: "reply" },
    body: JSON.stringify({
      message: {
        id: "msg-reply-001",
        subject: "[Ask] 場所を教えて — 歯科検診",
        body: replyBody,
      },
    }),
  };
}

// ── Test 1: 405 for non-POST ───────────────────────────────────────────────────

test("handler returns 405 for GET requests", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-test";
  const { handler } = require(HANDLER_PATH);
  const res = await handler({ httpMethod: "GET", queryStringParameters: {} });
  assert.strictEqual(res.statusCode, 405);
});

// ── Test 2: 500 when no auth credentials ──────────────────────────────────────

test("handler (question) returns 500 when no Google auth credentials", async () => {
  delete process.env.GOOGLE_CALENDAR_TOKEN;
  delete process.env.GOOGLE_REFRESH_TOKEN;
  delete process.env.GOOGLE_CLIENT_ID;
  delete process.env.GOOGLE_CLIENT_SECRET;
  process.env.AGENTMAIL_API_KEY = "am-key";
  process.env.AGENTMAIL_INBOX_ID = "inbox-id";

  globalThis.fetch = async () => {
    throw new Error("should not be called without auth");
  };

  const { handler } = require(HANDLER_PATH);
  const res = await handler(buildEvent("POST", "question"));
  assert.strictEqual(res.statusCode, 500);
  assert.ok(res.body.includes("auth_error") || res.body.includes("missing"));
});

// ── Test 3: 500 when AgentMail env vars missing ───────────────────────────────

test("handler (question) returns 500 when AGENTMAIL env vars missing", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-test";
  delete process.env.AGENTMAIL_API_KEY;
  delete process.env.AGENTMAIL_INBOX_ID;

  const { handler } = require(HANDLER_PATH);
  const res = await handler(buildEvent("POST", "question"));
  assert.strictEqual(res.statusCode, 500);
  assert.ok(res.body.includes("AGENTMAIL"));
});

// ── Test 4: action=question, no events needing ask → 200, asked=[] ─────────────

test("handler (question) returns 200 with asked=[] when all events have locations", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";
  process.env.AGENTMAIL_API_KEY = "am-key";
  process.env.AGENTMAIL_INBOX_ID = "inbox-id";
  process.env.DAIS_EMAIL = "test@example.com";

  const events = [
    makeEvent("ev1", "歯科検診", { location: "信濃町駅" }),
    makeEvent("ev2", "[Travel] 歯科検診"),
  ];

  globalThis.fetch = async (url) => {
    if (url.includes("calendar/v3")) {
      return { ok: true, json: async () => ({ items: events }) };
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const { handler } = require(HANDLER_PATH);
  const res = await handler(buildEvent("POST", "question"));
  assert.strictEqual(res.statusCode, 200);
  const body = JSON.parse(res.body);
  assert.ok(body.ok);
  assert.deepStrictEqual(body.asked, []);
  assert.strictEqual(body.checked, 2);
});

// ── Test 5: action=question, event missing location → email sent + gcal patched ──

test("handler (question) sends email and patches GCal for event missing location", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";
  process.env.AGENTMAIL_API_KEY = "am-key";
  process.env.AGENTMAIL_INBOX_ID = "inbox-123";
  process.env.DAIS_EMAIL = "dais@example.com";

  const events = [makeEvent("ev-abc", "Team Meeting")]; // no location

  let agentMailCalled = false;
  let agentMailBody = null;
  let gcalPatchCalled = false;
  let gcalPatchBody = null;

  globalThis.fetch = async (url, opts) => {
    if (url.includes("calendar/v3") && (!opts || opts.method !== "PATCH")) {
      return { ok: true, json: async () => ({ items: events }) };
    }
    if (url.includes("calendar/v3") && opts?.method === "PATCH") {
      gcalPatchCalled = true;
      gcalPatchBody = JSON.parse(opts.body);
      return { ok: true, json: async () => ({ id: "ev-abc", ...gcalPatchBody }) };
    }
    if (url.includes("agentmail.to")) {
      agentMailCalled = true;
      agentMailBody = JSON.parse(opts.body);
      return { ok: true, json: async () => ({ id: "msg-sent-001" }) };
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const { handler } = require(HANDLER_PATH);
  const res = await handler(buildEvent("POST", "question"));

  assert.strictEqual(res.statusCode, 200);
  const body = JSON.parse(res.body);
  assert.ok(body.ok);
  assert.strictEqual(body.asked.length, 1);
  assert.strictEqual(body.asked[0].eventId, "ev-abc");
  assert.strictEqual(body.asked[0].messageId, "msg-sent-001");

  // AgentMail was called with correct recipient
  assert.ok(agentMailCalled, "AgentMail send must be called");
  assert.strictEqual(agentMailBody.to, "dais@example.com");
  assert.ok(agentMailBody.subject.startsWith("[Ask]"), "subject must start with [Ask]");
  assert.ok(agentMailBody.text.includes("ev-abc"), "body must include event ID");

  // GCal was patched with pending flag
  assert.ok(gcalPatchCalled, "GCal patch must be called");
  assert.strictEqual(
    gcalPatchBody.extendedProperties?.private?.anicca_ask_pending,
    "true",
    "pending flag must be set"
  );
});

// ── Test 6: action=reply, valid reply → gcal patched with location ─────────────

test("handler (reply) patches GCal with location parsed from reply", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";

  const existingEvent = makeEvent("ev-xyz", "歯科検診", {
    extendedProperties: { private: { anicca_ask_pending: "true", anicca_ask_question_id: "msg-q1" } },
  });

  let gcalGetCalled = false;
  let gcalPatchCalled = false;
  let patchedBody = null;

  globalThis.fetch = async (url, opts) => {
    if (url.includes("calendar/v3/calendars") && url.includes("ev-xyz") && (!opts || opts.method === undefined)) {
      // GET event
      gcalGetCalled = true;
      return { ok: true, json: async () => existingEvent };
    }
    if (url.includes("calendar/v3") && opts?.method === "PATCH") {
      gcalPatchCalled = true;
      patchedBody = JSON.parse(opts.body);
      return { ok: true, json: async () => ({ ...existingEvent, location: patchedBody.location }) };
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const replyBody =
    "信濃町駅南口\n\n> Anicca より確認です。\n> Event ID: ev-xyz\nEvent ID: ev-xyz";

  const { handler } = require(HANDLER_PATH);
  const res = await handler(buildReplyEvent(replyBody));

  assert.strictEqual(res.statusCode, 200);
  const body = JSON.parse(res.body);
  assert.ok(body.ok);
  assert.strictEqual(body.eventId, "ev-xyz");
  assert.strictEqual(body.location, "信濃町駅南口");

  assert.ok(gcalGetCalled, "GCal GET must be called to fetch existing event");
  assert.ok(gcalPatchCalled, "GCal PATCH must be called with location");
  assert.strictEqual(patchedBody.location, "信濃町駅南口");

  // Pending flag must be cleared
  assert.ok(
    patchedBody.extendedProperties?.private?.anicca_ask_pending === undefined,
    "anicca_ask_pending must be removed"
  );
});

// ── Test 7: action=reply, no Event ID in reply body → 400 ────────────────────

test("handler (reply) returns 400 when reply body has no Event ID", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";

  globalThis.fetch = async () => {
    throw new Error("should not be called");
  };

  const { handler } = require(HANDLER_PATH);
  const res = await handler(
    buildReplyEvent("信濃町駅\n\n(no Event ID line here)")
  );
  assert.strictEqual(res.statusCode, 400);
  assert.ok(res.body.includes("no_event_id_in_reply"));
});

// ── Test 8: action=reply, no location found in reply → 422 ──────────────────

test("handler (reply) returns 422 when no location can be parsed from reply", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";

  globalThis.fetch = async () => {
    throw new Error("should not be called");
  };

  const { handler } = require(HANDLER_PATH);
  const replyBody = "> quoted only\n> nothing else\nEvent ID: ev-xyz";
  const res = await handler(buildReplyEvent(replyBody));
  assert.strictEqual(res.statusCode, 422);
  assert.ok(res.body.includes("no_location_found"));
});

// ── Test 9: action defaults to question when not specified ────────────────────

test("handler defaults to action=question when no action param in query or body", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";
  process.env.AGENTMAIL_API_KEY = "am-key";
  process.env.AGENTMAIL_INBOX_ID = "inbox-id";
  process.env.DAIS_EMAIL = "dais@example.com";

  globalThis.fetch = async (url) => {
    if (url.includes("calendar/v3")) {
      // Return empty events — no asks needed
      return { ok: true, json: async () => ({ items: [] }) };
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const { handler } = require(HANDLER_PATH);
  // No action param anywhere
  const res = await handler({ httpMethod: "POST", queryStringParameters: {}, body: null });

  assert.strictEqual(res.statusCode, 200);
  const body = JSON.parse(res.body);
  assert.ok(body.ok);
  assert.deepStrictEqual(body.asked, []);
});

// ── Test 10: action=question via body JSON ────────────────────────────────────

test("handler reads action=question from JSON body when not in querystring", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";
  process.env.AGENTMAIL_API_KEY = "am-key";
  process.env.AGENTMAIL_INBOX_ID = "inbox-id";

  globalThis.fetch = async (url) => {
    if (url.includes("calendar/v3")) {
      return { ok: true, json: async () => ({ items: [] }) };
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const { handler } = require(HANDLER_PATH);
  const res = await handler({
    httpMethod: "POST",
    queryStringParameters: {},
    body: JSON.stringify({ action: "question" }),
  });

  assert.strictEqual(res.statusCode, 200);
});

// ── Test 11: OAuth2 refresh token path works in question flow ─────────────────

test("handler (question) uses OAuth2 refresh token when GOOGLE_CALENDAR_TOKEN absent", async () => {
  delete process.env.GOOGLE_CALENDAR_TOKEN;
  process.env.GOOGLE_REFRESH_TOKEN = "rtoken-xyz";
  process.env.GOOGLE_CLIENT_ID = "client-id";
  process.env.GOOGLE_CLIENT_SECRET = "client-secret";
  process.env.AGENTMAIL_API_KEY = "am-key";
  process.env.AGENTMAIL_INBOX_ID = "inbox-id";

  let tokenRefreshCalled = false;

  globalThis.fetch = async (url, opts) => {
    if (url.includes("oauth2.googleapis.com/token")) {
      tokenRefreshCalled = true;
      return {
        ok: true,
        json: async () => ({ access_token: "refreshed-tok", expires_in: 3600 }),
      };
    }
    if (url.includes("calendar/v3")) {
      return { ok: true, json: async () => ({ items: [] }) };
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const { handler } = require(HANDLER_PATH);
  const res = await handler(buildEvent("POST", "question"));
  assert.strictEqual(res.statusCode, 200);
  assert.ok(tokenRefreshCalled, "OAuth2 token refresh must be called");
});
