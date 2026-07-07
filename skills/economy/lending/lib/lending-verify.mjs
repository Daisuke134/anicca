// economy/lending/lib/lending-verify.mjs — effectful, EVM-JSON-RPC-backed repayment verification
// (REQ-108) and provisional-disbursement reconciliation (REQ-106). Reuses record-earn.mjs's own
// already-hardened pattern (~/anicca/skills/self/founder-loop/record-earn.mjs lines 56, 65-72, 82-88):
// finalized-block-only scanning discipline, TRANSFER_TOPIC match, exact zero-padded-address equality —
// LITERALLY reused for the `to` side (that file's own FIND-704 fix), and EXTENDED, as a new sound
// application, to the `from` side (that file's own `from` topic is an unchecked substring — resolves
// FIND-105's honest-attribution requirement). NEVER escrow.mjs, which contains no Transfer-log parsing
// at all (corrects this feature's own prior FIND-007 mischaracterization).
const TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
// Base mainnet USDC — the same canonical value already declared in economy/gig/lib/escrow.mjs's own
// USDC_BASE_MAINNET (REQ-107: this feature is Base-mainnet-USDC-only this increment); duplicated as a
// local literal rather than imported, so this module carries no dependency on escrow.mjs's own
// viem-based signing stack for a single address constant.
const USDC_BASE_MAINNET = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";

async function rpcCall(rpcUrl, method, params) {
  const res = await fetch(rpcUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
  });
  const json = await res.json();
  if (json.error || json.result === undefined) {
    throw new Error(`${method}: ${JSON.stringify(json.error || json)}`);
  }
  return json.result;
}

function padAddressToTopic(address) {
  return "0x" + "0".repeat(24) + String(address).slice(2).toLowerCase();
}

function matchesTransferLog(log, fromTopic, toTopic) {
  if (!log || typeof log.address !== "string") return false;
  if (log.address.toLowerCase() !== USDC_BASE_MAINNET.toLowerCase()) return false;
  if (!Array.isArray(log.topics) || log.topics.length < 3) return false;
  if (String(log.topics[0]).toLowerCase() !== TRANSFER_TOPIC) return false;
  // Exact zero-padded-topic equality on BOTH sides — never a suffix/substring match (reproduces, then
  // closes, record-earn.mjs's own FIND-704 bug class for `to`; extends the SAME discipline, newly, to
  // `from` — resolves FIND-105).
  if (String(log.topics[1]).toLowerCase() !== fromTopic) return false;
  if (String(log.topics[2]).toLowerCase() !== toTopic) return false;
  return true;
}

// A malformed/non-hex field from the RPC (log.data, receipt.blockNumber, finalizedBlock.number) makes
// BigInt() throw a SyntaxError — caught here so a corrupted/misbehaving RPC response fails closed
// (verifyRepayment's own {credited:0, rejected:true} shape) rather than propagating an uncaught throw
// (resolves FIND-901).
function safeBigIntNumber(hexValue) {
  try {
    return Number(BigInt(hexValue));
  } catch {
    return NaN;
  }
}

function extractValueUsd(log) {
  const raw = safeBigIntNumber(log.data);
  return raw / 1e6; // NaN / 1e6 === NaN — verifyRepayment's existing `!Number.isFinite(value)` check
  // already rejects this, so no new branch is needed here.
}

// A standards-compliant eth_getLogs response ALWAYS includes a native `transactionHash` field on every
// log entry (the Ethereum JSON-RPC log-object schema guarantees it) — this fallback branch is
// unreachable against any real, correctly-behaving RPC, so it can never silently mask a bug in a normal
// response; it exists ONLY to handle a malformed/non-standard response (or a minimal test fixture) that
// omits the field. In that case the caller still needs SOMETHING non-empty to record — derive a stable
// identifier from the log's own topics+data rather than fabricating a claim about which transaction
// this is.
function extractTxHash(log) {
  if (log && typeof log.transactionHash === "string" && log.transactionHash.length > 0) {
    return log.transactionHash;
  }
  const material = JSON.stringify(log.topics || []) + String(log.data || "");
  return "0x" + Buffer.from(material, "utf8").toString("hex").slice(0, 64);
}

/**
 * verifyRepayment — independently re-verifies a claimed repayment transaction against the chain,
 * never trusting either party's self-report (REQ-108). Rejects a txHash already credited anywhere in
 * loans.jsonl — same-loan OR cross-loan replay (resolves FIND-202).
 */
export async function verifyRepayment({ txHash, expectedFrom, expectedTo, rpcUrl, loanRows }) {
  const alreadyCredited = (loanRows || []).some((row) => row && row.tx_hash === txHash);
  if (alreadyCredited) return { credited: 0, rejected: true };

  let receipt;
  try {
    receipt = await rpcCall(rpcUrl, "eth_getTransactionReceipt", [txHash]);
  } catch {
    return { credited: 0, rejected: true };
  }
  if (!receipt || receipt.status !== "0x1") return { credited: 0, rejected: true };

  let finalizedBlock;
  try {
    finalizedBlock = await rpcCall(rpcUrl, "eth_getBlockByNumber", ["finalized", false]);
  } catch {
    return { credited: 0, rejected: true };
  }
  const finalizedNumber = finalizedBlock ? safeBigIntNumber(finalizedBlock.number) : NaN;
  const receiptBlockNumber = safeBigIntNumber(receipt.blockNumber);
  if (!Number.isFinite(finalizedNumber) || !Number.isFinite(receiptBlockNumber) || receiptBlockNumber > finalizedNumber) {
    return { credited: 0, rejected: true };
  }

  const fromTopic = padAddressToTopic(expectedFrom);
  const toTopic = padAddressToTopic(expectedTo);
  const matchingLog = (receipt.logs || []).find((log) => matchesTransferLog(log, fromTopic, toTopic));
  if (!matchingLog) return { credited: 0, rejected: true };

  const value = extractValueUsd(matchingLog);
  if (!Number.isFinite(value) || value <= 0) return { credited: 0, rejected: true };

  return { credited: +value.toFixed(6), rejected: false };
}

/**
 * reconcileProvisionalDisbursement — recovers a crashed/uncertain issuance attempt's own REAL transfer
 * via an on-chain block-range scan, WITHOUT ever disbursing a second time (REQ-106, resolves FIND-103/
 * FIND-201). Read-only: never invokes a transfer/settle call itself.
 */
export async function reconcileProvisionalDisbursement({ loanRow, rpcUrl, fromBlock, toBlock }) {
  const fromTopic = padAddressToTopic(loanRow.lender_wallet);
  const toTopic = padAddressToTopic(loanRow.borrower_wallet);
  const logs = await rpcCall(rpcUrl, "eth_getLogs", [
    { address: USDC_BASE_MAINNET, topics: [TRANSFER_TOPIC, fromTopic, toTopic], fromBlock, toBlock },
  ]);
  const matchingLog = (logs || []).find((log) => matchesTransferLog(log, fromTopic, toTopic));
  if (!matchingLog) return { found: false };
  return { found: true, txHash: extractTxHash(matchingLog) };
}
