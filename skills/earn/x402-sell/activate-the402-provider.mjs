#!/usr/bin/env node
import { chmodSync, existsSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { randomBytes } from 'node:crypto';

const pendingPath = process.env.THE402_PENDING_CREDENTIALS_PATH
  || join(homedir(), '.anicca', 'the402-credentials.json.pending');
const credentialsPath = process.env.THE402_CREDENTIALS_PATH
  || join(homedir(), '.anicca', 'the402-credentials.json');
const existing = JSON.parse(readFileSync(pendingPath, 'utf8'));
const activated = existsSync(credentialsPath)
  ? JSON.parse(readFileSync(credentialsPath, 'utf8'))
  : null;
const auth = activated || existing;
if (typeof auth.participant_id !== 'string' || typeof auth.api_key !== 'string') {
  throw new Error('pending registration credentials are invalid');
}

const webhookUrl = 'https://aniccanomac-mini-1.tail7a0ba4.ts.net/webhooks/the402';
const configuredWebhookSecret = typeof activated?.webhook_secret === 'string'
  ? activated.webhook_secret
  : typeof existing.webhook_secret === 'string'
    ? existing.webhook_secret
  : `whsec_${randomBytes(32).toString('hex')}`;
const response = await fetch(`https://api.the402.ai/v1/participants/${auth.participant_id}`, {
  method: 'PUT',
  headers: {
    'content-type': 'application/json',
    'X-API-Key': auth.api_key,
  },
  body: JSON.stringify({
    name: 'Anicca Autonomous Research',
    description: 'Autonomous evidence-backed research briefs for AI agents, including x402 ecosystem adoption and implementation analysis.',
    type: 'both',
    webhook_url: webhookUrl,
    webhook_secret: configuredWebhookSecret,
    capabilities: ['research', 'x402', 'ai-agents', 'technical-writing'],
  }),
});
const body = await response.json().catch(() => null);
if (!response.ok) {
  throw new Error(`provider activation failed HTTP ${response.status}: ${body?.error || 'unknown_error'}`);
}

const root = body?.data || body;
const webhookSecret = root?.webhook_secret || root?.webhookSecret
  || root?.credentials?.webhook_secret || root?.credentials?.webhookSecret
  || configuredWebhookSecret;
const stored = {
  participant_id: auth.participant_id,
  api_key: auth.api_key,
  webhook_secret: webhookSecret,
  type: root?.type || 'both',
  payer: activated?.payer || existing.wallet,
  webhook_url: webhookUrl,
  referral_code: activated?.referral_code || existing.referral_code,
  activated_at: new Date().toISOString(),
};
const temporary = `${credentialsPath}.tmp-${process.pid}`;
writeFileSync(temporary, `${JSON.stringify(stored)}\n`, { mode: 0o600, flag: 'wx' });
chmodSync(temporary, 0o600);
renameSync(temporary, credentialsPath);

process.stdout.write(`${JSON.stringify({
  activated: true,
  participantId: stored.participant_id,
  type: stored.type,
  webhookUrl: stored.webhook_url,
  webhookSecretPresent: typeof stored.webhook_secret === 'string',
  credentialsPath,
})}\n`);
