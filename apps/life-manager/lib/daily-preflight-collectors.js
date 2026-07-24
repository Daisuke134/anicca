"use strict";

const crypto = require("node:crypto");
const { execFile } = require("node:child_process");
const { promisify } = require("node:util");
const { resendSend } = require("./mail-resend.js");
const { makeGogMail } = require("./transport/mail-gog.js");

const execFileAsync = promisify(execFile);
const PYTHON = "/Users/operator/.cache/telegram-user-venv/bin/python";
const SIDECAR = "/Users/operator/anicca/skills/tools/telegram-user/tg_user.py";
const REQUIRED_UPDATES = Object.freeze(["message", "edited_message", "callback_query"]);
const MAX_AGE_MS = 15 * 60 * 1000;
const PROVIDER_TIMEOUT_MS = 15000;
const TELEGRAM_COLLECTOR_DEADLINE_MS = 179000;
const EMAIL_COLLECTOR_DEADLINE_MS = 120000;
const CONTROLLED_COLLECTION_DEADLINE_MS = 179000;

function closedFailure(code) {
  const error = new Error(code);
  error.classification = code;
  return error;
}

function hashRef(value) {
  return `sha256:${crypto.createHash("sha256").update(String(value)).digest("hex").slice(0, 16)}`;
}

/* node:coverage ignore next 11 */
function sleepMs(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal && signal.aborted) return reject(signal.reason || closedFailure("operation_aborted"));
    const timer = setTimeout(resolve, ms);
    if (signal) signal.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(signal.reason || closedFailure("operation_aborted"));
    }, { once: true });
  });
}

async function withinDeadline(operation, deadlineMs, code, parentSignal) {
  const controller = new AbortController();
  const abortFromParent = () => controller.abort(parentSignal.reason || closedFailure(code));
  if (parentSignal) {
    if (parentSignal.aborted) abortFromParent();
    else parentSignal.addEventListener("abort", abortFromParent, { once: true });
  }
  let timer;
  try {
    const timeout = new Promise((_, reject) => { timer = setTimeout(() => {
      const failure = closedFailure(code);
      controller.abort(failure);
      reject(failure);
    }, deadlineMs); });
    const pending = operation(controller.signal);
    /* node:coverage ignore next 4 */
    return await Promise.race([
      pending,
      timeout,
    ]);
  } finally {
    clearTimeout(timer);
    if (parentSignal) parentSignal.removeEventListener("abort", abortFromParent);
    if (!controller.signal.aborted) controller.abort(closedFailure("operation_complete"));
  }
}

/* node:coverage ignore next 3 */
async function sanitizedCall(code, operation) {
  try { return await operation(); } catch { throw closedFailure(code); }
}

/* node:coverage ignore next 8 */
function serviceBase(env) {
  if (env.LIFE_CALL_HEALTH_URL) return String(env.LIFE_CALL_HEALTH_URL).replace(/\/health\/?$/, "");
  if (env.RAILWAY_PUBLIC_DOMAIN) return `https://${String(env.RAILWAY_PUBLIC_DOMAIN).replace(/^https?:\/\//, "")}`;
  if (env.PUBLIC_WSS) return String(env.PUBLIC_WSS).replace(/^wss:/, "https:").replace(/^ws:/, "http:").replace(/\/$/, "");
  return String(env.PUBLIC_BASE || env.ANICCA_PROXY_BASE_URL || "").replace(/\/$/, "");
}

async function callTelegramBot(token, method, parentSignal) {
  /* node:coverage ignore next 3 */
  const signal = parentSignal
    ? AbortSignal.any([parentSignal, AbortSignal.timeout(PROVIDER_TIMEOUT_MS)])
    : AbortSignal.timeout(PROVIDER_TIMEOUT_MS);
  const response = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
    signal,
  });
  if (!response.ok) throw closedFailure("telegram_provider_rejected");
  let body;
  try { body = await response.json(); } catch { body = null; }
  if (!body || body.ok !== true) throw closedFailure("telegram_provider_rejected");
  return body;
}

async function callPinnedSidecar(args, parentSignal) {
  /* node:coverage ignore next 3 */
  const signal = parentSignal
    ? AbortSignal.any([parentSignal, AbortSignal.timeout(PROVIDER_TIMEOUT_MS)])
    : AbortSignal.timeout(PROVIDER_TIMEOUT_MS);
  try {
    const { stdout } = await execFileAsync(PYTHON, [SIDECAR, ...args], {
      timeout: PROVIDER_TIMEOUT_MS, signal, maxBuffer: 1024 * 1024, encoding: "utf8",
    });
    const value = JSON.parse(stdout);
    if (!value || value.ok !== true) throw closedFailure("telegram_mtproto_unavailable");
    return value;
  } catch { throw closedFailure("telegram_mtproto_unavailable"); }
}

