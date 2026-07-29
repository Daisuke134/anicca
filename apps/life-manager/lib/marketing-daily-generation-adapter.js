"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const { buildRuntimeJob } = require("./runtime-job-store.js");

const ADAPTER_ID = "marketing-life-manager-daily-generation";
const LOOP_ID = "marketing.life-manager.daily.generate";
const CAPABILITY = "marketing.life-manager.daily.generate";
const HASH = /^[0-9a-f]{64}$/;
const OBJECT_REF = /^object:\/\/sha256\/([0-9a-f]{64})$/;
const DATE_REF = /^calendar:\/\/date\/(\d{4}-\d{2}-\d{2})$/;
const RECEIPT_KEYS = new Set([
  "schema_version",
  "kind",
  "status",
  "date",
  "creative_id",
  "video_ref",
  "video_sha256",
  "duration_seconds",
  "generated_at",
]);

function exactDate(value) {
  const text = String(value || "");
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
  if (!match) throw new Error("marketing generation date is invalid");
  const parsed = new Date(`${text}T00:00:00.000Z`);
  if (!Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== text) {
    throw new Error("marketing generation date is invalid");
  }
  return text;
}

function objectReference(value, label) {
  const ref = String(value || "");
  if (!OBJECT_REF.test(ref)) throw new Error(`${label} reference is invalid`);
  return ref;
}

function hashJob(value) {
  return crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

function buildMarketingDailyGenerationJob(input) {
  const tenantId = String(input && input.tenantId || "").trim();
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(tenantId)) {
    throw new Error("marketing generation tenant is invalid");
  }
  const date = exactDate(input.date);
  const inputRefs = {
    date_ref: `calendar://date/${date}`,
    bank_ref: objectReference(input.bankRef, "bank"),
    call_audio_ref: objectReference(input.callAudioRef, "call audio"),
    stock_ref: objectReference(input.stockRef, "stock"),
    telegram_proof_ref: objectReference(input.telegramProofRef, "Telegram proof"),
    whisper_ass_ref: objectReference(input.whisperAssRef, "Whisper ASS"),
  };
  const digest = hashJob({ tenant_id: tenantId, input_refs: inputRefs });
  return buildRuntimeJob({
    jobId: `marketing-daily-generation:${digest}`,
    tenantId,
    loopId: LOOP_ID,
    capability: CAPABILITY,
    effectClass: "none",
    effectKey: null,
    inputRefs,
    maxAttempts: 2,
  });
}

function normalizeJob(job) {
  const refs = job && (job.input_refs || job.inputRefs);
  if (!refs || typeof refs !== "object" || Array.isArray(refs)) {
    throw new Error("marketing generation job refs are invalid");
  }
  const expectedRefKeys = [
    "bank_ref",
    "call_audio_ref",
    "date_ref",
    "stock_ref",
    "telegram_proof_ref",
    "whisper_ass_ref",
  ];
  if (
    JSON.stringify(Object.keys(refs).sort())
    !== JSON.stringify(expectedRefKeys)
  ) {
    throw new Error("marketing generation job refs are invalid");
  }
  const dateMatch = DATE_REF.exec(String(refs.date_ref || ""));
  if (!dateMatch) throw new Error("marketing generation date reference is invalid");
  const contract = {
    tenantId: String(job.tenant_id || job.tenantId || "").trim(),
    date: exactDate(dateMatch[1]),
    assets: {
      bank: objectReference(refs.bank_ref, "bank"),
      callAudio: objectReference(refs.call_audio_ref, "call audio"),
      stock: objectReference(refs.stock_ref, "stock"),
      telegramProof: objectReference(refs.telegram_proof_ref, "Telegram proof"),
      whisperAss: objectReference(refs.whisper_ass_ref, "Whisper ASS"),
    },
  };
  const expected = buildMarketingDailyGenerationJob({
    tenantId: contract.tenantId,
    date: contract.date,
    bankRef: contract.assets.bank,
    callAudioRef: contract.assets.callAudio,
    stockRef: contract.assets.stock,
    telegramProofRef: contract.assets.telegramProof,
    whisperAssRef: contract.assets.whisperAss,
  });
  if (
    (job.capability || CAPABILITY) !== CAPABILITY
    || (job.loop_id || job.loopId || LOOP_ID) !== LOOP_ID
    || (job.effect_class || job.effectClass || "none") !== "none"
    || String(job.job_id || job.jobId || "") !== expected.job_id
    || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(contract.tenantId)
  ) {
    throw new Error("marketing generation job contract is invalid");
  }
  return contract;
}

