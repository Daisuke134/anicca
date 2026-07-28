import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { runBrowserAuthProductionE2E } from './browser-auth-production-e2e.js';

const REQUIRED_ENV = {
  BROWSER_AUTH_PRODUCTION_ORIGIN: 'https://app.example.test',
  BROWSER_AUTH_TENANT_A_UID: 'tenant-a',
  BROWSER_AUTH_TENANT_B_UID: 'tenant-b',
  LM_BROWSER_SESSION_KEY: '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
  LM_FEEDBACK_DATABASE_URL: 'postgresql://user:password@db.example.test/life_manager',
  LM_TELEGRAM_BOT_TOKEN: 'telegram-bot-token-secret',
  BROWSER_AUTH_TELEGRAM_CHAT_ID: '12345',
};

const RAW_VALUES = [
  'tenant-a@example.test',
  'tenant-b@example.test',
  'cookie-a-secret',
  'cookie-b-secret',
  'provider-body-secret',
];

const OUTPUT_KEYS = [
  'mode',
  'tenant_count',
  'origin',
  'context_hashes',
  'job_ids',
  'steel_session_ids',
  'telegram_evidence_ids',
  'released',
];

function makeDeps() {
  const calls = [];
  const markerA = 'opaque-tenant-marker-a';
  const markerB = 'opaque-tenant-marker-b';
  const contexts = new Map();
  const jobs = new Map();
  let sequence = 0;

  const call = (name, value) => {
    calls.push({ name, value });
    return value;
  };

  return {
    calls,
    authStore: {
      async readTenantAuth({ tenant }) {
        return call('authStore.readTenantAuth', {
          tenant,
          email: tenant === 'tenant-a' ? RAW_VALUES[0] : RAW_VALUES[1],
          cookie: tenant === 'tenant-a' ? RAW_VALUES[2] : RAW_VALUES[3],
          marker: tenant === 'tenant-a' ? markerA : markerB,
        });
      },
    },
    steel: {
      async createSession({ tenant }) {
        return call('steel.createSession', { id: `steel-${tenant}` });
      },
      async createContext({ sessionId, auth }) {
        const context = { id: `context-${sessionId}`, marker: auth.marker };
        contexts.set(context.id, context);
        return call('steel.createContext', context);
      },
      async releaseSession({ sessionId }) {
        return call('steel.releaseSession', { id: sessionId, released: true });
      },
    },
    durableQueue: {
      async enqueue({ tenant, contextHash }) {
        const id = `job-${tenant}-${++sequence}`;
        jobs.set(id, { id, tenant, contextHash });
        return call('durableQueue.enqueue', { id });
      },
      async read({ id }) {
        return call('durableQueue.read', jobs.get(id));
      },
    },
    runtime: {
      async execute({ jobId, contextId }) {
        return call('runtime.execute', { jobId, contextId, providerRequestId: `provider-${jobId}` });
      },
    },
    provider: {
      async readback({ providerRequestId, runtime }) {
        return call('provider.readback', {
          providerRequestId,
          accepted: true,
          handoffRequired: runtime.expiredLogin === true,
          body: RAW_VALUES[4],
        });
      },
    },
    telegram: {
      async sendEvidence({ tenant, jobId }) {
        return call('telegram.sendEvidence', { id: `telegram-${tenant}-${jobId}` });
      },
    },
  };
}

function assertBoundedResult(result, mode) {
  assert.deepEqual(Object.keys(result).sort(), OUTPUT_KEYS.slice().sort());
  assert.equal(result.mode, mode);
  assert.equal(result.tenant_count, 2);
  assert.equal(result.origin, REQUIRED_ENV.BROWSER_AUTH_PRODUCTION_ORIGIN);
  assert.equal(result.context_hashes.length, 2);
  assert.equal(new Set(result.context_hashes).size, 2);
  assert.equal(result.job_ids.length, 2);
  assert.equal(result.steel_session_ids.length, 2);
  assert.equal(result.telegram_evidence_ids.length, 2);
  assert.equal(result.released, true);
}

