/**
 * config-drift-detector.test.mjs — Phase 3 adversary FIND-001 fix: the COMPOSED, runnable detector
 * (`runConfigDriftDetector`), not just its parts.
 *
 * Every I/O boundary (`listProcesses`/`readPlistEnv`/`readRegistry`) is injected with fixture-backed
 * fakes below — this file NEVER spawns a real `ps`/`plutil`/`launchctl` process and never touches the
 * real filesystem. The fixtures below are literal copies of the REAL bug-1 (ANICCA_BRAIN drift) and
 * bug-2 (hl_trade registry drift) data recorded in specs/behavioral-spec.md's Context section.
 */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { runConfigDriftDetector } from '../config-drift.mjs';

const AGENT_ECONOMY_PS_LINE =
  '94249 node /Users/anicca/anicca/runtime/loop/index.mjs ANICCA_HOME=/Users/anicca/.anicca-founder XPC_SERVICE_NAME=ai.anicca.agent-economy-loop ANICCA_BRAIN=proxy';
const FRANKLIN_PS_LINE =
  '79192 node /Users/anicca/anicca/runtime/loop/index.mjs ANICCA_HOME=/Users/anicca/.blockrun XPC_SERVICE_NAME=ai.anicca.franklin-loop ANICCA_BRAIN=proxy';
const FRANKLIN2_PS_LINE =
  '86698 node /Users/anicca/anicca/runtime/loop/index.mjs ANICCA_HOME=/Users/anicca/.franklin2-home/.blockrun XPC_SERVICE_NAME=ai.anicca.franklin2-loop ANICCA_BRAIN=proxy';

const CANONICAL_REGISTRY_DORMANT = { slots: { hl_trade: { status: 'dormant' } } };
const RUNTIME_REGISTRY_LIVE = { slots: { hl_trade: { status: 'live' } } };
const RUNTIME_REGISTRY_DORMANT = { slots: { hl_trade: { status: 'dormant' } } };

function fakeDeps({ psLines, plistEnvsByPath = {}, registriesByPath = {}, canonicalRegistryPath = '/repo/skills/registry.json' }) {
  return {
    listProcesses: async () => psLines,
    readPlistEnv: async (plistPath) => (plistPath in plistEnvsByPath ? plistEnvsByPath[plistPath] : null),
    readRegistry: async (filePath) => (filePath in registriesByPath ? registriesByPath[filePath] : null),
    canonicalRegistryPath,
  };
}

const PLIST_DIR = `${process.env.HOME}/Library/LaunchAgents`;

test('FIND-001: the real bug-1 fixture (agent-economy-loop plist declares claude-p, runtime shows proxy) is detected end-to-end through the composed detector', async () => {
  const deps = fakeDeps({
    psLines: [AGENT_ECONOMY_PS_LINE],
    plistEnvsByPath: {
      [`${PLIST_DIR}/ai.anicca.agent-economy-loop.plist`]: { ANICCA_BRAIN: 'claude-p' },
    },
    registriesByPath: {
      '/repo/skills/registry.json': CANONICAL_REGISTRY_DORMANT,
      '/Users/anicca/.anicca-founder/skills/registry.json': RUNTIME_REGISTRY_DORMANT, // matches -> no registry drift for this run
    },
  });
  const report = await runConfigDriftDetector(deps);
  assert.equal(report.overallStatus, 'FAIL');
  assert.equal(report.brainDrift.length, 1);
  assert.deepEqual(report.brainDrift[0], {
    key: 'ANICCA_BRAIN',
    instance: 'ai.anicca.agent-economy-loop',
    declared: 'claude-p',
    actual: 'proxy',
  });
  assert.deepEqual(report.registryDrift, []);
});

