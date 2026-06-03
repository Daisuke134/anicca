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
function challenge402(c: import("hono").Context, routeId: RouteId, reason?: string) {
  const ch = buildChallenge(routeId);
  c.header("WWW-Authenticate", `x402 route_id="${routeId}", price="${ch.price_usdc} USDC", receiver="${ch.receiver}", nonce="${ch.nonce}"`);
  return c.json(
    {
      type: "https://x402.org/challenge",
      status: 402,
      title: "Payment Required",
      detail: reason ?? `This route costs ${ch.price_usdc} USDC. Send on Base and retry with x-paid-tx-hash.`,
      challenge: ch,
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
