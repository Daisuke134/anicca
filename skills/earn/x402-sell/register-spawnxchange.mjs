#!/usr/bin/env node
import { chmodSync, existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';
import { privateKeyToAccount } from 'viem/accounts';

import { loadEvmKey } from '../lib/resolve-identity.mjs';
import { validateSpawnxchangeChallenge } from './lib/spawnxchange-channel.mjs';

const API = 'https://spawnxchange.com/api/v1';
const EXPECTED_ADDRESS = '0x3EcCAD24794ca298D25378E9902A251322ea8749';
const USERNAME = 'anicca-settlement';
const CREDENTIALS_PATH = process.env.SPAWNXCHANGE_CREDENTIALS_PATH
  || join(homedir(), '.anicca', 'spawnxchange-credentials.json');

function writeSecureJson(path, value) {
  mkdirSync(dirname(path), { recursive: true, mode: 0o700 });
  const temporary = `${path}.tmp-${process.pid}`;
  writeFileSync(temporary, `${JSON.stringify(value)}\n`, { mode: 0o600, flag: 'wx' });
  chmodSync(temporary, 0o600);
  renameSync(temporary, path);
  chmodSync(path, 0o600);
}

async function jsonRequest(path, init) {
  const response = await fetch(`${API}${path}`, {
    ...init,
    signal: AbortSignal.timeout(20_000),
  });
  const body = await response.json().catch(() => null);
  return { response, body };
}

if (existsSync(CREDENTIALS_PATH)) {
  const existing = JSON.parse(readFileSync(CREDENTIALS_PATH, 'utf8'));
  process.stdout.write(`${JSON.stringify({
    status: 'already_registered',
    agent_id: existing.agent_id || null,
    username: existing.username || null,
    address: existing.address || null,
  })}\n`);
  process.exit(0);
}

for (const [url, marker] of [
  ['https://spawnxchange.com/terms/v1', 'Terms of Use'],
  ['https://spawnxchange.com/license/v1', 'Standard Buyer License'],
]) {
  const response = await fetch(url, { signal: AbortSignal.timeout(20_000) });
  const text = await response.text();
  if (!response.ok || !text.includes(marker) || !text.includes('VERSION: v1')) {
    throw new Error(`SpawnXchange legal document drift: ${url}`);
  }
}

const privateKey = loadEvmKey({ env: process.env });
if (!privateKey) throw new Error('franklin1 wallet key is unavailable');
const account = privateKeyToAccount(privateKey);
if (account.address.toLowerCase() !== EXPECTED_ADDRESS.toLowerCase()) {
  throw new Error(`refusing unexpected SpawnXchange wallet ${account.address}`);
}

const challengeResult = await jsonRequest('/auth/challenge', {
  method: 'POST',
  headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ address: account.address, chain: 'base', action: 'register' }),
});
if (!challengeResult.response.ok || typeof challengeResult.body?.message !== 'string') {
  throw new Error(`SpawnXchange challenge HTTP ${challengeResult.response.status}`);
}
validateSpawnxchangeChallenge({
  message: challengeResult.body.message,
  expectedAddress: account.address,
});
const signature = await account.signMessage({ message: challengeResult.body.message });

const registration = await jsonRequest('/register', {
  method: 'POST',
  headers: { 'content-type': 'application/json' },
  body: JSON.stringify({
    username: USERNAME,
    country: 'JP',
    terms_agreed: true,
    wallets: [{
      chain: 'base',
      address: account.address,
      signature,
      message: challengeResult.body.message,
    }],
  }),
});
if (registration.response.status !== 201) {
  const code = String(registration.body?.error || `http_${registration.response.status}`)
    .replace(/[^A-Za-z0-9_.:-]/g, '_').slice(0, 64);
  throw new Error(`SpawnXchange registration rejected: ${code}`);
}
if (!/^[0-9a-f-]{36}$/i.test(String(registration.body?.agent_id || ''))
    || typeof registration.body?.api_key !== 'string'
    || registration.body.api_key.length < 16) {
  throw new Error('SpawnXchange registration response shape drift');
}

writeSecureJson(CREDENTIALS_PATH, {
  api_key: registration.body.api_key,
  agent_id: registration.body.agent_id,
  username: USERNAME,
  address: account.address,
  chain: 'base',
  registered_at: new Date().toISOString(),
});
process.stdout.write(`${JSON.stringify({
  status: 'registered',
  agent_id: registration.body.agent_id,
  username: USERNAME,
  address: account.address,
  credentials_mode: '0600',
})}\n`);
