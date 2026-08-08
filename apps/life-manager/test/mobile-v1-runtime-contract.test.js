"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { Readable } = require("node:stream");
const { readMobileBootstrap } = require("../lib/mobile-bootstrap.js");
const { projectMobileMessage } = require("../lib/mobile-outbox.js");
const { fixture } = require("./mobile-contract-support.js");
const { handleMobileV1Request } = require("../lib/mobile-v1-router.js");
const { createMemoryMobileStore } = require("../lib/mobile-store.js");
const { sha256 } = require("../lib/mobile-utils.js");

function request(method, path, body, headers = {}) {
  const req = Readable.from(body === undefined ? [] : [JSON.stringify(body)]);
  req.method = method;
  req.url = `/api/mobile/v1${path}`;
  req.headers = { ...(body === undefined ? {} : { "content-type": "application/json" }), ...headers };
  return req;
}

function response() {
  return {
    statusCode: 200, headers: {}, body: "",
    setHeader(key, value) { this.headers[String(key).toLowerCase()] = value; },
    writeHead(status, headers = {}) { this.statusCode = status; Object.entries(headers).forEach(([key, value]) => this.setHeader(key, value)); },
    end(value = "") { this.body += value; this.ended = true; },
  };
}

function parsed(res) { return JSON.parse(res.body || "{}"); }

const FIXTURE_UID = "user:v1:server-derived-8f3a";
const ACCESS_TOKEN = "access-token:v1:fixture-8f3a";
const REFRESH_TOKEN = "refresh-token:v1:fixture-8f3a";
const FIXTURE_SESSION_ID = "session:v1:8f3a";
const FIXTURE_TIME = "2026-08-10T08:10:00.000Z";

function fixtureNow(value = FIXTURE_TIME) { return () => Date.parse(value); }

function fixtureOpaque(prefix) {
  const values = {
    "state:v1:": "state:v1:calendar-consent-8f3a",
    "access:v1:": ACCESS_TOKEN,
    "refresh:v1:": REFRESH_TOKEN,
    "session:v1:": FIXTURE_SESSION_ID,
    "family:v1:": "family:v1:8f3a",
    "deletion:v1:": "delete-capability:v1:opaque-8f3a",
  };
  return values[prefix] || `${prefix}fixture-8f3a`;
}

function fixtureUser(overrides = {}) {
  return {
    uid: FIXTURE_UID, name: null, home_address: null, product_locale: "en",
    time_zone: "America/Los_Angeles", calendar_status: "connected",
    calendar_provider: "composio_gcal", gmail_account_id: "calendar-account-8f3a",
    phone: null, calls_enabled: false, call_language: null, ...overrides,
  };
}

async function seedAccessSession(store, now = FIXTURE_TIME) {
  await store.createMobileSession({
    sessionId: FIXTURE_SESSION_ID, familyId: "family:v1:8f3a", uid: FIXTURE_UID,
    accessTokenHash: sha256(ACCESS_TOKEN), refreshTokenHash: sha256(REFRESH_TOKEN), productLocale: "en",
    accessExpiresAt: "2026-08-10T08:20:00.000Z", refreshExpiresAt: "2026-09-09T08:05:00.000Z",
    createdAt: now,
  });
}

