"use strict";

const { isProxy } = require("node:util").types;
const { validateFinancialSourceResult } = require("./cfo-financial-source.js");
const { composeMoneytreeRead, deriveMoneytreeState } = require("./cfo-moneytree-state.js");
const { buildCfoDailyReport } = require("./cfo-daily-snapshot.js");

const ERROR_PREFIX = "cfo_recovery_snapshot_invalid:";
const RECOVERY_KEYS = new Set(["reportingDate", "observedAt", "status", "attempts", "failureKind", "moneytreeRead", "repair", "action"]);
const ATTEMPTS_KEYS = new Set(["reads", "repairs", "waits"]);
const REPAIR_KEYS = new Set(["sourceLabel", "freshReread", "reconciled"]);
const ACTION_KEYS = new Set(["kind", "sourceLabel", "nextRetryAt"]);
const ACTION_KINDS = new Set(["reconsent", "provider_outage"]);
const REPORT_KEYS = new Set(["schemaVersion", "reportingDate", "revision", "state", "currency", "totals", "sources", "excluded", "repair", "action"]);
const TOTAL_KEYS = new Set(["assetsMinor", "liabilitiesMinor", "netWorthMinor", "changeMinor"]);
const RENDERED_SOURCE_KEYS = new Set(["sourceId", "label", "status", "asOf", "amountMinor", "verificationStatus"]);
const EXCLUDED_KEYS = new Set(["label", "reason"]);
const REPORT_ACTION_KEYS = new Set(["kind", "sourceLabel", "retryLabel", "nextRetryAt"]);
const FAILURE_KINDS = new Set(["unauthorized", "forbidden", "expired", "revoked", "timeout", "network", "rate_limited", "provider_5xx", "provider_outage"]);
const RFC3339 = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})$/;

