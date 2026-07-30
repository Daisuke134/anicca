// honne-ja-shadow-runtime.js — Honne JA generic video shadow scheduling.
//
// SHADOW CONTRACT (spec Order 11, Honne JA slice):
//   * Default OFF. Only the deliberate exact value LM_HONNE_JA_SHADOW_ENABLED=true
//     turns the scheduler wiring on; any other value stays off. The legacy
//     launchd owner ai.anicca.reelclaw-honne-ja (12:30/21:30 JST) remains the
//     production owner throughout shadowing.
//   * On a due slot, generation runs FOR REAL (real durable job, real immutable
//     receipt, no external effect — the generation adapter is a no-effect
//     producer).
//   * Publication jobs are enqueued into the durable store but HELD: shadow
//     grants no worker the marketing.video.publish capability, so the jobs stay
//     queued, and every hold is recorded durably with status "shadow_held".
//     No Instagram/TikTok/Postiz provider is ever called in shadow.
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const { HONNE_JA_SLOTS, honneJaDueSlot, zonedSlotInstant } = require("./honne-ja-shadow-schedule.js");
const {
  buildMarketingVideoGenerationJob,
  verifyMarketingVideoGenerationReceipt,
} = require("./marketing-video-generation-adapter.js");
const {
  enqueueVideoGenerationPublications,
} = require("./marketing-video-publication-chain.js");

const SHADOW_HOLD_STATUS = "shadow_held";
const EXPECTED_SHADOW_CYCLES = 7;

function requiredEnv(env, name) {
  const value = String(env[name] == null ? "" : env[name]).trim();
  if (!value) throw new Error(`${name} is required`);
  return value;
}

// options.manual=true activates the full reference contract for a deliberate
// one-shot shadow cycle WITHOUT enabling the scheduler flag.
function honneJaShadowConfig(env = {}, options = {}) {
  const enabled = String(env.LM_HONNE_JA_SHADOW_ENABLED == null ? "false" : env.LM_HONNE_JA_SHADOW_ENABLED)
    .trim()
    .toLowerCase() === "true";
  const base = {
    enabled,
    timeZone: String(env.LM_HONNE_JA_SHADOW_TIME_ZONE || "Asia/Tokyo").trim(),
    slots: HONNE_JA_SLOTS,
  };
  if (!enabled && options.manual !== true) return Object.freeze(base);
  const mediaRefs = requiredEnv(env, "LM_HONNE_JA_MEDIA_REFS")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  if (mediaRefs.length < 1) throw new Error("LM_HONNE_JA_MEDIA_REFS is required");
  return Object.freeze({
    ...base,
    tenantId: requiredEnv(env, "LM_RUNTIME_TENANT_ID"),
    productId: String(env.LM_HONNE_JA_PRODUCT_ID || "honne-ai").trim(),
    formatId: String(env.LM_HONNE_JA_FORMAT_ID || "reelclaw").trim(),
    locale: String(env.LM_HONNE_JA_LOCALE || "ja").trim(),
    packRef: requiredEnv(env, "LM_HONNE_JA_PACK_REF"),
    mediaRefs: Object.freeze(mediaRefs),
    publication: Object.freeze({
      approvalRef: requiredEnv(env, "LM_HONNE_JA_PUBLICATION_APPROVAL_REF"),
      instagramProfileRef: requiredEnv(env, "LM_HONNE_JA_INSTAGRAM_PROFILE_REF"),
      postizTokenRef: requiredEnv(env, "LM_HONNE_JA_POSTIZ_TOKEN_REF"),
      tiktokIntegrationRef: requiredEnv(env, "LM_HONNE_JA_TIKTOK_INTEGRATION_REF"),
    }),
  });
}

// The due generation job for `nowMs`, or null when the scheduler is disabled
// or no slot has fired yet on the current local day. Two polls inside the same
// slot window derive the same job_id, so the durable enqueue is idempotent.
function planHonneJaShadowGeneration(config, nowMs) {
  if (!config || config.enabled !== true) return null;
  const slot = honneJaDueSlot(nowMs, config.timeZone);
  if (!slot) return null;
  return buildMarketingVideoGenerationJob({
    tenantId: config.tenantId,
    productId: config.productId,
    formatId: config.formatId,
    locale: config.locale,
    slot,
    packRef: config.packRef,
    mediaRefs: [...config.mediaRefs],
  });
}

