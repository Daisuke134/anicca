// buyer-cdp-v2.mjs — v2 x402 buyer (@x402/fetch + @x402/evm/exact/client) for sellers already
// migrated to serve-v2.mjs (@x402/express@2.17.0). buyer-cdp.mjs (x402-fetch@1.2.0, v1 protocol)
// cannot pay a v2 seller: v2's paymentMiddleware puts the payment requirements in the
// PAYMENT-REQUIRED response HEADER (base64), not the JSON body x402-fetch@1 parses — confirmed
// 2026-07-17 by a live TypeError (x402-fetch's PaymentRequirementsSchema.parse(undefined)) when
// buyer-cdp.mjs hit franklin2's serve-v2.mjs /funding-rates. This sibling script is the same
// self-pay probe, upgraded to the official v2 client (docs.x402.org / npm @x402/fetch README).
//
// SELF-PAYMENT discovery/verification seed only — INV-7 excludes it from earnings (buyer and
// seller wallets are both ours in the Task4 verification run).
import { wrapFetchWithPaymentFromConfig } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm/exact/client";
import { privateKeyToAccount } from "viem/accounts";
import { loadEvmKey } from "../lib/resolve-identity.mjs";

const pk = loadEvmKey(); // #28: gated per-instance key (foreign spawn → null, never a borrowed legacy key)
if (!pk) { console.error("buyer-cdp-v2: no per-instance EVM key resolvable (env / $ANICCA_HOME / owner-legacy) — refusing"); process.exit(2); }
const account = privateKeyToAccount(pk);
console.log("buyer:", account.address);

const network = process.env.BUY_NETWORK || "eip155:8453"; // Base mainnet CAIP-2 (matches serve-v2.mjs NETWORK)
const fetchWithPay = wrapFetchWithPaymentFromConfig(fetch, {
  schemes: [{ network, client: new ExactEvmScheme(account) }],
});

const url = process.env.BUY_URL || "https://aniccanomac-mini-1.tail7a0ba4.ts.net:10000/funding-rates";
console.log("GET (with payment, v2):", url);
const resp = await fetchWithPay(url, { method: "GET" });
console.log("HTTP status:", resp.status);
const xpr = resp.headers.get("payment-response") || resp.headers.get("PAYMENT-RESPONSE");
if (xpr) {
  try { console.log("PAYMENT-RESPONSE:", Buffer.from(xpr, "base64").toString("utf8").slice(0, 400)); }
  catch { console.log("PAYMENT-RESPONSE(raw):", xpr.slice(0, 200)); }
}
const body = await resp.text();
console.log("body(first 500):", body.slice(0, 500));
