// swap — pure builders for a Uniswap V3 `exactInputSingle` ETH(WETH)->USDC swap on Base.
// No network here: execute-swap.mjs does the quote/sign/broadcast and imports these encoders.
// Keeping the calldata + slippage math pure makes the GATE-0 earn path unit-testable offline.

// Base mainnet canonical addresses (verified on-chain: code present at each).
export const WETH_BASE = "0x4200000000000000000000000000000000000006";
export const USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
export const SWAP_ROUTER_02_BASE = "0x2626664c2603336E57B271c5C0b26F421741e481";
export const QUOTER_V2_BASE = "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a";

// keccak4("exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))")
// SwapRouter02 has NO deadline field (unlike SwapRouter01).
export const EXACT_INPUT_SINGLE_SELECTOR = "0x04e45aaf";

const ADDR_RE = /^0x[0-9a-fA-F]{40}$/;

// Left-pad a hex value (no 0x) to a 32-byte (64 hex) ABI word.
function word(hexNo0x) {
  return hexNo0x.toLowerCase().padStart(64, "0");
}
function uintWord(v) {
  const n = BigInt(v);
  if (n < 0n) throw new Error("swap: negative uint");
  return word(n.toString(16));
}
function addrWord(a) {
  if (typeof a !== "string" || !ADDR_RE.test(a)) throw new Error(`swap: not an address: ${a}`);
  return word(a.replace(/^0x/, ""));
}

// Encode the exactInputSingle struct into router calldata.
// Param order: tokenIn, tokenOut, fee, recipient, amountIn, amountOutMinimum, sqrtPriceLimitX96.
export function buildExactInputSingleData({
  tokenIn,
  tokenOut,
  fee,
  recipient,
  amountIn,
  amountOutMinimum,
  sqrtPriceLimitX96 = 0n,
}) {
  const words = [
    addrWord(tokenIn),
    addrWord(tokenOut),
    uintWord(fee),
    addrWord(recipient),
    uintWord(amountIn),
    uintWord(amountOutMinimum),
    uintWord(sqrtPriceLimitX96),
  ];
  return EXACT_INPUT_SINGLE_SELECTOR + words.join("");
}

// Apply slippage tolerance (basis points) to a quoted output, floored to integer base units.
// minOut(548621, 50) = floor(548621 * 9950 / 10000) = 545877.
export function minOut(quotedOut, slippageBps) {
  const bps = Number(slippageBps);
  if (!Number.isInteger(bps) || bps < 0 || bps > 10000) {
    throw new Error(`swap: slippageBps must be 0..10000, got ${slippageBps}`);
  }
  const q = BigInt(quotedOut);
  return (q * BigInt(10000 - bps)) / 10000n;
}
