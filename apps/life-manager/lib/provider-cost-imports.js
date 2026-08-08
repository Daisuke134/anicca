"use strict";

const {
  recordTelnyxCdr,
  recordRailwayAllocation,
  recordSupabaseAllocation,
} = require("./provider-cost-adapters.js");

function idFor(provider, row, index, prefix) {
  const id = row && (row.id || row.requestId || row.request_id || row.period || row.period_key);
  return `${prefix || provider}:${id == null ? index : String(id)}`;
}

function durationFor(row) {
  return row && (row.durationSeconds ?? row.duration_seconds ?? row.billed_duration ?? row.duration ?? 0);
}

async function importRows(rows, importer, options = {}) {
  if (!Array.isArray(rows)) return { attempted: 0, recorded: 0, failed: 1, error: "measurement rows must be an array" };
  let recorded = 0;
  let failed = 0;
  for (let index = 0; index < rows.length; index++) {
    try {
      const ok = await importer(rows[index], index);
      if (ok) recorded++;
      else failed++;
    } catch {
      failed++;
    }
  }
  return { attempted: rows.length, recorded, failed };
}

async function importTelnyxCdrs(rows, options = {}) {
  return importRows(rows, (row, index) => recordTelnyxCdr({
    uid: row && row.uid != null ? row.uid : options.uid,
    requestId: row && (row.requestId || row.request_id) || idFor("telnyx", row, index, options.requestIdPrefix),
    durationSeconds: durationFor(row), cdr: row, metadata: options.metadata,
  }, options), options);
}

function allocationInput(provider, row, index, options) {
  return {
    uid: row && row.uid != null ? row.uid : options.uid,
    requestId: row && (row.requestId || row.request_id) || idFor(provider, row, index, options.requestIdPrefix),
    amountUsd: row && (row.amountUsd ?? row.amount_usd ?? row.costUsd ?? row.cost_usd ?? row.amount),
    estimatedUsd: row && (row.estimatedUsd ?? row.estimated_usd),
    quantity: row && row.quantity,
    unit: row && row.unit,
    period: row && (row.period || row.period_key || row.date),
    sku: row && row.sku,
    metadata: { ...(options.metadata || {}), ...(row && row.metadata && typeof row.metadata === "object" ? row.metadata : {}) },
  };
}

async function importRailwayAllocations(rows, options = {}) {
  return importRows(rows, (row, index) => recordRailwayAllocation(allocationInput("railway", row, index, options), options), options);
}

async function importSupabaseAllocations(rows, options = {}) {
  return importRows(rows, (row, index) => recordSupabaseAllocation(allocationInput("supabase", row, index, options), options), options);
}

async function importScheduledMeasurements(provider, loadRows, options = {}) {
  let rows;
  try {
    rows = await loadRows();
  } catch (error) {
    return { attempted: 0, recorded: 0, failed: 1, error: String(error && error.message ? error.message : error) };
  }
  if (provider === "telnyx") return importTelnyxCdrs(rows, options);
  if (provider === "railway") return importRailwayAllocations(rows, options);
  if (provider === "supabase") return importSupabaseAllocations(rows, options);
  return { attempted: 0, recorded: 0, failed: 1, error: `unsupported measurement provider: ${String(provider)}` };
}

module.exports = {
  importTelnyxCdrs,
  importRailwayAllocations,
  importSupabaseAllocations,
  importScheduledMeasurements,
};
