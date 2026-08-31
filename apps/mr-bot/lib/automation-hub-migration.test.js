"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

test("Automation Hub migration is tenant-bound, revisioned, and role-locked", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-31-lm-automation-hub.sql"), "utf8");
  assert.match(sql, /CREATE TABLE IF NOT EXISTS public\.lm_automation_stacks/);
  assert.match(sql, /CREATE TABLE IF NOT EXISTS public\.lm_automation_stack_tools/);
  assert.match(sql, /FUNCTION public\.read_lm_automation_stack\(p_uid text, p_chat_id text\)/);
  assert.match(sql, /'tools', COALESCE/);
  assert.match(sql, /FOR UPDATE/);
  assert.match(sql, /automation revision conflict/);
  assert.match(sql, /p_expected_revision IS NULL/);
  assert.match(sql, /p_tools IS NULL/);
  assert.match(sql, /p_enabled IS NULL/);
  assert.match(sql, /p_enabled AND p_verified THEN 'running'/);
  assert.match(sql, /telegram_chat_id::text = p_chat_id/);
  assert.match(sql, /ENABLE ROW LEVEL SECURITY/);
  assert.match(sql, /REVOKE ALL[\s\S]+FROM PUBLIC, anon, authenticated/);
  assert.match(sql, /GRANT EXECUTE[\s\S]+TO service_role/);
  assert.match(sql, /GRANT EXECUTE ON FUNCTION public\.read_lm_automation_stack\(text,text\) TO service_role/);
  assert.doesNotMatch(sql, /GRANT (SELECT|INSERT|UPDATE|DELETE)[^\n]+authenticated/);
});
