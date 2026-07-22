#!/usr/bin/env node
import { chmodSync, mkdirSync, renameSync, writeFileSync, existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';
import { createWalletClient, http } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { base } from 'viem/chains';
import { wrapFetchWithPayment } from 'x402-fetch';

import { loadEvmKey } from '../lib/resolve-identity.mjs';
import { validateThe402RegistrationChallenge } from './lib/the402-channel.mjs';
import { SELF_WALLETS } from './lib/self-wallets.mjs';

const REGISTER_URL = 'https://api.the402.ai/v1/register';
const WEBHOOK_URL = 'https://aniccanomac-mini-1.tail7a0ba4.ts.net/webhooks/the402';
const EXPECTED_PAYER = '0x3EcCAD24794ca298D25378E9902A251322ea8749';
const credentialsPath = process.env.THE402_CREDENTIALS_PATH
  || join(homedir(), '.anicca', 'the402-credentials.json');

function writeSecureJson(path, value) {
  mkdirSync(dirname(path), { recursive: true, mode: 0o700 });
  const temporary = `${path}.tmp-${process.pid}`;
  writeFileSync(temporary, `${JSON.stringify(value)}\n`, { mode: 0o600, flag: 'wx' });
  chmodSync(temporary, 0o600);
  renameSync(temporary, path);
}

function responseShape(value, depth = 0) {
  if (!value || typeof value !== 'object' || depth > 2) return typeof value;
  return Object.fromEntries(Object.entries(value).map(([key, child]) => [
    key,
    child && typeof child === 'object' ? responseShape(child, depth + 1) : typeof child,
  ]));
}

if (existsSync(credentialsPath) && process.env.THE402_REREGISTER !== '1') {
  throw new Error(`credentials already exist at ${credentialsPath}; refusing another paid registration`);
}

const privateKey = loadEvmKey({ env: process.env });
if (!privateKey) throw new Error('franklin1 wallet key is unavailable');
const account = privateKeyToAccount(privateKey);
if (account.address.toLowerCase() !== EXPECTED_PAYER.toLowerCase()) {
  throw new Error(`refusing unexpected payer ${account.address}`);
}

const registration = {
  name: 'Anicca Autonomous Research',
  description: 'Autonomous evidence-backed research briefs for AI agents, including x402 ecosystem adoption and implementation analysis.',
  type: 'provider',
  webhook_url: WEBHOOK_URL,
  capabilities: ['research', 'x402', 'ai-agents', 'technical-writing'],
};
const requestInit = {
  method: 'POST',
  headers: { 'content-type': 'application/json' },
  body: JSON.stringify(registration),
};

const challengeResponse = await fetch(REGISTER_URL, requestInit);
if (challengeResponse.status !== 402) {
  throw new Error(`expected registration HTTP 402, received ${challengeResponse.status}`);
}
validateThe402RegistrationChallenge(await challengeResponse.json(), { selfWallets: SELF_WALLETS });

const wallet = createWalletClient({
  account,
  chain: base,
  transport: http('https://mainnet.base.org'),
});
const paidFetch = wrapFetchWithPayment(fetch, wallet);
const response = await paidFetch(REGISTER_URL, requestInit);
const body = await response.json().catch(() => null);
if (!response.ok) throw new Error(`registration failed HTTP ${response.status}`);
const root = body?.data || body;
const participantId = root?.participant_id || root?.participantId || root?.participant?.id;
const apiKey = root?.api_key || root?.apiKey || root?.credentials?.api_key || root?.credentials?.apiKey;
const webhookSecret = root?.webhook_secret || root?.webhookSecret
  || root?.credentials?.webhook_secret || root?.credentials?.webhookSecret;
if (typeof participantId !== 'string' || typeof apiKey !== 'string') {
  const pendingPath = `${credentialsPath}.pending`;
  writeSecureJson(pendingPath, body);
  throw new Error(`registration response shape mismatch; preserved securely at ${pendingPath}; shape=${JSON.stringify(responseShape(body))}`);
}

if (typeof webhookSecret !== 'string') {
  const pendingPath = `${credentialsPath}.pending`;
  writeSecureJson(pendingPath, root);
  process.stdout.write(`${JSON.stringify({
    registered: true,
    participantId,
    type: root.type || 'agent',
    payer: account.address,
    webhookUrl: WEBHOOK_URL,
    requiresActivation: true,
    pendingPath,
  })}\n`);
  process.exit(0);
}

const stored = {
  participant_id: participantId,
  api_key: apiKey,
  webhook_secret: webhookSecret,
  type: root.type || root.participant?.type || 'provider',
  payer: account.address,
  webhook_url: WEBHOOK_URL,
  registered_at: new Date().toISOString(),
};
writeSecureJson(credentialsPath, stored);

process.stdout.write(`${JSON.stringify({
  registered: true,
  participantId: stored.participant_id,
  type: stored.type,
  payer: stored.payer,
  webhookUrl: stored.webhook_url,
  credentialsPath,
})}\n`);
