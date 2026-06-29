// x402 paid endpoint — anicca's first sovereign revenue route (spec 09).
// GET /.netlify/functions/x402-echo?text=hi
//   - no payment       -> HTTP 402 + x402-shaped challenge (accepts[]).
//   - x-payment-tx: 0x… -> verify the buyer's USDC payment to anicca on Base; 200 + echo.
// Self-verifies the on-chain USDC Transfer (no facilitator). Simplest effective path.

const ANICCA_WALLET = '0xa3CDd4ec6B94f01826aAf90A6d5538A2Aa8c4C21'; // payTo
const USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913';
const TRANSFER_TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef';
const PRICE_BASE = 1000; // 0.001 USDC (6 decimals)
const RPC = 'https://mainnet.base.org';

async function rpc(method, params) {
  const r = await fetch(RPC, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }),
  });
  const j = await r.json();
  if (j.error) throw new Error(j.error.message);
  return j.result;
}

async function verifyPayment(txHash) {
  if (!/^0x[0-9a-fA-F]{64}$/.test(txHash || '')) return { ok: false, reason: 'bad txHash' };
  const rcpt = await rpc('eth_getTransactionReceipt', [txHash]);
  if (!rcpt) return { ok: false, reason: 'tx not found' };
  if (rcpt.status !== '0x1') return { ok: false, reason: 'tx failed' };
  const recv = ANICCA_WALLET.toLowerCase().replace(/^0x/, '');
  for (const log of rcpt.logs || []) {
    if ((log.address || '').toLowerCase() !== USDC) continue;
    if ((log.topics?.[0] || '').toLowerCase() !== TRANSFER_TOPIC) continue;
    const to = (log.topics[2] || '').slice(-40).toLowerCase();
    if (to !== recv) continue;
    const amt = parseInt(log.data, 16);
    if (amt >= PRICE_BASE) return { ok: true, amountBase: amt, from: '0x' + (log.topics[1] || '').slice(-40) };
  }
  return { ok: false, reason: 'no USDC transfer to anicca >= price' };
}

exports.handler = async (event) => {
  const text = (event.queryStringParameters || {}).text || 'hello from anicca';
  const txHash = (event.headers || {})['x-payment-tx'] || (event.headers || {})['X-Payment-Tx'];

  if (!txHash) {
    return {
      statusCode: 402,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        x402Version: 1,
        accepts: [
          {
            scheme: 'exact',
            network: 'base',
            maxAmountRequired: String(PRICE_BASE),
            resource: '/.netlify/functions/x402-echo',
            description: 'Echo a string. Pay 0.001 USDC on Base to anicca, resend with header x-payment-tx.',
            mimeType: 'application/json',
            payTo: ANICCA_WALLET,
            asset: USDC,
            maxTimeoutSeconds: 1200,
          },
        ],
      }),
    };
  }

  // SECURITY: accepting a raw on-chain txHash is INSECURE for a paid endpoint —
  // tx hashes are public, so anyone who reads the chain could replay someone else's
  // payment to get content (no payer-identity binding, no replay/nonce, no finality).
  // The correct x402 'exact' scheme binds payment to the request via an EIP-712 signed
  // PaymentPayload + USDC transferWithAuthorization (nonce/payTo/value/resource), verified
  // by a facilitator. Until that is wired, we NEVER serve via the txHash path.
  void verifyPayment; // primitive kept for verifying anicca's OWN incoming payments, not third-party auth
  return {
    statusCode: 402,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      error: 'secure x402 settlement not yet enabled',
      detail: 'This route will accept an EIP-712 signed x402 PaymentPayload (transferWithAuthorization). Raw txHash is not accepted (forgeable/replayable).',
    }),
  };
};
