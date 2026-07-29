// probe-dist1.mjs — throwaway E2E for the MonetizedMCP adapter (DIST-1).
// Spawns serve-v2 (upstream x402 shop) + mcp-server (MonetizedMCP), then drives the MCP HTTP
// endpoint with the official MCP client: tools/list, price-listing, payment-methods, and a
// make-purchase WITHOUT payment (must forward to serve-v2, get 402, surface it gracefully).
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const SERVE_PORT = 8499;
const MCP_PORT = 8081;
const PAYTO = "0x3EcCAD24794ca298D25378E9902A251322ea8749"; // franklin1 (probe only)
const DIR = path.dirname(fileURLToPath(import.meta.url));

const kids = [];
function launch(name, file, env) {
  const p = spawn(process.execPath, [file], { cwd: DIR, env: { ...process.env, ...env } });
  p.stdout.on("data", (d) => process.stderr.write(`[${name}] ${d}`));
  p.stderr.on("data", (d) => process.stderr.write(`[${name}!] ${d}`));
  kids.push(p);
  return p;
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function cleanup() { for (const p of kids) { try { p.kill("SIGKILL"); } catch {} } }

async function waitPort(url, tries = 40) {
  for (let i = 0; i < tries; i++) {
    try { await fetch(url); return true; } catch { await sleep(250); }
  }
  return false;
}

const results = [];
function check(name, ok, detail) { results.push({ name, ok, detail }); console.log(`${ok ? "PASS" : "FAIL"}  ${name}  ${detail || ""}`); }

try {
  launch("serve", "serve-v2.mjs", {
    X402_CATALOG: "core", X402_PORT: String(SERVE_PORT), X402_PAYTO: PAYTO,
    X402_PUBLIC_URL: `http://127.0.0.1:${SERVE_PORT}`, X402_NETWORK: "base",
  });
  launch("mcp", "mcp-server.mjs", {
    PORT: String(MCP_PORT), X402_PORT: String(SERVE_PORT), X402_PAYTO: PAYTO,
    MCP_UPSTREAM_ORIGIN: `http://127.0.0.1:${SERVE_PORT}`,
  });

  const serveUp = await waitPort(`http://127.0.0.1:${SERVE_PORT}/.well-known/x402.json`);
  check("serve-v2 boots", serveUp, `port ${SERVE_PORT}`);
  const mcpUp = await waitPort(`http://127.0.0.1:${MCP_PORT}/mcp`);
  check("mcp-server boots", mcpUp, `port ${MCP_PORT}`);

  // sanity: hitting serve-v2 /research WITHOUT payment must be 402 (external path unchanged)
  const raw = await fetch(`http://127.0.0.1:${SERVE_PORT}/research?q=x`);
  check("serve-v2 unpaid=402", raw.status === 402, `got ${raw.status}`);

  const client = new Client({ name: "probe", version: "1.0.0" });
  const transport = new StreamableHTTPClientTransport(new URL(`http://127.0.0.1:${MCP_PORT}/mcp`));
  await client.connect(transport);

  const tools = await client.listTools();
  const names = tools.tools.map((t) => t.name).sort();
  check("tools = price-listing/payment-methods/make-purchase",
    ["make-purchase", "payment-methods", "price-listing"].every((n) => names.includes(n)),
    names.join(","));

  const pl = await client.callTool({ name: "price-listing", arguments: { searchQuery: "" } });
  const plData = JSON.parse(pl.content[0].text);
  check("price-listing returns 4 items", plData.items?.length === 4,
    (plData.items || []).map((i) => i.id).join(","));

  const pm = await client.callTool({ name: "payment-methods", arguments: {} });
  const pmData = JSON.parse(pm.content[0].text);
  check("payment-methods walletAddress == payTo",
    Array.isArray(pmData) && pmData[0]?.walletAddress === PAYTO,
    JSON.stringify(pmData));

  const mp = await client.callTool({ name: "make-purchase", arguments: {
    itemId: "research", params: { q: "test" }, signedTransaction: "", paymentMethod: "USDC_BASE_MAINNET" } });
  const mpData = JSON.parse(mp.content[0].text);
  const forwarded402 = JSON.parse(mpData.toolResult || "{}");
  check("make-purchase(no pay) forwards -> 402 surfaced",
    mpData.purchasableItemId === "research" && forwarded402.status === 402,
    `toolResult.status=${forwarded402.status}`);

  const mpBad = await client.callTool({ name: "make-purchase", arguments: {
    itemId: "nope", params: {}, signedTransaction: "", paymentMethod: "USDC_BASE_MAINNET" } });
  const mpBadData = JSON.parse(mpBad.content[0].text);
  check("make-purchase(unknown id) graceful",
    JSON.parse(mpBadData.toolResult || "{}").error?.includes("unknown itemId"),
    mpBadData.toolResult);

  await client.close();
} catch (e) {
  check("probe ran without throw", false, String(e.stack || e));
} finally {
  cleanup();
  const allPass = results.length > 0 && results.every((r) => r.ok);
  console.log(`\n=== ${allPass ? "ALL PASS" : "SOME FAIL"} (${results.filter(r=>r.ok).length}/${results.length}) ===`);
  await sleep(200);
  process.exit(allPass ? 0 : 1);
}
