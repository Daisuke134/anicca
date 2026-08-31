#!/usr/bin/env node
"use strict";

const { processTaskMarketTasks } = require("../lib/taskmarket-work-ledger.js");
const { recordEarnLoopRevenue } = require("../lib/earnings-runtime.js");
const { resolve } = require("node:path");
const { pathToFileURL } = require("node:url");

const DEFAULT_API = "https://api.taskmarket.dev";
const DEFAULT_RPC = "https://mainnet.base.org";
const MAX_RESPONSE_BYTES = 2_000_000;
const MAX_SUBMISSIONS = 500;

function address(value, label) {
  const raw = String(value == null ? "" : value).trim();
  if (!/^0x[0-9a-fA-F]{40}$/.test(raw)) throw new Error(`${label} must be an EVM address`);
  return raw;
}

function taskId(value) {
  const raw = String(value == null ? "" : value).trim().toLowerCase();
  if (!/^0x[0-9a-f]{64}$/.test(raw)) throw new Error("task must be a 32-byte hex ID");
  return raw;
}

function cleanBaseUrl(value, fallback) {
  const raw = String(value || fallback).replace(/\/+$/, "");
  const parsed = new URL(raw);
  if (!["https:", "http:"].includes(parsed.protocol)) throw new Error("URL must use HTTP(S)");
  return parsed.toString().replace(/\/+$/, "");
}

async function fetchJson(url, fetchImpl) {
  const response = await fetchImpl(url, { signal: AbortSignal.timeout(30_000) });
  const text = await response.text();
  if (!response.ok) throw new Error(`TaskMarket request failed (${response.status})`);
  if (Buffer.byteLength(text) > MAX_RESPONSE_BYTES) throw new Error("TaskMarket response exceeds bounded size");
  try {
    return JSON.parse(text);
  } catch {
    throw new Error("TaskMarket response is not JSON");
  }
}

async function fetchTaskIds({
  workerAddress,
  fetchImpl = globalThis.fetch,
  apiUrl = DEFAULT_API,
}) {
  if (typeof fetchImpl !== "function") throw new TypeError("TaskMarket discovery needs fetch");
  const worker = address(workerAddress, "worker address");
  const base = cleanBaseUrl(apiUrl, DEFAULT_API);
  const body = await fetchJson(
    `${base}/api/submissions/mine?workerAddress=${encodeURIComponent(worker)}`,
    fetchImpl,
  );
  if (!Array.isArray(body) || body.length > MAX_SUBMISSIONS) {
    throw new Error("TaskMarket submission feed is not a bounded array");
  }
  const ids = [];
  for (const row of body) {
    try {
      ids.push(taskId(row && row.taskId));
    } catch {
      throw new Error("TaskMarket submission contains an invalid task ID");
    }
  }
  return [...new Set(ids)].sort();
}

function parseArgs(argv) {
  const parsed = {
    workerAddress: null,
    selfWallets: [],
    taskIds: [],
    apiUrl: null,
    rpcUrl: null,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!value) throw new Error(`unknown or incomplete argument ${key}`);
    if (key === "--worker") parsed.workerAddress = argv[++index];
    else if (key === "--self-wallet") parsed.selfWallets.push(argv[++index]);
    else if (key === "--task") parsed.taskIds.push(argv[++index]);
    else if (key === "--api") parsed.apiUrl = argv[++index];
    else if (key === "--rpc") parsed.rpcUrl = argv[++index];
    else throw new Error(`unknown or incomplete argument ${key}`);
  }
  return parsed;
}

function rpcClient(fetchImpl, rpcUrl) {
  return async (method, params) => {
    const response = await fetchImpl(rpcUrl, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
      signal: AbortSignal.timeout(30_000),
    });
    const body = await response.json().catch(() => null);
    if (!response.ok || !body || body.error || body.result === undefined) {
      throw new Error("Base RPC request failed");
    }
    return body.result;
  };
}

async function main(deps = {}, argv = process.argv.slice(2)) {
  const parsed = parseArgs(argv);
  const workerAddress = parsed.workerAddress || deps.workerAddress || process.env.TASKMARKET_WORKER_ADDRESS;
  const environmentSelfWallets = String(process.env.TASKMARKET_SELF_WALLETS || "")
    .split(",").map((value) => value.trim()).filter(Boolean);
  let selfWallets = parsed.selfWallets.length
    ? parsed.selfWallets
    : (deps.selfWallets || environmentSelfWallets);
  const selfWalletsModule = deps.selfWalletsModule || process.env.TASKMARKET_SELF_WALLETS_MODULE;
  if ((!Array.isArray(selfWallets) || selfWallets.length === 0) && selfWalletsModule) {
    const imported = await import(pathToFileURL(resolve(selfWalletsModule)).href);
    selfWallets = imported.SELF_WALLETS;
  }
  const apiUrl = cleanBaseUrl(parsed.apiUrl || deps.apiUrl || process.env.TASKMARKET_API_URL, DEFAULT_API);
  const rpcUrl = cleanBaseUrl(parsed.rpcUrl || deps.rpcUrl || process.env.BASE_RPC_URL, DEFAULT_RPC);
  const fetchImpl = deps.fetchImpl || globalThis.fetch;
  const discovered = await fetchTaskIds({ workerAddress, fetchImpl, apiUrl });
  const taskIds = [...new Set([...discovered, ...parsed.taskIds.map(taskId), ...(deps.taskIds || []).map(taskId)])];
  const fetchTask = deps.fetchTask || (async (id) => {
    const body = await fetchJson(`${apiUrl}/api/tasks/${encodeURIComponent(id)}`, fetchImpl);
    if (!body || typeof body !== "object" || Array.isArray(body)) {
      throw new Error("TaskMarket task readback is malformed");
    }
    return body;
  });
  const rpcCall = deps.rpcCall || rpcClient(fetchImpl, rpcUrl);
  const result = await processTaskMarketTasks({
    taskIds,
    workerAddress,
    selfWallets,
    fetchTask,
    rpcCall,
    recordEntry: deps.recordEntry || recordEarnLoopRevenue,
  });
  const output = {
    observed_at: (deps.now || (() => new Date()))().toISOString(),
    ok: true,
    worker_address: address(workerAddress, "worker address").toLowerCase(),
    ...result,
  };
  (deps.writeOutput || ((text) => process.stdout.write(text)))(`${JSON.stringify(output)}\n`);
  return output;
}

if (require.main === module) {
  main().catch(() => {
    process.stderr.write('{"ok":false,"error":"taskmarket_work_ledger_failed"}\n');
    process.exitCode = 1;
  });
}

module.exports = {
  DEFAULT_API,
  DEFAULT_RPC,
  fetchTaskIds,
  parseArgs,
  rpcClient,
  main,
};
