"use strict";

const {
  claimBrowserJob,
  appendBrowserTrace,
  finishBrowserJob,
} = require("./browser-job-store.js");
const { runGenericBrowserTask } = require("./generic-browser-task.js");
const { makeStagehandSteelDriver } = require("./stagehand-steel-driver.js");
const { sendMessage } = require("./telegram.js");

async function runNextBrowserJob(deps = {}) {
  const claim = deps.claimJob || (() => claimBrowserJob(deps));
  const job = await claim();
  if (!job) return { status: "idle" };
  const makeDriver = deps.makeDriver || makeStagehandSteelDriver;
  const driver = deps.driver || makeDriver({
    apiKey: deps.geminiKey || process.env.GEMINI_API_KEY,
    agentEmail: deps.agentEmail || process.env.LM_AGENT_BROWSER_EMAIL,
  });
  const append = deps.appendTrace || ((id, stage, meta) => appendBrowserTrace(id, stage, meta, deps));
  const finish = deps.finishJob || ((id, result) => finishBrowserJob(id, result, deps));
  const send = deps.sendMessage || sendMessage;
  const telegramToken = deps.telegramToken || process.env.LM_TELEGRAM_BOT_TOKEN;
  return runGenericBrowserTask(job, {
    appendTrace: append,
    openSession: driver.openSession.bind(driver),
    discoverAndAct: driver.discoverAndAct.bind(driver),
    readProviderReceipt: driver.readProviderReceipt.bind(driver),
    releaseSession: driver.releaseSession.bind(driver),
    sendTelegram: (chatId, text) => send(telegramToken, chatId, text),
    finishJob: finish,
  });
}

function startBrowserJobLoop(options = {}) {
  const enabled = options.enabled === true;
  const intervalMs = Number.isInteger(options.intervalMs) ? options.intervalMs : 2_000;
  const setTimeoutImpl = options.setTimeoutImpl || setTimeout;
  const clearTimeoutImpl = options.clearTimeoutImpl || clearTimeout;
  const runOnce = options.runOnce || (() => runNextBrowserJob(options));
  let timer = null;
  let running = false;
  let closed = false;

  const runNow = async () => {
    if (!enabled || closed) return { status: "disabled" };
    if (running) return { status: "overlap_skipped" };
    running = true;
    try {
      return await runOnce();
    } catch (error) {
      console.error(`[browser-job] ${String(error && error.message || error)}`);
      return { status: "error" };
    } finally {
      running = false;
    }
  };

  const schedule = () => {
    if (!enabled || closed) return;
    timer = setTimeoutImpl(async () => {
      await runNow();
      schedule();
    }, intervalMs);
  };
  schedule();
  return {
    enabled,
    runNow,
    close() {
      closed = true;
      if (timer != null) clearTimeoutImpl(timer);
    },
  };
}

module.exports = {
  runNextBrowserJob,
  startBrowserJobLoop,
};
