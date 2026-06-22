// liquidity.mjs — PURE: produce a wake-prompt directive when the agent's liquid USDC has fallen below
// its OWN compute buffer, so it replenishes (close a profitable HL / withdraw idle yield) instead of
// stranding itself at ~$0 (the root of "zero balance, cannot act, begs for a seed"). The agent still
// DECIDES the action (HARD RULE #0: tool+steer, not a hardcoded auto-close); this only makes the buffer
// state explicit and urgent. Numbers are the instance's own (its liquid + its reserve) — never hardcoded.
//
// @param balanceUsdc  current liquid USDC
// @param reserveUsdc  the instance's compute buffer (COMPUTE_RESERVE_USDC; the deploy floor)
// @param hasHlPosition whether the agent holds an HL position it could close
// @returns directive string ("" when liquid is healthy)
export function liquidityDirective(balanceUsdc, reserveUsdc, hasHlPosition) {
  const liquid = Number(balanceUsdc);
  const reserve = Number(reserveUsdc);
  if (!Number.isFinite(liquid) || !Number.isFinite(reserve)) return "";
  if (liquid >= reserve) return "";
  const replenish = hasHlPosition
    ? `CLOSE a profitable HL position to realise PnL into liquid ({action:"close",coin}), or withdraw idle yield.`
    : `Withdraw idle yield to top up the buffer.`;
  return `⚠️ LIQUID BELOW COMPUTE BUFFER: $${liquid.toFixed(4)} < $${reserve} needed to fund inference + new earns. ` +
    `REPLENISH FIRST this wake — do NOT deploy more into positions. ${replenish}`;
}
