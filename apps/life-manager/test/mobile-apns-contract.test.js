"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { EventEmitter } = require("node:events");
const crypto = require("node:crypto");

const {
  APNS_HOSTS,
  INVALID_TOKEN_REASONS,
  buildChatNotificationPayload,
  buildProviderJwt,
  createApnsClient,
} = require("../lib/apns-client.js");
const {
  createMobilePushOrchestrator,
  isInvalidTokenResponse,
  validateCommittedOutboxRow,
} = require("../lib/mobile-push.js");

const TOKEN = "ab".repeat(32);
const CURSOR = "cursor:v1:ZXhhbXBsZQ";
const MESSAGE_ID = "message:v1:stable-1";
const APNS_ID = "123e4567-e89b-12d3-a456-426614174000";

function fakeHttp2(response, calls) {
  return {
    connect(authority) {
      calls.push({ authority });
      const session = new EventEmitter();
      session.request = (headers) => {
        const stream = new EventEmitter();
        stream.headers = headers;
        stream.setEncoding = () => {};
        stream.write = (body) => { stream.body = body; };
        stream.end = () => {
          process.nextTick(() => {
            stream.emit("response", {
              ":status": response.status,
              "apns-id": response.apnsId,
            });
            if (response.body !== undefined) stream.emit("data", JSON.stringify(response.body));
            stream.emit("end");
          });
        };
        calls.at(-1).stream = stream;
        return stream;
      };
      session.close = () => { calls.at(-1).closed = true; };
      session.destroy = () => { calls.at(-1).destroyed = true; };
      return session;
    },
  };
}

function senderOptions(response, calls, overrides = {}) {
  return {
    teamId: "TEAM123456",
    keyId: "KEY1234567",
    topic: "com.anicca.life-manager",
    tokenProvider: () => "jwt.fixture",
    http2: fakeHttp2(response, calls),
    requestIdFactory: () => APNS_ID,
    ...overrides,
  };
}

test("production and development select the documented APNs HTTP/2 hosts", async () => {
  for (const [environment, expectedHost] of Object.entries(APNS_HOSTS)) {
    const calls = [];
    const client = createApnsClient(senderOptions({ status: 200, apnsId: APNS_ID }, calls));
    await client.sendChatMessage({ token: TOKEN, environment, messageId: MESSAGE_ID, cursor: CURSOR });
    assert.equal(calls[0].authority, `https://${expectedHost}:443`);
  }
});

test("APNs request has the stable message payload, alert/sound, JWT, topic, and collapse ID", async () => {
  const calls = [];
  const client = createApnsClient(senderOptions({ status: 200, apnsId: APNS_ID }, calls));
  const result = await client.sendChatMessage({ token: TOKEN, environment: "production", messageId: MESSAGE_ID, cursor: CURSOR });
  const request = calls[0].stream;
  const payload = JSON.parse(request.body);

  assert.deepEqual(Object.keys(payload).sort(), ["aps", "cursor", "messageId", "type"].sort());
  assert.deepEqual(Object.keys(payload.aps).sort(), ["alert", "sound"].sort());
  assert.equal(payload.type, "chat_message");
  assert.equal(payload.messageId, MESSAGE_ID);
  assert.equal(payload.cursor, CURSOR);
  assert.equal(payload.aps.sound, "default");
  assert.equal(request.headers[":method"], "POST");
  assert.equal(request.headers[":path"], `/3/device/${TOKEN}`);
  assert.equal(request.headers.authorization, "bearer jwt.fixture");
  assert.equal(request.headers["apns-topic"], "com.anicca.life-manager");
  assert.equal(request.headers["apns-push-type"], "alert");
  assert.equal(request.headers["apns-priority"], "10");
  assert.equal(request.headers["apns-id"], APNS_ID);
  assert.equal(request.headers["apns-collapse-id"], "chat-message-v1-message-v1-stable-1");
  assert.equal(result.apnsId, APNS_ID);
  assert.equal(result.status, 200);
  assert.equal(result.reason, null);
});

