/**
 * gates.mjs — 5-gate status (D5) for the earn/gig slot. PURE + observability only.
 *
 * The gates describe how far a gig has progressed; they NEVER produce an earning.
 * earn_usdc comes ONLY from record-earn's on-chain scan (external USDC inflow). This
 * separation is the anti-shortcut invariant: passing V1..V4 yields $0 — only a real
 * external on-chain settle (V5) counts. A weak model cannot fabricate income.
 *
 * V1 proposal  : we placed a real bid (bids.jsonl)
 * V2 listing   : N/A for gig (no listing rail) → null
 * V3 deliverable: we produced + recorded a deliverable (deliverables.jsonl)
 * V4 inbound   : a contract was accepted (open contracts > 0)
 * V5 settle    : record-earn verified external USDC inflow (ledger external earn > 0)
 */
export function gateStatus({ bids = 0, deliverables = 0, acceptedContracts = 0, externalEarnUsdc = 0 } = {}) {
  return {
    V1_proposal: bids > 0,
    V2_listing: null,                 // not applicable to gig
    V3_deliverable: deliverables > 0,
    V4_inbound: acceptedContracts > 0,
    V5_settle: externalEarnUsdc > 0,
  };
}

/** The ONLY source of a positive earn is a real external on-chain inflow. */
export function earnFromSettle({ externalEarnUsdc = 0 } = {}) {
  return externalEarnUsdc > 0 ? Number(externalEarnUsdc) : 0;
}
