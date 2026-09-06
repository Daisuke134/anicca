import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import chat from "../../apps/life-manager/lib/investment-chat.js";
import control from "../../apps/life-manager/lib/investment-control.js";

function readJson(path) {
  try {
    const value = JSON.parse(readFileSync(path, "utf8"));
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  } catch { return {}; }
}

function localRoot() {
  return join(process.env.LIFE_MANAGER_STATE_ROOT || join(homedir(), ".local", "state", "life-manager"), "alpaca-investment");
}

function apply(action) {
  const script = fileURLToPath(new URL("../../skills/alpaca-investment/control.py", import.meta.url));
  const result = spawnSync("/usr/bin/python3", [script, "--state-root", localRoot(), "--action", action], {
    encoding: "utf8", timeout: 5000,
  });
  if (result.status !== 0) throw new Error("investment_control_write_failed");
}

function localSnapshot() {
  const root = localRoot();
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
    const register = (name, acceptsArgs, handler) => api.registerCommand({
      name, nativeNames: { default: name },
      description: `Investment Loop ${name}`,
      channels: ["telegram"], requireAuth: true, acceptsArgs, handler,
    });
    register("invest", true, async (ctx = {}) => {
      const action = String(ctx.args || "").trim().toLowerCase();
      if (!action) return chat.buildInvestmentReply(localSnapshot());
      if (["pause", "resume", "kill"].includes(action)) {
        apply(action);
        return { text: control.buildInvestmentControlReply(localRoot(), "status") };
      }
      if (["status", "why", "risk"].includes(action)) {
        return { text: control.buildInvestmentControlReply(localRoot(), action) };
      }
      return { text: "Investment Loop\n\n使い方: /invest status|why|risk|pause|resume|kill" };
    });
    for (const name of ["why", "risk", "pause", "resume"]) register(name, false, async () => {
      if (["pause", "resume"].includes(name)) apply(name);
      return { text: control.buildInvestmentControlReply(localRoot(), ["why", "risk"].includes(name) ? name : "status") };
    });
  },
};
