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

// ── Test 3: action=question is GCal-read-only — does NOT send mail or patch ─────
// gog can't run on Netlify, so question no longer needs AgentMail env vars and
// must NOT call AgentMail or PATCH GCal. It returns the events to ask (toAsk).

test("handler (question) is GCal-read-only: no AgentMail, no PATCH, returns toAsk", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-test";
  delete process.env.AGENTMAIL_API_KEY;
  delete process.env.AGENTMAIL_INBOX_ID;

  const events = [makeEvent("ev-abc", "Team Meeting")]; // no location → needs ask

  let agentMailCalled = false;
  let gcalPatchCalled = false;

  globalThis.fetch = async (url, opts) => {
    if (url.includes("calendar/v3") && (!opts || opts.method !== "PATCH")) {
      return { ok: true, json: async () => ({ items: events }) };
    }
    if (url.includes("calendar/v3") && opts?.method === "PATCH") {
      gcalPatchCalled = true;
      return { ok: true, json: async () => ({}) };
    }
    if (url.includes("agentmail.to")) {
      agentMailCalled = true;
      return { ok: true, json: async () => ({ id: "x" }) };
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const { handler } = require(HANDLER_PATH);
  const res = await handler(buildEvent("POST", "question"));
  assert.strictEqual(res.statusCode, 200);
  const body = JSON.parse(res.body);
  assert.ok(body.ok);
  assert.strictEqual(body.checked, 1);
  assert.strictEqual(body.toAsk.length, 1);
  assert.strictEqual(body.toAsk[0].eventId, "ev-abc");
  assert.ok(body.toAsk[0].subject.startsWith("[Ask]"));
  assert.ok(body.toAsk[0].body.includes("ev-abc"));
  assert.strictEqual(agentMailCalled, false, "question must NOT call AgentMail");
  assert.strictEqual(gcalPatchCalled, false, "question must NOT PATCH (mark-asked does that)");
});

// ── Test 4: action=question, no events needing ask → 200, toAsk=[] ─────────────

test("handler (question) returns 200 with toAsk=[] when all events resolved", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";

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
  assert.deepStrictEqual(body.toAsk, []);
  assert.strictEqual(body.checked, 2);
});

// ── Test 5: action=mark-asked → GETs event then PATCHes pending flag ───────────

test("handler (mark-asked) fetches event and PATCHes the pending flag", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";

  const existingEvent = makeEvent("ev-abc", "Team Meeting");
  let gcalGetCalled = false;
  let gcalPatchCalled = false;
  let gcalPatchBody = null;

  globalThis.fetch = async (url, opts) => {
    if (url.includes("calendar/v3") && url.includes("ev-abc") && (!opts || opts.method === undefined)) {
      gcalGetCalled = true;
      return { ok: true, json: async () => existingEvent };
    }
    if (url.includes("calendar/v3") && opts?.method === "PATCH") {
      gcalPatchCalled = true;
      gcalPatchBody = JSON.parse(opts.body);
      return { ok: true, json: async () => ({ id: "ev-abc", ...gcalPatchBody }) };
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const { handler } = require(HANDLER_PATH);
  const res = await handler({
    httpMethod: "POST",
    queryStringParameters: { action: "mark-asked" },
    body: JSON.stringify({ eventId: "ev-abc", messageId: "msg-sent-001" }),
  });

  assert.strictEqual(res.statusCode, 200);
  const body = JSON.parse(res.body);
  assert.ok(body.ok);
  assert.strictEqual(body.eventId, "ev-abc");
  assert.ok(gcalGetCalled, "mark-asked must GET the event");
  assert.ok(gcalPatchCalled, "mark-asked must PATCH the event");
  assert.strictEqual(
    gcalPatchBody.extendedProperties?.private?.anicca_ask_pending,
    "true",
    "pending flag must be set"
  );
  assert.strictEqual(
    gcalPatchBody.extendedProperties?.private?.anicca_ask_question_id,
    "msg-sent-001"
  );
});

// ── Test 5b: action=mark-asked without eventId → 400 ──────────────────────────

test("handler (mark-asked) returns 400 when eventId missing", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";
  globalThis.fetch = async () => {
    throw new Error("should not fetch");
  };
  const { handler } = require(HANDLER_PATH);
  const res = await handler({
    httpMethod: "POST",
    queryStringParameters: { action: "mark-asked" },
    body: JSON.stringify({ messageId: "m" }),
  });
  assert.strictEqual(res.statusCode, 400);
  assert.ok(res.body.includes("missing_event_id"));
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
  assert.ok(res.body.includes("no_location_or_duration_in_reply"));
});

// ── Test 8b: action=reply with duration → patches end.dateTime = start + N ─────

