#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const { buildDailyFunderDiscovery } = require("../lib/funder-program-discovery.js");

function args(argv) {
  const input = argv.indexOf("--input"); const existing = argv.indexOf("--existing");
  if (input < 0 || existing < 0 || !argv[input + 1] || !argv[existing + 1]) throw new Error("usage: render-funder-program-discovery-sql --input <json> --existing <json>");
  return { input: argv[input + 1], existing: argv[existing + 1] };
}
const quote = (value) => value === null ? "NULL" : `'${String(value).replaceAll("'", "''")}'`;

function render(discovery) {
  const sql = ["\\set ON_ERROR_STOP on", "BEGIN;"];
  for (const entry of discovery.entries) sql.push(`INSERT INTO public.lm_funder_registry_snapshots (
tenant_id,registry_id,funder_id,name,official_url,funder_type,priority,verification_status,automation_gate,source_ref,observed_at,revision_digest,legacy_claims,
source_url,last_verified_at,next_deadline,terms_hash,solo_allowed,location,status,source_content_sha256,evidence_sha256,rationale_sha256,discovery_kind,discovery_facts_digest
) VALUES (${[entry.tenant_id,entry.registry_id,entry.funder_id,entry.name,entry.official_url,entry.funder_type,entry.priority,entry.verification_status,entry.automation_gate,entry.source_ref,entry.observed_at,entry.revision_digest,JSON.stringify(entry.legacy_claims),entry.source_url,entry.observed_at,entry.next_deadline,entry.terms_hash,entry.solo_allowed,entry.location,entry.status,entry.source_content_sha256,entry.evidence_sha256,entry.rationale_sha256,entry.discovery_kind,entry.discovery_facts_digest].map(quote).join(",")}) ON CONFLICT (tenant_id,registry_id) DO NOTHING;`);
  const run = discovery.run;
  sql.push(`INSERT INTO public.lm_funder_discovery_runs (tenant_id,discovery_run_id,tokyo_day,observed_at,status,source_count,candidate_count,appended_count,source_receipts,registry_ids,run_digest)
VALUES (${[run.tenant_id,run.discovery_run_id,run.tokyo_day,run.observed_at,run.status,run.source_count,run.candidate_count,run.appended_count,JSON.stringify(run.source_receipts),JSON.stringify(run.registry_ids),run.run_digest].map(quote).join(",")}) ON CONFLICT (tenant_id,discovery_run_id) DO NOTHING;`);
  sql.push("COMMIT;", `SELECT ${quote(run.discovery_run_id)} AS discovery_run_id, ${run.source_count} AS source_count, ${run.candidate_count} AS candidate_count, ${run.appended_count} AS appended_count;`);
  return `${sql.join("\n")}\n`;
}

function main() {
  const files = args(process.argv.slice(2));
  const input = JSON.parse(fs.readFileSync(files.input, "utf8"));
  const existingEntries = JSON.parse(fs.readFileSync(files.existing, "utf8"));
  process.stdout.write(render(buildDailyFunderDiscovery({ ...input, existingEntries })));
}

if (require.main === module) {
  try { main(); } catch (error) { process.stderr.write(`${error.message}\n`); process.exitCode = 1; }
}
module.exports = { render };