function inside(parent, candidate) {
  const root = path.resolve(parent);
  const resolved = path.resolve(candidate);
  return resolved === root || resolved.startsWith(`${root}${path.sep}`);
}

function defaultRenderer(input, options = {}) {
  const pythonBin = String(options.pythonBin || process.env.PYTHON_BIN || "python3");
  const scriptPath = path.resolve(
    options.scriptPath
      || path.join(__dirname, "../../../skills/video/daily-lm-video/generate.py"),
  );
  const args = [
    scriptPath,
    "--bank", input.assets.bank,
    "--state", input.statePath,
    "--output-dir", input.outputDir,
    "--call-audio", input.assets.callAudio,
    "--stock", input.assets.stock,
    "--telegram-proof", input.assets.telegramProof,
    "--whisper-ass", input.assets.whisperAss,
    "--date", input.date,
  ];
  const result = (options.spawnSync || spawnSync)(pythonBin, args, {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    timeout: Number(options.timeoutMs || 240000),
    maxBuffer: 4 * 1024 * 1024,
  });
  if (!result || result.status !== 0) {
    throw new Error("marketing generation renderer failed");
  }
  const lines = String(result.stdout || "").split(/\r?\n/).filter(Boolean);
  if (lines.length !== 1) throw new Error("marketing generation renderer result is invalid");
  let parsed;
  try {
    parsed = JSON.parse(lines[0]);
  } catch {
    throw new Error("marketing generation renderer result is invalid");
  }
  return parsed;
}

function validateRenderResult(result, outputDir) {
  const creativeId = String(result && result.selected_id || "");
  const output = path.resolve(String(result && result.output || ""));
  const duration = Number(result && result.duration_seconds);
  if (
    !/^[A-Za-z0-9._-]+$/.test(creativeId)
    || !inside(outputDir, output)
    || !fs.statSync(output, { throwIfNoEntry: false })?.isFile()
    || !Number.isFinite(duration)
    || duration < 20
    || duration > 40
  ) {
    throw new Error("marketing generation renderer result is invalid");
  }
  return { creativeId, output, duration };
}

function verifyMarketingDailyGenerationReceipt(receipt) {
  if (!receipt || typeof receipt !== "object" || Array.isArray(receipt)) return false;
  if (Object.keys(receipt).some((key) => !RECEIPT_KEYS.has(key))) return false;
  const match = OBJECT_REF.exec(String(receipt.video_ref || ""));
  return Boolean(
    receipt.schema_version === 1
    && receipt.kind === "marketing_daily_generation"
    && receipt.status === "rendered"
    && (() => {
      try {
        return exactDate(receipt.date) === receipt.date;
      } catch {
        return false;
      }
    })()
    && /^[A-Za-z0-9._-]+$/.test(String(receipt.creative_id || ""))
    && match
    && HASH.test(String(receipt.video_sha256 || ""))
    && match[1] === receipt.video_sha256
    && Number.isFinite(receipt.duration_seconds)
    && receipt.duration_seconds >= 20
    && receipt.duration_seconds <= 40
    && typeof receipt.generated_at === "string"
    && Number.isFinite(Date.parse(receipt.generated_at))
  );
}

function safeMarketingDailyGenerationSummary(receipt) {
  if (!verifyMarketingDailyGenerationReceipt(receipt)) {
    throw new Error("marketing generation receipt verification failed");
  }
  return {
    status: receipt.status,
    date: receipt.date,
    creative_id: receipt.creative_id,
    video_ref: receipt.video_ref,
    video_sha256: receipt.video_sha256,
    duration_seconds: receipt.duration_seconds,
  };
}

