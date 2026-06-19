// x402 buyer (testnet, x402 1.x). Signs the EIP-712 payment authorization and pays automatically.
// Needs a Base Sepolia wallet with testnet USDC (X402_BUYER_KEY). Proves the secure flow E2E:
// GET → 402 challenge → sign+pay → facilitator verifies → 200 + content.
import { createSigner, wrapFetchWithPayment, decodeXPaymentResponse } from 'x402-fetch';

const KEY = process.env.X402_BUYER_KEY;
const URL = process.env.X402_URL || 'http://localhost:4021/echo?text=anicca-earns';
if (!KEY) { console.error('set X402_BUYER_KEY'); process.exit(1); }

const signer = await createSigner('base-sepolia', KEY);
const fetchWithPay = wrapFetchWithPayment(fetch, signer);

const res = await fetchWithPay(URL);
console.error('status:', res.status);
console.error('body:', (await res.text()).slice(0, 300));
const xpr = res.headers.get('x-payment-response');
if (xpr) { try { console.error('payment-response:', JSON.stringify(decodeXPaymentResponse(xpr))); } catch {} }
process.exit(res.status === 200 ? 0 : 1);
