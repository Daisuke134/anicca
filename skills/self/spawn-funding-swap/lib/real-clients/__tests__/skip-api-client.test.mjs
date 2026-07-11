// VCSDD spawn-funding-swap Phase 2a (sprint-2, RED). PROP-037/PROP-038 — lib/real-clients/skip-api-client.mjs.
// fetchImpl is always mocked (NFR-6). Written against a file that does NOT exist yet -- every test below
// MUST fail (module-not-found) until Phase 2b.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRealSkipApiClient } from "../skip-api-client.mjs";

// Mirrors the live-shaped response captured 2026-07-11 (field names only; values illustrative).
const LIVE_SHAPED_RESPONSE = { dest_asset_denom: "uakt", dest_asset_chain_id: "akashnet-2", amount_out: "24513647", txs_required: 2, chain_ids: ["8453", "noble-1", "osmosis-1", "akashnet-2"] };

test("PROP-037: getRoute coerces amount_in/chain_id fields to JSON strings regardless of the input type (driver.mjs passes a JS number for chain ids)", async () => {
  let capturedBody;
  const client = createRealSkipApiClient({
    fetchImpl: async (url, init) => {
      capturedBody = JSON.parse(init.body);
      return { ok: true, json: async () => LIVE_SHAPED_RESPONSE };
    },
  });
  await client.getRoute({ amount_in: 15_000_000n, source_asset_chain_id: 8453, source_asset_denom: "0xUSDC", dest_asset_chain_id: "akashnet-2", dest_asset_denom: "uakt" });
  assert.equal(capturedBody.amount_in, "15000000");
  assert.equal(typeof capturedBody.source_asset_chain_id, "string");
  assert.equal(capturedBody.source_asset_chain_id, "8453");
  assert.equal(typeof capturedBody.dest_asset_chain_id, "string");
  assert.equal(capturedBody.allow_multi_tx, true);
});

test("PROP-037: getRoute returns the parsed response body unmodified (field names already match validateRoute's contract)", async () => {
  const client = createRealSkipApiClient({ fetchImpl: async () => ({ ok: true, json: async () => LIVE_SHAPED_RESPONSE }) });
  const result = await client.getRoute({ amount_in: 1n, source_asset_chain_id: 8453, source_asset_denom: "0xUSDC", dest_asset_chain_id: "akashnet-2", dest_asset_denom: "uakt" });
  assert.deepEqual(result, LIVE_SHAPED_RESPONSE);
});

test("PROP-038: getRoute throws on a non-2xx HTTP response", async () => {
  const client = createRealSkipApiClient({ fetchImpl: async () => ({ ok: false, status: 500, json: async () => ({}) }) });
  await assert.rejects(() => client.getRoute({ amount_in: 1n, source_asset_chain_id: 8453, source_asset_denom: "0xUSDC", dest_asset_chain_id: "akashnet-2", dest_asset_denom: "uakt" }));
});

test("PROP-038: getRoute throws when the response body carries Skip's own error `code` field (e.g. 'no single-tx routes found')", async () => {
  const client = createRealSkipApiClient({ fetchImpl: async () => ({ ok: true, json: async () => ({ code: 5, message: "no single-tx routes found" }) }) });
  await assert.rejects(() => client.getRoute({ amount_in: 1n, source_asset_chain_id: 8453, source_asset_denom: "0xUSDC", dest_asset_chain_id: "akashnet-2", dest_asset_denom: "uakt" }));
});

test("PROP-038: getRoute throws on unparseable JSON", async () => {
  const client = createRealSkipApiClient({ fetchImpl: async () => ({ ok: true, json: async () => { throw new Error("bad json"); } }) });
  await assert.rejects(() => client.getRoute({ amount_in: 1n, source_asset_chain_id: 8453, source_asset_denom: "0xUSDC", dest_asset_chain_id: "akashnet-2", dest_asset_denom: "uakt" }));
});
