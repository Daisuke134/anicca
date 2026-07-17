// verify-settle-fail-replay.mjs — Task4/5/6 Step4 (v2 SETTLE-FAILURE injection): a zero-balance
// buyer wallet does NOT reach this path — @x402/evm/exact/client's ExactEvmScheme checks the
// signer's on-chain USDC balance BEFORE signing (chunk-2GHXG5WB.mjs) and CDP's facilitator
// verify() also rejects insufficient balance, so an underfunded buyer never gets past verify()
// (no X-PAYMENT is even sent; nothing is logged to attempts OR sales — confirmed empirically
// 2026-07-17 against franklin2). The one reproducible verify-pass/settle-fail trigger found:
// REPLAY the exact same signed EIP-3009 authorization (same nonce) for a second request right
// after the first one settles. verify() does not re-check on-chain nonce state, but settle()
// submits transferWithAuthorization on-chain, which reverts ("authorization nonce already
// submitted") — a genuine post-verify settle failure, landing in attempts-<wallet>.jsonl with
// settled:false while request #1's real settlement lands in sales-<wallet>.jsonl.
import { x402Client, x402HTTPClient } from "@x402/core/client";
import { ExactEvmScheme } from "@x402/evm/exact/client";
import { privateKeyToAccount } from "viem/accounts";
import { loadEvmKey } from "../lib/resolve-identity.mjs";

const pk = loadEvmKey();
if (!pk) { console.error("no key"); process.exit(2); }
const account = privateKeyToAccount(pk);
console.log("buyer:", account.address);

const network = process.env.BUY_NETWORK || "eip155:8453"; // Base mainnet CAIP-2
const client = new x402Client().register(network, new ExactEvmScheme(account));
const httpClient = new x402HTTPClient(client);

const url = process.env.BUY_URL || "https://aniccanomac-mini-1.tail7a0ba4.ts.net:10000/funding-rates";

// initial GET (no payment) to get the 402 challenge
const r1 = await fetch(url, { method: "GET" });
console.log("initial status:", r1.status);
const getHeader = (name) => r1.headers.get(name);
let body;
try { body = await r1.clone().json(); } catch { body = undefined; }
const paymentRequired = httpClient.getPaymentRequiredResponse(getHeader, body);
const paymentPayload = await httpClient.createPaymentPayload(paymentRequired);
const headerObj = httpClient.encodePaymentSignatureHeader(paymentPayload);
console.log("payment header keys:", Object.keys(headerObj));

// REQUEST A: pay for real with this fresh signature (should settle).
const respA = await fetch(url, { method: "GET", headers: { ...headerObj } });
console.log("\n=== REQUEST A (first use) ===");
console.log("status:", respA.status);
const prA = respA.headers.get("payment-response") || respA.headers.get("PAYMENT-RESPONSE");
console.log("PAYMENT-RESPONSE(A):", prA ? Buffer.from(prA, "base64").toString("utf8") : "(none)");
await respA.text();

// REQUEST B: REPLAY the exact same signed header (same nonce) immediately after.
const respB = await fetch(url, { method: "GET", headers: { ...headerObj } });
console.log("\n=== REQUEST B (replay, same signature/nonce) ===");
console.log("status:", respB.status);
const prB = respB.headers.get("payment-response") || respB.headers.get("PAYMENT-RESPONSE");
console.log("PAYMENT-RESPONSE(B):", prB ? Buffer.from(prB, "base64").toString("utf8") : "(none)");
const bodyB = await respB.text();
console.log("body(B, first 300):", bodyB.slice(0, 300));