test("the payload builder permits only stable chat facts and minimal APS fields", () => {
  const payload = buildChatNotificationPayload({ messageId: MESSAGE_ID, cursor: CURSOR, locale: "ja" });
  assert.deepEqual(Object.keys(payload).sort(), ["aps", "cursor", "messageId", "type"].sort());
  assert.deepEqual(Object.keys(payload.aps).sort(), ["alert", "sound"].sort());
  assert.equal(payload.type, "chat_message");
  assert.equal(payload.messageId, MESSAGE_ID);
  assert.equal(payload.cursor, CURSOR);
  assert.equal(payload.aps.sound, "default");
  assert.equal(JSON.stringify(payload).includes("uid"), false);
  assert.equal(JSON.stringify(payload).includes("route"), false);
  assert.equal(JSON.stringify(payload).includes("accessToken"), false);
  assert.throws(() => buildChatNotificationPayload({ messageId: "", cursor: CURSOR }), /messageId/u);
  assert.throws(() => buildChatNotificationPayload({ messageId: MESSAGE_ID, cursor: "" }), /cursor/u);
});

test("malformed tokens and environments fail closed before opening HTTP/2", async () => {
  const calls = [];
  const client = createApnsClient(senderOptions({ status: 200, apnsId: APNS_ID }, calls));
  await assert.rejects(
    () => client.sendChatMessage({ token: "not-a-token", environment: "production", messageId: MESSAGE_ID, cursor: CURSOR }),
    (error) => error.code === "apns_device_token_invalid",
  );
  await assert.rejects(
    () => client.sendChatMessage({ token: TOKEN, environment: "sandbox", messageId: MESSAGE_ID, cursor: CURSOR }),
    (error) => error.code === "apns_environment_invalid",
  );
  await assert.rejects(
    () => client.sendChatMessage({ token: TOKEN, environment: "production", messageId: MESSAGE_ID, cursor: "bad cursor" }),
    (error) => error.code === "apns_payload_invalid",
  );
  assert.equal(calls.length, 0);
});

test("provider JWT uses ES256 header and team-issued iat claims", () => {
  const keys = crypto.generateKeyPairSync("ec", { namedCurve: "prime256v1" });
  const token = buildProviderJwt({
    teamId: "TEAM123456",
    keyId: "KEY1234567",
    privateKey: keys.privateKey,
    nowSeconds: 1_754_000_000,
  });
  const [headerPart, payloadPart, signaturePart] = token.split(".");
  const header = JSON.parse(Buffer.from(headerPart, "base64url").toString("utf8"));
  const payload = JSON.parse(Buffer.from(payloadPart, "base64url").toString("utf8"));
  assert.deepEqual(header, { alg: "ES256", kid: "KEY1234567", typ: "JWT" });
  assert.deepEqual(payload, { iss: "TEAM123456", iat: 1_754_000_000 });
  assert.equal(Buffer.from(signaturePart, "base64url").length, 64);
  assert.equal(crypto.verify(
    "sha256",
    Buffer.from(`${headerPart}.${payloadPart}`),
    { key: keys.publicKey, dsaEncoding: "ieee-p1363" },
    Buffer.from(signaturePart, "base64url"),
  ), true);
});

test("APNs ID, status, and unknown provider reason are preserved", async () => {
  const calls = [];
  const client = createApnsClient(senderOptions({
    status: 418,
    apnsId: "apns-provider-id",
    body: { reason: "NewProviderReason", timestamp: 123 },
  }, calls));
  const result = await client.sendChatMessage({ token: TOKEN, environment: "production", messageId: MESSAGE_ID, cursor: CURSOR });
  assert.deepEqual(result, {
    ok: false,
    status: 418,
    apnsId: "apns-provider-id",
    reason: "NewProviderReason",
    timestamp: 123,
    invalidToken: false,
    environment: "production",
  });
  assert.equal(isInvalidTokenResponse(result), false);
});

test("documented inactive-token responses are classified for cleanup", () => {
  assert.deepEqual([...INVALID_TOKEN_REASONS].sort(), ["BadDeviceToken", "DeviceTokenNotForTopic", "Unregistered"].sort());
  assert.equal(isInvalidTokenResponse({ status: 400, reason: "BadDeviceToken" }), true);
  assert.equal(isInvalidTokenResponse({ status: 400, reason: "DeviceTokenNotForTopic" }), true);
  assert.equal(isInvalidTokenResponse({ status: 410, reason: "Unregistered" }), true);
  assert.equal(isInvalidTokenResponse({ status: 500, reason: "Unregistered" }), false);
});

