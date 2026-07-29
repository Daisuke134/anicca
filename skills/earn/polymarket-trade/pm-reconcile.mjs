#!/usr/bin/env node
// pm-reconcile.mjs — wire wallet-anchored reconcile for the Polymarket earner (TASKLIST #2).
//
// pm's ledger (__REPO_ROOT__/skills/earn/state/earn-ledger.jsonl, where redeem.py appends) only ever got
// WIN rows; buys and $0-resolve losses were never recorded, so the ledger disagreed with the real
// pUSD wallet. This runs at the END of every pm pass (run_earner.sh): it reads the REAL on-chain
// pUSD balance of the deposit wallet and books the drift as a wallet-scoped `reconcile` line, so
// losses/costs finally land and: sum(pm net_usdc since a snapshot) == real pUSD delta.
//
// Read-only w.r.t. the chain (eth_call balanceOf) — never signs, never spends. Fail-closed: any RPC
// error books nothing (reconcile() returns ok:false).
import path from "node:path";
import os from "node:os";
import { reconcile } from "../lib/reconcile.mjs";

const DEPOSIT_WALLET = "0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74"; // pm proxy wallet (holds funds)
const PUSD = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB";           // pUSD (6 decimals)
const RPC = process.env.POLYGON_RPC || "https://polygon-bor-rpc.publicnode.com";
// pm's earns are recorded here by redeem.py (LEDGER_PATH). reconcile MUST target the same file.
const LEDGER = process.env.PM_LEDGER_PATH ||
  path.join(os.homedir(), "anicca", "skills", "earn", "state", "earn-ledger.jsonl");

// eth_call balanceOf(DEPOSIT_WALLET) on pUSD -> USD number. Same primitive as colony-status.sh::erc20.
async function fetchPusd() {
  const data = "0x70a08231000000000000000000000000" + DEPOSIT_WALLET.slice(2).toLowerCase();
  const body = { jsonrpc: "2.0", id: 1, method: "eth_call",
    params: [{ to: PUSD, data }, "latest"] };
  const res = await fetch(RPC, { method: "POST",
    headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  const j = await res.json();
  const hex = j && j.result;
  if (!hex || hex === "0x") return null;      // fail-closed: unknown balance -> book nothing
  return Number(BigInt(hex)) / 1e6;
}

async function main() {
  const r = await reconcile(DEPOSIT_WALLET.toLowerCase(), LEDGER, fetchPusd, undefined,
    DEPOSIT_WALLET.toLowerCase()); // ownWallet scope: only pm's own rows drive the drift math
  if (!r.ok) { console.error(`[pm-reconcile] skipped: ${r.reason}`); return; }
  if (r.baseline) { console.error(`[pm-reconcile] baseline anchor @ $${r.balance}`); return; }
  console.error(`[pm-reconcile] drift=${r.drift} balance=$${r.balance}` +
    (r.drift < 0 ? " (unrecorded loss/cost booked)" : r.drift > 0 ? " (unrecorded gain booked)" : " (no material drift)"));
}

main().catch((e) => { console.error("[pm-reconcile] error:", e.message); process.exit(0); }); // never break the pass
