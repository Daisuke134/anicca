"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  parseArgs,
  readHonneJaShadowStatus,
} = require("./honne-ja-shadow-status.js");

const VIDEO_HASH = "a".repeat(64);
const COPY_HASH = "b".repeat(64);

// Expected-slot grid rows: 12:30/21:30 JST = 03:30Z/12:30Z. Tests pin the wall
// clock via deps.nowMs so slot-grid gap detection is deterministic.
const NOW_MS = Date.parse("2026-07-30T05:00:00.000Z"); // 14:00 JST

function slotReceiptRow(slot) {
  return {
    outcome: "completed",
    created_at: new Date(Date.parse(slot) + 2000).toISOString(),
    receipt: {
      schema_version: 1,
      kind: "marketing_video_artifact",
      status: "ready",
      product_id: "honne-ai",
      format_id: "reelclaw",
      form: "relationship-confession",
      locale: "ja",
      slot,
      creative_id: "HJA-008-aaaaaaaaaaaa",
      hook_id: "HJA-008",
      hook_sha256: "e".repeat(64),
      video_ref: `object://sha256/${VIDEO_HASH}`,
      video_sha256: VIDEO_HASH,
      copy_ref: `object://sha256/${COPY_HASH}`,
      copy_sha256: COPY_HASH,
      generated_at: new Date(Date.parse(slot) + 1000).toISOString(),
    },
  };
}

test("status arguments require the status command and a tenant", () => {
  assert.throws(() => parseArgs([]), /usage/i);
  assert.throws(() => parseArgs(["status"]), /--tenant is required/);
  assert.throws(() => parseArgs(["status", "--tenant", "t", "--bogus", "x"]), /invalid/i);
  const args = parseArgs(["status", "--tenant", "dais-local"]);
  assert.equal(args.tenant, "dais-local");
  assert.equal(args.product, "honne-ai");
  assert.equal(args.format, "reelclaw");
  assert.equal(args.locale, "ja");
});

test("status reader queries the durable store scoped by job identity refs", async () => {
  const calls = [];
  let output = "";
  const result = await readHonneJaShadowStatus(["status", "--tenant", "dais-local"], {
    query: async (sql, params) => {
      calls.push({ sql, params });
      return {
        rows: [
          slotReceiptRow("2026-07-29T12:30:00.000Z"),
          slotReceiptRow("2026-07-30T03:30:00.000Z"),
        ],
      };
    },
    stdout: { write(text) { output += text; } },
    nowMs: NOW_MS,
  });

  assert.equal(calls.length, 1);
  assert.match(calls[0].sql, /j\.capability = 'marketing\.video\.generate'/);
  assert.match(calls[0].sql, /input_refs->>'product_ref'/);
  assert.match(calls[0].sql, /ORDER BY r\.created_at ASC/);
  assert.deepEqual(calls[0].params, [
    "dais-local",
    "product://honne-ai",
    "format://reelclaw",
    "locale://ja",
  ]);
  assert.equal(result.consecutive, 2);
  const printed = JSON.parse(output);
  assert.equal(printed.cycles, "2/7");
  assert.equal(printed.gate_met, false);
  assert.deepEqual(printed.missed_slots, []);
  assert.equal(printed.receipts.length, 2);
  assert.equal(printed.receipts[0].slot, "2026-07-29T12:30:00.000Z");
  assert.equal(printed.receipts[0].generated_at, "2026-07-29T12:30:01.000Z");
  assert.equal(printed.receipts[0].recorded_at, "2026-07-29T12:30:02.000Z");
});

test("a failed run between successes truncates the consecutive count", async () => {
  let output = "";
  const result = await readHonneJaShadowStatus(["status", "--tenant", "dais-local"], {
    query: async () => ({
      rows: [
        slotReceiptRow("2026-07-29T03:30:00.000Z"),
        { outcome: "failed", created_at: "2026-07-29T12:30:02.000Z", receipt: { error_code: "CAPABILITY_EXECUTION_FAILED" } },
        slotReceiptRow("2026-07-30T03:30:00.000Z"),
      ],
    }),
    stdout: { write(text) { output += text; } },
    nowMs: NOW_MS,
  });
  assert.equal(result.consecutive, 1);
  assert.equal(JSON.parse(output).cycles, "1/7");
});

test("an expected slot with no receipt row is reported missed and resets the count", async () => {
  // Receipts exist for 2026-07-29 12:30 JST and 2026-07-30 12:30 JST, but the
  // 2026-07-29 21:30 JST slot left no row at all (scheduler was down).
  let output = "";
  const result = await readHonneJaShadowStatus(["status", "--tenant", "dais-local"], {
    query: async () => ({
      rows: [
        slotReceiptRow("2026-07-29T03:30:00.000Z"),
        slotReceiptRow("2026-07-30T03:30:00.000Z"),
      ],
    }),
    stdout: { write(text) { output += text; } },
    nowMs: NOW_MS,
  });
  assert.equal(result.consecutive, 1);
  const printed = JSON.parse(output);
  assert.equal(printed.cycles, "1/7");
  assert.equal(printed.gate_met, false);
  assert.deepEqual(printed.missed_slots, ["2026-07-29T12:30:00.000Z"]);
});

test("an empty durable history prints 0/7 without failing", async () => {
  let output = "";
  await readHonneJaShadowStatus(["status", "--tenant", "dais-local"], {
    query: async () => ({ rows: [] }),
    stdout: { write(text) { output += text; } },
    nowMs: NOW_MS,
  });
  const printed = JSON.parse(output);
  assert.equal(printed.cycles, "0/7");
  assert.deepEqual(printed.receipts, []);
  assert.deepEqual(printed.missed_slots, []);
});
