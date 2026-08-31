"use strict";
// FIN-c — the production leg of the earnings ledger.
//
// This is the wiring between the earn loop and the message the user reads: revenue goes in against the
// agent wallet, and a month comes back out as the spec 9.11 report. The rule module next door owns all
// the arithmetic and all the copy; this owns only the I/O, and it is deliberately unforgiving about
// two things.
//
// Nothing invalid is written and explained afterwards. Every entry is normalised before the request
// is built, so a malformed amount fails at the caller rather than becoming a row someone has to
// reconcile later — and the table is append-only, so a bad row cannot simply be corrected.
//
// Nothing unmeasured is reported. A ledger read that failed is not an empty month, and a balance the
// chain would not give us is not zero. Both abort the report instead of being filled in with a
// plausible number, because a report is only worth sending if every figure in it was observed.

const { normaliseEntry, rollUpMonth, formatMonthlyReport, monthBounds } = require("./earnings-ledger.js");

const TABLE = "lm_agent_earnings";

function credentials(opts = {}) {
  const supaUrl = opts.supaUrl || process.env.SUPABASE_URL;
  const supaKey = opts.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY;
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  if (!supaUrl || !supaKey) throw new Error("earnings ledger needs Supabase credentials");
  if (typeof fetchImpl !== "function") throw new Error("earnings ledger needs a fetch implementation");
  return { supaUrl, supaKey, fetchImpl };
}

function headers(key, extra) {
  return Object.assign({ apikey: key, Authorization: `Bearer ${key}` }, extra || {});
}

async function recordEarnLoopRevenue(entry, opts = {}) {
  // Validation first, and outside the try: an invalid entry is a caller bug, not a transport problem,
  // and it must never reach the network.
  const row = normaliseEntry(entry);
  const { supaUrl, supaKey, fetchImpl } = credentials(opts);

  const response = await fetchImpl(`${supaUrl}/rest/v1/${TABLE}`, {
    method: "POST",
    headers: headers(supaKey, { "Content-Type": "application/json", Prefer: "return=minimal" }),
    body: JSON.stringify(row),
  });

  if (response && response.ok) return { ok: true, duplicate: false, entry_key: row.entry_key };
  // The unique constraint doing its job. The earn loop retrying a write it already made is normal;
  // treating it as new revenue would be double-counting.
  if (response && response.status === 409) return { ok: true, duplicate: true, entry_key: row.entry_key };
  throw new Error(`earnings ledger insert failed (${response ? response.status : "no response"})`);
}

async function readMonthRows(period, opts = {}) {
  const { supaUrl, supaKey, fetchImpl } = credentials(opts);
  const { startMs, endMs } = monthBounds(period);
  const query = [
    "select=*",
    `wallet_address=eq.${encodeURIComponent(String(period.walletAddress))}`,
    `occurred_at=gte.${encodeURIComponent(new Date(startMs).toISOString())}`,
    `occurred_at=lt.${encodeURIComponent(new Date(endMs).toISOString())}`,
    "order=occurred_at.asc",
  ].join("&");

  const response = await fetchImpl(`${supaUrl}/rest/v1/${TABLE}?${query}`, { headers: headers(supaKey) });
  if (!response || !response.ok) {
    throw new Error(`earnings ledger read failed (${response ? response.status : "no response"})`);
  }
  const rows = await response.json();
  return Array.isArray(rows) ? rows : [];
}

// The balance line is the one figure that does not come from our own ledger, so it has to come from a
// reader the caller supplies — in production, the chain. Anything it cannot answer stops the report.
async function measureBalance(readBalanceMinor) {
  if (typeof readBalanceMinor !== "function") {
    throw new Error("a measured wallet balance reader is required");
  }
  let value;
  try {
    value = await readBalanceMinor();
  } catch (error) {
    throw new Error(`wallet balance could not be measured: ${error && error.message ? error.message : error}`);
  }
  if (value == null) throw new Error("wallet balance could not be measured");
  return value;
}

async function generateMonthlyReport(request, opts = {}) {
  const {
    year, month, timezone, walletAddress,
    readBalanceMinor, readBalanceAtomic, balanceDecimals,
    cause, plan, currency, locale, explorerBaseUrl,
  } = request || {};
  const hasMinorReader = readBalanceMinor != null;
  const hasAtomicReader = readBalanceAtomic != null;
  if (hasMinorReader && hasAtomicReader) {
    throw new Error("supply exactly one measured wallet balance reader");
  }
  if (!hasMinorReader && !hasAtomicReader) {
    throw new Error("a measured wallet balance reader is required");
  }
  if (hasAtomicReader && balanceDecimals == null) {
    throw new Error("an atomic balance reader needs balance decimals");
  }
  const rows = await readMonthRows({ year, month, timezone, walletAddress }, opts);
  const measuredBalance = await measureBalance(hasMinorReader ? readBalanceMinor : readBalanceAtomic);
  const balanceOptions = hasMinorReader
    ? { balanceMinor: measuredBalance }
    : { balanceAtomic: measuredBalance, balanceDecimals };
  const summary = rollUpMonth(rows, {
    year, month, timezone, walletAddress, currency, explorerBaseUrl, ...balanceOptions,
  });
  return { summary, text: formatMonthlyReport(summary, { cause, plan, locale }) };
}

module.exports = { TABLE, recordEarnLoopRevenue, readMonthRows, generateMonthlyReport };
