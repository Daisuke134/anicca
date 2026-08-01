"use strict";

const REGISTRY_ID = /^funder-registry:[0-9a-f]{64}$/;

async function appendFunderRegistryEntries(registry, options = {}) {
  if (!registry || registry.schema_version !== 1 || !Array.isArray(registry.entries) || typeof options.query !== "function") {
    throw new Error("funder registry store invalid");
  }
  const saved = [];
  for (const entry of registry.entries) {
    if (!entry || entry.tenant_id !== registry.tenant_id || !REGISTRY_ID.test(String(entry.registry_id || "")) || entry.revision_digest !== entry.registry_id.slice("funder-registry:".length)) {
      throw new Error("funder registry entry invalid");
    }
    const result = await options.query(`
      INSERT INTO public.lm_funder_registry_snapshots (
        tenant_id, registry_id, funder_id, name, official_url, funder_type,
        priority, verification_status, automation_gate, source_ref,
        observed_at, revision_digest, legacy_claims
      ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::timestamptz,$12,$13::jsonb)
      ON CONFLICT (tenant_id, registry_id) DO NOTHING
      RETURNING registry_id
    `, [
      entry.tenant_id, entry.registry_id, entry.funder_id, entry.name, entry.official_url,
      entry.funder_type, entry.priority, entry.verification_status, entry.automation_gate,
      entry.source_ref, entry.observed_at, entry.revision_digest, JSON.stringify(entry.legacy_claims),
    ]);
    saved.push(Object.freeze({ registry_id: entry.registry_id, inserted: Boolean(result && result.rows && result.rows.length === 1) }));
  }
  return Object.freeze(saved);
}

module.exports = { appendFunderRegistryEntries };
