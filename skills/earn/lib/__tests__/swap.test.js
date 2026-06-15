// node:test — swap: pure builders for a Uniswap V3 exactInputSingle ETH->USDC swap on Base.
// Network calls live elsewhere (execute-swap.mjs); these are deterministic encoders/math
// so the GATE-0 earn path is unit-proven before any on-chain broadcast.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  EXACT_INPUT_SINGLE_SELECTOR,
  buildExactInputSingleData,
  minOut,
  WETH_BASE,
  USDC_BASE,
} from "../swap.mjs";

const RECIPIENT = "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21";

test("selector is the keccak4 of exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))", () => {
  // Uniswap SwapRouter02 exactInputSingle selector = 0x04e45aaf
  assert.equal(EXACT_INPUT_SINGLE_SELECTOR, "0x04e45aaf");
});

test("buildExactInputSingleData starts with the selector and is 4 + 7*32 bytes", () => {
  const data = buildExactInputSingleData({
    tokenIn: WETH_BASE,
    tokenOut: USDC_BASE,
    fee: 500,
    recipient: RECIPIENT,
    amountIn: 300000000000000n, // 0.0003 ETH
    amountOutMinimum: 500000n, // 0.5 USDC
  });
  assert.ok(data.startsWith(EXACT_INPUT_SINGLE_SELECTOR));
  // 0x + 8 selector hex + 7 params * 64 hex each
  assert.equal(data.length, 2 + 8 + 7 * 64);
});

test("buildExactInputSingleData packs amountIn and amountOutMinimum verbatim (no rounding)", () => {
  const data = buildExactInputSingleData({
    tokenIn: WETH_BASE,
    tokenOut: USDC_BASE,
    fee: 500,
    recipient: RECIPIENT,
    amountIn: 300000000000000n,
    amountOutMinimum: 548000n,
  });
  const body = data.slice(2 + 8); // strip 0x + selector
  const words = body.match(/.{64}/g);
  // order: tokenIn, tokenOut, fee, recipient, amountIn, amountOutMinimum, sqrtPriceLimitX96
  assert.equal(BigInt("0x" + words[4]), 300000000000000n);
  assert.equal(BigInt("0x" + words[5]), 548000n);
  assert.equal(BigInt("0x" + words[6]), 0n); // sqrtPriceLimitX96 = 0 (no limit)
});

test("buildExactInputSingleData right-pads token + recipient addresses into 32-byte words", () => {
  const data = buildExactInputSingleData({
    tokenIn: WETH_BASE,
    tokenOut: USDC_BASE,
    fee: 3000,
    recipient: RECIPIENT,
    amountIn: 1n,
    amountOutMinimum: 0n,
  });
  const words = data.slice(2 + 8).match(/.{64}/g);
  assert.equal("0x" + words[0].slice(24), WETH_BASE.toLowerCase());
  assert.equal("0x" + words[1].slice(24), USDC_BASE.toLowerCase());
  assert.equal(BigInt("0x" + words[2]), 3000n); // fee
  assert.equal("0x" + words[3].slice(24), RECIPIENT.toLowerCase());
});

test("buildExactInputSingleData rejects a non-address recipient", () => {
  assert.throws(
    () =>
      buildExactInputSingleData({
        tokenIn: WETH_BASE,
        tokenOut: USDC_BASE,
        fee: 500,
        recipient: "not-an-address",
        amountIn: 1n,
        amountOutMinimum: 0n,
      }),
    /address/,
  );
});

test("minOut applies slippage in bps and floors to integer base units", () => {
  // quoted 0.548621 USDC = 548621 base units; 50 bps (0.5%) slippage
  assert.equal(minOut(548621n, 50), 545877n); // floor(548621 * 9950 / 10000)
});

test("minOut with 0 slippage returns the quote unchanged", () => {
  assert.equal(minOut(1000000n, 0), 1000000n);
});

test("minOut rejects negative or >10000 bps", () => {
  assert.throws(() => minOut(1n, -1), /slippageBps/);
  assert.throws(() => minOut(1n, 10001), /slippageBps/);
});
