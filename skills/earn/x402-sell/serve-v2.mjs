/**
 * serve.mjs — the X402 PRODUCT pillar: a TOOL that turns any capability into a paid HTTP endpoint
 * that receives USDC (no buyer account, no API key — the HTTP 402 Payment Required flow).
 *
 * Per HARD RULE #0: this is a TOOL, not a product idea. It does NOT decide WHAT to sell or for HOW
 * MUCH — the MODEL decides that (via env / args) and decides how to create demand. Here we ship the
 * default "web research" product (powered by the Agent-Reach skill: read Twitter/Reddit/YouTube/GitHub
 * with $0 API fees) because at $0 compute, every sale is pure profit — but the model can point the
 * worker at anything it wants to sell.
 *
 * Demand is the GOAL, not a wall: building what people want + attracting buyers is the model's job
 * (list it, share it on socials/GitHub, price it right). This file just makes "get paid in USDC for
 * doing X over HTTP" a one-command primitive. Works local AND cloud (needs a public URL for real
 * buyers — the cloud anicca or a tunnel provides that).
 *
 * Env (the MODEL sets these):
 *   X402_PAYTO        receiving wallet (default: ~/.automaton/wallet.json address)
 *   X402_PRICE        price per request, e.g. "$0.05" (default "$0.02")
 *   X402_NETWORK      "base" (default) | "base-sepolia"
 *   X402_PORT         default 8403
 *   X402_PRODUCT_CMD  shell command template that PRODUCES the paid result; "{q}" is the buyer's query.
 *                     default = Agent-Reach web research. The model can override to sell anything.
 */
import express from "express";
import { execFile } from "node:child_process";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { privateKeyToAccount } from "viem/accounts";
import { loadEvmKey } from "../lib/resolve-identity.mjs";
import { compoundInterest, calcEval, flattenJson, dnsLookup, whois, stockQuote } from "./primitives.mjs";
import { getFundingRatesCached, buildFundingRatesResponse, annualizedBps } from "./funding-rates.mjs";
import { buildFundingRateArbResponse } from "./funding-rate-arb.mjs";

function payTo() {
  if (process.env.X402_PAYTO) return process.env.X402_PAYTO;
  // #28: derive THIS instance's own payTo address from its gated per-instance key — never the shared
  // $HOME wallet's address (which would route another instance's earnings to the wrong wallet).
  const pk = loadEvmKey();
  if (pk) return privateKeyToAccount(pk).address;
  throw new Error("set X402_PAYTO (no per-instance EVM key resolvable)");
}

const PRICE = process.env.X402_PRICE || "$0.003";
// v2 requires CAIP-2 network ids (@x402/core PaymentOption.network: Network). X402_NETWORK stays the
// familiar "base" / "base-sepolia" input; this maps it to the CAIP-2 form the v2 scheme registry expects.
const NETWORK = (process.env.X402_NETWORK || "base") === "base-sepolia" ? "eip155:84532" : "eip155:8453";
const PORT = Number(process.env.X402_PORT || 8403);
// Public HTTPS origin the CDP Bazaar crawler will probe. MUST be the real reachable https:// URL:
// behind a TLS-terminating proxy (tailscale funnel / cloudflared) Express sees req.protocol="http",
// so x402-express would auto-derive an http:// resource URL that the crawler can't reach → never indexed
// (root cause 2026-07-14; cf coinbase/agentkit#877). Set X402_PUBLIC_URL to the https funnel origin.
const PUBLIC_URL = (process.env.X402_PUBLIC_URL || "").replace(/\/+$/, "");
// default product = $0 web-research digest via research-product.mjs (Wikipedia + HN + Jina, zero paid keys).
const PRODUCT_CMD = process.env.X402_PRODUCT_CMD ||
  `node ${new URL('./research-product.mjs', import.meta.url).pathname} {q}`;

const app = express();

