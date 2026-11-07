'use strict';
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const { prepareMaritimeRuntime } = require('./runtime-env.js');
const { prepareTenantCycle } = require('../lib/maritime-tenant-binding.js');
function runMaritimeCycle(args, { env = process.env, prepareRuntime = prepareMaritimeRuntime, spawnImpl = spawnSync,
  prepareTenant = prepareTenantCycle, platform = process.platform, uid = process.getuid?.() } = {}) {
  if (!Array.isArray(args) || args.length !== 6 || args[0] !== '--tenant' || args[2] !== '--occurrence' || args[4] !== '--date'
    || typeof args[1] !== 'string' || !/^lm_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(args[1])
    || args[1] !== env.LM_RUNTIME_TENANT_ID || typeof args[3] !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(args[3])
    || typeof args[5] !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(args[5])
    || !Number.isFinite(Date.parse(args[5])) || new Date(args[5]).toISOString().slice(0, 10) !== args[5]) {
    throw new Error('maritime_cycle_arguments_invalid');
  }
  const runtime = prepareRuntime({ env });
  const childEnv = { ...runtime.env };
  delete childEnv.LM_WAKE_RELAY_TOKEN;
  delete childEnv.LM_WAKE_RELAY_URL;
  // Tenant self-signup / binding wiring: when the runtime prepared a tenant
  // home, decide this cycle's mode before spawn. No binding yet -> the cycle
  // receives the self-signup directive; a binding that resolves -> only its
  // references-only JSON crosses into the cycle. An invalid or unresolvable
  // binding throws here and the cycle never starts (fail closed).
  const stateHome = runtime.env.LIFE_MANAGER_STATE_HOME;
  if (typeof stateHome === 'string' && stateHome) {
    const tenant = prepareTenant({ tenantId: args[1], env: childEnv, stateHome,
      publisherStateHome: path.join(stateHome, 'runtime', 'capafy-publisher') });
    Object.assign(childEnv, tenant.env);
  }
  const command = ['python3', '/app/skills/capafy-autopublish/scripts/cloud_cycle.py', ...args];
  const restricted = platform === 'linux' && uid === 0;
  const result = spawnImpl(restricted ? '/usr/bin/setpriv' : command[0], restricted
    ? ['--reuid=10001', '--regid=10001', '--clear-groups', '--bounding-set=-all', '--inh-caps=-all', '--ambient-caps=-all', '--no-new-privs', ...command]
    : command.slice(1), { cwd: '/app', env: childEnv, stdio: 'inherit' });
  return Number.isInteger(result?.status) && result.status >= 0 ? result.status : 2;
}
if (require.main === module) {
  try { process.exitCode = runMaritimeCycle(process.argv.slice(2)); }
  catch { process.stderr.write('maritime_cycle_startup_failed\n'); process.exitCode = 2; }
}
module.exports = { runMaritimeCycle };
