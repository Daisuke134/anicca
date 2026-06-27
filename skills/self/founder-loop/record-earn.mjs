#!/usr/bin/env node
// record-earn.mjs — append a VERIFIED earning to the FOUNDER node's OWN body ledger, with NO way to fabricate a dollar.
//
// The founder (me = Claude Code, human-funded) records ONLY a REAL settled INCREASE of its own on-chain USDC since the
// last record. A read-only monitor pulls this ledger to a public dashboard claiming "your Claude earns more than you
// pay", so a faked number = fraud. Anti-fake design (post-adversary sprint-2):
//   - PROD (FOUNDER_TEST != "1") trusts NOTHING from the caller: the founder dir is the HARDCODED canonical path, the
//     wallet is its wallet.json, the balance comes from a HARDCODED trusted Base RPC. Every override env (dir / wallet /
//     ledger / baseline / now / rpc) is honored ONLY under FOUNDER_TEST=1 (FIND-001/008).
//   - FIRST run initializes the baseline to the CURRENT balance and records NOTHING — pre-existing/seed capital is never
//     counted as an earning (FIND-007). Only later INCREASES are earnings.
//   - the baseline is read strictly (a corrupt/NaN file fails closed, never coerced to 0) and written ATOMICALLY (FIND-009).
//   - the ledger MUST resolve INSIDE the founder dir (INV-3); delta<=0 / missing wallet / RPC failure → exit!=0, no write (INV-6).
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const TEST = process.env.FOUNDER_TEST === "1";          // EVERY override below is honored ONLY in test
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf("--" + k); return i >= 0 ? args[i + 1] : d; };
function die(m) { console.error("record-earn: " + m); process.exit(1); }

const HOME = (TEST && process.env.HOME) || os.homedir(); // HOME is a seam too — TEST-gated so prod cannot move the trust root (FIND-301)
const FOUNDER_DIR = (TEST && process.env.FOUNDER_DIR) || path.join(HOME, ".anicca-founder"); // canonical in prod (FIND-008)
const STATE = path.join(FOUNDER_DIR, "state");
const WALLET_JSON = path.join(FOUNDER_DIR, "wallet.json");
const BASELINE_FILE = path.join(STATE, "usdc-baseline.txt");
let LEDGER = (TEST && process.env.FOUNDER_LEDGER) || path.join(STATE, "earn-ledger.jsonl");
// INV-3 (FIND-303): realpath the founder dir AND the ledger's nearest existing ancestor so a symlinked state/
// dir cannot escape the body — a lexical resolve does NOT dereference symlinks.
const realFounder = fs.realpathSync(FOUNDER_DIR);
let _anc = path.resolve(LEDGER);
while (!fs.existsSync(_anc) && path.dirname(_anc) !== _anc) _anc = path.dirname(_anc);
const realAnc = fs.realpathSync(_anc);
if (realAnc !== realFounder && !(realAnc + path.sep).startsWith(realFounder + path.sep)) {
  die("INV-3: ledger must resolve INSIDE the founder dir, never the public site/dashboard render.");
}

const SHARED = ["0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21", "0x9b1ee988b1a2931abce467f0a8eaff6c70c93e83"];
const FOUNDER_WALLET_EXPECTED = "0x810f6d61f7606deee2657d3083e150a222bc29c5"; // the generated founder wallet — positive identity pin (FIND-302)
let wallet;
if (TEST && process.env.FOUNDER_WALLET) wallet = process.env.FOUNDER_WALLET;
else { try { wallet = JSON.parse(fs.readFileSync(WALLET_JSON, "utf8")).address; } catch { die("no founder wallet.json (gen-wallet first)"); } }
if (!/^0x[a-fA-F0-9]{40}$/.test(wallet || "")) die("bad founder wallet address");
if (SHARED.includes(wallet.toLowerCase())) die("INV-1: founder wallet must NOT be a shared/other instance's wallet");
if (wallet.toLowerCase() !== FOUNDER_WALLET_EXPECTED) die("INV-1: founder wallet must be the PINNED founder wallet (rejects ANY other wallet, even non-shared) — FIND-302");

const source = opt("source", "x402");
const cost = Number(opt("cost", "0")) || 0;
const task = opt("task", "earn");
const wake = opt("wake", String(Math.floor(Date.now() / 1000)));

const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const TRUSTED_RPC = "https://mainnet.base.org";
async function usdcBalance(addr) {
  if (TEST && process.env.FOUNDER_USDC_NOW !== undefined) return Number(process.env.FOUNDER_USDC_NOW);
  const rpc = (TEST && process.env.BASE_RPC_URL) || TRUSTED_RPC;
  const data = "0x70a08231000000000000000000000000" + addr.slice(2).toLowerCase();
  const r = await fetch(rpc, { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_call", params: [{ to: USDC, data }, "latest"] }) });
  const j = await r.json();
  if (!j.result) throw new Error("rpc: " + JSON.stringify(j.error || j));
  return Number(BigInt(j.result)) / 1e6;
}
function writeBaselineAtomic(v) {
  fs.mkdirSync(STATE, { recursive: true });
  const tmp = BASELINE_FILE + ".tmp";
  fs.writeFileSync(tmp, String(v));
  fs.renameSync(tmp, BASELINE_FILE);   // atomic on the same fs (FIND-009)
}

// baseline = the founder's OWN last-recorded balance. STRICT: a corrupt file fails closed, never coerced to 0 (FIND-009).
let baseline = null; // null = "not initialized yet"
const baselineSeam = TEST ? process.env.FOUNDER_USDC_BASELINE : undefined; // honored ONLY in test
if (baselineSeam !== undefined) {
  baseline = Number(baselineSeam);
  if (!Number.isFinite(baseline) || baseline < 0) die("bad --baseline seam");
} else if (fs.existsSync(BASELINE_FILE)) {
  const raw = fs.readFileSync(BASELINE_FILE, "utf8").trim();
  const n = Number(raw);
  if (raw === "" || !Number.isFinite(n) || n < 0) die("baseline file corrupt — fail-closed (refusing to re-count the balance)");
  baseline = n;
}

const current = await usdcBalance(wallet).catch((e) => die("balance query failed (fail-closed): " + e.message));

// FIRST run: initialize the baseline to the current balance and record NOTHING — pre-existing/seed capital is NOT earned (FIND-007).
if (baseline === null) {
  writeBaselineAtomic(current);
  console.log(`record-earn: initialized baseline=${current} USDC (first run — no earning recorded; only future INCREASES count)`);
  process.exit(0);
}

const delta = +(current - baseline).toFixed(6);
if (!(delta > 0)) die(`no verified earning (USDC delta=${delta}; baseline=${baseline} now=${current}) — refusing a fake dollar`);

const row = { ts: Math.floor(Date.now() / 1000), wallet, source, task, earn_usdc: delta, cost_usdc: cost, net_usdc: +(delta - cost).toFixed(6), wake };
fs.mkdirSync(path.dirname(LEDGER), { recursive: true });
writeBaselineAtomic(current);   // FIND-304: advance the high-water-mark FIRST — a crash here loses ONE record (honest under-count), but the same dollars can NEVER be double-counted (a replay sees delta=0).
fs.appendFileSync(LEDGER, JSON.stringify(row) + "\n");
console.log(`record-earn: VERIFIED +${delta} USDC (${source}) -> ${LEDGER}`);
