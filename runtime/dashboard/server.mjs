// Anicca realtime net-worth + activity dashboard (6PM demo).
// AUTOMATIC: the server itself reads on-chain balances + the loop ledger on an interval and
// streams them via SSE — the page updates itself, no human refresh. Shows LOCAL (and CLOUD
// once Akash lands) anicca: live net worth, earnings since start, and a live activity log.
//
// No private keys. Read-only on-chain balanceOf + reading the agent's own ledger files.
import http from "http";
import fs from "fs";

const PORT = process.env.DASH_PORT || 8420;
const RPC = process.env.BASE_RPC_URL || "https://base-rpc.publicnode.com";
const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const AUSDC = "0x4e65fE4DbA92790696d040ac24Aa414708F5c0AB";
const MUSDC = "0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22";       // Moonwell mUSDC (8 dec)
const MORPHO = "0xbeef0e0834849aCC03f0089F01f4F1Eeb06873C9";      // Morpho vault (ERC-4626)

// Agents to track. Cloud is added once Akash deploy lands (D).
const AGENTS = [
  { id: "local", name: "Anicca / Local", host: "Mac mini + ClawRouter",
    wallet: "0xB9dd3B67921B354c656523d6851537988F31DD56",
    home: (process.env.HOME || "") + "/.anicca" },
];

const SNAP = (process.env.HOME || "") + "/.anicca/state/networth-snapshots.json";

async function call(to, data) {
  const r = await fetch(RPC, { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_call", params: [{ to, data }, "latest"] }) });
  const j = await r.json();
  return BigInt(j.result || "0x0");
}
const balOf = (token, who) => call(token, "0x70a08231" + who.toLowerCase().replace(/^0x/, "").padStart(64, "0"));

async function convertToAssets(vault, shares) {
  // ERC-4626 convertToAssets(uint256)
  const data = "0x07a2d13a" + shares.toString(16).padStart(64, "0");
  try { return await call(vault, data); } catch { return 0n; }
}
async function mExchangeRate() { try { return await call(MUSDC, "0x182df0f5"); } catch { return 0n; } }

async function netWorth(wallet) {
  const [liq, aave, mShares, mTok] = await Promise.all([
    balOf(USDC, wallet), balOf(AUSDC, wallet), balOf(MORPHO, wallet), balOf(MUSDC, wallet),
  ]);
  const morpho = await convertToAssets(MORPHO, mShares);           // 6-dec USDC
  const exRate = await mExchangeRate();                            // moonwell exchangeRate
  const moonwell = (mTok * exRate) / (10n ** 18n);                 // -> 6-dec USDC
  const usd = (x) => Number(x) / 1e6;
  const parts = { liquid: usd(liq), aave: usd(aave), morpho: usd(morpho), moonwell: usd(moonwell) };
  parts.total = parts.liquid + parts.aave + parts.morpho + parts.moonwell;
  return parts;
}

function tailLedger(home, n = 40) {
  try {
    const lines = fs.readFileSync(home + "/state/ledger.jsonl", "utf8").trim().split("\n");
    return lines.slice(-n).map((l) => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);
  } catch { return []; }
}

function loadSnaps() { try { return JSON.parse(fs.readFileSync(SNAP, "utf8")); } catch { return {}; } }
function saveSnaps(s) { try { fs.writeFileSync(SNAP, JSON.stringify(s)); } catch {} }

async function buildState() {
  const snaps = loadSnaps();
  const out = [];
  for (const a of AGENTS) {
    let nw, err = null;
    try { nw = await netWorth(a.wallet); } catch (e) { err = String(e?.message || e); nw = null; }
    if (nw) {
      if (!snaps[a.id]) snaps[a.id] = { first: nw.total, firstTs: nowSec(), last: nw.total };
      snaps[a.id].last = nw.total;
    }
    const base = snaps[a.id]?.first ?? nw?.total ?? 0;
    out.push({
      id: a.id, name: a.name, host: a.host, wallet: a.wallet,
      online: !err, netWorth: nw, error: err,
      earnedSinceStart: nw ? +(nw.total - base).toFixed(6) : 0,
      log: tailLedger(a.home),
    });
  }
  saveSnaps(snaps);
  return { ts: nowSec(), agents: out };
}
// Date.now is fine in a normal server runtime (not a workflow script).
function nowSec() { return Math.floor(Date.now() / 1000); }

let cache = { ts: 0, agents: [] };
async function refresh() { try { cache = await buildState(); } catch (e) { /* keep last */ } }
await refresh();
setInterval(refresh, 15000); // server auto-updates every 15s (no human)

const HTML = fs.readFileSync(new URL("./index.html", import.meta.url), "utf8");

http.createServer(async (req, res) => {
  if (req.url === "/api/state") {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    res.end(JSON.stringify(cache));
  } else if (req.url === "/events") {
    res.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-cache", Connection: "keep-alive" });
    const send = () => res.write(`data: ${JSON.stringify(cache)}\n\n`);
    send();
    const iv = setInterval(send, 4000);
    req.on("close", () => clearInterval(iv));
  } else {
    res.writeHead(200, { "Content-Type": "text/html" });
    res.end(HTML);
  }
}).listen(PORT, () => console.log(`anicca dashboard on http://127.0.0.1:${PORT}`));
