"use strict";

const {
  MobileError,
  nowMs,
  randomOpaque,
  sha256,
  timingEqual,
  parseBearer,
  normalizeLocale,
  safeTimeZone,
} = require("./mobile-utils.js");
const { makeComposioCalendar } = require("./transport/calendar-composio.js");

const STATE_TTL_MS = 5 * 60 * 1000;
const ACCESS_TTL_MS = 15 * 60 * 1000;
const REFRESH_TTL_MS = 30 * 24 * 60 * 60 * 1000;
const DEFAULT_MOBILE_OAUTH_CALLBACK_URL = "lifemanager://oauth/callback";
const COMPOSIO_API_BASE = "https://backend.composio.dev/api/v3.1";

function storeOf(deps) {
  const store = deps && deps.store;
  if (!store) throw new MobileError("session_store_unavailable", "Mobile session storage is unavailable.", 503, true);
  return store;
}

function opaque(prefix, deps = {}) {
  return typeof deps.randomOpaque === "function" ? deps.randomOpaque(prefix) : randomOpaque(prefix, deps);
}

async function validateSupabaseIdentity(token, deps = {}) {
  if (typeof token !== "string" || !token.trim()) throw new MobileError("identity_invalid", "The identity could not be validated.", 401);
  const base = String(deps.supaUrl || process.env.SUPABASE_URL || "").replace(/\/$/u, "");
  const key = String(deps.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_ANON_KEY || "");
  if (!base || !key) throw new MobileError("identity_unavailable", "The identity provider is unavailable.", 503, true);
  const fetchImpl = deps.fetchImpl || fetch;
  const headers = { apikey: key, Authorization: `Bearer ${token}` };
  const identityResponse = await fetchImpl(`${base}/auth/v1/user`, { headers });
  if (!identityResponse.ok) throw new MobileError("identity_invalid", "The identity could not be validated.", 401);
  const identity = await identityResponse.json().catch(() => null);
  if (!identity || typeof identity.id !== "string" || !identity.id) throw new MobileError("identity_invalid", "The identity could not be validated.", 401);
  const uid = `lm_${identity.id}`;
  const profileUrl = `${base}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}&select=product_locale&limit=1`;
  const profileResponse = await fetchImpl(profileUrl, { headers: { apikey: key, Authorization: `Bearer ${key}` } });
  if (!profileResponse.ok) throw new MobileError("identity_unavailable", "The Life Manager account is temporarily unavailable.", 503, true);
  const profiles = await profileResponse.json().catch(() => []);
  const profile = Array.isArray(profiles) ? profiles[0] : null;
  if (!profile) {
    const createResponse = await fetchImpl(`${base}/rest/v1/lm_users`, {
      method: "POST",
      headers: { apikey: key, Authorization: `Bearer ${key}`, "content-type": "application/json", Prefer: "resolution=merge-duplicates,return=minimal" },
      body: JSON.stringify({ uid, product_locale: "en", calls_enabled: false }),
    });
    if (!createResponse.ok && createResponse.status !== 409) throw new MobileError("identity_unavailable", "The Life Manager account is temporarily unavailable.", 503, true);
  }
  return { uid, subject: identity.id, productLocale: normalizeLocale((profile && profile.product_locale) || "en"), email: identity.email || null };
}

function callbackUrl(deps = {}) {
  const configured = deps.mobileOAuthCallbackUrl || process.env.LM_MOBILE_OAUTH_CALLBACK_URL || DEFAULT_MOBILE_OAUTH_CALLBACK_URL;
  try {
    const parsed = new URL(String(configured));
    if (!["https:", "life-manager:", "lifemanager:"].includes(parsed.protocol)) throw new Error("protocol");
    return parsed.toString().replace(/\?$/u, "");
  } catch {
    throw new MobileError("oauth_input_invalid", "The Calendar callback is not configured.", 503, true);
  }
}

function providerAccountId(body = {}) {
  return body.connected_account_id || body.connectedAccountId || body.data?.connected_account_id
    || body.data?.connectedAccountId || body.connectionData?.connected_account_id || body.connectionData?.connectedAccountId
    || body.connectionData?.val?.connected_account_id || body.connectionData?.val?.connectedAccountId || null;
}

