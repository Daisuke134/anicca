// register-x402scan.mjs — XSCAN-1: register a v2-migrated x402 seller origin with x402scan.com.
//
// x402scan's registry write endpoints (POST /api/x402/registry/register-origin,
// POST /api/x402/registry/register) are SIWX-gated (Sign-In-With-X, EIP-4361/CAIP-122 wallet
// auth) — NOT an unauthenticated form POST, despite the public /resources/register page looking
// like a plain URL box. Confirmed by reading the actual handler source:
//   github.com/Merit-Systems/x402scan apps/scan/src/app/api/x402/registry/register-origin/route.ts
//     .siwx().body(registryRegisterOriginBodySchema).handler(handleRegistryRegisterOrigin)
//   apps/scan/src/lib/router.ts (router discovery.guidance): "Registry write endpoints (register,
//     register-origin) require SIWX wallet authentication (use fetch_with_auth)."
// The official client-side flow is @x402/extensions/sign-in-with-x's wrapFetchWithSIWx(fetch, signer):
// it makes the request, sees the 402 + `extensions['sign-in-with-x']` challenge, signs a CAIP-122
// message with the wallet, retries with a `SIGN-IN-WITH-X` header. A viem PrivateKeyAccount
// (privateKeyToAccount) satisfies the EVMSigner interface directly (address + signMessage) — no
// extra glue needed. This is the SAME pattern @x402/fetch uses for payments, just for identity.
//
// register-origin itself fetches OUR /openapi.json (OpenAPI-first discovery per x402scan's own
// docs/DISCOVERY.md), probes each x-payment-info route for a real 402 challenge, and registers
// whichever routes pass. No manifest upload — the seller's live 402 responses ARE the source of
// truth ("Runtime 402 behavior is authoritative over static metadata").
//
// Usage:
//   ANICCA_HOME=~/.blockrun ORIGIN=https://franklin1.tail7a0ba4.ts.net node register-x402scan.mjs
//   ANICCA_HOME=~/.franklin2-home/.blockrun ORIGIN=https://aniccanomac-mini-1.tail7a0ba4.ts.net:10000 node register-x402scan.mjs
//
// Never echoes the private key (R5 / env-filter discipline) — only the derived public address.
//
// ★ wrapFetchWithSIWx bug (measured 2026-07-17, @x402/extensions@2.17.0): it only signs+retries
// when the SAME 402 also carries a payment `accepts[0].network` (it derives the target chain by
// matching that against `supportedChains`). x402scan's register-origin route is SIWX-only —
// identity-gated, no payment — so it returns `accepts:[]`, and the library's own network lookup
// (`paymentRequired.accepts?.[0]?.network`) comes back undefined and it silently returns the raw
// 402 without ever signing. Confirmed against
// node_modules/@x402/extensions/dist/esm/chunk-LMLJI6VE.mjs:701-740 (`wrapFetchWithSIWx`).
// Workaround (this file): call the lower-level `createSIWxPayload`/`encodeSIWxHeader` primitives
// directly against the challenge's `extensions['sign-in-with-x'].info` (which already carries a
// complete chainId+type, no matching needed for the auth-only case).
import { createSIWxPayload, encodeSIWxHeader } from "@x402/extensions/sign-in-with-x";
import { privateKeyToAccount } from "viem/accounts";
import { loadEvmKey } from "../lib/resolve-identity.mjs";

const pk = loadEvmKey();
if (!pk) {
  console.error("register-x402scan: no per-instance EVM key resolvable (env / $ANICCA_HOME / owner-legacy) — refusing");
  process.exit(2);
}
const account = privateKeyToAccount(pk);
console.log("signer address:", account.address);

const origin = process.env.ORIGIN;
if (!origin) {
  console.error("register-x402scan: set ORIGIN=https://your-seller-origin (no trailing slash)");
  process.exit(2);
}

const REGISTRY_URL = "https://www.x402scan.com/api/x402/registry/register-origin";
const reqBody = JSON.stringify({ origin });

console.log("POST", REGISTRY_URL, "origin:", origin);
const first = await fetch(REGISTRY_URL, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: reqBody,
});
console.log("HTTP status (1st, unauthenticated):", first.status);

if (first.status !== 402) {
  console.log("body:", await first.text());
  process.exit(first.ok ? 0 : 1);
}

const challenge = await first.json();
const siwxInfo = challenge?.extensions?.["sign-in-with-x"]?.info;
if (!siwxInfo) {
  console.error("register-x402scan: 402 but no sign-in-with-x extension present:", JSON.stringify(challenge));
  process.exit(1);
}

const payload = await createSIWxPayload(siwxInfo, account);
const siwxHeader = encodeSIWxHeader(payload);

const second = await fetch(REGISTRY_URL, {
  method: "POST",
  headers: { "Content-Type": "application/json", "SIGN-IN-WITH-X": siwxHeader },
  body: reqBody,
});
console.log("HTTP status (2nd, SIWX-signed):", second.status);
const text = await second.text();
console.log("body:", text);
process.exit(second.ok ? 0 : 1);
