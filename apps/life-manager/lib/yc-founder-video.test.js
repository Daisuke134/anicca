"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { buildYcFounderVideoUpload } = require("./yc-founder-video.js");

const valid = {
  draftId: "0b61fe42-e383-490d-b60e-04f1ad7ec5df",
  sourceRef: "application-kit://videos/Anicca_intro_EN.mp4",
  artifactDigest: "3".repeat(64),
  durationSeconds: 57.835,
  sizeBytes: 22291622,
  formatNames: ["mov", "mp4", "m4a", "3gp", "3g2", "mj2"],
  streams: [{ type: "video", codec: "h264" }, { type: "audio", codec: "aac" }],
};

test("58-second English H.264/AAC artifact creates one bounded upload plan", () => {
  const plan = buildYcFounderVideoUpload(valid);
  assert.equal(plan.duration_seconds, 57.835);
  assert.equal(plan.size_bytes, 22291622);
  assert.equal(plan.maximum_duration_seconds, 60);
  assert.equal(plan.maximum_size_bytes, 100000000);
  assert.equal(plan.file_input_sets, 1);
  assert.equal(plan.save_clicks, 1);
  assert.equal(plan.submit_clicks, 0);
  assert.match(plan.plan_digest, /^[0-9a-f]{64}$/);
});

test("overlong, oversized, wrong codec, missing audio, and wrong source fail closed", () => {
  const invalid = [
    { durationSeconds: 60.001 },
    { sizeBytes: 100000001 },
    { streams: [{ type: "video", codec: "hevc" }, { type: "audio", codec: "aac" }] },
    { streams: [{ type: "video", codec: "h264" }] },
    { sourceRef: "application-kit://videos/yc-founder-video-2026-fall.mp4" },
    { artifactDigest: "bad" },
  ];
  for (const overrides of invalid) assert.throws(() => buildYcFounderVideoUpload({ ...valid, ...overrides }), /founder video/i);
});
