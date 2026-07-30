"use strict";

const MODES = new Set(["local", "cloud"]);
const SECRET_REF = /^secret:\/\/[a-z0-9][a-z0-9._-]*(?:\/[a-z0-9][a-z0-9._-]*)*$/i;
const TENANT_ID = /^[a-z0-9][a-z0-9._-]{0,127}$/i;

function createSecretProvider({ mode, keychain, vault } = {}) {
  if (!MODES.has(mode)) {
    throw new Error("secret provider mode must be local or cloud");
  }
  const provider = mode === "local" ? keychain : vault;
  const providerName = mode === "local" ? "keychain" : "vault";
  if (!provider || typeof provider.get !== "function" || typeof provider.health !== "function") {
    throw new Error(`${providerName} adapter with get() and health() is required`);
  }

  return {
    async get(tenantId, ref) {
      if (typeof tenantId !== "string" || !TENANT_ID.test(tenantId)) {
        throw new Error("a valid tenant identity is required");
      }
      if (typeof ref !== "string" || !SECRET_REF.test(ref)) {
        throw new Error("a valid secret reference is required");
      }
      return provider.get(tenantId, ref);
    },

    async health() {
      let result;
      try {
        result = await provider.health();
      } catch {
        result = null;
      }
      return {
        ok: result === true || result?.ok === true,
        mode,
        provider: providerName,
      };
    },
  };
}

// AE-ZERO-START-1 §9.1 — colony-shared connector secrets.
//
// One Telegram bot serves the whole colony, and the shared worker claims jobs for EVERY tenant
// (`claim_lm_runtime_jobs` treats a null tenant as all tenants). Binding the bot token to a single
// LM_RUNTIME_TENANT_ID therefore makes every other tenant's job die with a scope mismatch: the tenant
// check is the wrong gate for a secret that is not tenant-private.
//
// Removing a gate is not an option, so this provider substitutes a different one. It performs NO tenant
// binding, and in exchange it resolves ONLY references on an explicit colony allowlist. Wallet key
// material can never be on that allowlist — it is refused at construction time — so the one thing that
// must stay tenant-private keeps flowing exclusively through the per-tenant keychain.
const COLONY_FORBIDDEN_REF = /^secret:\/\/lm-agent-wallet(?:\/|$)/i;

function createColonySecretProvider({ mode, keychain, vault, colonyRefs } = {}) {
  if (!MODES.has(mode)) {
    throw new Error("secret provider mode must be local or cloud");
  }
  const provider = mode === "local" ? keychain : vault;
  const providerName = mode === "local" ? "keychain" : "vault";
  // §12.3 provider asymmetry — the colony adapter's method is `getColonySecret(ref)`, NOT `get`. The tenant
  // provider's `get(tenantId, ref)` and a colony `get(ref)` would share a name with different arity, so a
  // crossed wiring would silently pass a tenant id where a reference belongs. A distinct name turns that
  // mistake into a loud TypeError at construction.
  if (!provider || typeof provider.getColonySecret !== "function" || typeof provider.health !== "function") {
    throw new Error(`${providerName} adapter with getColonySecret() and health() is required`);
  }
  if (typeof provider.get === "function") {
    throw new Error("a colony adapter must not expose get() — that is the tenant-scoped signature");
  }
  if (!Array.isArray(colonyRefs) || colonyRefs.length < 1) {
    throw new Error("a colony secret provider requires an explicit reference allowlist");
  }
  const allowed = new Set();
  for (const ref of colonyRefs) {
    if (typeof ref !== "string" || !SECRET_REF.test(ref)) {
      throw new Error("a colony secret reference is invalid");
    }
    // The whole safety argument for dropping the tenant check is that nothing tenant-private is
    // reachable here. Enforced at construction so it cannot be relaxed by a later caller.
    if (COLONY_FORBIDDEN_REF.test(ref)) {
      throw new Error("tenant wallet key material can never be a colony secret");
    }
    allowed.add(ref);
  }

  return {
    async get(tenantId, ref) {
      // The tenant is still validated for shape — a malformed caller is a bug worth catching — but it is
      // deliberately NOT used to authorise the lookup, because this secret belongs to no single tenant.
      if (typeof tenantId !== "string" || !TENANT_ID.test(tenantId)) {
        throw new Error("a valid tenant identity is required");
      }
      if (typeof ref !== "string" || !SECRET_REF.test(ref)) {
        throw new Error("a valid secret reference is required");
      }
      if (!allowed.has(ref)) {
        throw new Error("secret reference is not a declared colony secret");
      }
      return provider.getColonySecret(ref);
    },

    async health() {
      let result;
      try {
        result = await provider.health();
      } catch {
        result = null;
      }
      return {
        ok: result === true || result?.ok === true,
        mode,
        provider: providerName,
        scope: "colony",
      };
    },
  };
}

module.exports = { createColonySecretProvider, createSecretProvider };
