import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import chat from "../../apps/life-manager/lib/investment-chat.js";

function readJson(path) {
  try {
    const value = JSON.parse(readFileSync(path, "utf8"));
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  } catch { return {}; }
}

function localSnapshot() {
  const root = join(process.env.LIFE_MANAGER_STATE_ROOT || join(homedir(), ".local", "state", "life-manager"), "alpaca-investment");
  let account;
  try { account = JSON.parse(readFileSync(join(root, "account-status.json"), "utf8")); }
  catch (error) { return { lifecycle: error.code === "ENOENT" ? "setup_required" : "unknown" }; }
  if (!account || typeof account !== "object" || Array.isArray(account)) return { lifecycle: "unknown" };
  return {
    lifecycle: account.application_status,
    account: readJson(join(root, "observation-latest.json")).account,
    decision: readJson(join(root, "allocation-latest.json")),
  };
}

export default {
  id: "life-manager-invest-command",
  name: "Life Manager Investment Command",
  description: "Deterministic /invest status command for the existing Telegram gateway",
  register(api) {
    api.registerCommand({
      name: "invest",
      nativeNames: { default: "invest" },
      description: "Investment Loopの状態と設定",
      channels: ["telegram"],
      requireAuth: true,
      acceptsArgs: false,
      async handler() {
        return chat.buildInvestmentReply(localSnapshot());
      },
    });
  },
};
