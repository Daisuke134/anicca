// REQ-303/REQ-304: computeSpawnGate's exact two-pass sequencing relative to the Skip API bridge
// (resolves FIND-1803) — the FIRST pass's ready:false triggers the bridge attempt (never itself a
// REQ-305 failure); a SECOND pass runs after the bridge completes, and ONLY its ready:false is the
// actual deploy failure. balanceAkt is always a FRESH queryBalanceAkt() result each pass, never
// cached/hand-assembled (resolves FIND-1802). Reuses the existing, unmodified computeSpawnGate.
import { computeSpawnGate } from "../../spawn-child/lib/akt-cost-gate.js";

export async function evaluateAkashFundingGate({ queryBalanceAkt, costAkt, bufferAkt, attemptBridge }) {
  const firstBalanceAkt = await queryBalanceAkt();
  const firstPass = computeSpawnGate({ balanceAkt: firstBalanceAkt, costAkt, bufferAkt });
  if (firstPass.ready) {
    return { ...firstPass, bridgeAttempted: false, firstPassReady: true };
  }

  await attemptBridge();
  const secondBalanceAkt = await queryBalanceAkt();
  const secondPass = computeSpawnGate({ balanceAkt: secondBalanceAkt, costAkt, bufferAkt });
  return { ...secondPass, bridgeAttempted: true, firstPassReady: false };
}
