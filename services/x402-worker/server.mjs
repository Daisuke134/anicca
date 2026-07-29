// Standalone Node port of the x402 earn endpoint (index.ts Cloudflare Worker).
// Same buyer-signed EIP-3009 verification; KVNamespace -> on-disk nonce store.
// Runs anywhere Node runs (Mac Mini behind a cloudflared quick tunnel, a VPS, etc.)
// so we are not blocked by Cloudflare-account Turnstile.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { recoverTypedDataAddress } from "viem";

const PAY_TO = "0xB9dd3B67921B354c656523d6851537988F31DD56";
const BASE_CHAIN_ID = 8453;
const BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const PRICE_ATOMIC = 1000n; // 0.001 USDC (6 decimals)
const ROUTE = "/paid";
const PORT = Number(process.env.PORT || 8402);

const NONCE_FILE = path.join(process.env.STATE_DIR || ".", "nonces.json");
function loadNonces() {
  try { return JSON.parse(fs.readFileSync(NONCE_FILE, "utf8")); } catch { return {}; }
}
function nonceSeen(key) {
  const all = loadNonces();
  const now = Math.floor(Date.now() / 1000);
  return all[key] && all[key] > now;
}
function nonceMark(key) {
  const all = loadNonces();
  all[key] = Math.floor(Date.now() / 1000) + 86400; // 24h TTL
  fs.writeFileSync(NONCE_FILE, JSON.stringify(all));
}

const REQUIRED_FIELDS = ["chain_id","verifying_contract","from","to","value_atomic","valid_after","valid_before","nonce","signature"];
const eq = (a, b) => String(a).toLowerCase() === String(b).toLowerCase();

function send(res, status, body, extraHeaders = {}) {
  const payload = JSON.stringify(body);
  res.writeHead(status, { "content-type": "application/json", ...extraHeaders });
  res.end(payload);
}

function paymentRequirements(resource) {
  return {
    scheme: "exact",
    network: "eip155:8453",
    asset: BASE_USDC,
    amount: PRICE_ATOMIC.toString(),
    payTo: PAY_TO,
    resource,
    description: "Paid echo endpoint — pay 0.001 USDC on Base to receive a signed 200.",
    mimeType: "application/json",
    maxTimeoutSeconds: 60,
    extra: { name: "USD Coin", version: "2" },
    extensions: {
      bazaar: {
        info: {
          input: { type: "http", method: "GET" },
          output: { type: "json", example: { ok: true, service: "anicca-x402-cloud", buyer: "0x…", served_at: 0 } },
        },
      },
    },
  };
}

function send402(res, resource) {
  send(res, 402, { x402Version: 2, error: "payment required", accepts: [paymentRequirements(resource)] }, {
    "WWW-Authenticate": `x402 network="base", asset="${BASE_USDC}", amount="${PRICE_ATOMIC}", pay_to="${PAY_TO}", chain_id="${BASE_CHAIN_ID}", route="${ROUTE}"`,
    "x402-network": "base",
    "x402-asset": BASE_USDC,
    "x402-amount": PRICE_ATOMIC.toString(),
    "x402-pay-to": PAY_TO,
    "x402-chain-id": String(BASE_CHAIN_ID),
  });
}

function parseReceipt(headerB64) {
  try {
    const obj = JSON.parse(Buffer.from(headerB64, "base64").toString("utf8"));
    for (const f of REQUIRED_FIELDS) if (obj[f] === undefined || obj[f] === null) return null;
    return obj;
  } catch { return null; }
}

async function recoverSigner(r) {
  try {
    const domain = { name: "USD Coin", version: "2", chainId: Number(r.chain_id), verifyingContract: r.verifying_contract };
    const types = {
      TransferWithAuthorization: [
        { name: "from", type: "address" }, { name: "to", type: "address" },
        { name: "value", type: "uint256" }, { name: "validAfter", type: "uint256" },
        { name: "validBefore", type: "uint256" }, { name: "nonce", type: "bytes32" },
      ],
    };
    const message = {
      from: r.from, to: r.to, value: BigInt(r.value_atomic),
      validAfter: BigInt(r.valid_after), validBefore: BigInt(r.valid_before), nonce: r.nonce,
    };
    return await recoverTypedDataAddress({ domain, types, primaryType: "TransferWithAuthorization", message, signature: r.signature });
  } catch { return null; }
}

