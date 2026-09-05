import { execFile } from "node:child_process";
import { homedir } from "node:os";
import { join } from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

function statusScript() {
  const root = process.env.LIFE_MANAGER_REPO || join(homedir(), "loops", "current");
  return join(root, "skills", "anicca-life-manager", "scripts", "investment_status.py");
}

export default {
  id: "life-manager-invest-command",
  name: "Life Manager Investment Command",
  description: "Deterministic /invest status command for the existing Telegram gateway",
  register(api) {
    api.registerCommand({
      name: "invest",
      description: "Investment Loopの状態と設定",
      channels: ["telegram"],
      requireAuth: true,
      acceptsArgs: false,
      async handler() {
        try {
          const { stdout } = await execFileAsync("python3", [statusScript()], {
            timeout: 10_000,
            maxBuffer: 256 * 1024,
          });
          return { text: stdout.trim() };
        } catch {
          return {
            text: "Investment Loop\n\n状態を取得できませんでした。次の5分周期で再確認します。",
          };
        }
      },
    });
  },
};
