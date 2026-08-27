// mcp-server.mjs — DIST-1: expose the franklin x402 shop as a MonetizedMCP server so buyer
// agents on Fluora / MCPay can discover + purchase the products. This is a THIN protocol
// translator: it does NOT settle payments itself. The buyer's signed x402 payment
// (MakePurchaseRequest.signedTransaction == the x402 `X-PAYMENT` header) is forwarded verbatim
// to the already-running serve-v2 HTTP route, whose existing @x402/express paymentMiddleware
// verifies + settles it to X402_PAYTO and serves the product in one shot.
//
// Why this shape:
//  - serve-v2.mjs is UNCHANGED (invariant #1). All payment logic stays in its real x402 path.
//  - Payment happens EXACTLY once (in serve-v2). No second settlement here => no double-payment.
//  - INV-EXT holds: the settle is a real buyer->X402_PAYTO tx on Base; verify-inflow's self-tx
//    exclusion still classifies self-pay as $0.
//
// Source of truth for product metadata = serve-v2.mjs PRODUCTS (CORE_PATHS) + resale.mjs
// RESALE_PRODUCTS. Keep the 4 entries below in sync with those (prices/params).
//
// Env:
//   X402_PAYTO         seller wallet (same as serve-v2) — advertised in payment-methods
//   X402_PORT          port serve-v2 listens on (default 8403) — where purchases are fulfilled
//   X402_PUBLIC_URL    public https base serve-v2 advertises (used as the x402 `resource`)
//   PORT               port THIS MCP server listens on (default 8080), path /mcp
//   MCP_UPSTREAM_ORIGIN  optional override for the serve-v2 origin (default http://127.0.0.1:$X402_PORT)

import { MonetizedMCPServer, PaymentMethods } from "monetizedmcp-sdk";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { isInitializeRequest } from "@modelcontextprotocol/sdk/types.js";
import express from "express";
import { randomUUID } from "node:crypto";

const PAYTO = process.env.X402_PAYTO || "";
const SERVE_PORT = Number(process.env.X402_PORT || 8403);
const UPSTREAM_ORIGIN =
  process.env.MCP_UPSTREAM_ORIGIN || `http://127.0.0.1:${SERVE_PORT}`;

// The 4 concentrated CORE products (mirror serve-v2 CORE_PATHS). `amount` is USDC (dollars).
// `params` documents the accepted query params for buyers; `required` is enforced before forward.
const PRODUCTS = [
  {
    id: "web-search",
    path: "/web-search",
    amount: 0.014,
    name: "Live web search (Exa resale)",
    description:
      "Live web search results via the Exa API, paid per call by this store's own wallet over x402 so the buyer needs no Exa account or API key. numResults 1..5.",
    params: [
      { name: "q", required: true, type: "string", description: "search query" },
      { name: "numResults", required: false, type: "number", description: "1..5, default 3" },
    ],
  },
  {
    id: "funding-rates",
    path: "/funding-rates",
    amount: 0.003,
    name: "Cross-exchange perp funding rates",
    description:
      "Perp funding rates across Binance/Bybit/Hyperliquid normalized to 8h-equivalent, plus cross-exchange divergence (annualized bps, top20 arbitrage signal). Omit symbol for top20.",
    params: [{ name: "symbol", required: false, type: "string", description: "e.g. BTC; omit for top20" }],
  },
  {
    id: "funding-rate-arb",
    path: "/funding-rate-arb",
    amount: 0.003,
    name: "Pairwise funding-rate arbitrage signal",
    description:
      "Every distinct Binance/Bybit/Hyperliquid exchange-pair funding-rate spread per symbol, sorted by annualized bps divergence, with short(high)/long(low) direction per pair. Omit symbol for top20 across all symbols.",
    params: [{ name: "symbol", required: false, type: "string", description: "e.g. BTC; omit for top20" }],
  },
  {
    id: "research",
    path: "/research",
    amount: 0.003,
    name: "On-demand web research digest",
    description:
      "On-demand web research digest — free-source curated (Wikipedia + Hacker News + Jina Reader). Pay per request in USDC on Base.",
    params: [{ name: "q", required: true, type: "string", description: "topic to research" }],
  },
];

const BY_ID = new Map(PRODUCTS.map((p) => [p.id, p]));

// Build a safe querystring from caller params, restricted to the product's declared params.
function buildQuery(product, params) {
  const usp = new URLSearchParams();
  const given = params && typeof params === "object" ? params : {};
  for (const spec of product.params) {
    const v = given[spec.name];
    if (v === undefined || v === null || v === "") {
      if (spec.required) throw new Error(`missing required param: ${spec.name}`);
      continue;
    }
    usp.set(spec.name, String(v));
  }
  const qs = usp.toString();
  return qs ? `?${qs}` : "";
}

