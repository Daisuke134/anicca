#!/usr/bin/env node
// serve-mainnet.mjs — SELF-FACILITATING Base-mainnet x402 seller for the founder wallet.
// ONE paid route: POST /research ($0.003 USDC) → runs the $0 research-product (Wikipedia+HN+Jina).
// In-process facilitator signed by EVM_PRIVATE_KEY (founder 0x810f); the wallet pays its own settle gas.
// Pattern proven on-chain 2026-06-28 (tx 0x71d4ca08). No CDP, no twitterapi, no paid key.
// Boot env: EVM_PRIVATE_KEY + X402_WALLET_ADDRESS (+ optional X402_PRICE, X402_RPC_URL, PORT).
import express from 'express';
import { pathToFileURL } from 'node:url';
import { createWalletClient, http, publicActions } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { base } from 'viem/chains';
import { x402Facilitator } from '@x402/core/facilitator';
import { paymentMiddleware, x402ResourceServer } from '@x402/express';
import { toFacilitatorEvmSigner } from '@x402/evm';
import { registerExactEvmScheme } from '@x402/evm/exact/facilitator';
import { ExactEvmScheme as ExactEvmServerScheme } from '@x402/evm/exact/server';
import { research } from './research-product.mjs';

const USDC_BASE_MAINNET = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const NETWORK = 'eip155:8453';
const PRICE = process.env.X402_PRICE || '$0.003';
const PORT = Number(process.env.X402_PORT || process.env.PORT || 8411);
const KEY_RE = /^0x[0-9a-fA-F]{64}$/;
const ADDR_RE = /^0x[0-9a-fA-F]{40}$/;

function validateEnv() {
  const k = process.env.EVM_PRIVATE_KEY;
  const a = process.env.X402_WALLET_ADDRESS;
  if (!k || !KEY_RE.test(k)) throw new Error('EVM_PRIVATE_KEY missing/malformed');
  if (!a || !ADDR_RE.test(a)) throw new Error('X402_WALLET_ADDRESS missing/malformed');
}

export async function createApp() {
  validateEnv();
  const account = privateKeyToAccount(process.env.EVM_PRIVATE_KEY);
  const payTo = process.env.X402_WALLET_ADDRESS;
  const wallet = createWalletClient({
    account, chain: base,
    transport: process.env.X402_RPC_URL ? http(process.env.X402_RPC_URL) : http(),
  }).extend(publicActions);

  const evmSigner = toFacilitatorEvmSigner({
    address: account.address,
    getCode: wallet.getCode,
    readContract: wallet.readContract,
    verifyTypedData: wallet.verifyTypedData,
    writeContract: wallet.writeContract,
    sendTransaction: wallet.sendTransaction,
    waitForTransactionReceipt: wallet.waitForTransactionReceipt,
  });
  const facilitator = new x402Facilitator();
  registerExactEvmScheme(facilitator, { signer: evmSigner, networks: NETWORK });
  const resourceServer = new x402ResourceServer({
    verify: facilitator.verify.bind(facilitator),
    settle: facilitator.settle.bind(facilitator),
    getSupported: async () => facilitator.getSupported(),
  }).register(NETWORK, new ExactEvmServerScheme());

  const ROUTES = {
    'POST /research': {
      accepts: [{
        scheme: 'exact', price: PRICE, network: NETWORK, payTo,
        extra: { asset: USDC_BASE_MAINNET },
      }],
      mimeType: 'application/json',
      description: 'On-demand web research digest (free-source curated: Wikipedia + Hacker News + Jina Reader). POST {"query":"..."}; pay per request in USDC on Base mainnet.',
    },
  };

  const app = express();
  app.use(express.json());

  app.get('/health', (_req, res) => res.json({ status: 'ok', service: 'x402-research', payTo }));
  app.get('/metadata', (_req, res) => res.json({
    routes: [{ method: 'POST', path: '/research', price: PRICE, network: NETWORK, payTo, asset: USDC_BASE_MAINNET }],
  }));

  app.use(paymentMiddleware(ROUTES, resourceServer));

  app.post('/research', async (req, res) => {
    const q = (req.body && (req.body.query || req.body.q)) || '';
    try {
      const out = await research(q);
      res.json(out);
    } catch (e) {
      res.status(422).json({ error: 'research failed', detail: String(e && e.message ? e.message : e) });
    }
  });

  return app;
}

const isEntry = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isEntry) {
  try { validateEnv(); } catch (e) { console.error('[boot.env] ' + e.message); process.exit(1); }
  const app = await createApp();
  app.listen(PORT, () => console.log(JSON.stringify({ x402_research_seller: 'up', port: PORT, price: PRICE, network: NETWORK, payTo: process.env.X402_WALLET_ADDRESS })));
}
