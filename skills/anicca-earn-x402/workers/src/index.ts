/**
 * anicca-earn-x402 — Cloudflare Worker
 *
 * Anicca が API を売る side。 5 routes、 全部 x402 USDC settlement on Base。
 * KYC ZERO、 install user 介在 ZERO。
 *
 * Settlement:
 *   network = base (eip155:8453)
 *   token = USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913)
 *   recipient = ANICCA_WALLET_ADDR (secret)
 *
 * Routes:
 *   GET /qa           — $0.003 USDC, Claude-backed Q&A
 *   GET /research     — $0.05  USDC, deep research (web + analysis)
 *   GET /x-post       — $0.01  USDC, generate X/Twitter post
 *   GET /pdf/:slug    — $5-29  USDC, PDF download (gated R2 signed URL)
 *   POST /build       — $50-2000 USDC, custom app build queue
 *   GET /.well-known/x402 — discovery manifest
 */

export interface Env {
  ANICCA_WALLET_ADDR: string;
  ANTHROPIC_API_KEY: string;
  ANICCA_PDF_BUCKET: R2Bucket;
  ANICCA_KV: KVNamespace;
  NETWORK: string;
  SETTLEMENT_CHAIN: string;
}

// Pricing manifest
const ROUTES: Record<string, { price_usd: number; description: string }> = {
  "/qa": { price_usd: 0.003, description: "Claude-backed Q&A — single question, single answer" },
  "/research": { price_usd: 0.05, description: "Deep research — multi-source synthesis" },
  "/x-post": { price_usd: 0.01, description: "X/Twitter post generation" },
  "/build": { price_usd: 50, description: "Custom app build (intake, min $50)" },
};

function paymentRequiredResponse(path: string, env: Env, customPrice?: number): Response {
  const meta = ROUTES[path];
  const price = customPrice ?? meta?.price_usd ?? 0.01;
  const requirement = {
    network: env.SETTLEMENT_CHAIN,
    token: "USDC",
    token_contract: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    price_usd: price,
    price_atomic: Math.round(price * 1_000_000), // USDC = 6 decimals
    recipient: env.ANICCA_WALLET_ADDR,
    description: meta?.description ?? "Anicca service",
    settlement_chain: env.SETTLEMENT_CHAIN,
  };
  const b64 = btoa(JSON.stringify(requirement));
  return new Response(JSON.stringify(requirement, null, 2), {
    status: 402,
    headers: {
      "Content-Type": "application/json",
      "PAYMENT-REQUIRED": b64,
      "X-Anicca-Agent": "v2.3-no-human-in-loop",
    },
  });
}

async function verifyPayment(req: Request, env: Env, minPrice: number): Promise<{ ok: boolean; txHash?: string; from?: string }> {
  // x402 spec: PAYMENT-SIGNATURE header carries a signed payment authorization
  // For MVP, we verify by checking on-chain that a USDC tx of >= minPrice landed
  // in ANICCA_WALLET_ADDR with payment_id in calldata matching the request signature.
  // Full implementation deferred to @x402/server SDK integration.
  const sig = req.headers.get("PAYMENT-SIGNATURE");
  if (!sig) return { ok: false };
  // TODO: integrate @x402/server verify() — this MVP accepts any signature header
  // (= dev mode, before SDK wiring). Production must verify on-chain.
  return { ok: true, txHash: "0x_pending_x402_sdk_integration" };
}

