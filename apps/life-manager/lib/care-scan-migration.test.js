"use strict";
// 11a runtime — the shape of the care scan log itself. A scan record is only evidence if the
// database refuses to rewrite the facts: the daily claim (uid, scan_day) is unique, the detection
// facts are frozen at insert, and only the 11b chain result may land on the row afterwards.
// Mirrors lib/earnings-migration.test.js. Run: node --test lib/care-scan-migration.test.js

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SQL = fs.readFileSync(
  path.join(__dirname, "../migrations/2026-07-26-lm-care-scan-log.sql"),
  "utf8",
);

test("the table is created additively and never replaces anything", () => {
  assert.match(SQL, /CREATE TABLE IF NOT EXISTS public\.lm_care_scan_log/i);
  assert.doesNotMatch(SQL, /\bDROP TABLE\b/i);
  assert.doesNotMatch(SQL, /\bALTER TABLE public\.lm_(users|wake_log|mental_send_log)\b/i);
});

test("one scan per user per UTC day is a database fact, not an in-memory counter", () => {
  assert.match(SQL, /UNIQUE\s*\(\s*uid\s*,\s*scan_day\s*\)/i);
  assert.match(SQL, /scan_day date NOT NULL/i);
});

test("scan facts are append-only; only the 11b chain columns may be filled in later", () => {
  assert.match(SQL, /BEFORE UPDATE OR DELETE ON public\.lm_care_scan_log/i);
  assert.match(SQL, /lm_care_scan_log is append-only/i);
  assert.match(SQL, /NEW\.detections IS DISTINCT FROM OLD\.detections/i);
  assert.match(SQL, /REVOKE DELETE ON TABLE public\.lm_care_scan_log FROM service_role/i);
});

test("detections are structured jsonb with an honest empty default (abstention rows)", () => {
  assert.match(SQL, /detections jsonb NOT NULL DEFAULT '\[\]'::jsonb/i);
  assert.match(SQL, /history_event_count integer NOT NULL/i);
  assert.match(SQL, /chain jsonb/i);
  assert.match(SQL, /chain_error text/i);
});

test("the table is service-only and holds nothing secret", () => {
  assert.match(SQL, /ENABLE ROW LEVEL SECURITY/i);
  assert.match(SQL, /REVOKE ALL ON TABLE public\.lm_care_scan_log FROM PUBLIC, anon, authenticated/i);
  assert.doesNotMatch(SQL, /\b(home_address|phone|email|private_key|secret)\b/i);
});
