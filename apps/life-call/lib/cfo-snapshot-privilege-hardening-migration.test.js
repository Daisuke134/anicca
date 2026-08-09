"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");

const migrationPath = path.join(
  __dirname,
  "..",
  "migrations",
  "2026-08-09-cfo-snapshot-privilege-hardening.sql",
);

test("CFO snapshot hardening converges the service table to the exact write contract", () => {
  const sql = fs.readFileSync(migrationPath, "utf8");

  assert.match(
    sql,
    /REVOKE ALL ON TABLE public\.lm_cfo_daily_snapshots FROM service_role\s*;/i,
  );
  assert.match(
    sql,
    /GRANT SELECT, INSERT ON TABLE public\.lm_cfo_daily_snapshots TO service_role\s*;/i,
  );
  assert.match(
    sql,
    /REVOKE ALL ON TABLE public\.lm_cfo_daily_snapshots FROM PUBLIC, anon, authenticated\s*;/i,
  );

  assert.doesNotMatch(sql, /\b(?:CREATE|ALTER|DROP|INSERT\s+INTO|UPDATE\s+\S+\s+SET|DELETE\s+FROM|TRUNCATE)\b/i);
  assert.doesNotMatch(sql, /\b(?:FUNCTION|CONSTRAINT|INDEX|TRIGGER|POLICY|SEQUENCE)\b/i);
  assert.doesNotMatch(sql, /EXECUTE|GRANT ALL|DO\s*\$\$/i);
});