class AniccaShopMCP extends MonetizedMCPServer {
  async priceListing({ searchQuery } = {}) {
    const q = (searchQuery || "").toLowerCase().trim();
    const items = PRODUCTS.filter(
      (p) =>
        !q ||
        p.id.includes(q) ||
        p.name.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q)
    ).map((p) => ({
      id: p.id,
      name: p.name,
      description: p.description,
      price: { amount: p.amount, paymentMethod: PaymentMethods.USDC_BASE_MAINNET },
      params: Object.fromEntries(
        p.params.map((s) => [s.name, { type: s.type, required: !!s.required, description: s.description }])
      ),
    }));
    return { items };
  }

  async paymentMethods() {
    return [{ walletAddress: PAYTO, paymentMethod: PaymentMethods.USDC_BASE_MAINNET }];
  }

  async makePurchase({ itemId, params, signedTransaction, paymentMethod }) {
    const req = { itemId, params, signedTransaction, paymentMethod };
    const product = BY_ID.get(itemId);
    if (!product) {
      return {
        purchasableItemId: itemId,
        makePurchaseRequest: req,
        orderId: "",
        toolResult: JSON.stringify({ error: `unknown itemId: ${itemId}` }),
      };
    }
    let qs;
    try {
      qs = buildQuery(product, params);
    } catch (e) {
      return {
        purchasableItemId: itemId,
        makePurchaseRequest: req,
        orderId: "",
        toolResult: JSON.stringify({ error: String(e.message || e) }),
      };
    }

    const url = `${UPSTREAM_ORIGIN}${product.path}${qs}`;
    // Forward the buyer's x402 payment header verbatim. serve-v2's paymentMiddleware
    // verifies + settles it to X402_PAYTO, then serves the product. One settlement, upstream.
    let res, text;
    try {
      res = await fetch(url, {
        method: "GET",
        headers: signedTransaction ? { "X-PAYMENT": signedTransaction } : {},
      });
      text = await res.text();
    } catch (e) {
      return {
        purchasableItemId: itemId,
        makePurchaseRequest: req,
        orderId: "",
        toolResult: JSON.stringify({ error: `upstream unreachable: ${String(e.message || e)}` }),
      };
    }

    if (!res.ok) {
      // 402 (no/invalid payment) or upstream error — surface it so the buyer can pay + retry.
      return {
        purchasableItemId: itemId,
        makePurchaseRequest: req,
        orderId: "",
        toolResult: JSON.stringify({ status: res.status, body: safeJson(text) }),
      };
    }

    // Settlement receipt (if serve-v2 echoed one) doubles as the order id.
    const settleReceipt = res.headers.get("x-payment-response") || res.headers.get("x-payment") || "";
    return {
      purchasableItemId: itemId,
      makePurchaseRequest: req,
      orderId: settleReceipt || `${product.id}-${res.headers.get("date") || ""}`.trim(),
      toolResult: text,
    };
  }
}

function safeJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

// monetizedmcp-sdk@0.1.23 keeps one McpServer instance for every HTTP session. The official
// MCP SDK permits a Server to connect only once, so the second registry/buyer session crashes
// that runner. Follow the SDK's sessionful HTTP example: create a fresh server per initialized
// transport while keeping subsequent requests on the same transport.
function startMcpServer() {
  const app = express();
  const transports = new Map();
  app.use(express.json());

  app.post("/mcp", async (req, res) => {
    const sessionId = req.headers["mcp-session-id"];
    let transport = sessionId ? transports.get(sessionId) : undefined;

    if (!transport && !sessionId && isInitializeRequest(req.body)) {
      transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: () => randomUUID(),
        onsessioninitialized: (initializedSessionId) => {
          transports.set(initializedSessionId, transport);
        },
      });
      transport.onclose = () => {
        if (transport.sessionId) transports.delete(transport.sessionId);
      };
      const shop = new AniccaShopMCP();
      await shop.server.connect(transport);
    } else if (!transport) {
      res.status(400).json({
        jsonrpc: "2.0",
        error: { code: -32000, message: "Bad Request: No valid session ID provided" },
        id: null,
      });
      return;
    }

    await transport.handleRequest(req, res, req.body);
  });

  const handleSessionRequest = async (req, res) => {
    const sessionId = req.headers["mcp-session-id"];
    const transport = sessionId ? transports.get(sessionId) : undefined;
    if (!transport) {
      res.status(400).send("Invalid or missing session ID");
      return;
    }
    await transport.handleRequest(req, res);
  };

  app.get("/mcp", handleSessionRequest);
  app.delete("/mcp", handleSessionRequest);
  const port = Number(process.env.PORT || 8080);
  app.listen(port, () => console.log(`MCP Server listening on port ${port}`));
}

startMcpServer();
