"use strict";

const { classifyBrowserTask } = require("./browser-task-classifier.js");
const { enqueueBrowserJob } = require("./browser-job-store.js");
const { sendMessage } = require("./telegram.js");

async function handleBrowserTaskMessage(input, deps = {}) {
  const user = input && input.user;
  if (!user || !user.uid || user.paid !== true || user.tg_onboard_stage !== "done") {
    return { handled: false };
  }
  const text = String(input.text || "").trim();
  if (!text || !input.chatId || !input.messageId || input.updateId == null) return { handled: false };
  const classify = deps.classify || ((value) => classifyBrowserTask(value, {
    apiKey: deps.geminiKey,
    fetchImpl: deps.fetchImpl,
  }));
  const classification = await classify(text);
  if (!classification || classification.accepted !== true) {
    return { handled: false, reason: classification && classification.reason || "classifier_abstained" };
  }

  const enqueue = deps.enqueue || ((value) => enqueueBrowserJob(value, {
    supaUrl: deps.supaUrl,
    supaKey: deps.supaKey,
    fetchImpl: deps.fetchImpl,
  }));
  const queued = await enqueue({
    uid: user.uid,
    chatId: input.chatId,
    messageId: input.messageId,
    updateId: String(input.updateId),
    rawPrompt: text,
    classification,
  });
  if (!queued || !queued.job || !queued.job.id) throw new Error("browser queue returned no job");
  if (!queued.created) {
    return { handled: true, queued: false, jobId: String(queued.job.id), duplicate: true };
  }

  const send = deps.sendMessage || sendMessage;
  const sent = await send(
    deps.telegramToken,
    input.chatId,
    `🧭 Browser task queued.\nTrace: <code>${String(queued.job.id)}</code>`,
  );
  const messageId = sent && sent.ok && sent.result && sent.result.message_id;
  return {
    handled: true,
    queued: true,
    jobId: String(queued.job.id),
    telegramMessageId: messageId == null ? null : String(messageId),
  };
}

module.exports = { handleBrowserTaskMessage };