function defaultServices(deps = {}) {
  const dataDir = () => {
    const raw = String(deps.dataDir || process.env.LM_DATA_DIR || "").trim();
    if (!raw) throw new Error("marketing generation data directory is invalid");
    const resolved = path.resolve(raw);
    if (resolved === path.parse(resolved).root) {
      throw new Error("marketing generation data directory is invalid");
    }
    return resolved;
  };
  const objectStore = deps.objectStore || {
    resolve(ref) {
      const { resolveContentObject } = require("./content-object-store.js");
      return resolveContentObject(ref, { objectDir: path.join(dataDir(), "objects") });
    },
    import(source) {
      const { importContentObject } = require("./content-object-store.js");
      return importContentObject(source, { objectDir: path.join(dataDir(), "objects") });
    },
  };
  const workspaceProvider = deps.workspaceProvider || {
    get(tenantId) {
      const root = dataDir();
      if (!root || root === path.parse(root).root) {
        throw new Error("marketing generation data directory is invalid");
      }
      return path.join(
        root,
        "tenants",
        encodeURIComponent(tenantId),
        "marketing",
        "life-manager-daily",
        "generation",
      );
    },
  };
  return {
    objectStore,
    workspaceProvider,
    renderer: deps.renderer || ((input) => defaultRenderer(input, deps)),
    now: deps.now || (() => new Date().toISOString()),
  };
}

function createMarketingDailyGenerationLoopAdapter(deps = {}) {
  const services = defaultServices(deps);
  return Object.freeze({
    async plan(input) {
      return [buildMarketingDailyGenerationJob(input)];
    },
    async execute(job) {
      const contract = normalizeJob(job);
      const workspace = path.resolve(services.workspaceProvider.get(contract.tenantId));
      const stateDir = path.join(workspace, "state");
      const outputDir = path.join(workspace, "renders");
      fs.mkdirSync(stateDir, { recursive: true, mode: 0o700 });
      fs.mkdirSync(outputDir, { recursive: true, mode: 0o700 });
      const assets = Object.fromEntries(
        Object.entries(contract.assets).map(([name, ref]) => [
          name,
          services.objectStore.resolve(ref),
        ]),
      );
      const result = await services.renderer({
        tenantId: contract.tenantId,
        date: contract.date,
        assets,
        statePath: path.join(stateDir, "daily-render-state.jsonl"),
        outputDir,
      });
      const render = validateRenderResult(result, outputDir);
      for (const privatePath of [
        path.join(stateDir, "daily-render-state.jsonl"),
        path.join(stateDir, "daily-render-state.jsonl.lock"),
        render.output,
      ]) {
        if (fs.statSync(privatePath, { throwIfNoEntry: false })?.isFile()) {
          fs.chmodSync(privatePath, 0o600);
        }
      }
      const imported = services.objectStore.import(render.output);
      const receipt = {
        schema_version: 1,
        kind: "marketing_daily_generation",
        status: "rendered",
        date: contract.date,
        creative_id: render.creativeId,
        video_ref: imported.ref,
        video_sha256: imported.sha256,
        duration_seconds: render.duration,
        generated_at: services.now(),
      };
      if (!verifyMarketingDailyGenerationReceipt(receipt)) {
        throw new Error("marketing generation receipt verification failed");
      }
      return { receipt, result };
    },
    async reconcile(effect) {
      if (effect && verifyMarketingDailyGenerationReceipt(effect.receipt)) {
        return { state: "present", receipt: effect.receipt };
      }
      return { state: "absent" };
    },
    verify: verifyMarketingDailyGenerationReceipt,
    report: safeMarketingDailyGenerationSummary,
  });
}

module.exports = {
  ADAPTER_ID,
  LOOP_ID,
  CAPABILITY,
  buildMarketingDailyGenerationJob,
  createMarketingDailyGenerationLoopAdapter,
  defaultRenderer,
  safeMarketingDailyGenerationSummary,
  verifyMarketingDailyGenerationReceipt,
};
