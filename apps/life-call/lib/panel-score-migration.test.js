"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const migrationPath = path.join(__dirname, "..", "migrations", "2026-07-22-panel-score-outcomes.sql");

test("panel score migration is additive, revision-key idempotent, append-only, indexed, and role-locked", () => {
  const sql = fs.readFileSync(migrationPath, "utf8");
  assert.match(sql, /CREATE TABLE IF NOT EXISTS public\.lm_score_outcomes/i);
  assert.match(sql, /revision_key\s+uuid\s+NOT NULL/i);
  assert.match(sql, /UNIQUE\s*\(uid,\s*organ,\s*entity_key,\s*outcome_kind,\s*revision_key\)/i);
  assert.match(sql, /revision_key_conflict/i);
  assert.match(sql, /reject_lm_score_outcome_mutation/i);
  assert.match(sql, /ENABLE ROW LEVEL SECURITY/i);
  assert.match(sql, /SECURITY INVOKER/i);
  assert.match(sql, /SET search_path\s*=\s*public,\s*pg_temp/i);
  assert.match(sql, /REVOKE ALL ON TABLE public\.lm_score_outcomes FROM PUBLIC, anon, authenticated/i);
  assert.match(sql, /REVOKE ALL ON FUNCTION public\.lm_panel_score_outcome_snapshot\(text,\s*jsonb\) FROM PUBLIC, anon, authenticated/i);
  assert.match(sql, /GRANT EXECUTE ON FUNCTION public\.lm_panel_score_outcome_snapshot\(text,\s*jsonb\) TO service_role/i);
  assert.match(sql, /occurred_at\s*>=/i);
  assert.match(sql, /occurred_at\s*</i);
  assert.match(sql, /LIMIT\s+20001/i);
});
