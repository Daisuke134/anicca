// VCSDD sprint-2 RED — S7: additive Supabase migration for leaderboard columns.
// FAILS until the migration SQL file exists on disk with the correct additive DDL.
const { test } = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const MIG = path.resolve(__dirname, "../../../../supabase/2026-07-instances-leaderboard.sql");

function readMigration() {
  assert.ok(fs.existsSync(MIG), `migration file must exist at ${MIG}`);
  return fs.readFileSync(MIG, "utf8").toLowerCase();
}

test("S7.1: migration exists and adds tags text[] additive column", () => {
  const sql = readMigration();
  assert.match(sql, /alter\s+table\s+instances\s+add\s+column\s+if\s+not\s+exists\s+tags\s+text\[\]/);
});
test("S7.1: adds revenue_today_usd (nullable double precision)", () => {
  const sql = readMigration();
  assert.match(sql, /add\s+column\s+if\s+not\s+exists\s+revenue_today_usd\s+double\s+precision/);
  assert.doesNotMatch(sql, /revenue_today_usd\s+double\s+precision\s+not\s+null/);
});
test("S7.1: adds revenue_by_source jsonb", () => {
  const sql = readMigration();
  assert.match(sql, /add\s+column\s+if\s+not\s+exists\s+revenue_by_source\s+jsonb/);
});
test("S7.1: adds net_worth_src and earn_src text columns", () => {
  const sql = readMigration();
  assert.match(sql, /add\s+column\s+if\s+not\s+exists\s+net_worth_src\s+text/);
  assert.match(sql, /add\s+column\s+if\s+not\s+exists\s+earn_src\s+text/);
});
test("S7.1: adds last_heartbeat timestamptz", () => {
  const sql = readMigration();
  assert.match(sql, /add\s+column\s+if\s+not\s+exists\s+last_heartbeat\s+timestamptz/);
});
test("S7.1: adds GIN index on tags", () => {
  const sql = readMigration();
  assert.match(sql, /create\s+index\s+if\s+not\s+exists\s+idx_instances_tags_gin\s+on\s+instances\s+using\s+gin\s*\(\s*tags\s*\)/);
});
test("S7.1/S7.2: migration is idempotent — all DDL guarded by IF NOT EXISTS", () => {
  const sql = readMigration();
  // Every DDL statement that mutates schema must be idempotent (add column / create index).
  const stmts = sql.split(";").map((s) => s.trim()).filter((s) => s.startsWith("alter table") || s.startsWith("create index") || s.startsWith("create unique index"));
  assert.ok(stmts.length > 0, "migration must contain DDL statements");
  for (const s of stmts) {
    assert.ok(/if\s+not\s+exists/.test(s), `DDL must be idempotent (missing IF NOT EXISTS): ${s}`);
  }
});
test("S7.2: migration does NOT drop or NOT-NULL any existing column (back-compat)", () => {
  const sql = readMigration();
  assert.doesNotMatch(sql, /drop\s+column/);
  assert.doesNotMatch(sql, /alter\s+column[^;]*\bset\s+not\s+null\b/);
});
