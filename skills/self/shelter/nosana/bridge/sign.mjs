// sign.mjs — the ONE place this feature signs a Base (EVM) transaction. Every field (nonce, gas,
// fees, chainId, calldata) is supplied by the caller, already fetched for real; this module does
// no network I/O itself, only in-process signing via viem/accounts (this feature's one new
// dependency — see README).
//
// Money-safety property this exists for: viem's ECDSA signing (via @noble/curves) is
// RFC6979-deterministic given the same (privateKey, message) — the exact same property
// funding/acquire-nos.mjs relies on for Solana's ed25519 signatures (see that file's
// transactionSignatureBase58 doc comment). That means the signed transaction's hash is KNOWN
// before it is ever broadcast, which is what lets bridge.mjs write an at-most-once intent record
// with a real, verifiable hash BEFORE calling eth_sendRawTransaction — the hash is later looked up
// via eth_getTransactionReceipt regardless of whether the send call itself throws, times out, or
// silently double-broadcasts (idempotent by construction: the network only ever has ONE
// transaction with that hash).

import { privateKeyToAccount } from "viem/accounts";
import { keccak256 } from "viem";

/**
 * @param {object} p
 * @param {`0x${string}`} p.privateKey
 * @param {number} p.chainId
 * @param {bigint} p.nonce
 * @param {`0x${string}`} p.to
 * @param {`0x${string}`} p.data
 * @param {bigint} p.gas — gas limit.
 * @param {bigint} p.maxFeePerGas
 * @param {bigint} p.maxPriorityFeePerGas
 * @param {bigint} [p.value]
 * @returns {Promise<{signedTxHex: `0x${string}`, txHash: `0x${string}`}>}
 */
export async function signBaseTransaction({
  privateKey,
  chainId,
  nonce,
  to,
  data,
  gas,
  maxFeePerGas,
  maxPriorityFeePerGas,
  value = 0n,
}) {
  const account = privateKeyToAccount(privateKey);
  const signedTxHex = await account.signTransaction({
    chainId,
    nonce: Number(nonce),
    to,
    data,
    gas,
    maxFeePerGas,
    maxPriorityFeePerGas,
    value,
    type: "eip1559",
  });
  const txHash = keccak256(signedTxHex);
  return { signedTxHex, txHash };
}