async function buildComposioAuthorizationLink(input = {}, deps = {}) {
  if (!input.composioUserId || !input.state) throw new MobileError("oauth_input_invalid", "The Calendar connection is incomplete.");
  const apiKey = String(deps.composioKey || "");
  const authConfigId = String(deps.composioAuthConfig || deps.authConfigId || "");
  if (!apiKey || !authConfigId) throw new MobileError("oauth_unavailable", "Calendar connection is temporarily unavailable.", 503, true);
  let callbackUrl;
  try {
    const parsed = new URL(callbackUrlOf(input, deps));
    if (!["https:", "life-manager:", "lifemanager:"].includes(parsed.protocol)) throw new Error("callback_protocol");
    parsed.searchParams.set("state", input.state);
    callbackUrl = parsed.toString();
  } catch {
    throw new MobileError("oauth_input_invalid", "The Calendar callback is invalid.");
  }
  const fetchImpl = deps.fetchImpl || fetch;
  const response = await fetchImpl(`${COMPOSIO_API_BASE}/connected_accounts/link`, {
    method: "POST",
    headers: { "x-api-key": apiKey, "content-type": "application/json" },
    body: JSON.stringify({ auth_config_id: authConfigId, user_id: input.composioUserId, callback_url: callbackUrl }),
  });
  const body = await response.json().catch(() => ({}));
  const redirect = body.redirect_url || body.redirect_uri || body?.connectionData?.val?.redirectUrl;
  const connectedAccountId = providerAccountId(body);
  if (!response.ok || typeof redirect !== "string" || typeof connectedAccountId !== "string" || !connectedAccountId) throw new MobileError("oauth_unavailable", "Calendar connection is temporarily unavailable.", 503, true);
  try {
    const parsed = new URL(redirect);
    if (parsed.protocol !== "https:") throw new Error("provider_protocol");
  } catch {
    throw new MobileError("oauth_unavailable", "Calendar connection is temporarily unavailable.", 503, true);
  }
  return { authorizationUrl: redirect, connectedAccountId };
}

async function buildComposioAuthorizationUrl(input = {}, deps = {}) {
  const result = await buildComposioAuthorizationLink(input, deps);
  return result.authorizationUrl;
}

// Kept separate from buildComposioAuthorizationUrl so legacy panel/test callers can continue to
// consume a URL string while the mobile start route persists the exact connected account returned
// by Connect Link.
function callbackUrlOf(input, deps) {
  return input.callbackUrl || callbackUrl(deps);
}

function field(row, ...names) {
  for (const name of names) if (row && row[name] !== undefined) return row[name];
  return undefined;
}

async function identityFor(input, deps) {
  if (input && Object.hasOwn(input, "uid")) throw new MobileError("client_uid_forbidden", "The server derives the account from the validated identity.", 400);
  const token = input && (input.identityToken || input.supabaseToken || input.googleIdentityToken);
  if (!token) return null;
  const validator = deps.validateIdentity || deps.validateSupabaseIdentity || deps.supabaseUser
    || ((deps.supaUrl || process.env.SUPABASE_URL) ? (value) => validateSupabaseIdentity(value, deps) : null);
  if (typeof validator !== "function") throw new MobileError("identity_unavailable", "The identity provider is unavailable.", 503, true);
  const identity = await validator(token);
  if (!identity || !identity.uid) throw new MobileError("identity_invalid", "The identity could not be validated.", 401);
  return identity;
}

function expiresAt(ms) {
  return new Date(ms).toISOString();
}

