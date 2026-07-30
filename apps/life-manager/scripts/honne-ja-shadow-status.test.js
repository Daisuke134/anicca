"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  parseArgs,
  readHonneJaShadowStatus,
} = require("./honne-ja-shadow-status.js");

const VIDEO_HASH = "a".repeat(64);
const COPY_HASH = "b".repeat(64);

function receiptRow(n) {
  return {
    outcome: "completed",
    created_at: `2026-07-2${n}T03:30:02.000Z`,
    receipt: {
      schema_version: 1,
      kind: "marketing_video_artifact",
      status: "ready",
      product_id: "honne-ai",
      format_id: "reelclaw",
      form: "relationship-confession",
      locale: "ja",
      slot: `2026-07-2${n}T03:30:00.000Z`,
      creative_id: "HJA-008-aaaaaaaaaaaa",
      hook_id: "HJA-008",
      hook_sha256: "e".repeat(64),
      video_ref: `object://sha256/${VIDEO_HASH}`,
      video_sha256: VIDEO_HASH,
      copy_ref: `object://sha256/${COPY_HASH}`,
      copy_sha256: COPY_HASH,
      generated_at: `2026-07-2${n}T03:30:01.000Z`,
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
      return { rows: [receiptRow(1), receiptRow(2)] };
    },
    stdout: { write(text) { output += text; } },
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
  assert.equal(printed.receipts.length, 2);
  assert.equal(printed.receipts[0].slot, "2026-07-21T03:30:00.000Z");
  assert.equal(printed.receipts[0].generated_at, "2026-07-21T03:30:01.000Z");
  assert.equal(printed.receipts[0].recorded_at, "2026-07-21T03:30:02.000Z");
});

test("a failed run between successes truncates the consecutive count", async () => {
  let output = "";
  const result = await readHonneJaShadowStatus(["status", "--tenant", "dais-local"], {
    query: async () => ({
      rows: [
        receiptRow(1),
        { outcome: "failed", created_at: "2026-07-22T03:30:02.000Z", receipt: { error_code: "CAPABILITY_EXECUTION_FAILED" } },
        receiptRow(3),
      ],
    }),
    stdout: { write(text) { output += text; } },
  });
  assert.equal(result.consecutive, 1);
  assert.equal(JSON.parse(output).cycles, "1/7");
});

test("an empty durable history prints 0/7 without failing", async () => {
  let output = "";
  await readHonneJaShadowStatus(["status", "--tenant", "dais-local"], {
    query: async () => ({ rows: [] }),
    stdout: { write(text) { output += text; } },
  });
  const printed = JSON.parse(output);
  assert.equal(printed.cycles, "0/7");
  assert.deepEqual(printed.receipts, []);
});
