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

module.exports = { createSecretProvider };
