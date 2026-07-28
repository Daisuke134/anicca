"use strict";

const { promisify } = require("node:util");
const { execFile } = require("node:child_process");
const {
  BASE_CHAIN_ID,
  exactTransferReceipt,
} = require("./base-usdc-payout.js");

const DEFAULT_API = "https://api.taskmarket.dev";
const DEFAULT_RPC = "https://mainnet.base.org";
const TASKMARKET_CLI = "/opt/homebrew/bin/taskmarket";
const MAX_JSON_BYTES = 64_000;
const DEFAULT_CONFIRMATION_ATTEMPTS = 120;

function fail(message) {
  throw new Error(message);
}

function address(value, label) {
  const raw = String(value == null ? "" : value).trim().toLowerCase();
  if (!/^0x[0-9a-f]{40}$/.test(raw)) fail(`${label} must be an EVM address`);
  return raw;
}

function hash(value, label) {
  const raw = String(value == null ? "" : value).trim().toLowerCase();
  if (!/^0x[0-9a-f]{64}$/.test(raw)) fail(`${label} must be a transaction hash`);
  return raw;
}

function nonNegativeCount(value, label) {
  if (!Number.isSafeInteger(value) || value < 0) fail(`${label} must be a non-negative integer`);
  return value;
}

function exactAtomic(value, { allowZero = false } = {}) {
  const raw = String(value == null ? "" : value).trim();
  if (!/^\d+$/.test(raw)) fail("USDC balance must be an exact atomic integer");
  const amount = BigInt(raw);
  if (amount < 0n || (!allowZero && amount === 0n)) fail("USDC amount must be positive");
  return amount;
}

function atomicToUsdc(value) {
  const amount = exactAtomic(value);
  const whole = amount / 1_000_000n;
  const fraction = String(amount % 1_000_000n).padStart(6, "0");
  return `${whole}.${fraction}`;
}

function cleanHttpUrl(value, fallback) {
  const parsed = new URL(String(value || fallback));
  if (!["http:", "https:"].includes(parsed.protocol) || parsed.username || parsed.password) {
    fail("URL must be an uncredentialed HTTP(S) URL");
  }
  return parsed.toString().replace(/\/+$/, "");
}

function parseJson(text, label) {
  const raw = String(text == null ? "" : text);
  if (Buffer.byteLength(raw) > MAX_JSON_BYTES) fail(`${label} exceeds bounded size`);
  try {
    return JSON.parse(raw);
  } catch {
    fail(`${label} is not JSON`);
  }
}

function verifiedAwardCount(ledgerResult, workerAddress) {
  if (!ledgerResult || typeof ledgerResult !== "object" || ledgerResult.ok !== true) {
    fail("TaskMarket ledger result is not successful");
  }
  if (address(ledgerResult.worker_address, "ledger worker") !== workerAddress) {
    fail("TaskMarket ledger result belongs to a different worker");
  }
  const recorded = nonNegativeCount(ledgerResult.recorded, "recorded count");
  const duplicates = nonNegativeCount(ledgerResult.duplicates, "duplicate count");
  const count = recorded + duplicates;
  if (!Array.isArray(ledgerResult.transactions)) {
    fail("TaskMarket ledger result has no transaction evidence");
  }
  if (count > 0) {
    const transactions = [...new Set(ledgerResult.transactions.map((value) => hash(value, "award transaction")))];
    if (transactions.length < count) {
      fail("TaskMarket ledger result has insufficient transaction evidence");
    }
  }
  return count;
}

async function fetchJson(url, fetchImpl) {
  const response = await fetchImpl(url, { signal: AbortSignal.timeout(30_000) });
  const text = await response.text();
  if (!response.ok) fail(`TaskMarket request failed (${response.status})`);
  return parseJson(text, "TaskMarket response");
}

async function runCli(args, deps) {
  const execute = deps.execFileImpl || promisify(execFile);
  const result = await execute(TASKMARKET_CLI, args, {
    timeout: 60_000,
    maxBuffer: MAX_JSON_BYTES,
    windowsHide: true,
  });
  const parsed = parseJson(result && result.stdout, "TaskMarket CLI response");
  if (!parsed || parsed.ok !== true || !parsed.data || typeof parsed.data !== "object") {
    fail("TaskMarket CLI did not return a successful result");
  }
  return parsed.data;
}

