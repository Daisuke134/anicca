// Anicca's x402 endpoint (Wave 1 minimal viable).
// Spec 09 § 2 T2-T5. Listens on :8403 (NOT :8402 — collision with OpenClaw gateway).
//
// Routes:
//   GET  /health
//   GET  /v0/echo?text=<...>   price 0.001 USDC
//   POST /v0/learn             price 0.01  USDC
//
// Flow:
//   1. First call (no x-paid-tx-hash) → 402 + challenge JSON.
//   2. Buyer sends USDC on Base to receiver, then re-requests with x-paid-tx-hash header.
//   3. Server verifies tx via viem (Base mainnet RPC) and returns content.

import { Hono } from "hono";
import { serve } from "@hono/node-server";
import { buildChallenge, getReceiver, getRoutePrice, type RouteId } from "./challenge.ts";
import { verifyUsdcPayment } from "./verify.ts";

const PORT = Number(process.env.PORT ?? 8403);
const app = new Hono();

// --- Health -----------------------------------------------------------------
app.get("/health", (c) =>
  c.json({
    ok: true,
    service: "anicca-x402-endpoint",
    version: "0.1.0",
    port: PORT,
    receiver: getReceiver(),
    routes: ["/v0/echo", "/v0/learn"],
    timestamp: new Date().toISOString(),
  })
);

// --- Helper: 402 challenge response -----------------------------------------
// Body carries BOTH (a) Anicca's custom `challenge` object (human-readable, HMAC-signed nonce)
// AND (b) the canonical x402 v2 PaymentRequiredResponse + Bazaar extension fields so this
// endpoint is discoverable by Bazaar-compatible facilitators (Coinbase x402 facilitator etc.).
// Schema refs:
//   https://github.com/x402-foundation/x402/blob/main/docs/extensions/bazaar.mdx
//   https://api.agentic.market/v1/validate/run (live validator)
const USDC_DECIMAL_DIVISOR = 1_000_000;
const ROUTE_TIMEOUT_SECONDS = 600;

const ROUTE_META: Record<RouteId, {
  method: "GET" | "POST";
  path: string;
  description: string;
  outputExample: Record<string, unknown>;
  inputExample: Record<string, unknown>;
}> = {
  echo: {
    method: "GET",
    path: "/v0/echo",
    description: "Echoes the supplied text after USDC payment. Cheapest route; proves the loop.",
    inputExample: { text: "hello" },
    outputExample: {
      ok: true,
      route: "echo",
      echoed: "hello",
      paid: {
        tx_hash: "0x…",
        from: "0x…",
        to: "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21",
        value_usdc: 0.001,
      },
      served_at: "2026-06-03T00:00:00.000Z",
    },
  },
  learn: {
    method: "POST",
    path: "/v0/learn",
    description: "Returns Anicca's FTS5-indexed lesson for a given topic.",
    inputExample: { topic: "compounding" },
    outputExample: {
      ok: true,
      route: "learn",
      topic: "compounding",
      lesson: {
        summary: "Anicca's lesson for compounding…",
        links: [],
      },
      paid: { tx_hash: "0x…", from: "0x…", to: "0xa3CDd…", value_usdc: 0.01 },
      served_at: "2026-06-03T00:00:00.000Z",
    },
  },
  draft: {
    method: "POST",
    path: "/v0/draft",
    description: "Gig-reply draft using project context + relationships.",
    inputExample: { gig_id: "5549226" },
    outputExample: { ok: true, draft: "…" },
  },
  call: {
    method: "POST",
    path: "/v0/call",
    description: "Bland.ai outbound voice call (~30 s).",
    inputExample: { phone: "phone-ref", topic: "lateness check" },
    outputExample: { ok: true, call_id: "…" },
  },
};

// JSON Schema (Draft 2020-12) for the Bazaar discovery info. Mirrors the shape of
// `extensions.bazaar.info` so the facilitator can validate that the endpoint's
// declared interface matches expectations.
const BAZAAR_SCHEMA = {
  $schema: "https://json-schema.org/draft/2020-12/schema",
  type: "object",
  properties: {
    input: {
      type: "object",
      additionalProperties: false,
      properties: {
        type: { const: "http", type: "string" },
        method: { enum: ["GET", "POST"], type: "string" },
        queryParams: { type: "object", additionalProperties: true },
      },
      required: ["type", "method"],
    },
    output: {
      type: "object",
      additionalProperties: false,
      properties: {
        type: { const: "json", type: "string" },
        example: { type: "object", additionalProperties: true },
      },
      required: ["type", "example"],
    },
  },
  required: ["input", "output"],
};

function publicBaseUrl(c: import("hono").Context): string {
  const env = process.env.X402_PUBLIC_BASE_URL;
  if (env) return env.replace(/\/$/, "");
  const xfHost = c.req.header("x-forwarded-host");
  const xfProto = c.req.header("x-forwarded-proto");
  if (xfHost) return `${xfProto ?? "https"}://${xfHost}`;
  const host = c.req.header("host") ?? `localhost:${PORT}`;
  const proto = host.startsWith("localhost") ? "http" : "https";
  return `${proto}://${host}`;
}

