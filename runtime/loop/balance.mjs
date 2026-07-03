/**
 * balance.mjs — Effectful: fetch USDC balance from Base RPC with TTL cache.
 *
 * REQ-002: Balance read fails (RPC timeout) → caller keeps prior tier, no crash.
 * REQ-008: No macOS-only code.
 *
 * Special env var (tests only): ANICCA_BALANCE_OVERRIDE
 *   'fail' → throw (simulates RPC timeout)
 *   'NaN'  → return NaN (simulates malformed RPC response)
 *   any number string → return that number (bypasses RPC)
 */

import https from 'node:https';
import http from 'node:http';

// Base USDC contract address on Base mainnet
const USDC_CONTRACT = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const BASE_RPC_DEFAULT = 'https://mainnet.base.org';

// In-memory TTL cache: { address → { value: number, expireAt: number } }
const _cache = new Map();

/**
 * Fetch USDC balance (in human-readable USDC, 6 decimal places) for a wallet address.
 *
 * @param {string} address - wallet address (0x…)
 * @param {object} config - must include BALANCE_CACHE_TTL_S, optional BASE_RPC_URL
 * @returns {Promise<number>}
 * @throws {Error} on RPC failure (caller must handle and keep prior tier)
 */
export async function fetchUsdcBalance(address, config) {
  // Test override
  const override = process.env.ANICCA_BALANCE_OVERRIDE;
  if (override === 'fail') {
    throw new Error('ANICCA_BALANCE_OVERRIDE=fail: simulated RPC failure');
  }
  if (override !== undefined) {
    const parsed = parseFloat(override);
    return Number.isFinite(parsed) ? parsed : NaN;
  }

  // Validate the address before building any RPC call (no wallet → caller keeps prior tier).
  if (typeof address !== 'string' || !/^0x[0-9a-fA-F]{40}$/.test(address)) {
    throw new Error(`invalid wallet address: ${String(address)}`);
  }

  // TTL cache check
  const ttlS = Number(config.BALANCE_CACHE_TTL_S ?? 300);
  const now = Date.now();
  const cached = _cache.get(address);
  if (cached && now < cached.expireAt) {
    return cached.value;
  }

  // ERC-20 balanceOf(address) = keccak256("balanceOf(address)") = 0x70a08231
  const paddedAddr = address.toLowerCase().replace('0x', '').padStart(64, '0');
  const callData = '0x70a08231' + paddedAddr;

  // Robustness (loop must survive a single-endpoint DNS/RPC blip, else it falsely goes "broke"
  // and skips earning for the whole wake): try the configured URL first, then public fallbacks.
  const rpcUrls = [
    config.BASE_RPC_URL || process.env.BASE_RPC_URL || BASE_RPC_DEFAULT,
    'https://base-rpc.publicnode.com',
    'https://base.llamarpc.com',
    'https://mainnet.base.org',
  ].filter((u, i, a) => u && a.indexOf(u) === i);
  const payload = JSON.stringify({
    jsonrpc: '2.0',
    id: 1,
    method: 'eth_call',
    params: [{ to: USDC_CONTRACT, data: callData }, 'latest'],
  });

  let parsed, lastErr;
  for (const rpcUrl of rpcUrls) {
    try {
      parsed = JSON.parse(await rpcPost(rpcUrl, payload));
      if (parsed.error) throw new Error(`RPC error: ${JSON.stringify(parsed.error)}`);
      lastErr = null;
      break;
    } catch (e) {
      lastErr = e;
      parsed = null;
    }
  }
  if (!parsed) {
    throw lastErr || new Error('all Base RPC endpoints failed');
  }
  const hexBalance = parsed.result;
  if (!hexBalance || hexBalance === '0x') {
    return 0;
  }
  // USDC has 6 decimal places
  const balanceRaw = BigInt(hexBalance);
  const balance = Number(balanceRaw) / 1e6;

  _cache.set(address, { value: balance, expireAt: now + ttlS * 1000 });
  return balance;
}

/**
 * HTTP/HTTPS POST helper.
 */
function rpcPost(url, body) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const lib = parsed.protocol === 'https:' ? https : http;
    const options = {
      hostname: parsed.hostname,
      port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
      path: parsed.pathname + parsed.search,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
      },
      timeout: 8000,
    };
    const req = lib.request(options, (res) => {
      let data = '';
      res.on('data', chunk => { data += chunk; });
      res.on('end', () => resolve(data));
    });
    req.on('timeout', () => { req.destroy(); reject(new Error('RPC timeout')); });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}
