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

function payTo() {
  if (process.env.X402_PAYTO) return process.env.X402_PAYTO;
  try {
    const w = JSON.parse(readFileSync(homedir() + "/.automaton/wallet.json", "utf8"));
    return w.address;
  } catch {
    throw new Error("set X402_PAYTO (no ~/.automaton/wallet.json)");
  }
}

const PRICE = process.env.X402_PRICE || "$0.003";
const NETWORK = process.env.X402_NETWORK || "base";
const PORT = Number(process.env.X402_PORT || 8403);
// default product = $0 web-research digest via research-product.mjs (Wikipedia + HN + Jina, zero paid keys).
const PRODUCT_CMD = process.env.X402_PRODUCT_CMD ||
  `node ${new URL('./research-product.mjs', import.meta.url).pathname} {q}`;

const app = express();

// x402: protect the paid route. paymentMiddleware(payTo, routes, facilitator). Verified primitive
// (x402-express, prior session): payTo=wallet, $price USDC on Base, returns 402 until paid — no key
// needed to RECEIVE. Loaded dynamically so the skill installs the dep on first run.
const { paymentMiddleware } = await import("x402-express");
// CDP facilitator (when CDP keys present) → settles on Base mainnet AND lists the endpoint in the x402
// Bazaar discovery layer (how buyer agents FIND us). Falls back to the x402.org testnet facilitator when
// no CDP keys (generic install / dev). payTo stays our wallet — CDP only facilitates + catalogs, never custodies.
let facilitator = { url: "https://x402.org/facilitator" };
if (process.env.CDP_API_KEY_ID && process.env.CDP_API_KEY_SECRET) {
  const { createFacilitatorConfig } = await import("@coinbase/x402");
  facilitator = createFacilitatorConfig(process.env.CDP_API_KEY_ID, process.env.CDP_API_KEY_SECRET);
}
app.use(
  paymentMiddleware(
    payTo(),
    { "GET /research": { price: PRICE, network: NETWORK, config: { description: "On-demand web research digest — free-source curated (Wikipedia + Hacker News + Jina Reader). GET /research?q=<topic>; pay per request in USDC on Base. Runs on any install, $0 source cost." } } },
    facilitator
  )
);

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

// free: tells a buyer what's for sale + the price (so demand can find it).
app.get("/", (_req, res) =>
  res.json({ product: "web research (Twitter/Reddit/YouTube/GitHub)", price: PRICE,
             pay: "GET /research?q=... (x402: pay " + PRICE + " USDC on " + NETWORK + ")", payTo: payTo() }));

app.listen(PORT, () =>
  console.log(JSON.stringify({ x402_seller: "up", port: PORT, price: PRICE, network: NETWORK, payTo: payTo() })));
