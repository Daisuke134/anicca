"use strict";

const os = require("node:os");
const path = require("node:path");
const WebSocket = require("ws");
const { adaptMoneytreeAccounts } = require("../lib/cfo-moneytree.js");
const { deriveMoneytreeState, composeMoneytreeRead } = require("../lib/cfo-moneytree-state.js");

const ERROR = "cfo_moneytree_codex_read_failed:unavailable";
const CFO_CWD = path.resolve(__dirname, "..");
const MAX_BUFFER = 2 * 1024 * 1024;
const CALL_TIMEOUT_MS = 120000;
const APP_SERVER = "codex_apps";
const MONEYTREE_TOOL = "moneytree.show-accounts";

function appServerSocket(env) {
  const explicit = env.CODEX_APP_SERVER_SOCKET;
  if (typeof explicit === "string" && path.isAbsolute(explicit)) return explicit;
  const codexHome = typeof env.CODEX_HOME === "string" && env.CODEX_HOME ? env.CODEX_HOME : path.join(env.HOME || os.homedir(), ".codex");
  return path.join(codexHome, "app-server-control", "app-server-control.sock");
}

function validateAccounts(content) {
  if (!content || typeof content !== "object" || Array.isArray(content) || content.type !== "accounts" || !content.data || typeof content.data !== "object" || Array.isArray(content.data) || !content.data.accountGroups || typeof content.data.accountGroups !== "object" || Array.isArray(content.data.accountGroups)) throw new Error(ERROR);
  return content;
}

function callMoneytreeApp(options = {}) {
  return new Promise((resolve, reject) => {
    const env = options.env && typeof options.env === "object" ? options.env : process.env;
    const socket = appServerSocket(env);
    if (!path.isAbsolute(socket)) return reject(new Error(ERROR));
    const Client = options.WebSocketImpl || WebSocket;
    let nextId = 1;
    let settled = false;
    const timer = setTimeout(() => finish(new Error(ERROR)), CALL_TIMEOUT_MS);
    let ws;
    const finish = (error, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      try { if (ws && typeof ws.close === "function") ws.close(); } catch {}
      if (error) reject(error); else resolve(value);
    };
    const send = (method, params) => {
      const id = nextId++;
      ws.send(JSON.stringify({ jsonrpc: "2.0", id, method, params }));
      return id;
    };
    try {
      ws = new Client(`ws+unix://${socket}:/rpc`, { perMessageDeflate: false });
      ws.on("open", () => send("initialize", { clientInfo: { name: "life-manager-cfo-hourly", title: "Life Manager CFO hourly loop", version: "1.0.0" }, capabilities: { experimentalApi: true } }));
      ws.on("message", (data) => {
        if (Buffer.byteLength(String(data), "utf8") > MAX_BUFFER) return finish(new Error(ERROR));
        let message;
        try { message = JSON.parse(String(data)); } catch { return finish(new Error(ERROR)); }
        if (message.error) return finish(new Error(ERROR));
        if (message.id === 1) {
          try { ws.send(JSON.stringify({ jsonrpc: "2.0", method: "initialized" })); send("thread/start", { cwd: options.cwd || CFO_CWD, model: "gpt-5.6-luna", approvalPolicy: "never", sandbox: "read-only", ephemeral: true, serviceName: "life-manager-cfo-hourly", config: { features: { apps: true } } }); } catch { finish(new Error(ERROR)); }
        } else if (message.id === 2) {
          const threadId = message.result && message.result.thread && message.result.thread.id;
          if (typeof threadId !== "string" || !threadId) return finish(new Error(ERROR));
          try { send("mcpServer/tool/call", { threadId, server: APP_SERVER, tool: MONEYTREE_TOOL, arguments: { locale: "ja" } }); } catch { finish(new Error(ERROR)); }
        } else if (message.id === 3) {
          const result = message.result;
          if (!result || result.isError === true) return finish(new Error(ERROR));
          try { finish(null, validateAccounts(result.structuredContent || result.structured_content)); } catch { finish(new Error(ERROR)); }
        }
      });
      ws.on("error", () => finish(new Error(ERROR)));
      ws.on("close", () => finish(new Error(ERROR)));
    } catch { finish(new Error(ERROR)); }
  });
}

async function readMoneytreeViaCodex(options = {}) {
  try {
    const base = options.env && typeof options.env === "object" ? options.env : process.env;
    const referenceKey = base.LM_UID_SECRET;
    if (typeof referenceKey !== "string" || Buffer.byteLength(referenceKey, "utf8") < 32) throw new Error(ERROR);
    const rawNow = typeof options.now === "function" ? options.now() : (options.now || new Date());
    const observedAt = new Date(rawNow).toISOString();
    const call = options.callAppServer || callMoneytreeApp;
    const content = await call({ env: base, cwd: CFO_CWD });
    const source = adaptMoneytreeAccounts({ accountsJson: JSON.stringify(content), observedAt, referenceKey });
    const state = deriveMoneytreeState({ signal: "interactive_success", observedAt, aggregationAsOf: null, aggregationFreshnessCutoff: null, liabilitiesExposed: false, liabilityCount: null });
    return composeMoneytreeRead({ source, state });
  } catch { throw new Error(ERROR); }
}

async function main(options = {}) {
  let envelope;
  try {
    const read = await readMoneytreeViaCodex(options);
    envelope = { ok: true, sourceId: read.source.sourceId, accountCount: read.source.accounts.length, partial: read.state.partial };
  } catch { envelope = { ok: false, sourceId: null, accountCount: 0, partial: true }; }
  const output = `${JSON.stringify(envelope)}\n`;
  if (typeof options.stdout === "function") options.stdout(output); else process.stdout.write(output);
  return envelope.ok ? 0 : 1;
}

if (require.main === module) main().then((exitCode) => { process.exitCode = exitCode; });

module.exports = { callMoneytreeApp, readMoneytreeViaCodex, main };
