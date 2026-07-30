"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { createColonySecretProvider, createSecretProvider } = require("./secret-provider.js");

const TELEGRAM_REF = "secret://telegram/bot-token";

// A colony adapter takes the reference ONLY — it is handed no tenant, which is the structural reason it
// cannot leak one tenant's secret to another: there is nothing tenant-shaped for it to get wrong.
function colonyAdapter({ value, health = { ok: true } }) {
  const calls = [];
  return {
    calls,
    async get(ref) {
      calls.push({ method: "get", args: [...arguments], ref });
      return value;
    },
    async health() {
      calls.push({ method: "health" });
      return health;
    },
  };
}

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

// AE-ZERO-START-1 §9.1 — the colony provider. These are hostile-payload tests: the point is what the
// provider REFUSES once the tenant check is deliberately absent.

test("a colony secret resolves for every tenant, which is the whole point", async () => {
  // The measured BLOCKER: a shared worker claims jobs for all tenants, so a tenant-bound bot token makes
  // every tenant except LM_RUNTIME_TENANT_ID fail with a scope mismatch.
  const keychain = colonyAdapter({ value: "colony-bot-token" });
  const provider = createColonySecretProvider({
    mode: "local",
    keychain,
    colonyRefs: [TELEGRAM_REF],
  });

  for (const tenantId of ["tenant-a", "tenant-b", "lm_550e8400-e29b-41d4-a716-446655440000"]) {
    assert.equal(await provider.get(tenantId, TELEGRAM_REF), "colony-bot-token");
  }
  // The adapter was never told which tenant asked, so it cannot be tricked into a cross-tenant answer.
  assert.equal(keychain.calls.every((call) => call.args.length === 1), true);
  assert.equal(keychain.calls.every((call) => call.ref === TELEGRAM_REF), true);
});

test("a colony provider can never be built around tenant wallet key material", () => {
  // The hostile payload: an operator or a future caller trying to route wallet keys through the provider
  // that has no tenant binding. Refused at construction, not at call time.
  for (const ref of [
    "secret://lm-agent-wallet/tenant-a/base",
    "secret://lm-agent-wallet/tenant-a/solana",
    "secret://lm-agent-wallet",
    "SECRET://LM-AGENT-WALLET/tenant-a/base",
  ]) {
    assert.throws(
      () => createColonySecretProvider({
        mode: "local",
        keychain: colonyAdapter({ value: "must-not-be-reachable" }),
        colonyRefs: [ref],
      }),
      /key material/i,
      `${ref} must be refused as a colony secret`,
    );
  }
});

test("a colony provider refuses any reference it was not explicitly given", async () => {
  const keychain = colonyAdapter({ value: "colony-bot-token" });
  const provider = createColonySecretProvider({
    mode: "local",
    keychain,
    colonyRefs: [TELEGRAM_REF],
  });

  for (const ref of [
    // Well-formed but undeclared: without the tenant check, the allowlist IS the gate.
    "secret://postiz/api-key",
    "secret://lm-agent-wallet/tenant-a/base",
    "secret://telegram/bot-token-2",
    // Malformed.
    "sk_live_raw_secret",
    "secret://",
    "secret://telegram/bot token",
  ]) {
    await assert.rejects(provider.get("tenant-a", ref), /reference/i, `${ref} must be refused`);
  }
  assert.deepEqual(keychain.calls, [], "nothing undeclared may reach the adapter");
});

test("a colony provider still refuses a malformed caller identity and an empty allowlist", async () => {
  const keychain = colonyAdapter({ value: "colony-bot-token" });
  const provider = createColonySecretProvider({ mode: "local", keychain, colonyRefs: [TELEGRAM_REF] });
  for (const tenantId of ["", "../tenant-b", "tenant/b", null]) {
    await assert.rejects(provider.get(tenantId, TELEGRAM_REF), /tenant/i);
  }
  assert.deepEqual(keychain.calls, []);

  for (const colonyRefs of [undefined, [], "secret://telegram/bot-token", [""], [123]]) {
    assert.throws(
      () => createColonySecretProvider({ mode: "local", keychain, colonyRefs }),
      /allowlist|invalid/i,
    );
  }
});

test("colony health says it is colony-scoped and leaks no adapter fields", async () => {
  const keychain = colonyAdapter({
    value: "colony-bot-token",
    health: { ok: true, token: "must-never-escape" },
  });
  const provider = createColonySecretProvider({ mode: "local", keychain, colonyRefs: [TELEGRAM_REF] });
  const health = await provider.health();
  assert.deepEqual(health, { ok: true, mode: "local", provider: "keychain", scope: "colony" });
  assert.equal(JSON.stringify(health).includes("must-never-escape"), false);
});

test("the tenant-scoped provider is NOT weakened — it still binds every lookup", async () => {
  // §9.1 is explicit that createSecretProvider must keep its tenant gate for every other adapter.
  const keychain = adapter({ value: "tenant-secret" });
  const provider = createSecretProvider({ mode: "local", keychain });
  assert.equal(await provider.get("tenant-a", "secret://lm-agent-wallet/tenant-a/base"), "tenant-secret");
  // The tenant id is passed through to the adapter, which is where the binding check lives.
  assert.equal(keychain.calls[0].tenantId, "tenant-a");
  assert.equal((await provider.health()).scope, undefined, "tenant scope is the default, not a label");
});
