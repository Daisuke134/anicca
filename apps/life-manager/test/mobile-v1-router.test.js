"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { Readable } = require("node:stream");
const { handleMobileV1Request } = require("../lib/mobile-v1-router.js");

function request(method, url, body, headers = {}) {
  const req = Readable.from(body === undefined ? [] : [JSON.stringify(body)]);
  req.method = method;
  req.url = url;
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

test("router authenticates bearer scope, emits no-store JSON, and rejects client uid authority", async () => {
  const calls = [];
  const deps = {
    authenticateMobileRequest: async (req) => { calls.push(req.headers.authorization); return { uid: "user-a", sessionId: "session-a", productLocale: "en", timezone: "UTC" }; },
    readMobileBootstrap: async (scope) => ({ user: { id: scope.uid }, calendar: { status: "connected" }, analysis: { status: "idle" }, offer: { status: "available" } }),
  };
  const res = response();
  await handleMobileV1Request(request("GET", "/api/mobile/v1/bootstrap?uid=user-b", undefined, { authorization: "Bearer access" }), res, deps);
  assert.equal(res.statusCode, 200);
  assert.equal(res.headers["cache-control"], "no-store");
  assert.equal(res.headers["content-type"], "application/json; charset=utf-8");
  assert.equal(parsed(res).user.id, "user-a");
  assert.deepEqual(calls, ["Bearer access"]);
});

test("every mutation requires idempotency and same key/body replays one side effect", async () => {
  let writes = 0;
  const deps = {
    authenticateMobileRequest: async () => ({ uid: "user-a", sessionId: "session-a", productLocale: "en", timezone: "UTC" }),
    patchMobileProfile: async () => { writes++; return { name: "A" }; },
    idempotencyStore: new Map(),
  };
  const headers = { authorization: "Bearer access", "idempotency-key": "profile-1", "content-type": "application/json" };
  const one = response();
  await handleMobileV1Request(request("PATCH", "/api/mobile/v1/profile", { name: "A" }, headers), one, deps);
  const two = response();
  await handleMobileV1Request(request("PATCH", "/api/mobile/v1/profile", { name: "A" }, headers), two, deps);
  assert.equal(writes, 1);
  assert.deepEqual(parsed(one), parsed(two));
  const missing = response();
  await handleMobileV1Request(request("PATCH", "/api/mobile/v1/profile", { name: "A" }, { authorization: "Bearer access" }), missing, deps);
  assert.equal(missing.statusCode, 400);
  assert.equal(parsed(missing).error.code, "idempotency_required");
  const conflict = response();
  await handleMobileV1Request(request("PATCH", "/api/mobile/v1/profile", { name: "B" }, headers), conflict, deps);
  assert.equal(conflict.statusCode, 409);
  assert.equal(writes, 1);
});

test("approved paths dispatch question, call, device, and deletion adapters and unknown paths fail closed", async () => {
  const seen = [];
  const deps = {
    authenticateMobileRequest: async () => ({ uid: "user-a", sessionId: "session-a", productLocale: "en", timezone: "UTC" }),
    idempotencyStore: new Map(),
    replyMobileQuestion: async (_scope, input) => { seen.push(["question", input.questionId]); return { status: "answered" }; },
    requestMobileCall: async () => { seen.push(["call"]); return { status: "placed" }; },
    upsertMobileDevice: async () => { seen.push(["device-put"]); return { deviceId: "device-a" }; },
    removeMobileDevice: async () => { seen.push(["device-delete"]); return { deleted: true }; },
    deleteMobileAccount: async () => { seen.push(["account"]); return { status: "completed" }; },
  };
  const cases = [
    ["POST", "/api/mobile/v1/questions/question-a/reply", { answer: "Tokyo" }, ["question", "question-a"]],
    ["POST", "/api/mobile/v1/calls/test", { confirmed: true }, ["call"]],
    ["PUT", "/api/mobile/v1/devices/apns", { token: "aa".repeat(32), environment: "production", locale: "en", timezone: "UTC" }, ["device-put"]],
    ["DELETE", "/api/mobile/v1/devices/apns", { token: "aa".repeat(32) }, ["device-delete"]],
    ["DELETE", "/api/mobile/v1/account", { confirmed: true }, ["account"]],
  ];
  for (const [method, path, body, expected] of cases) {
    const res = response();
    await handleMobileV1Request(request(method, path, body, { authorization: "Bearer access", "idempotency-key": `${method}:${path}` }), res, deps);
    assert.equal(res.statusCode, 200, `${method} ${path}`);
  }
  assert.deepEqual(seen, cases.map((item) => item[3]));
  const unknown = response();
  await handleMobileV1Request(request("GET", "/api/mobile/v1/unknown", undefined, { authorization: "Bearer access" }), unknown, deps);
  assert.equal(unknown.statusCode, 404);
});

test("JSON mutation content type and version prefix fail closed", async () => {
  const deps = { authenticateMobileRequest: async () => ({ uid: "user-a", sessionId: "session-a", productLocale: "en" }), idempotencyStore: new Map() };
  const invalidType = response();
  await handleMobileV1Request(request("PATCH", "/api/mobile/v1/profile", { name: "A" }, { authorization: "Bearer access", "idempotency-key": "type-1", "content-type": "text/plain" }), invalidType, deps);
  assert.equal(invalidType.statusCode, 415);
  assert.equal(parsed(invalidType).error.code, "json_required");
  const wrongVersion = response();
  await handleMobileV1Request(request("GET", "/api/mobile/v12/bootstrap", undefined, { authorization: "Bearer access" }), wrongVersion, deps);
  assert.equal(wrongVersion.statusCode, 404);
});

test("logout DELETE accepts an empty body while retaining idempotency", async () => {
  let revoked = 0;
  const deps = {
    authenticateMobileRequest: async () => ({ uid: "user-a", sessionId: "session-a", productLocale: "en" }),
    revokeMobileSession: async () => { revoked++; return { revoked: true }; },
    idempotencyStore: new Map(),
  };
  const res = response();
  await handleMobileV1Request(request("DELETE", "/api/mobile/v1/session", undefined, {
    authorization: "Bearer access", "idempotency-key": "logout-1",
  }), res, deps);
  assert.equal(res.statusCode, 200);
  assert.deepEqual(parsed(res), { revoked: true });
  assert.equal(revoked, 1);
});

test("pre-auth idempotency scopes session starts by the validated identity token", async () => {
  let starts = 0;
  const deps = {
    startCalendarSession: async () => { starts++; return { state: `state-${starts}`, authorizationUrl: "https://accounts.example.test" }; },
    idempotencyStore: new Map(),
  };
  for (const identityToken of ["identity-a", "identity-b"]) {
    const res = response();
    await handleMobileV1Request(request("POST", "/api/mobile/v1/session/calendar/start", { identityToken }, {
      "idempotency-key": "start-key", "content-type": "application/json",
    }), res, deps);
    assert.equal(res.statusCode, 200);
  }
  assert.equal(starts, 2);
});

test("refresh retries replay the exact token set while the generic receipt keeps no plaintext token", async () => {
  const idempotencyStore = new Map();
  const tokens = {
    accessToken: "access:v1:secret", refreshToken: "refresh:v1:next", tokenType: "Bearer",
    expiresAt: "2026-08-08T00:20:00.000Z", refreshExpiresAt: "2026-09-08T00:00:00.000Z",
  };
  const deps = { idempotencyStore, refreshMobileSession: async () => tokens };
  const headers = { "idempotency-key": "refresh-router-1", "content-type": "application/json" };
  const first = response();
  await handleMobileV1Request(request("POST", "/api/mobile/v1/session/refresh", { refreshToken: "refresh:v1:old" }, headers), first, deps);
  const replay = response();
  await handleMobileV1Request(request("POST", "/api/mobile/v1/session/refresh", { refreshToken: "refresh:v1:old" }, headers), replay, deps);
  assert.deepEqual(parsed(replay), tokens);
  const receipt = [...idempotencyStore.values()][0];
  assert.equal(JSON.stringify(receipt).includes(tokens.accessToken), false);
  assert.equal(JSON.stringify(receipt).includes(tokens.refreshToken), false);
});
