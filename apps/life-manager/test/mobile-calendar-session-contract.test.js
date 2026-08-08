"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  startCalendarSession,
  exchangeMobileSession,
  readComposioConnectedAccount,
  readComposioPrimaryCalendar,
} = require("../lib/mobile-session.js");
const { createMemoryMobileStore, createSupabaseMobileStore } = require("../lib/mobile-store.js");
const { makeComposioCalendar } = require("../lib/transport/calendar-composio.js");

const NOW = Date.parse("2026-08-09T00:00:00.000Z");

function deps(overrides = {}) {
  const store = createMemoryMobileStore({ now: () => NOW, ...(overrides.storeOptions || {}) });
  let sequence = 0;
  return {
    store,
    now: () => NOW,
    randomBytes: () => Buffer.alloc(18, ++sequence),
    composioKey: "composio-test-key",
    composioAuthConfig: "ac_gcal_test",
    mobileOAuthCallbackUrl: "lifemanager://oauth/callback",
    buildAuthorizationLink: async (input) => {
      assert.match(input.composioUserId, /^lm_[A-Za-z0-9_-]+$/u);
      assert.equal(input.callbackUrl, "lifemanager://oauth/callback");
      assert.equal(store._states.size, 1, "one-use state must be durable before Connect Link opens");
      return { authorizationUrl: `https://connect.composio.test/${encodeURIComponent(input.state)}`, connectedAccountId: "ca_google_123" };
    },
    readConnectedAccount: async ({ connectedAccountId }) => ({
      id: connectedAccountId,
      user_id: "lm_provisional",
      status: "ACTIVE",
      toolkit: { slug: "googlecalendar" },
      auth_config: { id: "ac_gcal_test" },
    }),
    readPrimaryCalendar: async () => ({ id: "person@example.test", summary: "Primary" }),
    ...overrides,
  };
}

async function start(depsOverride = {}) {
  const runtime = deps(depsOverride);
  const result = await startCalendarSession({}, runtime);
  return { runtime, result };
}

