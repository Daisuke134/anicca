// verify-tx — read a Base (or any EVM) tx receipt status over JSON-RPC.
// Pure transport: fetch is injectable so tests never touch the network.
// Returns "0x1" (success) / "0x0" (reverted) / null (receipt not yet available).
const BASE_RPC = process.env.BASE_RPC_URL || "https://mainnet.base.org";
const TX_RE = /^0x[0-9a-fA-F]{64}$/;
const ADDRESS_RE = /^0x[0-9a-fA-F]{40}$/;
const TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";

function normalizeHash(value) {
  const hash = typeof value === "string" ? value.trim().toLowerCase() : "";
  return TX_RE.test(hash) ? hash : null;
}

function normalizeAddress(value) {
  const address = typeof value === "string" ? value.trim().toLowerCase() : "";
  return ADDRESS_RE.test(address) ? address : null;
}

function topicAddress(value) {
  const address = normalizeAddress(value);
  return address ? `0x${address.slice(2).padStart(64, "0")}` : null;
}

function hexInteger(value) {
  if (typeof value === "bigint") return value >= 0n ? value : null;
  if (typeof value === "number") return Number.isSafeInteger(value) && value >= 0 ? BigInt(value) : null;
  if (typeof value !== "string" || !/^(?:0x[0-9a-f]+|[0-9]+)$/i.test(value.trim())) return null;
  try {
    const parsed = /^0x/i.test(value.trim()) ? BigInt(value.trim()) : BigInt(value.trim());
    return parsed >= 0n ? parsed : null;
  } catch {
    return null;
  }
}

function chainIdNumber(value) {
  if (typeof value === "string") {
    const lower = value.trim().toLowerCase();
    if (lower === "base" || lower === "base-mainnet" || lower === "base_mainnet") return 8453;
    if (lower === "base-sepolia" || lower === "base_sepolia") return 84532;
    if (lower.startsWith("eip155:")) return chainIdNumber(lower.slice(7));
  }
  const parsed = hexInteger(value);
  return parsed !== null && parsed <= BigInt(Number.MAX_SAFE_INTEGER) ? Number(parsed) : null;
}

function expectedValueAtomic(expected) {
  const raw = expected?.expected_amount_atomic ?? expected?.expectedAmountAtomic
    ?? expected?.amount_atomic ?? expected?.amountAtomic;
  if (raw !== undefined && raw !== null) return hexInteger(raw);
  const decimalAmount = expected?.expected_amount ?? expected?.expectedAmount;
  if (decimalAmount === undefined || decimalAmount === null) return null;
  const decimals = expected?.asset_decimals ?? expected?.assetDecimals ?? expected?.decimals ?? 6;
  if (!Number.isInteger(decimals) || decimals < 0 || decimals > 36) return null;
  const text = typeof decimalAmount === "number" ? String(decimalAmount) : String(decimalAmount).trim();
  if (!/^\d+(?:\.\d+)?$/.test(text)) return null;
  const [whole, fraction = ""] = text.split(".");
  if (fraction.length > decimals) return null;
  try { return BigInt(`${whole}${fraction.padEnd(decimals, "0")}`); } catch { return null; }
}

async function rpcCall(rpc, fetchImpl, method, params) {
  const response = await fetchImpl(rpc, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
  });
  if (!response || !response.ok) throw new Error(`verify-tx: rpc ${response?.status ?? "error"}`);
  const json = await response.json();
  if (json?.error) throw new Error("verify-tx: rpc error");
  return json?.result;
}

export async function receiptStatus(txHash, opts = {}) {
  if (typeof txHash !== "string" || !TX_RE.test(txHash)) {
    throw new Error(`verify-tx: not a tx hash: ${txHash}`);
  }
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  const rpc = opts.rpc || BASE_RPC;
  const res = await fetchImpl(rpc, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_getTransactionReceipt", params: [txHash] }),
  });
  if (!res.ok) throw new Error(`verify-tx: rpc ${res.status}`);
  const j = await res.json();
  const receipt = j && j.result;
  if (!receipt || typeof receipt.status !== "string") return null;
  return receipt.status; // "0x1" | "0x0"
}

/**
 * Verify one successful EVM receipt and its exact ERC-20 Transfer log.  This is intentionally a
 * read-only transport boundary: callers provide an injected fetch in tests and no private data is
 * ever included in errors or the returned evidence.
 *
 * Accepted call forms are verifyEvmReceipt({tx_hash, expected_*..., fetchImpl, rpc}) and the
 * compatibility form verifyEvmReceipt(txHash, expected, opts).  `verified:false` is returned for
 * malformed/mismatched provider data; transport/RPC failures also fail closed as false rather than
 * turning a successful status into a revenue claim.
 */
