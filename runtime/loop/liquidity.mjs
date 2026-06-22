// liquidity.mjs — PURE: produce a wake-prompt directive when the agent's liquid USDC has fallen below
// its OWN compute buffer, so it replenishes (close a profitable HL / withdraw idle yield) instead of
// stranding itself at ~$0 (the root of "zero balance, cannot act, begs for a seed"). The agent still
// DECIDES the action (HARD RULE #0: tool+steer, not a hardcoded auto-close); this only makes the buffer
// state explicit and urgent. Numbers are the instance's own (its liquid + its reserve) — never hardcoded.
//
// It offers BOTH replenish paths (close HL / withdraw yield) and lets the agent pick whichever it holds —
// we do NOT try to infer "has an HL position" from a brittle string (the prod positionsSummary only ever
// lists yield, and a regex on "long"/"short" false-positives on words like "longshot").
//
// @param balanceUsdc  current liquid USDC
// @param reserveUsdc  the instance's compute buffer (COMPUTE_RESERVE_USDC; the deploy floor)
// @returns directive string ("" when liquid is healthy: at/above the buffer)
export function liquidityDirective(balanceUsdc, reserveUsdc) {
  const liquid = Number(balanceUsdc);
  const reserve = Number(reserveUsdc);
  if (!Number.isFinite(liquid) || !Number.isFinite(reserve)) return "";
  if (reserve <= 0) return "";          // no buffer configured → nothing to defend
  if (liquid >= reserve) return "";     // healthy
  return `⚠️ LIQUID BELOW COMPUTE BUFFER: $${liquid.toFixed(4)} < $${reserve} needed to fund inference + new earns. ` +
    `REPLENISH FIRST this wake — do NOT deploy more into positions. ` +
    `CLOSE a profitable HL position to realise PnL into liquid ({action:"close",coin}), or withdraw idle yield — whichever you hold.`;
}
