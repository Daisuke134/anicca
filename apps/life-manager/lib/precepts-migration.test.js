"use strict";
// H4 ORG-precepts — the shape of the precepts ledger, and the one ALTER that lets its sends into
// MENTAL's budget. Spec H4 ② says append-only, and "append-only" is only true if the DATABASE
// refuses the rewrite: a promise in a comment is not a guarantee.
//
// These assertions are over the SQL this branch actually ships, so a migration edited in the console
// and never committed cannot pass them, and a future edit that quietly drops a guard fails here.
// Mirrors lib/diet-migration.test.js. Run: node --test lib/precepts-migration.test.js

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const LEDGER_SQL = fs.readFileSync(
  path.join(__dirname, "../migrations/2026-07-27-lm-precepts-log.sql"), "utf8",
);
const TRIGGER_SQL = fs.readFileSync(
  path.join(__dirname, "../migrations/2026-07-27-lm-mental-send-log-precepts-trigger.sql"), "utf8",
);
// The "we do not store this" check must read the SCHEMA, not the prose: the header says in so many
// words that no score is ever stored, and a naive grep over the whole file would fail the migration
// for documenting its own restraint.
const STATEMENTS = LEDGER_SQL.replace(/^\s*--.*$/gm, "");

test("the table is created additively and never replaces anything", () => {
  assert.match(LEDGER_SQL, /CREATE TABLE IF NOT EXISTS public\.lm_precepts_log/i);
  assert.doesNotMatch(LEDGER_SQL, /\bDROP TABLE\b/i);
  assert.doesNotMatch(LEDGER_SQL, /\bALTER TABLE public\.lm_(users|wake_log|mental_send_log|care_scan_log|diet_log)\b/i);
});

test("one table carries all three row kinds, constrained to the three the code writes", () => {
  assert.match(LEDGER_SQL, /kind text NOT NULL/i);
  assert.match(LEDGER_SQL, /kind IN \('ask', 'answer', 'mirror'\)/i);
});

test("the five tap answers are a database constraint, not a convention", () => {
  assert.match(LEDGER_SQL, /answer IN \('lie', 'harsh', 'time', 'impulse', 'calm'\)/i);
  // An answer row must carry an answer and a non-answer row must not — otherwise the mirror's counts
  // are computed over rows that never recorded a choice.
  assert.match(LEDGER_SQL, /\(kind = 'answer'\) = \(answer IS NOT NULL\)/i);
});

test("one row per user per local day per kind — the cap is the unique index", () => {
  assert.match(LEDGER_SQL, /CREATE UNIQUE INDEX IF NOT EXISTS lm_precepts_log_uid_day_kind/i);
  assert.match(LEDGER_SQL, /ON public\.lm_precepts_log \(uid, day, kind\)/i);
  assert.match(LEDGER_SQL, /day date NOT NULL/i);
});

test("the ledger is append-only: no row may be edited or deleted, ever", () => {
  assert.match(LEDGER_SQL, /BEFORE UPDATE OR DELETE ON public\.lm_precepts_log/i);
  assert.match(LEDGER_SQL, /lm_precepts_log is append-only/i);
  assert.match(LEDGER_SQL, /REVOKE DELETE ON TABLE public\.lm_precepts_log FROM service_role/i);
  assert.match(LEDGER_SQL, /REVOKE UPDATE ON TABLE public\.lm_precepts_log FROM service_role/i);
});

test("TRUNCATE cannot empty an append-only ledger either", () => {
  // The row trigger sees UPDATE and DELETE. TRUNCATE is neither, and the table owner keeps it by
  // default — so the append-only promise would have a hole exactly the width of one statement.
  assert.match(LEDGER_SQL, /REVOKE TRUNCATE, REFERENCES, TRIGGER ON TABLE public\.lm_precepts_log FROM service_role/i);
  assert.match(LEDGER_SQL, /BEFORE TRUNCATE ON public\.lm_precepts_log/i);
  assert.match(LEDGER_SQL, /FOR EACH STATEMENT/i);
});

