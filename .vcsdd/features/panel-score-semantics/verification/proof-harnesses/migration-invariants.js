"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const REPO_ROOT = path.resolve(__dirname, "../../../../..");
const migrationPath = path.join(REPO_ROOT, "apps/life-call/migrations/2026-07-22-panel-score-outcomes.sql");
const sql = fs.readFileSync(migrationPath, "utf8");
let checks = 0;

function matches(pattern, label) {
  assert.match(sql, pattern, label);
  checks += 1;
}

function countAtLeast(pattern, minimum, label) {
  const count = [...sql.matchAll(pattern)].length;
  assert.ok(count >= minimum, `${label}: ${count} < ${minimum}`);
  checks += 1;
}

matches(/CREATE TABLE IF NOT EXISTS public\.lm_score_outcomes/i, "additive ledger table");
matches(/revision_key\s+uuid\s+NOT NULL\s+CHECK\s*\(revision_key\s*<>\s*'00000000-0000-0000-0000-000000000000'::uuid\)/i, "non-zero revision key storage check");
matches(/UNIQUE\s*\(uid,\s*organ,\s*entity_key,\s*outcome_kind,\s*revision_key\)/i, "exact immutable revision tuple");
matches(/amount_minor\s+numeric/i, "non-rounding numeric storage");
matches(/amount_minor\s*=\s*trunc\(amount_minor\)/i, "integer-only amount constraint");
matches(/amount_minor\s*>=\s*0\s+AND\s+amount_minor\s*<=\s*9007199254740991/i, "safe amount range");
matches(/jsonb_typeof\(components\)\s*=\s*'object'/i, "structured components");
matches(/lm_score_outcomes_kind_status[\s\S]*daily_travel[\s\S]*physical_need[\s\S]*mental_trigger[\s\S]*financial_external_income/i, "typed organ/kind/status check");
for (const token of [
  "required_succeeded", "required_failed", "required_pending", "context_unnecessary", "optional",
  "detected", "candidate", "search", "unconfirmed_request", "confirmed_booking", "confirmed_completion", "unresolved",
  "delivered", "suppression_honored", "correction_persisted", "cap_overflow",
  "verified", "realized", "charged", "confirmed", "excluded",
]) matches(new RegExp(`'${token}'`, "i"), `typed status ${token}`);
matches(/CREATE INDEX IF NOT EXISTS lm_score_outcomes_period_idx\s+ON public\.lm_score_outcomes\s*\(uid,\s*organ,\s*occurred_at,\s*recorded_at,\s*public_ref\)/i, "bounded period index");
matches(/CREATE INDEX IF NOT EXISTS lm_score_outcomes_winner_idx[\s\S]*\(uid,\s*organ,\s*entity_key,\s*outcome_kind,\s*recorded_at DESC,\s*revision_key DESC,\s*public_ref DESC\)/i, "deterministic winner index");
matches(/ENABLE ROW LEVEL SECURITY/i, "RLS enabled");
matches(/CREATE POLICY lm_score_outcomes_service_select[\s\S]*FOR SELECT TO service_role/i, "service select policy");
matches(/REVOKE ALL ON TABLE public\.lm_score_outcomes FROM PUBLIC, anon, authenticated/i, "browser table denial");
matches(/GRANT SELECT, INSERT ON TABLE public\.lm_score_outcomes TO service_role/i, "service table grant");
matches(/REVOKE UPDATE, DELETE ON TABLE public\.lm_score_outcomes FROM service_role/i, "service mutation denial");
matches(/BEFORE UPDATE OR DELETE ON public\.lm_score_outcomes[\s\S]*reject_lm_score_outcome_mutation/i, "append-only trigger");
matches(/CREATE OR REPLACE FUNCTION public\.lm_append_score_outcome\(p_outcome jsonb\)[\s\S]*ON CONFLICT \(uid, organ, entity_key, outcome_kind, revision_key\) DO NOTHING/i, "atomic retry insertion");
for (const field of ["outcome_status", "occurred_at", "resolved_at", "amount_minor", "currency", "components"]) {
  matches(new RegExp(`existing\\.${field} IS NOT DISTINCT FROM`, "i"), `retry equality ${field}`);
}
matches(/RAISE EXCEPTION 'revision_key_conflict'/i, "changed-payload conflict");
matches(/CREATE OR REPLACE FUNCTION public\.lm_panel_score_outcome_snapshot\(p_uid text, p_periods jsonb\)[\s\S]*LANGUAGE sql[\s\S]*STABLE[\s\S]*SECURITY INVOKER/i, "single-statement stable invoker snapshot");
countAtLeast(/SECURITY INVOKER/gi, 3, "all functions are invoker security");
countAtLeast(/SET search_path\s*=\s*public,\s*pg_temp/gi, 3, "all functions fix search_path");
matches(/WHERE outcome\.uid\s*=\s*p_uid[\s\S]*outcome\.occurred_at\s*>=\s*requested\.start_at[\s\S]*outcome\.occurred_at\s*<\s*requested\.end_at/i, "tenant and half-open SQL filter");
matches(/LIMIT\s+20001/i, "overflow sentinel bound");
matches(/summary\.row_count\s*>\s*20000[\s\S]*'overflow', true[\s\S]*'rows_by_organ', '\{\}'::jsonb/i, "complete-or-overflow response");
matches(/REVOKE ALL ON FUNCTION public\.lm_panel_score_outcome_snapshot\(text, jsonb\) FROM PUBLIC, anon, authenticated/i, "browser function denial");
matches(/GRANT EXECUTE ON FUNCTION public\.lm_panel_score_outcome_snapshot\(text, jsonb\) TO service_role/i, "service function grant");

const sha256 = crypto.createHash("sha256").update(sql).digest("hex");
console.log(`PROP-005 PASS static_checks=${checks} migration_sha256=${sha256} supporting_real_postgres_required=true production_postflight_deferred_to_phase6=true`);
