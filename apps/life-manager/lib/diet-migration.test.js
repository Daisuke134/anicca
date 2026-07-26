"use strict";
// H2 ORG-diet — the shape of the diet ledger. Spec H2 ② says append-only, and "append-only" is only
// true if the DATABASE refuses the rewrite: a promise in a comment is not a guarantee. One table,
// one `kind` discriminator (ask|answer|nudge), and a unique (uid, day, kind) index that IS the cap —
// the 60s tick relies on the duplicate-key 409, not on an in-memory counter that a restart forgets.
// Mirrors lib/care-scan-migration.test.js. Run: node --test lib/diet-migration.test.js

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SQL = fs.readFileSync(
  path.join(__dirname, "../migrations/2026-07-27-lm-diet-log.sql"),
  "utf8",
);
// The "we do not store this" check must read the SCHEMA, not the prose: the header comment says in
// so many words that calories and weight are never stored, and a naive grep over the whole file
// would fail the migration for documenting its own restraint.
const STATEMENTS = SQL.replace(/^\s*--.*$/gm, "");

test("the table is created additively and never replaces anything", () => {
  assert.match(SQL, /CREATE TABLE IF NOT EXISTS public\.lm_diet_log/i);
  assert.doesNotMatch(SQL, /\bDROP TABLE\b/i);
  assert.doesNotMatch(SQL, /\bALTER TABLE public\.lm_(users|wake_log|mental_send_log|care_scan_log)\b/i);
});

test("one table carries all three row kinds, constrained to the three the code writes", () => {
  assert.match(SQL, /kind text NOT NULL/i);
  assert.match(SQL, /kind IN \('ask', 'answer', 'nudge'\)/i);
});

test("the four tap answers are a database constraint, not a convention", () => {
  assert.match(SQL, /answer IN \('teishoku', 'men', 'fast', 'skip'\)/i);
  // An answer row must carry an answer and a non-answer row must not — otherwise the 14-day share
  // is computed over rows that never recorded a choice.
  assert.match(SQL, /\(kind = 'answer'\) = \(answer IS NOT NULL\)/i);
});

test("one row per user per local day per kind — the cap is the unique index", () => {
  assert.match(SQL, /CREATE UNIQUE INDEX IF NOT EXISTS lm_diet_log_uid_day_kind/i);
  assert.match(SQL, /ON public\.lm_diet_log \(uid, day, kind\)/i);
  assert.match(SQL, /day date NOT NULL/i);
});

test("the ledger is append-only: no row may be edited or deleted, ever", () => {
  assert.match(SQL, /BEFORE UPDATE OR DELETE ON public\.lm_diet_log/i);
  assert.match(SQL, /lm_diet_log is append-only/i);
  assert.match(SQL, /REVOKE DELETE ON TABLE public\.lm_diet_log FROM service_role/i);
  assert.match(SQL, /REVOKE UPDATE ON TABLE public\.lm_diet_log FROM service_role/i);
});

test("the table is service-only and holds nothing private about the person", () => {
  assert.match(SQL, /ENABLE ROW LEVEL SECURITY/i);
  assert.match(SQL, /REVOKE ALL ON TABLE public\.lm_diet_log FROM PUBLIC, anon, authenticated/i);
  assert.doesNotMatch(STATEMENTS, /\b(home_address|phone|email|private_key|secret|weight|bmi|calorie)\b/i);
});

test("the trailing-window reads have an index to run on", () => {
  assert.match(SQL, /CREATE INDEX IF NOT EXISTS lm_diet_log_uid_created_at/i);
});
