// Secure x402 seller (testnet). The x402 middleware issues the 402 challenge and verifies
// the buyer's EIP-712 signed X-PAYMENT via the facilitator (handles replay/nonce/payer-identity =
// the 3 security findings the raw-txHash approach failed). Base Sepolia + x402.org facilitator (free).
import express from 'express';
import { paymentMiddleware, x402ResourceServer } from '@x402/express';
import { ExactEvmScheme } from '@x402/evm/exact/server';
import { HTTPFacilitatorClient } from '@x402/core/server';

const PORT = process.env.X402_PORT || 4021;
const payTo = process.env.X402_PAYTO; // anicca's testnet receiving wallet (0x…)
if (!payTo) { console.error('set X402_PAYTO'); process.exit(1); }

const app = express();
const facilitatorClient = new HTTPFacilitatorClient({ url: 'https://x402.org/facilitator' });
const server = new x402ResourceServer(facilitatorClient).register('eip155:84532', new ExactEvmScheme());

app.use(
  paymentMiddleware(
    {
      'GET /echo': {
        accepts: [{ scheme: 'exact', price: '$0.001', network: 'eip155:84532', payTo }],
        description: 'Echo a string. Pay $0.001 USDC (Base Sepolia) via x402.',
        mimeType: 'application/json',
      },
    },
    server,
  ),
);

app.get('/echo', (req, res) => {
  res.send({ echo: req.query.text || 'hello from anicca', paid: true });
});

app.get('/health', (_req, res) => res.send({ ok: true }));

app.listen(PORT, () => console.error(`[x402] seller on :${PORT} payTo=${payTo}`));