function rpcBoundary(rpcUrl, fetchImpl) {
  let id = 0;
  return async (method, params) => {
    const response = await fetchImpl(rpcUrl, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: ++id, method, params }),
      signal: AbortSignal.timeout(30_000),
    });
    const body = await response.json().catch(() => null);
    if (!response.ok || !body || body.error || body.result === undefined) {
      fail(`Base RPC ${method} failed`);
    }
    return body.result;
  };
}

function hexInteger(value, label) {
  const raw = String(value == null ? "" : value);
  if (!/^0x[0-9a-f]+$/i.test(raw)) fail(`${label} must be a hex integer`);
  return BigInt(raw);
}

async function finalizedReceipt(txHash, expected, rpcCall, deps) {
  const attempts = deps.confirmationAttempts == null
    ? DEFAULT_CONFIRMATION_ATTEMPTS
    : deps.confirmationAttempts;
  if (!Number.isSafeInteger(attempts) || attempts < 1 || attempts > 600) {
    fail("confirmation attempts are out of bounds");
  }
  const sleep = deps.sleep || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  const chainId = hexInteger(await rpcCall("eth_chainId", []), "chain ID");
  if (chainId !== BigInt(BASE_CHAIN_ID)) fail("handoff RPC is not Base mainnet");
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const receipt = await rpcCall("eth_getTransactionReceipt", [txHash]);
    if (receipt) {
      const blockNumber = exactTransferReceipt(receipt, expected);
      const finalized = await rpcCall("eth_getBlockByNumber", ["finalized", false]);
      if (finalized && hexInteger(finalized.number, "finalized block") >= BigInt(blockNumber)) {
        return blockNumber;
      }
    }
    if (attempt + 1 < attempts) await sleep(1_000);
  }
  fail("TaskMarket handoff was not finalized before the confirmation deadline");
}

async function handoffTaskMarketAwards(request = {}, deps = {}) {
  const worker = address(request.workerAddress, "worker address");
  const destination = address(request.destination, "withdrawal destination");
  const awardCount = verifiedAwardCount(request.ledgerResult, worker);
  if (awardCount === 0) {
    return {
      ok: true,
      status: "noop",
      reason: "no_verified_award",
      verified_awards: 0,
    };
  }

  const fetchImpl = deps.fetchImpl || globalThis.fetch;
  if (typeof fetchImpl !== "function") fail("TaskMarket handoff needs fetch");
  const apiUrl = cleanHttpUrl(request.apiUrl, DEFAULT_API);
  const withdrawal = await fetchJson(
    `${apiUrl}/api/wallet/withdrawal-address?address=${encodeURIComponent(worker)}`,
    fetchImpl,
  );
  if (address(withdrawal.withdrawalAddress, "registered withdrawal destination") !== destination) {
    fail("registered withdrawal destination does not match Life Manager");
  }

  const balance = await runCli(["wallet", "balance"], deps);
  if (address(balance.address, "TaskMarket balance address") !== worker) {
    fail("TaskMarket balance belongs to a different worker");
  }
  const amount = exactAtomic(balance.balanceBaseUnits, { allowZero: true });
  if (amount === 0n) {
    return {
      ok: true,
      status: "noop",
      reason: "worker_balance_zero",
      verified_awards: awardCount,
    };
  }

  const withdraw = await runCli(["withdraw", atomicToUsdc(amount)], deps);
  const txHash = hash(withdraw.txHash, "withdrawal transaction");
  if (exactAtomic(withdraw.amountBaseUnits) !== amount) {
    fail("TaskMarket withdrawal amount does not match measured balance");
  }
  if (address(withdraw.to, "TaskMarket withdrawal destination") !== destination) {
    fail("TaskMarket withdrawal destination changed during execution");
  }

  const rpcUrl = cleanHttpUrl(request.rpcUrl, DEFAULT_RPC);
  const rpcCall = deps.rpcCall || rpcBoundary(rpcUrl, fetchImpl);
  const blockNumber = await finalizedReceipt(txHash, {
    txHash,
    amountAtomic: amount.toString(),
    from: worker,
    to: destination,
  }, rpcCall, deps);

  return {
    ok: true,
    status: "transferred",
    verified_awards: awardCount,
    tx_hash: txHash,
    amount_atomic: amount.toString(),
    from: worker,
    to: destination,
    block_number: blockNumber,
  };
}

module.exports = {
  DEFAULT_API,
  DEFAULT_RPC,
  TASKMARKET_CLI,
  atomicToUsdc,
  verifiedAwardCount,
  handoffTaskMarketAwards,
};
