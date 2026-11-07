'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {
  parseTenantBinding, tenantCredentialRef, tenantBrowserSessionRef,
  loadTenantPlatformState, recordTenantStateTransition,
  resolveTenantBinding, prepareTenantCycle,
} = require('./maritime-tenant-binding.js');
const UID = 'lm_11111111-1111-4111-8111-111111111111';
const OTHER = 'lm_22222222-2222-4222-8222-222222222222';
const SECRET = 'FIXTURE-SECRET-DO-NOT-LEAK';
function binding(overrides = {}) {
  return { tenantId: UID, provider: 'capafy', subjectId: 'seller-tenant-1',
    credentialRef: tenantCredentialRef('capafy'), browserSessionRef: tenantBrowserSessionRef('capafy'), ...overrides };
}
function tenantHome(t) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'lm-tenant-binding-'));
  t.after(() => fs.rmSync(home, { recursive: true, force: true }));
  return home;
}
function writeVaultFixture(home) {
  const credential = path.join(home, 'vault', 'capafy', 'credential');
  fs.mkdirSync(path.dirname(credential), { recursive: true, mode: 0o700 });
  fs.writeFileSync(credential, JSON.stringify({ secret: SECRET }), { mode: 0o600 });
  const session = path.join(home, 'vault', 'capafy', 'browser-session');
  fs.mkdirSync(session, { recursive: true, mode: 0o700 });
  return { credential, session };
}
test('binding is the references-only Stage 1 shape and never a value carrier', () => {
  const parsed = parseTenantBinding(binding(), { tenantId: UID, platformId: 'capafy' });
  assert.deepEqual({ ...parsed }, binding());
  assert.equal(tenantCredentialRef('capafy'), 'tenant-home/vault/capafy/credential');
  assert.equal(tenantBrowserSessionRef('capafy'), 'tenant-home/vault/capafy/browser-session');
  // subjectId-only bindings stay valid at parse time (cloud_cycle.py contract).
  assert.equal(parseTenantBinding({ tenantId: UID, provider: 'capafy', subjectId: 's' }, { tenantId: UID, platformId: 'capafy' }).subjectId, 's');
  for (const bad of [
    binding({ tenantId: OTHER }),                       // foreign tenant
    binding({ provider: 'promptbase' }),                 // provider is not the cycle platform
    binding({ subjectId: '' }),
    binding({ subjectId: { secret: SECRET } }),          // object where a reference belongs
    binding({ credentialRef: { secret: SECRET } }),      // secret object, not a reference
    binding({ credentialRef: '/etc/passwd' }),           // absolute path escape
    binding({ credentialRef: 'tenant-home/vault/promptbase/credential' }), // other platform vault
    binding({ credentialRef: 'tenant-home/vault/capafy/../agent-mail' }),  // traversal
    binding({ browserSessionRef: 'https://example.invalid/session' }),
    { ...binding(), extra: 'nope' },                     // unknown key
    null, [], 'binding',
  ]) {
    assert.throws(() => parseTenantBinding(bad, { tenantId: UID, platformId: 'capafy' }), /tenant_binding_invalid/);
  }
});
test('platform state persists in the tenant home and only advances in order', (t) => {
  const home = tenantHome(t);
  const fresh = loadTenantPlatformState({ stateHome: home, tenantId: UID, platformId: 'capafy' });
  assert.equal(fresh.state, 'none');
  assert.equal(fresh.binding, null);
  const signed = recordTenantStateTransition({ stateHome: home, tenantId: UID, platformId: 'capafy', next: 'signed_up', at: '2026-11-07T00:00:00.000Z' });
  assert.equal(signed.state, 'signed_up');
  const bound = recordTenantStateTransition({ stateHome: home, tenantId: UID, platformId: 'capafy', next: 'bound', binding: binding(), at: '2026-11-07T00:01:00.000Z' });
  assert.equal(bound.state, 'bound');
  assert.deepEqual({ ...bound.binding }, binding());
  const reloaded = loadTenantPlatformState({ stateHome: home, tenantId: UID, platformId: 'capafy' });
  assert.equal(reloaded.state, 'bound');
  assert.deepEqual(reloaded.history.map(h => `${h.from}->${h.to}`), ['none->signed_up', 'signed_up->bound']);
  assert.throws(() => recordTenantStateTransition({ stateHome: home, tenantId: UID, platformId: 'capafy', next: 'signed_up' }), /tenant_signup_state_invalid/);
  const file = path.join(home, 'state', 'capafy-autopublish', 'signup-state.json');
  assert.equal(fs.statSync(file).mode & 0o077, 0);
  const corrupt = path.join(home, 'state', 'capafy-autopublish', 'signup-state.json');
  fs.writeFileSync(corrupt, '{"state":"bound","tenantId":"' + OTHER + '"}');
  assert.throws(() => loadTenantPlatformState({ stateHome: home, tenantId: UID, platformId: 'capafy' }), /tenant_signup_state_invalid/);
});
test('resolution materializes a paths-only publisher session and never reads credential values', (t) => {
  const home = tenantHome(t);
  const { credential, session } = writeVaultFixture(home);
  const publisherStateHome = path.join(home, 'runtime', 'capafy-publisher');
  const resolved = resolveTenantBinding({ binding: binding(), tenantId: UID, platformId: 'capafy', stateHome: home, publisherStateHome, now: '2026-11-07T00:02:00.000Z' });
  assert.equal(resolved.status, 'resolved');
  assert.equal(resolved.credentialPath, credential);
  assert.equal(resolved.browserSessionPath, session);
  const manifest = JSON.parse(fs.readFileSync(resolved.manifestPath, 'utf8'));
  assert.equal(manifest.tenantId, UID);
  assert.equal(manifest.provider, 'capafy');
  assert.equal(manifest.subjectId, 'seller-tenant-1');
  assert.equal(manifest.credentialPath, credential);
  assert.equal(JSON.stringify(manifest).includes(SECRET), false);
  assert.equal(fs.statSync(resolved.manifestPath).mode & 0o077, 0);
});
test('resolution fails closed on missing, exposed, or escaping vault material', (t) => {
  const home = tenantHome(t);
  const publisherStateHome = path.join(home, 'runtime', 'capafy-publisher');
  const attempt = (b) => () => resolveTenantBinding({ binding: b, tenantId: UID, platformId: 'capafy', stateHome: home, publisherStateHome });
  assert.throws(attempt(binding()), /tenant_binding_unresolvable/); // nothing in the vault yet
  const { credential, session } = writeVaultFixture(home);
  fs.rmSync(session, { recursive: true }); // credential without its browser session cannot resolve
  assert.throws(attempt(binding()), /tenant_binding_unresolvable/);
  fs.mkdirSync(session, { mode: 0o700 });
  assert.equal(attempt(binding())().status, 'resolved');
  fs.chmodSync(credential, 0o644); // group/other-readable credential material is not resolvable
  assert.throws(attempt(binding()), /tenant_binding_unresolvable/);
  fs.chmodSync(credential, 0o600);
  fs.rmSync(credential);
  fs.symlinkSync('/etc/passwd', credential); // symlink escape out of the tenant vault
  assert.throws(attempt(binding()), /tenant_binding_unresolvable/);
  assert.throws(attempt({ tenantId: UID, provider: 'capafy', subjectId: 's' }), /tenant_binding_unresolvable/); // refs required to resolve
});
test('cycle preparation emits a self-signup directive when no binding exists', (t) => {
  const home = tenantHome(t);
  const prepared = prepareTenantCycle({ tenantId: UID, env: {}, stateHome: home, publisherStateHome: path.join(home, 'runtime', 'capafy-publisher') });
  assert.equal(prepared.mode, 'self_signup');
  assert.equal(prepared.env.LM_CAPAFY_BINDING_JSON, undefined);
  const directive = JSON.parse(prepared.env.LM_TENANT_SIGNUP_JSON);
  assert.equal(directive.tenantId, UID);
  assert.equal(directive.platformId, 'capafy');
  assert.equal(directive.identityRef, 'tenant-home/vault/agent-mail');
  assert.equal(directive.identityPath, path.join(home, 'vault', 'agent-mail'));
  assert.equal(directive.credentialPath, path.join(home, 'vault', 'capafy', 'credential'));
  assert.equal(directive.browserSessionPath, path.join(home, 'vault', 'capafy', 'browser-session'));
  assert.equal(directive.credentialRef, 'tenant-home/vault/capafy/credential');
  assert.equal(directive.stateFile, path.join(home, 'state', 'capafy-autopublish', 'signup-state.json'));
});
test('cycle preparation resolves a persisted binding and advances signed_up to bound', (t) => {
  const home = tenantHome(t);
  writeVaultFixture(home);
  recordTenantStateTransition({ stateHome: home, tenantId: UID, platformId: 'capafy', next: 'signed_up' });
  recordTenantStateTransition({ stateHome: home, tenantId: UID, platformId: 'capafy', next: 'bound', binding: binding() });
  // Rewind to signed_up with the binding attached, as the signup cycle leaves it.
  const stateFile = path.join(home, 'state', 'capafy-autopublish', 'signup-state.json');
  const record = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
  record.state = 'signed_up';
  fs.writeFileSync(stateFile, JSON.stringify(record), { mode: 0o600 });
  const prepared = prepareTenantCycle({ tenantId: UID, env: {}, stateHome: home, publisherStateHome: path.join(home, 'runtime', 'capafy-publisher') });
  assert.equal(prepared.mode, 'bound');
  assert.deepEqual(JSON.parse(prepared.env.LM_CAPAFY_BINDING_JSON), binding());
  assert.equal(prepared.env.LM_TENANT_SIGNUP_JSON, undefined);
  assert.equal(loadTenantPlatformState({ stateHome: home, tenantId: UID, platformId: 'capafy' }).state, 'bound');
  assert.ok(fs.existsSync(prepared.resolution.manifestPath));
});
test('cycle preparation accepts the Maritime env binding route and rejects foreign bindings', (t) => {
  const home = tenantHome(t);
  writeVaultFixture(home);
  const prepared = prepareTenantCycle({ tenantId: UID, env: { LM_CAPAFY_BINDING_JSON: JSON.stringify(binding()) }, stateHome: home, publisherStateHome: path.join(home, 'runtime', 'capafy-publisher') });
  assert.equal(prepared.mode, 'bound');
  assert.equal(loadTenantPlatformState({ stateHome: home, tenantId: UID, platformId: 'capafy' }).state, 'bound');
  assert.throws(() => prepareTenantCycle({ tenantId: UID, env: { LM_CAPAFY_BINDING_JSON: JSON.stringify(binding({ tenantId: OTHER })) }, stateHome: home, publisherStateHome: home }), /tenant_binding_invalid/);
  assert.throws(() => prepareTenantCycle({ tenantId: UID, env: { LM_CAPAFY_BINDING_JSON: '{broken' }, stateHome: home, publisherStateHome: home }), /tenant_binding_invalid/);
});
