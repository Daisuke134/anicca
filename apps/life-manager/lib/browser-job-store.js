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
  "provider_readback",
  "telegram_sent",
  "steel_released",
]);

function nonEmpty(value, label, max = 1000) {
  const text = String(value == null ? "" : value).trim();
  if (!text || text.length > max) throw new Error(`${label} invalid`);
  return text;
}

function credentials(opts = {}) {
  const supaUrl = String(opts.supaUrl || process.env.SUPABASE_URL || "").replace(/\/$/, "");
  const supaKey = opts.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY;
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  if (!supaUrl || !supaKey || typeof fetchImpl !== "function") {
    throw new Error("browser job store unavailable");
  }
  return { supaUrl, supaKey, fetchImpl };
}

function headers(key, extra = {}) {
  return {
    apikey: key,
    Authorization: `Bearer ${key}`,
    "Content-Type": "application/json",
    ...extra,
  };
}

async function rows(response, label) {
  if (!response || !response.ok) {
    const status = response ? response.status : "no response";
    throw new Error(`${label} failed (${status})`);
  }
  const body = await response.json();
  if (!Array.isArray(body)) throw new Error(`${label} returned non-array body`);
  return body;
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
  const { supaUrl, supaKey, fetchImpl } = credentials(opts);
  const inserted = await rows(await fetchImpl(`${supaUrl}/rest/v1/lm_browser_jobs`, {
    method: "POST",
    headers: headers(supaKey, {
      Prefer: "resolution=ignore-duplicates,return=representation",
    }),
    body: JSON.stringify(job),
  }), "browser job enqueue");
  if (inserted.length === 1) return { created: true, job: inserted[0] };
  if (inserted.length > 1) throw new Error("browser job enqueue returned multiple rows");

  const query = `uid=eq.${encodeURIComponent(job.uid)}` +
    `&telegram_chat_id=eq.${encodeURIComponent(job.telegram_chat_id)}` +
    `&telegram_message_id=eq.${encodeURIComponent(job.telegram_message_id)}` +
    "&select=*&limit=1";
  const existing = await rows(await fetchImpl(`${supaUrl}/rest/v1/lm_browser_jobs?${query}`, {
    headers: headers(supaKey),
  }), "browser job duplicate read");
  if (existing.length !== 1) throw new Error("browser job duplicate was not readable");
  return { created: false, job: existing[0] };
}

async function claimBrowserJob(opts = {}) {
  const { supaUrl, supaKey, fetchImpl } = credentials(opts);
  const leaseSeconds = Number.isInteger(opts.leaseSeconds) ? opts.leaseSeconds : 180;
  if (leaseSeconds < 30 || leaseSeconds > 900) throw new Error("browser job lease invalid");
  const claimed = await rows(await fetchImpl(`${supaUrl}/rest/v1/rpc/claim_lm_browser_job`, {
    method: "POST",
    headers: headers(supaKey),
    body: JSON.stringify({ p_lease_seconds: leaseSeconds }),
  }), "browser job claim");
  if (claimed.length > 1) throw new Error("browser job claim returned multiple rows");
  return claimed[0] || null;
}

async function appendBrowserTrace(jobId, stage, meta, opts = {}) {
  const id = nonEmpty(jobId, "browser job id", 100);
  if (!TRACE_STAGES.has(stage)) throw new Error("browser trace stage invalid");
  const bounded = meta && typeof meta === "object" && !Array.isArray(meta) ? meta : {};
  if (Buffer.byteLength(JSON.stringify(bounded)) > 8192) throw new Error("browser trace metadata too large");
  const { supaUrl, supaKey, fetchImpl } = credentials(opts);
  const updated = await rows(await fetchImpl(`${supaUrl}/rest/v1/rpc/append_lm_browser_job_trace`, {
    method: "POST",
    headers: headers(supaKey),
    body: JSON.stringify({ p_job_id: id, p_stage: stage, p_meta: bounded }),
  }), "browser trace append");
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
    selected_url: terminal.selected_url || null,
    provider_receipt: terminal.provider_receipt || null,
    steel_released: terminal.steel_released === true,
  };
  if (Buffer.byteLength(JSON.stringify(receipt)) > 16_384) throw new Error("browser receipt too large");
  const { supaUrl, supaKey, fetchImpl } = credentials(opts);
  const updated = await rows(await fetchImpl(`${supaUrl}/rest/v1/rpc/finish_lm_browser_job`, {
    method: "POST",
    headers: headers(supaKey),
    body: JSON.stringify({
      p_job_id: id,
      p_status: terminal.status,
      p_receipt: receipt,
      p_telegram_message_id: messageId,
    }),
  }), "browser job finish");
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

