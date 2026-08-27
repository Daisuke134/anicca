// 402 challenge generator.
// Per spec 09 § 6 + § 2 T3: response includes price_usdc, receiver, nonce, route_id, expires_at.
// Nonce + HMAC signature provide forgery-protection / replay-protection in tandem with on-chain
// tx hash uniqueness. The nonce_sig is server-recomputable so any returned challenge can be
// confirmed as originating here (anti-tamper).

import { createHmac, randomBytes, randomUUID } from "node:crypto";
import pricing from "./pricing.json" with { type: "json" };

export type RouteId = "echo" | "learn" | "draft" | "call";

export interface Challenge {
  version: "x402/v1";
  route_id: RouteId;
  price_usdc: number;
  currency: "USDC";
  chain: "base";
  chain_id: 8453;
  asset: string; // USDC contract on Base
  receiver: string;
  nonce: string;
  expires_at: string; // ISO8601, +5min
  nonce_sig: string; // HMAC-SHA256 over `${nonce}|${route_id}|${expires_at}|${price_usdc}`
  pay_with_header: "x-paid-tx-hash";
  hint: string;
}

const USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";

// HMAC secret: load from env or generate at process start. A per-process secret means
// nonces issued by this instance cannot be forged by an outsider; survive process
// restarts only if X402_HMAC_SECRET is set (recommended for prod / multi-instance).
const HMAC_SECRET: string =
  process.env.X402_HMAC_SECRET && process.env.X402_HMAC_SECRET.length >= 16
    ? process.env.X402_HMAC_SECRET
    : randomBytes(32).toString("hex");

function signNonce(parts: {
  nonce: string;
  routeId: RouteId;
  expiresAt: string;
  priceUsdc: number;
}): string {
  const payload = `${parts.nonce}|${parts.routeId}|${parts.expiresAt}|${parts.priceUsdc}`;
  return createHmac("sha256", HMAC_SECRET).update(payload).digest("hex");
}

export function buildChallenge(routeId: RouteId): Challenge {
  const route = (pricing.routes as Record<string, { price_usdc: number }>)[routeId];
  if (!route) {
    throw new Error(`Unknown route_id: ${routeId}`);
  }
  const nowMs = Date.now();
  const expiresAt = new Date(nowMs + 5 * 60 * 1000).toISOString();
  const nonce = randomUUID();
  const nonce_sig = signNonce({ nonce, routeId, expiresAt, priceUsdc: route.price_usdc });

  return {
    version: "x402/v1",
    route_id: routeId,
    price_usdc: route.price_usdc,
    currency: "USDC",
    chain: "base",
    chain_id: 8453,
    asset: USDC_BASE,
    receiver: pricing.receiver,
    nonce,
    expires_at: expiresAt,
    nonce_sig,
    pay_with_header: "x-paid-tx-hash",
    hint: `Send exactly ${route.price_usdc} USDC on Base to ${pricing.receiver}, then resend the same request with header 'x-paid-tx-hash: <0x...>'.`,
  };
}

export function getReceiver(): string {
  return pricing.receiver;
}

export function getRoutePrice(routeId: RouteId): number {
  return (pricing.routes as Record<string, { price_usdc: number }>)[routeId].price_usdc;
}

/** Re-derive the HMAC for a previously issued challenge — useful for offline confirmation. */
export function recomputeNonceSig(parts: {
  nonce: string;
  routeId: RouteId;
  expiresAt: string;
  priceUsdc: number;
}): string {
  return signNonce(parts);
}
