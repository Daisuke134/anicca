// telemetry-post-claude-p.mjs — ONE-SHOT signed telemetry POST for claude-p (human-funded, EVM/Polygon
// instance — this Claude → Polymarket earner). Appended fail-safe to
// skills/earn/polymarket-trade/run_earner.sh after each trading pass. Posts once and exits — this is a
// launchd one-shot pass, not a daemon.
//
// IDENTITY NOTE (2026-07-05 finding, see skills/earn/polymarket-trade/SKILL.md): claude-p's REAL funded
// Polymarket wallet (0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74) is a smart-contract PROXY (ERC-1167,
// POLY_1271 signature type) controlled by the owner EOA in .env's POLYGON_WALLET_PRIVATE_KEY — it has NO
// private key of its own, so it structurally cannot produce a plain EIP-191 signature (which is all the
// telemetry endpoint currently verifies). The owner EOA (0x810F6D61…) is ALSO the shared
// founder/treasury identity used elsewhere (SEED_ADDRESSES) — signing telemetry as that address would
// misreport claude-p's identity as the treasury's. So, exactly like anicca-a3cdd4's own poster (whose
// wallet.json SIGNS while net worth is read from many separate DeFi vault addresses), this poster uses a
// DEDICATED signing-only identity key (~/.anicca-founder/state/telemetry-identity.json, holds no funds,
// never used for trading) while reporting the REAL balance read from the documented funded proxy address.
import fs from "fs";
import { privateKeyToAccount } from "viem/accounts";

const IDENTITY_PATH = process.env.HOME + "/.anicca-founder/state/telemetry-identity.json";
const FUNDED_ADDRESS = "0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74"; // claude-p's real Polymarket proxy wallet (documented in CLAUDE.md SSOT + colony-status.sh)
const POLY_RPC = "https://polygon-bor-rpc.publicnode.com";
const PUSD = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB";
const BALANCE_OF_SELECTOR = "0x70a08231";
const TELEMETRY_URL = process.env.ANICCA_TELEMETRY_URL || "https://aniccaai.com/.netlify/functions/telemetry";

const pk = JSON.parse(fs.readFileSync(IDENTITY_PATH, "utf8")).privateKey;
const acct = privateKeyToAccount(pk.startsWith("0x") ? pk : "0x" + pk);

async function erc20Balance(rpc, token, addr) {
  try {
    const data = BALANCE_OF_SELECTOR + addr.slice(2).toLowerCase().padStart(64, "0");
    const r = await fetch(rpc, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_call", params: [{ to: token, data }, "latest"] }) });
    const j = await r.json();
    if (!j.result || j.result === "0x") return 0;
    return Number(BigInt(j.result)) / 1e6;
  } catch { return 0; }
}

async function pmUnrealizedPnl(addr) {
  try {
    const r = await fetch(`https://data-api.polymarket.com/positions?user=${addr}&sizeThreshold=0.1`);
    const d = await r.json();
    const list = Array.isArray(d) ? d : [];
    return list.reduce((s, p) => s + (Number(p.cashPnl) || 0), 0);
  } catch { return 0; }
}

async function post() {
  const [bal, upnl] = await Promise.all([erc20Balance(POLY_RPC, PUSD, FUNDED_ADDRESS), pmUnrealizedPnl(FUNDED_ADDRESS)]);
  const net_worth_usd = +bal.toFixed(6);
  const payload = {
    id: acct.address, ts: Math.floor(Date.now() / 1000), host: "claude-p", geo: "JP",
    funding: "human", env: "local", brain: "claude-p",
    model_live: "claude-sonnet-5", model_tier: "frontier",
    net_worth_usd, revenue_mo_usd: +upnl.toFixed(6), burn_day_usd: 0, runway_days: 999, status: "alive",
  };
  const message = JSON.stringify(payload);
  const signature = await acct.signMessage({ message });
  const r = await fetch(TELEMETRY_URL, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message, signature }) });
  console.log(new Date().toISOString(), "claude-p net", net_worth_usd, "->", r.status, await r.text());
}
await post();
