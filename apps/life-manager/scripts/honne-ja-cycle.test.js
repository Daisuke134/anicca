"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const cycle = require("./honne-ja-cycle.js");
const { ANICCA_EN_CARD_INSTAGRAM_SLOTS, ANICCA_EN_WIDGET_INSTAGRAM_SLOTS, ANICCA_HE_SLOTS, ANICCA_JA_WIDGET_INSTAGRAM_SLOTS, ANICCA_JP4_SLOTS, ANICCA_MAIN_INSTAGRAM_SLOTS, ANICCA_MAIN_SLOTS, PRODUCTION_SLOTS, parseArgs, runSlot, telegramNativeUrlVerified } = cycle;

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

test("Anicca EN Widget Instagram publishes only the exact account at three daily slots", () => {
  assert.deepEqual([...ANICCA_EN_WIDGET_INSTAGRAM_SLOTS], ["07:30", "09:30", "19:00"]);
  const lane = parseArgs(["run-anicca-en-widget-instagram"]).lane;
  assert.equal(lane.format, "reelclaw-widget");
  assert.equal(lane.platform, "instagram");
  assert.equal(lane.account, "@anicca.en");
  assert.equal(lane.integrationId, "cmn8y95rg02d2qx0y09bbk5pb");
  assert.equal(lane.instagramProfileRef, "profile://instagram/anicca.en");
  assert.equal(lane.packKey, "LM_ANICCA_EN_WIDGET_PRODUCTION_PACK_REF");
  assert.equal(lane.mediaKey, "LM_ANICCA_EN_WIDGET_PRODUCTION_MEDIA_REFS");
});

test("Anicca JA Widget Instagram publishes only the exact account at three daily slots", () => {
  assert.deepEqual([...ANICCA_JA_WIDGET_INSTAGRAM_SLOTS], ["08:05", "13:05", "18:20"]);
  const lane = parseArgs(["run-anicca-ja-widget-instagram"]).lane;
  assert.equal(lane.format, "reelclaw-widget");
  assert.equal(lane.platform, "instagram");
  assert.equal(lane.account, "@anicca.jp.videos");
  assert.equal(lane.integrationId, "cmmzzg2es0539p30ycb94ayx0");
  assert.equal(lane.instagramProfileRef, "profile://instagram/anicca.jp.videos");
  assert.equal(lane.packKey, "LM_ANICCA_JA_WIDGET_PRODUCTION_PACK_REF");
  assert.equal(lane.mediaKey, "LM_ANICCA_JA_WIDGET_PRODUCTION_MEDIA_REFS");
  assert.equal(lane.approvalKey, "LM_ANICCA_JA_WIDGET_PRODUCTION_APPROVAL_REF");
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

test("production publication identity is stable per slot and distinct across days", () => {
  assert.equal(typeof cycle.buildCyclePublicationJob, "function");
  const lane = parseArgs(["run-anicca-main-instagram"]).lane;
  const artifact = {
    form: "nudge-card",
    creative_id: "AJ-CARD-002-7e24db967bf7",
    video_ref: `object://sha256/${"1".repeat(64)}`,
    copy_ref: `object://sha256/${"2".repeat(64)}`,
  };
  const approvalRef = `object://sha256/${"3".repeat(64)}`;
  const first = cycle.buildCyclePublicationJob(lane, "dais-local", "2026-08-26T10:10:00.000Z", artifact, approvalRef);
  const replay = cycle.buildCyclePublicationJob(lane, "dais-local", "2026-08-26T10:10:00.000Z", artifact, approvalRef);
  const nextDay = cycle.buildCyclePublicationJob(lane, "dais-local", "2026-08-27T10:10:00.000Z", artifact, approvalRef);
  assert.equal(first.job_id, replay.job_id);
  assert.equal(first.effect_key, replay.effect_key);
  assert.notEqual(first.job_id, nextDay.job_id);
  assert.notEqual(first.effect_key, nextDay.effect_key);
});