function tokenSet(uid, productLocale, deps, at = nowMs(deps)) {
  const accessToken = opaque("access:v1:", deps);
  const refreshToken = opaque("refresh:v1:", deps);
  const sessionId = opaque("session:v1:", deps);
  const familyId = opaque("family:v1:", deps);
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
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    throw new MobileError("oauth_input_invalid", "Calendar connection input must be an object.");
  }
  const authorityFields = new Set([
    "uid", "identityToken", "supabaseToken", "googleIdentityToken", "email", "code",
    "redirectUri", "redirect_uri", "status", "connectedAccountId", "connected_account_id",
  ]);
  if (Object.keys(input || {}).some((key) => authorityFields.has(key))) {
    throw new MobileError("oauth_input_invalid", "Calendar connection input is server-owned.");
  }
  if (Object.keys(input || {}).length > 0) throw new MobileError("oauth_input_invalid", "Calendar connection input must be empty.");
  const at = nowMs(deps);
  const state = opaque("state:v1:", deps);
  const composioUserId = opaque("lm_", deps);
  const expires = expiresAt(at + STATE_TTL_MS);
  const authConfigId = String(deps.composioAuthConfig || deps.authConfigId || process.env.COMPOSIO_GCAL_AUTH_CONFIG || "");
  const stateRow = {
    state,
    stateHash: sha256(state),
    uid: null,
    subject: null,
    provider: "google_calendar",
    redirectUri: callbackUrl(deps),
    composioUserId,
    connectedAccountId: null,
    authConfigId,
    expiresAt: expires,
  };
  // The one-use state is durable before Connect Link is opened. If the provider request fails,
  // this orphaned state naturally expires and cannot be replayed or used by another tenant.
  await store.createOAuthState(stateRow);
  const builder = deps.buildAuthorizationLink || deps.buildAuthorizationUrl || deps.calendarAuthorizationUrl;
  const built = typeof builder === "function"
    ? await builder({ state, composioUserId, callbackUrl: callbackUrl(deps), provider: "google_calendar" }, deps)
    : await buildComposioAuthorizationLink({ state, composioUserId }, deps);
  const authorizationUrl = typeof built === "string" ? built : built && (built.authorizationUrl || built.redirectUrl);
  const connectedAccountId = typeof built === "object" && built ? (built.connectedAccountId || built.connected_account_id) : null;
  if (typeof authorizationUrl !== "string" || !/^https:\/\//u.test(authorizationUrl)) {
    throw new MobileError("oauth_unavailable", "Calendar connection is temporarily unavailable.", 503, true);
  }
  if (!connectedAccountId || typeof connectedAccountId !== "string") {
    throw new MobileError("oauth_unavailable", "Calendar connection is temporarily unavailable.", 503, true);
  }
  if (typeof store.updateOAuthState !== "function") throw new MobileError("oauth_state_failed", "Calendar connection is temporarily unavailable.", 503, true);
  await store.updateOAuthState(sha256(state), { connectedAccountId });
  return { state, authorizationUrl, expiresAt: expires };
}

function objectKeysExactly(input, expected) {
  const actual = Object.keys(input || {}).sort();
  const target = [...expected].sort();
  return actual.length === target.length && actual.every((value, index) => value === target[index]);
}

