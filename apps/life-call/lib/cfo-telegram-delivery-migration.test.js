"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");

const migrationPath = path.join(__dirname, "..", "migrations", "2026-08-09-cfo-telegram-deliveries.sql");

function functionBody(sql, signature) {
  const start = sql.indexOf(signature);
  const end = sql.indexOf("\nREVOKE ALL ON FUNCTION", start);
  assert.ok(start >= 0 && end > start, `${signature} must have a closed definition`);
  return sql.slice(start, end);
}

function projectionKeys(fnBody) {
  const projections = [...fnBody.matchAll(/jsonb_build_object\(([\s\S]*?)\)\s*;/gi)].map((match) => match[1]);
  assert.equal(projections.length, 1, "each function must return exactly one closed projection");
  return projections[0];
}

test("Telegram delivery migration creates append-only claim/receipt tables with composite snapshot linkage", () => {
  const sql = fs.readFileSync(migrationPath, "utf8");

  assert.match(
    sql,
    /ALTER TABLE public\.lm_cfo_daily_snapshots\s+ADD CONSTRAINT \S+\s+UNIQUE \(uid, reporting_date, revision, public_ref\)/i,
  );
  [
    /CREATE TABLE IF NOT EXISTS public\.lm_cfo_telegram_delivery_claims/i,
    /CREATE TABLE IF NOT EXISTS public\.lm_cfo_telegram_delivery_receipts/i,
    /public_ref\s+uuid\s+NOT NULL\s+DEFAULT\s+gen_random_uuid\(\).*00000000-0000-0000-0000-000000000000/is,
    /UNIQUE\s*\(uid,\s*report_kind,\s*reporting_date,\s*revision\)/i,
    /FOREIGN KEY \(uid, reporting_date, revision, snapshot_public_ref\)\s*\n?\s*REFERENCES public\.lm_cfo_daily_snapshots \(uid, reporting_date, revision, public_ref\)/i,
    /claim_public_ref\s+uuid\s+NOT NULL\s+UNIQUE\s+REFERENCES public\.lm_cfo_telegram_delivery_claims\s*\(public_ref\)/i,
    /message_id\s+bigint\s+NOT NULL\s+CHECK\s*\(message_id\s*>\s*0\)/i,
    /BEFORE UPDATE OR DELETE ON public\.lm_cfo_telegram_delivery_claims/i,
    /BEFORE UPDATE OR DELETE ON public\.lm_cfo_telegram_delivery_receipts/i,
    /SECURITY INVOKER/i,
    /SET search_path\s*=\s*public,\s*pg_temp/i,
  ].forEach((pattern) => assert.match(sql, pattern));

  ["lm_cfo_telegram_delivery_claims", "lm_cfo_telegram_delivery_receipts"].forEach((table) => {
    assert.match(sql, new RegExp(`ALTER TABLE public\\.${table} ENABLE ROW LEVEL SECURITY`, "i"));
    assert.match(sql, new RegExp(`CREATE POLICY \\S+ ON public\\.${table} FOR SELECT TO service_role USING \\(true\\)`, "i"));
    assert.match(sql, new RegExp(`CREATE POLICY \\S+ ON public\\.${table} FOR INSERT TO service_role WITH CHECK \\(true\\)`, "i"));
    assert.match(sql, new RegExp(`REVOKE ALL ON TABLE public\\.${table} FROM PUBLIC, anon, authenticated`, "i"));
    assert.match(sql, new RegExp(`GRANT SELECT, INSERT ON TABLE public\\.${table} TO service_role`, "i"));
    assert.match(sql, new RegExp(`REVOKE UPDATE, DELETE ON TABLE public\\.${table} FROM service_role`, "i"));
  });

  assert.match(
    sql,
    /lm_claim_cfo_telegram_delivery\(\s*p_uid text, p_snapshot_public_ref uuid, p_report_kind text, p_reporting_date date, p_revision integer\s*\)/i,
  );
  assert.match(sql, /REVOKE ALL ON FUNCTION public\.lm_claim_cfo_telegram_delivery\(text, uuid, text, date, integer\) FROM PUBLIC, anon, authenticated/i);
  assert.match(sql, /GRANT EXECUTE ON FUNCTION public\.lm_claim_cfo_telegram_delivery\(text, uuid, text, date, integer\) TO service_role/i);
  assert.match(sql, /REVOKE ALL ON FUNCTION public\.lm_record_cfo_telegram_delivery\(uuid, bigint\) FROM PUBLIC, anon, authenticated/i);
  assert.match(sql, /GRANT EXECUTE ON FUNCTION public\.lm_record_cfo_telegram_delivery\(uuid, bigint\) TO service_role/i);

  assert.doesNotMatch(sql, /chat_id|message_text|token|balance|report_payload|source_bundle/i);
});

test("claim RPC decisions are exactly send, sent, reconcile with insert attempted before conflict lookup", () => {
  const sql = fs.readFileSync(migrationPath, "utf8");
  const claim = functionBody(sql, "CREATE OR REPLACE FUNCTION public.lm_claim_cfo_telegram_delivery");

  assert.match(claim, /decision\s*:=\s*'send'/i);
  assert.match(claim, /decision\s*:=\s*'sent'/i);
  assert.match(claim, /decision\s*:=\s*'reconcile'/i);
  assert.doesNotMatch(claim, /\bUPDATE\s+\S+\s+SET\b/i);

  const insertAt = claim.indexOf("INSERT INTO public.lm_cfo_telegram_delivery_claims");
  const conflictSelectAt = claim.indexOf("SELECT * INTO claimed FROM public.lm_cfo_telegram_delivery_claims");
  assert.ok(insertAt >= 0 && conflictSelectAt > insertAt, "insert attempt precedes conflict lookup");

  const receiptCheckAt = claim.indexOf("lm_cfo_telegram_delivery_receipts");
  assert.ok(receiptCheckAt > conflictSelectAt, "receipt existence decides sent vs reconcile only after conflict lookup");

  const keys = [...projectionKeys(claim).matchAll(/'([a-z_]+)'\s*,/gi)].map((match) => match[1]);
  assert.deepEqual(keys, ["public_ref", "decision", "reporting_date", "revision", "created_at"]);
  assert.doesNotMatch(projectionKeys(claim), /\b(?:uid|report_kind|snapshot_public_ref)\b/i);
});

test("record RPC requires a positive message id, is idempotent on retry, and conflicts on a changed id", () => {
  const sql = fs.readFileSync(migrationPath, "utf8");
  const record = functionBody(sql, "CREATE OR REPLACE FUNCTION public.lm_record_cfo_telegram_delivery");

  assert.match(record, /p_message_id\s+IS NULL\s+OR\s+p_message_id\s*<=\s*0/i);
  assert.match(record, /ON CONFLICT DO NOTHING/i);
  assert.match(record, /IS DISTINCT FROM p_message_id/i);
  assert.match(record, /RAISE EXCEPTION 'provider_receipt_conflict'/i);
  assert.doesNotMatch(record, /\bUPDATE\s+\S+\s+SET\b/i);

  const keys = [...projectionKeys(record).matchAll(/'([a-z_]+)'\s*,/gi)].map((match) => match[1]);
  assert.deepEqual(keys, ["public_ref", "claim_public_ref", "message_id", "created_at"]);
});