function fail(reason) { throw new Error(`${ERROR_PREFIX}${reason}`); }
function plain(value) { return value !== null && typeof value === "object" && !Array.isArray(value) && !isProxy(value) && Object.getPrototypeOf(value) === Object.prototype; }
function exact(value, allowed) {
  if (!plain(value)) fail("invalid_shape");
  const keys = Reflect.ownKeys(value);
  if (keys.length !== allowed.size || keys.some((key) => typeof key !== "string" || !allowed.has(key))) fail("invalid_keys");
  for (const key of keys) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (!descriptor || !Object.prototype.hasOwnProperty.call(descriptor, "value") || !descriptor.enumerable) fail("invalid_shape");
  }
}
function timestamp(value) { if (typeof value !== "string" || !RFC3339.test(value) || !Number.isFinite(Date.parse(value))) fail("invalid_timestamp"); }
function date(value) { if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value) || new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) !== value) fail("invalid_date"); }
function cloneFreeze(value) {
  let clone; try { clone = structuredClone(value); } catch { fail("invalid_value"); }
  const freeze = (item, seen = new WeakSet()) => {
    if (item === null || typeof item !== "object" || seen.has(item)) return;
    seen.add(item); Reflect.ownKeys(item).forEach((key) => freeze(item[key], seen)); Object.freeze(item);
  };
  freeze(clone); return clone;
}
function validateRecovery(recovery) {
  exact(recovery, RECOVERY_KEYS); date(recovery.reportingDate); timestamp(recovery.observedAt);
  if (!["fresh", "recovered", "action_required"].includes(recovery.status)) fail("invalid_status");
  exact(recovery.attempts, ATTEMPTS_KEYS);
  if (!Number.isSafeInteger(recovery.attempts.reads) || recovery.attempts.reads < 1 || !Number.isSafeInteger(recovery.attempts.repairs) || recovery.attempts.repairs < 0 || !Array.isArray(recovery.attempts.waits)) fail("invalid_attempts");
  if (recovery.attempts.waits.some((value) => !Number.isSafeInteger(value) || value < 0)) fail("invalid_attempts");
  if (recovery.failureKind !== null && (!FAILURE_KINDS.has(recovery.failureKind) || typeof recovery.failureKind !== "string")) fail("invalid_failure");
  if (recovery.status === "action_required") {
    if (recovery.moneytreeRead !== null || recovery.repair !== null) fail("unresolved_recovery");
    exact(recovery.action, ACTION_KEYS); if (!ACTION_KINDS.has(recovery.action.kind) || recovery.action.sourceLabel !== "Moneytree") fail("invalid_action"); timestamp(recovery.action.nextRetryAt);
    const reconsentFailure = new Set(["unauthorized", "expired", "forbidden", "revoked"]);
    const outageFailure = new Set(["timeout", "network", "rate_limited", "provider_5xx", "provider_outage"]);
    if (recovery.failureKind === null || (reconsentFailure.has(recovery.failureKind) && recovery.action.kind !== "reconsent") || (outageFailure.has(recovery.failureKind) && recovery.action.kind !== "provider_outage")) fail("action_failure_mismatch");
  } else {
    if (!plain(recovery.moneytreeRead) || recovery.action !== null) fail("missing_read");
    let read;
    try { read = composeMoneytreeRead({ source: recovery.moneytreeRead.source, state: recovery.moneytreeRead.state }); } catch { fail("invalid_read"); }
    if (read.source.asOf !== recovery.observedAt || read.state.observedAt !== recovery.observedAt) fail("observed_at_mismatch");
    if (recovery.status === "fresh" && recovery.repair !== null) fail("unexpected_repair");
    if (recovery.status === "recovered") {
      exact(recovery.repair, REPAIR_KEYS); if (recovery.repair.sourceLabel !== "Moneytree" || recovery.repair.freshReread !== true || recovery.repair.reconciled !== true) fail("unproven_recovery");
      if (recovery.failureKind !== null || recovery.attempts.reads < 2) fail("unproven_recovery");
    }
  }
}
function consentFor(recovery) {
  if (recovery.action.kind === "provider_outage") return "unknown";
  return ["unauthorized", "expired"].includes(recovery.failureKind) ? "expired" : "revoked";
}
function actionSource(recovery) {
  const consent = consentFor(recovery);
  const source = validateFinancialSourceResult({ schemaVersion: 1, sourceId: "moneytree_mufg", consent, freshness: "unavailable", asOf: recovery.observedAt, accounts: [], liabilities: [], evidenceRef: "evidence:moneytree_unavailable", partial: true, actionRequired: { kind: recovery.action.kind, sourceLabel: "Moneytree", actionRef: recovery.action.kind === "reconsent" ? "action:moneytree_reconsent" : "action:moneytree_outage" } });
  const state = deriveMoneytreeState({ signal: recovery.action.kind === "reconsent" ? (consent === "expired" ? "expired" : "revoked") : "provider_outage", observedAt: recovery.observedAt, aggregationAsOf: null, aggregationFreshnessCutoff: null, liabilitiesExposed: false, liabilityCount: null });
  return composeMoneytreeRead({ source, state });
}
function reportWithRevision(report, revision) { return { ...report, revision }; }
function buildCfoDailyReportFromRecovery(input) {
  try {
    exact(input, new Set(["revision", "recovery"]));
    if (!Number.isSafeInteger(input.revision) || input.revision < 1) fail("invalid_revision");
    validateRecovery(input.recovery);
    const recovery = input.recovery;
    let report; let sourceBundle;
    if (recovery.status === "action_required") {
      sourceBundle = actionSource(recovery);
      report = { schemaVersion: 1, reportingDate: recovery.reportingDate, revision: input.revision, state: "action_required", currency: "JPY", totals: { assetsMinor: null, liabilitiesMinor: null, netWorthMinor: null, changeMinor: null }, sources: [{ sourceId: "moneytree_mufg", label: "MUFG", status: "unavailable", asOf: recovery.observedAt, amountMinor: null, verificationStatus: "unavailable" }], excluded: [{ label: "資産", reason: "Moneytreeから取得できません" }], repair: null, action: { kind: recovery.action.kind, sourceLabel: "Moneytree", retryLabel: recovery.action.kind === "reconsent" ? "Moneytreeを再接続してください" : "30分後に自動再試行します", nextRetryAt: recovery.action.nextRetryAt } };
    } else {
      sourceBundle = composeMoneytreeRead({ source: recovery.moneytreeRead.source, state: recovery.moneytreeRead.state });
      report = reportWithRevision(buildCfoDailyReport({ reportingDate: recovery.reportingDate, moneytreeRead: sourceBundle }), input.revision);
      if (recovery.status === "recovered") report = { ...report, state: "recovered", repair: { sourceLabel: "Moneytree", freshReread: true, reconciled: true } };
    }
    return validateCfoRecoverySnapshotBundle({ report, sourceBundle });
  } catch (error) { if (error && error.message && error.message.startsWith(ERROR_PREFIX)) throw error; throw new Error(`${ERROR_PREFIX}invalid_input`); }
}
function validateCfoRecoverySnapshotBundle(input) {
  try {
    exact(input, new Set(["report", "sourceBundle"]));
    const sourceBundle = composeMoneytreeRead({ source: input.sourceBundle.source, state: input.sourceBundle.state });
    const report = input.report;
    exact(report, REPORT_KEYS); exact(report.totals, TOTAL_KEYS);
    if (!Array.isArray(report.sources) || report.sources.length !== 1 || !Array.isArray(report.excluded)) fail("invalid_report");
    exact(report.sources[0], RENDERED_SOURCE_KEYS);
    for (const excluded of report.excluded) { exact(excluded, EXCLUDED_KEYS); if (typeof excluded.label !== "string" || typeof excluded.reason !== "string") fail("invalid_report"); }
    if (report.schemaVersion !== 1 || report.currency !== "JPY" || report.reportingDate !== sourceBundle.source.asOf.slice(0, 10)) fail("mismatched_identity");
    if (!Number.isSafeInteger(report.revision) || report.revision < 1) fail("invalid_revision");
    const renderedSource = report.sources[0];
    if (renderedSource.sourceId !== sourceBundle.source.sourceId || renderedSource.asOf !== sourceBundle.source.asOf || renderedSource.amountMinor !== (sourceBundle.source.accounts.reduce((sum, account) => sum + (account.balanceMinor || 0), 0) || null)) fail("stale_amount");
    if (report.totals.assetsMinor !== renderedSource.amountMinor || report.totals.liabilitiesMinor !== null || report.totals.changeMinor !== null) fail("stale_amount");
    if (report.state === "action_required") {
      exact(report.action, REPORT_ACTION_KEYS);
      if (!ACTION_KINDS.has(report.action.kind) || report.action.sourceLabel !== "Moneytree" || typeof report.action.retryLabel !== "string") fail("unsafe_action_report");
      timestamp(report.action.nextRetryAt);
      const source = sourceBundle.source; const state = sourceBundle.state;
      if (source.freshness !== "unavailable" || source.evidenceRef !== "evidence:moneytree_unavailable" || source.accounts.length !== 0 || source.liabilities.length !== 0 || source.partial !== true || source.asOf !== state.observedAt || state.retrievalStatus !== "unavailable" || state.aggregationStatus !== "unknown" || state.liabilityCoverage !== "unknown" || state.partial !== true || !state.actionRequired || state.actionRequired.kind !== report.action.kind || source.actionRequired.kind !== report.action.kind || source.actionRequired.sourceLabel !== "Moneytree" || (report.action.kind === "provider_outage" ? source.consent !== "unknown" || state.consentStatus !== "unknown" : !["expired", "revoked"].includes(source.consent) || state.consentStatus !== source.consent) || report.repair !== null || Object.values(report.totals).some((value) => value !== null) || renderedSource.label !== "MUFG" || renderedSource.status !== "unavailable" || renderedSource.amountMinor !== null || renderedSource.verificationStatus !== "unavailable") fail("unsafe_action_report");
    } else if (report.state === "partial" || report.state === "recovered") {
      const source = sourceBundle.source; const state = sourceBundle.state;
      if (source.freshness !== "fresh" || source.consent !== "valid" || source.partial !== true || source.liabilities.length !== 0 || state.observedAt !== source.asOf || state.retrievalStatus !== "succeeded" || state.consentStatus !== "valid" || state.actionRequired !== null || report.action !== null || report.totals.liabilitiesMinor !== null || report.totals.netWorthMinor !== null || report.totals.changeMinor !== null || renderedSource.label !== "MUFG" || renderedSource.status !== "fresh" || renderedSource.verificationStatus !== "provider_reported") fail("unsafe_report_state");
      if (report.state === "partial" && report.repair !== null) fail("partial_repair_forbidden");
      if (report.state === "recovered") { exact(report.repair, REPAIR_KEYS); if (report.repair.sourceLabel !== "Moneytree" || report.repair.freshReread !== true || report.repair.reconciled !== true) fail("unproven_recovery"); }
    } else fail("invalid_state");
    if (report.state !== "action_required" && report.sources[0].asOf !== sourceBundle.source.asOf) fail("mismatched_time");
    return cloneFreeze({ report, sourceBundle });
  } catch (error) { if (error && error.message && error.message.startsWith(ERROR_PREFIX)) throw error; throw new Error(`${ERROR_PREFIX}invalid_bundle`); }
}

module.exports = { buildCfoDailyReportFromRecovery, validateCfoRecoverySnapshotBundle };
