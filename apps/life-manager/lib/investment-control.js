"use strict";

const { readFileSync } = require("node:fs");
const { join } = require("node:path");

function defaultControl() { return { paused: false, killed: false, revision: 0 }; }

function validControl(value, { stored = false } = {}) {
  return Boolean(value && typeof value === "object" && !Array.isArray(value)
    && typeof value.paused === "boolean" && typeof value.killed === "boolean"
    && Number.isSafeInteger(value.revision) && value.revision >= (stored ? 1 : 0)
    && !(value.killed && !value.paused)
    && Object.keys(value).every((key) => ["paused", "killed", "revision", "updated_at", "last_action"].includes(key)));
}

function readInvestmentControl(root) {
  try {
    const value = JSON.parse(readFileSync(join(root, "control.json"), "utf8"));
    if (!validControl(value, { stored: true })) throw new Error("investment_control_state_invalid");
    return value;
  } catch (error) {
    if (error.code === "ENOENT") return defaultControl();
    throw new Error("investment_control_state_invalid");
  }
}

function readJson(path) {
  try {
    const value = JSON.parse(readFileSync(path, "utf8"));
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  } catch { return {}; }
}

function money(value) {
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return typeof value === "string" && /^-?\d+(?:\.\d+)?$/.test(value) ? value : null;
}

function buildInvestmentControlReply(root, action) {
  const control = readInvestmentControl(root);
  const allocation = readJson(join(root, "allocation-latest.json"));
  if (action === "why") return `Investment Loop\n\n理由: ${typeof allocation.reason === "string" ? allocation.reason : "最新の判断理由をまだ読み取れません。"}`;
  if (action === "risk") {
    const risk = readJson(join(root, "risk-latest.json"));
    const day = money(risk.realized_pnl_ny_day_usd);
    const unrealized = money(risk.unrealized_pnl_usd);
    const flow = money(risk.cash_flow_ny_day_usd);
    return ["Investment Loop", "", "リスク上限: 総投資 $100 / 1取引の最大損失 $10 / 1日の損失停止 $20",
      `現在: 確定損益 ${day == null ? "不明" : `$${day}`}、含み損益 ${unrealized == null ? "不明" : `$${unrealized}`}、入出金 ${flow == null ? "不明" : `$${flow}`}`,
      "このコマンドからLive化や上限変更はできません。"].join("\n");
  }
  const state = control.killed ? "停止済み" : control.paused ? "一時停止中" : "稼働中";
  return `Investment Loop\n\n運転状態: ${state}\nモード変更・Live化・資金上限変更はできません。`;
}

module.exports = { buildInvestmentControlReply, readInvestmentControl, validControl };
