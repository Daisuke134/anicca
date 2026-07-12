/**
 * net-worth.mjs — an instance's TOTAL assets, across every chain and token it holds.
 *
 * Why this exists (2026-07-12): every balance reader in the codebase saw exactly ONE token on ONE
 * chain, so an instance could not see most of its own money:
 *   - runtime/loop/balance.mjs: Base USDC (EVM) or Solana USDC — nothing else.
 *   - @blockrun/llm's getBalance(): USDC only; the package has no code that reads a SOL lamport
 *     balance at all.
 * Consequences observed live: claude-p held $14.15 in its Polymarket deposit wallet and its loop
 * reported ~$0; Franklin was sent $18.88 of SOL and its loop kept saying "my USDC is too small to
 * trade" because SOL was invisible to it.
 *
 * This module reads every (chain, address, token) pair it is given and returns one number plus the
 * breakdown. Direct RPC only — no portfolio API, no API key, no new dependency. The read patterns
 * are the ones already proven in skills/self/colony-status.sh.
 *
 * Native tokens (SOL, POL) are priced via a spot endpoint; if pricing is unavailable the native leg
 * contributes 0 and is flagged `priced: false` rather than guessed — an unpriceable asset must never
 * silently inflate net worth (a wrong high number would let a capital gate open on money that is not
 * spendable).
 *
 * Pure-ish: all I/O goes through an injectable `fetchImpl`, so the whole thing is unit-testable
 * without a network (see __tests__/net-worth.test.mjs).
 */

// ---------------------------------------------------------------------------------------------
// Chain + token constants (machine facts, not judgment — same values colony-status.sh already uses)
// ---------------------------------------------------------------------------------------------
export const RPC = {
  base: 'https://base-rpc.publicnode.com',
  polygon: 'https://polygon-bor-rpc.publicnode.com',
  solana: 'https://api.mainnet-beta.solana.com',
};

/** ERC-20 stablecoins worth counting, per EVM chain. All are 6-decimal USD stablecoins. */
export const EVM_TOKENS = {
  base: [
    { symbol: 'USDC', address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', decimals: 6 },
  ],
  polygon: [
    { symbol: 'USDC.e', address: '0x2791bca1f2de4661ed88a30c99a7a9449aa84174', decimals: 6 },
    { symbol: 'USDC', address: '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359', decimals: 6 },
    { symbol: 'pUSD', address: '0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB', decimals: 6 },
  ],
};

export const SOLANA_USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';

/** Native gas assets. Counted at spot, but only when a price is actually available. */
export const NATIVE = {
  base: { symbol: 'ETH', decimals: 18, priceId: 'ETH-USD' },
  polygon: { symbol: 'POL', decimals: 18, priceId: 'POL-USD' },
  solana: { symbol: 'SOL', decimals: 9, priceId: 'SOL-USD' },
};

const SPOT_URL = (id) => `https://api.coinbase.com/v2/prices/${id}/spot`;

/**
 * Hyperliquid is an off-chain-margin venue: funds deposited there do NOT show up in any wallet's
 * ERC-20 balance, so every chain-only reader misses them entirely. Discovered live 2026-07-12: the
 * loop had autonomously self-funded HL and was carrying a real ETH position worth $7.72 that no
 * balance reader in the codebase could see. accountValue already includes unrealized P&L.
 */
export const HL_INFO_URL = 'https://api.hyperliquid.xyz/info';

// ---------------------------------------------------------------------------------------------
// Low-level reads
// ---------------------------------------------------------------------------------------------
const BALANCE_OF = '0x70a08231';

async function jsonRpc(url, method, params, fetchImpl) {
  const res = await fetchImpl(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }),
  });
  const body = await res.json();
  if (body.error) throw new Error(`${method}: ${JSON.stringify(body.error)}`);
  return body.result;
}

/** Parse a hex quantity into a human-readable number. '0x' / '' / null → 0 (an unfunded ERC-20 read). */
export function hexToUnits(hex, decimals) {
  if (!hex || hex === '0x') return 0;
  return Number(BigInt(hex)) / 10 ** decimals;
}

/** Left-pad an EVM address into the 32-byte word balanceOf(address) expects. */
export function balanceOfCalldata(address) {
  const a = String(address).toLowerCase().replace(/^0x/, '');
  if (!/^[0-9a-f]{40}$/.test(a)) throw new Error(`not an EVM address: ${address}`);
  return BALANCE_OF + '0'.repeat(24) + a;
}

export async function evmErc20Balance(chain, token, address, fetchImpl, rpcUrl) {
  const hex = await jsonRpc(
    rpcUrl || RPC[chain],
    'eth_call',
    [{ to: token.address, data: balanceOfCalldata(address) }, 'latest'],
    fetchImpl,
  );
  return hexToUnits(hex, token.decimals);
}

export async function evmNativeBalance(chain, address, fetchImpl, rpcUrl) {
  const hex = await jsonRpc(rpcUrl || RPC[chain], 'eth_getBalance', [address, 'latest'], fetchImpl);
  return hexToUnits(hex, NATIVE[chain].decimals);
}

export async function solanaNativeBalance(address, fetchImpl, rpcUrl) {
  const r = await jsonRpc(rpcUrl || RPC.solana, 'getBalance', [address], fetchImpl);
  return (r?.value ?? 0) / 10 ** NATIVE.solana.decimals;
}