test("orchestrator sends only a committed semantic row, records provider facts, and removes inactive token", async () => {
  const calls = [];
  const records = [];
  const removed = [];
  const scope = { uid: "user-a" };
  const sender = createMobilePushOrchestrator({
    apnsClient: {
      async sendChatMessage(input) {
        calls.push(input);
        return { ok: false, status: 410, apnsId: "apns-410", reason: "Unregistered", invalidToken: true, environment: input.environment };
      },
    },
    listDevices: async (seenScope) => {
      assert.deepEqual(seenScope, scope);
      return [{ deviceId: "device-a", token: TOKEN, environment: "production", locale: "en" }];
    },
    recordApnsResult: async (seenScope, receipt) => records.push({ seenScope, receipt }),
    removeDevice: async (seenScope, token, reason) => removed.push({ seenScope, token, reason }),
  });
  const row = { uid: "user-a", id: MESSAGE_ID, key: "chat.welcome", sequence: 7, cursor: CURSOR };
  const result = await sender.notifyCommittedOutbox(scope, row);

  assert.equal(calls.length, 1);
  assert.deepEqual(calls[0], { token: TOKEN, environment: "production", messageId: MESSAGE_ID, cursor: CURSOR, locale: "en" });
  assert.equal(records.length, 1);
  assert.deepEqual(records[0], {
    seenScope: scope,
    receipt: {
      uid: "user-a", messageId: MESSAGE_ID, deviceId: "device-a", environment: "production",
      ok: false, apnsId: "apns-410", status: 410, reason: "Unregistered", invalidToken: true,
    },
  });
  assert.deepEqual(removed, [{ seenScope: scope, token: TOKEN, reason: "Unregistered" }]);
  assert.deepEqual(result, { messageId: MESSAGE_ID, attempted: 1, delivered: 0, removed: 1, results: [records[0].receipt] });
});

test("orchestrator rejects an uncommitted row and never invokes APNs", async () => {
  let sends = 0;
  const sender = createMobilePushOrchestrator({
    apnsClient: { async sendChatMessage() { sends++; } },
    listDevices: async () => [{ token: TOKEN, environment: "production" }],
  });
  await assert.rejects(
    () => sender.notifyCommittedOutbox({ uid: "user-a" }, { id: MESSAGE_ID, key: "chat.welcome", cursor: CURSOR }),
    (error) => error.code === "mobile_outbox_uncommitted",
  );
  assert.equal(sends, 0);
});

test("orchestrator preserves unknown provider failures and does not delete their token", async () => {
  const removed = [];
  const records = [];
  const sender = createMobilePushOrchestrator({
    apnsClient: { async sendChatMessage() { return { ok: false, status: 503, apnsId: "apns-503", reason: "NewProviderReason", invalidToken: false, environment: "development" }; } },
    listDevices: async () => [{ deviceId: "device-a", token: TOKEN, environment: "development" }],
    recordApnsResult: async (_scope, receipt) => records.push(receipt),
    removeDevice: async (...args) => removed.push(args),
  });
  const result = await sender.notifyCommittedOutbox({ uid: "user-a" }, { id: MESSAGE_ID, sequence: 1, cursor: CURSOR, key: "chat.welcome" });
  assert.equal(result.results[0].reason, "NewProviderReason");
  assert.equal(removed.length, 0);
  assert.equal(records[0].status, 503);
});

test("orchestrator fails closed for a malformed stored device and never treats token as tenant identity", async () => {
  let sends = 0;
  const seenScopes = [];
  const sender = createMobilePushOrchestrator({
    apnsClient: { async sendChatMessage() { sends++; } },
    listDevices: async (scope) => { seenScopes.push(scope); return [{ token: "bad", environment: "production" }]; },
  });
  await assert.rejects(
    () => sender.notifyCommittedOutbox({ uid: "user-a" }, { uid: "user-a", id: MESSAGE_ID, sequence: 1, cursor: CURSOR, key: "chat.welcome" }),
    (error) => error.code === "apns_device_token_invalid",
  );
  assert.deepEqual(seenScopes, [{ uid: "user-a" }]);
  assert.equal(sends, 0);
});

test("committed-row validator requires a durable sequence and stable cursor", () => {
  assert.deepEqual(validateCommittedOutboxRow({ id: MESSAGE_ID, sequence: 1, cursor: CURSOR, key: "chat.welcome" }), {
    id: MESSAGE_ID,
    sequence: 1,
    cursor: CURSOR,
    key: "chat.welcome",
  });
  assert.throws(() => validateCommittedOutboxRow({ id: MESSAGE_ID, cursor: CURSOR }), /sequence/u);
  assert.throws(() => validateCommittedOutboxRow({ id: MESSAGE_ID, sequence: 1 }), /cursor/u);
});
