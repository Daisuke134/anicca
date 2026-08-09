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
const postgresIntegrationPath = path.join(
  __dirname,
  "..",
  "test",
  "postgres",
  "cfo-snapshot-corrections-postgres.integration.sh",
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

test("PostgreSQL catalog evidence uses test-only local database labels", () => {
  const integrationScript = fs.readFileSync(postgresIntegrationPath, "utf8");
  const catalogGenerationStart = integrationScript.indexOf("jq -cn");
  const catalogGenerationEnd = integrationScript.indexOf(
    '[[ "$CONSTRAINT_SEMANTICS_MATCH"',
    catalogGenerationStart,
  );

  assert.notEqual(catalogGenerationStart, -1);
  assert.notEqual(catalogGenerationEnd, -1);

  const catalogGeneration = integrationScript.slice(
    catalogGenerationStart,
    catalogGenerationEnd,
  );

  assert.doesNotMatch(catalogGeneration, /\blive[A-Za-z0-9_-]*/i);
  assert.match(catalogGeneration, /\bprimaryTest[A-Za-z0-9_-]*/);
  assert.match(catalogGeneration, /\bisolatedTest[A-Za-z0-9_-]*/);
});
