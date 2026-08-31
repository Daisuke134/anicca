"use strict";

const {
  claimBrowserJob,
  appendBrowserTrace,
  finishBrowserJob,
} = require("./browser-job-store.js");
const { runGenericBrowserTask } = require("./generic-browser-task.js");
const { makeStagehandSteelDriver } = require("./stagehand-steel-driver.js");
const { sendMessage, sendPhoto } = require("./telegram.js");
let defaultDriver = null;

function driverFor(deps) {
  if (deps.driver) return deps.driver;
  const makeDriver = deps.makeDriver || makeStagehandSteelDriver;
  const created = () => makeDriver({
    apiKey: deps.geminiKey || process.env.GEMINI_API_KEY,
    agentEmail: deps.agentEmail || process.env.LM_AGENT_BROWSER_EMAIL,
    agentName: deps.agentName || process.env.LM_AGENT_BROWSER_NAME,
  });
  if (deps.makeDriver) return created();
  if (!defaultDriver) defaultDriver = created();
  return defaultDriver;
}

async function runNextBrowserJob(deps = {}) {
  const heldDriver = deps.driver || (!deps.makeDriver && defaultDriver);
  if (heldDriver && typeof heldDriver.hasHeldSession === "function" && heldDriver.hasHeldSession()) {
    if (typeof heldDriver.releaseExpiredSessions === "function") {
      await heldDriver.releaseExpiredSessions();
    }
    if (heldDriver.hasHeldSession()) return { status: "handoff_waiting" };
  }
  const claim = deps.claimJob || (() => claimBrowserJob(deps));
  const job = await claim();
  if (!job) return { status: "idle" };
  const driver = driverFor(deps);
  const append = deps.appendTrace || ((id, stage, meta) => appendBrowserTrace(id, stage, meta, deps));
  const finish = deps.finishJob || ((id, result) => finishBrowserJob(id, result, deps));
  const send = deps.sendMessage || sendMessage;
  const sendEvidence = deps.sendPhoto || sendPhoto;
  const telegramToken = deps.telegramToken || process.env.LM_TELEGRAM_BOT_TOKEN;
  return runGenericBrowserTask(job, {
    appendTrace: append,
    openSession: driver.openSession.bind(driver),
    discoverAndAct: driver.discoverAndAct.bind(driver),
    readProviderReceipt: driver.readProviderReceipt.bind(driver),
    captureEvidence: driver.captureEvidence.bind(driver),
    releaseSession: driver.releaseSession.bind(driver),
    sendTelegram: (chatId, text) => send(telegramToken, chatId, text),
    sendTelegramEvidence: (chatId, evidence, caption) =>
      sendEvidence(telegramToken, chatId, evidence.bytes, caption),
    finishJob: finish,
  });
}

async function completeBrowserHandoff(sessionId, answer, deps = {}) {
  const driver = deps.driver || defaultDriver;
  if (!driver || typeof driver.readHeldReceipt !== "function" || typeof driver.releaseSession !== "function") {
    throw new Error("browser handoff unavailable");
  }
  const providerReceipt = await driver.readHeldReceipt(sessionId);
  if (answer === "approve" && providerReceipt.confirmed !== true) {
    return { providerReceipt, release: null };
  }
  const release = await driver.releaseSession(sessionId, { providerReceipt });
  if (!release || release.released !== true) throw new Error("browser handoff release unavailable");
  return { providerReceipt, release };
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
  completeBrowserHandoff,
  runNextBrowserJob,
  startBrowserJobLoop,
};
