'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { runMaritimeCycle } = require('./run-cycle.js');
const { recordTenantStateTransition } = require('../lib/maritime-tenant-binding.js');
const UID = 'lm_11111111-1111-4111-8111-111111111111';
const args = ['--tenant', UID, '--occurrence', 'cycle-1', '--date', '2026-10-20'];
test('detached exec prepares its own runtime and invokes only the existing Python wrapper', () => {
  const calls = [];
  const prepared = { config: { tenantId: UID }, env: { AGENT_RUNNER_CONFIG: '/data/tenant/runner.json', LM_CLOUD_MODEL_API_KEY: 'fixture' } };
  const code = runMaritimeCycle(args, { env: { LM_RUNTIME_TENANT_ID: UID }, platform: 'darwin', uid: 501,
    prepareRuntime: input => { calls.push(['prepare', input]); return prepared; },
    spawnImpl: (...input) => { calls.push(['spawn', ...input]); return { status: 0 }; } });
  assert.equal(code, 0);
  assert.equal(calls[0][0], 'prepare');
  assert.deepEqual(calls[1], ['spawn', 'python3', ['/app/skills/capafy-autopublish/scripts/cloud_cycle.py', ...args],
    { cwd: '/app', env: prepared.env, stdio: 'inherit' }]);
  assert.equal(JSON.stringify(calls[1].slice(1,3)).includes('fixture'), false);
});
test('Linux root drops factory privileges and removes the relay token without a root fallback',()=>{
 const calls=[];
 const status=runMaritimeCycle(args,{env:{LM_RUNTIME_TENANT_ID:UID},platform:'linux',uid:0,
  prepareRuntime:()=>({env:{LM_CLOUD_MODEL_API_KEY:'fixture-model',LM_WAKE_RELAY_TOKEN:'fixture-root-relay'}}),
  spawnImpl:(...input)=>{calls.push(input);return {error:new Error('missing setpriv')};}});
 assert.equal(status,2);assert.equal(calls.length,1);
 assert.equal(calls[0][0],'/usr/bin/setpriv');
 assert.deepEqual(calls[0][1].slice(0,7),['--reuid=10001','--regid=10001','--clear-groups','--bounding-set=-all','--inh-caps=-all','--ambient-caps=-all','--no-new-privs']);
 assert.equal(calls[0][1][7],'python3');assert.equal(calls[0][2].env.LM_WAKE_RELAY_TOKEN,undefined);
 assert.equal(calls[0][2].env.LM_CLOUD_MODEL_API_KEY,'fixture-model');
});
test('caller cannot change tenant, inject options, duplicate arguments, or supply invalid dates', () => {
  for (const argv of [ ['--tenant', '../other', ...args.slice(2)], [...args, '--shell', 'unsafe'],
    [...args, '--date', '2026-10-21'], [...args.slice(0,-1), '2026-02-30'],
    ['--tenant', 'lm_22222222-2222-4222-8222-222222222222', ...args.slice(2)] ]) {
    let calls = 0;
    assert.throws(() => runMaritimeCycle(argv, { env: { LM_RUNTIME_TENANT_ID: UID }, prepareRuntime: () => { calls++; } }), /invalid/);
    assert.equal(calls, 0);
  }
});
test('tenant preparation is wired in: an unbound tenant cycle carries the self-signup directive', (t) => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'lm-run-cycle-'));
  t.after(() => fs.rmSync(home, { recursive: true, force: true }));
  let spawned;
  const code = runMaritimeCycle(args, { env: { LM_RUNTIME_TENANT_ID: UID }, platform: 'darwin', uid: 501,
    prepareRuntime: () => ({ env: { LIFE_MANAGER_STATE_HOME: home } }),
    spawnImpl: (...input) => { spawned = input; return { status: 0 }; } });
  assert.equal(code, 0);
  const directive = JSON.parse(spawned[2].env.LM_TENANT_SIGNUP_JSON);
  assert.equal(directive.tenantId, UID);
  assert.equal(directive.credentialPath, path.join(home, 'vault', 'capafy', 'credential'));
  assert.equal(spawned[2].env.LM_CAPAFY_BINDING_JSON, undefined);
});
test('tenant preparation is wired in: a bound tenant cycle carries only the references-only binding', (t) => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'lm-run-cycle-'));
  t.after(() => fs.rmSync(home, { recursive: true, force: true }));
  const credential = path.join(home, 'vault', 'capafy', 'credential');
  fs.mkdirSync(path.dirname(credential), { recursive: true, mode: 0o700 });
  fs.writeFileSync(credential, '{"secret":"fixture"}', { mode: 0o600 });
  fs.mkdirSync(path.join(home, 'vault', 'capafy', 'browser-session'), { recursive: true, mode: 0o700 });
  const binding = { tenantId: UID, provider: 'capafy', subjectId: 'seller-tenant-1',
    credentialRef: 'tenant-home/vault/capafy/credential', browserSessionRef: 'tenant-home/vault/capafy/browser-session' };
  recordTenantStateTransition({ stateHome: home, tenantId: UID, platformId: 'capafy', next: 'signed_up' });
  recordTenantStateTransition({ stateHome: home, tenantId: UID, platformId: 'capafy', next: 'bound', binding });
  let spawned;
  const code = runMaritimeCycle(args, { env: { LM_RUNTIME_TENANT_ID: UID }, platform: 'darwin', uid: 501,
    prepareRuntime: () => ({ env: { LIFE_MANAGER_STATE_HOME: home } }),
    spawnImpl: (...input) => { spawned = input; return { status: 0 }; } });
  assert.equal(code, 0);
  assert.deepEqual(JSON.parse(spawned[2].env.LM_CAPAFY_BINDING_JSON), binding);
  assert.equal(JSON.stringify(spawned[2].env).includes('fixture'), false);
  assert.equal(spawned[2].env.LM_TENANT_SIGNUP_JSON, undefined);
  const manifest = path.join(home, 'runtime', 'capafy-publisher', 'sessions', 'capafy', 'session.json');
  assert.ok(fs.existsSync(manifest));
});
test('an unresolvable tenant binding stops the cycle before spawn', (t) => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'lm-run-cycle-'));
  t.after(() => fs.rmSync(home, { recursive: true, force: true }));
  const binding = { tenantId: UID, provider: 'capafy', subjectId: 'seller-tenant-1',
    credentialRef: 'tenant-home/vault/capafy/credential', browserSessionRef: 'tenant-home/vault/capafy/browser-session' };
  recordTenantStateTransition({ stateHome: home, tenantId: UID, platformId: 'capafy', next: 'signed_up' });
  recordTenantStateTransition({ stateHome: home, tenantId: UID, platformId: 'capafy', next: 'bound', binding });
  let calls = 0;
  assert.throws(() => runMaritimeCycle(args, { env: { LM_RUNTIME_TENANT_ID: UID }, platform: 'darwin', uid: 501,
    prepareRuntime: () => ({ env: { LIFE_MANAGER_STATE_HOME: home } }),
    spawnImpl: () => { calls++; return { status: 0 }; } }), /tenant_binding_unresolvable/);
  assert.equal(calls, 0);
});
test('child failures remain nonzero and never get rewritten as completed', () => {
  for (const result of [{ status: 2 }, { status: null, signal: 'SIGTERM' }, { error: new Error('private') }]) {
    assert.notEqual(runMaritimeCycle(args, { env: { LM_RUNTIME_TENANT_ID: UID },
      prepareRuntime: () => ({ env: {} }), spawnImpl: () => result }), 0);
  }
});
