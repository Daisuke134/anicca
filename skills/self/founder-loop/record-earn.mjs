#!/usr/bin/env node
// record-earn.mjs — append a VERIFIED earning to the FOUNDER node's OWN body ledger.
//
// The founder (me = Claude Code, human-funded) records ONLY real, settled revenue: it confirms the founder wallet's
// on-chain USDC balance ACTUALLY INCREASED (a real settlement) before writing — never a fabricated/simulated dollar
// (HARD 0.24, INV-2/INV-6). It writes ONLY the founder body ledger, NEVER aniccaai.com / apps/landing / dashboard.json
// (INV-3) — the read-only monitor pulls this ledger, so the numbers cannot be faked.
//
// usage:  node record-earn.mjs --source <x402|...> --baseline <usdc_before> [--task <t>] [--cost <usd>] [--wake <id>]
//   delta = (USDC balanceOf the founder wallet NOW) - baseline.  delta <= 0  -> exit 1, write nothing.
//   delta  > 0  -> append {ts, wallet, source, task, earn_usdc:delta, cost_usdc, net_usdc, wake} to the founder ledger.
//
// Test seam: FOUNDER_USDC_NOW (skip the RPC), FOUNDER_WALLET, FOUNDER_LEDGER, BASE_RPC_URL.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf("--" + k); return i >= 0 ? args[i + 1] : d; };

const HOME = process.env.HOME || os.homedir();
const FOUNDER_DIR = process.env.FOUNDER_DIR || path.join(HOME, ".anicca-founder");
const WALLET_JSON = path.join(FOUNDER_DIR, "wallet.json");
const LEDGER = process.env.FOUNDER_LEDGER || path.join(FOUNDER_DIR, "state", "earn-ledger.jsonl");

function die(msg) { console.error("record-earn: " + msg); process.exit(1); }

// INV-3: refuse to write anywhere near the public site / dashboard render.
if (/aniccaai|apps\/landing|dashboard\.json|public\//.test(LEDGER)) {
  die("INV-3 violation: the founder ledger must be the founder's OWN body, never the public site / dashboard.");
}

const source = opt("source");
if (!source) die("missing --source");
const baselineRaw = opt("baseline");
if (baselineRaw === undefined) die("missing --baseline (the USDC balance before this earn move)");
const baseline = Number(baselineRaw);
if (!Number.isFinite(baseline) || baseline < 0) die("bad --baseline");
const cost = Number(opt("cost", "0")) || 0;
const task = opt("task", "earn");
const wake = opt("wake", String(Math.floor(Date.now() / 1000)));

// founder wallet address
let wallet = process.env.FOUNDER_WALLET;
if (!wallet) {
  try { wallet = JSON.parse(fs.readFileSync(WALLET_JSON, "utf8")).address; } catch { /* fall through */ }
}
if (!wallet || !/^0x[a-fA-F0-9]{40}$/.test(wallet)) die("no founder wallet address (gen-wallet first)");

// INV-1: never the Automaton self-funded wallet or another instance's wallet.
const SHARED = ["0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21", "0x9b1ee988b1a2931abce467f0a8eaff6c70c93e83"];
if (SHARED.includes(wallet.toLowerCase())) die("INV-1 violation: founder wallet must NOT be a shared/other instance's wallet");

const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"; // USDC on Base
async function usdcBalance(addr) {
  if (process.env.FOUNDER_USDC_NOW !== undefined) return Number(process.env.FOUNDER_USDC_NOW); // test seam
  const rpc = process.env.BASE_RPC_URL || "https://mainnet.base.org";
  const data = "0x70a08231000000000000000000000000" + addr.slice(2).toLowerCase();
  const r = await fetch(rpc, { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_call", params: [{ to: USDC, data }, "latest"] }) });
  const j = await r.json();
  if (!j.result) throw new Error("rpc: " + JSON.stringify(j.error || j));
  return Number(BigInt(j.result)) / 1e6;
}

const now = await usdcBalance(wallet).catch((e) => die("balance query failed: " + e.message));
const delta = +(now - baseline).toFixed(6);

// INV-2 / INV-6: only a REAL positive settlement is an earning. No proof of increase => write nothing, fail-closed.
if (!(delta > 0)) die(`no verified earning (USDC delta=${delta}; baseline=${baseline} now=${now}) — refusing to write a fake dollar`);

const row = { ts: Math.floor(Date.now() / 1000), wallet, source, task, earn_usdc: delta, cost_usdc: cost, net_usdc: +(delta - cost).toFixed(6), wake };
fs.mkdirSync(path.dirname(LEDGER), { recursive: true });
fs.appendFileSync(LEDGER, JSON.stringify(row) + "\n");
console.log(`record-earn: VERIFIED +${delta} USDC (${source}) -> ${LEDGER}`);