export async function solanaUsdcBalance(address, fetchImpl, rpcUrl) {
  const r = await jsonRpc(
    rpcUrl || RPC.solana,
    'getTokenAccountsByOwner',
    [address, { mint: SOLANA_USDC_MINT }, { encoding: 'jsonParsed' }],
    fetchImpl,
  );
  const accounts = r?.value ?? [];
  return accounts.reduce(
    (sum, a) => sum + Number(a?.account?.data?.parsed?.info?.tokenAmount?.uiAmount ?? 0),
    0,
  );
}

/**
 * Hyperliquid account value (margin + unrealized P&L) for an EVM address, in USD.
 * Returns 0 for an address that has never deposited (HL answers with a zeroed marginSummary).
 */
export async function hyperliquidAccountValue(address, fetchImpl, infoUrl) {
  const res = await fetchImpl(infoUrl || HL_INFO_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type: 'clearinghouseState', user: address }),
  });
  const body = await res.json();
  const v = Number(body?.marginSummary?.accountValue);
  return Number.isFinite(v) ? v : 0;
}

/** Spot price in USD, or null when unavailable. Never throws — an unpriceable asset is skipped, not guessed. */
export async function spotPrice(priceId, fetchImpl) {
  try {
    const res = await fetchImpl(SPOT_URL(priceId), { method: 'GET' });
    const body = await res.json();
    const amt = Number(body?.data?.amount);
    return Number.isFinite(amt) && amt > 0 ? amt : null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------------------------
// Aggregation
// ---------------------------------------------------------------------------------------------
/**
 * @param {Array<{chain:'base'|'polygon'|'solana', address:string, label?:string}>} wallets
 * @param {{fetchImpl?:Function, includeNative?:boolean, rpc?:object}} [opts]
 * @returns {Promise<{total_usd:number, holdings:Array, errors:Array}>}
 *
 * Every leg is read independently: one failing RPC or one unpriceable native asset degrades that
 * single leg to an `errors` entry and contributes 0 — it never throws away the legs that DID read,
 * and it never invents a number for the leg that didn't. Callers that gate real money on this must
 * treat a non-empty `errors` as "this total is a LOWER BOUND", never as "this is everything".
 */
export async function fetchNetWorth(wallets, opts = {}) {
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  const includeNative = opts.includeNative !== false;
  const rpc = { ...RPC, ...(opts.rpc || {}) };
  const holdings = [];
  const errors = [];

  const priceCache = new Map();
  const priceOf = async (priceId) => {
    if (!priceCache.has(priceId)) priceCache.set(priceId, await spotPrice(priceId, fetchImpl));
    return priceCache.get(priceId);
  };

  for (const w of wallets) {
    const label = w.label || w.address;

    if (w.chain === 'hyperliquid') {
      try {
        const v = await hyperliquidAccountValue(w.address, fetchImpl, opts.hlInfoUrl);
        if (v > 0) holdings.push({ label, chain: 'hyperliquid', symbol: 'USD', amount: v, usd: v, priced: true });
      } catch (e) {
        errors.push({ label, chain: 'hyperliquid', error: String(e.message || e) });
      }
      continue;
    }

    if (w.chain === 'solana') {
      try {
        const usdc = await solanaUsdcBalance(w.address, fetchImpl, rpc.solana);
        if (usdc > 0) holdings.push({ label, chain: 'solana', symbol: 'USDC', amount: usdc, usd: usdc, priced: true });
      } catch (e) {
        errors.push({ label, chain: 'solana', symbol: 'USDC', error: String(e.message || e) });
      }
      if (includeNative) {
        try {
          const sol = await solanaNativeBalance(w.address, fetchImpl, rpc.solana);
          if (sol > 0) {
            const px = await priceOf(NATIVE.solana.priceId);
            holdings.push({
              label, chain: 'solana', symbol: 'SOL', amount: sol,
              usd: px ? sol * px : 0, priced: px != null,
            });
            if (px == null) errors.push({ label, chain: 'solana', symbol: 'SOL', error: 'no spot price — counted as $0' });
          }
        } catch (e) {
          errors.push({ label, chain: 'solana', symbol: 'SOL', error: String(e.message || e) });
        }
      }
      continue;
    }

    const tokens = EVM_TOKENS[w.chain];
    if (!tokens) {
      errors.push({ label, chain: w.chain, error: `unknown chain: ${w.chain}` });
      continue;
    }
    for (const t of tokens) {
      try {
        const amt = await evmErc20Balance(w.chain, t, w.address, fetchImpl, rpc[w.chain]);
        if (amt > 0) holdings.push({ label, chain: w.chain, symbol: t.symbol, amount: amt, usd: amt, priced: true });
      } catch (e) {
        errors.push({ label, chain: w.chain, symbol: t.symbol, error: String(e.message || e) });
      }
    }
    if (includeNative) {
      try {
        const amt = await evmNativeBalance(w.chain, w.address, fetchImpl, rpc[w.chain]);
        if (amt > 0) {
          const nat = NATIVE[w.chain];
          const px = await priceOf(nat.priceId);
          holdings.push({
            label, chain: w.chain, symbol: nat.symbol, amount: amt,
            usd: px ? amt * px : 0, priced: px != null,
          });
          if (px == null) errors.push({ label, chain: w.chain, symbol: nat.symbol, error: 'no spot price — counted as $0' });
        }
      } catch (e) {
        errors.push({ label, chain: w.chain, symbol: NATIVE[w.chain].symbol, error: String(e.message || e) });
      }
    }
  }

  const total_usd = holdings.reduce((s, h) => s + h.usd, 0);
  return { total_usd: Math.round(total_usd * 1e6) / 1e6, holdings, errors };
}