// x402 v2: protect the paid route. paymentMiddleware(routes, resourceServer). Verified primitives
// (@x402/express@2.17.0, this session, node_modules .d.ts read): resourceServer = x402ResourceServer
// wired to a facilitator client + a per-network scheme; no key needed to RECEIVE. Loaded dynamically
// so the skill installs the dep on first run.
const { paymentMiddleware, x402ResourceServer } = await import("@x402/express");
const { HTTPFacilitatorClient } = await import("@x402/core/server");
const { ExactEvmScheme } = await import("@x402/evm/exact/server");
// v1 back-compat body (Task 4.5.A) + Bazaar discovery extension (Task 4.5.B). Verified real APIs this
// session (node_modules .d.ts + runtime probe, no guessing):
//   - RouteConfig.unpaidResponseBody?: (context) => {contentType, body} — @x402/core
//     dist/cjs/x402Client-CdmxbRFj.d.ts:751. Defaults to {} when absent (root cause of the v1-buyer
//     TypeError documented in docs/research/2026-07-17-x402-v1-v2-compat.md).
//   - processPriceToAtomicAmount(price, network) from the legacy "x402" package (already a transitive
//     dep of x402-express/x402-fetch; now declared directly in package.json per no-parasitic-deps rule)
//     — the exact helper x402-express@1.2.0 itself uses (node_modules/x402-express/dist/cjs/index.js)
//     to build the v1 PaymentRequirementsV1[] shape.
//   - declareDiscoveryExtension({method,input,inputSchema,output}) from "@x402/extensions/bazaar"
//     returns {bazaar:{info,schema}} for RouteConfig.extensions. paymentMiddleware auto-detects it via
//     checkIfBazaarNeeded(routes) and registers bazaarResourceServerExtension itself
//     (node_modules/@x402/express/dist/cjs/index.js:166) — no manual resourceServer wiring needed.
const { processPriceToAtomicAmount } = await import("x402/shared");
const { declareDiscoveryExtension } = await import("@x402/extensions/bazaar");
// v1 legacy network id is a plain string ("base"/"base-sepolia"), unlike v2's CAIP-2 NETWORK above.
const NETWORK_V1 = process.env.X402_NETWORK || "base";
import { isSettled, decodePayer } from "./lib/settle-gate.mjs";
// CDP facilitator (when CDP keys present) → settles on Base mainnet AND lists the endpoint in the x402
// Bazaar discovery layer (how buyer agents FIND us). Falls back to the x402.org testnet facilitator when
// no CDP keys (generic install / dev). payTo stays our wallet — CDP only facilitates + catalogs, never custodies.
let facilitatorClient;
if (process.env.CDP_API_KEY_ID && process.env.CDP_API_KEY_SECRET) {
  const { createFacilitatorConfig } = await import("@coinbase/x402");
  const cfg = createFacilitatorConfig(process.env.CDP_API_KEY_ID, process.env.CDP_API_KEY_SECRET);
  facilitatorClient = new HTTPFacilitatorClient({ url: cfg.url, createAuthHeaders: cfg.createAuthHeaders });
} else {
  facilitatorClient = new HTTPFacilitatorClient({ url: "https://x402.org/facilitator" });
}
// v2 resource server: facilitator client + one scheme registered per network (exact-payment EVM here).
// ALSO register the same ExactEvmScheme under the plain v1 network id (NETWORK_V1, e.g. "base"): the
// unpaidResponseBody shim above gets a v1 client to construct+send a real X-PAYMENT header, but its
// payload carries `network:"base"` (v1 shape) — x402ResourceServer only matches an incoming payment to
// a scheme by exact network-string lookup (x402ResourceServer.hasRegisteredScheme), so without this
// second registration a v1 payment payload never matches "eip155:8453" and silently falls back to the
// unpaid 402 path again (verified live 2026-07-17: correct v1 body + correctly signed X-PAYMENT header
// still got re-served the unpaid challenge until this alias was added).
const resourceServer = new x402ResourceServer(facilitatorClient)
  .register(NETWORK, new ExactEvmScheme())
  .register(NETWORK_V1, new ExactEvmScheme());
