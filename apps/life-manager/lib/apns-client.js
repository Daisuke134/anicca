"use strict";

const crypto = require("node:crypto");
const nodeHttp2 = require("node:http2");

const APNS_HOSTS = Object.freeze({
  development: "api.sandbox.push.apple.com",
  production: "api.push.apple.com",
});
const APNS_ENVIRONMENTS = new Set(Object.keys(APNS_HOSTS));
const APNS_TOKEN_RE = /^[0-9a-f]{64}$/iu;
const APNS_UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/iu;

// Apple documents BadDeviceToken (400), DeviceTokenNotForTopic (400), and
// Unregistered (410) as token-specific responses. These are the only provider
// responses for which deleting a token is safe; transient/auth/topic errors
// must remain visible and must not silently erase a device registration.
const INVALID_TOKEN_REASONS = new Set([
  "BadDeviceToken",
  "DeviceTokenNotForTopic",
  "Unregistered",
]);

const LOCALE_ALERTS = Object.freeze({
  en: Object.freeze({ title: "Life Manager", body: "You have a new message." }),
  ja: Object.freeze({ title: "Life Manager", body: "新しいメッセージがあります。" }),
});

class ApnsError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = "ApnsError";
    this.code = code;
    Object.assign(this, details);
  }
}

function nonEmpty(value, code, field) {
  const text = value == null ? "" : String(value).trim();
  if (!text) throw new ApnsError(code, `${field} is required.`);
  return text;
}

function normalizeEnvironment(value) {
  const environment = String(value || "").trim().toLowerCase();
  if (!APNS_ENVIRONMENTS.has(environment)) {
    throw new ApnsError("apns_environment_invalid", "The APNs environment is invalid.");
  }
  return environment;
}

function validateDeviceToken(value) {
  const token = String(value || "").trim().toLowerCase();
  if (!APNS_TOKEN_RE.test(token)) {
    throw new ApnsError("apns_device_token_invalid", "The APNs device token is invalid.");
  }
  return token;
}

function validateNotificationFacts(input = {}) {
  const messageId = nonEmpty(input.messageId, "apns_payload_invalid", "messageId");
  const cursor = nonEmpty(input.cursor, "apns_payload_invalid", "cursor");
  if (!/^cursor:v1:[A-Za-z0-9_-]+$/u.test(cursor)) {
    throw new ApnsError("apns_payload_invalid", "The cursor is invalid.");
  }
  return { messageId, cursor };
}

function base64url(value) {
  return Buffer.from(value).toString("base64url");
}

/**
 * Build the provider-token JWT required by APNs token authentication.
 * ES256 signatures in compact JWTs use the raw R||S form, not OpenSSL's DER
 * form; `dsaEncoding=ieee-p1363` asks Node to produce that form directly.
 */
function buildProviderJwt({ teamId, keyId, privateKey, nowSeconds = Math.floor(Date.now() / 1000) } = {}) {
  const issuer = nonEmpty(teamId, "apns_credentials_invalid", "teamId");
  const kid = nonEmpty(keyId, "apns_credentials_invalid", "keyId");
  if (!privateKey) throw new ApnsError("apns_credentials_invalid", "privateKey is required.");
  const iat = Number(nowSeconds);
  if (!Number.isSafeInteger(iat) || iat <= 0) throw new ApnsError("apns_credentials_invalid", "nowSeconds must be a positive integer.");

  const header = base64url(JSON.stringify({ alg: "ES256", kid, typ: "JWT" }));
  const payload = base64url(JSON.stringify({ iss: issuer, iat }));
  const signingInput = `${header}.${payload}`;
  let signature;
  try {
    signature = crypto.sign("sha256", Buffer.from(signingInput), {
      key: privateKey,
      dsaEncoding: "ieee-p1363",
    });
  } catch (error) {
    throw new ApnsError("apns_credentials_invalid", "The APNs private key could not sign a provider token.", { cause: error });
  }
  if (signature.length !== 64) throw new ApnsError("apns_credentials_invalid", "The APNs signature has an invalid length.");
  return `${signingInput}.${signature.toString("base64url")}`;
}