async function verify(r) {
  if (!eq(r.to, PAY_TO)) return { ok: false, reason: "wrong_pay_to" };
  if (Number(r.chain_id) !== BASE_CHAIN_ID) return { ok: false, reason: "wrong_chain" };
  if (!eq(r.verifying_contract, BASE_USDC)) return { ok: false, reason: "wrong_asset" };
  if (BigInt(r.value_atomic) < PRICE_ATOMIC) return { ok: false, reason: "insufficient_amount" };
  const now = Math.floor(Date.now() / 1000);
  if (Number(r.valid_after) > now) return { ok: false, reason: "not_yet_valid" };
  if (Number(r.valid_before) <= now) return { ok: false, reason: "expired" };
  const recovered = await recoverSigner(r);
  if (!recovered) return { ok: false, reason: "bad_signature" };
  if (!eq(recovered, r.from)) return { ok: false, reason: "signer_not_from" };
  if (eq(recovered, PAY_TO)) return { ok: false, reason: "self_signed_rejected" };
  const nonceKey = `nonce:${r.from.toLowerCase()}:${String(r.nonce).toLowerCase()}`;
  if (nonceSeen(nonceKey)) return { ok: false, reason: "nonce_replay" };
  nonceMark(nonceKey);
  return { ok: true, buyer: recovered };
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);

  if (url.pathname === "/health") return send(res, 200, { ok: true, service: "anicca-x402-cloud", wave: 2 });

  if (url.pathname === "/.well-known/x402") {
    const resource = url.origin + ROUTE;
    return send(res, 200, { x402Version: 2, resources: [{ resource, ...paymentRequirements(resource) }] });
  }

  if (url.pathname === "/openapi.json") {
    // Canonical discovery contract for x402scan / Poncho (https://www.x402scan.com/discovery/spec)
    return send(res, 200, {
      openapi: "3.1.0",
      info: {
        title: "anicca-x402 paid echo",
        version: "1.0.0",
        description: "Pay 0.001 USDC on Base (EIP-3009) to receive a signed 200. Inbound agent-economy endpoint operated by Anicca.",
        contact: { email: process.env.LIFE_MANAGER_CONTACT_EMAIL || "contact@aniccaai.com" },
      },
      servers: [{ url: url.origin }],
      paths: {
        [ROUTE]: {
          get: {
            operationId: "paidEcho",
            summary: "Paid echo — returns a signed 200 after x402 payment",
            "x-payment-info": { x402: {} },
            responses: {
              "200": {
                description: "OK",
                content: { "application/json": { schema: { type: "object", properties: { ok: { type: "boolean" }, buyer: { type: "string" }, served_at: { type: "integer" } } } } },
              },
              "402": { description: "Payment Required" },
            },
          },
        },
      },
    });
  }

  if (url.pathname !== ROUTE) return send(res, 404, { error: "no such route" });

  const header = req.headers["x-payment"];
  if (!header) return send402(res, url.origin + ROUTE);
  const receipt = parseReceipt(Array.isArray(header) ? header[0] : header);
  if (!receipt) return send(res, 402, { error: "invalid_receipt", reason: "unparseable" });
  const result = await verify(receipt);
  if (!result.ok) return send(res, 402, { error: "invalid_receipt", reason: result.reason });
  return send(res, 200, { ok: true, service: "anicca-x402-cloud", buyer: result.buyer, served_at: Math.floor(Date.now() / 1000) });
});

server.listen(PORT, () => console.log(`x402-serve listening on :${PORT} pay_to=${PAY_TO}`));