// single product table — drives the payment middleware, "/" index, /.well-known/x402.json and /llms.txt.
const PRODUCTS = [
  { path: "/research", price: PRICE, example: "/research?q=<topic>", what: "web research digest",
    description: "On-demand web research digest — free-source curated (Wikipedia + Hacker News + Jina Reader). GET /research?q=<topic>; pay per request in USDC on Base. Runs on any install, $0 source cost." },
  // deterministic compute primitives — pure CPU or free data, no LLM in the serving path.
  { path: "/compound-interest", price: "$0.001", example: "/compound-interest?principal=10000&rate=5&years=10&compoundsPerYear=12", what: "compound interest calc",
    description: "Compound interest calculator. GET /compound-interest?principal=10000&rate=5&years=10&compoundsPerYear=12 → final amount + interest earned. Deterministic JSON, instant." },
  { path: "/calc", price: "$0.001", example: "/calc?expr=(2%2B3)*4", what: "expression evaluator",
    description: "Arithmetic expression evaluator (+ - * / % ^ and parentheses). GET /calc?expr=(2%2B3)*4 → {result}. Deterministic JSON, instant, no code execution." },
  { path: "/json-flatten", price: "$0.001", example: "/json-flatten?json=<url-encoded JSON>", what: "flatten nested JSON",
    description: "Flatten nested JSON to dot-notation key/value pairs. GET /json-flatten?json=<url-encoded JSON> → flat object. Deterministic, instant." },
  { path: "/dns-lookup", price: "$0.001", example: "/dns-lookup?domain=example.com&type=A", what: "DNS records",
    description: "DNS lookup. GET /dns-lookup?domain=example.com&type=A|AAAA|MX|TXT|NS|CNAME|SOA → records as JSON. Live authoritative data, instant." },
  { path: "/whois", price: "$0.002", example: "/whois?domain=example.com", what: "WHOIS lookup",
    description: "WHOIS lookup with IANA referral follow. GET /whois?domain=example.com → registrar whois text as JSON. Live registry data." },
  { path: "/stock-quote", price: "$0.003", example: "/stock-quote?symbol=AAPL", what: "stock quote",
    description: "Real-time stock quote (price, currency, previous close, exchange). GET /stock-quote?symbol=AAPL → JSON. Free-source market data." },
  { path: "/funding-rates", price: "$0.003", example: "/funding-rates?symbol=BTC", what: "cross-exchange perp funding rates",
    description: "Perp funding rates across Binance/Bybit/Hyperliquid, normalized to 8h-equivalent, plus cross-exchange divergence (annualized bps, top20 arbitrage signal). GET /funding-rates or /funding-rates?symbol=BTC → JSON. Free-source, 60s cache." },
  { path: "/funding-rate-arb", price: "$0.003", example: "/funding-rate-arb?symbol=BTC", what: "pairwise funding-rate arbitrage signal",
    description: "Every distinct Binance/Bybit/Hyperliquid exchange-pair funding-rate spread per symbol (not just the single highest-vs-lowest pair), sorted by annualized bps divergence descending, with short(high-funding venue)/long(low-funding venue) direction per pair. GET /funding-rate-arb (top20 across all symbols) or /funding-rate-arb?symbol=BTC (all pairs for that symbol) → JSON. Pure arithmetic on the same cached data as /funding-rates, $0 marginal cost, 60s cache." },
];

// GET-with-query param schemas per route (moved above routes: also feeds the v1 compat body's
// outputSchema.input and the Bazaar declareDiscoveryExtension() call below). x402scan requires an
// input schema per operation or the route is "non-invocable" and skipped from registration — see
// x402scan.com/discovery/spec. Query params only (no request body: all our routes are GET).
const QUERY_PARAMS = {
  "/research": [{ name: "q", required: true, type: "string", description: "topic to research" }],
  "/compound-interest": [
    { name: "principal", required: true, type: "number" }, { name: "rate", required: true, type: "number" },
    { name: "years", required: true, type: "number" }, { name: "compoundsPerYear", required: false, type: "number" },
  ],
  "/calc": [{ name: "expr", required: true, type: "string", description: "arithmetic expression" }],
  "/json-flatten": [{ name: "json", required: true, type: "string", description: "URL-encoded JSON" }],
  "/dns-lookup": [{ name: "domain", required: true, type: "string" }, { name: "type", required: false, type: "string" }],
  "/whois": [{ name: "domain", required: true, type: "string" }],
  "/stock-quote": [{ name: "symbol", required: true, type: "string" }],
  "/funding-rates": [{ name: "symbol", required: false, type: "string" }],
  "/funding-rate-arb": [{ name: "symbol", required: false, type: "string", description: "base asset, e.g. BTC — filters to all exchange pairs for that symbol; omit for top20 across all symbols" }],
};
// concrete example input values per route (Bazaar discovery extension "input" field — a worked
// example, distinct from inputSchema's type constraints), mirrors PRODUCTS[].example.
const EXAMPLE_INPUT = {
  "/research": { q: "AI agents 2026" },
  "/compound-interest": { principal: 10000, rate: 5, years: 10, compoundsPerYear: 12 },
  "/calc": { expr: "(2+3)*4" },
  "/json-flatten": { json: "{\"a\":{\"b\":1}}" },
  "/dns-lookup": { domain: "example.com", type: "A" },
  "/whois": { domain: "example.com" },
  "/stock-quote": { symbol: "AAPL" },
  "/funding-rates": { symbol: "BTC" },
  "/funding-rate-arb": { symbol: "BTC" },
};

