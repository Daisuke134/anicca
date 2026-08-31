"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

test("Automation Hub migration is tenant-bound, revisioned, and role-locked", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-31-lm-automation-hub.sql"), "utf8");
  assert.match(sql, /CREATE TABLE IF NOT EXISTS public\.lm_automation_stacks/);
  assert.match(sql, /CREATE TABLE IF NOT EXISTS public\.lm_automation_stack_tools/);
  assert.match(sql, /FOR UPDATE/);
  assert.match(sql, /automation revision conflict/);
  assert.match(sql, /p_enabled AND p_verified THEN 'running'/);
  assert.match(sql, /telegram_chat_id::text = p_chat_id/);
  assert.match(sql, /ENABLE ROW LEVEL SECURITY/);
  assert.match(sql, /REVOKE ALL[\s\S]+FROM PUBLIC, anon, authenticated/);
  assert.match(sql, /GRANT EXECUTE[\s\S]+TO service_role/);
  assert.doesNotMatch(sql, /GRANT (SELECT|INSERT|UPDATE|DELETE)[^\n]+authenticated/);
});
