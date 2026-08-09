"use strict";

const { buildCfoDailyReport } = require("./cfo-daily-snapshot.js");
const { composeMoneytreeRead } = require("./cfo-moneytree-state.js");
const { createCfoSupabaseRpc } = require("./cfo-supabase-rpc.js");

const ERROR_PREFIX = "cfo_snapshot_store_failed:";
const INPUT_KEYS = new Set(["uid", "reportingDate", "runId", "moneytreeRead"]);
const RECEIPT_KEYS = new Set(["public_ref", "reporting_date", "run_id", "revision", "created_at"]);
const SNAPSHOT_OPTION_KEYS = new Set(["supaUrl", "supaKey", "fetchImpl", "log"]);

const { fail, internal, exact, validDate, uuid, timestamp, validateOptions, freeze, postRpc } = createCfoSupabaseRpc(ERROR_PREFIX);

function validateInput(input) {
  exact(input, INPUT_KEYS);
  if (typeof input.uid !== "string" || input.uid.length === 0 || input.uid.length > 255 || input.uid.trim() !== input.uid || /[\u0000-\u001f\u007f]/.test(input.uid)) fail("invalid_uid");
  if (!validDate(input.reportingDate)) fail("invalid_date");
  return { uid: input.uid, reportingDate: input.reportingDate, runId: uuid(input.runId, "invalid_run_id") };
}
function validateReceipt(value, expected) {
  exact(value, RECEIPT_KEYS, "invalid_receipt");
  uuid(value.public_ref, "invalid_receipt");
  if (value.reporting_date !== expected.reportingDate || typeof value.reporting_date !== "string") fail("receipt_mismatch");
  if (typeof value.run_id !== "string" || value.run_id !== expected.runId) fail("receipt_mismatch");
  if (value.revision !== 1 || !timestamp(value.created_at)) fail("invalid_receipt");
  try { return freeze(structuredClone(value)); } catch { fail("invalid_receipt"); }
}

async function appendCfoDailySnapshot(input, opts = {}) {
  let identity, config;
  try { identity = validateInput(input); config = validateOptions(opts, SNAPSHOT_OPTION_KEYS); } catch (error) { if (internal(error)) throw error; fail("invalid_input"); }
  let report, sourceBundle;
  try {
    report = buildCfoDailyReport({ reportingDate: identity.reportingDate, moneytreeRead: input.moneytreeRead });
    sourceBundle = composeMoneytreeRead({ source: input.moneytreeRead.source, state: input.moneytreeRead.state });
  } catch { fail("invalid_input"); }
  const parsed = await postRpc(config, "lm_append_cfo_daily_snapshot", { p_uid: identity.uid, p_reporting_date: identity.reportingDate, p_run_id: identity.runId, p_report_payload: report, p_source_bundle: sourceBundle });
  try { return validateReceipt(parsed, identity); } catch (error) { if (internal(error)) throw error; fail("invalid_receipt"); }
}

module.exports = { appendCfoDailySnapshot };
