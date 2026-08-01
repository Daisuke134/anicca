"use strict";

const REGISTRY_ID = /^funder-registry:[0-9a-f]{64}$/;
const RUN_ID = /^funder-discovery:[0-9a-f]{64}$/;

async function insertOrReplay(query, insertSql, selectSql, params, id, digest, label) {
  const inserted = await query(insertSql, params);
  if (inserted && inserted.rows && inserted.rows.length === 1) return true;
  const replay = await query(selectSql, [params[0], id]);
  if (!replay || !replay.rows || replay.rows.length !== 1 || replay.rows[0].digest !== digest) throw new Error(`${label} collision`);
  return false;
}

async function appendDailyFunderDiscovery(discovery, options = {}) {
  if (!discovery || discovery.schema_version !== 1 || !Array.isArray(discovery.entries) || !discovery.run || typeof options.query !== "function") {
    throw new Error("funder discovery store invalid");
  }
  const savedEntries = [];
  for (const entry of discovery.entries) {
    if (!entry || entry.tenant_id !== discovery.tenant_id || !REGISTRY_ID.test(String(entry.registry_id || ""))
      || entry.revision_digest !== entry.registry_id.slice("funder-registry:".length)) throw new Error("funder discovery entry invalid");
    const inserted = await insertOrReplay(options.query, `
      INSERT INTO public.lm_funder_registry_snapshots (
        tenant_id, registry_id, funder_id, name, official_url, funder_type, priority,
        verification_status, automation_gate, source_ref, observed_at, revision_digest, legacy_claims,
        source_url, last_verified_at, next_deadline, terms_hash, solo_allowed, location, status,
        source_content_sha256, evidence_sha256, rationale_sha256, discovery_kind, discovery_facts_digest
      ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::timestamptz,$12,$13::jsonb,$14,$15::timestamptz,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25)
      ON CONFLICT (tenant_id, registry_id) DO NOTHING RETURNING registry_id AS id`, `
      SELECT revision_digest AS digest FROM public.lm_funder_registry_snapshots WHERE tenant_id=$1 AND registry_id=$2`, [
      entry.tenant_id, entry.registry_id, entry.funder_id, entry.name, entry.official_url, entry.funder_type, entry.priority,
      entry.verification_status, entry.automation_gate, entry.source_ref, entry.observed_at, entry.revision_digest, JSON.stringify(entry.legacy_claims),
      entry.source_url, entry.observed_at, entry.next_deadline, entry.terms_hash, entry.solo_allowed, entry.location, entry.status,
      entry.source_content_sha256, entry.evidence_sha256, entry.rationale_sha256, entry.discovery_kind, entry.discovery_facts_digest,
    ], entry.registry_id, entry.revision_digest, "funder registry");
    savedEntries.push(Object.freeze({ registry_id: entry.registry_id, inserted }));
  }
  const run = discovery.run;
  if (run.tenant_id !== discovery.tenant_id || !RUN_ID.test(String(run.discovery_run_id || "")) || run.run_digest !== run.discovery_run_id.slice("funder-discovery:".length)) {
    throw new Error("funder discovery run invalid");
  }
  const runInserted = await insertOrReplay(options.query, `
    INSERT INTO public.lm_funder_discovery_runs (
      tenant_id, discovery_run_id, tokyo_day, observed_at, status, source_count, candidate_count,
      appended_count, source_receipts, registry_ids, run_digest
    ) VALUES ($1,$2,$3::date,$4::timestamptz,$5,$6,$7,$8,$9::jsonb,$10::jsonb,$11)
    ON CONFLICT (tenant_id, discovery_run_id) DO NOTHING RETURNING discovery_run_id AS id`, `
    SELECT run_digest AS digest FROM public.lm_funder_discovery_runs WHERE tenant_id=$1 AND discovery_run_id=$2`, [
    run.tenant_id, run.discovery_run_id, run.tokyo_day, run.observed_at, run.status, run.source_count,
    run.candidate_count, run.appended_count, JSON.stringify(run.source_receipts), JSON.stringify(run.registry_ids), run.run_digest,
  ], run.discovery_run_id, run.run_digest, "funder discovery run");
  return Object.freeze({ entries: Object.freeze(savedEntries), run: Object.freeze({ discovery_run_id: run.discovery_run_id, inserted: runInserted }) });
}

module.exports = { appendDailyFunderDiscovery };
