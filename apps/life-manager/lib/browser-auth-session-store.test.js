"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { createCipheriv, createHash } = require("node:crypto");
const canonicalize = require("canonicalize");
const {
  normalizeAuthOrigin,
  validateSessionContext,
  scopeSessionContextToOrigin,
  sealBrowserContext,
  openBrowserContext,
  readBrowserAuthSession,
  upsertBrowserAuthSession,
  invalidateBrowserAuthSession,
} = require("./browser-auth-session-store.js");

const KEY_HEX = "11".repeat(32);

function sealLegacyUnscopedContext({ uid, origin, principalKind, context }) {
  const plaintext = canonicalize(context);
  const iv = Buffer.alloc(12, 7);
  const cipher = createCipheriv("aes-256-gcm", Buffer.from(KEY_HEX, "hex"), iv);
  cipher.setAAD(Buffer.from(`${uid}\n${origin}\n${principalKind}\n1`, "utf8"));
  const ciphertext = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
  return {
    uid,
    origin,
    principal_kind: principalKind,
    ciphertext: ciphertext.toString("base64url"),
    iv: iv.toString("base64url"),
    auth_tag: cipher.getAuthTag().toString("base64url"),
    context_sha256: createHash("sha256").update(plaintext, "utf8").digest("hex"),
    key_version: 1,
  };
}

test("browser auth contexts are strictly scoped to the exact public HTTPS origin", () => {
  const foreignCookies = [
    ["sibling", "evilluma.com"],
    ["public-tld", ".com"],
    ["public-multilabel", ".co.uk"],
    ["localhost", "localhost"],
    ["private-ip", "127.0.0.1"],
    ["private-name", ".internal"],
    ["other-site", "example.org"],
    ["suffix-trick", "luma.com.evil"],
    ["prefix-trick", "evilluma.com"],
    ["child-domain", "auth.app.luma.com"],
    ["other-app", "other.luma.com"],
    ["foreign-root", "google.com"],
  ].map(([name, domain]) => ({
    name,
    value: `drop-${name}`,
    domain,
    path: "/",
  }));
  const scoped = scopeSessionContextToOrigin({
    cookies: [
      { name: "exact", value: "keep-exact", domain: "app.luma.com", path: "/", hostOnly: true },
      { name: "parent-unproven", value: "drop-parent-unproven", domain: ".luma.com", path: "/account" },
      { name: "parent-proven", value: "keep-parent-proven", domain: ".luma.com", path: "/account", hostOnly: false },
      { name: "partition-foreign", value: "drop-partition-foreign", domain: "app.luma.com", path: "/", partitionKey: { topLevelSite: "https://other.example" } },
      { name: "partition-same-site", value: "drop-partition-same-site", domain: "app.luma.com", path: "/", partitionKey: { topLevelSite: "https://app.luma.com" } },
      ...foreignCookies,
    ],
    localStorage: {
      "https://app.luma.com": { marker: "keep-local" },
      "https://evilluma.com": { marker: "drop-sibling-local" },
      "http://app.luma.com": { marker: "drop-http-local" },
    },
    sessionStorage: {
      "https://app.luma.com": { marker: "keep-session" },
      "https://luma.com": { marker: "drop-parent-session" },
    },
    indexedDB: {
      "https://app.luma.com": { databases: [{ name: "keep-db" }] },
      "https://evil.example": { databases: [{ name: "drop-foreign-db" }] },
    },
  }, "https://app.luma.com/path");

  assert.deepEqual(scoped.cookies.map(({ name, domain, path }) => ({ name, domain, path })), [
    { name: "exact", domain: "app.luma.com", path: "/" },
    { name: "parent-proven", domain: ".luma.com", path: "/account" },
  ]);
  assert.deepEqual(scoped.localStorage, {
    "https://app.luma.com": { marker: "keep-local" },
  });
  assert.deepEqual(scoped.sessionStorage, {
    "https://app.luma.com": { marker: "keep-session" },
  });
  assert.deepEqual(scoped.indexedDB, {
    "https://app.luma.com": { databases: [{ name: "keep-db" }] },
  });
  assert.doesNotMatch(JSON.stringify(scoped), /drop-/);
  assert.throws(() => scopeSessionContextToOrigin({
    cookies: [{ name: "foreign", value: "drop-only", domain: "evilluma.com", path: "/" }],
  }, "https://luma.com"), /browser auth context invalid/i);
});