test('FIND-001: the real bug-2 fixture (canonical hl_trade=dormant, runtime copy=live) is detected end-to-end through the composed detector', async () => {
  const deps = fakeDeps({
    psLines: [AGENT_ECONOMY_PS_LINE],
    plistEnvsByPath: {
      [`${PLIST_DIR}/ai.anicca.agent-economy-loop.plist`]: { ANICCA_BRAIN: 'proxy' }, // no brain drift this time
    },
    registriesByPath: {
      '/repo/skills/registry.json': CANONICAL_REGISTRY_DORMANT,
      '/Users/anicca/.anicca-founder/skills/registry.json': RUNTIME_REGISTRY_LIVE,
    },
  });
  const report = await runConfigDriftDetector(deps);
  assert.equal(report.overallStatus, 'FAIL');
  assert.deepEqual(report.brainDrift, []);
  assert.equal(report.registryDrift.length, 1);
  assert.deepEqual(report.registryDrift[0], {
    key: 'hl_trade.status',
    copyPath: '/Users/anicca/.anicca-founder/skills/registry.json',
    declared: 'dormant',
    actual: 'live',
  });
});

test('FIND-001: BOTH real bugs fire simultaneously across 3 discovered targets (agent-economy-loop drifting, both Franklins clean) — REQ-003 per-instance expectations, no global hardcoding', async () => {
  const deps = fakeDeps({
    psLines: [AGENT_ECONOMY_PS_LINE, FRANKLIN_PS_LINE, FRANKLIN2_PS_LINE],
    plistEnvsByPath: {
      [`${PLIST_DIR}/ai.anicca.agent-economy-loop.plist`]: { ANICCA_BRAIN: 'claude-p' },
      [`${PLIST_DIR}/ai.anicca.franklin-loop.plist`]: { ANICCA_BRAIN: 'proxy' },
      [`${PLIST_DIR}/ai.anicca.franklin2-loop.plist`]: { ANICCA_BRAIN: 'proxy' },
    },
    registriesByPath: {
      '/repo/skills/registry.json': CANONICAL_REGISTRY_DORMANT,
      '/Users/anicca/.anicca-founder/skills/registry.json': RUNTIME_REGISTRY_DORMANT,
      '/Users/anicca/.blockrun/skills/registry.json': RUNTIME_REGISTRY_LIVE,
      '/Users/anicca/.franklin2-home/.blockrun/skills/registry.json': RUNTIME_REGISTRY_LIVE,
    },
  });
  const report = await runConfigDriftDetector(deps);
  assert.equal(report.targets.length, 3);
  assert.equal(report.overallStatus, 'FAIL');
  assert.equal(report.brainDrift.length, 1, 'only agent-economy-loop should show a brain drift, NOT the Franklins (REQ-003: same function, per-instance declared values)');
  assert.equal(report.brainDrift[0].instance, 'ai.anicca.agent-economy-loop');
  assert.equal(report.registryDrift.length, 2, 'both Franklin runtime copies drifted from the canonical dormant status');
  const driftedCopies = report.registryDrift.map((d) => d.copyPath).sort();
  assert.deepEqual(driftedCopies, [
    '/Users/anicca/.blockrun/skills/registry.json',
    '/Users/anicca/.franklin2-home/.blockrun/skills/registry.json',
  ]);
});

test('everything clean -> overallStatus PASS, zero drift entries', async () => {
  const deps = fakeDeps({
    psLines: [FRANKLIN_PS_LINE],
    plistEnvsByPath: { [`${PLIST_DIR}/ai.anicca.franklin-loop.plist`]: { ANICCA_BRAIN: 'proxy' } },
    registriesByPath: {
      '/repo/skills/registry.json': CANONICAL_REGISTRY_DORMANT,
      '/Users/anicca/.blockrun/skills/registry.json': RUNTIME_REGISTRY_DORMANT,
    },
  });
  const report = await runConfigDriftDetector(deps);
  assert.equal(report.overallStatus, 'PASS');
  assert.deepEqual(report.brainDrift, []);
  assert.deepEqual(report.registryDrift, []);
});

