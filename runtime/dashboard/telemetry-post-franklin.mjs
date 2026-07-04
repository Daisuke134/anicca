// telemetry-post-franklin.mjs — ONE-SHOT signed telemetry POST for Franklin (SELF-funded, Solana
// ed25519 instance). Appended fail-safe to skills/earn/sol-trade/run.sh after each trading pass (never
// blocks/affects the trade itself). Reads Franklin's OWN wallet key in-process only (never logged,
// never echoed) to sign; every balance read is a PUBLIC RPC call. Posts once and exits (unlike the
// long-running anicca-a3cdd4 daemon poster) because this runs once per launchd pass, not as a service.
//
// Contract = apps/landing/netlify/functions/_lib/{telemetry-schema,telemetry-verify}.js chain:"solana"
// branch: id = base58 pubkey (the verification key itself, ed25519 has no signer-recovery step), never
// case-folded; signature = base58(tweetnacl detached signature over the verbatim JSON.stringify bytes).
import fs from "fs";
import bs58 from "bs58";
import nacl from "tweetnacl";

const HOME = process.env.HOME;
const SOLANA_WALLET_FILE = HOME + "/.blockrun/.solana-session"; // base58 64-byte secret key (Franklin's own wallet, written by @blockrun/llm on first `franklin setup`)
const COST_LOG = HOME + "/.blockrun/cost_log.jsonl";
const SOLR = "https://api.mainnet-beta.solana.com";
const SOL_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
const TELEMETRY_URL = process.env.ANICCA_TELEMETRY_URL || "https://aniccaai.com/.netlify/functions/telemetry";

const secretB58 = fs.readFileSync(SOLANA_WALLET_FILE, "utf8").trim();
const secretKey = bs58.decode(secretB58); // 64 bytes: tweetnacl secretKey format == Solana Keypair.secretKey
const address = bs58.encode(Buffer.from(secretKey.slice(32))); // last 32 bytes = the public key

async function rpc(method, params) {
  const r = await fetch(SOLR, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }) });
  const j = await r.json();
  return j.result;
}

async function solBalance() {
  try { const r = await rpc("getBalance", [address]); return (r?.value || 0) / 1e9; } catch { return 0; }
}
async function usdcBalance() {
  try {
    const r = await rpc("getTokenAccountsByOwner", [address, { mint: SOL_USDC_MINT }, { encoding: "jsonParsed" }]);
    const list = r?.value || [];
    return list.reduce((s, a) => s + (Number(a.account?.data?.parsed?.info?.tokenAmount?.uiAmount) || 0), 0);
  } catch { return 0; }
}
async function solPrice() {
  try { const r = await fetch("https://api.coinbase.com/v2/prices/SOL-USD/spot"); return Number((await r.json()).data.amount) || 0; } catch { return 0; }
}
// Franklin's own LLM spend ledger (BlockRun x402 per-call cost, from its own wallet) — today's sum.
function burnToday() {
  const midnight = Math.floor(Date.now() / 86400000) * 86400;
  try {
    return fs.readFileSync(COST_LOG, "utf8").trim().split("\n")
      .map((l) => { try { return JSON.parse(l); } catch { return null; } })
      .filter((o) => o && o.ts >= midnight)
      .reduce((s, o) => s + (Number(o.cost_usd) || 0), 0);
  } catch { return 0; }
}

async function post() {
  const [sol, usdc, price] = await Promise.all([solBalance(), usdcBalance(), solPrice()]);
  const net_worth_usd = +(usdc + sol * price).toFixed(6);
  const burn_day_usd = +burnToday().toFixed(6);
  const payload = {
    id: address, ts: Math.floor(Date.now() / 1000), host: "Franklin", geo: "JP", chain: "solana",
    funding: "self", env: "local", brain: "proxy",
    model_live: "openai/gpt-5-mini", model_tier: "frontier",
    net_worth_usd, revenue_mo_usd: 0, burn_day_usd, runway_days: 999, status: "alive",
  };
  const message = JSON.stringify(payload);
  const sig = nacl.sign.detached(Buffer.from(message, "utf8"), secretKey);
  const signature = bs58.encode(Buffer.from(sig));
  const r = await fetch(TELEMETRY_URL, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message, signature }) });
  console.log(new Date().toISOString(), "Franklin net", net_worth_usd, "->", r.status, await r.text());
}
await post();
