"use strict";

const { createHash } = require("node:crypto");
const { spawn } = require("node:child_process");
const { validateFinancialRecord } = require("./financial-organ-schema.js");

function normalizeAccounts(toolResult, observedAt = new Date().toISOString()) {
  const data = toolResult?.structuredContent?.data;
  if (!data || data.baseCurrency !== "JPY") throw new Error("Moneytree JPY account data is unavailable");
  const groups = [...(data.accountGroups?.banks || []), ...(data.accountGroups?.investments || [])];
  return groups.flatMap((group) => (group.accounts || []).map((account) => {
    const balance = account.current_balance_in_base ?? account.current_balance;
    const key = `${group.institutionKey}:${account.id}`;
    return validateFinancialRecord("account", {
      id: `moneytree:${createHash("sha256").update(key).digest("hex").slice(0, 24)}`,
      source: "moneytree",
      source_ref: `moneytree:${createHash("sha256").update(`source:${key}`).digest("hex")}`,
      name: "Moneytree account",
      kind: account.account_subtype || "account",
      balance_jpy: balance,
      observed_at: observedAt,
    });
  }));
}

function readAccounts({ codexBin = "codex", cwd = process.cwd(), timeoutMs = 20_000 } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(codexBin, ["app-server", "--stdio"], { cwd, stdio: ["pipe", "pipe", "ignore"] });
    let buffer = "";
    const finish = (error, value) => {
      clearTimeout(timer);
      child.kill();
      error ? reject(error) : resolve(value);
    };
    const timer = setTimeout(() => finish(new Error("Moneytree app-server timeout")), timeoutMs);
    const send = (message) => child.stdin.write(`${JSON.stringify(message)}\n`);

    child.on("error", (error) => finish(error));
    child.stdout.on("data", (chunk) => {
      buffer += chunk;
      let newline;
      while ((newline = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, newline);
        buffer = buffer.slice(newline + 1);
        if (!line) continue;
        let message;
        try { message = JSON.parse(line); } catch { continue; }
        if (message.error) return finish(new Error(message.error.message || "Moneytree app-server error"));
        if (message.id === 1) {
          send({ method: "initialized", params: {} });
          send({ id: 2, method: "thread/start", params: { ephemeral: true, cwd } });
        } else if (message.id === 2) {
          send({
            id: 3,
            method: "mcpServer/tool/call",
            params: {
              threadId: message.result.thread.id,
              server: "codex_apps",
              tool: "moneytree.show-accounts",
              arguments: { locale: "ja" },
            },
          });
        } else if (message.id === 3) {
          const result = message.result;
          if (result?.isError) return finish(new Error("Moneytree tool returned an error"));
          return finish(null, normalizeAccounts(result));
        }
      }
    });
    send({
      id: 1,
      method: "initialize",
      params: { clientInfo: { name: "life_manager", title: "Life Manager", version: "0.1.0" } },
    });
  });
}

if (require.main === module) {
  readAccounts().then((accounts) => {
    process.stdout.write(`${JSON.stringify({ connected: true, accounts: accounts.length })}\n`);
  }).catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = { normalizeAccounts, readAccounts };