test('real-fleet fix (com.anicca.daemon, found running the real detector 2026-07-12): a 4th discovered instance whose plist and runtime env BOTH simply never mention ANICCA_BRAIN at all -> PASS, not a spurious drift', async () => {
  const CLAWROUTER_PS_LINE =
    '61618 node /Users/anicca/anicca/runtime/loop/index.mjs ANICCA_HOME=/Users/anicca/.anicca XPC_SERVICE_NAME=com.anicca.daemon ANICCA_INSTANCE=clawrouter';
  const deps = fakeDeps({
    psLines: [CLAWROUTER_PS_LINE],
    plistEnvsByPath: {
      [`${PLIST_DIR}/com.anicca.daemon.plist`]: { ANICCA_HOME: '/Users/anicca/.anicca', ANICCA_INSTANCE: 'clawrouter' }, // no ANICCA_BRAIN key, matches the real deployed plist
    },
    registriesByPath: {
      '/repo/skills/registry.json': CANONICAL_REGISTRY_DORMANT,
      '/Users/anicca/.anicca/skills/registry.json': RUNTIME_REGISTRY_DORMANT,
    },
  });
  const report = await runConfigDriftDetector(deps);
  assert.equal(report.overallStatus, 'PASS', `expected PASS, got brainDrift=${JSON.stringify(report.brainDrift)}`);
  assert.deepEqual(report.brainDrift, []);
});

test('REQ-010 edge case: zero discovered targets -> overallStatus is the explicit "NO_TARGETS", never silently "PASS"', async () => {
  const deps = fakeDeps({ psLines: [], registriesByPath: { '/repo/skills/registry.json': CANONICAL_REGISTRY_DORMANT } });
  const report = await runConfigDriftDetector(deps);
  assert.equal(report.targets.length, 0);
  assert.equal(report.overallStatus, 'NO_TARGETS');
});

test('FIND-003 wired end-to-end: an unreadable plist (readPlistEnv resolves null) reports FAIL/unobservable through the composed detector, not a silent PASS', async () => {
  const deps = fakeDeps({
    psLines: [AGENT_ECONOMY_PS_LINE],
    plistEnvsByPath: {}, // deliberately empty: readPlistEnv will resolve null for the one plist path requested
    registriesByPath: {
      '/repo/skills/registry.json': CANONICAL_REGISTRY_DORMANT,
      '/Users/anicca/.anicca-founder/skills/registry.json': RUNTIME_REGISTRY_DORMANT,
    },
  });
  const report = await runConfigDriftDetector(deps);
  assert.equal(report.overallStatus, 'FAIL');
  assert.equal(report.brainDrift.length, 1);
  assert.equal(report.brainDrift[0].reason, 'unobservable');
});

test('REQ-004: an unreadable canonical registry.json fails EVERY runtime copy closed, never an empty (PASS) registryDrift', async () => {
  const deps = fakeDeps({
    psLines: [AGENT_ECONOMY_PS_LINE],
    plistEnvsByPath: { [`${PLIST_DIR}/ai.anicca.agent-economy-loop.plist`]: { ANICCA_BRAIN: 'proxy' } },
    registriesByPath: {
      '/Users/anicca/.anicca-founder/skills/registry.json': RUNTIME_REGISTRY_DORMANT,
      // canonical path deliberately absent from registriesByPath -> readRegistry resolves null for it
    },
  });
  const report = await runConfigDriftDetector(deps);
  assert.equal(report.overallStatus, 'FAIL');
  assert.equal(report.registryDrift.length, 1);
  assert.equal(report.registryDrift[0].reason, 'unobservable');
});

test('injected deps mean this file never touches a real ps/plutil/launchctl process or the real filesystem', async () => {
  let listProcessesCalls = 0;
  const deps = {
    listProcesses: async () => { listProcessesCalls += 1; return [AGENT_ECONOMY_PS_LINE]; },
    readPlistEnv: async () => ({ ANICCA_BRAIN: 'proxy' }),
    readRegistry: async () => ({ slots: {} }),
    canonicalRegistryPath: '/fake/registry.json',
  };
  await runConfigDriftDetector(deps);
  assert.equal(listProcessesCalls, 1, 'the injected fake, not a real ps invocation, must be the one and only process source');
});