test("handler (reply) patches GCal duration (end) from 所要 N分 reply", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";

  // Event with end==start (duration unknown)
  const existingEvent = {
    id: "ev-dur",
    summary: "歯科検診",
    start: { dateTime: "2026-06-17T10:00:00+09:00", timeZone: "Asia/Tokyo" },
    end: { dateTime: "2026-06-17T10:00:00+09:00" },
    extendedProperties: { private: { anicca_ask_pending: "true" } },
  };

  let patchedBody = null;
  globalThis.fetch = async (url, opts) => {
    if (url.includes("calendar/v3") && url.includes("ev-dur") && (!opts || opts.method === undefined)) {
      return { ok: true, json: async () => existingEvent };
    }
    if (url.includes("calendar/v3") && opts?.method === "PATCH") {
      patchedBody = JSON.parse(opts.body);
      return { ok: true, json: async () => ({ ...existingEvent }) };
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const replyBody = "渋谷ヒカリエ 8F\n所要 90分\n---\nEvent ID: ev-dur";
  const { handler } = require(HANDLER_PATH);
  const res = await handler(buildReplyEvent(replyBody));

  assert.strictEqual(res.statusCode, 200);
  const body = JSON.parse(res.body);
  assert.strictEqual(body.location, "渋谷ヒカリエ 8F");
  assert.strictEqual(body.durationMinutes, 90);
  assert.strictEqual(patchedBody.location, "渋谷ヒカリエ 8F");
  // 10:00+09:00 + 90m = 01:30Z + 90m? compute: 10:00 JST = 01:00Z; +90m = 02:30Z
  assert.strictEqual(patchedBody.end.dateTime, "2026-06-17T02:30:00.000Z");
  assert.strictEqual(patchedBody.end.timeZone, "Asia/Tokyo");
});

// ── Test 8c: duration-only reply must NOT write a bogus location ───────────────

test("handler (reply) duration-only reply sets end but not location", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";

  const existingEvent = {
    id: "ev-donly",
    summary: "会議",
    start: { dateTime: "2026-06-17T09:00:00+09:00" },
    end: { dateTime: "2026-06-17T09:00:00+09:00" },
    extendedProperties: { private: { anicca_ask_pending: "true" } },
  };

  let patchedBody = null;
  globalThis.fetch = async (url, opts) => {
    if (url.includes("calendar/v3") && url.includes("ev-donly") && (!opts || opts.method === undefined)) {
      return { ok: true, json: async () => existingEvent };
    }
    if (url.includes("calendar/v3") && opts?.method === "PATCH") {
      patchedBody = JSON.parse(opts.body);
      return { ok: true, json: async () => ({ ...existingEvent }) };
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const replyBody = "所要 60分\n---\nEvent ID: ev-donly";
  const { handler } = require(HANDLER_PATH);
  const res = await handler(buildReplyEvent(replyBody));

  assert.strictEqual(res.statusCode, 200);
  const body = JSON.parse(res.body);
  assert.strictEqual(body.durationMinutes, 60);
  assert.strictEqual("location" in patchedBody, false, "must NOT write a bogus location");
  assert.ok(patchedBody.end?.dateTime, "end must be set");
});

// ── Test 9: action defaults to question when not specified ────────────────────

test("handler defaults to action=question when no action param in query or body", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";

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
  assert.deepStrictEqual(body.toAsk, []);
});

// ── Test 10: action=question via body JSON ────────────────────────────────────

test("handler reads action=question from JSON body when not in querystring", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";

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

// ── Test NEW-B: reply handler returns 200 no-op for non-[Ask] messages ─────────

test("handler (reply) returns 200 no-op when message has no [Ask] subject or Event ID", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";

  globalThis.fetch = async () => {
    throw new Error("GCal should not be called for non-ask messages");
  };

  const { handler } = require(HANDLER_PATH);
  const res = await handler({
    httpMethod: "POST",
    queryStringParameters: { action: "reply" },
    body: JSON.stringify({
      message: {
        id: "msg-wake-report",
        subject: "Anicca wake — net $0.0059 / rev $0.0",
        body: "Anicca is awake and earning.",
      },
    }),
  });

  assert.strictEqual(res.statusCode, 200);
  const body = JSON.parse(res.body);
  assert.ok(body.ok, "non-ask messages must return ok:true");
  assert.strictEqual(body.skipped, "not_an_ask_reply", "must indicate it was skipped");
});

// ── Test NEW-C: reply handler returns 404 when GCal event not found (not 502) ──

test("handler (reply) returns 404 (not 502) when GCal event ID not found", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";

  globalThis.fetch = async (url, opts) => {
    if (url.includes("calendar/v3") && (!opts || opts.method === undefined)) {
      // Simulate GCal 404 for unknown event
      return {
        ok: false,
        status: 404,
        text: async () => JSON.stringify({ error: { code: 404, message: "Not Found" } }),
      };
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const { handler } = require(HANDLER_PATH);
  const replyBody = "信濃町駅\n\n---\nEvent ID: ev-deleted-or-unknown";
  const res = await handler(buildReplyEvent(replyBody));

  // Expect 404 not 502
  assert.strictEqual(res.statusCode, 404, "deleted/unknown event must return 404, not 502");
  assert.ok(res.body.includes("event_not_found"), "body must include event_not_found");
});

test("handler (question) uses OAuth2 refresh token when GOOGLE_CALENDAR_TOKEN absent", async () => {
  delete process.env.GOOGLE_CALENDAR_TOKEN;
  process.env.GOOGLE_REFRESH_TOKEN = "rtoken-xyz";
  process.env.GOOGLE_CLIENT_ID = "client-id";
  process.env.GOOGLE_CLIENT_SECRET = "client-secret";

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
