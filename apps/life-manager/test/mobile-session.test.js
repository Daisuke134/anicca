"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  startCalendarSession,
  exchangeMobileSession,
  authenticateMobileRequest,
  refreshMobileSession,
  revokeMobileSession,
  validateSupabaseIdentity,
  buildComposioAuthorizationUrl,
} = require("../lib/mobile-session.js");

const NOW = Date.parse("2026-08-08T00:00:00.000Z");

function memorySessionDeps(overrides = {}) {
  const states = new Map();
  const sessions = new Map();
  let randomCounter = 0;
  const identities = new Map([["identity-token", { uid: "user-a", subject: "google-a", productLocale: "en" }]]);
  const deps = {
    now: () => NOW,
    randomBytes: (size) => Buffer.alloc(size, ++randomCounter),
    validateIdentity: async (token) => identities.get(token) || null,
    buildAuthorizationUrl: ({ state }) => `https://accounts.example.test/authorize?state=${state}`,
    store: {
      async createOAuthState(row) { states.set(row.stateHash, { ...row }); },
      async claimOAuthState(stateHash) {
        const row = states.get(stateHash);
        if (!row || row.usedAt || Date.parse(row.expiresAt) <= NOW) return null;
        row.usedAt = new Date(NOW).toISOString();
        return { ...row };
      },
      async createMobileSession(row) { sessions.set(row.sessionId, { ...row }); },
      async findAccessSession(hash) {
        return [...sessions.values()].find((row) => row.accessTokenHash === hash) || null;
      },
      async findRefreshSession(hash) {
        return [...sessions.values()].find((row) => row.refreshTokenHash === hash) || null;
      },
      async rotateRefreshSession(row, next) {
        if (row.rotatedAt || row.revokedAt) {
          for (const item of sessions.values()) if (item.familyId === row.familyId) item.revokedAt = new Date(NOW).toISOString();
          return { replay: true };
        }
        row.rotatedAt = new Date(NOW).toISOString();
        await this.createMobileSession(next);
        return { session: next };
      },
      async revokeMobileSession(scope) {
        const row = sessions.get(scope.sessionId);
        if (row) row.revokedAt = new Date(NOW).toISOString();
      },
      async readUser(scope) { return { uid: scope.uid, product_locale: "en", time_zone: "Asia/Tokyo" }; },
    },
    _states: states,
    _sessions: sessions,
  };
  return { ...deps, ...overrides, store: { ...deps.store, ...(overrides.store || {}) } };
}

