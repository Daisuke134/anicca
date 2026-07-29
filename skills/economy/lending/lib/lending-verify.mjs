// economy/lending/lib/lending-verify.mjs — effectful, EVM-JSON-RPC-backed repayment verification
// (REQ-108) and provisional-disbursement reconciliation (REQ-106). Reuses record-earn.mjs's own
// already-hardened pattern (__REPO_ROOT__/skills/self/founder-loop/record-earn.mjs lines 56, 65-72, 82-88):
// finalized-block-only scanning discipline, TRANSFER_TOPIC match, exact zero-padded-address equality —
// LITERALLY reused for the `to` side (that file's own FIND-704 fix), and EXTENDED, as a new sound
// application, to the `from` side (that file's own `from` topic is an unchecked substring — resolves
// FIND-105's honest-attribution requirement). NEVER escrow.mjs, which contains no Transfer-log parsing
// at all (corrects this feature's own prior FIND-007 mischaracterization).
//
// impl-review iteration-4, FIND-301 (critical): both replay-guard comparisons below (`alreadyCredited`,
// `alreadyRecorded`) now use `txHashesEqual` (`lending-signer.mjs`) instead of raw `===` — a tx_hash
// reaching loans.jsonl from the facilitator-format disbursement route vs. this module's own
// `eth_getLogs`-derived `extractTxHash` route has no shared, code-enforced casing contract, and an
// unnormalized comparison would silently fail to match, reopening FIND-201's cross-loan misattribution
// hazard on a casing difference alone.
import { txHashesEqual } from "./lending-signer.mjs";

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
  const alreadyCredited = (loanRows || []).some((row) => row && txHashesEqual(row.tx_hash, txHash));
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

// A malformed/non-hex log.data (mirrors safeBigIntNumber's own fail-closed discipline above) makes
// BigInt() throw — caught here so a corrupted/misbehaving RPC response never crashes reconciliation,
// it just fails that ONE log's own value-match (the log is correctly treated as non-matching, never as
// a false positive).
function safeBigIntValue(hexValue) {
  try {
    return BigInt(hexValue);
  } catch {
    return null;
  }
}

/**
 * reconcileProvisionalDisbursement — recovers a crashed/uncertain issuance attempt's own REAL transfer
 * via an on-chain block-range scan, WITHOUT ever disbursing a second time (REQ-106, resolves FIND-103/
 * FIND-201). Read-only: never invokes a transfer/settle call itself.
 *
 * impl-review iteration-2, FIND-101 (critical): matchesTransferLog alone only proves address+from+to
 * topic equality — it says nothing about whether the MATCHED transfer is actually THIS loan's own
 * disbursement, vs. some other, unrelated USDC transfer that happens to have moved between the exact
 * same two wallets within the lookback window (e.g. a completely different payment, or a repayment of a
 * PRIOR loan between the same lender/borrower pair). A value-blind match risks misattributing an
 * unrelated transfer as proof of THIS row's own disbursement (silently landing "active" with the WRONG
 * tx_hash while the intended borrower never actually received THIS loan's own principal_usd) — money
 * mis-accounting, not a UI nit. Fix: only a transfer whose OWN decoded value EXACTLY equals
 * loanRow.principal_usd (converted to USDC's 6-decimal base units, the SAME `Math.round(principal_usd *
 * 1e6)` convention `defaultDisburse` itself already uses to construct amountBase) counts as evidence of
 * THIS loan's own disbursement. An unrelated-value transfer between the same two wallets is correctly
 * left unmatched — the row stays whatever `resolveStaleProvisioning`'s caller decides (never falsely
 * "settled").
 *
 * impl-review iteration-3, FIND-201 (critical): an exact wallet-pair + exact-value match is STILL not
 * sufficient proof of THIS row's own disbursement when the SAME borrower has multiple stuck rows —
 * computeLoanCapUsd returns a flat cap for every cold-start attempt, so repeat stuck-row cycles to the
 * same struggling borrower share both the identical wallet pair AND the identical value FIND-101's own
 * fix now trusts. Fix: reuse verifyRepayment's own already-proven cross-ledger replay guard
 * (lending-verify.mjs:84-86) here too — a candidate log whose own tx_hash is ALREADY recorded against
 * ANY row in loanRows (this loan's own row or a DIFFERENT loan_id) is never trusted as evidence of this
 * row's disbursement. Fail-closed: such a candidate is treated as non-matching, never as a match — the
 * row stays unconfirmed rather than risk misattributing another loan's real transfer as this one's.
 */
export async function reconcileProvisionalDisbursement({ loanRow, loanRows, rpcUrl, fromBlock, toBlock }) {
  const fromTopic = padAddressToTopic(loanRow.lender_wallet);
  const toTopic = padAddressToTopic(loanRow.borrower_wallet);
  const logs = await rpcCall(rpcUrl, "eth_getLogs", [
    { address: USDC_BASE_MAINNET, topics: [TRANSFER_TOPIC, fromTopic, toTopic], fromBlock, toBlock },
  ]);
  const expectedValueBase = BigInt(Math.round(loanRow.principal_usd * 1e6));
  const matchingLog = (logs || []).find((log) => {
    if (!matchesTransferLog(log, fromTopic, toTopic)) return false;
    const valueBase = safeBigIntValue(log.data);
    if (valueBase === null || valueBase !== expectedValueBase) return false;
    // FIND-201: same guard verifyRepayment already applies — a tx_hash already bound to ANY loan row
    // (same-loan or cross-loan) can never be counted as proof of a DIFFERENT/this reconciliation's own
    // disbursement.
    const txHash = extractTxHash(log);
    const alreadyRecorded = (loanRows || []).some((row) => row && txHashesEqual(row.tx_hash, txHash));
    return !alreadyRecorded;
  });
  if (!matchingLog) return { found: false };
  return { found: true, txHash: extractTxHash(matchingLog) };
}
