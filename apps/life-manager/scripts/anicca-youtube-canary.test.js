"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const {
  APPROVAL_REF,
  CAPTION_REF,
  CONFIRMATION,
  INTEGRATION_REF,
  VIDEO_REF,
  assertYoutubeJob,
  resolveTransport,
  verifyDirectPublicUrl,
} = require("./anicca-youtube-canary.js");

function job(overrides = {}) {
  return {
    tenant_id: "dais-local",
    capability: "marketing.video.publish",
    effect_class: "publish",
    input_refs: {
      product_ref: "product://anicca-ios",
      format_ref: "format://reelclaw-card",
      form_ref: "form://nudge-card",
      locale_ref: "locale://ja",
      platform_ref: "platform://youtube",
      instagram_profile_ref: "profile://instagram/unassigned",
      youtube_integration_ref: INTEGRATION_REF,
      video_ref: VIDEO_REF,
      caption_ref: CAPTION_REF,
      approval_ref: APPROVAL_REF,
    },
    ...overrides,
  };
}

test("allows only the exact account-bound Anicca YouTube creative", () => {
  const resolved = [];
  const candidate = job();
  assert.equal(assertYoutubeJob(candidate, { resolve: (ref) => resolved.push(ref) }), candidate);
  assert.deepEqual(resolved, [VIDEO_REF, CAPTION_REF, APPROVAL_REF]);
  for (const [field, value] of [
    ["youtube_integration_ref", "integration://postiz/youtube/wrong"],
    ["video_ref", "object://sha256/" + "a".repeat(64)],
    ["caption_ref", "object://sha256/" + "b".repeat(64)],
    ["approval_ref", "object://sha256/" + "c".repeat(64)],
  ]) {
    assert.throws(() => assertYoutubeJob(job({ input_refs: { ...job().input_refs, [field]: value } }), { resolve() {} }), /not the approved lane/i);
  }
  assert.equal(resolveTransport({ LM_ANICCA_YOUTUBE_CANARY_TRANSPORT: "postiz", LM_ANICCA_YOUTUBE_CANARY_CONFIRM: CONFIRMATION }), "postiz");
  assert.throws(() => resolveTransport({ LM_ANICCA_YOUTUBE_CANARY_TRANSPORT: "postiz" }), /confirmation is invalid/i);
});

test("direct verifier rejects a profile URL even when HTTP is 200", async () => {
  await assert.rejects(() => verifyDirectPublicUrl("https://www.youtube.com/@anicca-jp", async () => ({ status: 200 })), /direct URL is invalid/i);
  const url = "https://www.youtube.com/shorts/AbCdEf12345";
  assert.deepEqual(await verifyDirectPublicUrl(url, async () => ({ status: 200, url })), { status: 200, url });
});
