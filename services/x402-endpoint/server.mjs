// Secure x402 seller (testnet, x402 1.x). The middleware issues the 402 challenge and verifies
// the buyer's EIP-712 signed X-PAYMENT via the facilitator (replay/nonce/payer-identity handled =
// the 3 security findings the raw-txHash approach failed). Base Sepolia + x402.org facilitator (free).
import express from 'express';
import { paymentMiddleware } from 'x402-express';

const PORT = process.env.X402_PORT || 4021;
const payTo = process.env.X402_PAYTO;
if (!payTo) { console.error('set X402_PAYTO'); process.exit(1); }

const app = express();
app.use(
  paymentMiddleware(
    payTo,
    { 'GET /echo': { price: '$0.001', network: 'base-sepolia' } },
    { url: 'https://x402.org/facilitator' },
  ),
);

app.get('/echo', (req, res) => {
  res.send({ echo: req.query.text || 'hello from anicca', paid: true });
});
app.get('/health', (_req, res) => res.send({ ok: true }));

app.listen(PORT, () => console.error(`[x402] seller on :${PORT} payTo=${payTo} (base-sepolia, x402.org facilitator)`));
