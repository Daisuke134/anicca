"use strict";

const { toChecksumAddress } = require("./agent-wallet.js");
const { normaliseEntry } = require("./earnings-ledger.js");
const { recordEarnLoopRevenue } = require("./earnings-runtime.js");

const BASE_CHAIN_ID = 8453;
const USDC_ADDRESS = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913";
const TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";

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

function atomic(value, label) {
  const raw = String(value == null ? "" : value).trim();
  if (!/^\d+$/.test(raw) || BigInt(raw) <= 0n) fail(`${label} must be a positive atomic integer`);
  return BigInt(raw);
}

function integerHex(value) {
  try {
    const number = Number(BigInt(value));
    return Number.isSafeInteger(number) && number >= 0 ? number : null;
  } catch {
    return null;
  }
}

function topicAddress(value) {
  return `0x${value.slice(2).padStart(64, "0")}`;
}

function boundary(options) {
  const worker = address(options && options.workerAddress, "worker address");
  const selfWallets = new Set((Array.isArray(options && options.selfWallets) ? options.selfWallets : [])
    .map((value) => address(value, "self wallet")));
  selfWallets.add(worker);
  return { worker, selfWallets };
}

function validateAward(task, award, options) {
  if (!task || typeof task !== "object") fail("TaskMarket task is required");
  if (!award || typeof award !== "object") fail("TaskMarket award is required");
  const { worker, selfWallets } = boundary(options);
  const taskId = hash(task.id, "task id");
  if (task.status !== "completed") fail("TaskMarket task must be completed");
  if (task.selfAward === true) fail("TaskMarket self-award is not external revenue");
  const requester = address(task.requester, "requester");
  if (selfWallets.has(requester)) fail("TaskMarket requester is a self wallet");
  const awardedWorker = address(award.workerAddress, "awarded worker");
  if (awardedWorker !== worker) fail("TaskMarket award is not for the owned worker");
  const tx = hash(award.settlementTxHash, "settlement transaction");
  const gross = atomic(award.grossAmount, "gross amount");
  const payment = atomic(award.workerPayment, "worker payment");
  const fee = atomic(award.platformFee, "platform fee");
  if (payment + fee !== gross) fail("TaskMarket worker payment and fee must sum to gross");
  const rank = Number(award.rank);
  if (!Number.isSafeInteger(rank) || rank < 1) fail("TaskMarket award rank must be positive");
  const settledAt = new Date(award.settledAt);
  if (typeof award.settledAt !== "string" || Number.isNaN(settledAt.getTime())) {
    fail("TaskMarket settledAt must be a timestamp");
  }
  const listed = Array.isArray(task.awards) && task.awards.some((item) => (
    address(item && item.workerAddress, "listed award worker") === worker
    && hash(item && item.settlementTxHash, "listed settlement transaction") === tx
    && String(item && item.workerPayment) === payment.toString()
  ));
  if (!listed || !Number.isSafeInteger(task.awardCount) || task.awardCount < 1) {
    fail("TaskMarket award is not present in task readback");
  }
  return {
    worker, requester, taskId, tx, gross, payment, fee,
    rank, settledAt: settledAt.toISOString(),
  };
}

function taskMarketLedgerEntry(task, award, options = {}) {
  const verified = validateAward(task, award, options);
  if (!Number.isSafeInteger(options.receiptBlock) || options.receiptBlock < 0) {
    fail("receipt block must be a non-negative safe integer");
  }
  return normaliseEntry({
    entry_key: `taskmarket:${verified.taskId}:${verified.tx}:${verified.rank}:income`,
    wallet_address: toChecksumAddress(verified.worker.slice(2)),
    kind: "financial_external_income",
    amount_atomic: verified.payment.toString(),
    amount_decimals: 6,
    currency: "USD",
    occurred_at: verified.settledAt,
    tx_hash: verified.tx,
    source: "taskmarket_work",
    meta: {
      protocol: "taskmarket",
      network: "eip155:8453",
      task_id: verified.taskId,
      requester: verified.requester,
      worker: verified.worker,
      worker_agent_id: award.workerAgentId == null ? null : String(award.workerAgentId),
      rank: Number.isSafeInteger(award.rank) ? award.rank : null,
      gross_atomic: verified.gross.toString(),
      platform_fee_atomic: verified.fee.toString(),
      usdc_atomic: verified.payment.toString(),
      receipt_block: options.receiptBlock,
      finalized: true,
      external: true,
    },
  });
}

