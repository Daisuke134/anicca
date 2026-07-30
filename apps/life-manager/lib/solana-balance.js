"use strict";
// AE-ZERO-START-1 §4.4 — the measured native Solana balance.
//
// Deliberately the mirror of `lib/base-usdc-balance.js` rather than an addition to
// `lib/agent-wallet-solana.js`: the EVM rail already keeps key derivation (agent-wallet.js) and balance
// reading (base-usdc-balance.js) in separate files, and keeping the module that handles secrets free of
// network calls is worth a file of its own.
//
// One rule: never return a number the chain did not give us. A defaulted 0 would be published to the
// tenant as a measured fact, and "$0.00 that was not measured is a lie". Every unclean answer throws.
//
// Lamports are integers and JavaScript numbers stop being exact at 2^53, so the value crosses this
// boundary as a decimal string and is formatted with BigInt arithmetic only.

const { isSolanaAddress } = require("./agent-wallet-solana.js");

const DEFAULT_SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com";
// §12.3 NEW-8 — the zero-start message says "nothing here is estimated", and a `confirmed` balance can
// still be rolled back. The read has to earn that sentence, so the commitment is fixed at `finalized` and
// is deliberately NOT a caller option: nobody should be able to talk it down.
const SOLANA_BALANCE_COMMITMENT = "finalized";
const LAMPORTS_PER_SOL = 1_000_000_000n;
const SOL_DECIMALS = 9;

async function readSolBalance(walletAddress, opts = {}) {
  const address = String(walletAddress == null ? "" : walletAddress).trim();
  if (!isSolanaAddress(address)) throw new Error("Solana balance needs a base58 Solana address");
  const rpcUrl = opts.rpcUrl || DEFAULT_SOLANA_RPC_URL;
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  if (typeof fetchImpl !== "function") throw new Error("Solana balance reader needs fetch");

  const response = await fetchImpl(rpcUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      method: "getBalance",
      params: [address, { commitment: SOLANA_BALANCE_COMMITMENT }],
    }),
  });
  const body = await (response && typeof response.json === "function"
    ? response.json().catch(() => null)
    : Promise.resolve(null));
  const status = response ? response.status : "no response";
  if (!response || !response.ok || !body || body.error) {
    throw new Error(`Solana balance read failed (${status})`);
  }
  const value = body.result && body.result.value;
  // Number.isSafeInteger, not Number.isInteger: above 2^53 the RPC's own JSON number is already lossy,
  // and quietly rounding a balance is the failure this module exists to prevent.
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0) {
    // 2^53 is ~9 million SOL; a real balance never reaches it, so this is a malformed answer, not a limit.
    throw new Error("Solana balance read returned no usable lamport value");
  }
  return String(value);
}

function formatSol(lamports) {
  const raw = typeof lamports === "bigint" ? lamports.toString() : String(lamports == null ? "" : lamports).trim();
  if (!/^\d+$/.test(raw)) throw new Error("lamports must be a whole non-negative integer");
  const value = BigInt(raw);
  const whole = value / LAMPORTS_PER_SOL;
  const fraction = String(value % LAMPORTS_PER_SOL).padStart(SOL_DECIMALS, "0").replace(/0+$/, "");
  return `${whole}${fraction ? `.${fraction}` : ""} SOL`;
}

module.exports = {
  DEFAULT_SOLANA_RPC_URL,
  LAMPORTS_PER_SOL,
  SOLANA_BALANCE_COMMITMENT,
  formatSol,
  readSolBalance,
};
