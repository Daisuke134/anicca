'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const { TENANT_PLATFORMS, advanceTenantPlatformState } = require('./maritime-tenant-signup.js');
// Tenant credential binding (PR #8745 remainder): the references-only binding
// {tenantId, provider, subjectId, credentialRef, browserSessionRef} is the only
// thing that travels (Maritime env / cycle env / state file). Credential VALUES
// never leave the tenant home vault: this layer validates references, persists
// the signup state machine, and resolves references into a paths-only publisher
// session manifest under the tenant publisher state home. It never opens the
// credential material itself.
const UID = /^lm_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const BINDING_KEYS = new Set(['tenantId', 'provider', 'subjectId', 'credentialRef', 'browserSessionRef']);
const STATES = new Set(['none', 'signed_up', 'bound', 'first_action_done']);
const REF = /^tenant-home\/vault\/([a-z][a-z0-9-]*)\/([A-Za-z0-9][A-Za-z0-9._-]{0,63})$/;
// The cycle host (cloud_cycle.py) reads the binding from this env name; the
// self-signup directive travels under its own name and is prompt-embedded there.
const BINDING_ENV_BY_PLATFORM = Object.freeze({ capafy: 'LM_CAPAFY_BINDING_JSON' });
const SIGNUP_DIRECTIVE_ENV = 'LM_TENANT_SIGNUP_JSON';
function invalidBinding() { throw new Error('tenant_binding_invalid'); }
function unresolvable() { throw new Error('tenant_binding_unresolvable'); }
function invalidState() { throw new Error('tenant_signup_state_invalid'); }
function platformFor(platformId) {
  const platform = TENANT_PLATFORMS.find(p => p.id === platformId);
  if (!platform) invalidBinding();
  return platform;
}
function tenantCredentialRef(platformId) { return `tenant-home/vault/${platformId}/credential`; }
function tenantBrowserSessionRef(platformId) { return `tenant-home/vault/${platformId}/browser-session`; }
function parseRef(value, platformId) {
  if (typeof value !== 'string') invalidBinding();
  const match = REF.exec(value);
  if (!match || match[1] !== platformId || match[2].includes('..')) invalidBinding();
  return value;
}
// Same contract cloud_cycle.py enforces on LM_CAPAFY_BINDING_JSON: references
// are metadata strings, never secret objects, and a binding naming another
// tenant or platform is rejected before anything executes.
function parseTenantBinding(value, { tenantId, platformId } = {}) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalidBinding();
  if (typeof tenantId !== 'string' || !UID.test(tenantId)) invalidBinding();
  platformFor(platformId);
  if (Object.keys(value).some(key => !BINDING_KEYS.has(key))) invalidBinding();
  if (value.tenantId !== tenantId || value.provider !== platformId) invalidBinding();
  if (typeof value.subjectId !== 'string' || !value.subjectId || value.subjectId.length > 128
    || /[\u0000-\u001f\u007f]/.test(value.subjectId)) invalidBinding();
  const parsed = { tenantId, provider: platformId, subjectId: value.subjectId };
  if (value.credentialRef !== undefined) parsed.credentialRef = parseRef(value.credentialRef, platformId);
  if (value.browserSessionRef !== undefined) parsed.browserSessionRef = parseRef(value.browserSessionRef, platformId);
  return Object.freeze(parsed);
}
function tenantPlatformStatePath(stateHome, platformId) {
  return path.join(stateHome, platformFor(platformId).stateDir, 'signup-state.json');
}
const TENANT_UID = 10001;
function hostIsRoot() { return process.platform === 'linux' && process.getuid?.() === 0; }
function handDirectoryToTenant(fsImpl, directory) {
  // Mirror runtime-env.js fixed-directory handling: open through a no-follow
  // directory fd so ownership changes never chase a symlink.
  const constants = fsImpl.constants || fs.constants;
  const flags = constants.O_RDONLY | constants.O_DIRECTORY | constants.O_NOFOLLOW;
  const fd = fsImpl.openSync(directory, flags);
  try { fsImpl.fchownSync(fd, TENANT_UID, TENANT_UID); fsImpl.fchmodSync(fd, 0o700); } finally { fsImpl.closeSync(fd); }
}
function atomicJson(target, value, fsImpl) {
  const directory = path.dirname(target);
  // Directories this write creates belong to the tenant uid when the root
  // host writes them, not just the file: a root-owned 0700 directory leaves
  // the dropped-privilege cycle unable to even stat the files inside it
  // (the first bound cycle crashed exactly there, on the session manifest).
  const created = [];
  if (hostIsRoot()) {
    let cursor = directory;
    while (!fsImpl.existsSync(cursor)) { created.push(cursor); cursor = path.dirname(cursor); }
    if (!created.includes(directory)) created.push(directory);
  }
  fsImpl.mkdirSync(directory, { recursive: true, mode: 0o700 });
  const temporary = path.join(directory, `.signup-state-${randomUUID()}.json`);
  try {
    const fd = fsImpl.openSync(temporary, 'wx', 0o600);
    try {
      // Mirror runtime-env.js: files the root host writes into a tenant home
      // belong to the dropped-privilege tenant uid.
      if (hostIsRoot()) fsImpl.fchownSync(fd, TENANT_UID, TENANT_UID);
      fsImpl.writeFileSync(fd, JSON.stringify(value, null, 2) + '\n');
    } finally { fsImpl.closeSync(fd); }
    fsImpl.renameSync(temporary, target);
  } finally { if (fsImpl.existsSync(temporary)) fsImpl.unlinkSync(temporary); }
  for (const dir of created) handDirectoryToTenant(fsImpl, dir);
}
function loadTenantPlatformState({ stateHome, tenantId, platformId, fsImpl = fs } = {}) {
  if (typeof stateHome !== 'string' || !stateHome || typeof tenantId !== 'string' || !UID.test(tenantId)) invalidState();
  platformFor(platformId);
  const file = tenantPlatformStatePath(stateHome, platformId);
  if (!fsImpl.existsSync(file)) {
    return Object.freeze({ schemaVersion: 1, tenantId, platformId, state: 'none', binding: null, history: Object.freeze([]) });
  }
  let record;
  try { record = JSON.parse(fsImpl.readFileSync(file, 'utf8')); } catch { invalidState(); }
  if (!record || typeof record !== 'object' || Array.isArray(record) || record.schemaVersion !== 1
    || record.tenantId !== tenantId || record.platformId !== platformId || !STATES.has(record.state)
    || !Array.isArray(record.history)) invalidState();
  let binding = null;
  if (record.binding !== null && record.binding !== undefined) {
    try { binding = parseTenantBinding(record.binding, { tenantId, platformId }); } catch { invalidState(); }
  }
  if (record.state !== 'none' && record.state !== 'signed_up' && !binding) invalidState();
  return Object.freeze({ schemaVersion: 1, tenantId, platformId, state: record.state, binding,
    history: Object.freeze(record.history.map(entry => Object.freeze({ ...entry }))) });
}
function saveTenantPlatformState({ stateHome, record, fsImpl = fs }) {
  atomicJson(tenantPlatformStatePath(stateHome, record.platformId), {
    schemaVersion: 1, tenantId: record.tenantId, platformId: record.platformId,
    state: record.state, binding: record.binding ? { ...record.binding } : null,
    history: record.history.map(entry => ({ ...entry })),
  }, fsImpl);
}
function recordTenantStateTransition({ stateHome, tenantId, platformId, next, binding, at, fsImpl = fs } = {}) {
  const current = loadTenantPlatformState({ stateHome, tenantId, platformId, fsImpl });
  advanceTenantPlatformState(current.state, next); // throws tenant_signup_state_invalid out of order
  const parsedBinding = binding === undefined ? current.binding
    : binding === null ? null : parseTenantBinding(binding, { tenantId, platformId });
  if (next !== 'none' && next !== 'signed_up' && !parsedBinding) invalidState();
  const record = { schemaVersion: 1, tenantId, platformId, state: next, binding: parsedBinding,
    history: [...current.history, { from: current.state, to: next, at: typeof at === 'string' ? at : new Date().toISOString() }] };
  saveTenantPlatformState({ stateHome, record, fsImpl });
  return loadTenantPlatformState({ stateHome, tenantId, platformId, fsImpl });
}
// Resolve one vault reference to a path provably inside the tenant home.
// Symlinks and escapes are rejected; the target's contents are never read.
function resolveVaultRef(stateHome, ref, platformId, fsImpl) {
  const match = REF.exec(ref);
  const home = fsImpl.realpathSync(stateHome);
  const target = path.join(home, 'vault', match[1], match[2]);
  let info;
  try { info = fsImpl.lstatSync(target); } catch { unresolvable(); }
  if (info.isSymbolicLink()) unresolvable();
  let real;
  try { real = fsImpl.realpathSync(target); } catch { unresolvable(); }
  if (real !== target || !real.startsWith(home + path.sep)) unresolvable();
  return { target, info };
}
function resolveTenantBinding({ binding, tenantId, platformId, stateHome, publisherStateHome, now, fsImpl = fs } = {}) {
  const parsed = parseTenantBinding(binding, { tenantId, platformId });
  if (typeof stateHome !== 'string' || !stateHome || typeof publisherStateHome !== 'string' || !publisherStateHome
    || !parsed.credentialRef || !parsed.browserSessionRef) unresolvable();
  const credential = resolveVaultRef(stateHome, parsed.credentialRef, platformId, fsImpl);
  if (!credential.info.isFile() || (credential.info.mode & 0o077) !== 0) unresolvable();
  const session = resolveVaultRef(stateHome, parsed.browserSessionRef, platformId, fsImpl);
  if (!session.info.isDirectory()) unresolvable();
  const manifestPath = path.join(publisherStateHome, 'sessions', platformId, 'session.json');
  atomicJson(manifestPath, {
    schemaVersion: 1, tenantId, provider: platformId, subjectId: parsed.subjectId,
    credentialRef: parsed.credentialRef, browserSessionRef: parsed.browserSessionRef,
    credentialPath: credential.target, browserSessionPath: session.target,
    resolvedAt: typeof now === 'string' ? now : new Date().toISOString(),
  }, fsImpl);
  return Object.freeze({ status: 'resolved', manifestPath, credentialPath: credential.target, browserSessionPath: session.target });
}
// The run-cycle wiring: decide, before the tenant cycle starts, whether this
// cycle is the self-signup cycle (no binding yet -> directive for the in-tenant
// agent) or a bound cycle (binding resolves -> references-only env injected).
// Fail closed: a present-but-invalid or unresolvable binding stops the cycle
// instead of silently degrading to no-account mode.
function prepareTenantCycle({ tenantId, env = {}, stateHome, publisherStateHome, platformId = 'capafy', fsImpl = fs } = {}) {
  const platform = platformFor(platformId);
  if (!platform.enabled || !BINDING_ENV_BY_PLATFORM[platformId]) invalidBinding();
  if (typeof stateHome !== 'string' || !stateHome) invalidState();
  let record = loadTenantPlatformState({ stateHome, tenantId, platformId, fsImpl });
  let candidate = record.binding;
  const envBinding = env[BINDING_ENV_BY_PLATFORM[platformId]];
  if (typeof envBinding === 'string' && envBinding) {
    let parsedEnv;
    try { parsedEnv = JSON.parse(envBinding); } catch { invalidBinding(); }
    candidate = parseTenantBinding(parsedEnv, { tenantId, platformId });
  }
  if (candidate) {
    const resolution = resolveTenantBinding({ binding: candidate, tenantId, platformId, stateHome, publisherStateHome, fsImpl });
    if (record.state === 'none') {
      record = recordTenantStateTransition({ stateHome, tenantId, platformId, next: 'signed_up', fsImpl });
    }
    if (record.state === 'signed_up') {
      record = recordTenantStateTransition({ stateHome, tenantId, platformId, next: 'bound', binding: candidate, fsImpl });
    } else if (!record.binding) {
      record = { ...record, binding: candidate };
      saveTenantPlatformState({ stateHome, record, fsImpl });
      record = loadTenantPlatformState({ stateHome, tenantId, platformId, fsImpl });
    }
    return Object.freeze({ mode: 'bound', platformId, state: record.state, resolution,
      env: Object.freeze({ [BINDING_ENV_BY_PLATFORM[platformId]]: JSON.stringify(candidate) }) });
  }
  const directive = {
    tenantId, platformId,
    identityRef: 'tenant-home/vault/agent-mail',
    identityPath: path.join(stateHome, 'vault', 'agent-mail'),
    credentialRef: tenantCredentialRef(platformId),
    credentialPath: path.join(stateHome, 'vault', platformId, 'credential'),
    browserSessionRef: tenantBrowserSessionRef(platformId),
    browserSessionPath: path.join(stateHome, 'vault', platformId, 'browser-session'),
    stateFile: tenantPlatformStatePath(stateHome, platformId),
  };
  return Object.freeze({ mode: 'self_signup', platformId, state: record.state,
    env: Object.freeze({ [SIGNUP_DIRECTIVE_ENV]: JSON.stringify(directive) }) });
}
module.exports = { parseTenantBinding, tenantCredentialRef, tenantBrowserSessionRef,
  loadTenantPlatformState, recordTenantStateTransition, resolveTenantBinding, prepareTenantCycle,
  tenantPlatformStatePath, BINDING_ENV_BY_PLATFORM, SIGNUP_DIRECTIVE_ENV };