async function writePanelCommand(peer, command, signal) {
  const result = await callPinnedSidecar(["send", peer, command], signal);
  if (!Number.isInteger(result.sent_id)) throw closedFailure("telegram_send_rejected");
  return { id: result.sent_id, atMs: Date.now() };
}

async function readPanelReplies(peer, signal) {
  const result = await callPinnedSidecar(["read", peer, "20"], signal);
  return (Array.isArray(result.messages) ? result.messages : []).map(message => ({
    id: Number(message.id), atMs: Date.parse(message.date), inbound: message.out === false,
  }));
}

function validateTelegramObservation(value, nowMs) {
  if (!value || !Number.isInteger(value.sentId) || !Number.isInteger(value.replyId) || value.replyId <= value.sentId ||
      !Number.isFinite(value.sentAtMs) || !Number.isFinite(value.replyAtMs) || value.replyAtMs < value.sentAtMs ||
      value.replyAtMs < nowMs - MAX_AGE_MS) throw closedFailure("telegram_round_trip_unverified");
  if (value.webhookUrl !== value.expectedWebhookUrl) throw closedFailure("telegram_webhook_url_mismatch");
  if (!Array.isArray(value.allowedUpdates) || REQUIRED_UPDATES.some(update => !value.allowedUpdates.includes(update))) {
    throw closedFailure("telegram_allowed_updates");
  }
  if (value.lastError) throw closedFailure("telegram_provider_error");
  const samples = value.pendingUpdateSamples;
  if (!Array.isArray(samples) || !samples.length || samples.some(n => !Number.isInteger(n) || n < 0) || samples.at(-1) !== 0) {
    throw closedFailure("telegram_backlog");
  }
  return Object.freeze({
    attempted: true, verified: true, checkedAt: new Date(nowMs).toISOString(),
    requestMessageRef: hashRef(value.sentId), replyMessageRef: hashRef(value.replyId),
    exactUrl: true, allowedUpdates: [...value.allowedUpdates].sort(), providerError: false,
    pendingUpdateCount: 0, pendingUpdateSamples: [...samples],
    replyReadCount: value.replyReadCount,
    webhookReadCount: value.webhookReadCount,
  });
}

async function collectTelegramWithSignal(parentSignal) {
  return withinDeadline(async signal => {
    const env = process.env;
    if (!env.LM_TELEGRAM_BOT_TOKEN || !serviceBase(env)) throw closedFailure("telegram_configuration");
    const me = await sanitizedCall("telegram_provider_rejected", () => callTelegramBot(env.LM_TELEGRAM_BOT_TOKEN, "getMe", signal));
    const username = me && me.result && me.result.username;
    if (!/^[A-Za-z0-9_]{5,32}$/.test(String(username || ""))) throw closedFailure("telegram_bot_identity");
    const peer = `@${username}`;
    const nonce = crypto.randomBytes(12).toString("hex");
    const sent = await sanitizedCall("telegram_send_rejected", () => writePanelCommand(peer, `/panel core8d_${nonce}`, signal));
    let reply;
    let replyReadCount = 0;
    for (let index = 0; index < 6; index += 1) {
      const messages = await sanitizedCall("telegram_mtproto_unavailable", () => readPanelReplies(peer, signal));
      replyReadCount += 1;
      reply = messages.find(message => message.inbound && Number.isInteger(message.id) && message.id > sent.id && message.atMs >= sent.atMs);
      if (reply) break;
      if (index + 1 < 6) await sleepMs(2000, signal);
    }
    if (!reply) throw closedFailure("telegram_reply_timeout");
    const samples = []; let info;
    for (let index = 0; index < 3; index += 1) {
      const response = await sanitizedCall("telegram_provider_rejected", () => callTelegramBot(env.LM_TELEGRAM_BOT_TOKEN, "getWebhookInfo", signal)); info = response && response.result;
      samples.push(Number(info && info.pending_update_count));
      if (samples.at(-1) === 0) break;
      if (index + 1 < 3) await sleepMs(2000, signal);
    }
    const expectedWebhookUrl = `${serviceBase(env)}/telegram`;
    return validateTelegramObservation({
      sentId: sent.id, replyId: reply.id, sentAtMs: sent.atMs, replyAtMs: reply.atMs,
      webhookUrl: String(info && info.url || ""), expectedWebhookUrl,
      allowedUpdates: info && info.allowed_updates, lastError: Boolean(info && (info.last_error_message || info.last_error_date)),
      pendingUpdateSamples: samples, replyReadCount, webhookReadCount: samples.length,
    }, Date.now());
  }, TELEGRAM_COLLECTOR_DEADLINE_MS, "telegram_collector_deadline", parentSignal);
}

