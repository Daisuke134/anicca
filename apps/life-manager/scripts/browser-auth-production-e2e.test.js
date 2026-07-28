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
  'opaque-tenant-marker-a',
  'opaque-tenant-marker-b',
  'cookie-a-secret',
  'provider-body-secret',
];
const OUTPUT_KEYS = [
  'mode', 'tenant_count', 'origin', 'context_hashes', 'job_ids',
  'steel_session_ids', 'telegram_evidence_ids', 'released',
];

function terminalFor({ id, markerHash, mode, tenant }) {
  return {
    id,
    uid: tenant,
    status: mode === 'verify-expired-handoff' ? 'handoff_required' : 'completed',
    auth_marker_hash: markerHash,
    receipt: {
      auth_marker_hash: markerHash,
      session_id: `steel-${tenant}`,
      evidence_message_id: `telegram-${tenant}-${id}`,
      steel_released: true,
      provider_receipt: {
        status: mode === 'verify-expired-handoff' ? 'login_required' : 'authenticated',
        handoff_required: mode === 'verify-expired-handoff',
        handoff_reason: mode === 'verify-expired-handoff' ? 'login' : null,
      },
    },
    trace: mode === 'verify-expired-handoff'
      ? [{ stage: 'auth_context_invalidated', meta: { invalidated: true } }]
      : [{ stage: 'auth_context_loaded', meta: { loaded: true } }],
  };
}

function makeDeps({ mutateTerminal } = {}) {
  const calls = [];
  const jobs = new Map();
  let sequence = 0;
  const call = (name, value) => {
    calls.push({ name, value });
    return value;
  };
  return {
    calls,
    durableQueue: {
      async enqueue({ tenant, uid, markerHash, mode }) {
        assert.equal(typeof markerHash, 'string');
        assert.match(markerHash, /^[a-f0-9]{64}$/);
        const id = `job-${tenant}-${++sequence}`;
        jobs.set(id, { id, uid, tenant, mode, auth_marker_hash: markerHash, status: 'queued' });
        return call('durableQueue.enqueue', { id, auth_marker_hash: markerHash });
      },
      async read({ id }) {
        return call('durableQueue.read', jobs.get(id) || null);
      },
    },
    executor: {
      async run({ jobId }) {
        const job = jobs.get(jobId);
        call('executor.claim', { id: jobId });
        call('executor.execute', { id: jobId });
        const terminal = terminalFor({
          id: jobId,
          markerHash: job.auth_marker_hash,
          mode: job.mode,
          tenant: job.tenant,
        });
        jobs.set(jobId, mutateTerminal ? mutateTerminal(terminal, job) : terminal);
        return call('executor.finish', { id: jobId });
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
}

test('rejects an unknown mode without reflecting its value', async () => {
  const mode = `unknown-${RAW_VALUES[2]}`;
  await assert.rejects(
    runBrowserAuthProductionE2E({ mode, env: REQUIRED_ENV, deps: makeDeps() }),
    (error) => {
      assert.equal(error.message, 'Unknown browser auth production E2E mode');
      assertNoSecrets(error.message);
      return true;
    },
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

test('CLI never reflects a secret-like unknown mode to stdout or stderr', () => {
  const child = spawnSync(
    process.execPath,
    [fileURLToPath(new URL('./browser-auth-production-e2e.js', import.meta.url)), `unknown-${RAW_VALUES[2]}`],
    { encoding: 'utf8', env: { ...process.env, ...REQUIRED_ENV } },
  );
  assert.equal(child.status, 1);
  assert.equal(child.stdout, '');
  assert.equal(child.stderr, 'Unknown browser auth production E2E mode\n');
  assertNoSecrets(`${child.stdout}${child.stderr}`);
});

test('executes the durable claim → runtime → finish → terminal readback path before emitting hashes', async () => {
  const deps = makeDeps();
  const result = await runBrowserAuthProductionE2E({
    mode: 'verify-two-tenant-contexts', env: REQUIRED_ENV, deps,
  });

  assertBoundedResult(result, 'verify-two-tenant-contexts');
  assert.deepEqual(
    deps.calls.map(({ name }) => name),
    [
      'durableQueue.enqueue', 'executor.claim', 'executor.execute', 'executor.finish', 'durableQueue.read',
      'durableQueue.enqueue', 'executor.claim', 'executor.execute', 'executor.finish', 'durableQueue.read',
    ],
  );
  assertNoSecrets(JSON.stringify(result));
});

test('rejects nonterminal jobs, missing provider receipts, and unreleased Steel rows', async () => {
  const cases = [
    ['nonterminal', (terminal) => ({ ...terminal, status: 'claimed' })],
    ['missing receipt', (terminal) => ({ ...terminal, receipt: null })],
    ['unreleased Steel', (terminal) => ({ ...terminal, receipt: { ...terminal.receipt, steel_released: false } })],
  ];
  for (const [label, mutateTerminal] of cases) {
    await assert.rejects(
      runBrowserAuthProductionE2E({
        mode: 'verify-two-tenant-contexts', env: REQUIRED_ENV, deps: makeDeps({ mutateTerminal }),
      }),
      new RegExp(label === 'nonterminal' ? 'terminal' : label === 'missing receipt' ? 'provider receipt' : 'Steel release'),
    );
  }
});

test('rejects body-only login text and requires a structured expired handoff plus invalidation', async () => {
  await assert.rejects(
    runBrowserAuthProductionE2E({
      mode: 'verify-expired-handoff',
      env: REQUIRED_ENV,
      deps: makeDeps({
        mutateTerminal: (terminal) => ({
          ...terminal,
          receipt: {
            ...terminal.receipt,
            provider_receipt: { status: `login ${RAW_VALUES[3]}`, body: 'login', handoff_required: false },
          },
        }),
      }),
    }),
    /structured provider login handoff/,
  );
  await assert.rejects(
    runBrowserAuthProductionE2E({
      mode: 'verify-expired-handoff',
      env: REQUIRED_ENV,
      deps: makeDeps({
        mutateTerminal: (terminal) => ({ ...terminal, trace: [{ stage: 'auth_context_invalidated', meta: { invalidated: false } }] }),
      }),
    }),
    /invalidation/,
  );
});

test('rejects missing, same, or unbound durable terminal marker hashes', async () => {
  const cases = [
    ['missing', (terminal) => ({ ...terminal, auth_marker_hash: null })],
    ['unbound', (terminal) => ({ ...terminal, receipt: { ...terminal.receipt, auth_marker_hash: 'f'.repeat(64) } })],
    ['same', (terminal) => ({ ...terminal, auth_marker_hash: 'e'.repeat(64), receipt: { ...terminal.receipt, auth_marker_hash: 'e'.repeat(64) } })],
  ];
  for (const [label, mutateTerminal] of cases) {
    await assert.rejects(
      runBrowserAuthProductionE2E({
        mode: 'verify-two-tenant-contexts', env: REQUIRED_ENV, deps: makeDeps({ mutateTerminal }),
      }),
      new RegExp(label === 'same' ? 'isolated' : 'marker hash'),
    );
  }
});

test('handles an expired login only after terminal provider readback, invalidation, evidence, and Steel release', async () => {
  const deps = makeDeps();
  const result = await runBrowserAuthProductionE2E({
    mode: 'verify-expired-handoff', env: REQUIRED_ENV, deps,
  });
  assertBoundedResult(result, 'verify-expired-handoff');
  assertNoSecrets(JSON.stringify(result));
});
