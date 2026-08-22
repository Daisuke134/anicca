const test = require("node:test");
const assert = require("node:assert/strict");
const { makeEntryHandler } = require("../marketing-entry");

test("persists only reduced X source and exact placement", async () => {
  const rows = [];
  const handler = makeEntryHandler({ persist: async (row) => rows.push(row),
    receiptId: () => "entry-1", now: () => "2026-08-22T00:00:00Z" });
  const placement = "elevenlabs-discovered-voice-changer-en-1";
  assert.equal((await handler({ httpMethod: "POST", body: JSON.stringify({ placement_id: placement, source: "X" }) })).statusCode, 204);
  assert.deepEqual(rows[0], { schema_version: 1, receipt_id: "entry-1", campaign_token: "entry_x",
    product_id: `entry:${placement}`, clicked_at: "2026-08-22T00:00:00Z" });
  assert.equal(JSON.stringify(rows[0]).includes("referrer"), false);
  assert.equal((await handler({ httpMethod: "POST", body: JSON.stringify({ placement_id: placement, source: "UNKNOWN" }) })).statusCode, 400);
  assert.equal(rows.length, 1);
});
// AFFILIATE_ENTRY_V1
