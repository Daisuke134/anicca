// gda-distribute.mjs — orchestration over gda-pool.mjs: turn a set of verified on-chain recipients
// into a Superfluid GDA distribution. The wallet-cohort of /income (recipients who gave a Base
// address) become equal-unit pool members; anicca then streams USDCx to the pool and every member
// receives their pro-rata share continuously, in ONE tx. Bank/email/mobile recipients use the other
// rails; GDA is the on-chain cohort only. Pure planning (no key here) — the caller signs via sendGdaCall.

import { buildCreatePoolCall, buildUpdateMemberUnitsCall, buildDistributeFlowCall, MAX_INT96 } from "./gda-pool.mjs";

// Pure: dedupe + lowercase-normalize recipient addresses, dropping blanks/dupes. one human = one unit
// is enforced upstream by the personhood gate (nullifier), so here we just ensure address uniqueness.
export function normalizeRecipients(addresses) {
  if (!Array.isArray(addresses)) throw new Error("gda-distribute: addresses[] required");
  const seen = new Set();
  const out = [];
  for (const a of addresses) {
    if (typeof a !== "string" || !/^0x[0-9a-fA-F]{40}$/.test(a)) continue;
    const k = a.toLowerCase();
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(a);
  }
  return out;
}

// Pure: a per-second int96 flow rate from a monthly USDCx budget (6dp token). Splitting across the
// month avoids a lump dump; the pool itself splits pro-rata by units. Rejects non-positive / overflow.
export function monthlyToFlowRate(monthlyUsdcx, secondsPerMonth = 2_592_000) {
  const m = Number(monthlyUsdcx);
  if (!Number.isFinite(m) || m <= 0) throw new Error("gda-distribute: monthlyUsdcx must be > 0");
  const perSec = BigInt(Math.floor((m * 1e6) / secondsPerMonth)); // wei of a 6dp token
  if (perSec <= 0n) throw new Error("gda-distribute: monthly budget too small for a >0 per-second rate");
  if (perSec > MAX_INT96) throw new Error("gda-distribute: flow rate exceeds int96 max");
  return perSec;
}

// Pure: build the ordered calldata plan to (optionally) create the pool, set each recipient to 1 unit,
// and open the stream. The caller sends them in order via sendGdaCall (own wallet). Returns
// { calls: [{kind, data, member?}], memberCount }. No member => no distribute (nothing to stream to).
export function planDistribution({ token, admin, pool, recipients, flowRatePerSec, createPool = false }) {
  const members = normalizeRecipients(recipients);
  const calls = [];
  if (createPool) {
    if (!token || !admin) throw new Error("gda-distribute: createPool needs token + admin");
    calls.push({ kind: "createPool", data: buildCreatePoolCall({ token, admin }) });
  }
  if (!pool && !createPool) throw new Error("gda-distribute: pool address required (or createPool:true)");
  if (members.length === 0) throw new Error("gda-distribute: no valid recipient addresses — refusing to stream to an empty pool");
  // NOTE: when createPool is true the pool address isn't known until the create tx returns; the caller
  // must thread the returned pool address into the member/distribute calls. For an existing pool, we
  // emit them inline here.
  if (pool) {
    for (const member of members) {
      calls.push({ kind: "updateMemberUnits", member, data: buildUpdateMemberUnitsCall({ pool, member, units: 1 }) });
    }
    if (typeof flowRatePerSec === "bigint" && flowRatePerSec > 0n) {
      calls.push({ kind: "distributeFlow", data: buildDistributeFlowCall({ token, from: admin, pool, flowRatePerSec }) });
    }
  }
  return { calls, memberCount: members.length };
}
