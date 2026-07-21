"use strict";

const crypto = require("node:crypto");
const { execFile } = require("node:child_process");
const { promisify } = require("node:util");
const { resendSend } = require("./mail-resend.js");
const { makeGogMail } = require("./transport/mail-gog.js");

const execFileAsync = promisify(execFile);
const PYTHON = "/Users/anicca/.cache/telegram-user-venv/bin/python";
const SIDECAR = "/Users/anicca/anicca/skills/tools/telegram-user/tg_user.py";
const REQUIRED_UPDATES = Object.freeze(["message", "edited_message", "callback_query"]);
const MAX_AGE_MS = 15 * 60 * 1000;

function closedFailure(code) {
  const error = new Error(code);
  error.classification = code;
  return error;
}

function hashRef(value) {
  return `sha256:${crypto.createHash("sha256").update(String(value)).digest("hex").slice(0, 16)}`;
}

function sleepMs(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

async function sanitizedCall(code, operation) {
  try { return await operation(); } catch { throw closedFailure(code); }
}

function serviceBase(env) {
  if (env.LIFE_CALL_HEALTH_URL) return String(env.LIFE_CALL_HEALTH_URL).replace(/\/health\/?$/, "");
  if (env.RAILWAY_PUBLIC_DOMAIN) return `https://${String(env.RAILWAY_PUBLIC_DOMAIN).replace(/^https?:\/\//, "")}`;
  if (env.PUBLIC_WSS) return String(env.PUBLIC_WSS).replace(/^wss:/, "https:").replace(/^ws:/, "http:").replace(/\/$/, "");
  return String(env.PUBLIC_BASE || env.ANICCA_PROXY_BASE_URL || "").replace(/\/$/, "");
}

async function defaultBotCall(token, method, fetchImpl = fetch) {
  const response = await fetchImpl(`https://api.telegram.org/bot${token}/${method}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
  });
  if (!response.ok) throw closedFailure("telegram_provider_rejected");
  const body = await response.json().catch(() => null);
  if (!body || body.ok !== true) throw closedFailure("telegram_provider_rejected");
  return body;
}

async function sidecar(args, execFileImpl = execFileAsync) {
  try {
    const { stdout } = await execFileImpl(PYTHON, [SIDECAR, ...args], {
      timeout: 15000, maxBuffer: 1024 * 1024, encoding: "utf8",
    });
    const value = JSON.parse(stdout);
    if (!value || value.ok !== true) throw closedFailure("telegram_mtproto_unavailable");
    return value;
  } catch { throw closedFailure("telegram_mtproto_unavailable"); }
}

async function defaultMtprotoSend(peer, command, now, execFileImpl) {
  const result = await sidecar(["send", peer, command], execFileImpl);
  if (!Number.isInteger(result.sent_id)) throw closedFailure("telegram_send_rejected");
  return { id: result.sent_id, atMs: now() };
}

async function defaultMtprotoRead(peer, execFileImpl) {
  const result = await sidecar(["read", peer, "20"], execFileImpl);
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
  });
}

function createTelegramCollector({ env = process.env, fetchImpl = fetch, botCall, mtprotoSend, mtprotoRead,
  execFileImpl = execFileAsync, sleep = sleepMs, now = Date.now, maxReplyPolls = 6, maxWebhookPolls = 3 } = {}) {
  const callBot = botCall || ((method) => defaultBotCall(env.LM_TELEGRAM_BOT_TOKEN, method, fetchImpl));
  const send = mtprotoSend || ((peer, command) => defaultMtprotoSend(peer, command, now, execFileImpl));
  const read = mtprotoRead || (peer => defaultMtprotoRead(peer, execFileImpl));
  return async function collectTelegram() {
    if (!env.LM_TELEGRAM_BOT_TOKEN || !serviceBase(env)) throw closedFailure("telegram_configuration");
    const me = await sanitizedCall("telegram_provider_rejected", () => callBot("getMe"));
    const username = me && me.result && me.result.username;
    if (!/^[A-Za-z0-9_]{5,32}$/.test(String(username || ""))) throw closedFailure("telegram_bot_identity");
    const peer = `@${username}`;
    const nonce = crypto.randomBytes(12).toString("hex");
    const sent = await sanitizedCall("telegram_send_rejected", () => send(peer, `/panel core8d_${nonce}`));
    let reply;
    for (let index = 0; index < maxReplyPolls; index += 1) {
      const messages = await sanitizedCall("telegram_mtproto_unavailable", () => read(peer));
      reply = messages.find(message => message.inbound && Number.isInteger(message.id) && message.id > sent.id && message.atMs >= sent.atMs);
      if (reply) break;
      if (index + 1 < maxReplyPolls) await sleep(2000);
    }
    if (!reply) throw closedFailure("telegram_reply_timeout");
    const samples = []; let info;
    for (let index = 0; index < maxWebhookPolls; index += 1) {
      const response = await sanitizedCall("telegram_provider_rejected", () => callBot("getWebhookInfo")); info = response && response.result;
      samples.push(Number(info && info.pending_update_count));
      if (samples.at(-1) === 0) break;
      if (index + 1 < maxWebhookPolls) await sleep(2000);
    }
    const expectedWebhookUrl = `${serviceBase(env)}/telegram`;
    return validateTelegramObservation({
      sentId: sent.id, replyId: reply.id, sentAtMs: sent.atMs, replyAtMs: reply.atMs,
      webhookUrl: String(info && info.url || ""), expectedWebhookUrl,
      allowedUpdates: info && info.allowed_updates, lastError: Boolean(info && (info.last_error_message || info.last_error_date)),
      pendingUpdateSamples: samples,
    }, now());
  };
}

function validateEmailObservation(value, nowMs, allowedRecipients = []) {
  const allowed = new Set(allowedRecipients.map(address => String(address).trim().toLowerCase()).filter(Boolean));
  if (!value || !value.recipient || value.recipient !== value.receiveIdentity || !allowed.has(value.recipient)) {
    throw closedFailure("email_recipient_not_controlled");
  }
  if (!value.providerAcceptedId) throw closedFailure("email_send_rejected");
  if (!value.receiptMessageId || !value.nonce || value.receivedNonce !== value.nonce) throw closedFailure("email_receive_timeout");
  if (!Number.isFinite(value.sentAtMs) || !Number.isFinite(value.receivedAtMs) || value.receivedAtMs < value.sentAtMs ||
      value.receivedAtMs < nowMs - MAX_AGE_MS) throw closedFailure("email_receipt_stale");
  return Object.freeze({
    attempted: true, providerAccepted: true, inboxReceived: true, recipientOwned: true,
    checkedAt: new Date(nowMs).toISOString(), providerRef: hashRef(value.providerAcceptedId),
    messageIdRef: hashRef(value.receiptMessageId),
  });
}

function createEmailCollector({ env = process.env, fetchImpl = fetch, send, findReceipt,
  mailFactory = makeGogMail, sleep = sleepMs, now = Date.now,
  randomNonce = () => crypto.randomBytes(18).toString("hex"), maxPolls = 6 } = {}) {
  const mail = mailFactory({ bin: "/opt/homebrew/bin/gog", account: env.GOG_ACCOUNT });
  const sendMail = send || (args => resendSend({ ...args, resendKey: env.RESEND_API_KEY, fetchImpl }));
  const receive = findReceipt || (args => mail.findReceipt(args));
  return async function collectEmail() {
    const recipient = String(env.GOG_ACCOUNT || "").trim().toLowerCase();
    const receiveIdentity = String(env.GOG_ACCOUNT || "").trim().toLowerCase();
    const allowedRecipients = String(env.LM_CONTROLLED_EMAIL_ALLOWLIST || "").split(",")
      .map(address => address.trim().toLowerCase()).filter(Boolean);
    if (!recipient || !allowedRecipients.includes(recipient)) throw closedFailure("email_recipient_not_controlled");
    if (!env.RESEND_API_KEY) throw closedFailure("email_configuration");
    const nonce = randomNonce(); const sentAtMs = now();
    const accepted = await sendMail({ to: recipient, subject: `Life Manager controlled check ${nonce}`,
      text: `Controlled delivery check ${nonce}. No action is required.` });
    if (!accepted || accepted.sent !== true || !accepted.id) throw closedFailure("email_send_rejected");
    let receipt;
    for (let index = 0; index < maxPolls; index += 1) {
      receipt = await receive({ nonce, afterMs: sentAtMs });
      if (receipt && receipt.id) break;
      if (index + 1 < maxPolls) await sleep(3000);
    }
    return validateEmailObservation({ recipient, receiveIdentity,
      providerAcceptedId: accepted.id, receiptMessageId: receipt && receipt.id,
      nonce, receivedNonce: receipt && receipt.matchedNonce, sentAtMs,
      receivedAtMs: receipt && receipt.receivedAtMs,
    }, now(), allowedRecipients);
  };
}

function createProductionCollectorRegistry({ env = process.env, fetchImpl = fetch } = {}) {
  return Object.freeze({ telegram: createTelegramCollector({ env, fetchImpl }), email: createEmailCollector({ env, fetchImpl }) });
}

module.exports = { createEmailCollector, createProductionCollectorRegistry, createTelegramCollector,
  validateEmailObservation, validateTelegramObservation };