async function realFixtureRuntime(kind) {
  const now = kind === "session-start" ? "2026-08-10T08:00:00.000Z" : kind === "session-exchange" || kind === "session-refresh" ? "2026-08-10T08:05:00.000Z" : FIXTURE_TIME;
  const user = kind === "bootstrap"
    ? fixtureUser({ calendar_provider: "composio_gcal", gmail_account_id: "calendar-account-8f3a" })
    : kind === "analysis"
      ? fixtureUser({ name: "Alex Morgan", home_address: "Shipathon Roppongi" })
      : kind === "call"
        ? fixtureUser({ name: "Alex Morgan", phone: "+14155550123", calls_enabled: true, call_language: "en" })
        : fixtureUser();
  const store = createMemoryMobileStore({
    now: fixtureNow(now), users: [user],
    callAttemptIdFactory: () => "call:v1:opaque-8f3a",
    deviceIdFactory: () => "device:v1:opaque-8f3a",
  });
  const deps = { store, now: fixtureNow(now), randomOpaque: fixtureOpaque };
  if (["session-revoke", "bootstrap", "profile", "analysis", "chat", "question", "call", "apns-put", "apns-delete", "account"].includes(kind)) {
    await seedAccessSession(store, now);
  }
  if (kind === "session-start") {
    deps.validateIdentity = async () => ({ uid: FIXTURE_UID, subject: "calendar-subject-8f3a", productLocale: "en" });
    deps.buildAuthorizationUrl = async () => fixture("session-start.json").authorizationUrl;
  }
  if (kind === "session-exchange") {
    await store.createOAuthState({
      state: "state:v1:calendar-consent-8f3a", stateHash: sha256("state:v1:calendar-consent-8f3a"),
      uid: FIXTURE_UID, subject: "calendar-subject-8f3a", provider: "google_calendar",
      expiresAt: "2026-08-10T08:10:00.000Z",
    });
    deps.validateIdentity = async () => ({ uid: FIXTURE_UID, subject: "calendar-subject-8f3a", productLocale: "en" });
    deps.exchangeCalendarCode = async () => ({ connection: { provider: "google_calendar" } });
  }
  if (kind === "session-refresh") {
    // The refresh fixture is a real stored session, not a handler return override.
    await store.createMobileSession({
      sessionId: FIXTURE_SESSION_ID, familyId: "family:v1:8f3a", uid: FIXTURE_UID,
      accessTokenHash: sha256("access-token:v1:old-8f3a"), refreshTokenHash: sha256(REFRESH_TOKEN), productLocale: "en",
      accessExpiresAt: "2026-08-10T08:20:00.000Z", refreshExpiresAt: "2026-09-09T08:05:00.000Z", createdAt: now,
    });
  }
  if (kind === "analysis") {
    const analysisFixture = fixture("analysis-route_ready.json");
    deps.fetchUpcomingEvents = async () => [{
      id: "calendar-event:v1:tokyo-tower-2026-08-10", summary: "Tokyo Tower visit", location: "Tokyo Tower",
      timezone: "America/Los_Angeles", startIso: "2026-08-10T09:05:00.000Z", endIso: "2026-08-10T10:05:00.000Z",
    }];
    deps.computeMobileRoute = async () => fixture("route.json");
    deps.encodeCursor = () => analysisFixture.message.cursor;
  }
  if (kind === "chat") {
    const chat = fixture("chat-page.json");
    await store.appendOutbox({ uid: FIXTURE_UID }, {
      id: chat.messages[0].id, cursor: chat.messages[0].cursor, type: "system", key: "chat.welcome",
      args: {}, userContent: chat.messages[0].userContent, createdAt: chat.messages[0].createdAt,
    });
    await store.appendOutbox({ uid: FIXTURE_UID }, {
      id: chat.messages[1].id, cursor: chat.messages[1].cursor, type: "route", key: "chat.route_ready",
      args: {}, userContent: chat.messages[1].userContent, route: chat.messages[1].route, createdAt: chat.messages[1].createdAt,
    });
    deps.encodeCursor = (sequence) => sequence === 2 ? chat.nextCursor : `cursor:v1:fixture-${sequence}`;
  }
  if (kind === "question") {
    await store.createQuestion({ uid: FIXTURE_UID }, { id: "question:v1:home-8f3a", type: "origin", prompt: "Where?" });
    deps.fetchUpcomingEvents = async () => [];
  }
  if (kind === "call") deps.placeCall = async () => ({ ok: true, ccid: "call-provider-receipt-8f3a" });
  if (kind === "account") deps.disconnectCalendar = async () => ({ state: "disconnected" });
  return deps;
}

