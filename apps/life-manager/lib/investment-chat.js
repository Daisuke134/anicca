"use strict";

const ALPACA_SIGNUP_URL = "https://app.alpaca.markets/signup";
const LIFECYCLES = new Set(["setup_required", "in_review", "approved", "active", "rejected", "action_required"]);

function normalizeInvestmentLifecycle(value) {
  if (typeof value !== "string") return "unknown";
  const lifecycle = value.toLowerCase();
  return LIFECYCLES.has(lifecycle) ? lifecycle : "unknown";
}

function moneyValue(value) {
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : null;
  if (typeof value === "string" && /^-?\d+(?:\.\d+)?$/.test(value)) return value;
  return null;
}

function validRecord(value) {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function validAccount(value) {
  if (!validRecord(value)) return false;
  return moneyValue(value.equity) != null && moneyValue(value.cash) != null;
}

function validDecision(value) {
  if (!validRecord(value)) return false;
  return typeof value.approved === "boolean"
    && typeof value.reason === "string" && Boolean(value.reason.trim());
}

function validInvestmentSnapshot(snapshot) {
  return validRecord(snapshot)
    && normalizeInvestmentLifecycle(snapshot.lifecycle) !== "unknown"
    && (!("account" in snapshot) || validAccount(snapshot.account))
    && (!("decision" in snapshot) || validDecision(snapshot.decision));
}

function buildInvestmentReply(snapshot = {}) {
  if (!snapshot || typeof snapshot !== "object") snapshot = {};
  const lifecycle = normalizeInvestmentLifecycle(snapshot.lifecycle);
  if (lifecycle === "setup_required") {
    return {
      text: [
        "Investment Loop", "",
        "Alpacaで口座開設と本人確認を完了してください。",
        "Life Managerと同じメールアドレスを使うと接続が簡単です。",
        "完了後はLife Managerが審査状態を確認し、自動運転まで進めます。",
      ].join("\n"),
      presentation: { blocks: [{ type: "buttons", buttons: [
        { label: "Alpacaで口座開設する", url: ALPACA_SIGNUP_URL },
        { label: "今はしない", action: { type: "callback", value: "invest:later" } },
      ] }] },
    };
  }

  const lines = ["Investment Loop", ""];
  if (lifecycle === "in_review") {
    lines.push("ライブ口座: 審査中です。今は操作不要です。承認を確認したら、次に必要な操作だけ知らせます。");
  } else if (["approved", "active"].includes(lifecycle)) {
    lines.push("ライブ口座: 承認済みです。入金とリスク上限を確認するまでライブ注文は出しません。");
  } else if (["rejected", "action_required"].includes(lifecycle)) {
    lines.push("ライブ口座: 追加対応が必要です。Alpacaの画面で表示される本人対応だけ行ってください。");
  } else {
    lines.push("ライブ口座: 状態をまだ確認できません。ライブ注文は出しません。");
  }

  const account = validAccount(snapshot.account) ? snapshot.account : {};
  const decision = validDecision(snapshot.decision) ? snapshot.decision : {};
  const equity = moneyValue(account.equity);
  const cash = moneyValue(account.cash);
  if (equity != null && cash != null) {
    const decisionLabel = decision.approved === true ? "取引候補あり"
      : decision.approved === false ? "取引なし" : "未確認";
    lines.push(`paper loop: 稼働中。資産 $${equity}、現金 $${cash}、今回の判断は${decisionLabel}です。`);
    if (decision.reason) lines.push(`理由: ${decision.reason}`);
  } else {
    lines.push("paper loop: 最新状態をまだ読み取れません。次の5分周期で再確認します。");
  }
  return { text: lines.join("\n") };
}

function telegramExtra(reply) {
  const buttons = reply.presentation?.blocks?.find((block) => block.type === "buttons")?.buttons;
  if (!buttons) return { parse_mode: undefined };
  return { parse_mode: undefined, reply_markup: { inline_keyboard: [buttons.map((button) => ({
    text: button.label,
    ...(button.url ? { url: button.url } : { callback_data: button.action.value }),
  }))] } };
}

module.exports = { ALPACA_SIGNUP_URL, buildInvestmentReply, telegramExtra, validInvestmentSnapshot };