test("browser auth rejects unsafe exact hosts, partitioned cookies, and ambiguous dotted domains", () => {
  for (const origin of [
    "https://github.io",
    "https://co.uk",
    "https://localhost",
    "https://127.0.0.1",
    "https://[::1]",
  ]) {
    const domain = new URL(origin).hostname;
    assert.throws(() => scopeSessionContextToOrigin({
      cookies: [{ name: "unsafe", value: "drop-unsafe", domain, path: "/" }],
    }, origin), /browser auth context invalid/i);
  }

  const exact = scopeSessionContextToOrigin({
    cookies: [
      { name: "normal", value: "keep-normal", domain: "login.luma.com", path: "/" },
      { name: "partitioned", value: "drop-partition", domain: "login.luma.com", path: "/", partitionKey: { topLevelSite: "https://login.luma.com" } },
    ],
  }, "https://login.luma.com");
  assert.deepEqual(exact.cookies.map(({ name }) => name), ["normal"]);
  assert.doesNotMatch(JSON.stringify(exact), /drop-partition/);

  assert.throws(() => normalizeAuthOrigin("https://luma.com./account"), /browser auth origin invalid/i);
  assert.throws(() => scopeSessionContextToOrigin({
    cookies: [{ name: "dotted", value: "drop-dotted", domain: "luma.com.", path: "/" }],
  }, "https://luma.com"), /browser auth context invalid/i);
});

test("browser auth canonicalizes equivalent IDN U-label and punycode hostnames", () => {
  const scoped = scopeSessionContextToOrigin({
    cookies: [{ name: "idn", value: "keep-idn", domain: "bücher.de", path: "/" }],
    localStorage: {
      "https://xn--bcher-kva.de": { marker: "keep-idn-storage" },
      "https://bücher.de": { marker: "drop-noncanonical-key" },
    },
  }, "https://bücher.de/account");

  assert.deepEqual(scoped.cookies, [
    { name: "idn", value: "keep-idn", domain: "bücher.de", path: "/" },
  ]);
  assert.deepEqual(scoped.localStorage, {
    "https://xn--bcher-kva.de": { marker: "keep-idn-storage" },
  });
});

test("browser auth defensive open removes cross-origin data from contaminated legacy rows", () => {
  const legacy = sealLegacyUnscopedContext({
    uid: "u-one",
    origin: "https://luma.com",
    principalKind: "user_provided",
    context: {
      cookies: [
        { name: "allowed", value: "keep-cookie", domain: ".luma.com", path: "/" },
        { name: "foreign", value: "drop-cookie", domain: ".google.com", path: "/" },
      ],
      localStorage: {
        "https://luma.com": { marker: "keep-storage" },
        "https://accounts.google.com": { marker: "drop-storage" },
      },
    },
  });

  const opened = openBrowserContext(legacy, KEY_HEX);
  assert.deepEqual(opened, {
    cookies: [{ name: "allowed", value: "keep-cookie", domain: ".luma.com", path: "/" }],
    localStorage: { "https://luma.com": { marker: "keep-storage" } },
  });
  assert.doesNotMatch(JSON.stringify(opened), /drop-cookie|drop-storage/);
});

test("browser auth contexts are encrypted, tenant-bound, and do not expose plaintext", () => {
  const one = { cookies: [{ name: "session", value: "tenant-one", domain: "auth.fixture.dev", path: "/" }] };
  const two = { cookies: [{ name: "session", value: "tenant-two", domain: "auth.fixture.dev", path: "/" }] };
  const sealedOne = sealBrowserContext({
    uid: "u-one", origin: "https://auth.fixture.dev", principalKind: "user_provided", context: one,
  }, KEY_HEX);
  const sealedTwo = sealBrowserContext({
    uid: "u-two", origin: "https://auth.fixture.dev", principalKind: "user_provided", context: two,
  }, KEY_HEX);

  assert.deepEqual(openBrowserContext({
    ...sealedOne, uid: "u-one", origin: "https://auth.fixture.dev", principal_kind: "user_provided",
  }, KEY_HEX), one);
  assert.throws(() => openBrowserContext({
    ...sealedOne, uid: "u-two", origin: "https://auth.fixture.dev", principal_kind: "user_provided",
  }, KEY_HEX), /browser auth context invalid/i);
  assert.doesNotMatch(JSON.stringify(sealedOne), /tenant-one/);
  assert.notEqual(sealedOne.ciphertext, sealedTwo.ciphertext);
  assert.equal(sealedOne.key_version, 1);
  assert.match(sealedOne.context_sha256, /^[a-f0-9]{64}$/);
});

test("browser auth inputs fail closed to HTTPS origins, principal kinds, bounded closed contexts, and 32-byte keys", () => {
  assert.equal(normalizeAuthOrigin("https://auth.fixture.dev/path?ignored=1"), "https://auth.fixture.dev");
  assert.throws(() => normalizeAuthOrigin("http://auth.fixture.dev"), /browser auth origin invalid/i);
  assert.throws(() => normalizeAuthOrigin({ origin: "https://auth.fixture.dev" }), /browser auth origin invalid/i);
  assert.deepEqual(validateSessionContext({ localStorage: { theme: "dark" } }), { localStorage: { theme: "dark" } });
  assert.throws(() => validateSessionContext({ tokens: { value: "no" } }), /browser auth context invalid/i);
  assert.throws(() => sealBrowserContext({
    uid: "u-one", origin: "https://auth.fixture.dev", principalKind: "none", context: {},
  }, KEY_HEX), /browser auth context invalid/i);
  assert.throws(() => sealBrowserContext({
    uid: "u-one", origin: "https://auth.fixture.dev", principalKind: "user_provided", context: {},
  }, "12"), /browser auth context invalid/i);
});