const collectProductionTelegram = collectTelegramWithSignal;

function validateEmailObservation(value, nowMs, allowedRecipients = []) {
  const allowed = new Set(allowedRecipients.map(address => String(address).trim().toLowerCase()).filter(Boolean));
  if (!value || !value.recipient || value.recipient !== value.receiveIdentity || !allowed.has(value.recipient)) {
    throw closedFailure("email_recipient_not_controlled");
  }
  if (!value.providerAcceptedId) throw closedFailure("email_send_rejected");
  if (!value.receiptMessageId || !value.nonce || value.receivedNonce !== value.nonce) throw closedFailure("email_receive_timeout");
  const lowerMs = value.receivedAtLowerMs;
  const upperMs = value.receivedAtUpperMs;
  if (!Number.isFinite(value.sentAtMs) || !Number.isFinite(lowerMs) || !Number.isFinite(upperMs) ||
      lowerMs > upperMs || value.sentAtMs < nowMs - MAX_AGE_MS || value.sentAtMs > nowMs ||
      lowerMs > nowMs || upperMs < value.sentAtMs || upperMs < nowMs - MAX_AGE_MS) {
    throw closedFailure("email_receipt_stale");
  }
  return Object.freeze({
    attempted: true, providerAccepted: true, inboxReceived: true, recipientOwned: true,
    checkedAt: new Date(nowMs).toISOString(), providerRef: hashRef(value.providerAcceptedId),
    messageIdRef: hashRef(value.receiptMessageId), inboxReadCount: value.inboxReadCount,
  });
}

async function collectEmailWithSignal(parentSignal) {
  return withinDeadline(async signal => {
    const env = process.env;
    const mail = makeGogMail({ bin: "/opt/homebrew/bin/gog", account: env.GOG_ACCOUNT });
    const recipient = String(env.GOG_ACCOUNT || "").trim().toLowerCase();
    const receiveIdentity = String(env.GOG_ACCOUNT || "").trim().toLowerCase();
    const allowedRecipients = String(env.LM_CONTROLLED_EMAIL_ALLOWLIST || "").split(",")
      .map(address => address.trim().toLowerCase()).filter(Boolean);
    if (!recipient || !allowedRecipients.includes(recipient)) throw closedFailure("email_recipient_not_controlled");
    if (!env.RESEND_API_KEY) throw closedFailure("email_configuration");
    const nonce = crypto.randomBytes(18).toString("hex");
    const accepted = await resendSend({ to: recipient, subject: `Life Manager controlled check ${nonce}`,
      text: `Controlled delivery check ${nonce}. No action is required.`, resendKey: env.RESEND_API_KEY,
      /* node:coverage ignore next 2 */
      fetchImpl: (url, options = {}) => fetch(url, { ...options,
        signal: AbortSignal.any([signal, AbortSignal.timeout(PROVIDER_TIMEOUT_MS)]) }) });
    if (!accepted || accepted.sent !== true || !accepted.id) throw closedFailure("email_send_rejected"); const sentAtMs = Date.now();
    let receipt; let inboxReadCount = 0;
    for (let index = 0; index < 6; index += 1) {
      receipt = signal
        ? await mail.findReceipt({ nonce, afterMs: sentAtMs, signal })
        : await mail.findReceipt({ nonce, afterMs: sentAtMs });
      inboxReadCount += 1;
      if (receipt && receipt.id) break;
      if (index + 1 < 6) await sleepMs(3000, signal);
    }
    return validateEmailObservation({ recipient, receiveIdentity,
      providerAcceptedId: accepted.id, receiptMessageId: receipt && receipt.id,
      nonce, receivedNonce: receipt && receipt.matchedNonce, sentAtMs,
      receivedAtLowerMs: receipt && receipt.receivedAtLowerMs,
      receivedAtUpperMs: receipt && receipt.receivedAtUpperMs, inboxReadCount,
    }, Date.now(), allowedRecipients);
  }, EMAIL_COLLECTOR_DEADLINE_MS, "email_collector_deadline", parentSignal);
}

const collectProductionEmail = collectEmailWithSignal;

async function collectProductionControlledL3() {
  return withinDeadline(async signal => {
    const [telegram, email] = await Promise.all([collectTelegramWithSignal(signal), collectEmailWithSignal(signal)]);
    return Object.freeze({ telegram, email });
  }, CONTROLLED_COLLECTION_DEADLINE_MS, "controlled_collection_deadline");
}

module.exports = { collectProductionControlledL3, validateEmailObservation, validateTelegramObservation };
