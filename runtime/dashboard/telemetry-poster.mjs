// Telemetry poster — the local anicca reports its live state to aniccaai.com every 120s so it
// shows on the public dashboard (ranking) and its own /<host> live page. Signs the verbatim
// message with the agent's own wallet key (no human key). Includes the last 20 ledger lines so
// the /<host> page can stream the agent's REAL activity log (no fakes).
import { privateKeyToAccount } from "viem/accounts";
import { createPublicClient, http } from "viem";
import { base } from "viem/chains";
import fs from "fs";

const HOME = process.env.HOME;
const pk = JSON.parse(fs.readFileSync(HOME + "/.automaton/wallet.json")).privateKey;
const acct = privateKeyToAccount(pk.startsWith("0x") ? pk : "0x" + pk);
const NAME = process.env.ANICCA_NAME || "anicca-local";   // display name / number (spawned: anicca001, bob, ...)
const LEDGER = (process.env.ANICCA_HOME || HOME + "/.anicca") + "/state/ledger.jsonl";

const pub = createPublicClient({ chain: base, transport: http("https://base-rpc.publicnode.com") });
const ABI = [{ name: "balanceOf", type: "function", stateMutability: "view", inputs: [{ type: "address" }], outputs: [{ type: "uint256" }] }];
const U = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", A = "0x4e65fE4DbA92790696d040ac24Aa414708F5c0AB",
      M = "0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22", V = "0xbeef0e0834849aCC03f0089F01f4F1Eeb06873C9";
const bal = (t, w) => pub.readContract({ address: t, abi: ABI, functionName: "balanceOf", args: [w] }).then(Number);

async function netWorth() {
  const [l, a, mt, ms] = await Promise.all([bal(U, acct.address), bal(A, acct.address), bal(M, acct.address), bal(V, acct.address)]);
  const ex = Number(await pub.readContract({ address: M, abi: [{ name: "exchangeRateStored", type: "function", stateMutability: "view", inputs: [], outputs: [{ type: "uint256" }] }], functionName: "exchangeRateStored" }));
  const mo = Number(await pub.readContract({ address: V, abi: [{ name: "convertToAssets", type: "function", stateMutability: "view", inputs: [{ type: "uint256" }], outputs: [{ type: "uint256" }] }], functionName: "convertToAssets", args: [BigInt(ms)] }));
  const usd = (x) => x / 1e6;
  return { liquid: usd(l), aave: usd(a), morpho: usd(mo), moonwell: (mt * ex / 1e18) / 1e6 };
}

function recentLog(n = 20) {
  try {
    return fs.readFileSync(LEDGER, "utf8").trim().split("\n").slice(-n)
      .map((s) => { try { const o = JSON.parse(s); return { ts: o.ts, kind: o.kind, slot: o.slot || null, model: o.model || null, note: o.task || o.source || (o.deposited_usdc ? `+${o.deposited_usdc} USDC->yield` : "") }; } catch { return null; } })
      .filter(Boolean);
  } catch { return []; }
}

function lastModel() {
  const lines = recentLog(20);
  for (let i = lines.length - 1; i >= 0; i--) if (lines[i].model) return lines[i].model;
  return "auto";
}
const FREE_RE = /nvidia|flash|qwen|free|oss|gpt-oss/i;

async function post() {
  try {
    const nw = await netWorth();
    const total = +(nw.liquid + nw.aave + nw.morpho + nw.moonwell).toFixed(2);
    const ts = Math.floor(Date.now() / 1000);
    const model = lastModel();
    const tier = FREE_RE.test(model) ? "free" : "frontier";
    const msg = JSON.stringify({
      id: acct.address.toLowerCase(), ts, host: NAME, geo: "JP",
      model_live: model, model_tier: tier,
      net_worth_usd: total, revenue_mo_usd: 0, burn_day_usd: 0, runway_days: 999, status: "alive",
      breakdown: nw, log: recentLog(20),
    });
    const signature = await acct.signMessage({ message: msg });
    const r = await fetch("https://aniccaai.com/.netlify/functions/telemetry", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: msg, signature }),
    });
    console.log(new Date().toISOString(), NAME, "net", total, "log", recentLog(20).length, "->", r.status, await r.text());
  } catch (e) { console.log("err", e.message); }
}
await post();
setInterval(post, 120000);
