"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { createSecretProvider } = require("./secret-provider.js");

function adapter({ value, health = { ok: true } }) {
  const calls = [];
  return {
    calls,
    async get(tenantId, ref) {
      calls.push({ method: "get", tenantId, ref });
      return value;
    },
    async health() {
      calls.push({ method: "health" });
      return health;
    },
  };
}

test("local mode resolves a secret reference through keychain only", async () => {
  const keychain = adapter({ value: "local-secret-value" });
  const vault = adapter({ value: "wrong-provider" });
  const provider = createSecretProvider({ mode: "local", keychain, vault });

  assert.equal(
    await provider.get("tenant-a", "secret://revenuecat/api-key"),
    "local-secret-value",
  );
  assert.deepEqual(keychain.calls, [{
    method: "get",
    tenantId: "tenant-a",
    ref: "secret://revenuecat/api-key",
  }]);
  assert.deepEqual(vault.calls, []);
});

test("cloud mode scopes secret lookup to the tenant vault only", async () => {
  const keychain = adapter({ value: "wrong-provider" });
  const vault = adapter({ value: "cloud-secret-value" });
  const provider = createSecretProvider({ mode: "cloud", keychain, vault });

  assert.equal(
    await provider.get("tenant-b", "secret://postiz/access-token"),
    "cloud-secret-value",
  );
  assert.deepEqual(vault.calls, [{
    method: "get",
    tenantId: "tenant-b",
    ref: "secret://postiz/access-token",
  }]);
  assert.deepEqual(keychain.calls, []);
});

test("rejects raw secret values and malformed references before adapter access", async () => {
  const keychain = adapter({ value: "must-not-run" });
  const provider = createSecretProvider({ mode: "local", keychain });

  for (const invalidRef of [
    "sk_live_raw_secret",
    "REVENUECAT_API_KEY=raw-secret",
    "secret://",
    "secret://postiz/access token",
  ]) {
    await assert.rejects(
      provider.get("tenant-a", invalidRef),
      /secret reference/i,
    );
  }
  assert.deepEqual(keychain.calls, []);
});

test("rejects missing tenant identity and missing mode-specific adapter", async () => {
  const keychain = adapter({ value: "secret" });
  const local = createSecretProvider({ mode: "local", keychain });

  for (const tenantId of ["", "../tenant-b", "tenant/b"]) {
    await assert.rejects(
      local.get(tenantId, "secret://revenuecat/api-key"),
      /tenant/i,
    );
  }
  assert.deepEqual(keychain.calls, []);
  assert.throws(
    () => createSecretProvider({ mode: "cloud", keychain }),
    /vault/i,
  );
});

test("health exposes only provider status and never adapter secret fields", async () => {
  const vault = adapter({
    value: "cloud-secret-value",
    health: {
      ok: true,
      token: "must-never-escape",
      endpoint: "https://vault.internal/private",
    },
  });
  const provider = createSecretProvider({ mode: "cloud", vault });

  assert.deepEqual(await provider.health(), {
    ok: true,
    mode: "cloud",
    provider: "vault",
  });
  assert.equal(JSON.stringify(await provider.health()).includes("must-never-escape"), false);
});

test("provider does not write retrieved secret values to console", async () => {
  const secret = "never-log-this-value";
  const keychain = adapter({ value: secret });
  const provider = createSecretProvider({ mode: "local", keychain });
  const seen = [];
  const original = {
    log: console.log,
    info: console.info,
    warn: console.warn,
    error: console.error,
  };
  for (const method of Object.keys(original)) {
    console[method] = (...args) => seen.push(args.map(String).join(" "));
  }

  try {
    assert.equal(
      await provider.get("tenant-a", "secret://telegram/bot-token"),
      secret,
    );
    await provider.health();
  } finally {
    Object.assign(console, original);
  }

  assert.equal(seen.some((line) => line.includes(secret)), false);
});
