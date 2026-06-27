#!/usr/bin/env node
// record-earn.mjs — append a VERIFIED earning to the FOUNDER node's OWN body ledger, with NO way to fabricate a dollar.
//
// The founder (me = Claude Code, human-funded) records ONLY a REAL settled increase of its own on-chain USDC. The
// read-only monitor pulls this ledger to a public dashboard that claims "your Claude earns more than you pay", so a
// faked number = fraud. Anti-fake design (post-adversary sprint-1):
//   - the wallet is ALWAYS the canonical founder wallet.json address (INV-1) — never a caller-supplied/shared wallet.
//   - the balance is read from a TRUSTED, hardcoded Base RPC — NOT a caller-controllable env (FIND-005).
//   - the baseline is the founder's OWN last-recorded balance in state (FIND-001) — not a caller arg.
//   - every test seam (fake balance / baseline / wallet / ledger / rpc) is gated behind FOUNDER_TEST=1 (FIND-001).
//   - the ledger MUST resolve INSIDE the founder dir (INV-3, FIND-004) — never the public site / dashboard render.
//   - no real increase, missing wallet, or RPC failure → exit !=0, write NOTHING (INV-6).
//
// prod usage:  node record-earn.mjs [--source x402] [--task ...] [--cost <usd>]
//   reads baseline from state, reads current USDC from the trusted RPC, delta=current-baseline; delta>0 ⇒ append + bump baseline.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const TEST = process.env.FOUNDER_TEST === "1";                 // all seams below are honored ONLY in test
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf("--" + k); return i >= 0 ? args[i + 1] : d; };
function die(m) { console.error("record-earn: " + m); process.exit(1); }

const HOME = process.env.HOME || os.homedir();
const FOUNDER_DIR = process.env.FOUNDER_DIR || path.join(HOME, ".anicca-founder"); // body location (the monitor reads the canonical ~/.anicca-founder)
const STATE = path.join(FOUNDER_DIR, "state");
const WALLET_JSON = path.join(FOUNDER_DIR, "wallet.json");
const BASELINE_FILE = path.join(STATE, "usdc-baseline.txt");

// ledger path — default inside the founder body; a test override is still forced to resolve INSIDE FOUNDER_DIR (INV-3).
let LEDGER = (TEST && process.env.FOUNDER_LEDGER) || path.join(STATE, "earn-ledger.jsonl");
if (!(path.resolve(LEDGER) + "").startsWith(path.resolve(FOUNDER_DIR) + path.sep)) {
  die("INV-3 violation: ledger must resolve INSIDE the founder dir (" + FOUNDER_DIR + "), never the public site/dashboard.");
}

const SHARED = ["0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21", "0x9b1ee988b1a2931abce467f0a8eaff6c70c93e83"];
// wallet — canonical = founder wallet.json (the positive allowlist). A test override is still denylisted (INV-1).
let wallet;
if (TEST && process.env.FOUNDER_WALLET) wallet = process.env.FOUNDER_WALLET;
else { try { wallet = JSON.parse(fs.readFileSync(WALLET_JSON, "utf8")).address; } catch { die("no founder wallet.json (gen-wallet first)"); } }
if (!/^0x[a-fA-F0-9]{40}$/.test(wallet || "")) die("bad founder wallet address");
if (SHARED.includes(wallet.toLowerCase())) die("INV-1 violation: founder wallet must NOT be a shared/other instance's wallet");

const source = opt("source", "x402");
const cost = Number(opt("cost", "0")) || 0;
const task = opt("task", "earn");
const wake = opt("wake", String(Math.floor(Date.now() / 1000)));

const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"; // USDC on Base
const TRUSTED_RPC = "https://mainnet.base.org";              // hardcoded; NOT caller-overridable in prod (FIND-005)
async function usdcBalance(addr) {
  if (TEST && process.env.FOUNDER_USDC_NOW !== undefined) return Number(process.env.FOUNDER_USDC_NOW); // test seam ONLY
  const rpc = (TEST && process.env.BASE_RPC_URL) || TRUSTED_RPC;
  const data = "0x70a08231000000000000000000000000" + addr.slice(2).toLowerCase();
  const r = await fetch(rpc, { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_call", params: [{ to: USDC, data }, "latest"] }) });
  const j = await r.json();
  if (!j.result) throw new Error("rpc: " + JSON.stringify(j.error || j));
  return Number(BigInt(j.result)) / 1e6;
}

// baseline = the founder's OWN last-recorded balance (self-maintained), NOT a caller arg (FIND-001).
let baseline;
if (TEST && process.env.FOUNDER_USDC_BASELINE !== undefined) baseline = Number(process.env.FOUNDER_USDC_BASELINE);
else { try { baseline = Number(fs.readFileSync(BASELINE_FILE, "utf8").trim()) || 0; } catch { baseline = 0; } }
if (!Number.isFinite(baseline) || baseline < 0) die("bad baseline");

const current = await usdcBalance(wallet).catch((e) => die("balance query failed (fail-closed): " + e.message));
const delta = +(current - baseline).toFixed(6);
if (!(delta > 0)) die(`no verified earning (USDC delta=${delta}; baseline=${baseline} now=${current}) — refusing a fake dollar`);

const row = { ts: Math.floor(Date.now() / 1000), wallet, source, task, earn_usdc: delta, cost_usdc: cost, net_usdc: +(delta - cost).toFixed(6), wake };
fs.mkdirSync(path.dirname(LEDGER), { recursive: true });
fs.appendFileSync(LEDGER, JSON.stringify(row) + "\n");
fs.mkdirSync(STATE, { recursive: true });
fs.writeFileSync(BASELINE_FILE, String(current));   // advance the baseline so the same dollars are never double-counted
console.log(`record-earn: VERIFIED +${delta} USDC (${source}) -> ${LEDGER}`);
