// Sprint-6 T6 — live Solana reader for enrichOnChain. Same fail-closed contract as
// chain-reader.js's makeBaseReader: if unconfigured or a read fails, the accessor THROWS so
// enrich flags that figure `unverified` (never a trusted/fake number). PUBLIC data only.
//
// Reuses the SAME accessor names as makeBaseReader (ethUsdPrice/usdcBalanceAtomic/
// nativeBalanceWei/externalInflowsUsd) so enrich.js's dispatch (Sprint-6 S6.5) stays
// chain-agnostic — the naming is EVM-flavored but the shape is what enrich.js calls generically.
const { Connection, PublicKey } = require("@solana/web3.js");
const { TOKEN_PROGRAM_ID } = require("@solana/spl-token");

const USDC_MINT_SOLANA = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"; // USDC on Solana mainnet
const LOOKBACK_SIGNATURES = 200; // recent-signatures cap per address (devnet/mainnet parity)

async function defaultFetchPrice() {
  const res = await fetch("https://api.coinbase.com/v2/prices/SOL-USD/spot");
  const j = await res.json();
  const p = Number(j?.data?.amount);
  if (!Number.isFinite(p)) throw new Error("no SOL price");
  return p;
}

async function makeSolanaReader(ids = [], opts = {}) {
  const rpc = opts.rpcUrl || process.env.SOLANA_RPC_URL || "https://api.devnet.solana.com";
  const conn = opts.conn || new Connection(rpc);
  const fetchPrice = opts.fetchPrice || defaultFetchPrice;
  const cache = { native: {}, usdc: {}, inflows: {} };
  let price = null;

  if (ids.length) {
    try { price = await fetchPrice(); } catch { /* price stays null -> ethUsdPrice throws */ }
    for (const id of ids) {
      try { cache.native[id] = await conn.getBalance(new PublicKey(id)); } catch { /* leave undefined */ }
      try {
        const accts = await conn.getParsedTokenAccountsByOwner(new PublicKey(id), { programId: TOKEN_PROGRAM_ID });
        const match = (accts.value || []).find((a) => a.account?.data?.parsed?.info?.mint === USDC_MINT_SOLANA);
        cache.usdc[id] = match ? Number(match.account.data.parsed.info.tokenAmount.amount) : 0;
      } catch { /* leave undefined -> usdcBalanceAtomic throws */ }
      try {
        const sigs = await conn.getSignaturesForAddress(new PublicKey(id), { limit: LOOKBACK_SIGNATURES });
        const txs = await Promise.all(sigs.map((s) => conn.getParsedTransaction(s.signature, { maxSupportedTransactionVersion: 0 }).catch(() => null)));
        cache.inflows[id] = txs.filter(Boolean).map((tx) => transferToTarget(tx, id)).filter(Boolean);
      } catch { /* leave undefined -> externalInflowsUsd throws */ }
    }
  }

  return {
    ethUsdPrice: () => { if (price == null) throw new Error("no SOL price"); return price; },
    usdcBalanceAtomic: (a) => { const v = cache.usdc[a]; if (v == null) throw new Error("no usdc balance"); return v; },
    nativeBalanceWei: (a) => { const v = cache.native[a]; if (v == null) throw new Error("no native balance"); return v; },
    externalInflowsUsd: (a, sinceTs, exSet) => {
      const list = cache.inflows[a];
      if (list == null) throw new Error("no inflow data");
      return list
        .filter((x) => x.blockTime >= sinceTs && !(x.from && exSet.has(x.from)))
        .reduce((s, x) => s + (x.lamports / 1e9) * (price ?? 0), 0);
    },
  };
}

// A real transfer's "sender" = the account (besides the target) with the largest balance
// decrease in the same transaction. Returns null if the target's balance didn't increase.
function transferToTarget(tx, targetAddr) {
  const keys = (tx.transaction?.message?.accountKeys || []).map((k) => (k.pubkey ? k.pubkey.toBase58() : String(k)));
  const pre = tx.meta?.preBalances || [];
  const post = tx.meta?.postBalances || [];
  const targetIdx = keys.indexOf(targetAddr);
  if (targetIdx < 0) return null;
  const delta = (post[targetIdx] ?? 0) - (pre[targetIdx] ?? 0);
  if (delta <= 0) return null;
  let senderIdx = -1, maxDecrease = 0;
  keys.forEach((_, i) => {
    if (i === targetIdx) return;
    const dec = (pre[i] ?? 0) - (post[i] ?? 0);
    if (dec > maxDecrease) { maxDecrease = dec; senderIdx = i; }
  });
  return { lamports: delta, from: senderIdx >= 0 ? keys[senderIdx] : null, blockTime: tx.blockTime ?? 0 };
}

module.exports = { makeSolanaReader, USDC_MINT_SOLANA };