function challenge402(c: import("hono").Context, routeId: RouteId, reason?: string) {
  const ch = buildChallenge(routeId);
  const meta = ROUTE_META[routeId];
  const amountBaseUnits = Math.round(ch.price_usdc * USDC_DECIMAL_DIVISOR).toString();
  const resourceUrl = `${publicBaseUrl(c)}${meta.path}`;
  c.header(
    "WWW-Authenticate",
    `x402 route_id="${routeId}", price="${ch.price_usdc} USDC", receiver="${ch.receiver}", nonce="${ch.nonce}"`
  );
  // Validator only allows {type, method, queryParams} keys in bazaar.info.input.
  // For POST we keep queryParams empty (the example body lives under output.example only).
  const input: Record<string, unknown> = {
    type: "http",
    method: meta.method,
    queryParams: meta.method === "GET" ? meta.inputExample : {},
  };
  return c.json(
    {
      // Anicca-native fields
      type: "https://x402.org/challenge",
      status: 402,
      title: "Payment Required",
      detail: reason ?? `This route costs ${ch.price_usdc} USDC. Send on Base and retry with x-paid-tx-hash.`,
      challenge: ch,
      // Canonical x402 v2 PaymentRequiredResponse + Bazaar extension (validator-clean per
      // https://api.agentic.market/v1/validate/run)
      x402Version: 2,
      resource: { url: resourceUrl, type: "http", method: meta.method, description: meta.description },
      accepts: [
        {
          scheme: "exact",
          network: "eip155:8453",
          asset: ch.asset,
          extra: { name: "USD Coin", version: "2" },
          amount: amountBaseUnits,
          maxTimeoutSeconds: ROUTE_TIMEOUT_SECONDS,
          payTo: ch.receiver,
        },
      ],
      extensions: {
        bazaar: {
          info: {
            input,
            output: { type: "json", example: meta.outputExample },
          },
          schema: BAZAAR_SCHEMA,
        },
      },
    },
    402
  );
}

// --- /v0/echo ---------------------------------------------------------------
app.get("/v0/echo", async (c) => {
  const text = c.req.query("text") ?? "";
  const txHash = c.req.header("x-paid-tx-hash");

  if (!txHash) {
    return challenge402(c, "echo");
  }

  const result = await verifyUsdcPayment({
    txHash,
    expectedReceiver: getReceiver(),
    minUsdc: getRoutePrice("echo"),
  });

  if (!result.ok) {
    return challenge402(c, "echo", `payment verification failed: ${result.reason}`);
  }

  // Emit a single-line REVENUE marker for the monitor.sh tailer to forward to Slack #metrics.
  // eslint-disable-next-line no-console
  console.log(
    `REVENUE route=echo value_usdc=${result.valueUsdc} tx=${result.txHash} from=${result.from} block=${result.blockNumber.toString()} at=${new Date().toISOString()}`
  );
  return c.json({
    ok: true,
    route: "echo",
    echoed: text,
    paid: {
      tx_hash: result.txHash,
      from: result.from,
      to: result.to,
      value_usdc: result.valueUsdc,
      block: result.blockNumber.toString(),
    },
    served_at: new Date().toISOString(),
  });
});

// --- /v0/learn --------------------------------------------------------------
app.post("/v0/learn", async (c) => {
  const txHash = c.req.header("x-paid-tx-hash");

  if (!txHash) {
    return challenge402(c, "learn");
  }

  const result = await verifyUsdcPayment({
    txHash,
    expectedReceiver: getReceiver(),
    minUsdc: getRoutePrice("learn"),
  });

  if (!result.ok) {
    return challenge402(c, "learn", `payment verification failed: ${result.reason}`);
  }

  let topic = "";
  try {
    const body = await c.req.json<{ topic?: string }>();
    topic = (body?.topic ?? "").toString();
  } catch {
    topic = c.req.query("topic") ?? "";
  }

  // Emit revenue marker for monitor.
  // eslint-disable-next-line no-console
  console.log(
    `REVENUE route=learn topic="${topic.replace(/"/g, "\\\"")}" value_usdc=${result.valueUsdc} tx=${result.txHash} from=${result.from} block=${result.blockNumber.toString()} at=${new Date().toISOString()}`
  );
  // Wave 1: minimal lesson payload. Real FTS5 lookup lands in T5/T8.
  return c.json({
    ok: true,
    route: "learn",
    topic,
    lesson: {
      summary: `Anicca's lesson for "${topic}" is being assembled. Wave 1 returns the receipt; full FTS5 retrieval lands in subsequent task.`,
      links: [],
    },
    paid: {
      tx_hash: result.txHash,
      from: result.from,
      to: result.to,
      value_usdc: result.valueUsdc,
      block: result.blockNumber.toString(),
    },
    served_at: new Date().toISOString(),
  });
});

// --- 404 fallback -----------------------------------------------------------
app.notFound((c) =>
  c.json(
    {
      ok: false,
      error: "not_found",
      hint: "Try GET /health, GET /v0/echo?text=hi, or POST /v0/learn.",
    },
    404
  )
);

// --- Boot --------------------------------------------------------------------
serve({ fetch: app.fetch, port: PORT, hostname: "0.0.0.0" });
// eslint-disable-next-line no-console
console.log(`[anicca-x402] listening on :${PORT} — receiver ${getReceiver()}`);
