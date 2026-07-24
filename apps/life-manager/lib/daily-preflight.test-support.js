"use strict";

// Tests only: production CLI and production modules never import this collector-DI harness.
const crypto = require("node:crypto");
const { validateAndBuildFinalReport, validateSerializedFinalReportShape,
  validateEmailProof, validateTelegramProof } = require("./daily-preflight.js");
const { validateEmailObservation, validateTelegramObservation } = require("./daily-preflight-collectors.js");

function failure(code) { return new Error(code); }
function baseUrl(env) {
  if (env.LIFE_CALL_HEALTH_URL) return String(env.LIFE_CALL_HEALTH_URL).replace(/\/health\/?$/, "");
  if (env.RAILWAY_PUBLIC_DOMAIN) return `https://${String(env.RAILWAY_PUBLIC_DOMAIN).replace(/^https?:\/\//, "")}`;
  if (env.PUBLIC_WSS) return String(env.PUBLIC_WSS).replace(/^wss:/, "https:").replace(/^ws:/, "http:").replace(/\/$/, "");
  return String(env.PUBLIC_BASE || env.ANICCA_PROXY_BASE_URL || "").replace(/\/$/, "");
}
async function sanitized(code, operation) { try { return await operation(); } catch { throw failure(code); } }

function createTelegramCollector({ env = {}, botCall, mtprotoSend, mtprotoRead, execFileImpl,
  fetchImpl, sleep = () => Promise.resolve(), now = Date.now, maxReplyPolls = 6, maxWebhookPolls = 3 } = {}) {
  const callBot = botCall || (async method => {
    const response = await fetchImpl(`https://api.telegram.org/bot${env.LM_TELEGRAM_BOT_TOKEN}/${method}`, { method: "POST" });
    return response.json();
  });
  const sidecar = async args => {
    if (typeof execFileImpl !== "function") throw failure("test_transport_fake_required");
    const { stdout } = await execFileImpl("/Users/anicca/.cache/telegram-user-venv/bin/python",
      ["/Users/anicca/anicca/skills/tools/telegram-user/tg_user.py", ...args],
      { timeout: 15000, maxBuffer: 1024 * 1024, encoding: "utf8" });
    return JSON.parse(stdout);
  };
  const send = mtprotoSend || (async (peer, command) => {
    const result = await sidecar(["send", peer, command]);
    return { id: result.sent_id, atMs: now() };
  });
  const read = mtprotoRead || (async peer => {
    const result = await sidecar(["read", peer, "20"]);
    return (result.messages || []).map(message => ({ id: Number(message.id), atMs: Date.parse(message.date), inbound: message.out === false }));
  });
  return async () => {
    if (!env.LM_TELEGRAM_BOT_TOKEN || !baseUrl(env)) throw failure("telegram_configuration");
    const me = await sanitized("telegram_provider_rejected", () => callBot("getMe"));
    const username = me && me.result && me.result.username;
    if (!/^[A-Za-z0-9_]{5,32}$/.test(String(username || ""))) throw failure("telegram_bot_identity");
    const peer = `@${username}`; const nonce = crypto.randomBytes(12).toString("hex");
    const sent = await sanitized("telegram_send_rejected", () => send(peer, `/panel core8d_${nonce}`));
    let reply;
    for (let index = 0; index < maxReplyPolls; index += 1) {
      const messages = await sanitized("telegram_mtproto_unavailable", () => read(peer));
      reply = messages.find(message => message.inbound && Number.isInteger(message.id) && message.id > sent.id && message.atMs >= sent.atMs);
      if (reply) break;
      if (index + 1 < maxReplyPolls) await sleep(2000);
    }
    if (!reply) throw failure("telegram_reply_timeout");
    const samples = []; let info;
    for (let index = 0; index < maxWebhookPolls; index += 1) {
      const response = await sanitized("telegram_provider_rejected", () => callBot("getWebhookInfo"));
      info = response && response.result; samples.push(Number(info && info.pending_update_count));
      if (samples.at(-1) === 0) break;
      if (index + 1 < maxWebhookPolls) await sleep(2000);
    }
    return validateTelegramObservation({ sentId: sent.id, replyId: reply.id, sentAtMs: sent.atMs, replyAtMs: reply.atMs,
      webhookUrl: String(info && info.url || ""), expectedWebhookUrl: `${baseUrl(env)}/telegram`,
      allowedUpdates: info && info.allowed_updates, lastError: Boolean(info && (info.last_error_message || info.last_error_date)),
      pendingUpdateSamples: samples }, now());
  };
}

