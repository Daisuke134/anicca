import { recoverTypedDataAddress } from "viem";

const PAY_TO = "0xB9dd3B67921B354c656523d6851537988F31DD56";
const BASE_CHAIN_ID = 8453;
const BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const PRICE_ATOMIC = 1000n; // 0.001 USDC (6 decimals)
const ROUTE = "/paid";

interface Env {
  NONCE_KV: KVNamespace;
}

interface PaymentReceipt {
  protocol: string;
  chain_id: number;
  verifying_contract: string;
  from: string;
  to: string;
  value_atomic: number | string;
  valid_after: number | string;
  valid_before: number | string;
  nonce: string;
  signature: string;
}

const REQUIRED_FIELDS: (keyof PaymentReceipt)[] = [
  "chain_id",
  "verifying_contract",
  "from",
  "to",
  "value_atomic",
  "valid_after",
  "valid_before",
  "nonce",
  "signature",
];

function eq(a: string, b: string): boolean {
  return a.toLowerCase() === b.toLowerCase();
}

function json(status: number, body: unknown, extraHeaders?: Record<string, string>): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...(extraHeaders ?? {}) },
  });
}

// x402 v2 PaymentRequirements + Bazaar discovery extension. This is the schema the
// agentic.market validator and the x402 facilitator crawler index — the "listing" is the
// endpoint serving this body, not a POST to any registry. CAIP-2 network id eip155:8453 = Base.
function send402(resource: string): Response {
  return json(
    402,
    {
      x402Version: 2,
      error: "payment required",
      accepts: [
        {
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
                output: {
                  type: "json",
                  example: { ok: true, service: "anicca-x402-cloud", buyer: "0x…", served_at: 0 },
                },
              },
            },
          },
        },
      ],
    },
    {
      "WWW-Authenticate":
        `x402 network="base", asset="${BASE_USDC}", amount="${PRICE_ATOMIC}", ` +
        `pay_to="${PAY_TO}", chain_id="${BASE_CHAIN_ID}", route="${ROUTE}"`,
      "x402-network": "base",
      "x402-asset": BASE_USDC,
      "x402-amount": PRICE_ATOMIC.toString(),
      "x402-pay-to": PAY_TO,
      "x402-chain-id": String(BASE_CHAIN_ID),
    },
  );
}

function parseReceipt(headerB64: string): PaymentReceipt | null {
  try {
    const raw = atob(headerB64);
    const obj = JSON.parse(raw) as PaymentReceipt;
    for (const f of REQUIRED_FIELDS) {
      if (obj[f] === undefined || obj[f] === null) return null;
    }
    return obj;
  } catch {
    return null;
  }
}

// Recover the signer of an EIP-3009 transferWithAuthorization. This is the real x402
// "exact-evm" scheme (Coinbase x402): the BUYER signs, so the recovered address MUST equal
// `from` (the buyer) and MUST NOT be `to`/pay_to. A Wave-1 self-signed receipt (signer == to)
// fails this check and is rejected.
async function recoverSigner(r: PaymentReceipt): Promise<string | null> {
  try {
    const domain = {
      name: "USD Coin",
      version: "2",
      chainId: Number(r.chain_id),
      verifyingContract: r.verifying_contract as `0x${string}`,
    } as const;
    const types = {
      TransferWithAuthorization: [
        { name: "from", type: "address" },
        { name: "to", type: "address" },
        { name: "value", type: "uint256" },
        { name: "validAfter", type: "uint256" },
        { name: "validBefore", type: "uint256" },
        { name: "nonce", type: "bytes32" },
      ],
    } as const;
    const message = {
      from: r.from as `0x${string}`,
      to: r.to as `0x${string}`,
      value: BigInt(r.value_atomic),
      validAfter: BigInt(r.valid_after),
      validBefore: BigInt(r.valid_before),
      nonce: r.nonce as `0x${string}`,
    };
    return await recoverTypedDataAddress({
      domain,
      types,
      primaryType: "TransferWithAuthorization",
      message,
      signature: r.signature as `0x${string}`,
    });
  } catch {
    return null;
  }
}

async function verify(r: PaymentReceipt, env: Env): Promise<{ ok: true; buyer: string } | { ok: false; reason: string }> {
  if (!eq(r.to, PAY_TO)) return { ok: false, reason: "wrong_pay_to" };
  if (Number(r.chain_id) !== BASE_CHAIN_ID) return { ok: false, reason: "wrong_chain" };
  if (!eq(r.verifying_contract, BASE_USDC)) return { ok: false, reason: "wrong_asset" };
  if (BigInt(r.value_atomic) < PRICE_ATOMIC) return { ok: false, reason: "insufficient_amount" };
  const now = Math.floor(Date.now() / 1000);
  if (Number(r.valid_after) > now) return { ok: false, reason: "not_yet_valid" };
  if (Number(r.valid_before) <= now) return { ok: false, reason: "expired" };

  const recovered = await recoverSigner(r);
  if (!recovered) return { ok: false, reason: "bad_signature" };
  // Wave-2 differentiator: the signer is the BUYER (`from`), never us (`to`/pay_to).
  if (!eq(recovered, r.from)) return { ok: false, reason: "signer_not_from" };
  if (eq(recovered, PAY_TO)) return { ok: false, reason: "self_signed_rejected" };

  const nonceKey = `nonce:${r.from.toLowerCase()}:${r.nonce.toLowerCase()}`;
  const seen = await env.NONCE_KV.get(nonceKey);
  if (seen) return { ok: false, reason: "nonce_replay" };
  await env.NONCE_KV.put(nonceKey, "1", { expirationTtl: 86400 });

  return { ok: true, buyer: recovered };
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return json(200, { ok: true, service: "anicca-x402-cloud", wave: 2 });
    }

    if (url.pathname !== ROUTE) {
      return json(404, { error: "no such route" });
    }

    const header = request.headers.get("x-payment");
    if (!header) return send402(url.origin + ROUTE);

    const receipt = parseReceipt(header);
    if (!receipt) return json(402, { error: "invalid_receipt", reason: "unparseable" });

    const result = await verify(receipt, env);
    if (!result.ok) return json(402, { error: "invalid_receipt", reason: result.reason });

    return json(200, {
      ok: true,
      service: "anicca-x402-cloud",
      buyer: result.buyer,
      served_at: Math.floor(Date.now() / 1000),
    });
  },
} satisfies ExportedHandler<Env>;
