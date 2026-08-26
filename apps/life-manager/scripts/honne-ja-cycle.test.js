"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { ANICCA_EN_CARD_INSTAGRAM_SLOTS, ANICCA_HE_SLOTS, ANICCA_JP4_SLOTS, ANICCA_MAIN_INSTAGRAM_SLOTS, ANICCA_MAIN_SLOTS, PRODUCTION_SLOTS, parseArgs, runSlot, telegramNativeUrlVerified } = require("./honne-ja-cycle.js");

test("Honne JA production cadence has three exact idempotent slots", () => {
  assert.deepEqual([...PRODUCTION_SLOTS], ["08:30", "12:30", "21:30"]);
  assert.equal(runSlot(null, Date.parse("2026-08-22T04:00:00.000Z")), "2026-08-22T03:30:00.000Z");
  assert.equal(runSlot(null, Date.parse("2026-08-22T13:00:00.000Z")), "2026-08-22T12:30:00.000Z");
  assert.throws(() => runSlot(null, Date.parse("2026-08-21T23:29:00.000Z")), /no due slot/i);
});

test("Anicca main Instagram has three exact daily Reel slots", () => {
  assert.deepEqual([...ANICCA_MAIN_INSTAGRAM_SLOTS], ["08:10", "13:10", "19:10"]);
  const lane = parseArgs(["run-anicca-main-instagram"]).lane;
  assert.equal(lane.platform, "instagram"); assert.equal(lane.account, "@anicca.jp1");
});

test("Anicca EN Card Instagram is exact-account bound at three daily slots", () => {
  assert.deepEqual([...ANICCA_EN_CARD_INSTAGRAM_SLOTS], ["08:45", "12:45", "21:30"]);
  const lane = parseArgs(["run-anicca-en-card-instagram"]).lane;
  assert.equal(lane.platform, "instagram");
  assert.equal(lane.account, "@anicca.encards");
  assert.equal(lane.integrationId, "cmpc3gx4001nklg0y27a8o66q");
  assert.equal(lane.instagramProfileRef, "profile://instagram/anicca.encards");
  assert.equal(lane.packKey, "LM_ANICCA_EN_CARD_PACK_REF");
  assert.equal(lane.mediaKey, "LM_ANICCA_EN_CARD_MEDIA_REFS");
  const url = "https://www.instagram.com/reel/ExactArtifact1/";
  assert.equal(telegramNativeUrlVerified(lane, {}, url), true);
});

test("Honne JA production CLI accepts only an optional exact slot", () => {
  const slot = "2026-08-22T03:30:00.000Z";
  assert.equal(parseArgs(["run"]).slot, null);
  assert.equal(parseArgs(["run", "--slot", slot]).slot, slot);
  assert.throws(() => parseArgs(["run", "--slot"]), /usage/i);
  assert.throws(() => runSlot("invalid", Date.now()), /timestamp is invalid/i);
});

test("Anicca main uses only its three historical JA widget slots", () => {
  assert.deepEqual([...ANICCA_MAIN_SLOTS], ["08:00", "16:00", "22:37"]);
  assert.equal(parseArgs(["run-anicca-main"]).lane.account, "@anicca.jp");
  assert.equal(runSlot(null, Date.parse("2026-08-22T07:30:00.000Z"), ANICCA_MAIN_SLOTS), "2026-08-22T07:00:00.000Z");
});

test("JP4 lane is account-bound and capped at three isolated slots", () => {
  const lane = parseArgs(["run-anicca-jp4"]).lane;
  assert.equal(lane.account, "@anicca.jp4"); assert.equal(lane.integrationId, "cmn8x8hdv028uqx0y4gdfse5t"); assert.equal(lane.approvalKey, "LM_ANICCA_JP4_TIKTOK_APPROVAL_REF"); assert.deepEqual([...ANICCA_JP4_SLOTS], ["09:15", "15:15", "20:45"]); assert.equal(lane.slots.length, 3);
});

test("HE lane is account-bound and capped at three isolated slots", () => {
  const lane = parseArgs(["run-anicca-he"]).lane;
  assert.equal(lane.account, "@anicca.he"); assert.equal(lane.integrationId, "cmq2aoena08bhqp0yx1epjcik"); assert.equal(lane.approvalKey, "LM_ANICCA_HE_TIKTOK_APPROVAL_REF"); assert.deepEqual([...ANICCA_HE_SLOTS], ["07:15", "13:45", "18:15"]); assert.equal(lane.slots.length, 3);
});
