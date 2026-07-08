// report-args.mjs — founderReportArgs(prevEarn, totalEarn, status) -> {result, earned_usdc, evidence}
// (REQ-LV-018). Pure: deterministically builds loop-report.sh's 3rd/4th/5th args from STATE.md's
// two numbers + STATUS string. Does NOT call loop-report.sh itself and does NOT touch
// record-earn.mjs (INV-H2 unchanged) — that wiring stays a Tier2/3 concern inside founder-loop.sh.

const FOUNDER_WALLET = "0x810f6d61f7606deee2657d3083e150a222bc29c5";

export function founderReportArgs(prevEarn, totalEarn, status) {
  const delta = totalEarn - prevEarn;
  if (delta > 0) {
    return {
      result: "success",
      earned_usdc: delta,
      evidence: `increase +${delta} USDC, wallet ${FOUNDER_WALLET}`,
    };
  }
  // No increment (or a defensive decrease, which should not happen) -> queue-empty, never a
  // negative earned_usdc.
  return {
    result: "queue-empty",
    earned_usdc: 0,
    evidence: `none: ${status}`,
  };
}
