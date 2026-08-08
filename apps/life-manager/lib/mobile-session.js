"use strict";

const {
  MobileError,
  nowMs,
  randomOpaque,
  sha256,
  parseBearer,
  normalizeLocale,
  safeTimeZone,
} = require("./mobile-utils.js");

const STATE_TTL_MS = 5 * 60 * 1000;
const ACCESS_TTL_MS = 15 * 60 * 1000;
const REFRESH_TTL_MS = 30 * 24 * 60 * 60 * 1000;

function storeOf(deps) {
  const store = deps && deps.store;
  if (!store) throw new MobileError("session_store_unavailable", "Mobile session storage is unavailable.", 503, true);
  return store;
}

function field(row, ...names) {
  for (const name of names) if (row && row[name] !== undefined) return row[name];
  return undefined;
}

async function identityFor(input, deps) {
  if (input && Object.hasOwn(input, "uid")) throw new MobileError("client_uid_forbidden", "The server derives the account from the validated identity.", 400);
  const token = input && (input.identityToken || input.supabaseToken || input.googleIdentityToken);
  if (!token) return null;
  const validator = deps.validateIdentity || deps.validateSupabaseIdentity || deps.supabaseUser;
  if (typeof validator !== "function") throw new MobileError("identity_unavailable", "The identity provider is unavailable.", 503, true);
  const identity = await validator(token);
  if (!identity || !identity.uid) throw new MobileError("identity_invalid", "The identity could not be validated.", 401);
  return identity;
}

function expiresAt(ms) {
  return new Date(ms).toISOString();
}

function tokenSet(uid, productLocale, deps, at = nowMs(deps)) {
  const accessToken = randomOpaque("access:v1:", deps);
  const refreshToken = randomOpaque("refresh:v1:", deps);
  const sessionId = randomOpaque("session:v1:", deps);
  const familyId = randomOpaque("family:v1:", deps);
  return {
    sessionId,
    familyId,
    uid,
    productLocale: normalizeLocale(productLocale || "en"),
    accessToken,
    refreshToken,
    accessTokenHash: sha256(accessToken),
    refreshTokenHash: sha256(refreshToken),
    accessExpiresAt: expiresAt(at + ACCESS_TTL_MS),
    refreshExpiresAt: expiresAt(at + REFRESH_TTL_MS),
    createdAt: expiresAt(at),
  };
}

function publicTokenSet(tokens) {
  return {
    accessToken: tokens.accessToken,
    refreshToken: tokens.refreshToken,
    tokenType: "Bearer",
    expiresAt: tokens.accessExpiresAt,
    refreshExpiresAt: tokens.refreshExpiresAt,
  };
}

async function startCalendarSession(input = {}, deps = {}) {
  const store = storeOf(deps);
  const identity = await identityFor(input, deps);
  const at = nowMs(deps);
  const state = randomOpaque("state:v1:", deps);
  const expires = expiresAt(at + STATE_TTL_MS);
  await store.createOAuthState({
    state,
    stateHash: sha256(state),
    uid: identity && identity.uid ? identity.uid : null,
    subject: identity && (identity.subject || identity.sub) ? (identity.subject || identity.sub) : null,
    provider: "google_calendar",
    redirectUri: input.redirectUri || null,
    expiresAt: expires,
  });
  const builder = deps.buildAuthorizationUrl || deps.calendarAuthorizationUrl;
  const authorizationUrl = typeof builder === "function"
    ? await builder({ state, redirectUri: input.redirectUri || null, provider: "google_calendar" })
    : `https://accounts.google.com/o/oauth2/v2/auth?response_type=code&state=${encodeURIComponent(state)}`;
  if (typeof authorizationUrl !== "string" || !/^https:\/\//u.test(authorizationUrl)) {
    throw new MobileError("oauth_unavailable", "Calendar connection is temporarily unavailable.", 503, true);
  }
  return { state, authorizationUrl, expiresAt: expires };
}

