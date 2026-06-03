// 402 challenge generator.
// Per spec 09 § 6 + § 2 T3: response includes price_usdc, receiver, nonce, route_id.
// Nonce provides replay protection in tandem with on-chain tx hash uniqueness.

import { randomUUID } from "node:crypto";
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
  pay_with_header: "x-paid-tx-hash";
  hint: string;
}

const USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";

export function buildChallenge(routeId: RouteId): Challenge {
  const route = pricing.routes[routeId];
  if (!route) {
    throw new Error(`Unknown route_id: ${routeId}`);
  }
  const nowMs = Date.now();
  const expiresAt = new Date(nowMs + 5 * 60 * 1000).toISOString();

  return {
    version: "x402/v1",
    route_id: routeId,
    price_usdc: route.price_usdc,
    currency: "USDC",
    chain: "base",
    chain_id: 8453,
    asset: USDC_BASE,
    receiver: pricing.receiver,
    nonce: randomUUID(),
    expires_at: expiresAt,
    pay_with_header: "x-paid-tx-hash",
    hint: `Send exactly ${route.price_usdc} USDC on Base to ${pricing.receiver}, then resend the same request with header 'x-paid-tx-hash: <0x...>'.`,
  };
}

export function getReceiver(): string {
  return pricing.receiver;
}

export function getRoutePrice(routeId: RouteId): number {
  return pricing.routes[routeId].price_usdc;
}
