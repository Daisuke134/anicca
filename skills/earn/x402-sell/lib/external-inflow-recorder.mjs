import {
  appendFileSync,
  closeSync,
  existsSync,
  mkdirSync,
  openSync,
  readFileSync,
  unlinkSync,
} from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
export const TRANSFER_TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef';

const DEFAULT_STATE_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', 'state');

function normalizeAddress(value) {
  const normalized = String(value || '').toLowerCase();
  return /^0x[0-9a-f]{40}$/.test(normalized) ? normalized : null;
}

function normalizeTx(value) {
  const normalized = String(value || '').toLowerCase();
  return /^0x[0-9a-f]{64}$/.test(normalized) ? normalized : null;
}

function topicAddress(address) {
  return `0x${address.slice(2).padStart(64, '0')}`;
}

function blockNumber(value) {
  try {
    const parsed = Number(BigInt(value));
    return Number.isSafeInteger(parsed) && parsed >= 0 ? parsed : null;
  } catch { return null; }
}

function receiptTransfer(receipt, { tx, payTo, finalizedBlock, selfSet }) {
  if (!receipt || receipt.status !== '0x1') return null;
  const receiptTx = normalizeTx(receipt.transactionHash);
  const receiptBlock = blockNumber(receipt.blockNumber);
  if (receiptTx !== tx || receiptBlock === null || receiptBlock > finalizedBlock) return null;

  const matches = (Array.isArray(receipt.logs) ? receipt.logs : []).filter((log) => {
    if (String(log?.address || '').toLowerCase() !== USDC_ADDRESS.toLowerCase()) return false;
    if (!Array.isArray(log.topics) || log.topics.length < 3) return false;
    if (String(log.topics[0] || '').toLowerCase() !== TRANSFER_TOPIC) return false;
    if (String(log.topics[2] || '').toLowerCase() !== topicAddress(payTo)) return false;
    const logTx = log.transactionHash == null ? tx : normalizeTx(log.transactionHash);
    return logTx === tx;
  });
  if (matches.length !== 1) return null;

  const log = matches[0];
  const fromTopic = String(log.topics[1] || '').toLowerCase();
  if (!/^0x[0-9a-f]{64}$/.test(fromTopic) || !/^0{24}[0-9a-f]{40}$/.test(fromTopic.slice(2))) return null;
  const from = normalizeAddress(`0x${fromTopic.slice(-40)}`);
  if (!from || selfSet.has(from)) return null;
  if (!/^0x[0-9a-f]+$/i.test(String(log.data || ''))) return null;
  let atomic;
  try { atomic = BigInt(log.data); } catch { return null; }
  if (atomic <= 0n) return null;

  return {
    tx,
    block: receiptBlock,
    from,
    to: payTo,
    payTo,
    usdc: Number(atomic) / 1_000_000,
    finalized: true,
    status: 'success',
    external: true,
  };
}

export async function collectVerifiedExternalInflows({
  payTo,
  fromBlock,
  rpcCall,
  selfWallets = [],
  settledTransactions = new Set(),
}) {
  const receiver = normalizeAddress(payTo);
  if (!receiver) throw new TypeError('payTo must be a valid EVM address');
  if (typeof rpcCall !== 'function') throw new TypeError('rpcCall must be a function');
  const settledSet = new Set([...settledTransactions].map(normalizeTx).filter(Boolean));

  const finalized = await rpcCall('eth_getBlockByNumber', ['finalized', false]);
  const finalizedBlock = blockNumber(finalized?.number);
  if (finalizedBlock === null) throw new Error('RPC returned no finalized block');
  const start = Number.isSafeInteger(Number(fromBlock)) && Number(fromBlock) >= 0
    ? Number(fromBlock)
    : 0;
  if (start > finalizedBlock || settledSet.size === 0) return { finalizedBlock, rows: [] };

  const candidates = await rpcCall('eth_getLogs', [{
    address: USDC_ADDRESS,
    fromBlock: `0x${start.toString(16)}`,
    toBlock: `0x${finalizedBlock.toString(16)}`,
    topics: [TRANSFER_TOPIC, null, topicAddress(receiver)],
  }]);
  if (!Array.isArray(candidates)) throw new Error('eth_getLogs returned a non-array');
  const txs = [...new Set(candidates.map((log) => normalizeTx(log?.transactionHash)).filter((tx) => tx && settledSet.has(tx)))];
  const selfSet = new Set([receiver, ...selfWallets.map(normalizeAddress).filter(Boolean)]);
  const rows = [];

  for (const tx of txs) {
    const receipt = await rpcCall('eth_getTransactionReceipt', [tx]);
    const transaction = await rpcCall('eth_getTransactionByHash', [tx]);
    const initiator = normalizeAddress(transaction?.from);
    if (!initiator || selfSet.has(initiator)) continue;
    const row = receiptTransfer(receipt, { tx, payTo: receiver, finalizedBlock, selfSet });
    if (row) rows.push(row);
  }
  return { finalizedBlock, rows };
}

export function walletLedgerPath(payTo, { stateDir = DEFAULT_STATE_DIR } = {}) {
  const receiver = normalizeAddress(payTo);
  if (!receiver) throw new TypeError('payTo must be a valid EVM address');
  return join(stateDir, `external-inflows-${receiver}.jsonl`);
}

function readExistingTransactions(ledgerPath) {
  if (!existsSync(ledgerPath)) return new Set();
  return new Set(readFileSync(ledgerPath, 'utf8').split('\n').filter(Boolean).flatMap((line) => {
    try {
      const tx = normalizeTx(JSON.parse(line)?.tx);
      return tx ? [tx] : [];
    } catch { return []; }
  }));
}

export function appendUniqueExternalInflows(ledgerPath, rows) {
  mkdirSync(dirname(ledgerPath), { recursive: true });
  const lockPath = `${ledgerPath}.lock`;
  let lock;
  try {
    lock = openSync(lockPath, 'wx');
    const seen = readExistingTransactions(ledgerPath);
    const fresh = [];
    let duplicates = 0;
    for (const row of rows || []) {
      const tx = normalizeTx(row?.tx);
      if (!tx || seen.has(tx)) {
        duplicates += 1;
        continue;
      }
      seen.add(tx);
      fresh.push({ ...row, tx });
    }
    if (fresh.length) appendFileSync(ledgerPath, `${fresh.map((row) => JSON.stringify(row)).join('\n')}\n`);
    return { recorded: fresh.length, duplicates };
  } finally {
    if (lock !== undefined) {
      closeSync(lock);
      try { unlinkSync(lockPath); } catch { /* already removed */ }
    }
  }
}
