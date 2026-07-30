// lib/outbound-runtime.js — the node-side outbound pass runtime.
//
// Loads a config pack, runs the 6-stage engine (runtime/loop/outbound/pipeline.mjs), appends the
// trace ledger, records the pass's CLAIM on the streak, and reports to Telegram through the
// existing lib/telegram.js.
//
// Two honesty rules are load-bearing here:
//   1. Telegram degrades, never lies: no token or no chat id => {status:"skipped",
//      reason:"telegram_unbound"}. It never throws and never reports a send that did not happen.
//   2. This runtime CANNOT award a green day. It calls applyClaim, which records what the pass
//      says it did. Only scripts/outbound-verify.js — which re-reads the artifact off disk and
//      re-runs the evidence gate — may call applyDay.
"use strict";

const path = require("node:path");
const { pathToFileURL } = require("node:url");
const fs = require("node:fs");

const { loadPackConfig, isDenied, PACKS } = require("./outbound-config.js");
const { sendMessage: telegramSendMessage } = require("./telegram.js");
const { resolveDataRoot } = require("./runtime-paths.js");

const ENGINE_DIR = path.join(__dirname, "..", "..", "..", "runtime", "loop", "outbound");
const engineUrl = (file) => pathToFileURL(path.join(ENGINE_DIR, file)).href;

const loadPipeline = () => import(engineUrl("pipeline.mjs"));
const loadStreak = () => import(engineUrl("streak.mjs"));

function assertKnownPack(pack) {
  const name = String(pack == null ? "" : pack);
  if (!PACKS.includes(name)) {
    throw new Error(`outbound pack must be one of ${PACKS.join(", ")}, got ${JSON.stringify(name)}`);
  }
  return name;
}

// ------------------------------------------------------------------ trace ledger (spec §6)

function targetId(target) {
  if (target == null) return null;
  if (typeof target === "string") return target;
  return String(target.id || target.name || target.url || "");
}

// The ledger records the artifact PATH, never its bytes: the verifier re-reads the file from disk,
// so a copy of the bytes inside the ledger would just be a second self-report to trust.
function traceEvidence(evidence) {
  if (!evidence || typeof evidence !== "object") return null;
  const e2 = evidence.e2 && typeof evidence.e2 === "object" ? { ...evidence.e2 } : null;
  if (e2) delete e2.bytes;
  return {
    e1: evidence.e1 == null ? null : evidence.e1,
    e2,
    e3: evidence.e3 == null ? null : evidence.e3,
  };
}

function traceEntry({ pack, segment, target, template_variant: variant, result, replyText }) {
  return {
    ts: result.ts,
    pack: String(pack),
    segment: segment == null ? null : String(segment),
    target: targetId(target),
    template_variant: variant == null ? null : String(variant),
    sent_at: result.status === "verified" ? result.ts : null,
    evidence: traceEvidence(result.evidence),
    stage_reached: result.stage_reached,
    outcome: result.status,
    outcome_at: result.ts,
    reply_text: replyText == null ? null : String(replyText),
  };
}

async function traceLedgerFile(homeDir, pack) {
  const { traceLedgerPath } = await loadStreak();
  return traceLedgerPath(homeDir, pack);
}

// Scratch state lives under the canonical portable data root (LM_DATA_DIR, else
// <home>/.local/state/life-manager) — never in the repo, and never under the legacy runtime root
// that lib/runtime-paths.js and scripts/scan-legacy-paths.js both reject.
function traceLedgerFileSync(homeDir, pack, env = {}) {
  const root = resolveDataRoot({ HOME: String(homeDir), ...(env.LM_DATA_DIR ? { LM_DATA_DIR: env.LM_DATA_DIR } : {}) });
  return path.join(root, "outbound", `trace-${assertKnownPack(pack)}.jsonl`);
}

function appendTrace(homeDir, pack, entries) {
  const file = traceLedgerFileSync(homeDir, pack);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const rows = (Array.isArray(entries) ? entries : []);
  if (rows.length > 0) {
    fs.appendFileSync(file, `${rows.map((row) => JSON.stringify(row)).join("\n")}\n`, "utf8");
  } else if (!fs.existsSync(file)) {
    fs.writeFileSync(file, "", "utf8");
  }
  return file;
}

function readTrace(homeDir, pack) {
  const file = traceLedgerFileSync(homeDir, pack);
  let raw;
  try {
    raw = fs.readFileSync(file, "utf8");
  } catch (error) {
    if (error && error.code === "ENOENT") return [];
    throw error;
  }
  return raw.split("\n").filter((line) => line.trim()).map((line, index) => {
    try {
      return JSON.parse(line);
    } catch (error) {
      throw new Error(`outbound trace ${file} line ${index + 1} is not valid JSON: ${error.message}`);
    }
  });
}

// ------------------------------------------------------------------ Telegram report

