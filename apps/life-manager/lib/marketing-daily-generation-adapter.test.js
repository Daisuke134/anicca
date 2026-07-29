"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { createContentObjectStore } = require("./content-object-store.js");
const {
  buildMarketingDailyGenerationJob,
  createMarketingDailyGenerationLoopAdapter,
  safeMarketingDailyGenerationSummary,
  verifyMarketingDailyGenerationReceipt,
} = require("./marketing-daily-generation-adapter.js");

function fixtureStore(root) {
  const store = createContentObjectStore({
    objectDir: path.join(root, "objects"),
  });
  const refs = {};
  for (const [name, contents] of Object.entries({
    bank: '{"id":"A01"}\n',
    callAudio: "audio",
    stock: "stock",
    telegramProof: "proof",
    whisperAss: "ass",
  })) {
    const source = path.join(root, name);
    fs.writeFileSync(source, contents);
    refs[`${name}Ref`] = store.import(source).ref;
  }
  return { store, refs };
}

test("generation job is tenant-bound, date-idempotent, and reference-only", () => {
  const refs = {
    bankRef: `object://sha256/${"a".repeat(64)}`,
    callAudioRef: `object://sha256/${"b".repeat(64)}`,
    stockRef: `object://sha256/${"c".repeat(64)}`,
    telegramProofRef: `object://sha256/${"d".repeat(64)}`,
    whisperAssRef: `object://sha256/${"e".repeat(64)}`,
  };
  const job = buildMarketingDailyGenerationJob({
    tenantId: "tenant-a",
    date: "2026-07-30",
    ...refs,
  });

  assert.equal(job.loop_id, "marketing.life-manager.daily.generate");
  assert.equal(job.capability, "marketing.life-manager.daily.generate");
  assert.equal(job.effect_class, "none");
  assert.equal(job.effect_key, null);
  assert.match(job.job_id, /^marketing-daily-generation:[0-9a-f]{64}$/);
  assert.deepEqual(job.input_refs, {
    date_ref: "calendar://date/2026-07-30",
    bank_ref: refs.bankRef,
    call_audio_ref: refs.callAudioRef,
    stock_ref: refs.stockRef,
    telegram_proof_ref: refs.telegramProofRef,
    whisper_ass_ref: refs.whisperAssRef,
  });
  assert.doesNotMatch(JSON.stringify(job), /\.openclaw|\/Users\/|password|token/i);
});

test("generation adapter renders from immutable objects into a tenant workspace and imports the MP4", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-generation-"));
  const { store, refs } = fixtureStore(root);
  const calls = [];
  const adapter = createMarketingDailyGenerationLoopAdapter({
    objectStore: store,
    workspaceProvider: {
      get(tenantId) {
        assert.equal(tenantId, "tenant-a");
        return path.join(root, "tenants", tenantId, "generation");
      },
    },
    renderer: async (input) => {
      calls.push(input);
      fs.mkdirSync(input.outputDir, { recursive: true });
      fs.writeFileSync(input.statePath, '{"creative_id":"A01"}\n');
      fs.writeFileSync(`${input.statePath}.lock`, "");
      const output = path.join(input.outputDir, `${input.date}-A01.mp4`);
      fs.writeFileSync(output, "real-render-fixture");
      return {
        selected_id: "A01",
        output,
        duration_seconds: 34.656,
      };
    },
    now: () => "2026-07-29T15:00:00.000Z",
  });
  const job = buildMarketingDailyGenerationJob({
    tenantId: "tenant-a",
    date: "2026-07-30",
    ...refs,
  });

  const execution = await adapter.execute(job);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].date, "2026-07-30");
  assert.ok(calls[0].statePath.startsWith(path.join(root, "tenants", "tenant-a")));
  assert.deepEqual(Object.keys(calls[0].assets).sort(), [
    "bank", "callAudio", "stock", "telegramProof", "whisperAss",
  ]);
  assert.equal(verifyMarketingDailyGenerationReceipt(execution.receipt), true);
  assert.equal(
    fs.readFileSync(store.resolve(execution.receipt.video_ref), "utf8"),
    "real-render-fixture",
  );
  for (const privatePath of [
    calls[0].statePath,
    `${calls[0].statePath}.lock`,
    path.join(calls[0].outputDir, "2026-07-30-A01.mp4"),
  ]) {
    assert.equal(fs.statSync(privatePath).mode & 0o777, 0o600);
  }
  assert.deepEqual(safeMarketingDailyGenerationSummary(execution.receipt), {
    status: "rendered",
    date: "2026-07-30",
    creative_id: "A01",
    video_ref: execution.receipt.video_ref,
    video_sha256: execution.receipt.video_sha256,
    duration_seconds: 34.656,
  });
  assert.doesNotMatch(JSON.stringify(execution.receipt), /tmp|tenants|\/Users\/|\.openclaw/);
});

test("generation receipt rejects paths, invalid hashes, and out-of-range duration", () => {
  const base = {
    schema_version: 1,
    kind: "marketing_daily_generation",
    status: "rendered",
    date: "2026-07-30",
    creative_id: "A01",
    video_ref: `object://sha256/${"f".repeat(64)}`,
    video_sha256: "f".repeat(64),
    duration_seconds: 34.656,
    generated_at: "2026-07-29T15:00:00.000Z",
  };
  assert.equal(verifyMarketingDailyGenerationReceipt(base), true);
  assert.equal(verifyMarketingDailyGenerationReceipt({ ...base, output: "/tmp/render.mp4" }), false);
  assert.equal(verifyMarketingDailyGenerationReceipt({ ...base, video_sha256: "bad" }), false);
  assert.equal(verifyMarketingDailyGenerationReceipt({ ...base, duration_seconds: 41 }), false);
});

test("generation adapter rejects extra refs and a job id that does not bind the inputs", async () => {
  const refs = {
    bankRef: `object://sha256/${"a".repeat(64)}`,
    callAudioRef: `object://sha256/${"b".repeat(64)}`,
    stockRef: `object://sha256/${"c".repeat(64)}`,
    telegramProofRef: `object://sha256/${"d".repeat(64)}`,
    whisperAssRef: `object://sha256/${"e".repeat(64)}`,
  };
  const job = buildMarketingDailyGenerationJob({
    tenantId: "tenant-a",
    date: "2026-07-30",
    ...refs,
  });
  const adapter = createMarketingDailyGenerationLoopAdapter();

  await assert.rejects(
    adapter.execute({
      ...job,
      input_refs: { ...job.input_refs, surprise_ref: refs.bankRef },
    }),
    /refs/i,
  );
  await assert.rejects(
    adapter.execute({ ...job, job_id: "marketing-daily-generation:tampered" }),
    /contract/i,
  );
});