test("the table is service-only and CANNOT hold a sentence about a person", () => {
  assert.match(LEDGER_SQL, /ENABLE ROW LEVEL SECURITY/i);
  assert.match(LEDGER_SQL, /REVOKE ALL ON TABLE public\.lm_precepts_log FROM PUBLIC, anon, authenticated/i);
  // H4 ③: no score, no note, no verdict. The absence of a free-text column is what makes "we never
  // write a judgement about the user" a property of the schema rather than of our good intentions.
  assert.doesNotMatch(STATEMENTS, /\b(home_address|phone|email|private_key|secret|score|note|notes|comment|summary|verdict|rating)\b/i);
});

test("the index covers the column the queries actually filter on", () => {
  assert.match(LEDGER_SQL, /CREATE INDEX IF NOT EXISTS lm_precepts_log_uid_day/i);
  assert.match(LEDGER_SQL, /ON public\.lm_precepts_log \(uid, day DESC\)/i);
  assert.doesNotMatch(STATEMENTS, /\(uid, created_at DESC\)/i);
});

// ── the MENTAL budget ALTER (H4 ⑤) ────────────────────────────────────────────────────────────────

test("lm_mental_send_log's trigger CHECK really is constrained today — the ALTER is not optional", () => {
  // The premise of the second migration, asserted rather than assumed. Without this the precepts
  // insert would 400 forever: the message goes out, the budget row never lands, and the shared cap
  // silently stops counting the organ that is spending it.
  const original = fs.readFileSync(
    path.join(__dirname, "../migrations/2026-07-25-lm-mental-send-log.sql"), "utf8",
  );
  assert.match(original, /trigger text NOT NULL CHECK \(trigger IN \('pre_event', 'between_events', 'pre_sleep'\)\)/i);
  assert.doesNotMatch(original, /precepts/i);
});

test("the ALTER adds exactly the two tokens the runtime writes, keeping all three old ones", () => {
  assert.match(TRIGGER_SQL, /CHECK \(trigger IN \('pre_event', 'between_events', 'pre_sleep', 'precepts', 'precepts_mirror'\)\)/i);
  const { PRECEPTS_SEND_TRIGGER } = require("./precepts-runtime.js");
  const { MIRROR_SEND_TRIGGER } = require("./precepts-mirror.js");
  for (const token of [PRECEPTS_SEND_TRIGGER, MIRROR_SEND_TRIGGER]) {
    assert.ok(TRIGGER_SQL.includes(`'${token}'`), `the SQL must allow the token the code writes: ${token}`);
  }
});

test("the old constraint is found by DEFINITION, so a guessed name cannot no-op the migration", () => {
  // Dropping a name that does not exist succeeds and changes nothing, leaving the new constraint to
  // be rejected as a duplicate: a migration that reports success and does not migrate.
  assert.match(TRIGGER_SQL, /pg_constraint/i);
  assert.match(TRIGGER_SQL, /pg_get_constraintdef\(oid\) ILIKE '%pre_sleep%'/i);
  assert.match(TRIGGER_SQL, /EXECUTE format\('ALTER TABLE public\.lm_mental_send_log DROP CONSTRAINT %I'/i);
  // Idempotent: a second run finds the constraint it added (it mentions pre_sleep too) and replaces
  // it with the identical definition.
  assert.match(TRIGGER_SQL, /ADD CONSTRAINT lm_mental_send_log_trigger_check/i);
});

test("the ALTER touches no row and drops no column", () => {
  assert.doesNotMatch(TRIGGER_SQL, /\bDROP (TABLE|COLUMN)\b/i);
  assert.doesNotMatch(TRIGGER_SQL, /\b(DELETE FROM|TRUNCATE|UPDATE)\b/i);
});