async function readComposioConnectedAccount(connectedAccountId, deps = {}) {
  const apiKey = String(deps.composioKey || process.env.COMPOSIO_API_KEY || "");
  if (!apiKey) throw new MobileError("oauth_provider_unavailable", "Calendar connection is temporarily unavailable.", 503, true);
  const fetchImpl = deps.fetchImpl || fetch;
  let response;
  try {
    response = await fetchImpl(`${COMPOSIO_API_BASE}/connected_accounts/${encodeURIComponent(connectedAccountId)}`, { headers: { "x-api-key": apiKey } });
  } catch {
    throw new MobileError("oauth_provider_unavailable", "Calendar connection is temporarily unavailable.", 503, true);
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new MobileError("oauth_provider_invalid", "The Calendar connection could not be verified.", 400);
  const rootAccount = body && typeof body.id === "string" && (body.user_id || body.status || body.toolkit || body.auth_config) ? body : null;
  const account = body && (body.connected_account || body.connectedAccount || body.data?.connected_account
    || body.data?.connectedAccount || rootAccount || body.data || body);
  if (!account || typeof account !== "object") return account;
  const { data: _credentialData, state: _credentialState, params: _credentialParams, ...safeAccount } = account;
  return safeAccount;
}

function accountToolkit(account) {
  return String(account && (account.toolkit_slug || account.toolkit?.slug || account.toolkit?.slug_name || account.toolkitSlug || "")).toLowerCase();
}

function accountAuthConfig(account) {
  return account && (account.auth_config_id || account.authConfigId || account.auth_config?.id || account.authConfig?.id || null);
}

async function readComposioPrimaryCalendar(composioUserId, connectedAccountId, deps = {}) {
  const calendar = makeComposioCalendar({
    apiKey: deps.composioKey || process.env.COMPOSIO_API_KEY,
    fetchImpl: deps.fetchImpl,
    recordCall: deps.recordCall,
    recordProviderCost: deps.recordProviderCost,
    authorizeProviderOperation: deps.authorizeProviderOperation,
  });
  try {
    return await calendar.readPrimaryCalendar(composioUserId, { connectedAccountId });
  } catch {
    throw new MobileError("oauth_identity_unavailable", "The Calendar identity could not be verified.", 400);
  }
}

function normalizeProviderSubject(primary) {
  const candidates = [
    primary && primary.providerSubject,
    primary && primary.provider_subject,
    primary && primary.email,
    primary && primary.id,
    primary && primary.calendarId,
    primary && primary.calendar_id,
    primary && primary.owner && (primary.owner.email || primary.owner.id),
    primary && primary.data && (primary.data.email || primary.data.id),
  ];
  const value = candidates.find((candidate) => typeof candidate === "string" && candidate.trim() && candidate.trim().toLowerCase() !== "primary");
  if (!value) throw new MobileError("oauth_identity_unavailable", "The Calendar identity could not be verified.", 400);
  const normalized = value.normalize("NFKC").trim().toLowerCase();
  if (!normalized || normalized.length > 512) throw new MobileError("oauth_identity_unavailable", "The Calendar identity could not be verified.", 400);
  return normalized;
}

async function exchangeMobileSession(input = {}, deps = {}) {
  const store = storeOf(deps);
  if (!objectKeysExactly(input, ["state", "status", "connectedAccountId"])) throw new MobileError("oauth_input_invalid", "The calendar callback is incomplete.");
  if (typeof input.state !== "string" || !input.state || typeof input.connectedAccountId !== "string" || !input.connectedAccountId) {
    throw new MobileError("oauth_input_invalid", "The calendar callback is incomplete.");
  }
  if (input.status !== "success") throw new MobileError("oauth_callback_failed", "The Calendar connection was not completed.");
  const claimed = await store.claimOAuthState(sha256(input.state));
  if (!claimed) throw new MobileError("oauth_state_invalid", "The calendar connection has expired or was already used.", 400);

  if (String(claimed.connectedAccountId || claimed.connected_account_id || "") !== input.connectedAccountId) {
    throw new MobileError("oauth_account_mismatch", "The Calendar connection could not be verified.", 400);
  }
  const composioUserId = claimed.composioUserId || claimed.composio_user_id;
  const authConfigId = claimed.authConfigId || claimed.auth_config_id;
  if (!composioUserId || !authConfigId) throw new MobileError("oauth_state_invalid", "The Calendar connection state is incomplete.", 400);
  const account = typeof deps.readConnectedAccount === "function"
    ? await deps.readConnectedAccount({ connectedAccountId: input.connectedAccountId, composioUserId, authConfigId, state: claimed })
    : await readComposioConnectedAccount(input.connectedAccountId, deps);
  const owner = account && (account.user_id || account.userId || account.connection?.user_id);
  if (!account || String(account.id || "") !== input.connectedAccountId || String(owner || "") !== String(composioUserId)
    || String(account.status || "").toUpperCase() !== "ACTIVE" || account.is_disabled === true || account.enabled === false
    || accountToolkit(account) !== "googlecalendar" || String(accountAuthConfig(account) || "") !== String(authConfigId)) {
    throw new MobileError("oauth_provider_invalid", "The Calendar connection could not be verified.", 400);
  }
  const primary = typeof deps.readPrimaryCalendar === "function"
    ? await deps.readPrimaryCalendar({ connectedAccountId: input.connectedAccountId, composioUserId, authConfigId, account })
    : await readComposioPrimaryCalendar(composioUserId, input.connectedAccountId, deps);
  const normalizedSubject = normalizeProviderSubject(primary);
  const providerSubjectHash = sha256(normalizedSubject);
  if (typeof store.linkCalendarIdentity !== "function") throw new MobileError("oauth_identity_unavailable", "The Calendar identity could not be linked.", 503, true);
  const linked = await store.linkCalendarIdentity({
    provider: "google_calendar", providerSubjectHash, uid: opaque("lm_", deps),
    composioUserId, connectedAccountId: input.connectedAccountId, authConfigId, productLocale: "en",
  });
  const uid = linked && (linked.uid || linked.lifeManagerUid || linked.userId);
  if (!uid) throw new MobileError("oauth_identity_unavailable", "The Calendar identity could not be linked.", 503, true);
  const productLocale = normalizeLocale(linked.productLocale || linked.product_locale || "en");
  const tokens = tokenSet(uid, productLocale, deps);
  await store.createMobileSession({
    ...tokens,
    providerConnection: { provider: "google_calendar", connectedAccountId: input.connectedAccountId },
  });
  return publicTokenSet(tokens);
}

async function authenticateMobileRequest(req, deps = {}) {
  const raw = parseBearer(req);
  if (!raw) throw new MobileError("unauthorized", "A mobile bearer session is required.", 401);
  const store = storeOf(deps);
  const tokenHash = sha256(raw);
  const row = await store.findAccessSession(tokenHash);
  if (!row) throw new MobileError("unauthorized", "The mobile session is invalid.", 401);
  const storedHash = field(row, "accessTokenHash", "access_token_hash");
  if (!storedHash || !timingEqual(storedHash, tokenHash)) throw new MobileError("unauthorized", "The mobile session is invalid.", 401);
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
  const scope = { uid, sessionId, productLocale, timezone };
  // Mobile provider cleanup must use the provider-owned provisional user and exact
  // account persisted during OAuth. Keep these facts server-derived and omit them
  // for legacy users so existing web/mobile scopes remain byte-for-byte compatible.
  const composioUserId = user && (user.calendar_composio_user_id || user.calendarComposioUserId);
  const connectedAccountId = user && (user.gmail_account_id || user.gmailAccountId);
  if (composioUserId) scope.calendarComposioUserId = composioUserId;
  if (connectedAccountId) scope.connectedAccountId = connectedAccountId;
  return scope;
}

async function refreshMobileSession(refreshToken, deps = {}) {
  if (!refreshToken || typeof refreshToken !== "string") throw new MobileError("refresh_invalid", "A refresh token is required.", 401);
  const store = storeOf(deps);
  const tokenHash = sha256(refreshToken);
  const row = await store.findRefreshSession(tokenHash);
  if (!row) throw new MobileError("refresh_invalid", "The refresh token is invalid.", 401);
  const storedHash = field(row, "refreshTokenHash", "refresh_token_hash");
  if (!storedHash || !timingEqual(storedHash, tokenHash)) throw new MobileError("refresh_invalid", "The refresh token is invalid.", 401);
  const at = nowMs(deps);
  const expiry = Date.parse(field(row, "refreshExpiresAt", "refresh_expires_at") || "");
  const rotatedAt = field(row, "rotatedAt", "rotated_at");
  const revokedAt = field(row, "revokedAt", "revoked_at");
  // A rotated row is a replay signal even when the first successful rotation already marked it
  // revoked. Let the database/memory store atomically revoke the complete family again; returning
  // refresh_expired here would leave a stolen old token looking like a harmless expiry.
  if (!rotatedAt && (!Number.isFinite(expiry) || expiry <= at || revokedAt)) {
    throw new MobileError("refresh_expired", "The refresh token has expired.", 401);
  }
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
  validateSupabaseIdentity,
  buildComposioAuthorizationUrl,
  buildComposioAuthorizationLink,
  readComposioConnectedAccount,
  readComposioPrimaryCalendar,
  normalizeProviderSubject,
  startCalendarSession,
  exchangeMobileSession,
  authenticateMobileRequest,
  refreshMobileSession,
  revokeMobileSession,
};