function createEmailCollector({ env = {}, send, findReceipt, mailFactory = () => ({ findReceipt }),
  sleep = () => Promise.resolve(), now = Date.now, randomNonce = () => crypto.randomBytes(18).toString("hex"), maxPolls = 6,
  fetchImpl } = {}) {
  const mail = mailFactory({ bin: "/opt/homebrew/bin/gog", account: env.GOG_ACCOUNT });
  const sendMail = send || (async args => {
    const response = await fetchImpl("https://api.resend.com/emails", { method: "POST", body: JSON.stringify(args) });
    const body = await response.json(); return { sent: response.ok, id: body.id };
  });
  const receive = findReceipt || (args => mail.findReceipt(args));
  return async () => {
    const recipient = String(env.GOG_ACCOUNT || "").trim().toLowerCase();
    const allowed = String(env.LM_CONTROLLED_EMAIL_ALLOWLIST || "").split(",").map(v => v.trim().toLowerCase()).filter(Boolean);
    if (!recipient || !allowed.includes(recipient)) throw failure("email_recipient_not_controlled");
    if (!env.RESEND_API_KEY) throw failure("email_configuration");
    const nonce = randomNonce(); const sentAtMs = now();
    const accepted = await sendMail({ to: recipient, subject: `Life Manager controlled check ${nonce}`, text: `Controlled delivery check ${nonce}. No action is required.` });
    if (!accepted || accepted.sent !== true || !accepted.id) throw failure("email_send_rejected");
    let receipt;
    for (let index = 0; index < maxPolls; index += 1) {
      receipt = await receive({ nonce, afterMs: sentAtMs });
      if (receipt && receipt.id) break;
      if (index + 1 < maxPolls) await sleep(3000);
    }
    return validateEmailObservation({ recipient, receiveIdentity: recipient, providerAcceptedId: accepted.id,
      receiptMessageId: receipt && receipt.id, nonce, receivedNonce: receipt && receipt.matchedNonce,
      sentAtMs, receivedAtLowerMs: receipt && (receipt.receivedAtLowerMs ?? receipt.receivedAtMs),
      receivedAtUpperMs: receipt && (receipt.receivedAtUpperMs ?? receipt.receivedAtMs) }, now(), allowed);
  };
}

async function collectControlledL3ForTest({ mode, nowMs, collectors } = {}) {
  if (mode !== "controlled-l3") throw new Error("controlled_mode_required");
  if (!collectors || typeof collectors.telegram !== "function" || typeof collectors.email !== "function") {
    throw new Error("collector_registry_invalid");
  }
  const [telegram, email] = await Promise.all([collectors.telegram(), collectors.email()]);
  return Object.freeze({ telegram: validateTelegramProof(telegram, nowMs), email: validateEmailProof(email, nowMs) });
}

async function collectTelegramControlledForTest({ roundTrip, getWebhookInfo, sleep = () => Promise.resolve(), now = Date.now, maxPolls = 3 } = {}) {
  if (typeof roundTrip !== "function" || typeof getWebhookInfo !== "function") throw new Error("telegram_collector_unavailable");
  const trip = await roundTrip();
  const samples = [];
  let finalInfo;
  for (let index = 0; index < maxPolls; index += 1) {
    finalInfo = await getWebhookInfo();
    samples.push(finalInfo && finalInfo.pending_update_count);
    if (samples.at(-1) === 0) break;
    if (index + 1 < maxPolls) await sleep();
  }
  return {
    attempted: true, verified: trip && trip.verified === true,
    checkedAt: new Date(now()).toISOString(), requestMessageRef: trip && trip.requestMessageRef,
    replyMessageRef: trip && trip.replyMessageRef, exactUrl: finalInfo && finalInfo.exactUrl === true,
    allowedUpdates: finalInfo && finalInfo.allowed_updates,
    providerError: Boolean(finalInfo && finalInfo.providerError),
    pendingUpdateCount: samples.at(-1), pendingUpdateSamples: samples,
  };
}

function validateAndBuildFinalReportForTest(input) {
  return input && input.runRef !== undefined && input.runCorrelation === undefined
    ? validateSerializedFinalReportShape(input)
    : validateAndBuildFinalReport(input);
}

module.exports = { collectControlledL3ForTest, collectTelegramControlledForTest, createEmailCollector, createTelegramCollector,
  validateAndBuildFinalReportForTest };
