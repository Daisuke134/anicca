"use strict";

const DATE = /^\d{4}-\d{2}-\d{2}$/;
const RECEIPT = /^provider-receipt:\/\/(luma|connpass)\/[A-Za-z0-9._:~-]+$/;
const COVERED = new Set(["covered_existing", "covered_new", "unavailable"]);

function addDays(date, count) {
  const [year, month, day] = date.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day + count)).toISOString().slice(0, 10);
}

function validateCoverage(coverage) {
  if (!coverage || coverage.schema_version !== 1 || !Array.isArray(coverage.days) || coverage.days.length !== 21) {
    throw new Error("event coverage round invalid");
  }
  let openCount = 0;
  for (let index = 0; index < coverage.days.length; index += 1) {
    const day = coverage.days[index];
    if (!day || !DATE.test(String(day.date || "")) || (index > 0 && day.date !== addDays(coverage.days[index - 1].date, 1))) {
      throw new Error("event coverage day invalid");
    }
    if (day.status === "open") {
      if (day.evidence_ref != null) throw new Error("event coverage open evidence invalid");
      openCount += 1;
    } else if (!COVERED.has(day.status) || typeof day.evidence_ref !== "string" || !day.evidence_ref.includes("://")) {
      throw new Error("event coverage status invalid");
    }
  }
  if (
    coverage.window_start !== coverage.days[0].date
    || coverage.window_end !== coverage.days.at(-1).date
    || coverage.open_count !== openCount
    || coverage.complete !== (openCount === 0)
  ) {
    throw new Error("event coverage summary invalid");
  }
  return openCount;
}

async function runEventCoverageRound(options = {}) {
  const coverage = options.coverage;
  const runDay = options.runDay;
  const initialOpenCount = validateCoverage(coverage);
  if (typeof runDay !== "function") throw new Error("event coverage runner invalid");

  const bookedDays = [];
  const openDays = [];
  let processedCount = 0;
  for (const day of coverage.days) {
    if (day.status !== "open") continue;
    processedCount += 1;
    let result;
    try {
      result = await runDay(Object.freeze({ date: day.date }));
    } catch {
      openDays.push(Object.freeze({ date: day.date, reason: "operation_failure" }));
      continue;
    }
    const status = String(result && result.status || "").trim();
    const receiptRef = String(result && result.receipt_ref || "").trim();
    const provider = String(result && result.provider || "").trim();
    const receipt = RECEIPT.exec(receiptRef);
    if (
      status === "booked"
      && result.date === day.date
      && receipt
      && provider === receipt[1]
    ) {
      bookedDays.push(Object.freeze({
        date: day.date,
        provider,
        receipt_ref: receiptRef,
      }));
      continue;
    }
    const reason = ["coverage_open", "recovery_required", "reconciliation_required"].includes(status)
      ? String(result.reason || status)
      : "unverified_result";
    openDays.push(Object.freeze({ date: day.date, reason }));
  }

  const remainingOpenCount = initialOpenCount - bookedDays.length;
  return Object.freeze({
    status: remainingOpenCount === 0 ? "complete" : "continue_required",
    window_start: coverage.window_start,
    window_end: coverage.window_end,
    round_completed: true,
    processed_count: processedCount,
    booked_count: bookedDays.length,
    remaining_open_count: remainingOpenCount,
    next_run_required: remainingOpenCount > 0,
    booked_days: Object.freeze(bookedDays),
    open_days: Object.freeze(openDays),
  });
}

module.exports = { runEventCoverageRound };
