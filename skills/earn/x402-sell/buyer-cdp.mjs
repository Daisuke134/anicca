// buyer-cdp.mjs — v1 x402 buyer (x402-fetch) to seed the Bazaar listing with ONE real CDP-facilitated
// payment. Buyer = automaton 0xa3CDd4 (~/.automaton/wallet.json) pays $0.003 USDC to the public seller
// (payTo 0x810f). SELF-PAYMENT discovery seed — INV-7 excludes it from earnings (both wallets are mine).
import { wrapFetchWithPayment } from "x402-fetch";
import { createWalletClient, http } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base } from "viem/chains";
import { readFileSync } from "node:fs";

const w = JSON.parse(readFileSync(process.env.HOME + "/.automaton/wallet.json", "utf8"));
let pk = w.privateKey.startsWith("0x") ? w.privateKey : "0x" + w.privateKey;
const account = privateKeyToAccount(pk);
console.log("buyer:", account.address);

const wallet = createWalletClient({ account, chain: base, transport: http("https://mainnet.base.org") });
const fetchWithPay = wrapFetchWithPayment(fetch, wallet);

const url = process.env.BUY_URL || "https://aniccanomac-mini-1.tail7a0ba4.ts.net/research?q=x402%20agent%20payments";
console.log("GET (with payment):", url);
const resp = await fetchWithPay(url, { method: "GET" });
console.log("HTTP status:", resp.status);
const xpr = resp.headers.get("x-payment-response");
if (xpr) {
  try { console.log("X-PAYMENT-RESPONSE:", Buffer.from(xpr, "base64").toString("utf8").slice(0, 300)); }
  catch { console.log("X-PAYMENT-RESPONSE(raw):", xpr.slice(0, 120)); }
}
const body = await resp.text();
console.log("body(first 300):", body.slice(0, 300));
