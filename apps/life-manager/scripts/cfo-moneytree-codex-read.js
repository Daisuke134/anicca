"use strict";

const { execFile } = require("node:child_process");
const path = require("node:path");
const { adaptMoneytreeAccounts } = require("../lib/cfo-moneytree.js");
const { deriveMoneytreeState, composeMoneytreeRead } = require("../lib/cfo-moneytree-state.js");

const ERROR = "cfo_moneytree_codex_read_failed:unavailable";
const CFO_CWD = path.resolve(__dirname, "..");
const MAX_BUFFER = 2 * 1024 * 1024;
const RUNTIME_KEYS = ["HOME", "PATH", "USER", "LOGNAME", "SHELL", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE"];
const PROMPT = "Use the installed Moneytree App exactly once: call show_accounts with locale ja. Do not call any other tool. Do not summarize, transcribe, calculate, or print balances, account IDs, institution labels, credentials, or private fields. Stop after show_accounts.";

function safeEnv(base) {
  const env = {};
  for (const key of RUNTIME_KEYS) if (typeof base[key] === "string") env[key] = base[key];
  if (typeof base.CODEX_HOME === "string") env.CODEX_HOME = base.CODEX_HOME;
  env.CODEX_INTERNAL_ORIGINATOR_OVERRIDE = "codex_exec";
  return env;
}

function accountsResult(stdout) {
  if (typeof stdout !== "string" || Buffer.byteLength(stdout, "utf8") > MAX_BUFFER) throw new Error(ERROR);
  const events = [];
  for (const line of stdout.split(/\r?\n/)) {
    if (!line.trim()) continue;
    try { events.push(JSON.parse(line)); } catch { throw new Error(ERROR); }
  }
  const completed = events.filter((event) => event && event.type === "item.completed" && event.item && event.item.type === "mcp_tool_call");
  if (completed.length !== 1) throw new Error(ERROR);
  const content = completed[0].item.result && completed[0].item.result.structured_content;
  if (!content || typeof content !== "object" || Array.isArray(content) || content.type !== "accounts" || !content.data || typeof content.data !== "object" || Array.isArray(content.data) || !content.data.accountGroups || typeof content.data.accountGroups !== "object" || Array.isArray(content.data.accountGroups)) throw new Error(ERROR);
  return content;
}

function invoke(execFileImpl, args, env) {
  return new Promise((resolve, reject) => {
    let child, started = false, ended = false, callbackCalled = false, callbackError, callbackStdout, settled = false;
    const finish = () => {
      if (!started || settled) return;
      try {
        if (!child || !child.stdin || typeof child.stdin.end !== "function") throw new Error(ERROR);
        if (!ended) child.stdin.end(), ended = true;
        if (!callbackCalled) return;
        settled = true;
        if (callbackError) reject(new Error(ERROR)); else resolve(callbackStdout);
      } catch { settled = true; reject(new Error(ERROR)); }
    };
    try {
      child = execFileImpl("codex", args, { cwd: CFO_CWD, env, shell: false, timeout: 120000, maxBuffer: MAX_BUFFER }, (error, stdout) => {
        callbackCalled = true; callbackError = error; callbackStdout = stdout; finish();
      });
      started = true; finish();
    } catch { reject(new Error(ERROR)); }
  });
}

async function readMoneytreeViaCodex(options = {}) {
  try {
    const base = options.env && typeof options.env === "object" ? options.env : process.env;
    const referenceKey = base.LM_UID_SECRET;
    if (typeof referenceKey !== "string" || Buffer.byteLength(referenceKey, "utf8") < 32) throw new Error(ERROR);
    const rawNow = typeof options.now === "function" ? options.now() : (options.now || new Date());
    const observedAt = new Date(rawNow).toISOString();
    const args = ["exec", "--ephemeral", "--json", "--model", "gpt-5.6-luna", "--sandbox", "read-only", "--cd", CFO_CWD, PROMPT];
    const content = accountsResult(await invoke(options.execFileImpl || execFile, args, safeEnv(base)));
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

module.exports = { readMoneytreeViaCodex, main };