// Enqueue the Instagram+TikTok publication jobs for one verified generation
// receipt and record the hold durably. Execution is NEVER triggered here: the
// jobs stay queued because shadow grants no worker the publish capability.
async function holdHonneJaShadowPublications(receipt, config, deps = {}) {
  if (!config || !config.publication) {
    throw new Error("honne JA shadow publication references are required");
  }
  if (typeof deps.appendHold !== "function") {
    throw new Error("honne JA shadow hold sink is required");
  }
  if (!verifyMarketingVideoGenerationReceipt(receipt)) {
    throw new Error("marketing video generation receipt is invalid");
  }
  const results = await enqueueVideoGenerationPublications(receipt, {
    tenantId: config.tenantId,
    productId: config.productId,
    approvalRef: config.publication.approvalRef,
    instagramProfileRef: config.publication.instagramProfileRef,
    postizTokenRef: config.publication.postizTokenRef,
    tiktokIntegrationRef: config.publication.tiktokIntegrationRef,
  }, { enqueueJob: deps.enqueueJob, storeOptions: deps.storeOptions });
  const hold = {
    schema_version: 1,
    kind: "marketing_video_publication_hold",
    status: SHADOW_HOLD_STATUS,
    product_id: receipt.product_id,
    creative_id: receipt.creative_id,
    slot: receipt.slot,
    publication_job_ids: results.map(({ job }) => job.job_id),
    held_at: (deps.now || (() => new Date().toISOString()))(),
  };
  // Record the hold once per new hold event: a replay whose jobs all already
  // exist converges silently instead of appending duplicate ledger lines.
  const recorded = results.some(({ created }) => created === true);
  if (recorded) await deps.appendHold(hold);
  return { results, hold, recorded };
}

// Durable hold ledger: one JSON line per shadow hold beneath the tenant data
// root. Returns the ledger path so callers can report where the hold lives.
function appendHonneJaShadowHold(hold, options = {}) {
  const rawDataDir = String(options.dataDir || "").trim();
  const dataDir = path.resolve(rawDataDir);
  if (!rawDataDir || dataDir === path.parse(dataDir).root) {
    throw new Error("honne JA shadow data directory is invalid");
  }
  const tenantId = String(options.tenantId || "").trim();
  const productId = String(options.productId || "").trim();
  if (!tenantId || !productId) {
    throw new Error("honne JA shadow hold scope is invalid");
  }
  const ledgerDir = path.join(
    dataDir,
    "tenants",
    encodeURIComponent(tenantId),
    "marketing",
    "video-publication-shadow",
    encodeURIComponent(productId),
  );
  fs.mkdirSync(ledgerDir, { recursive: true, mode: 0o700 });
  const ledgerPath = path.join(ledgerDir, "held.jsonl");
  fs.appendFileSync(ledgerPath, `${JSON.stringify(hold)}\n`, { mode: 0o600 });
  return ledgerPath;
}

// How many missed expected slots the status reader enumerates for visibility
// before truncating (one week of the 2-slot/day grid). The streak is already
// broken at the first gap regardless of truncation.
const MISSED_SLOT_REPORT_LIMIT = 14;