function stableCollapseId(messageId) {
  const value = nonEmpty(messageId, "apns_payload_invalid", "messageId");
  // Keep ordinary semantic IDs readable and deterministic. Hash unusually
  // long IDs so the APNs 64-byte collapse-id limit is always respected.
  const safe = value.replace(/[^A-Za-z0-9._-]+/gu, "-").replace(/^-+|-+$/gu, "") || "message";
  const readable = `chat-message-v1-${safe}`;
  if (Buffer.byteLength(readable, "utf8") <= 64) return readable;
  return `chat-message-v1-${crypto.createHash("sha256").update(value).digest("hex").slice(0, 40)}`;
}

function localeKey(locale) {
  return String(locale || "en").toLowerCase().startsWith("ja") ? "ja" : "en";
}

/**
 * APNs carries only the stable outbox address and an opaque cursor hint.
 * Route data, user identity, calendar content, and bearer credentials never
 * enter this payload.
 */
function buildChatNotificationPayload(input = {}) {
  const { messageId, cursor } = validateNotificationFacts(input);
  const alert = LOCALE_ALERTS[localeKey(input.locale)];
  return {
    aps: {
      alert: { title: alert.title, body: alert.body },
      sound: "default",
    },
    type: "chat_message",
    messageId,
    cursor,
  };
}

function responseHeader(headers, name) {
  if (!headers || typeof headers !== "object") return undefined;
  const wanted = String(name).toLowerCase();
  for (const [key, value] of Object.entries(headers)) {
    if (String(key).toLowerCase() === wanted) return Array.isArray(value) ? value[0] : value;
  }
  return undefined;
}

function parseProviderBody(text) {
  if (!text) return null;
  try {
    const value = JSON.parse(text);
    return value && typeof value === "object" ? value : null;
  } catch {
    return null;
  }
}

function invalidTokenResponse({ status, reason } = {}) {
  return Number(status) === 410 || (Number(status) === 400 && INVALID_TOKEN_REASONS.has(String(reason || "")));
}

function makeTransportError(error) {
  if (error instanceof ApnsError) return error;
  const message = error && error.message ? String(error.message) : "The APNs request failed.";
  return new ApnsError("apns_transport_error", message, { cause: error });
}

async function issueHttp2Request({ connect, authority, headers, body, environment, requestId }) {
  let session;
  try {
    session = await connect(authority, { ALPNProtocols: ["h2"] });
    if (!session || typeof session.request !== "function") throw new Error("APNs HTTP/2 session is unavailable.");
    const stream = session.request(headers);
    if (!stream || typeof stream.on !== "function") throw new Error("APNs HTTP/2 request stream is unavailable.");

    const response = await new Promise((resolve, reject) => {
      let responseHeaders = null;
      const chunks = [];
      let settled = false;
      const finish = (error, value) => {
        if (settled) return;
        settled = true;
        if (error) reject(error); else resolve(value);
      };
      stream.on("response", (value) => { responseHeaders = value || {}; });
      stream.on("data", (chunk) => { chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk))); });
      stream.on("end", () => finish(null, { responseHeaders, body: Buffer.concat(chunks).toString("utf8") }));
      stream.on("error", (error) => finish(error));
      if (typeof session.on === "function") session.on("error", (error) => finish(error));
      try {
        if (typeof stream.setEncoding === "function") stream.setEncoding("utf8");
        if (typeof stream.end === "function") {
          if (typeof stream.write === "function") stream.write(body);
          stream.end();
        } else throw new Error("APNs HTTP/2 stream cannot end.");
      } catch (error) {
        finish(error);
      }
    });
    const status = Number(responseHeader(response.responseHeaders, ":status"));
    const providerBody = parseProviderBody(response.body);
    const reason = providerBody && providerBody.reason != null
      ? String(providerBody.reason)
      : (response.body && response.body.trim() ? response.body.trim() : null);
    const result = {
      ok: Number.isFinite(status) && status >= 200 && status < 300,
      status: Number.isFinite(status) ? status : null,
      apnsId: responseHeader(response.responseHeaders, "apns-id") || requestId,
      reason,
      invalidToken: invalidTokenResponse({ status, reason }),
      environment,
    };
    if (providerBody && providerBody.timestamp != null) result.timestamp = providerBody.timestamp;
    return result;
  } catch (error) {
    throw makeTransportError(error);
  } finally {
    // A sender can later pool sessions without changing this contract. Closing
    // the injected session here keeps one request's provider state isolated and
    // ensures test/failure sessions cannot leak handles.
    try {
      if (session && typeof session.close === "function") session.close();
    } catch { /* close is best effort after the response */ }
  }
}

