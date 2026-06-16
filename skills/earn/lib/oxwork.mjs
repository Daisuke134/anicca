// 0xwork external-revenue helpers. Pure transport (fetch injectable); no signing here.
// GATE-0 = EXTERNAL revenue: a third-party poster funds a USDC bounty into 0xwork escrow
// (taskPool). On approval the escrow releases USDC FROM the poster's funds INTO Anicca's wallet —
// the payout tx has from = taskPool, not Anicca. A swap has no such taskPool->wallet transfer.
const API = process.env.OXWORK_API || "https://api.0xwork.org";
const USDC = (process.env.USDC_ADDRESS || "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913").toLowerCase();
const TASKPOOL = (process.env.OXWORK_TASKPOOL || "0xF404aFdbA46e05Af7B395FB45c43e66dB549C6D2").toLowerCase();
// Anicca's capability set. NOTE: live supply is volatile (today both open tasks are "Social").
// We match case-insensitively AND default-allow when OXWORK_ANY_CATEGORY=1 so a wake is reachable
// even when only Social tasks exist — the agent decides per-task if it can deliver verifiable proof.
const DEFAULT_CAPS = (process.env.OXWORK_CAPS || "Writing,Research,Code,Data,Social,Creative").split(",");

export async function pickTask(caps = DEFAULT_CAPS, opts = {}) {
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  const res = await fetchImpl(`${API}/tasks?status=open`);
  if (!res.ok) throw new Error(`oxwork: tasks ${res.status}`);
  const { tasks = [] } = await res.json();
  const capSet = new Set(caps.map((c) => c.trim().toLowerCase()));
  const anyCat = process.env.OXWORK_ANY_CATEGORY === "1" || capSet.size === 0;
  return (
    tasks
      .filter((t) => String(t.status).toLowerCase() === "open") // case-insensitive status ("Open")
      .filter((t) => t.stake_amount === null || Number(t.stake_amount) === 0) // no worker stake (wallet ~0)
      .filter((t) => Number(t.bounty_amount ?? t.bounty) > 0)
      .find((t) => anyCat || capSet.has(String(t.category).toLowerCase())) || null
  );
}

// GATE-0 proof: the payout tx carries an ERC-20 USDC Transfer (topic0=Transfer) with
// from == taskPool (external) and to == our wallet. A swap has NO such log => false.
export async function isExternalPayout(receipt, wallet) {
  if (!receipt || !Array.isArray(receipt.logs)) return false;
  const TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
  const padW = "0x" + wallet.toLowerCase().replace(/^0x/, "").padStart(64, "0");
  const padPool = "0x" + TASKPOOL.replace(/^0x/, "").padStart(64, "0");
  return receipt.logs.some(
    (l) =>
      l.address &&
      l.address.toLowerCase() === USDC &&
      Array.isArray(l.topics) &&
      l.topics[0] === TRANSFER &&
      l.topics[1] &&
      l.topics[1].toLowerCase() === padPool && // from = 0xwork escrow (external)
      l.topics[2] &&
      l.topics[2].toLowerCase() === padW // to   = our wallet
  );
}
