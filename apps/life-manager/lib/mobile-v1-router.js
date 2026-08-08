"use strict";

const { createSupabaseMobileStore } = require("./mobile-store.js");
const { withMobileIdempotency } = require("./mobile-idempotency.js");
const { MobileError, parseBearer, requestId, sha256 } = require("./mobile-utils.js");
const session = require("./mobile-session.js");
const { readMobileBootstrap } = require("./mobile-bootstrap.js");
const { patchMobileProfile } = require("./mobile-profile.js");
const { analyzeNextEvent } = require("./mobile-analysis.js");
const { listMobileMessages } = require("./mobile-outbox.js");
const { replyMobileQuestion } = require("./mobile-question.js");
const { requestMobileCall } = require("./mobile-call.js");
const { upsertMobileDevice, removeMobileDevice } = require("./mobile-device.js");
const { deleteMobileAccount } = require("./mobile-account.js");

const PREFIX = "/api/mobile/v1";
const MAX_BODY_BYTES = 256 * 1024;

function writeJson(res, status, value, extra = {}) {
  if (!res.headersSent) res.writeHead(status, { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...extra });
  res.end(JSON.stringify(value));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    let size = 0;
    const onData = (chunk) => {
      size += Buffer.byteLength(chunk);
      if (size > MAX_BODY_BYTES) {
        reject(new MobileError("request_too_large", "The request body is too large.", 413));
        if (typeof req.destroy === "function") req.destroy();
        return;
      }
      body += chunk;
    };
    req.on("data", onData);
    req.on("end", () => resolve(body));
    req.on("error", reject);
  });
}

function parsePath(req) {
  let url;
  try { url = new URL(req.url || "/", "http://mobile.local"); } catch { throw new MobileError("path_invalid", "The request path is invalid.", 400); }
  if (url.pathname !== PREFIX && !url.pathname.startsWith(`${PREFIX}/`)) throw new MobileError("not_mobile_route", "Not a mobile route.", 404);
  return { path: url.pathname.slice(PREFIX.length) || "/", query: url.searchParams };
}

function requestBodyRequired(method, path) {
  if (method === "POST" || method === "PATCH" || method === "PUT") return true;
  return method === "DELETE" && path !== "/session";
}

function idempotencyKey(req) {
  const headers = req.headers || {};
  return headers["idempotency-key"] || headers["Idempotency-Key"] || "";
}

function mapIdempotencyStore(map) {
  return {
    async readIdempotency(scope, key) { return map.get(`${scope.uid}:${key}`) || null; },
    async claimIdempotency(scope, key, value) { const id = `${scope.uid}:${key}`; if (map.has(id)) return false; map.set(id, { ...value, status: "pending" }); return true; },
    async completeIdempotency(scope, key, value) { map.set(`${scope.uid}:${key}`, { ...map.get(`${scope.uid}:${key}`), ...value }); },
  };
}

function anonymousScope(req, key, body = {}) {
  const identity = body.identityToken || body.supabaseToken || body.googleIdentityToken || "";
  const client = identity || (req.headers && req.headers["user-agent"] || "");
  return { uid: `preauth:${sha256(`${key}:${client}`).slice(0, 40)}`, sessionId: null, productLocale: "en", timezone: "UTC" };
}

function makeRuntime(overrides = {}) {
  const store = overrides.store || (overrides.supaUrl || process.env.SUPABASE_URL
    ? createSupabaseMobileStore({ supaUrl: overrides.supaUrl || process.env.SUPABASE_URL, supaKey: overrides.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY, fetchImpl: overrides.fetchImpl })
    : null);
  const runtime = { ...overrides, store, ...(overrides.idempotencyStore ? { idempotency: mapIdempotencyStore(overrides.idempotencyStore) } : {}) };
  if (typeof runtime.analyzeNextEvent !== "function") runtime.analyzeNextEvent = analyzeNextEvent;
  if (typeof runtime.validateIdentity !== "function" && (runtime.supaUrl || process.env.SUPABASE_URL)) {
    runtime.validateIdentity = (token) => session.validateSupabaseIdentity(token, runtime);
  }
  return runtime;
}

function handler(runtime, name, fallback) {
  return typeof runtime[name] === "function" ? runtime[name] : fallback;
}

async function executeMutation(req, body, scope, runtime, operation) {
  const key = idempotencyKey(req);
  if (!key) throw new MobileError("idempotency_required", "Idempotency-Key is required for this mutation.");
  const idempotency = runtime.idempotency || runtime.store;
  if (!idempotency) throw new MobileError("idempotency_unavailable", "Mutation storage is unavailable.", 503, true);
  return withMobileIdempotency({ scope, key, payload: { method: req.method, path: parsePath(req).path, body }, operation }, { store: idempotency });
}