function createApnsClient(options = {}) {
  const topic = nonEmpty(options.topic || options.bundleId, "apns_credentials_invalid", "topic");
  const http2 = options.http2 || nodeHttp2;
  const connect = options.connect || options.connectImpl || options.http2Connect
    || (typeof http2 === "function" ? http2 : http2 && http2.connect);
  if (typeof connect !== "function") throw new ApnsError("apns_http2_invalid", "An HTTP/2 connect implementation is required.");
  const now = typeof options.now === "function" ? options.now : () => Math.floor(Date.now() / 1000);
  const requestIdFactory = typeof options.requestIdFactory === "function" ? options.requestIdFactory : () => crypto.randomUUID();
  let tokenProvider;
  if (typeof options.tokenProvider === "function") tokenProvider = options.tokenProvider;
  else if (typeof options.jwtProvider === "function") tokenProvider = options.jwtProvider;
  else if (typeof options.createJwt === "function") tokenProvider = options.createJwt;
  else if (options.jwt != null) tokenProvider = () => options.jwt;
  else tokenProvider = () => buildProviderJwt({
    teamId: options.teamId,
    keyId: options.keyId,
    privateKey: options.privateKey,
    nowSeconds: now(),
  });

  async function sendChatMessage(input = {}) {
    const token = validateDeviceToken(input.token || input.deviceToken);
    const environment = normalizeEnvironment(input.environment);
    const facts = validateNotificationFacts(input);
    const payload = buildChatNotificationPayload({ ...facts, locale: input.locale });
    const requestId = String(await requestIdFactory({ ...facts, token: undefined, environment }) || "");
    if (!APNS_UUID_RE.test(requestId)) throw new ApnsError("apns_request_id_invalid", "The APNs request ID must be a UUID.");
    const jwt = nonEmpty(await tokenProvider({ environment, topic }), "apns_credentials_invalid", "provider token");
    const authority = `https://${APNS_HOSTS[environment]}:443`;
    const headers = {
      ":method": "POST",
      ":path": `/3/device/${token}`,
      authorization: `bearer ${jwt}`,
      "apns-topic": topic,
      "apns-push-type": "alert",
      "apns-priority": "10",
      "apns-id": requestId,
      "apns-collapse-id": stableCollapseId(facts.messageId),
      "content-type": "application/json",
    };
    return issueHttp2Request({
      connect,
      authority,
      headers,
      body: JSON.stringify(payload),
      environment,
      requestId,
    });
  }

  return {
    sendChatMessage,
    send: sendChatMessage,
    sendNotification: sendChatMessage,
  };
}

module.exports = {
  APNS_HOSTS,
  APNS_TOKEN_RE,
  INVALID_TOKEN_REASONS,
  ApnsError,
  buildChatNotificationPayload,
  buildProviderJwt,
  createApnsClient,
  invalidTokenResponse,
  normalizeEnvironment,
  stableCollapseId,
  validateDeviceToken,
};