function assertNoSecrets(output) {
  for (const [name, secret] of Object.entries(REQUIRED_ENV)) {
    if (name === 'BROWSER_AUTH_PRODUCTION_ORIGIN' || name.endsWith('_UID') || name === 'BROWSER_AUTH_TELEGRAM_CHAT_ID') continue;
    assert.doesNotMatch(output, new RegExp(secret.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
  for (const secret of RAW_VALUES) {
    assert.doesNotMatch(output, new RegExp(secret.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
  assert.doesNotMatch(output, /opaque-tenant-marker-[ab]/);
}

test('rejects an unknown mode', async () => {
  await assert.rejects(
    runBrowserAuthProductionE2E({ mode: 'unknown', env: REQUIRED_ENV, deps: makeDeps() }),
    /Unknown browser auth production E2E mode: unknown/,
  );
});

test('rejects missing required environment variables by name only', async () => {
  const env = { ...REQUIRED_ENV };
  delete env.LM_BROWSER_SESSION_KEY;
  delete env.BROWSER_AUTH_TENANT_B_UID;

  await assert.rejects(
    runBrowserAuthProductionE2E({ mode: 'seed-two-tenant-contexts', env, deps: makeDeps() }),
    (error) => {
      assert.match(error.message, /BROWSER_AUTH_TENANT_B_UID/);
      assert.match(error.message, /LM_BROWSER_SESSION_KEY/);
      assertNoSecrets(error.message);
      return true;
    },
  );
});

test('CLI writes no sensitive value to stdout or stderr when configuration is rejected', () => {
  const env = {
    ...process.env,
    ...REQUIRED_ENV,
    BROWSER_AUTH_TENANT_A_EMAIL: RAW_VALUES[0],
    BROWSER_AUTH_TENANT_A_COOKIE: RAW_VALUES[2],
    BROWSER_AUTH_PROVIDER_BODY: RAW_VALUES[4],
  };
  delete env.LM_BROWSER_SESSION_KEY;
  const child = spawnSync(
    process.execPath,
    [fileURLToPath(new URL('./browser-auth-production-e2e.js', import.meta.url)), 'seed-two-tenant-contexts'],
    { encoding: 'utf8', env },
  );

  assert.equal(child.status, 1);
  assert.equal(child.stdout, '');
  assert.match(child.stderr, /LM_BROWSER_SESSION_KEY/);
  assertNoSecrets(`${child.stdout}${child.stderr}`);
});

test('seeds two isolated tenant contexts with bounded, opaque output', async () => {
  const deps = makeDeps();
  const result = await runBrowserAuthProductionE2E({
    mode: 'seed-two-tenant-contexts',
    env: REQUIRED_ENV,
    deps,
  });

  assertBoundedResult(result, 'seed-two-tenant-contexts');
  assert.deepEqual(
    deps.calls.map(({ name }) => name),
    [
      'authStore.readTenantAuth', 'steel.createSession', 'steel.createContext', 'durableQueue.enqueue',
      'durableQueue.read', 'runtime.execute', 'provider.readback', 'telegram.sendEvidence', 'steel.releaseSession',
      'authStore.readTenantAuth', 'steel.createSession', 'steel.createContext', 'durableQueue.enqueue',
      'durableQueue.read', 'runtime.execute', 'provider.readback', 'telegram.sendEvidence', 'steel.releaseSession',
    ],
  );
  assertNoSecrets(JSON.stringify(result));
});

test('verifies two tenants through durable runtime, provider readback, Telegram evidence, and release', async () => {
  const deps = makeDeps();
  const result = await runBrowserAuthProductionE2E({
    mode: 'verify-two-tenant-contexts',
    env: REQUIRED_ENV,
    deps,
  });

  assertBoundedResult(result, 'verify-two-tenant-contexts');
  const names = deps.calls.map(({ name }) => name);
  for (const requiredCall of [
    'authStore.readTenantAuth', 'steel.createSession', 'steel.createContext', 'durableQueue.enqueue',
    'durableQueue.read', 'runtime.execute', 'provider.readback', 'telegram.sendEvidence', 'steel.releaseSession',
  ]) assert.ok(names.includes(requiredCall), `expected ${requiredCall}`);
  assert.ok(names.lastIndexOf('steel.releaseSession') > names.lastIndexOf('provider.readback'));
  assertNoSecrets(JSON.stringify(result));
});

test('handles an expired login by producing evidence only after provider readback and releasing Steel', async () => {
  const deps = makeDeps();
  deps.runtime.execute = async ({ jobId, contextId }) => {
    deps.calls.push({ name: 'runtime.execute', value: { jobId, contextId, expired: true } });
    return { jobId, contextId, providerRequestId: `expired-${jobId}`, expiredLogin: true };
  };

  const result = await runBrowserAuthProductionE2E({
    mode: 'verify-expired-handoff',
    env: REQUIRED_ENV,
    deps,
  });

  assertBoundedResult(result, 'verify-expired-handoff');
  const names = deps.calls.map(({ name }) => name);
  assert.ok(names.includes('provider.readback'));
  assert.ok(names.includes('telegram.sendEvidence'));
  assert.ok(names.lastIndexOf('steel.releaseSession') > names.lastIndexOf('provider.readback'));
  assertNoSecrets(JSON.stringify(result));
});
