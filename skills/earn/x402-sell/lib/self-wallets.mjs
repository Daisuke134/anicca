// self-wallets.mjs — the ONE list of every EVM wallet the colony controls itself (INV-7: a
// payment FROM any of these is never counted as external revenue). Factored out of
// verify-inflow.mjs (SELF-STORE-1, 2026-07-18) so every judge (verify-inflow.mjs,
// x402-sell/store-review.mjs, and anything future) shares exactly one list instead of drifting
// copies. Must stay a superset of founder-loop/record-earn.mjs's SHARED list
// (__tests__/verify-inflow-wallets.test.mjs pins that agreement).
export const SELF_WALLETS = [
  "0x810f6d61f7606deee2657d3083e150a222bc29c5", // founder seller payTo
  "0xb9dd3b67921b354c656523d6851537988f31dd56",
  // 2026-07-18 harsh audit additions — every identity this machine controls, even "never pays" ones:
  "0xda4b6e34a25fa70a901f30161f1fd6a3ec68219b", // franklin1 Polymarket deposit proxy (.blockrun/wallets.json)
  "0x02bb6b2af70dbf2c367c1b69aca9858bf3525502", // claude-p telemetry signing wallet (no funds by design) // automaton (anicca-a3cdd4 spend wallet) / machine legacy default identity (resolve-identity fallback) — self-probes pay from this
  "0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21", // automaton, pre-rotation address
  "0x9b1ee988b1a2931abce467f0a8eaff6c70c93e83", // known-internal wallet
  "0x904b50d2e214da947d83d6a2d32c4e3ffc17eb74", // claude-p
  "0x3eccad24794ca298d25378e9902a251322ea8749", // franklin1 (per-instance EVM)
  "0xe7747fd899d8987821bb4cb3d6adf22565f87ce9", // franklin2 (per-instance EVM)
  // Funding routed THROUGH us, never earned. Traced 2026-07-12 (record-earn.mjs:40-49): source of
  // both the two largest "earn" rows ever recorded ($22.97 tx 0x3b3eeee6…, $7.98 tx 0x41ead2f3…)
  // and franklin1's $6.4778 — a plain EOA (no contract code) holding >$3.1M USDC on Base, far too
  // big and too centralized to be a $0.001 micro-payment buyer. Fail closed until identified.
  "0xf70da97812cb96acdf810712aa562db8dfa3dbef",
].map((a) => a.toLowerCase());

export const SELF_WALLET_SET = new Set(SELF_WALLETS);
