"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SQL = fs.readFileSync(path.join(
  __dirname,
  "../migrations/2026-07-28-lm-browser-auth-sessions.sql",
), "utf8");

test("browser auth sessions are service-only, tenant-bound encrypted rows", () => {
  assert.match(SQL, /CREATE TABLE IF NOT EXISTS public\.lm_browser_auth_sessions/i);
  assert.match(SQL, /PRIMARY KEY \(uid, origin, principal_kind\)/i);
  assert.match(SQL, /principal_kind text NOT NULL CHECK \(principal_kind IN \('agent_owned', 'user_provided'\)\)/i);
  for (const column of ["ciphertext", "iv", "auth_tag", "context_sha256", "key_version"]) {
    assert.match(SQL, new RegExp(`${column}\\s+(?:text|integer)\\s+NOT NULL`, "i"));
  }
  assert.match(SQL, /ALTER TABLE public\.lm_browser_auth_sessions ENABLE ROW LEVEL SECURITY/i);
  assert.match(SQL, /REVOKE ALL ON TABLE public\.lm_browser_auth_sessions FROM PUBLIC/i);
  for (const role of ["anon", "authenticated", "service_role"]) {
    assert.match(SQL, new RegExp(`FROM pg_roles WHERE rolname = '${role}'`, "i"));
  }
  assert.match(SQL, /REVOKE ALL ON TABLE public\.lm_browser_auth_sessions FROM anon/i);
  assert.match(SQL, /REVOKE ALL ON TABLE public\.lm_browser_auth_sessions FROM authenticated/i);
  assert.match(SQL, /GRANT SELECT, INSERT, UPDATE ON TABLE public\.lm_browser_auth_sessions TO service_role/i);
  assert.doesNotMatch(SQL, /CREATE POLICY|GRANT .* TO (?:anon|authenticated)/i);
});