test("calendar start is server-owned: empty body creates provisional owner, callback, and exact state facts", async () => {
  for (const invalid of [null, [], "{}"]) {
    await assert.rejects(() => startCalendarSession(invalid, deps()), (error) => error.code === "oauth_input_invalid");
  }
  const { runtime, result } = await start();
  assert.match(result.state, /^state:v1:/u);
  assert.match(result.authorizationUrl, /^https:\/\//u);
  assert.equal(result.expiresAt, "2026-08-09T00:05:00.000Z");
  const state = [...runtime.store._states.values()][0];
  assert.match(state.composioUserId, /^lm_[A-Za-z0-9_-]+$/u);
  assert.equal(state.connectedAccountId, "ca_google_123");
  assert.equal(state.authConfigId, "ac_gcal_test");
  assert.equal(state.uid, null);
  for (const key of ["uid", "redirectUri", "identityToken", "supabaseToken", "googleIdentityToken", "email", "code"]) {
    await assert.rejects(() => startCalendarSession({ [key]: "attacker-controlled" }, runtime), (error) => error.code === "oauth_input_invalid");
  }
});

test("exchange accepts only the Composio callback facts and issues a session after provider read-back and identity mapping", async () => {
  const { runtime, result } = await start();
  const connectedAccountCalls = [];
  const calendarCalls = [];
  runtime.readConnectedAccount = async (input) => {
    connectedAccountCalls.push(input);
    return {
      id: "ca_google_123", user_id: [...runtime.store._states.values()][0].composioUserId,
      status: "ACTIVE", toolkit: { slug: "googlecalendar" }, auth_config: { id: "ac_gcal_test" },
    };
  };
  runtime.readPrimaryCalendar = async (input) => {
    calendarCalls.push(input);
    return { id: "Person@Example.test", summary: "Primary" };
  };
  const exchanged = await exchangeMobileSession({ state: result.state, status: "success", connectedAccountId: "ca_google_123" }, runtime);
  assert.equal(exchanged.tokenType, "Bearer");
  assert.equal(runtime.store._sessions.size, 1);
  assert.equal(connectedAccountCalls[0].connectedAccountId, "ca_google_123");
  assert.equal(calendarCalls[0].connectedAccountId, "ca_google_123");
  const uid = [...runtime.store._sessions.values()][0].uid;
  assert.match(uid, /^lm_[A-Za-z0-9_-]+$/u);
  assert.equal([...runtime.store._users.values()][0].calendar_status, "connected");
  assert.equal([...runtime.store._users.values()][0].gmail_account_id, "ca_google_123");
  assert.equal([...runtime.store._calendarConnections.values()][0].providerSubjectHash.length, 64);
  assert.doesNotMatch(JSON.stringify([...runtime.store._calendarConnections.values()]), /Person@Example/iu);
});

test("exchange rejects failed status, code, uid, extra facts, mismatched account, wrong owner/toolkit/config, and missing primary identity without a session", async () => {
  const cases = [
    { name: "failed status", input: { status: "failed", connectedAccountId: "ca_google_123" }, code: "oauth_callback_failed" },
    { name: "code", input: { status: "success", connectedAccountId: "ca_google_123", code: "provider-code" }, code: "oauth_input_invalid" },
    { name: "uid", input: { status: "success", connectedAccountId: "ca_google_123", uid: "lm_attacker" }, code: "oauth_input_invalid" },
    { name: "extra", input: { status: "success", connectedAccountId: "ca_google_123", email: "attacker@example.test" }, code: "oauth_input_invalid" },
  ];
  for (const item of cases) {
    const { runtime, result } = await start();
    await assert.rejects(() => exchangeMobileSession({ state: result.state, ...item.input }, runtime), (error) => error.code === item.code, item.name);
    assert.equal(runtime.store._sessions.size, 0, item.name);
  }
  {
    const { runtime, result } = await start();
    await assert.rejects(() => exchangeMobileSession({ state: result.state, status: "success", connectedAccountId: "ca_other" }, runtime), (error) => error.code === "oauth_account_mismatch");
    assert.equal(runtime.store._sessions.size, 0);
  }

  for (const variant of [
    { name: "mismatched account read-back", mutate: () => {}, code: "oauth_provider_invalid" },
    { name: "wrong owner", mutate: (runtime) => { runtime.readConnectedAccount = async () => ({ id: "ca_google_123", user_id: "lm_other", status: "ACTIVE", toolkit: { slug: "googlecalendar" }, auth_config: { id: "ac_gcal_test" } }); }, code: "oauth_provider_invalid" },
    { name: "wrong toolkit", mutate: (runtime) => { runtime.readConnectedAccount = async () => ({ id: "ca_google_123", user_id: [...runtime.store._states.values()][0].composioUserId, status: "ACTIVE", toolkit: { slug: "gmail" }, auth_config: { id: "ac_gcal_test" } }); }, code: "oauth_provider_invalid" },
    { name: "wrong auth config", mutate: (runtime) => { runtime.readConnectedAccount = async () => ({ id: "ca_google_123", user_id: [...runtime.store._states.values()][0].composioUserId, status: "ACTIVE", toolkit: { slug: "googlecalendar" }, auth_config: { id: "ac_other" } }); }, code: "oauth_provider_invalid" },
    { name: "missing primary", mutate: (runtime) => {
      runtime.readConnectedAccount = async () => ({ id: "ca_google_123", user_id: [...runtime.store._states.values()][0].composioUserId, status: "ACTIVE", toolkit: { slug: "googlecalendar" }, auth_config: { id: "ac_gcal_test" } });
      runtime.readPrimaryCalendar = async () => ({});
    }, code: "oauth_identity_unavailable" },
  ]) {
    const { runtime, result } = await start();
    if (variant.name === "mismatched account read-back") {
      runtime.readConnectedAccount = async () => ({ id: "ca_other", user_id: [...runtime.store._states.values()][0].composioUserId, status: "ACTIVE", toolkit: { slug: "googlecalendar" }, auth_config: { id: "ac_gcal_test" } });
    } else variant.mutate(runtime);
    await assert.rejects(() => exchangeMobileSession({ state: result.state, status: "success", connectedAccountId: "ca_google_123" }, runtime), (error) => error.code === variant.code, variant.name);
    assert.equal(runtime.store._sessions.size, 0, variant.name);
  }
});

test("exchange claims state once and does not create a second session on replay", async () => {
  const { runtime, result } = await start();
  runtime.readConnectedAccount = async () => ({ id: "ca_google_123", user_id: [...runtime.store._states.values()][0].composioUserId, status: "ACTIVE", toolkit: { slug: "googlecalendar" }, auth_config: { id: "ac_gcal_test" } });
  runtime.readPrimaryCalendar = async () => ({ id: "person@example.test" });
  await exchangeMobileSession({ state: result.state, status: "success", connectedAccountId: "ca_google_123" }, runtime);
  await assert.rejects(() => exchangeMobileSession({ state: result.state, status: "success", connectedAccountId: "ca_google_123" }, runtime), (error) => error.code === "oauth_state_invalid");
  assert.equal(runtime.store._sessions.size, 1);
});

test("Composio calendar transport includes exact connected account only when one is supplied", async () => {
  const requests = [];
  const calendar = makeComposioCalendar({
    apiKey: "key",
    recordCall: async () => false,
    fetchImpl: async (url, init) => {
      requests.push({ url, init, body: JSON.parse(init.body) });
      return { ok: true, async json() { return { successful: true, data: { items: [{ id: "person@example.test" }] } }; } };
    },
  });
  await calendar.readPrimaryCalendar("lm_stable", { connectedAccountId: "ca_exact" });
  assert.equal(requests[0].body.connected_account_id, "ca_exact");
  assert.equal(requests[0].body.user_id, "lm_stable");
  assert.deepEqual(requests[0].body.arguments, { calendarId: "primary" });
});

test("default Composio read-back and primary identity paths use v3.1 plus the exact account", async () => {
  const requests = [];
  const fetchImpl = async (url, init = {}) => {
    requests.push({ url, init, body: init.body ? JSON.parse(init.body) : null });
    if (String(url).includes("/connected_accounts/ca_exact")) {
      return { ok: true, async json() { return { id: "ca_exact", user_id: "lm_provisional", status: "ACTIVE", toolkit: { slug: "googlecalendar" }, auth_config: { id: "ac_gcal" } }; } };
    }
    return { ok: true, async json() { return { successful: true, data: { response_data: { items: [{ id: "person@example.test" }] } } }; } };
  };
  const account = await readComposioConnectedAccount("ca_exact", { composioKey: "key", fetchImpl });
  const primary = await readComposioPrimaryCalendar("lm_provisional", "ca_exact", {
    composioKey: "key", fetchImpl, recordCall: async () => false, authorizeProviderOperation: async () => ({ allowed: true }),
  });
  assert.equal(account.id, "ca_exact");
  assert.equal(primary.id, "person@example.test");
  const execute = requests.find((request) => String(request.url).includes("/tools/execute/"));
  assert.equal(execute.body.connected_account_id, "ca_exact");
  assert.equal(execute.body.user_id, "lm_provisional");
});

test("Supabase mobile store sends server-owned OAuth facts through the v2 claim and atomic identity RPC", async () => {
  const calls = [];
  const store = createSupabaseMobileStore({
    supaUrl: "https://db.example.test", supaKey: "service-key",
    fetchImpl: async (url, init = {}) => {
      calls.push({ url, init });
      if (url.includes("/rpc/claim_lm_mobile_oauth_state_v2")) return { ok: true, async json() { return [{ state_hash: "h", composio_user_id: "lm_provisional", connected_account_id: "ca_1", auth_config_id: "ac_1" }]; } };
      if (url.includes("/rpc/link_lm_mobile_calendar_identity")) return { ok: true, async json() { return [{ uid: "lm_stable", product_locale: "en" }]; } };
      return { ok: true, async json() { return []; } };
    },
  });
  await store.createOAuthState({ stateHash: "h", provider: "google_calendar", composioUserId: "lm_provisional", connectedAccountId: "ca_1", authConfigId: "ac_1", expiresAt: "2026-08-09T00:05:00.000Z" });
  const claimed = await store.claimOAuthState("h");
  assert.equal(claimed.composioUserId, "lm_provisional");
  const linked = await store.linkCalendarIdentity({ provider: "google_calendar", providerSubjectHash: "a".repeat(64), uid: "lm_new", composioUserId: "lm_provisional", connectedAccountId: "ca_1", authConfigId: "ac_1", productLocale: "en" });
  assert.equal(linked.uid, "lm_stable");
  const statePayload = JSON.parse(calls.find((call) => call.url.includes("lm_mobile_oauth_states")).init.body);
  assert.equal(statePayload.composio_user_id, "lm_provisional");
  const linkPayload = JSON.parse(calls.find((call) => call.url.includes("link_lm_mobile_calendar_identity")).init.body);
  assert.equal(linkPayload.p_provider_subject_hash, "a".repeat(64));
  assert.equal(Object.hasOwn(linkPayload, "p_provider_subject"), false);
});
