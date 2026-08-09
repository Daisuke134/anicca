"use strict";

const { validateCfoRecoverySnapshotBundle } = require("./cfo-recovery-snapshot.js");
const { createCfoSupabaseRpc } = require("./cfo-supabase-rpc.js");

const ERROR_PREFIX = "cfo_snapshot_revision_store_failed:";
const INPUT_KEYS = new Set(["uid", "reportingDate", "runId", "revision", "supersedesRevision", "report", "sourceBundle"]);
const RECEIPT_KEYS = new Set(["public_ref", "reporting_date", "run_id", "revision", "supersedes_revision", "created_at"]);

const { runOperation, fail, internal, exact, validDate, uuid, timestamp, validateOptions, freeze, postRpc } = createCfoSupabaseRpc(ERROR_PREFIX);

function validateInput(input) {
  exact(input, INPUT_KEYS);
  if (typeof input.uid !== "string" || input.uid.length === 0 || input.uid.length > 255 || input.uid.trim() !== input.uid || /[\u0000-\u001f\u007f]/.test(input.uid)) fail("invalid_uid");
  if (!validDate(input.reportingDate)) fail("invalid_date");
  const runId = uuid(input.runId, "invalid_run_id");
  if (!Number.isSafeInteger(input.revision) || input.revision < 2) fail("invalid_revision");
  if (!Number.isSafeInteger(input.supersedesRevision) || input.supersedesRevision !== input.revision - 1) fail("invalid_predecessor");
  return { uid: input.uid, reportingDate: input.reportingDate, runId, revision: input.revision, supersedesRevision: input.supersedesRevision };
}

function validateReceipt(value, expected) {
  exact(value, RECEIPT_KEYS, "invalid_receipt");
  uuid(value.public_ref, "invalid_receipt");
  if (value.reporting_date !== expected.reportingDate || value.run_id !== expected.runId) fail("receipt_mismatch");
  if (value.revision !== expected.revision || value.supersedes_revision !== expected.supersedesRevision) fail("receipt_mismatch");
  if (!timestamp(value.created_at)) fail("invalid_receipt");
  let clone;
  try { clone = structuredClone(value); } catch { fail("invalid_receipt"); }
  return freeze(clone);
}

async function appendCfoDailySnapshotRevision(input, opts = {}) {
  return runOperation(async () => {
    let identity, config, bundle;
    try {
      identity = validateInput(input);
      config = validateOptions(opts);
      bundle = validateCfoRecoverySnapshotBundle({ report: input.report, sourceBundle: input.sourceBundle });
      if (bundle.report.revision !== identity.revision || bundle.report.reportingDate !== identity.reportingDate) fail("bundle_identity_mismatch");
    } catch (error) {
      if (internal(error)) throw error;
      fail("invalid_input");
    }
    const parsed = await postRpc(config, "lm_append_cfo_daily_snapshot_revision", {
      p_uid: identity.uid, p_reporting_date: identity.reportingDate, p_run_id: identity.runId,
      p_revision: identity.revision, p_supersedes_revision: identity.supersedesRevision,
      p_report_payload: bundle.report, p_source_bundle: bundle.sourceBundle,
    });
    try { return validateReceipt(parsed, identity); } catch (error) {
      if (internal(error)) throw error;
      fail("invalid_receipt");
    }
  });
}

module.exports = { appendCfoDailySnapshotRevision };
