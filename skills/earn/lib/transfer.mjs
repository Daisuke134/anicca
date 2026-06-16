// transfer.mjs — pure builder for an ERC20 `transfer(address,uint256)` calldata on Base.
// No network here (execute-ubi.py signs/broadcasts). Keeping calldata + amount math pure makes
// the UBI send path unit-testable offline, exactly like swap.mjs does for the swap path.
//
// VERIFIED (ctx7 /websites/base encodeProlink example + local keccak, 2026-06-16):
//   selector keccak4("transfer(address,uint256)") = 0xa9059cbb
//   USDC (Base mainnet) = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913, decimals = 6.
export const TRANSFER_SELECTOR = "0xa9059cbb";
export const USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
export const USDC_DECIMALS = 6;

const ADDR_RE = /^0x[0-9a-fA-F]{40}$/;

function word(hexNo0x) {
  return hexNo0x.toLowerCase().padStart(64, "0");
}
function addrWord(a) {
  if (typeof a !== "string" || !ADDR_RE.test(a)) throw new Error(`transfer: not an address: ${a}`);
  return word(a.replace(/^0x/, ""));
}
function uintWord(v) {
  const n = BigInt(v);
  if (n < 0n) throw new Error("transfer: negative amount");
  return word(n.toString(16));
}

// Encode transfer(to, amountBaseUnits) calldata. amount is in 6-decimal USDC BASE UNITS (BigInt-able).
export function buildTransferData({ to, amountBaseUnits }) {
  return TRANSFER_SELECTOR + addrWord(to) + uintWord(amountBaseUnits);
}

// Convert a human USDC number (e.g. 0.45) to integer base units (450000n) with NO float drift.
export function toBaseUnits(usdc) {
  // round at 6dp first to kill fp noise, then scale — mirrors ledger.mjs round().
  const micros = Math.round(Number(usdc) * 1e6);
  if (!Number.isFinite(micros) || micros < 0) throw new Error(`transfer: bad usdc amount ${usdc}`);
  return BigInt(micros);
}

// share-of-net in basis points, floored to base units (integer math, like swap.mjs minOut).
export function shareBaseUnits(netUsdc, bps) {
  const b = Number(bps);
  if (!Number.isInteger(b) || b < 0 || b > 10000) throw new Error(`transfer: bps must be 0..10000, got ${bps}`);
  return (toBaseUnits(netUsdc) * BigInt(b)) / 10000n;
}

// Equal split of a pool (base units) across n recipients; floor each; remainder is dust (kept by sender).
export function splitPool(poolBaseUnits, n) {
  const pool = BigInt(poolBaseUnits);
  const count = BigInt(n);
  if (count <= 0n) return { per: 0n, dust: pool };
  const per = pool / count;
  return { per, dust: pool - per * count };
}
