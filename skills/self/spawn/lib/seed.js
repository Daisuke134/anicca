// Pure seed-plan + ledger finalization for self/spawn auto-seed (spawn-auto-seed REQ-3/REQ-5).
// No I/O here — the on-chain transfer lives in scripts/seed-child.py; this only validates + shapes.

const USDC_DECIMALS = 6;

function buildSeedPlan({ seedUsdc, parentWallet, childWallet, parentBalanceUsdc } = {}) {
  if (typeof seedUsdc !== "number" || !Number.isFinite(seedUsdc) || seedUsdc <= 0) {
    throw new Error(`seed amount invalid: ${seedUsdc}`);
  }
  if (!parentWallet || !childWallet) {
    throw new Error("parent/child wallet required");
  }
  if (String(childWallet).toLowerCase() === String(parentWallet).toLowerCase()) {
    throw new Error("child wallet equals parent wallet — refusing self-seed");
  }
  if (typeof parentBalanceUsdc !== "number" || !Number.isFinite(parentBalanceUsdc) || parentBalanceUsdc < seedUsdc) {
    throw new Error(`parent balance ${parentBalanceUsdc} < seed ${seedUsdc} — cannot seed`);
  }
  const amountUnits = Math.round(seedUsdc * 10 ** USDC_DECIMALS);
  return { amountUnits };
}

function finalizeSeedRow(row, { txHash } = {}) {
  if (typeof txHash !== "string" || !/^0x[0-9a-fA-F]+$/.test(txHash)) {
    throw new Error(`seed tx hash invalid: ${txHash}`);
  }
  return { ...row, seed_tx: txHash, seed_status: "sent" };
}

module.exports = { buildSeedPlan, finalizeSeedRow, USDC_DECIMALS };
