// Anicca x402 endpoint — multi-LLM fallback (DeepSeek primary, OpenAI fallback, Anthropic optional)

const ROUTES = {
  qa:        { price_usd: 0.003, description: "Claude-backed Q&A — single question, single answer" },
  research:  { price_usd: 0.05,  description: "Deep research — multi-source synthesis" },
  "x-post":  { price_usd: 0.01,  description: "X / Farcaster post generation" },
  build:     { price_usd: 50,    description: "Custom app build queue (min $50)" },
};

function paymentRequired(routeKey, customPrice) {
  const meta = ROUTES[routeKey];
  const price = customPrice ?? meta?.price_usd ?? 0.01;
  const wallet = process.env.ANICCA_WALLET_ADDR || "0x9B1Ee988b1A2931ABCE467f0a8eAff6c70c93e83";
  const requirement = {
    network: "eip155:8453", token: "USDC",
    token_contract: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    price_usd: price, price_atomic: Math.round(price * 1_000_000),
    recipient: wallet,
    description: meta?.description ?? "Anicca service",
    settlement_chain: "eip155:8453",
  };
  return {
    statusCode: 402,
    headers: {
      "Content-Type": "application/json",
      "PAYMENT-REQUIRED": Buffer.from(JSON.stringify(requirement)).toString("base64"),
      "X-Anicca-Agent": "v2.3-no-human-in-loop",
    },
    body: JSON.stringify(requirement, null, 2),
  };
}

async function callLLM(prompt, system, max_tokens = 1024) {
  const anthKey = process.env.ANTHROPIC_API_KEY;
  const deepseekKey = process.env.DEEPSEEK_API_KEY;
  const openaiKey = process.env.OPENAI_API_KEY;

  // Try DeepSeek first (cheapest, $0.27/1M tokens output, fast)
  if (deepseekKey) {
    try {
      const r = await fetch("https://api.deepseek.com/chat/completions", {
        method: "POST",
        headers: { "Authorization": `Bearer ${deepseekKey}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "deepseek-chat",
          max_tokens, messages: [
            ...(system ? [{role:"system",content:system}] : []),
            {role:"user",content:prompt}
          ],
        }),
      });
      const d = await r.json();
      const text = d?.choices?.[0]?.message?.content;
      if (text) return { text, model: "deepseek-chat" };
    } catch (e) { console.error("deepseek err", e); }
  }

  // Anthropic fallback
  if (anthKey) {
    try {
      const r = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "x-api-key": anthKey, "anthropic-version": "2023-06-01", "content-type": "application/json" },
        body: JSON.stringify({ model: "claude-sonnet-4-20250514", max_tokens, system, messages: [{role:"user",content:prompt}] }),
      });
      const d = await r.json();
      return { text: d?.content?.[0]?.text ?? "(empty)", model: "claude-sonnet-4" };
    } catch (e) { console.error("anthropic err", e); }
  }

  // OpenAI fallback
  if (openaiKey) {
    try {
      const r = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: { "Authorization": `Bearer ${openaiKey}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "gpt-4o-mini",
          max_tokens, messages: [
            ...(system ? [{role:"system",content:system}] : []),
            {role:"user",content:prompt}
          ],
        }),
      });
      const d = await r.json();
      const text = d?.choices?.[0]?.message?.content;
      if (text) return { text, model: "gpt-4o-mini" };
    } catch (e) { console.error("openai err", e); }
  }

  return { error: "no_llm_key_available" };
}

function verifyPayment(headers) {
  const sig = headers["payment-signature"] || headers["PAYMENT-SIGNATURE"] || headers["x-payment"];
  if (!sig) return { ok: false };
  // MVP: any signature header accepted (= dev mode). Production: verify on-chain.
  return { ok: true, tx: "0x_pending_x402_sdk_integration" };
}

exports.handler = async (event) => {
  let route = event.queryStringParameters?.route;
  if (!route) {
    const p = (event.path || "").replace(/^\/+/, "").toLowerCase();
    if (p === ".well-known/x402" || p === "well-known/x402") route = "well-known";
    else if (["qa","research","x-post","build"].includes(p)) route = p;
    else route = "well-known";
  }

  const wallet = process.env.ANICCA_WALLET_ADDR || "0x9B1Ee988b1A2931ABCE467f0a8eAff6c70c93e83";

  if (route === "well-known") {
    return {
      statusCode: 200, headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        agent: "Anicca", version: "v2.3", wallet,
        network: "eip155:8453", ens: "anicca.eth",
        routes: ROUTES,
        tagline: "Autonomous Buddhist AI. Earns via x402. No human in the loop.",
        github: "https://github.com/Daisuke134/anicca-oss",
        spec: "https://github.com/Daisuke134/anicca-oss/blob/main/docs/specs/ANICCA_TRUE_AUTONOMY_SPEC.md",
        live_since: "2026-06-01T01:33:00Z",
      }, null, 2),
    };
  }

  const paid = verifyPayment(event.headers || {});
  if (!paid.ok) return paymentRequired(route);

  const params = event.queryStringParameters || {};

  if (route === "qa") {
    const q = params.q || "";
    if (!q) return { statusCode: 400, body: JSON.stringify({ error: "missing q" }) };
    const r = await callLLM(q, "You are Anicca, an autonomous Buddhist AI agent. Answer questions clearly and concisely. End every answer by signing as 'Anicca'.", 512);
    return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ q, answer: r.text ?? null, error: r.error, model: r.model, tx: paid.tx }) };
  }

  if (route === "research") {
    const topic = params.topic || "";
    if (!topic) return { statusCode: 400, body: JSON.stringify({ error: "missing topic" }) };
    const r = await callLLM(`Deep-research this topic, produce a structured 800-word report with citations:\n\n${topic}`, "You are Anicca's research agent. Concise, citation-backed.", 2048);
    return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ topic, report: r.text ?? null, error: r.error, model: r.model, tx: paid.tx }) };
  }

  if (route === "x-post") {
    const brief = params.brief || "";
    const r = await callLLM(`Write a single X / Farcaster post (max 280 chars) for: ${brief}`, "You are Anicca's social writer. No hashtag spam, no emojis, just signal. Clear thinking under 280 chars.", 300);
    return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ brief, post: r.text ?? null, error: r.error, model: r.model, tx: paid.tx }) };
  }

  if (route === "build" && event.httpMethod === "POST") {
    let body = {};
    try { body = JSON.parse(event.body || "{}"); } catch {}
    const id = require("crypto").randomUUID();
    return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ build_id: id, status: "queued", eta: "5-7 days", intake: body, tx: paid.tx }) };
  }

  return { statusCode: 404, body: JSON.stringify({ error: "route not found", route, supported: Object.keys(ROUTES) }) };
};