async function exchangeMobileSession(input = {}, deps = {}) {
  const store = storeOf(deps);
  if (Object.hasOwn(input, "uid")) throw new MobileError("client_uid_forbidden", "The server derives the account from the validated identity.");
  if (!input.state || !input.code) throw new MobileError("oauth_input_invalid", "The calendar callback is incomplete.");
  const identity = await identityFor(input, deps);
  const claimed = await store.claimOAuthState(sha256(input.state), {
    state: input.state,
    uid: identity && identity.uid ? identity.uid : null,
    subject: identity && (identity.subject || identity.sub) ? (identity.subject || identity.sub) : null,
  });
  if (!claimed) throw new MobileError("oauth_state_invalid", "The calendar connection has expired or was already used.", 400);

  const exchanged = typeof deps.exchangeCalendarCode === "function"
    ? await deps.exchangeCalendarCode({ code: input.code, state: claimed, identity })
    : {};
  const resolved = identity || exchanged.identity || exchanged.user || exchanged;
  const uid = resolved && (resolved.uid || resolved.lifeManagerUid || resolved.userId);
  if (!uid || Object.hasOwn(input, "uid")) throw new MobileError("identity_invalid", "The calendar identity could not be linked to a Life Manager account.", 401);
  if (claimed.uid && String(claimed.uid) !== String(uid)) throw new MobileError("oauth_owner_mismatch", "The callback belongs to a different account.", 403);
  if (typeof deps.verifyCalendarOwnership === "function" && !await deps.verifyCalendarOwnership({ uid, exchanged, identity: resolved })) {
    throw new MobileError("oauth_owner_mismatch", "The calendar connection belongs to a different account.", 403);
  }

  const productLocale = normalizeLocale(resolved.productLocale || resolved.product_locale || "en");
  const tokens = tokenSet(uid, productLocale, deps);
  await store.createMobileSession({
    ...tokens,
    providerConnection: exchanged.connection || exchanged.account || null,
  });
  return publicTokenSet(tokens);
}

async function authenticateMobileRequest(req, deps = {}) {
  const raw = parseBearer(req);
  if (!raw) throw new MobileError("unauthorized", "A mobile bearer session is required.", 401);
  const store = storeOf(deps);
  const row = await store.findAccessSession(sha256(raw));
  if (!row) throw new MobileError("unauthorized", "The mobile session is invalid.", 401);
  const at = nowMs(deps);
  const accessExpiry = Date.parse(field(row, "accessExpiresAt", "access_expires_at") || "");
  if (field(row, "revokedAt", "revoked_at")) throw new MobileError("unauthorized", "The mobile session is revoked.", 401);
  if (!Number.isFinite(accessExpiry) || accessExpiry <= at) throw new MobileError("unauthorized", "The mobile session has expired.", 401);
  const uid = field(row, "uid");
  const sessionId = field(row, "sessionId", "session_id");
  if (!uid || !sessionId) throw new MobileError("unauthorized", "The mobile session is incomplete.", 401);
  const user = typeof store.readUser === "function" ? await store.readUser({ uid, sessionId }) : null;
  const productLocale = normalizeLocale(field(row, "productLocale", "product_locale") || (user && (user.product_locale || user.productLocale)) || "en");
  const timezone = safeTimeZone((user && (user.time_zone || user.timezone || user.call_time_zone)) || "UTC");
  return { uid, sessionId, productLocale, timezone };
}

async function refreshMobileSession(refreshToken, deps = {}) {
  if (!refreshToken || typeof refreshToken !== "string") throw new MobileError("refresh_invalid", "A refresh token is required.", 401);
  const store = storeOf(deps);
  const row = await store.findRefreshSession(sha256(refreshToken));
  if (!row) throw new MobileError("refresh_invalid", "The refresh token is invalid.", 401);
  const at = nowMs(deps);
  const expiry = Date.parse(field(row, "refreshExpiresAt", "refresh_expires_at") || "");
  if (!Number.isFinite(expiry) || expiry <= at || field(row, "revokedAt", "revoked_at")) throw new MobileError("refresh_expired", "The refresh token has expired.", 401);
  const next = tokenSet(field(row, "uid"), field(row, "productLocale", "product_locale") || "en", deps, at);
  next.familyId = field(row, "familyId", "family_id") || next.familyId;
  const rotated = await store.rotateRefreshSession(row, next);
  if (!rotated || rotated.replay || rotated.revoked) throw new MobileError("refresh_replay", "The refresh token was already used; the session family was revoked.", 401);
  return publicTokenSet(next);
}

async function revokeMobileSession(scope, deps = {}) {
  if (!scope || !scope.uid || !scope.sessionId) throw new MobileError("unauthorized", "A mobile session is required.", 401);
  await storeOf(deps).revokeMobileSession(scope);
  return { revoked: true };
}

module.exports = {
  STATE_TTL_MS,
  ACCESS_TTL_MS,
  REFRESH_TTL_MS,
  startCalendarSession,
  exchangeMobileSession,
  authenticateMobileRequest,
  refreshMobileSession,
  revokeMobileSession,
};
