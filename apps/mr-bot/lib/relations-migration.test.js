"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SQL = fs.readFileSync(path.join(
  __dirname, "../migrations/2026-07-27-lm-relations-log.sql",
), "utf8");
const MENTAL_SQL = fs.readFileSync(path.join(
  __dirname, "../migrations/2026-07-27-lm-mental-send-log-relations-trigger.sql",
), "utf8");

test("relations ledger is PII-minimal, append-only, and race-safe", () => {
  assert.match(SQL, /CREATE TABLE IF NOT EXISTS public\.lm_relations_log/i);
  assert.match(SQL, /kind IN \('scan', 'suggestion_attempt', 'delivery'\)/i);
  assert.match(SQL, /UNIQUE INDEX[\s\S]*\(uid, day, kind\)/i);
  assert.match(SQL, /BEFORE UPDATE OR DELETE/i);
  assert.match(SQL, /BEFORE TRUNCATE/i);
  assert.match(SQL, /REVOKE TRUNCATE, REFERENCES, TRIGGER/i);
  assert.doesNotMatch(SQL, /\b(email|phone|event_title|location|message_text|display_name)\b/i);
});

test("relations sends are admitted to the shared MENTAL budget", () => {
  assert.match(MENTAL_SQL, /'relations'/);
  assert.match(MENTAL_SQL, /expected exactly 1 CHECK constraint/i);
});
