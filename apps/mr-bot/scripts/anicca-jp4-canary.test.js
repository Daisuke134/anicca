"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { createMarketingLocalLedger } = require("../lib/marketing-local-ledger.js");
const { buildMarketingVideoPublicationJob } = require("../lib/marketing-video-publication-adapter.js");
const { APPROVAL_REF, CONFIRMATION, INTEGRATION, INTEGRATION_REF, VIDEOS, assertJp4Job, resolveTransport, run } = require("./anicca-jp4-canary.js");

function fixture() {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-jp4-canary-"));
  const objects = { resolve: () => "/dev/null" };
  const videoRef = [...VIDEOS][0];
  const captionRef = "object://sha256/" + "c".repeat(64);
  const job = buildMarketingVideoPublicationJob({ tenantId: "dais-local", productId: "anicca-ios", formatId: "reelclaw-card", form: "nudge-card", locale: "ja", slot: "2026-08-21T14:30:00.000Z", creativeId: "AJ-CARD-003-5639e14832ad", platform: "tiktok", videoRef, captionRef, approvalRef: APPROVAL_REF, instagramProfileRef: "profile://instagram/unassigned", postizTokenRef: "secret://postiz/api-key", tiktokIntegrationRef: INTEGRATION_REF });
  return { dataDir, objects, job, store: createMarketingLocalLedger({ dataDir }) };
}

async function fakeExecute(job, services) {
  if (job.capability === "marketing.video.publish") {
    const refs = job.input_refs;
    await services.completeJob({ tenantId: job.tenant_id, jobId: job.job_id, attempt: job.attempt, workerId: services.workerId, receipt: { schema_version: 1, kind: "marketing_video_distribution", status: "published", product_id: "anicca-ios", format_id: "reelclaw-card", form: "nudge-card", locale: "ja", slot: refs.slot_ref.slice("schedule-slot://".length), creative_id: "AJ-CARD-003-5639e14832ad", platform: "tiktok", video_sha256: refs.video_ref.slice("object://sha256/".length), caption_sha256: refs.caption_ref.slice("object://sha256/".length), public_url: "https://www.tiktok.com/@anicca.jp4/video/1", provider_post_id: "postiz-jp4-1", provider_route: "postiz", provider_reconciled: true, published_at: "2026-08-21T14:30:01.000Z" } });
    return;
  }
  const payload = JSON.parse(decodeURIComponent(job.input_refs.marketing_liveness_ref.slice("marketing-liveness://".length)));
  await services.completeJob({ tenantId: job.tenant_id, jobId: job.job_id, attempt: job.attempt, workerId: services.workerId, receipt: { schema_version: 1, kind: "telegram_marketing_liveness", ...payload, message_id: 77, chat_id_hash: "a".repeat(64), sent_at: "2026-08-21T14:30:02.000Z" } });
}

test("JP4 fake canary returns one direct receipt, one natural Telegram receipt, and zero replay effects", async () => {
  const value = fixture();
  await value.store.enqueueJob({ jobId: value.job.job_id, tenantId: value.job.tenant_id, loopId: value.job.loop_id, capability: value.job.capability, effectClass: value.job.effect_class, effectKey: value.job.effect_key, inputRefs: value.job.input_refs, maxAttempts: value.job.max_attempts });
  const result = await run(["run", "--tenant", "dais-local", "--job-id", value.job.job_id], { LM_DATA_DIR: value.dataDir, LM_ANICCA_JP4_CANARY_TRANSPORT: "fake", LM_ANICCA_JP4_CANARY_WORKER_ID: "test" }, { store: value.store, objectStore: value.objects, fakeTransport: true, fakeExecute });
  assert.equal(result.publication.public_url, "https://www.tiktok.com/@anicca.jp4/video/1");
  assert.equal(result.publication.replay_created, false);
  assert.equal(result.telegram.message_id, 77);
  assert.equal(result.telegram.replay_created, false);
});

test("JP4 runner rejects unapproved asset or real transport without exact confirmation", () => {
  const value = fixture();
  assert.throws(() => assertJp4Job({ ...value.job, input_refs: { ...value.job.input_refs, video_ref: "object://sha256/" + "b".repeat(64) } }, value.objects), /approved lane/);
  assert.throws(() => resolveTransport({ LM_ANICCA_JP4_CANARY_TRANSPORT: "postiz" }), /confirmation/);
  assert.equal(resolveTransport({ LM_ANICCA_JP4_CANARY_TRANSPORT: "postiz", LM_ANICCA_JP4_CANARY_CONFIRM: CONFIRMATION }), "postiz");
  assert.equal(INTEGRATION, "cmn8x8hdv028uqx0y4gdfse5t");
});