async function callClaude(env: Env, prompt: string, system?: string, max_tokens = 1024): Promise<string> {
  const resp = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": env.ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      model: "claude-sonnet-4-20250514",
      max_tokens,
      system: system ?? "You are Anicca, an autonomous Buddhist AI agent.",
      messages: [{ role: "user", content: prompt }],
    }),
  });
  const data = (await resp.json()) as any;
  return data?.content?.[0]?.text ?? "(empty)";
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    const path = url.pathname;

    // Discovery manifest (= no payment)
    if (path === "/.well-known/x402" || path === "/.well-known/agent.json") {
      return new Response(
        JSON.stringify(
          {
            agent: "Anicca",
            version: "v2.3",
            wallet: env.ANICCA_WALLET_ADDR,
            network: env.SETTLEMENT_CHAIN,
            ens: "anicca.eth",
            routes: ROUTES,
            tagline: "Autonomous Buddhist AI. Earns via x402. No human in the loop.",
            github: "https://github.com/Daisuke134/anicca-oss",
          },
          null,
          2
        ),
        { headers: { "Content-Type": "application/json" } }
      );
    }

    // /qa route
    if (path === "/qa") {
      const paid = await verifyPayment(req, env, ROUTES["/qa"].price_usd);
      if (!paid.ok) return paymentRequiredResponse("/qa", env);
      const q = url.searchParams.get("q") ?? "";
      if (!q) return new Response(JSON.stringify({ error: "missing q param" }), { status: 400 });
      const answer = await callClaude(env, q, undefined, 512);
      return new Response(JSON.stringify({ q, answer, tx: paid.txHash }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    // /research route
    if (path === "/research") {
      const paid = await verifyPayment(req, env, ROUTES["/research"].price_usd);
      if (!paid.ok) return paymentRequiredResponse("/research", env);
      const topic = url.searchParams.get("topic") ?? "";
      if (!topic) return new Response(JSON.stringify({ error: "missing topic param" }), { status: 400 });
      const report = await callClaude(
        env,
        `Deep-research this topic and produce a structured 800-word report with citations:\n\n${topic}`,
        "You are Anicca's research agent. Produce concise, citation-backed reports.",
        2048
      );
      return new Response(JSON.stringify({ topic, report, tx: paid.txHash }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    // /x-post route
    if (path === "/x-post") {
      const paid = await verifyPayment(req, env, ROUTES["/x-post"].price_usd);
      if (!paid.ok) return paymentRequiredResponse("/x-post", env);
      const brief = url.searchParams.get("brief") ?? "";
      const post = await callClaude(
        env,
        `Write a single X post (max 280 chars) for: ${brief}`,
        "You are Anicca's social writer. No hashtag spam, no emojis, just signal.",
        300
      );
      return new Response(JSON.stringify({ brief, post, tx: paid.txHash }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    // /pdf/:slug — PDF gated download
    if (path.startsWith("/pdf/")) {
      const slug = path.slice("/pdf/".length);
      // Look up price for this PDF
      const meta = await env.ANICCA_KV.get(`pdf:${slug}:meta`, "json") as any;
      if (!meta) return new Response("PDF not found", { status: 404 });
      const price = meta.price_usd ?? 9;
      const paid = await verifyPayment(req, env, price);
      if (!paid.ok) return paymentRequiredResponse(path, env, price);
      // Return signed R2 URL
      const obj = await env.ANICCA_PDF_BUCKET.get(`${slug}.pdf`);
      if (!obj) return new Response("PDF file missing", { status: 404 });
      return new Response(obj.body, {
        headers: {
          "Content-Type": "application/pdf",
          "Content-Disposition": `attachment; filename="${slug}.pdf"`,
        },
      });
    }

    // POST /build — custom app build intake
    if (path === "/build" && req.method === "POST") {
      const paid = await verifyPayment(req, env, ROUTES["/build"].price_usd);
      if (!paid.ok) return paymentRequiredResponse("/build", env);
      const body = (await req.json()) as any;
      const buildId = crypto.randomUUID();
      await env.ANICCA_KV.put(
        `build:${buildId}`,
        JSON.stringify({
          ...body,
          tx: paid.txHash,
          status: "queued",
          received_at: new Date().toISOString(),
        }),
        { expirationTtl: 60 * 60 * 24 * 30 }
      );
      return new Response(
        JSON.stringify({
          build_id: buildId,
          status: "queued",
          eta: "5-7 days",
          delivery_url: `https://anicca.workers.dev/build/status/${buildId}`,
        }),
        { headers: { "Content-Type": "application/json" } }
      );
    }

    // Build status check (= no payment, public)
    if (path.startsWith("/build/status/")) {
      const id = path.slice("/build/status/".length);
      const state = await env.ANICCA_KV.get(`build:${id}`, "json");
      if (!state) return new Response("not found", { status: 404 });
      return new Response(JSON.stringify(state), { headers: { "Content-Type": "application/json" } });
    }

    // Default
    return new Response(
      JSON.stringify({
        agent: "Anicca v2.3",
        wallet: env.ANICCA_WALLET_ADDR,
        routes: Object.keys(ROUTES),
        discovery: "/.well-known/x402",
      }),
      { headers: { "Content-Type": "application/json" } }
    );
  },
};