// Local calendar day ({year, month, day}) of `ms` in `timeZone`.
function localCalendarDay(ms, timeZone) {
  let parts;
  try {
    parts = new Intl.DateTimeFormat("en-CA", {
      timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).formatToParts(new Date(ms));
  } catch {
    throw new Error("honne JA shadow status time zone is invalid");
  }
  const map = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
  return { year: Number(map.year), month: Number(map.month), day: Number(map.day) };
}

// Pure calendar step backward (Date.UTC arithmetic never touches time zones).
function previousCalendarDay(day) {
  const rolled = new Date(Date.UTC(day.year, day.month - 1, day.day) - 86400000);
  return {
    year: rolled.getUTCFullYear(),
    month: rolled.getUTCMonth() + 1,
    day: rolled.getUTCDate(),
  };
}

// Latest expected slot instant at or before `beforeMs` on the HONNE_JA_SLOTS
// 12:30/21:30 local grid. Walking `latestExpectedSlotInstant(slotMs - 1)`
// yields the previous grid slot, so the whole expected sequence is derivable
// backward from any instant. A slot that does not exist on a local calendar
// day (DST gap) is skipped: it was never expected to fire.
function latestExpectedSlotInstant(beforeMs, timeZone) {
  let day = localCalendarDay(beforeMs, timeZone);
  for (let dayIndex = 0; dayIndex < 4; dayIndex += 1) {
    for (let slotIndex = HONNE_JA_SLOTS.length - 1; slotIndex >= 0; slotIndex -= 1) {
      let instant;
      try {
        instant = zonedSlotInstant(day, HONNE_JA_SLOTS[slotIndex], timeZone);
      } catch {
        continue;
      }
      if (Date.parse(instant) <= beforeMs) return instant;
    }
    day = previousCalendarDay(day);
  }
  return null;
}

// Seven-cycle gate reader: rows are durable receipt rows for the Honne JA
// generation jobs ordered ASC by created_at ({outcome, receipt, created_at}).
// Spec §13 requires seven consecutive EXPECTED local cycles without missed or
// duplicate effects, so the count is anchored to the 12:30/21:30 expected slot
// grid ending at the latest slot already due at `options.nowMs`:
//   * every expected slot in the trailing run must hold exactly ONE completed
//     row whose receipt passes the generation adapter's own verification;
//   * an expected slot that passed with NO receipt row (scheduler off, scan
//     dead) is a missed effect — it breaks the streak and is reported in
//     `missed_slots`;
//   * a failed or unverifiable row, a duplicate row for one slot, and an
//     off-grid slot all break the streak;
//   * a slot still in the future (or not yet due today) is simply not
//     expected yet and never counts as missed.
function honneJaShadowStatus(rows, options = {}) {
  if (!Array.isArray(rows)) {
    throw new Error("honne JA shadow status receipts are invalid");
  }
  const expected = options.expected == null ? EXPECTED_SHADOW_CYCLES : options.expected;
  if (!Number.isInteger(expected) || expected < 1) {
    throw new Error("honne JA shadow status expectation is invalid");
  }
  const nowMs = options.nowMs == null ? Date.now() : options.nowMs;
  if (typeof nowMs !== "number" || !Number.isFinite(nowMs)) {
    throw new Error("honne JA shadow status time is invalid");
  }
  const timeZone = String(options.timeZone || "Asia/Tokyo").trim();

  // Trailing rows that are completed AND verifiable; any failed or
  // unverifiable row bounds the run (existing reset behavior preserved).
  const trailing = [];
  for (let index = rows.length - 1; index >= 0; index -= 1) {
    const row = rows[index];
    if (
      !row
      || row.outcome !== "completed"
      || !verifyMarketingVideoGenerationReceipt(row.receipt)
    ) {
      break;
    }
    trailing.unshift({
      slot: row.receipt.slot,
      hook_id: row.receipt.hook_id,
      creative_id: row.receipt.creative_id,
      generated_at: row.receipt.generated_at,
      recorded_at: String(row.created_at == null ? "" : row.created_at),
    });
  }

  // Match the trailing rows (newest first) one-to-one against the expected
  // slot grid walked backward from now.
  const receipts = [];
  const missedSlots = [];
  if (trailing.length > 0) {
    const slotCounts = new Map();
    for (const entry of trailing) {
      slotCounts.set(entry.slot, (slotCounts.get(entry.slot) || 0) + 1);
    }
    let expectedSlot = latestExpectedSlotInstant(nowMs, timeZone);
    let index = trailing.length - 1;
    while (index >= 0 && expectedSlot) {
      const entry = trailing[index];
      if (entry.slot !== expectedSlot) {
        // Gap: enumerate the expected slots newer than this receipt that have
        // no row (visibility), then stop — the streak is broken here. An
        // off-grid or future receipt slot enumerates nothing and also stops.
        const entryMs = Date.parse(entry.slot);
        let cursor = expectedSlot;
        while (
          cursor
          && Date.parse(cursor) > entryMs
          && missedSlots.length < MISSED_SLOT_REPORT_LIMIT
        ) {
          missedSlots.unshift(cursor);
          cursor = latestExpectedSlotInstant(Date.parse(cursor) - 1, timeZone);
        }
        break;
      }
      // Duplicate rows for one slot = duplicate effect = gate violation: the
      // duplicated slot never counts and nothing older than it counts.
      if (slotCounts.get(entry.slot) > 1) break;
      receipts.unshift(entry);
      index -= 1;
      expectedSlot = latestExpectedSlotInstant(Date.parse(expectedSlot) - 1, timeZone);
    }
  }

  const consecutive = receipts.length;
  return {
    consecutive,
    expected,
    display: `${Math.min(consecutive, expected)}/${expected}`,
    gate_met: consecutive >= expected,
    receipts,
    missed_slots: missedSlots,
  };
}

module.exports = {
  EXPECTED_SHADOW_CYCLES,
  SHADOW_HOLD_STATUS,
  appendHonneJaShadowHold,
  holdHonneJaShadowPublications,
  honneJaShadowConfig,
  honneJaShadowStatus,
  planHonneJaShadowGeneration,
};