// per-route config: v2 RouteConfig.accepts[] (scheme/price/network/payTo/extra), replaces v1's flat
// {price,network,config}.
const USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";

// Task 4.5.A — v1 back-compat 402 body. v1 clients (x402-fetch@1, buyer-cdp.mjs) parse `accepts` out
// of the JSON body; v2's default unpaidResponseBody is {} (see comment above the imports), so without
// this a v1 buyer TypeErrors on `.map` of undefined and never pays. Mirrors the exact
// PaymentRequirementsV1 shape x402-express@1.2.0 itself builds (node_modules/x402-express/dist/cjs/
// index.js, the EVM branch) so v1 clients parse it identically.
function v1AcceptsFor(p) {
  const atomic = processPriceToAtomicAmount(p.price, NETWORK_V1);
  if ("error" in atomic) throw new Error(`v1 compat body: ${atomic.error} (route ${p.path})`);
  return [{
    scheme: "exact",
    network: NETWORK_V1,
    maxAmountRequired: atomic.maxAmountRequired,
    resource: PUBLIC_URL ? `${PUBLIC_URL}${p.path}` : p.path,
    description: p.description,
    mimeType: "application/json",
    payTo: payTo(),
    maxTimeoutSeconds: 60,
    asset: atomic.asset.address,
    outputSchema: { input: { type: "http", method: "GET", discoverable: true } },
    extra: atomic.asset.eip712,
  }];
}

// Task 4.5.B — Bazaar discovery extension. Replaces the plain `discoverable:true` flag (measured
// 1/8 products actually indexed by x402scan with that flag — docs/research/2026-07-17-x402-v1-v2-
// compat.md §"本番 seller の v1/v2 分布"). declareDiscoveryExtension() returns {bazaar:{info,schema}}
// for RouteConfig.extensions; paymentMiddleware auto-registers bazaarResourceServerExtension via
// checkIfBazaarNeeded() (see import comment above) — nothing else to wire.
const routes = Object.fromEntries(PRODUCTS.map((p) => [
  `GET ${p.path}`,
  {
    accepts: [{ scheme: "exact", price: p.price, network: NETWORK, payTo: payTo(), extra: { asset: USDC_BASE } }],
    description: p.description,
    mimeType: "application/json",
    unpaidResponseBody: () => ({
      contentType: "application/json",
      body: { x402Version: 1, error: "X-PAYMENT header is required", accepts: v1AcceptsFor(p) },
    }),
    ...(PUBLIC_URL ? {
      resource: `${PUBLIC_URL}${p.path}`,
      extensions: declareDiscoveryExtension({
        method: "GET",
        input: EXAMPLE_INPUT[p.path] || {},
        inputSchema: {
          properties: Object.fromEntries((QUERY_PARAMS[p.path] || []).map((q) => [q.name, { type: q.type, description: q.description }])),
          required: (QUERY_PARAMS[p.path] || []).filter((q) => q.required).map((q) => q.name),
        },
        output: { example: {} },
      }),
    } : {}),
  },
]));

