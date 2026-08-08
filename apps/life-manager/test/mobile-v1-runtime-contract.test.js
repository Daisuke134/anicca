"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { Readable } = require("node:stream");
const { readMobileBootstrap } = require("../lib/mobile-bootstrap.js");
const { projectMobileMessage } = require("../lib/mobile-outbox.js");
const { fixture } = require("./mobile-contract-support.js");
const { handleMobileV1Request } = require("../lib/mobile-v1-router.js");

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

test("router responses are directly fixture-validated across the complete Gate 3 surface", async () => {
  const scope = { uid: "user:v1:server-derived-8f3a", sessionId: "session:v1:8f3a", productLocale: "en", timezone: "America/Los_Angeles" };
  const deps = {
    authenticateMobileRequest: async () => scope,
    idempotencyStore: new Map(),
    startCalendarSession: async () => fixture("session-start.json"),
    exchangeMobileSession: async () => fixture("session.json"),
    refreshMobileSession: async () => fixture("session.json"),
    revokeMobileSession: async () => fixture("session-revoked.json"),
    readMobileBootstrap: async () => fixture("bootstrap.json"),
    patchMobileProfile: async () => fixture("profile-patch.json"),
    analyzeNextEvent: async () => fixture("analysis-route_ready.json"),
    listMobileMessages: async () => fixture("chat-page.json"),
    replyMobileQuestion: async () => fixture("question-reply.json"),
    requestMobileCall: async () => fixture("call.json"),
    upsertMobileDevice: async () => fixture("apns-device.json"),
    removeMobileDevice: async () => fixture("device-deleted.json"),
    deleteMobileAccount: async () => fixture("account-deletion.json"),
  };
  const cases = [
    ["POST", "/session/calendar/start", { identityToken: "identity:v1:fixture" }, "session-start.json"],
    ["POST", "/session/exchange", { state: "state:v1:fixture", code: "code:v1:fixture", identityToken: "identity:v1:fixture" }, "session.json"],
    ["POST", "/session/refresh", { refreshToken: "refresh-token:v1:fixture-8f3a" }, "session.json"],
    ["DELETE", "/session", undefined, "session-revoked.json"],
    ["GET", "/bootstrap", undefined, "bootstrap.json"],
    ["PATCH", "/profile", { name: "Alex Morgan", home: "100 Market Street, San Francisco", productLocale: "en" }, "profile-patch.json"],
    ["POST", "/analysis", { analysisId: "analysis:v1:route-ready-8f3a" }, "analysis-route_ready.json"],
    ["GET", "/chat", undefined, "chat-page.json"],
    ["POST", "/questions/question:v1:home-8f3a/reply", { answer: "Tokyo" }, "question-reply.json"],
    ["POST", "/calls/test", { confirmed: true }, "call.json"],
    ["PUT", "/devices/apns", { token: "aa".repeat(32), environment: "production", locale: "en", timezone: "America/Los_Angeles" }, "apns-device.json"],
    ["DELETE", "/devices/apns", { token: "aa".repeat(32) }, "device-deleted.json"],
    ["DELETE", "/account", { confirmed: true }, "account-deletion.json"],
  ];
  for (const [method, path, body, fixtureName] of cases) {
    const headers = { "idempotency-key": `${method}:${path}:fixture-8f3a` };
    if (!path.startsWith("/session/") && path !== "/session/calendar/start" && path !== "/session/exchange" && path !== "/session/refresh") headers.authorization = "Bearer access-token:v1:fixture-8f3a";
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