async function handleMobileV1Request(req, res, dependencies = {}) {
  const runtime = makeRuntime(dependencies);
  const id = requestId(req);
  try {
    const { path, query } = parsePath(req);
    const method = String(req.method || "GET").toUpperCase();
    let body = {};
    const optionalEmptyBody = method === "DELETE" && path === "/session";
    if (requestBodyRequired(method, path) || optionalEmptyBody) {
      const contentType = String((req.headers || {})["content-type"] || "");
      const raw = await readBody(req);
      if (raw || !optionalEmptyBody) {
        if (!/^application\/json(?:;|$)/iu.test(contentType)) throw new MobileError("json_required", "Mutations require an application/json body.", 415);
      }
      if (raw) {
        try { body = JSON.parse(raw); } catch { throw new MobileError("invalid_json", "The request body must be valid JSON."); }
      }
    }
    const isPublicSession = path === "/session/calendar/start" || path === "/session/exchange" || path === "/session/refresh";
    const needsAuth = !isPublicSession;
    const auth = handler(runtime, "authenticateMobileRequest", session.authenticateMobileRequest);
    const scope = needsAuth ? await auth(req, runtime) : anonymousScope(req, idempotencyKey(req) || path, body);
    const result = await dispatch({ req, method, path, query, body, scope, runtime, isPublicSession });
    writeJson(res, 200, result);
  } catch (error) {
    const mobileError = error instanceof MobileError ? error : new MobileError("mobile_unavailable", "The mobile request could not be completed.", 503, true);
    const errorBody = {
      code: mobileError.code || "mobile_unavailable", message: mobileError.message,
      retryable: Boolean(mobileError.retryable), requestId: id,
    };
    if (mobileError.details && typeof mobileError.details === "object") errorBody.details = mobileError.details;
    writeJson(res, mobileError.status || 500, {
      error: errorBody,
    }, mobileError.code === "method_not_allowed" ? { Allow: mobileError.allow || "GET" } : {});
  }
}

async function dispatch({ req, method, path, query, body, scope, runtime, isPublicSession }) {
  const mutation = async (operation) => executeMutation(req, body, scope, runtime, operation);
  if (method === "POST" && path === "/session/calendar/start") return mutation(() => handler(runtime, "startCalendarSession", session.startCalendarSession)(body, runtime));
  if (method === "POST" && path === "/session/exchange") return mutation(() => handler(runtime, "exchangeMobileSession", session.exchangeMobileSession)(body, runtime));
  if (method === "POST" && path === "/session/refresh") return mutation(() => handler(runtime, "refreshMobileSession", session.refreshMobileSession)(body.refreshToken || body.refresh_token, runtime));
  if (method === "DELETE" && path === "/session") return mutation(() => handler(runtime, "revokeMobileSession", session.revokeMobileSession)(scope, runtime));
  if (method === "GET" && path === "/bootstrap") return handler(runtime, "readMobileBootstrap", readMobileBootstrap)(scope, runtime);
  if (method === "PATCH" && path === "/profile") return mutation(() => handler(runtime, "patchMobileProfile", patchMobileProfile)(scope, body, runtime));
  if (method === "POST" && path === "/analysis") return mutation(() => handler(runtime, "analyzeNextEvent", analyzeNextEvent)(scope, body, runtime));
  if (method === "GET" && path === "/chat") return handler(runtime, "listMobileMessages", listMobileMessages)(scope, query.get("cursor"), runtime);

  const question = /^\/questions\/([^/]+)\/reply$/u.exec(path);
  if (method === "POST" && question) return mutation(() => handler(runtime, "replyMobileQuestion", replyMobileQuestion)(scope, { ...body, questionId: decodeURIComponent(question[1]) }, runtime));
  if (method === "POST" && path === "/calls/test") return mutation(() => handler(runtime, "requestMobileCall", requestMobileCall)(scope, { ...body, idempotencyKey: idempotencyKey(req) }, runtime));
  if (method === "PUT" && path === "/devices/apns") return mutation(() => handler(runtime, "upsertMobileDevice", upsertMobileDevice)(scope, body, runtime));
  if (method === "DELETE" && path === "/devices/apns") return mutation(() => handler(runtime, "removeMobileDevice", removeMobileDevice)(scope, body, runtime));
  if (method === "DELETE" && path === "/account") return mutation(() => handler(runtime, "deleteMobileAccount", deleteMobileAccount)(scope, { ...body, idempotencyKey: idempotencyKey(req) }, runtime));
  if (isPublicSession || path === "/session" || path === "/bootstrap" || path === "/profile" || path === "/analysis" || path === "/chat") throw new MobileError("method_not_allowed", "The method is not allowed.", 405, false);
  throw new MobileError("not_found", "The mobile route was not found.", 404);
}

module.exports = { PREFIX, MAX_BODY_BYTES, handleMobileV1Request, parsePath, readBody, buildComposioAuthorizationUrl: session.buildComposioAuthorizationUrl };