test("bootstrap runtime is directly frozen by the Gate 3 bootstrap fixture", async () => {
  const expected = fixture("bootstrap.json");
  const actual = await readMobileBootstrap({ uid: expected.user.id, productLocale: expected.user.productLocale, timezone: expected.user.timezone }, {
    store: {
      async readUser() {
        return {
          uid: expected.user.id, name: expected.user.name, home_address: expected.user.home.display,
          product_locale: expected.user.productLocale, time_zone: expected.user.timezone,
          calendar_status: expected.calendar.status,
        };
      },
      async readAnalysisState() { return expected.analysis; },
    },
  });
  assert.deepEqual(actual, expected);
});

test("chat runtime messages are directly frozen by the Gate 3 chat fixture", () => {
  const expected = fixture("chat-page.json");
  const first = expected.messages[0];
  const actual = projectMobileMessage({
    id: first.id, sequence: 1, cursor: first.cursor, createdAt: first.createdAt,
    key: "chat.welcome", type: first.type, userContent: first.userContent,
    question: first.question, route: first.route,
  }, expected.messages[0].locale);
  assert.deepEqual(actual, first);
});

test("real router domain handlers are fixture-validated across the complete Gate 3 surface", async () => {
  const cases = [
    ["session-start", "POST", "/session/calendar/start", { identityToken: "identity:v1:fixture" }, "session-start.json", false],
    ["session-exchange", "POST", "/session/exchange", { state: "state:v1:calendar-consent-8f3a", code: "code:v1:fixture", identityToken: "identity:v1:fixture" }, "session.json", false],
    ["session-refresh", "POST", "/session/refresh", { refreshToken: REFRESH_TOKEN }, "session.json", false],
    ["session-revoke", "DELETE", "/session", undefined, "session-revoked.json", true],
    ["bootstrap", "GET", "/bootstrap", undefined, "bootstrap.json", true],
    ["profile", "PATCH", "/profile", { name: "Alex Morgan", home: "100 Market Street, San Francisco", productLocale: "en" }, "profile-patch.json", true],
    ["analysis", "POST", "/analysis", { analysisId: "analysis:v1:route-ready-8f3a" }, "analysis-route_ready.json", true],
    ["chat", "GET", "/chat", undefined, "chat-page.json", true],
    ["question", "POST", "/questions/question:v1:home-8f3a/reply", { answer: "Tokyo" }, "question-reply.json", true],
    ["call", "POST", "/calls/test", { confirmed: true }, "call.json", true],
    ["apns-put", "PUT", "/devices/apns", { token: "aa".repeat(32), environment: "production", locale: "en", timezone: "America/Los_Angeles" }, "apns-device.json", true],
    ["apns-delete", "DELETE", "/devices/apns", { token: "aa".repeat(32) }, "device-deleted.json", true],
    ["account", "DELETE", "/account", { confirmed: true, operationId: "deletion:v1:opaque-8f3a", deletionCapability: "delete-capability:v1:opaque-8f3a" }, "account-deletion.json", true],
  ];
  for (const [kind, method, path, body, fixtureName, authenticated] of cases) {
    const deps = await realFixtureRuntime(kind);
    const headers = { "idempotency-key": `${method}:${path}:fixture-8f3a` };
    if (authenticated) headers.authorization = `Bearer ${ACCESS_TOKEN}`;
    const result = response();
    await handleMobileV1Request(request(method, path, body, headers), result, deps);
    assert.equal(result.statusCode, 200, `${method} ${path}`);
    assert.deepEqual(parsed(result), fixture(fixtureName), `${method} ${path} response drifted from fixture`);
  }
});

test("Gate 3 response fixtures contain only public bounded fields", () => {
  const apns = fixture("apns-device.json");
  assert.deepEqual(Object.keys(apns).sort(), ["deviceId", "environment", "lastSeenAt", "locale", "timezone", "token"].sort());
  const call = fixture("call.json");
  assert.deepEqual(Object.keys(call).sort(), ["attemptId", "callLanguage", "providerReceipt", "status"].sort());
  const deletion = fixture("account-deletion.json");
  assert.deepEqual(Object.keys(deletion).sort(), ["completedAt", "deletionCapability", "operationId", "providerCleanup", "status"].sort());
  assert.match(deletion.deletionCapability, /^delete-capability:v1:/u);
  assert.equal(Object.hasOwn(call.providerReceipt, "rawToken"), false);
});
