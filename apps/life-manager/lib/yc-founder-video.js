"use strict";

const { createHash } = require("node:crypto");

const SOURCE_REF = "application-kit://videos/Anicca_intro_EN.mp4";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}

function buildYcFounderVideoUpload(input = {}) {
  const draftId = String(input.draftId || "");
  const sourceRef = String(input.sourceRef || "");
  const artifactDigest = String(input.artifactDigest || "");
  const durationSeconds = Number(input.durationSeconds);
  const sizeBytes = Number(input.sizeBytes);
  const formatNames = Array.isArray(input.formatNames) ? input.formatNames.map(String) : [];
  const streams = Array.isArray(input.streams) ? input.streams : [];
  const video = streams.filter(({ type }) => type === "video");
  const audio = streams.filter(({ type }) => type === "audio");
  if (!UUID.test(draftId) || sourceRef !== SOURCE_REF || !/^[0-9a-f]{64}$/.test(artifactDigest)
    || !Number.isFinite(durationSeconds) || durationSeconds <= 0 || durationSeconds > 60
    || !Number.isSafeInteger(sizeBytes) || sizeBytes <= 0 || sizeBytes > 100_000_000
    || !formatNames.includes("mp4") || video.length < 1 || audio.length < 1
    || video.some(({ codec }) => codec !== "h264") || audio.some(({ codec }) => codec !== "aac")) {
    throw new Error("YC founder video artifact invalid");
  }
  const core = {
    schema_version: 1,
    draft_id: draftId.toLowerCase(),
    source_ref: sourceRef,
    artifact_digest: artifactDigest,
    duration_seconds: durationSeconds,
    maximum_duration_seconds: 60,
    size_bytes: sizeBytes,
    maximum_size_bytes: 100_000_000,
    video_codec: "h264",
    audio_codec: "aac",
    file_input_sets: 1,
    save_clicks: 1,
    submit_clicks: 0,
  };
  return Object.freeze({ ...core, plan_digest: createHash("sha256").update(stable(core)).digest("hex") });
}

module.exports = { buildYcFounderVideoUpload };
