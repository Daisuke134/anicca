"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const {
  auditMarketingDestinationRegistry,
  findMarketingDestinationTarget,
  loadMarketingDestinationContract,
  validateMarketingDestinationContract,
} = require("./marketing-destination-contract.js");

const CONTRACT = path.resolve(__dirname, "../../../config/marketing-destinations.json");

test("the marketing destination SSOT fixes every retained route and every non-target connection", () => {
  const value = loadMarketingDestinationContract(CONTRACT);
  assert.equal(value.targets.length, 13);
  assert.equal(value.holds.filter((row) => row.integration_id).length, 17);
  assert.equal(value.holds.filter((row) => row.integration_id === null).length, 3);
  assert.ok(value.targets.every((row) => row.cadence_jst.length === 3));
  assert.deepEqual(
    value.holds.filter((row) => row.integration_id === null).map((row) => `${row.platform}:${row.postiz_profile}`).sort(),
    ["tiktok:@anicca.girl", "tiktok:@anicca.jp1", "tiktok:@anicca.videojp"],
  );
});

test("duplicate retained handles across platforms fail closed", () => {
  const value = JSON.parse(fs.readFileSync(CONTRACT, "utf8"));
  value.targets[1].native_handle = value.targets[0].native_handle;
  assert.throws(() => validateMarketingDestinationContract(value), /duplicate native handle/i);
});

test("a target without an exact pack, form, cadence, label, or entrypoint fails closed", () => {
  const value = JSON.parse(fs.readFileSync(CONTRACT, "utf8"));
  for (const field of ["approved_pack_ref", "media_form", "cadence_jst", "label", "entrypoint"]) {
    const candidate = structuredClone(value);
    delete candidate.targets[0][field];
    assert.throws(() => validateMarketingDestinationContract(candidate), new RegExp(field));
  }
});

test("the loop registry exactly matches the destination SSOT labels, entrypoints, and cadences", () => {
  const contract = loadMarketingDestinationContract(CONTRACT);
  const registry = JSON.parse(fs.readFileSync(path.resolve(__dirname, "../../../config/loop-registry.json"), "utf8"));
  assert.equal(auditMarketingDestinationRegistry(contract, registry).targets, 13);
  const candidate = structuredClone(registry);
  candidate.loops[contract.targets[0].loop_name].cadence.calendar_interval[0].Minute = 1;
  assert.throws(() => auditMarketingDestinationRegistry(contract, candidate), /cadence/i);
});

test("publication identity selects exactly one route and rejects cross-family content", () => {
  const contract = loadMarketingDestinationContract(CONTRACT);
  const input = {
    jobProductId: "honne-ai",
    locale: "en",
    platform: "tiktok",
    integrationId: "cmoig11ew001zlv0yk6vqo1us",
    jobFormatId: "reelclaw",
    mediaForm: "relationship-confession",
  };
  assert.equal(findMarketingDestinationTarget(contract, input).lane_id, "honne-en");
  assert.equal(findMarketingDestinationTarget(contract, { ...input, jobFormatId: "reelclaw-card" }), null);
  assert.equal(findMarketingDestinationTarget(contract, { ...input, mediaForm: "nudge-card" }), null);
  assert.equal(findMarketingDestinationTarget(contract, { ...input, integrationId: "cmp9sdev5012voh0y58qs45xc" }), null);
});
