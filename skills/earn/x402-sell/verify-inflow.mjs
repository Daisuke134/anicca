// verify-inflow.mjs — on-chain source of truth for "did an EXTERNAL buyer actually pay us?"
// Scans Base USDC Transfer logs to X402_PAYTO and splits them into self-pay (our own wallets,
// INV-7: never counted as revenue) vs external (real earnings). No API key: public Base RPC.
//   node verify-inflow.mjs [hoursBack=48]
const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
const PAY_TO = (process.env.X402_PAYTO || "0x810f6d61f7606deee2657d3083e150a222bc29c5").toLowerCase();
// every wallet we control on any instance — a payment from any of these is NOT revenue (INV-7).
// Must stay a superset of founder-loop/record-earn.mjs's SHARED list: an address any judge in the
// colony calls internal has to be internal in EVERY judge, or we overstate what we earned.
// (__tests__/verify-inflow-wallets.test.mjs pins that agreement.)
const OUR_WALLETS = new Set([
  PAY_TO,
  "0xb9dd3b67921b354c656523d6851537988f31dd56", // automaton (anicca-a3cdd4 spend wallet)
  "0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21", // automaton, pre-rotation address
  "0x9b1ee988b1a2931abce467f0a8eaff6c70c93e83", // known-internal wallet
  "0x904b50d2e214da947d83d6a2d32c4e3ffc17eb74", // claude-p
  "0x810f6d61f7606deee2657d3083e150a222bc29c5", // founder seller payTo
  "0x3eccad24794ca298d25378e9902a251322ea8749", // franklin (per-instance EVM)
  "0xe7747fd899d8987821bb4cb3d6adf22565f87ce9", // franklin2 (per-instance EVM)
  "0xb9dd3b67921b354c656523d6851537988f31dd56", // machine legacy/default identity (resolve-identity fallback) — self-probes pay from this; measured 2026-07-18, 9 franklin2 sales rows misread as external until added
  // Funding routed THROUGH us, never earned. Traced 2026-07-12 (record-earn.mjs:40-49): it is the
  // source of both largest "earn" rows ever recorded ($22.97 tx 0x3b3eeee6…, $7.98 tx 0x41ead2f3…)
  // and of franklin1's $6.4778 — a plain EOA (no contract code) holding >$3.1M USDC on Base, far too
  // big and too centralized to be a $0.001 micro-payment buyer. Fail closed until identified.
  "0xf70da97812cb96acdf810712aa562db8dfa3dbef",
].map((a) => a.toLowerCase()));
const RPC = process.env.X402_RPC_URL || "https://mainnet.base.org";
const HOURS = Number(process.argv[2] || 48);
const BLOCKS_PER_HOUR = 1800; // Base: 2s block time

async function rpc(method, params) {
  const r = await fetch(RPC, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
    signal: AbortSignal.timeout(30_000),
  });
  const j = await r.json();
  if (j.error) throw new Error(`${method}: ${JSON.stringify(j.error)}`);
  return j.result;
}

const latest = parseInt(await rpc("eth_blockNumber", []), 16);
const fromBlock = latest - HOURS * BLOCKS_PER_HOUR;
const toTopic = "0x" + PAY_TO.slice(2).padStart(64, "0");
const CHUNK = 10_000; // public RPC getLogs range cap
const logs = [];
for (let start = fromBlock; start <= latest; start += CHUNK) {
  const end = Math.min(start + CHUNK - 1, latest);
  logs.push(...await rpc("eth_getLogs", [{
    address: USDC, fromBlock: "0x" + start.toString(16), toBlock: "0x" + end.toString(16),
    topics: [TRANSFER_TOPIC, null, toTopic],
  }]));
}

const rows = logs.map((l) => ({
  tx: l.transactionHash,
  block: parseInt(l.blockNumber, 16),
  from: "0x" + l.topics[1].slice(26),
  usdc: Number(BigInt(l.data)) / 1e6,
})).map((r) => ({ ...r, external: !OUR_WALLETS.has(r.from.toLowerCase()) }));

const ext = rows.filter((r) => r.external);
const sum = (a) => Math.round(a.reduce((s, r) => s + r.usdc, 0) * 1e6) / 1e6;
console.log(JSON.stringify({
  payTo: PAY_TO, hoursBack: HOURS, scannedBlocks: [fromBlock, latest],
  inflows: rows.length, selfPay: rows.length - ext.length, selfPayUsdc: sum(rows.filter((r) => !r.external)),
  EXTERNAL: ext.length, externalUsdc: sum(ext),
}, null, 2));
for (const r of ext) console.log("EXTERNAL-TX:", JSON.stringify(r));
