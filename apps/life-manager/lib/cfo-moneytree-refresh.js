"use strict";

const { CFO_SECRET_REFS, readCfoSecret } = require("./cfo-secret-ref.js");

const ERROR = "cfo_moneytree_refresh_invalid:request";
const PRODUCTION = "https://jp-api.getmoneytree.com";
const STAGING = "https://jp-api-staging.getmoneytree.com";
const MAX_DAILY_REQUESTS = 4;
const SCOPES = Object.freeze(["guest_read", "accounts_read", "transactions_read", "request_refresh"]);

function fail() { throw new Error(ERROR); }
function plain(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    && Object.getPrototypeOf(value) === Object.prototype;
}
function iso(value) { return typeof value === "string" && value.length <= 64 && Number.isFinite(Date.parse(value)); }
function baseUrl(value) {
  const candidate = value == null ? PRODUCTION : String(value).replace(/\/$/, "");
  if (candidate !== PRODUCTION && candidate !== STAGING) fail();
  return candidate;
}
function accessToken(value) {
  if (typeof value !== "string" || value.length < 20 || value.length > 4096 || /[\r\n]/.test(value)) return null;
  return value;
}

/**
 * Request a Moneytree LINK provider refresh without ever fabricating a read.
 * The caller owns the durable quota counter and supplies a user-authorized
 * OAuth access token carrying request_refresh. A 202 only means the provider
 * queued an asynchronous job; the next read must still prove new data.
 */
async function requestMoneytreeRefresh(options = {}) {
  try {
    if (!plain(options)) fail();
    const observedAt = options.observedAt == null ? new Date().toISOString() : options.observedAt;
    if (!iso(observedAt)) fail();
    let token = accessToken(options.accessToken);
    if (!token && options.secretProvider && options.tenantId) {
      try { token = accessToken(await readCfoSecret(options.secretProvider, options.tenantId, options.accessTokenRef || CFO_SECRET_REFS.moneytree_link_refresh_token)); } catch { token = null; }
    }
    if (!token) return Object.freeze({ status: "unavailable", reason: "request_refresh_credentials_missing", observedAt });
    const requestCount = options.dailyRequestCount;
    if (requestCount === null) return Object.freeze({ status: "unavailable", reason: "refresh_quota_unknown", observedAt });
    if (!Number.isSafeInteger(requestCount) || requestCount < 0 || requestCount > MAX_DAILY_REQUESTS) fail();
    if (requestCount >= MAX_DAILY_REQUESTS) return Object.freeze({ status: "rate_limited", reason: "daily_quota_exhausted", observedAt, dailyLimit: MAX_DAILY_REQUESTS });
    const fetchImpl = options.fetchImpl || globalThis.fetch;
    if (typeof fetchImpl !== "function") fail();
    const endpoint = `${baseUrl(options.baseUrl)}/link/profile/refresh.json`;
    const response = await fetchImpl(endpoint, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, Accept: "application/json" },
    });
    const status = Number(response && response.status) || 0;
    if (status === 202) return Object.freeze({ status: "accepted", reason: "provider_refresh_queued", observedAt, httpStatus: 202, dailyLimit: MAX_DAILY_REQUESTS, nextReadAfterSeconds: 300 });
    if (status === 401) return Object.freeze({ status: "reauthorization_required", reason: "access_token_invalid", observedAt, httpStatus: 401 });
    if (status === 403) return Object.freeze({ status: "reauthorization_required", reason: "request_refresh_scope_missing", observedAt, httpStatus: 403 });
    if (status === 429) return Object.freeze({ status: "rate_limited", reason: "provider_or_daily_rate_limit", observedAt, httpStatus: 429, dailyLimit: MAX_DAILY_REQUESTS });
    return Object.freeze({ status: "failed", reason: "provider_refresh_rejected", observedAt, httpStatus: status || null });
  } catch (error) {
    if (error && error.message === ERROR) throw error;
    return Object.freeze({ status: "failed", reason: "provider_refresh_transport", observedAt: new Date().toISOString() });
  }
}

function buildMoneytreeAuthorizationUrl({ clientId, redirectUri, state, authorizationBaseUrl = "https://myaccount.getmoneytree.com/oauth/authorize" } = {}) {
  if (typeof clientId !== "string" || clientId.length < 1 || clientId.length > 512
    || typeof redirectUri !== "string" || redirectUri.length < 1 || redirectUri.length > 2048
    || typeof state !== "string" || state.length < 16 || state.length > 512) fail();
  const url = new URL(authorizationBaseUrl);
  url.searchParams.set("client_id", clientId);
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("scope", SCOPES.join(" "));
  url.searchParams.set("state", state);
  url.searchParams.set("locale", "ja-JP");
  return url.toString();
}

module.exports = { PRODUCTION, STAGING, MAX_DAILY_REQUESTS, SCOPES, requestMoneytreeRefresh, buildMoneytreeAuthorizationUrl };
