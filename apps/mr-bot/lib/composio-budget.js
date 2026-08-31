"use strict";

const { monthlyComposioCallCount } = require("./ledger.js");
const ALERT_AT = 18000;
const DEGRADE_AT = 19500;
const NORMAL_INTERVAL_MS = 60000;
const DEGRADED_INTERVAL_MS = 300000;
const ALERT_THROTTLE_MS = 6 * 60 * 60 * 1000;

function intervalForCount(count) {
  const value = Number(count) || 0;
  return { alert: value >= ALERT_AT, intervalMs: value >= DEGRADE_AT ? DEGRADED_INTERVAL_MS : NORMAL_INTERVAL_MS };
}

class ComposioBudgetGuard {
  constructor(opts = {}) {
    this.sendAlert = opts.sendAlert || (async () => {});
    this.lastAlertAt = -Infinity;
    this.intervalMs = NORMAL_INTERVAL_MS;
  }
  async update(count, nowMs = Date.now()) {
    if (count == null) return { alert: false, intervalMs: this.intervalMs };
    const state = intervalForCount(count);
    this.intervalMs = state.intervalMs;
    if (state.alert && nowMs - this.lastAlertAt >= ALERT_THROTTLE_MS) {
      await this.sendAlert(Number(count));
      this.lastAlertAt = nowMs;
    }
    return state;
  }
}

async function sendAdminAlert(count, opts = {}) {
  const token = opts.token || process.env.LM_TELEGRAM_BOT_TOKEN;
  const chatId = opts.chatId || process.env.LM_ADMIN_TELEGRAM_CHAT_ID;
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  if (!token || !chatId || typeof fetchImpl !== "function") return false;
  const response = await fetchImpl(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text: `⚠️ Composio monthly calls: ${count.toLocaleString()} / 20,000` }),
  });
  return Boolean(response && response.ok);
}

const schedulerBudgetGuard = new ComposioBudgetGuard({
  sendAlert: (count) => sendAdminAlert(count).catch(() => false),
});

async function schedulerPollInterval(nowMs = Date.now()) {
  const count = await monthlyComposioCallCount({ nowMs });
  return (await schedulerBudgetGuard.update(count, nowMs)).intervalMs;
}

module.exports = { ALERT_AT, DEGRADE_AT, ALERT_THROTTLE_MS, ComposioBudgetGuard, intervalForCount, sendAdminAlert, schedulerPollInterval };
