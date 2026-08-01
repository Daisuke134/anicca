"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { buildEventCoverageMessage, deliverEventCoverageSummary } = require("./event-coverage-telegram.js");

function fixture() {
  const states = ["covered_existing", "covered_new", "unavailable", "open"];
  const days = Array.from({ length: 21 }, (_, index) => {
    const date = new Date(Date.UTC(2026, 7, 2 + index)).toISOString().slice(0, 10);
    const status = states[index] || "open";
    return { date, status, evidence_ref: status === "open" ? null : `${status === "covered_new" ? "provider-receipt://luma" : "coverage-proof://day"}/${date}` };
  });
  return {
    coverage: {
      schema_version: 1,
      window_start: days[0].date,
      window_end: days.at(-1).date,
      days,
      counts: { covered_existing: 1, covered_new: 1, unavailable: 1, open: 18 },
      open_count: 18,
      complete: false,
    },
    reservations: [{
      date: "2026-08-03",
      event_title: "Tokyo Agent Night",
      receipt_ref: "provider-receipt://luma/receipt-aug03",
      selection_reason: "Life Managerの利用者候補と東京で直接会えるためです。",
    }],
  };
}

test("one readable message contains all 21 days, counts, receipt, and selection reason", () => {
  const message = buildEventCoverageMessage(fixture());
  assert.match(message, /^📅 Life Manager イベント21日レポート/);
  assert.match(message, /既存 1｜新規 1｜参加不可 1｜残り 18/);
  assert.match(message, /Tokyo Agent Night/);
  assert.match(message, /receipt-aug03/);
  assert.match(message, /Life Managerの利用者候補/);
  assert.equal((message.match(/^.+ 8\//gm) || []).length, 21);
  assert.ok(message.length <= 4096);
  assert.doesNotMatch(message, /job_id|runner|sha256|\{\{/i);
});

test("every covered_new day requires exactly one same-day verified reservation", () => {
  const value = fixture();
  assert.throws(() => buildEventCoverageMessage({ ...value, reservations: [] }), /reservation/i);
  assert.throws(() => buildEventCoverageMessage({ ...value, reservations: [...value.reservations, value.reservations[0]] }), /reservation/i);
  assert.throws(() => buildEventCoverageMessage({ ...value, reservations: [{ ...value.reservations[0], receipt_ref: "missing" }] }), /receipt/i);
});

test("delivery sends exactly one text and persists only positive message ID plus privacy-safe summary", async () => {
  const sends = [];
  const receipt = await deliverEventCoverageSummary({
    tenantId: "dais-local", telegramTarget: "123456789", ...fixture(),
  }, {
    send: async (message, options) => { sends.push({ message, options }); return { messageId: "6006" }; },
    observedAt: () => "2026-08-01T16:50:00.000Z",
  });
  assert.equal(sends.length, 1);
  assert.equal(sends[0].options.telegramTarget, "123456789");
  assert.equal(receipt.provider_id, "6006");
  assert.equal(receipt.counts.open, 18);
  assert.doesNotMatch(JSON.stringify(receipt), /123456789|Tokyo Agent Night|利用者候補/);
});

test("missing positive message ID is not a delivered report", async () => {
  await assert.rejects(deliverEventCoverageSummary({
    tenantId: "dais-local", telegramTarget: "123456789", ...fixture(),
  }, { send: async () => ({ ok: true }) }), /positive message ID/i);
});
