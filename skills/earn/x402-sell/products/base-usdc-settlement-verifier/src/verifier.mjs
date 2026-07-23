export const BASE_CHAIN_ID = 8453;
export const BASE_USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
export const TRANSFER_TOPIC = [
  '0xddf252ad1be2c89b69c2b068fc378daa',
  '952ba7f163c4a11628f55a4df523b3ef',
].join('');

const TX_RE = /^0x[0-9a-fA-F]{64}$/;
const ADDRESS_RE = /^0x[0-9a-fA-F]{40}$/;

function reject(reason) {
  throw new Error(`settlement verification failed: ${reason}`);
}

function normalizeAddress(value, name) {
  if (!ADDRESS_RE.test(String(value || ''))) reject(`invalid ${name}`);
  return String(value).toLowerCase();
}

function addressFromTopic(topic, name) {
  if (!/^0x[0-9a-fA-F]{64}$/.test(String(topic || ''))
      || !String(topic).slice(2, 26).match(/^0{24}$/)) reject(`invalid ${name} topic`);
  return `0x${String(topic).slice(26)}`.toLowerCase();
}

function blockNumber(value, name) {
  let parsed;
  try { parsed = BigInt(value); } catch { reject(`invalid ${name}`); }
  if (parsed < 0n || parsed > BigInt(Number.MAX_SAFE_INTEGER)) reject(`invalid ${name}`);
  return Number(parsed);
}

export async function verifyBaseUsdcSettlement({
  txHash,
  expectedPayTo,
  expectedAmountAtomic,
  selfWallets = [],
  rpcUrl = 'https://mainnet.base.org',
  fetchImpl = fetch,
}) {
  if (!TX_RE.test(String(txHash || ''))) reject('invalid tx hash');
  const tx = String(txHash).toLowerCase();
  const payTo = normalizeAddress(expectedPayTo, 'payTo');
  let amount;
  try { amount = BigInt(expectedAmountAtomic); } catch { reject('invalid amount'); }
  if (amount <= 0n) reject('invalid amount');
  if (!Array.isArray(selfWallets)) reject('invalid self wallets');
  const owned = new Set(selfWallets.map((wallet) => normalizeAddress(wallet, 'self wallet')));
  if (typeof rpcUrl !== 'string' || !/^https:\/\//.test(rpcUrl)) reject('invalid RPC URL');

  let requestId = 0;
  async function rpc(method, params) {
    const response = await fetchImpl(rpcUrl, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: ++requestId, method, params }),
    });
    if (!response.ok) reject(`${method} HTTP ${response.status}`);
    const body = await response.json();
    if (body?.error || body?.result === undefined || body?.result === null) reject(`${method} RPC error`);
    return body.result;
  }

  const chainId = blockNumber(await rpc('eth_chainId', []), 'chain ID');
  if (chainId !== BASE_CHAIN_ID) reject('wrong chain');
  const finalized = await rpc('eth_getBlockByNumber', ['finalized', false]);
  const finalizedBlock = blockNumber(finalized?.number, 'finalized block');
  const [receipt, transaction] = await Promise.all([
    rpc('eth_getTransactionReceipt', [tx]),
    rpc('eth_getTransactionByHash', [tx]),
  ]);

  if (String(receipt?.transactionHash || '').toLowerCase() !== tx) reject('receipt tx mismatch');
  if (blockNumber(receipt?.status, 'receipt status') !== 1) reject('failed receipt');
  const settledBlock = blockNumber(receipt?.blockNumber, 'receipt block');
  if (settledBlock > finalizedBlock) reject('transaction is not finalized');
  const receiptBlockHash = String(receipt?.blockHash || '').toLowerCase();
  if (!TX_RE.test(receiptBlockHash)) reject('invalid receipt block hash');
  const canonicalBlock = await rpc('eth_getBlockByNumber', [`0x${settledBlock.toString(16)}`, false]);
  if (blockNumber(canonicalBlock?.number, 'canonical block') !== settledBlock
      || String(canonicalBlock?.hash || '').toLowerCase() !== receiptBlockHash) {
    reject('canonical block mismatch');
  }
  if (String(transaction?.hash || '').toLowerCase() !== tx) reject('transaction mismatch');
  const initiator = normalizeAddress(transaction?.from, 'transaction sender');
  if (owned.has(initiator)) reject('self transaction sender');

  const matches = [];
  for (const log of Array.isArray(receipt?.logs) ? receipt.logs : []) {
    if (String(log?.address || '').toLowerCase() !== BASE_USDC.toLowerCase()) continue;
    if (!Array.isArray(log?.topics) || log.topics.length < 3
        || String(log.topics[0]).toLowerCase() !== TRANSFER_TOPIC) continue;
    const payer = addressFromTopic(log.topics[1], 'payer');
    const receiver = addressFromTopic(log.topics[2], 'receiver');
    let transferred;
    try { transferred = BigInt(log.data); } catch { continue; }
    if (receiver === payTo && transferred === amount) matches.push({ payer, receiver });
  }
  if (matches.length !== 1) reject(matches.length ? 'ambiguous matching transfer' : 'exact USDC transfer not found');
  if (owned.has(matches[0].payer)) reject('self transfer sender');

  return {
    verified: true,
    chainId,
    txHash: tx,
    blockNumber: settledBlock,
    finalizedBlock,
    usdc: BASE_USDC.toLowerCase(),
    payer: matches[0].payer,
    payTo,
    amountAtomic: amount.toString(),
  };
}