// free discovery surfaces (mounted BEFORE the payment middleware so they are never paywalled):
// .well-known/x402.json manifest + llms.txt — how buyer agents and their crawlers find what's for sale.
app.get("/.well-known/x402.json", (_req, res) =>
  res.json({
    x402Version: 2,
    resources: PRODUCTS.map((p) => ({
      resource: PUBLIC_URL ? `${PUBLIC_URL}${p.path}` : p.path, method: "GET", price: p.price,
      network: NETWORK, payTo: payTo(), asset: USDC_BASE, description: p.description,
    })),
  }));
app.get("/llms.txt", (_req, res) =>
  res.type("text/plain").send([
    "# x402 paid API — pay-per-request in USDC on Base (HTTP 402 flow, no account, no API key)",
    `# payTo: ${payTo()}  |  manifest: ${PUBLIC_URL || ""}/.well-known/x402.json`,
    "",
    ...PRODUCTS.map((p) => `GET ${PUBLIC_URL || ""}${p.example}  (${p.price}) — ${p.description}`),
  ].join("\n")));

// (QUERY_PARAMS now defined earlier, above `routes`, so the v1 compat body + Bazaar extension can use it too)
// Discovery spec (x402scan.com/discovery/spec): canonical machine-readable contract for buyer
// agents; also required to pass SIWX-gated registration (POST /api/x402/registry/register-origin).
app.get("/openapi.json", (_req, res) =>
  res.json({
    openapi: "3.1.0",
    info: {
      title: "Anicca x402 seller", version: "1",
      "x-guidance": "Deterministic pay-per-call primitives + web research, priced in USDC on Base via x402. GET each path with its query params; a 402 challenge carries the payment requirements, pay it, retry with X-PAYMENT.",
    },
    paths: Object.fromEntries(PRODUCTS.map((p) => [p.path, {
      get: {
        operationId: p.path.slice(1).replace(/-([a-z])/g, (_, c) => c.toUpperCase()),
        summary: p.what, description: p.description,
        parameters: (QUERY_PARAMS[p.path] || []).map((q) => ({
          name: q.name, in: "query", required: q.required, description: q.description,
          schema: { type: q.type },
        })),
        "x-payment-info": { price: { mode: "fixed", currency: "USD", amount: p.price.replace("$", "") }, protocols: [{ x402: {} }] },
        responses: { 200: { description: "OK" }, 402: { description: "Payment Required" } },
      },
    }])),
  }));

app.use(paymentMiddleware(routes, resourceServer));

// sales log — INV-SETTLE: a request is only a SALE once settle() succeeds on-chain, never on
// verify alone. v2 (@x402/express@2.17.0, node_modules/@x402/core dist/cjs/http/index.js) sets the
// PAYMENT-RESPONSE header on settle SUCCESS *and* on settle FAILURE (v2.6+ regression vs v1 — a bare
// header-presence check is a false positive here, FIX-3 re-triggered). isSettled()/decodePayer()
// (lib/settle-gate.mjs) base64-decode the header and gate on SettleResponse.success===true — the only
// correct settle signal, read at the res 'finish' event (after the real response left the process).
// Requests that clear verify but never settle still carry a real demand signal, so they go to
// attempts-<wallet>.jsonl instead of being silently dropped.
import { appendFileSync, mkdirSync } from "node:fs";
import { join, dirname as pdirname } from "node:path";
const STATE_DIR = join(pdirname(new URL(import.meta.url).pathname), "state");
const SALES_LOG = process.env.X402_SALES_LOG || join(STATE_DIR, `sales-${payTo().toLowerCase()}.jsonl`);
const ATTEMPTS_LOG = process.env.X402_ATTEMPTS_LOG || join(STATE_DIR, `attempts-${payTo().toLowerCase()}.jsonl`);
try { mkdirSync(STATE_DIR, { recursive: true }); } catch { /* best-effort */ }
app.use((req, res, next) => {
  const product = PRODUCTS.find((p) => p.path === req.path);
  if (!product) return next();
  let payer = null;
  try {
    const xp = JSON.parse(Buffer.from(req.header("x-payment") || "", "base64").toString("utf8"));
    payer = xp?.payload?.authorization?.from || null;
  } catch { /* header absent/opaque — payer stays null, never blocks logging */ }
  res.on("finish", () => {
    const hdr = res.getHeader("PAYMENT-RESPONSE");
    const settled = isSettled(hdr);
    const settledPayer = payer || decodePayer(hdr);
    const line = JSON.stringify({ ts: new Date().toISOString(), route: req.path, price: product.price, payer: settledPayer, settled }) + "\n";
    try { appendFileSync(settled ? SALES_LOG : ATTEMPTS_LOG, line); } catch { /* logging must never break serving */ }
  });
  next();
});