function renderOutboundReport(pack, results) {
  const rows = Array.isArray(results) ? results : [];
  const verified = rows.filter((row) => row.status === "verified");
  const failed = rows.filter((row) => row.status !== "verified");
  const lines = [
    `<b>outbound / ${pack}</b>`,
    `verified ${verified.length} · failed ${failed.length}`,
  ];
  for (const row of verified) lines.push(`✅ ${targetId(row.target) || "(no target)"}`);
  for (const row of failed) {
    lines.push(`❌ ${targetId(row.target) || "(no target)"} — ${row.stage_reached}: ${row.reason}`);
  }
  return lines.join("\n");
}

async function sendOutboundReport({ token, chatId, pack, results, sendMessage }) {
  const botToken = String(token || "");
  const chat = String(chatId == null ? "" : chatId);
  if (!botToken || !chat) {
    // Honest degradation: an unbound Telegram is a missing binding, not a failed pass.
    return { status: "skipped", reason: "telegram_unbound" };
  }
  const send = typeof sendMessage === "function" ? sendMessage : telegramSendMessage;
  let response;
  try {
    response = await send(botToken, chat, renderOutboundReport(pack, results));
  } catch (error) {
    return { status: "failed", reason: `telegram_threw: ${error && error.message ? error.message : error}` };
  }
  const messageId = response && response.result && response.result.message_id;
  if (!response || response.ok !== true || !Number.isInteger(messageId)) {
    const detail = (response && (response.description || response.error)) || "no message id";
    return { status: "failed", reason: `telegram_rejected: ${detail}` };
  }
  return { status: "sent", telegram_message_id: messageId };
}

// ------------------------------------------------------------------ policy wrapper

// daily_cap and the denylist are the deterministic half of QUALIFY (spec §3.1). They are applied
// here, around the injected stages, so the pipeline stays pure and the model is never even asked
// about a denylisted target.
function withPolicy(stages, config) {
  return {
    ...stages,
    discover: async (context) => {
      const outcome = await stages.discover(context);
      if (!outcome || outcome.ok !== true) return outcome;
      const candidates = Array.isArray(outcome.candidates) ? outcome.candidates : [];
      return { ...outcome, candidates: candidates.slice(0, config.daily_cap) };
    },
    qualify: async (context) => {
      const needle = isDenied(config, context.target);
      if (needle) return { ok: false, reason: `denylisted:${needle}` };
      return stages.qualify(context);
    },
  };
}

// ------------------------------------------------------------------ the pass

async function runOutboundPass(request = {}) {
  const pack = assertKnownPack(request.pack);
  const homeDir = String(request.homeDir || process.env.HOME || "");
  if (!homeDir) throw new Error("outbound pass needs a home directory for its scratch state");
  const nowMs = request.nowMs == null ? Date.now() : Number(request.nowMs);
  if (!Number.isFinite(nowMs)) throw new Error("outbound pass needs nowMs as an instant");
  const config = request.config || loadPackConfig(pack);
  const telegram = request.telegram || {};

  const { applyClaim, readStreak, writeStreak, streakStatePath, heartbeatPath, touchHeartbeat } =
    await loadStreak();
  const statePath = streakStatePath(homeDir);
  const beat = () => touchHeartbeat(heartbeatPath(homeDir), new Date(nowMs));

  if (config.enabled !== true) {
    beat();
    return {
      status: "skipped",
      reason: "pack_disabled",
      pack,
      ts: new Date(nowMs).toISOString(),
      results: [],
      streak: readStreak(statePath),
      telegram: { status: "skipped", reason: "pack_disabled" },
    };
  }

  const { runPipeline } = await loadPipeline();
  const pass = await runPipeline({
    pack,
    config,
    stages: withPolicy(request.stages || {}, config),
    nowMs,
  });

  const date = new Date(nowMs).toISOString().slice(0, 10);
  const entries = pass.results.map((result) => traceEntry({
    pack,
    segment: request.segment == null ? (config.segments[0] || null) : request.segment,
    target: result.target,
    template_variant: config.template_variant || null,
    result,
  }));
  const traceFile = appendTrace(homeDir, pack, entries);

  const claimed = pass.results.filter((result) => result.status === "verified").length;
  const streak = applyClaim(readStreak(statePath), { pack, date, claimedCount: claimed });
  writeStreak(statePath, streak);

  const report = await sendOutboundReport({
    token: telegram.token,
    chatId: telegram.chatId,
    pack,
    results: pass.results,
    sendMessage: telegram.sendMessage,
  });

  beat();
  return {
    status: "completed",
    pack,
    ts: pass.ts,
    results: pass.results,
    claimed,
    trace_file: traceFile,
    streak,
    telegram: report,
  };
}

module.exports = {
  appendTrace,
  readTrace,
  traceEntry,
  traceLedgerFile,
  renderOutboundReport,
  sendOutboundReport,
  runOutboundPass,
  withPolicy,
};