export async function verifyEvmReceipt(input, expected = {}, options = {}) {
  const objectForm = input && typeof input === "object" && !Array.isArray(input);
  const request = objectForm
    ? { ...input, ...(input.expected && typeof input.expected === "object" ? input.expected : {}), ...(input.opts && typeof input.opts === "object" ? input.opts : {}) }
    : { ...expected, tx_hash: input, ...options };
  const txHash = normalizeHash(request.tx_hash ?? request.txHash ?? request.transaction_hash ?? request.transactionHash);
  const fetchImpl = request.fetchImpl || request.fetch || globalThis.fetch;
  const rpc = request.rpc || request.rpcUrl || BASE_RPC;
  const expectedChain = request.expected_chain_id ?? request.expectedChainId ?? request.expected_chain ?? request.expectedChain
    ?? request.chain_id ?? request.chainId;
  const expectedContract = request.expected_contract ?? request.expectedContract ?? request.contract
    ?? request.asset_contract ?? request.assetContract ?? request.expected_asset_contract ?? request.expectedAssetContract
    ?? request.asset_address ?? request.assetAddress;
  const expectedPayer = request.expected_payer ?? request.expectedPayer ?? request.payer ?? request.from;
  const expectedRecipient = request.expected_recipient ?? request.expectedRecipient ?? request.recipient ?? request.to;
  const expectedLogIndex = request.expected_log_index ?? request.expectedLogIndex ?? request.expected_logIndex
    ?? request.log_index ?? request.logIndex;
  const amountAtomic = expectedValueAtomic(request);
  if (!txHash || typeof fetchImpl !== "function") return { verified: false, status: null, reason: "invalid_request" };
  const contract = expectedContract == null ? null : normalizeAddress(expectedContract);
  const payer = expectedPayer == null ? null : normalizeAddress(expectedPayer);
  const recipient = expectedRecipient == null ? null : normalizeAddress(expectedRecipient);
  if ((expectedContract != null && !contract) || (expectedPayer != null && !payer) || (expectedRecipient != null && !recipient)) {
    return { verified: false, status: null, reason: "invalid_expected_address" };
  }
  if (request.expected_amount_atomic !== undefined || request.expectedAmountAtomic !== undefined
    || request.amount_atomic !== undefined || request.amountAtomic !== undefined
    || request.expected_amount !== undefined || request.expectedAmount !== undefined) {
    if (amountAtomic === null) return { verified: false, status: null, reason: "invalid_expected_amount" };
  }
  let chainId = null;
  try {
    if (expectedChain !== undefined && expectedChain !== null) {
      chainId = chainIdNumber(await rpcCall(rpc, fetchImpl, "eth_chainId", []));
      const expectedNumber = chainIdNumber(expectedChain);
      if (chainId === null || expectedNumber === null || chainId !== expectedNumber) {
        return { verified: false, status: null, chain_id: chainId, reason: "wrong_chain" };
      }
    }
    const receipt = await rpcCall(rpc, fetchImpl, "eth_getTransactionReceipt", [txHash]);
    if (!receipt || receipt.status !== "0x1") {
      return { verified: false, status: receipt?.status ?? null, chain_id: chainId, reason: "not_successful" };
    }
    if (receipt.transactionHash != null && normalizeHash(receipt.transactionHash) !== txHash) {
      return { verified: false, status: receipt.status, chain_id: chainId, reason: "wrong_transaction" };
    }
    const wantedIndex = expectedLogIndex === undefined || expectedLogIndex === null ? null : hexInteger(expectedLogIndex);
    if (expectedLogIndex !== undefined && expectedLogIndex !== null && wantedIndex === null) {
      return { verified: false, status: receipt.status, chain_id: chainId, reason: "invalid_log_index" };
    }
    const logs = Array.isArray(receipt.logs) ? receipt.logs : [];
    const matches = logs.filter((log) => {
      if (!log || !normalizeAddress(log.address)) return false;
      if (contract && String(log.address).toLowerCase() !== contract) return false;
      if (log.transactionHash != null && normalizeHash(log.transactionHash) !== txHash) return false;
      if (!Array.isArray(log.topics) || log.topics.length < 3 || String(log.topics[0]).toLowerCase() !== TRANSFER_TOPIC) return false;
      if (!/^0x[0-9a-f]{64}$/i.test(String(log.topics[1])) || !/^0x[0-9a-f]{64}$/i.test(String(log.topics[2]))) return false;
      if (payer && String(log.topics[1]).toLowerCase() !== topicAddress(payer)) return false;
      if (recipient && String(log.topics[2]).toLowerCase() !== topicAddress(recipient)) return false;
      if (wantedIndex !== null && hexInteger(log.logIndex) !== wantedIndex) return false;
      if (amountAtomic !== null) {
        const actual = hexInteger(log.data);
        if (actual === null || actual !== amountAtomic) return false;
      }
      return true;
    });
    if (matches.length !== 1) {
      return { verified: false, status: receipt.status, chain_id: chainId, reason: "transfer_not_unique" };
    }
    const transfer = matches[0];
    const transferPayer = `0x${String(transfer.topics[1]).slice(-40).toLowerCase()}`;
    const transferRecipient = `0x${String(transfer.topics[2]).slice(-40).toLowerCase()}`;
    if (transferPayer === transferRecipient) {
      return { verified: false, status: receipt.status, chain_id: chainId, reason: "self_payment" };
    }
    const actualIndex = hexInteger(transfer.logIndex);
    const actualAmount = hexInteger(transfer.data);
    return {
      verified: true,
      status: receipt.status,
      chain_id: chainId,
      tx_hash: txHash,
      transfer: {
        contract: String(transfer.address).toLowerCase(),
        payer: transferPayer,
        recipient: transferRecipient,
        amount_atomic: actualAmount === null ? null : actualAmount.toString(),
        log_index: actualIndex === null ? null : Number(actualIndex),
      },
      receipt,
    };
  } catch {
    return { verified: false, status: null, chain_id: chainId, reason: "rpc_failure" };
  }
}

export const verifyEvmTransfer = verifyEvmReceipt;
export const verifyTransactionReceipt = verifyEvmReceipt;
export const verifyTxReceipt = verifyEvmReceipt;
export const verifyReceipt = verifyEvmReceipt;
