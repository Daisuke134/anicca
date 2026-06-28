// buyer-e2e.mjs — REAL on-chain x402 buy to prove the settle leg (founder F1 §Done(c)).
// Buyer = automaton 0xa3CDd4 (~/.automaton/wallet.json). Pays $0.003 USDC to payTo 0x810f.
// This is a SELF-PAYMENT discovery/mechanism seed — INV-7 must REJECT it as earn (NOT revenue).
import { x402Client, wrapFetchWithPayment, x402HTTPClient } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm/exact/client";
import { privateKeyToAccount } from "viem/accounts";
import { readFileSync } from "node:fs";

const w = JSON.parse(readFileSync(process.env.HOME + "/.automaton/wallet.json", "utf8"));
let pk = w.privateKey.startsWith("0x") ? w.privateKey : "0x" + w.privateKey;
const signer = privateKeyToAccount(pk);
console.log("buyer address:", signer.address);

const client = new x402Client();
client.register("eip155:*", new ExactEvmScheme(signer, { rpcUrl: "https://mainnet.base.org" }));
const fetchWithPayment = wrapFetchWithPayment(fetch, client);
const httpClient = new x402HTTPClient(client);

const url = process.env.BUY_URL || "http://localhost:8410/social/x";
console.log("POST", url);
const resp = await fetchWithPayment(url, {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ query: "AI agents x402 base", kind: "search", limit: 5 }),
});
console.log("HTTP status:", resp.status);
const xpr = resp.headers.get("x-payment-response");
if (xpr) {
  console.log("X-PAYMENT-RESPONSE(raw):", xpr);
  try { console.log("X-PAYMENT-RESPONSE(decoded):", Buffer.from(xpr, "base64").toString("utf8")); } catch {}
}
const result = await httpClient.processResponse(resp);
console.dir(result, { depth: null });