// the paid endpoint: runs the product command with the buyer's query, returns the result.
app.get("/research", (req, res) => {
  const q = String(req.query.q || "").slice(0, 500);
  if (!q) return res.status(400).json({ error: "pass ?q=<what to research>" });
  const parts = PRODUCT_CMD.replace("{q}", JSON.stringify(q)).split(" ");
  execFile(parts[0], parts.slice(1), { timeout: 90_000, maxBuffer: 4 << 20 }, (err, stdout) => {
    if (err) return res.status(502).json({ error: "product failed", detail: String(err).slice(0, 200) });
    res.json({ query: q, result: stdout.slice(0, 200_000), paidTo: payTo(), price: PRICE });
  });
});

// primitive handlers: payment middleware above already gated them; here is pure compute.
const answer = (res, fn) =>
  Promise.resolve().then(fn).then((out) => res.json(out))
    .catch((e) => res.status(422).json({ error: String(e && e.message || e).slice(0, 200) }));

app.get("/compound-interest", (req, res) => answer(res, () => compoundInterest(req.query)));
app.get("/calc", (req, res) => answer(res, () => calcEval(String(req.query.expr || ""))));
app.get("/json-flatten", (req, res) => answer(res, () => flattenJson(JSON.parse(String(req.query.json || "")))));
app.get("/dns-lookup", (req, res) => answer(res, () => dnsLookup(String(req.query.domain || ""), String(req.query.type || "A"))));
app.get("/whois", (req, res) => answer(res, () => whois(String(req.query.domain || ""))));
app.get("/stock-quote", (req, res) => answer(res, () => stockQuote(String(req.query.symbol || ""))));

// funding-rates: unlike the other primitives, "failure" has two distinct meanings — a single
// exchange dying should DEGRADE (still serve the other exchanges, 200 + degraded:true), only ALL
// THREE dying is a real outage (503). getFundingRatesCached() throws only in that all-dead case.
app.get("/funding-rates", (req, res) => {
  getFundingRatesCached()
    .then(({ rows, errors }) => res.json(buildFundingRatesResponse(rows, { symbol: req.query.symbol, errors })))
    .catch((e) => res.status(503).json({ error: "all upstream exchanges unavailable", detail: String(e && e.message || e).slice(0, 300) }));
});

// funding-rate-arb: same degrade-not-fail contract as /funding-rates (shares the same cache — no
// extra upstream load), pure pairwise arithmetic on top.
app.get("/funding-rate-arb", (req, res) => {
  getFundingRatesCached()
    .then(({ rows, errors }) => res.json(buildFundingRateArbResponse(rows, annualizedBps, { symbol: req.query.symbol, errors })))
    .catch((e) => res.status(503).json({ error: "all upstream exchanges unavailable", detail: String(e && e.message || e).slice(0, 300) }));
});

// free: tells a buyer what's for sale + the price (so demand can find it).
app.get("/", (_req, res) =>
  res.json({
    products: PRODUCTS.map((p) => ({ path: p.example, price: p.price, what: p.what })),
    manifest: "/.well-known/x402.json", llms: "/llms.txt",
    pay: "x402 — pay per request in USDC on " + NETWORK, payTo: payTo(),
  }));

const server = app.listen(PORT, () =>
  console.log(JSON.stringify({ x402_seller: "up", port: PORT, price: PRICE, network: NETWORK, payTo: payTo() })));

// Without this, losing the port race printed "up" and exited 0 — so run.sh's UP check, the ledger
// narrate, and launchd's exit code all read a dead seller as a healthy one, and KeepAlive respawned
// it 364 times without ever flagging a fault. A seller that cannot bind must say so and exit nonzero.
server.on("error", (err) => {
  console.error(JSON.stringify({ x402_seller: "failed", port: PORT, error: err.code || String(err) }));
  process.exit(1);
});
