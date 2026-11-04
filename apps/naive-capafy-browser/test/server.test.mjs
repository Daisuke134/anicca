import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const operationId = '3dfe52e4-b2e0-4719-8848-65c683c0ed15';
const fixedEmail = 'agent@example.naive';

test('pins the hosted runtime and selects a root Fetch entrypoint', async () => {
  const packageJson = JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
  const packageLock = JSON.parse(fs.readFileSync(new URL('../package-lock.json', import.meta.url), 'utf8'));

  assert.equal(packageJson.engines.node, '22.x');
  assert.equal(packageLock.packages[''].engines.node, '22.x');
  assert.equal(fs.existsSync(new URL('../index.mjs', import.meta.url)), true);
  assert.equal(packageJson.main, 'index.mjs');
  assert.equal(packageJson.scripts.start, 'node src/node.mjs');

  const app = await import('../index.mjs');
  assert.equal(typeof app.default?.fetch, 'function');
  const response = await app.default.fetch(new Request('https://naive-app.example/healthz'));
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { ok: true, app: 'naive-capafy-browser' });
});

async function loadHandler() {
  let mod;
  try {
    mod = await import('../src/server.mjs');
  } catch (error) {
    assert.fail('browser MCP handler module must load: ' + (error?.code ?? 'import_error'));
  }
  assert.equal(typeof mod.createBrowserMcpHandler, 'function');
  return mod.createBrowserMcpHandler;
}

function environment(overrides = {}) {
  return {
    VETTA_MCP_TOKEN: 'platform-app-token',
    NAIVE_API_URL: 'https://api.vetta.sh',
    NAIVE_API_KEY: 'app-scoped-api-key',
    NAIVE_COMPUTER_ID: 'cmp_12345678901234567890123456789012',
    NAIVE_IDENTITY_ID: 'idn_12345678901234567890123456789012',
    CAPAFY_AGENT_EMAIL: fixedEmail,
    CAPAFY_LOGIN_URL: 'https://capafy.ai/login',
    CAPAFY_SIGNUP_URL: 'https://capafy.ai/signup',
    ...overrides,
  };
}

function browserReply(action, url) {
  return Response.json({
    object: 'browser_action', action, url, text: 'Capafy public page', data: null,
    links: null, elements: null, file_id: null, performed: true,
  });
}

function rpcRequest(args, authorization = 'Bearer platform-app-token') {
  return new Request('https://naive-app.example/mcp', {
    method: 'POST',
    headers: { authorization, 'content-type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0', id: 1, method: 'tools/call',
      params: { name: 'capafy_browser', arguments: args },
    }),
  });
}

test('rejects a missing or incorrect App bearer before making a Naive API request', async () => {
  const createHandler = await loadHandler();
  let calls = 0;
  const handler = createHandler({ env: environment(), fetchImpl: async () => { calls += 1; } });

  const response = await handler(rpcRequest({ operation_id: operationId, action: 'observe' }, 'Bearer wrong'));

  assert.equal(response.status, 401);
  assert.equal(calls, 0);
});

test('rejects an off-domain navigation before the SDK can reach Naive', async () => {
  const createHandler = await loadHandler();
  let calls = 0;
  const handler = createHandler({ env: environment(), fetchImpl: async () => { calls += 1; } });

  const response = await handler(rpcRequest({
    operation_id: operationId, action: 'goto', url: 'https://example.com/login',
  }));
  const body = await response.json();

  assert.equal(response.status, 200);
  assert.equal(body.result.isError, true);
  assert.equal(calls, 0);
});

test('opens Capafy through the configured Computer and forwards operation_id as SDK idempotency key', async () => {
  const createHandler = await loadHandler();
  const calls = [];
  const handler = createHandler({
    env: environment(),
    fetchImpl: async (input, init) => {
      calls.push({ url: String(input), headers: new Headers(init?.headers), body: init?.body });
      return browserReply('goto', 'https://capafy.ai/');
    },
  });

  const response = await handler(rpcRequest({
    operation_id: operationId, action: 'goto', url: 'https://capafy.ai/',
  }));
  const body = await response.json();

  assert.equal(response.status, 200);
  assert.equal(body.result.isError, false);
  assert.equal(calls.length, 1);
  assert.match(calls[0].url, /\/v1\/computers\/cmp_12345678901234567890123456789012\/browser\//);
  assert.equal(calls[0].headers.get('authorization'), 'Bearer app-scoped-api-key');
  assert.equal(calls[0].headers.get('idempotency-key'), operationId);
});

test('signup uses only the server-held Identity, email, service and Capafy URL', async () => {
  const createHandler = await loadHandler();
  const calls = [];
  const handler = createHandler({
    env: environment(),
    fetchImpl: async (input, init) => {
      calls.push({ url: String(input), body: JSON.parse(init.body) });
      return browserReply('act', 'https://capafy.ai/signup');
    },
  });

  const response = await handler(rpcRequest({ operation_id: operationId, action: 'signup' }));
  const body = await response.json();

  assert.equal(body.result.isError, false);
  assert.equal(calls.length, 1);
  assert.match(calls[0].url, /\/v1\/computers\/cmp_12345678901234567890123456789012\/browser\//);
  assert.deepEqual(calls[0].body, {
    service: 'capafy.ai',
    url: 'https://capafy.ai/signup',
    identity_id: 'idn_12345678901234567890123456789012',
    email: fixedEmail,
  });
  assert.doesNotMatch(JSON.stringify(body), /app-scoped-api-key|platform-app-token/);
});

test('login uses only the server-held Identity, service and Capafy URL', async () => {
  const createHandler = await loadHandler();
  const calls = [];
  const handler = createHandler({
    env: environment(),
    fetchImpl: async (input, init) => {
      calls.push({ url: String(input), body: JSON.parse(init.body) });
      return browserReply('act', 'https://capafy.ai/login');
    },
  });

  const response = await handler(rpcRequest({ operation_id: operationId, action: 'login' }));
  const body = await response.json();

  assert.equal(body.result.isError, false);
  assert.equal(calls.length, 1);
  assert.deepEqual(calls[0].body, {
    service: 'capafy.ai',
    url: 'https://capafy.ai/login',
    identity_id: 'idn_12345678901234567890123456789012',
  });
  assert.doesNotMatch(JSON.stringify(body), /app-scoped-api-key|platform-app-token/);
});

test('refuses caller-supplied Identity or email values', async () => {
  const createHandler = await loadHandler();
  let calls = 0;
  const handler = createHandler({ env: environment(), fetchImpl: async () => { calls += 1; } });

  const response = await handler(rpcRequest({
    operation_id: operationId, action: 'signup', email: 'someone@example.com',
  }));
  const body = await response.json();

  assert.equal(body.result.isError, true);
  assert.equal(calls, 0);
});

test('rejects malformed and oversized MCP requests without calling the provider', async () => {
  const createHandler = await loadHandler();
  let calls = 0;
  const handler = createHandler({ env: environment(), fetchImpl: async () => { calls += 1; } });

  const malformed = await handler(new Request('https://naive-app.example/mcp', {
    method: 'POST',
    headers: { authorization: 'Bearer platform-app-token', 'content-type': 'application/json' },
    body: '{',
  }));
  const oversized = await handler(new Request('https://naive-app.example/mcp', {
    method: 'POST',
    headers: { authorization: 'Bearer platform-app-token', 'content-type': 'application/json' },
    body: ' '.repeat(65537),
  }));

  assert.equal(malformed.status, 400);
  assert.equal(oversized.status, 413);
  assert.equal(calls, 0);
});
