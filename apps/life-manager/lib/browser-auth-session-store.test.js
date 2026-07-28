"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  normalizeAuthOrigin,
  validateSessionContext,
  sealBrowserContext,
  openBrowserContext,
  readBrowserAuthSession,
  upsertBrowserAuthSession,
  invalidateBrowserAuthSession,
} = require("./browser-auth-session-store.js");

const KEY_HEX = "11".repeat(32);

test("browser auth contexts are encrypted, tenant-bound, and do not expose plaintext", () => {
  const one = { cookies: [{ name: "session", value: "tenant-one", domain: "auth.example", path: "/" }] };
  const two = { cookies: [{ name: "session", value: "tenant-two", domain: "auth.example", path: "/" }] };
  const sealedOne = sealBrowserContext({
    uid: "u-one", origin: "https://auth.example", principalKind: "user_provided", context: one,
  }, KEY_HEX);
  const sealedTwo = sealBrowserContext({
    uid: "u-two", origin: "https://auth.example", principalKind: "user_provided", context: two,
  }, KEY_HEX);

  assert.deepEqual(openBrowserContext({
    ...sealedOne, uid: "u-one", origin: "https://auth.example", principal_kind: "user_provided",
  }, KEY_HEX), one);
  assert.throws(() => openBrowserContext({
    ...sealedOne, uid: "u-two", origin: "https://auth.example", principal_kind: "user_provided",
  }, KEY_HEX), /browser auth context invalid/i);
  assert.doesNotMatch(JSON.stringify(sealedOne), /tenant-one/);
  assert.notEqual(sealedOne.ciphertext, sealedTwo.ciphertext);
  assert.equal(sealedOne.key_version, 1);
  assert.match(sealedOne.context_sha256, /^[a-f0-9]{64}$/);
});

test("browser auth inputs fail closed to HTTPS origins, principal kinds, bounded closed contexts, and 32-byte keys", () => {
  assert.equal(normalizeAuthOrigin("https://auth.example/path?ignored=1"), "https://auth.example");
  assert.throws(() => normalizeAuthOrigin("http://auth.example"), /browser auth origin invalid/i);
  assert.throws(() => normalizeAuthOrigin({ origin: "https://auth.example" }), /browser auth origin invalid/i);
  assert.deepEqual(validateSessionContext({ localStorage: { theme: "dark" } }), { localStorage: { theme: "dark" } });
  assert.throws(() => validateSessionContext({ tokens: { value: "no" } }), /browser auth context invalid/i);
  assert.throws(() => sealBrowserContext({
    uid: "u-one", origin: "https://auth.example", principalKind: "none", context: {},
  }, KEY_HEX), /browser auth context invalid/i);
  assert.throws(() => sealBrowserContext({
    uid: "u-one", origin: "https://auth.example", principalKind: "user_provided", context: {},
  }, "12"), /browser auth context invalid/i);
});

test("browser auth session persistence uses exact parameterized tenant rows and never sends plaintext to Postgres", async () => {
  const context = { cookies: [{ name: "session", value: "tenant-one", domain: "auth.example", path: "/" }] };
  const sealed = sealBrowserContext({
    uid: "u-one", origin: "https://auth.example", principalKind: "user_provided", context,
  }, KEY_HEX);
  const row = {
    uid: "u-one",
    origin: "https://auth.example",
    principal_kind: "user_provided",
    state: "active",
    ...sealed,
  };
  const reads = [];
  const read = await readBrowserAuthSession({
    uid: "u-one", origin: "https://auth.example", principalKind: "user_provided", keyHex: KEY_HEX,
  }, {
    query: async (sql, params) => {
      reads.push({ sql, params });
      return { rows: [row] };
    },
  });
  assert.deepEqual(read.context, context);
  assert.match(reads[0].sql, /WHERE uid = \$1 AND origin = \$2 AND principal_kind = \$3/i);
  assert.deepEqual(reads[0].params, ["u-one", "https://auth.example", "user_provided"]);

  const writes = [];
  const saved = await upsertBrowserAuthSession({
    uid: "u-one", origin: "https://auth.example", principalKind: "user_provided", context, keyHex: KEY_HEX,
  }, {
    query: async (sql, params) => {
      writes.push({ sql, params });
      return { rows: [row] };
    },
  });
  assert.equal(saved.state, "active");
  assert.deepEqual(saved.context, context);
  assert.match(writes[0].sql, /INSERT INTO public\.lm_browser_auth_sessions/i);
  assert.match(writes[0].sql, /ON CONFLICT \(uid, origin, principal_kind\) DO UPDATE/i);
  assert.doesNotMatch(JSON.stringify(writes[0].params), /tenant-one/);

  const invalidated = await invalidateBrowserAuthSession({
    uid: "u-one", origin: "https://auth.example", principalKind: "user_provided",
  }, {
    query: async (sql, params) => {
      writes.push({ sql, params });
      return { rows: [{ uid: "u-one" }] };
    },
  });
  assert.equal(invalidated, true);
  assert.match(writes[1].sql, /UPDATE public\.lm_browser_auth_sessions/i);
  assert.deepEqual(writes[1].params, ["u-one", "https://auth.example", "user_provided"]);
});

test("browser auth storage reads the design runtime key and ignores the retired environment name", async () => {
  const priorSessionKey = process.env.LM_BROWSER_SESSION_KEY;
  const priorRetiredKey = process.env.LM_BROWSER_AUTH_CONTEXT_KEY_HEX;
  const context = { sessionStorage: { current: "tenant-session" } };
  const sealed = sealBrowserContext({
    uid: "u-one", origin: "https://auth.example", principalKind: "user_provided", context,
  }, KEY_HEX);
  try {
    process.env.LM_BROWSER_SESSION_KEY = KEY_HEX;
    process.env.LM_BROWSER_AUTH_CONTEXT_KEY_HEX = "22".repeat(32);
    const record = await readBrowserAuthSession({
      uid: "u-one", origin: "https://auth.example", principalKind: "user_provided",
    }, {
      query: async () => ({ rows: [{
        uid: "u-one",
        origin: "https://auth.example",
        principal_kind: "user_provided",
        state: "active",
        ...sealed,
      }] }),
    });
    assert.deepEqual(record.context, context);
  } finally {
    if (priorSessionKey === undefined) delete process.env.LM_BROWSER_SESSION_KEY;
    else process.env.LM_BROWSER_SESSION_KEY = priorSessionKey;
    if (priorRetiredKey === undefined) delete process.env.LM_BROWSER_AUTH_CONTEXT_KEY_HEX;
    else process.env.LM_BROWSER_AUTH_CONTEXT_KEY_HEX = priorRetiredKey;
  }
});
