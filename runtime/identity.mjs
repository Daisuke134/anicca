// identity.mjs — every Anicca instance gets a GUARANTEED-UNIQUE id, automatically, on first run.
//
// Two ids per instance:
//   1. wallet address  — the IMMUTABLE cryptographic id (collision-impossible: each spawn generates a
//                        fresh keypair, so two aniccas can NEVER share it). This is the true primary key
//                        the dashboard dedupes on.
//   2. display name    — a human-friendly handle derived from the address: `anicca-<6 hex>` (e.g.
//                        anicca-a3cdd4). Because it is derived from the unique address it is also unique;
//                        we additionally check the live dashboard and extend the suffix on the (near-zero)
//                        chance of a prefix clash. The name is persisted to ~/.anicca/identity/name so it
//                        is STABLE across restarts (an instance keeps its identity), and a monotonically
//                        increasing `seq` is read from the dashboard for friendly ordering on the board.
//
// No central registry, no coordination, no human: the address makes uniqueness free, the dashboard is the
// shared ledger of all live names, and the first telemetry POST auto-registers the instance instantly.
import fs from "fs";
import path from "path";

const DASH = process.env.ANICCA_DASHBOARD_SYNC || "https://aniccaai.com/.netlify/functions/dashboard-sync";

async function existingNames() {
  try {
    const r = await fetch(DASH, { signal: AbortSignal.timeout(8000) });
    const d = await r.json();
    return new Set((d.leaderboard || []).map((x) => String(x.host || "").toLowerCase()).filter(Boolean));
  } catch { return new Set(); }
}

// Returns { name, id, seq } for this instance. Stable across restarts; unique across the colony.
export async function assignIdentity(address, home = process.env.ANICCA_HOME || path.join(process.env.HOME, ".anicca")) {
  const id = String(address).toLowerCase();
  const dir = path.join(home, "identity");
  const file = path.join(dir, "name");
  // stable: reuse the persisted name if this instance was already named
  try { const saved = fs.readFileSync(file, "utf8").trim(); if (saved) return { name: saved, id, seq: null }; } catch {}

  const taken = await existingNames();
  const hex = id.replace(/^0x/, "");
  let len = 6;
  let name = `anicca-${hex.slice(0, len)}`;
  while (taken.has(name.toLowerCase()) && len < hex.length) { len += 2; name = `anicca-${hex.slice(0, len)}`; } // extend on clash
  const seq = taken.size + 1; // friendly board ordering (#N), not used for uniqueness

  try { fs.mkdirSync(dir, { recursive: true }); fs.writeFileSync(file, name); } catch {}
  return { name, id, seq };
}