test("calendar start creates one-use opaque state without accepting client uid", async () => {
  const deps = memorySessionDeps();
  const result = await startCalendarSession({ identityToken: "identity-token", redirectUri: "life-manager://oauth" }, deps);
  assert.match(result.state, /^state:v1:/u);
  assert.match(result.authorizationUrl, /^https:\/\//u);
  assert.equal(result.expiresAt, "2026-08-08T00:05:00.000Z");
  await assert.rejects(() => startCalendarSession({ uid: "user-b" }, deps), (error) => error.code === "client_uid_forbidden");
});

test("exchange rejects expired, replayed, and wrong-owner state before creating a session", async () => {
  const deps = memorySessionDeps();
  const started = await startCalendarSession({ identityToken: "identity-token" }, deps);
  const wrong = memorySessionDeps({ validateIdentity: async () => ({ uid: "user-b", subject: "google-b", productLocale: "en" }) });
  await assert.rejects(() => exchangeMobileSession({ state: started.state, code: "code" }, wrong), (error) => error.code === "oauth_state_invalid");

  const exchanged = await exchangeMobileSession({ state: started.state, code: "code", identityToken: "identity-token" }, deps);
  assert.equal(exchanged.tokenType, "Bearer");
  assert.match(exchanged.accessToken, /^access:v1:/u);
  await assert.rejects(() => exchangeMobileSession({ state: started.state, code: "code", identityToken: "identity-token" }, deps), (error) => error.code === "oauth_state_invalid");
  assert.equal(deps._sessions.size, 1);
});

test("bearer authentication derives tenant scope from stored session, never request uid", async () => {
  const deps = memorySessionDeps();
  const started = await startCalendarSession({ identityToken: "identity-token" }, deps);
  const session = await exchangeMobileSession({ state: started.state, code: "code", identityToken: "identity-token" }, deps);
  const scope = await authenticateMobileRequest({ headers: { authorization: `Bearer ${session.accessToken}`, "x-uid": "user-b" } }, deps);
  assert.deepEqual(scope, { uid: "user-a", sessionId: scope.sessionId, productLocale: "en", timezone: "Asia/Tokyo" });
  assert.notEqual(scope.sessionId, "");
  await assert.rejects(() => authenticateMobileRequest({ headers: {} }, deps), (error) => error.code === "unauthorized");
});

test("refresh rotates token and replay revokes the whole family; logout revokes current session", async () => {
  const deps = memorySessionDeps();
  const started = await startCalendarSession({ identityToken: "identity-token" }, deps);
  const first = await exchangeMobileSession({ state: started.state, code: "code", identityToken: "identity-token" }, deps);
  const second = await refreshMobileSession(first.refreshToken, deps);
  assert.notEqual(second.refreshToken, first.refreshToken);
  await assert.rejects(() => refreshMobileSession(first.refreshToken, deps), (error) => error.code === "refresh_replay");
  assert.equal([...deps._sessions.values()].every((row) => row.revokedAt), true);

  const freshDeps = memorySessionDeps();
  const s = await startCalendarSession({ identityToken: "identity-token" }, freshDeps);
  const token = await exchangeMobileSession({ state: s.state, code: "code", identityToken: "identity-token" }, freshDeps);
  const scope = await authenticateMobileRequest({ headers: { authorization: `Bearer ${token.accessToken}` } }, freshDeps);
  await revokeMobileSession(scope, freshDeps);
  await assert.rejects(() => authenticateMobileRequest({ headers: { authorization: `Bearer ${token.accessToken}` } }, freshDeps), (error) => error.code === "unauthorized");
});

test("default Supabase identity validation derives the Life Manager uid and never trusts a body uid", async () => {
  const requests = [];
  const result = await validateSupabaseIdentity("supabase-access", {
    supaUrl: "https://supabase.example.test",
    supaKey: "service-key",
    fetchImpl: async (url, init) => {
      requests.push([url, init]);
      if (url.endsWith("/auth/v1/user")) return { ok: true, async json() { return { id: "auth-user-1", email: "person@example.test" }; } };
      return { ok: true, async json() { return [{ product_locale: "ja" }]; } };
    },
  });
  assert.deepEqual(result, { uid: "lm_auth-user-1", subject: "auth-user-1", productLocale: "ja", email: "person@example.test" });
  assert.equal(requests[0][1].headers.Authorization, "Bearer supabase-access");
  assert.doesNotMatch(JSON.stringify(requests), /uid=eq\.auth-user-1/u);
});

test("Composio authorization adapter binds the server UID and one-use state to the app callback", async () => {
  let request;
  const redirect = await buildComposioAuthorizationUrl({ uid: "lm_user-a", state: "state:v1:one", redirectUri: "life-manager://oauth" }, {
    composioKey: "composio-key", composioAuthConfig: "gcal-config",
    fetchImpl: async (url, init) => { request = { url, init }; return { ok: true, async json() { return { redirect_url: "https://accounts.google.test/authorize" }; } }; },
  });
  assert.equal(redirect, "https://accounts.google.test/authorize");
  const body = JSON.parse(request.init.body);
  assert.deepEqual(body, { auth_config_id: "gcal-config", user_id: "lm_user-a", callback_url: "life-manager://oauth?state=state%3Av1%3Aone" });
});

test("Composio authorization rejects executable callback schemes", async () => {
  await assert.rejects(() => buildComposioAuthorizationUrl({
    uid: "lm_user-a", state: "state:v1:one", redirectUri: "javascript:alert(1)",
  }, { composioKey: "composio-key", composioAuthConfig: "gcal-config", fetchImpl: async () => {
    throw new Error("provider must not be called");
  } }), (error) => error.code === "oauth_input_invalid");
});

test("bearer authentication rejects a row whose stored hash does not match", async () => {
  await assert.rejects(() => authenticateMobileRequest({ headers: { authorization: "Bearer access" } }, {
    store: {
      async findAccessSession() {
        return {
          accessTokenHash: "f".repeat(64), uid: "user-a", sessionId: "session-a",
          accessExpiresAt: "2099-01-01T00:00:00.000Z", revokedAt: null,
        };
      },
      async readUser() { return { product_locale: "en" }; },
    },
  }), (error) => error.code === "unauthorized");
});