async function verifyTaskMarketAwardOnBase(task, award, options = {}) {
  let parsed;
  try {
    parsed = validateAward(task, award, options);
  } catch (error) {
    return { ok: false, reason: error.message };
  }
  if (typeof options.rpcCall !== "function") return { ok: false, reason: "rpc_required" };
  try {
    const chainId = integerHex(await options.rpcCall("eth_chainId", []));
    if (chainId !== BASE_CHAIN_ID) return { ok: false, reason: "wrong_chain" };
    const finalized = await options.rpcCall("eth_getBlockByNumber", ["finalized", false]);
    const finalizedBlock = integerHex(finalized && finalized.number);
    if (finalizedBlock == null) return { ok: false, reason: "finality_unavailable" };
    const receipt = await options.rpcCall("eth_getTransactionReceipt", [parsed.tx]);
    if (!receipt || receipt.status !== "0x1") return { ok: false, reason: "receipt_failed" };
    if (hash(receipt.transactionHash, "receipt transaction") !== parsed.tx) {
      return { ok: false, reason: "receipt_tx_mismatch" };
    }
    const receiptBlock = integerHex(receipt.blockNumber);
    if (receiptBlock == null || receiptBlock > finalizedBlock) {
      return { ok: false, reason: "not_finalized" };
    }
    const selfSet = parsed.selfWallets || boundary(options).selfWallets;
    const transfers = (Array.isArray(receipt.logs) ? receipt.logs : []).filter((log) => {
      if (address(log && log.address, "log token") !== USDC_ADDRESS) return false;
      if (!Array.isArray(log.topics) || log.topics.length < 3) return false;
      if (String(log.topics[0]).toLowerCase() !== TRANSFER_TOPIC) return false;
      if (String(log.topics[2]).toLowerCase() !== topicAddress(parsed.worker)) return false;
      if (!/^0x[0-9a-f]+$/i.test(String(log.data || ""))) return false;
      const sender = `0x${String(log.topics[1]).slice(-40).toLowerCase()}`;
      return !selfSet.has(sender) && BigInt(log.data) === parsed.payment;
    });
    if (transfers.length !== 1) return { ok: false, reason: "exact_transfer_missing" };
    return { ok: true, receiptBlock };
  } catch (error) {
    return { ok: false, reason: `rpc_or_receipt_invalid:${error.message}` };
  }
}

async function processTaskMarketTasks({
  taskIds,
  workerAddress,
  selfWallets,
  fetchTask,
  rpcCall,
  recordEntry = recordEarnLoopRevenue,
}) {
  if (!Array.isArray(taskIds)) throw new TypeError("taskIds must be an array");
  if (typeof fetchTask !== "function") throw new TypeError("fetchTask must be a function");
  if (typeof rpcCall !== "function") throw new TypeError("rpcCall must be a function");
  if (typeof recordEntry !== "function") throw new TypeError("recordEntry must be a function");
  const worker = address(workerAddress, "worker address");
  const result = {
    tasks_seen: taskIds.length,
    pending: 0,
    rejected: 0,
    recorded: 0,
    duplicates: 0,
    transactions: [],
  };
  for (const taskId of [...new Set(taskIds)]) {
    let current;
    try {
      current = await fetchTask(hash(taskId, "task id"));
    } catch {
      result.rejected += 1;
      continue;
    }
    const awards = Array.isArray(current && current.awards)
      ? current.awards.filter((item) => {
        try {
          return address(item && item.workerAddress, "award worker") === worker;
        } catch {
          return false;
        }
      })
      : [];
    if (current.status !== "completed" || awards.length === 0) {
      result.pending += 1;
      continue;
    }
    for (const currentAward of awards) {
      const verified = await verifyTaskMarketAwardOnBase(current, currentAward, {
        workerAddress: worker,
        selfWallets,
        rpcCall,
      });
      if (!verified.ok) {
        result.rejected += 1;
        continue;
      }
      let row;
      try {
        row = taskMarketLedgerEntry(current, currentAward, {
          workerAddress: worker,
          selfWallets,
          receiptBlock: verified.receiptBlock,
        });
      } catch {
        result.rejected += 1;
        continue;
      }
      const write = await recordEntry(row);
      result.transactions.push(row.tx_hash);
      if (write && write.duplicate) result.duplicates += 1;
      else result.recorded += 1;
    }
  }
  return result;
}

module.exports = {
  BASE_CHAIN_ID,
  USDC_ADDRESS,
  TRANSFER_TOPIC,
  taskMarketLedgerEntry,
  verifyTaskMarketAwardOnBase,
  processTaskMarketTasks,
};
