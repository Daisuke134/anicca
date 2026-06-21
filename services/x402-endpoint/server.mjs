// Secure x402 seller (x402 1.x). The middleware issues the 402 challenge and verifies the buyer's
// EIP-712 signed X-PAYMENT via the facilitator (replay/nonce/payer-identity handled = the 3 security
// findings the raw-txHash approach failed).
//
// Network/facilitator are env-configurable so the SAME server runs on testnet AND mainnet:
//   X402_NETWORK     "base-sepolia" (default, free x402.org facilitator) | "base" (mainnet)
//   X402_FACILITATOR facilitator URL (default: x402.org for testnet; CDP facilitator
//                    https://api.cdp.coinbase.com/platform/v2/x402 for Base MAINNET real USDC)
//   X402_PRICE       price per request (default "$0.001")
//   X402_PAYTO       receiving wallet (anicca's own wallet)  [required]
//   X402_PORT        listen port (default 4021)
// Testnet E2E GREEN 2026-06-19 (settlement tx 0x8683daa…, anicca 0.0→0.001 USDC). See E2E-RESULT.md.
import express from 'express';
import { paymentMiddleware } from 'x402-express';

const PORT = process.env.X402_PORT || 4021;
const payTo = process.env.X402_PAYTO;
if (!payTo) { console.error('set X402_PAYTO'); process.exit(1); }
const NETWORK = process.env.X402_NETWORK || 'base-sepolia';
const PRICE = process.env.X402_PRICE || '$0.001';
// Default facilitator: x402.org for testnet; for mainnet the operator MUST set the CDP facilitator.
const FACILITATOR = process.env.X402_FACILITATOR
  || (NETWORK === 'base' ? 'https://api.cdp.coinbase.com/platform/v2/x402' : 'https://x402.org/facilitator');

const app = express();
app.use(
  paymentMiddleware(
    payTo,
    { 'GET /echo': { price: PRICE, network: NETWORK } },
    { url: FACILITATOR },
  ),
);

app.get('/echo', (req, res) => {
  res.send({ echo: req.query.text || 'hello from anicca', paid: true });
});
app.get('/health', (_req, res) => res.send({ ok: true }));

app.listen(PORT, () => console.error(`[x402] seller on :${PORT} payTo=${payTo} network=${NETWORK} price=${PRICE} facilitator=${FACILITATOR}`));