test("browser auth session persistence uses exact parameterized tenant rows and never sends plaintext to Postgres", async () => {
  const context = {
    cookies: [
      { name: "session", value: "tenant-one", domain: "auth.fixture.dev", path: "/" },
      { name: "foreign", value: "foreign-one", domain: "other.example", path: "/" },
    ],
    localStorage: {
      "https://auth.fixture.dev": { marker: "tenant-storage" },
      "https://other.example": { marker: "foreign-storage" },
    },
  };
  const scopedContext = {
    cookies: [{ name: "session", value: "tenant-one", domain: "auth.fixture.dev", path: "/" }],
    localStorage: { "https://auth.fixture.dev": { marker: "tenant-storage" } },
  };
  const sealed = sealBrowserContext({
    uid: "u-one", origin: "https://auth.fixture.dev", principalKind: "user_provided", context,
  }, KEY_HEX);
  const row = {
    uid: "u-one",
    origin: "https://auth.fixture.dev",
    principal_kind: "user_provided",
    state: "active",
    ...sealed,
  };
  const reads = [];
  const read = await readBrowserAuthSession({
    uid: "u-one", origin: "https://auth.fixture.dev", principalKind: "user_provided", keyHex: KEY_HEX,
  }, {
    query: async (sql, params) => {
      reads.push({ sql, params });
      return { rows: [row] };
    },
  });
  assert.deepEqual(read.context, scopedContext);
  assert.equal(read.context_sha256, sealed.context_sha256);
  assert.equal(read.key_version, 1);
  assert.match(reads[0].sql, /WHERE uid = \$1 AND origin = \$2 AND principal_kind = \$3/i);
  assert.deepEqual(reads[0].params, ["u-one", "https://auth.fixture.dev", "user_provided"]);

  const writes = [];
  const saved = await upsertBrowserAuthSession({
    uid: "u-one", origin: "https://auth.fixture.dev", principalKind: "user_provided", context, keyHex: KEY_HEX,
  }, {
    query: async (sql, params) => {
      writes.push({ sql, params });
      return { rows: [row] };
    },
  });
  assert.equal(saved.state, "active");
  assert.deepEqual(saved.context, scopedContext);
  assert.equal(saved.context_sha256, sealed.context_sha256);
  assert.equal(saved.key_version, 1);
  assert.match(writes[0].sql, /INSERT INTO public\.lm_browser_auth_sessions/i);
  assert.match(writes[0].sql, /ON CONFLICT \(uid, origin, principal_kind\) DO UPDATE/i);
  assert.doesNotMatch(JSON.stringify(writes[0].params), /tenant-one|tenant-storage|foreign-one|foreign-storage/);

  const invalidated = await invalidateBrowserAuthSession({
    uid: "u-one", origin: "https://auth.fixture.dev", principalKind: "user_provided",
  }, {
    query: async (sql, params) => {
      writes.push({ sql, params });
      return { rows: [{ uid: "u-one" }] };
    },
  });
  assert.equal(invalidated, true);
  assert.match(writes[1].sql, /UPDATE public\.lm_browser_auth_sessions/i);
  assert.deepEqual(writes[1].params, ["u-one", "https://auth.fixture.dev", "user_provided"]);
});

test("browser auth storage reads the design runtime key and ignores the retired environment name", async () => {
  const priorSessionKey = process.env.LM_BROWSER_SESSION_KEY;
  const priorRetiredKey = process.env.LM_BROWSER_AUTH_CONTEXT_KEY_HEX;
  const context = { sessionStorage: { "https://auth.fixture.dev": { current: "tenant-session" } } };
  const sealed = sealBrowserContext({
    uid: "u-one", origin: "https://auth.fixture.dev", principalKind: "user_provided", context,
  }, KEY_HEX);
  try {
    process.env.LM_BROWSER_SESSION_KEY = KEY_HEX;
    process.env.LM_BROWSER_AUTH_CONTEXT_KEY_HEX = "22".repeat(32);
    const record = await readBrowserAuthSession({
      uid: "u-one", origin: "https://auth.fixture.dev", principalKind: "user_provided",
    }, {
      query: async () => ({ rows: [{
        uid: "u-one",
        origin: "https://auth.fixture.dev",
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
