"use strict";

const { createHash } = require("node:crypto");

const TERMINAL_STATUSES = new Set([
  "completed",
  "possibly_completed",
  "handoff_required",
  "failed",
]);
const TRACE_STAGES = new Set([
  "claimed",
  "discovery",
  "selected",
  "action_started",
  "action_observed",
  "provider_readback",
  "telegram_sent",
  "evidence_sent",
  "steel_released",
]);

function nonEmpty(value, label, max = 1000) {
  const text = String(value == null ? "" : value).trim();
  if (!text || text.length > max) throw new Error(`${label} invalid`);
  return text;
}

let defaultPool;

function database(opts = {}) {
  if (typeof opts.query === "function") return { query: opts.query };
  const connectionString = String(
    opts.connectionString || process.env.LM_FEEDBACK_DATABASE_URL || "",
  ).trim();
  if (!connectionString) throw new Error("browser job store unavailable");
  if (!defaultPool) {
    const Pool = opts.Pool || require("pg").Pool;
    defaultPool = new Pool({ connectionString, max: 4 });
  }
  return { query: defaultPool.query.bind(defaultPool) };
}

function buildBrowserJob(input) {
  const uid = nonEmpty(input && input.uid, "browser job uid", 200);
  const chatId = nonEmpty(input && input.chatId, "browser job chat id", 100);
  const messageId = nonEmpty(input && input.messageId, "browser job message id", 100);
  const updateId = nonEmpty(input && input.updateId, "browser job update id", 100);
  const rawPrompt = nonEmpty(input && input.rawPrompt, "browser raw prompt", 10_000);
  const classification = input && input.classification;
  if (!classification || typeof classification !== "object") throw new Error("browser classification invalid");
  const locale = nonEmpty(classification.locale, "browser job locale", 8);
  if (!["en", "ja"].includes(locale)) throw new Error("browser job locale invalid");
  return Object.freeze({
    uid,
    telegram_chat_id: chatId,
    telegram_message_id: messageId,
    telegram_update_id: updateId,
    prompt_hash: createHash("sha256").update(rawPrompt).digest("hex"),
    goal: nonEmpty(classification.goal, "browser job goal", 1000),
    locale,
    action_kind: nonEmpty(classification.actionKind, "browser job action kind", 100),
    requires_login: classification.requiresLogin === true,
    status: "queued",
    trace: [],
  });
}

async function enqueueBrowserJob(input, opts = {}) {
  const job = buildBrowserJob(input);
  const { query } = database(opts);
  const inserted = (await query(`
    INSERT INTO public.lm_browser_jobs (
      uid, telegram_chat_id, telegram_message_id, telegram_update_id,
      prompt_hash, goal, locale, action_kind, requires_login, status
    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
    ON CONFLICT (uid, telegram_chat_id, telegram_message_id) DO NOTHING
    RETURNING *
  `, [
    job.uid,
    job.telegram_chat_id,
    job.telegram_message_id,
    job.telegram_update_id,
    job.prompt_hash,
    job.goal,
    job.locale,
    job.action_kind,
    job.requires_login,
    job.status,
  ])).rows;
  if (inserted.length === 1) return { created: true, job: inserted[0] };
  if (inserted.length > 1) throw new Error("browser job enqueue returned multiple rows");

  const existing = (await query(`
    SELECT * FROM public.lm_browser_jobs
    WHERE uid = $1 AND telegram_chat_id = $2 AND telegram_message_id = $3
    LIMIT 1
  `, [job.uid, job.telegram_chat_id, job.telegram_message_id])).rows;
  if (existing.length !== 1) throw new Error("browser job duplicate was not readable");
  return { created: false, job: existing[0] };
}

async function claimBrowserJob(opts = {}) {
  const { query } = database(opts);
  const leaseSeconds = Number.isInteger(opts.leaseSeconds) ? opts.leaseSeconds : 480;
  if (leaseSeconds < 30 || leaseSeconds > 900) throw new Error("browser job lease invalid");
  const claimed = (await query(
    "SELECT * FROM public.claim_lm_browser_job($1)",
    [leaseSeconds],
  )).rows;
  if (claimed.length > 1) throw new Error("browser job claim returned multiple rows");
  return claimed[0] || null;
}

async function appendBrowserTrace(jobId, stage, meta, opts = {}) {
  const id = nonEmpty(jobId, "browser job id", 100);
  if (!TRACE_STAGES.has(stage)) throw new Error("browser trace stage invalid");
  const bounded = meta && typeof meta === "object" && !Array.isArray(meta) ? meta : {};
  if (Buffer.byteLength(JSON.stringify(bounded)) > 8192) throw new Error("browser trace metadata too large");
  const { query } = database(opts);
  const updated = (await query(
    "SELECT * FROM public.append_lm_browser_job_trace($1, $2, $3::jsonb)",
    [id, stage, JSON.stringify(bounded)],
  )).rows;
  if (updated.length !== 1) throw new Error("browser trace append lost job");
  return true;
}

async function finishBrowserJob(jobId, terminal, opts = {}) {
  const id = nonEmpty(jobId, "browser job id", 100);
  if (!terminal || !TERMINAL_STATUSES.has(terminal.status)) throw new Error("browser terminal status invalid");
  const messageId = terminal.telegram_message_id == null ? null : Number(terminal.telegram_message_id);
  if (messageId !== null && (!Number.isSafeInteger(messageId) || messageId <= 0)) {
    throw new Error("browser Telegram message id invalid");
  }
  const receipt = {
    session_id: terminal.session_id || null,
    selected_url: terminal.selected_url || null,
    selected_origin: terminal.selected_origin || null,
    selection_reason: terminal.selection_reason || null,
    action: terminal.action || null,
    provider_receipt: terminal.provider_receipt || null,
    evidence_message_id: terminal.evidence_message_id || null,
    evidence_sha256: terminal.evidence_sha256 || null,
    steel_released: terminal.steel_released === true,
  };
  if (Buffer.byteLength(JSON.stringify(receipt)) > 16_384) throw new Error("browser receipt too large");
  const { query } = database(opts);
  const updated = (await query(
    "SELECT * FROM public.finish_lm_browser_job($1, $2, $3::jsonb, $4)",
    [id, terminal.status, JSON.stringify(receipt), messageId],
  )).rows;
  if (updated.length !== 1) throw new Error("browser job finish lost claim");
  return true;
}

module.exports = {
  buildBrowserJob,
  enqueueBrowserJob,
  claimBrowserJob,
  appendBrowserTrace,
  finishBrowserJob,
};
