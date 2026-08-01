import assert from 'node:assert/strict';
import test from 'node:test';

import { validateRegistry } from '../scripts/validate-agent-registry.mjs';
import {
  generatedDocsMatch,
  renderCatalog,
  renderReadmeSection,
  updateMarkedSection,
} from '../scripts/render-agent-catalog.mjs';

const rootAgent = {
  agent_id: 'life-manager',
  display_name: 'Life Manager Orchestrator',
  organ: 'executive',
  parent_agent_id: null,
  objective: 'Coordinate specialist agents around the user goal.',
  objective_ja: 'ユーザーの目標に合わせて専門エージェントを統括する。',
  lifecycle: 'live',
  deployments: ['local', 'cloud'],
  decision_owner: 'model',
  skills: [],
  tools: ['canonical-job-protocol'],
  loop_adapters: [],
  runtime_families: ['life-manager-runtime'],
  effect_classes: ['read', 'draft'],
  source_refs: ['runtime/loop/index.mjs'],
  evidence_refs: ['docs/earning-agents-reference.md'],
};

const childAgent = {
  ...rootAgent,
  agent_id: 'finance.gig',
  display_name: 'Gig Work Agent',
  organ: 'finance',
  parent_agent_id: 'life-manager',
  objective: 'Find, deliver, and verify feasible remote gig work.',
  objective_ja: '実行可能なリモートギグを探し、納品し、結果を検証する。',
  lifecycle: 'legacy_live',
  deployments: ['local'],
  tools: ['browser'],
  runtime_families: ['gig-loop'],
  source_refs: ['skills/earn/gig/gig-cli.sh'],
  evidence_refs: ['docs/superpowers/specs/2026-06-30-gig-self-improving-multiapply-loop-design.md'],
};

function registry(agents = [rootAgent, childAgent]) {
  return {
    schema_version: 1,
    generated_docs: {
      readme: 'README.md',
      readme_ja: 'README.ja.md',
      catalog: 'docs/agent-catalog.md',
    },
    agents,
  };
}

function errorCodes(value, references = {}) {
  return validateRegistry(value, {
    repoRoot: new URL('..', import.meta.url),
    ...references,
  }).map((error) => error.code);
}

test('accepts a minimal hierarchy backed by repository evidence', () => {
  assert.deepEqual(errorCodes(registry()), []);
});

test('rejects duplicate agent IDs before a renderer can collapse two agents', () => {
  assert.ok(errorCodes(registry([rootAgent, childAgent, childAgent])).includes('duplicate_agent_id'));
});

test('rejects a parent ID that is not present in the same registry', () => {
  const orphan = { ...childAgent, parent_agent_id: 'finance.missing' };
  assert.ok(errorCodes(registry([rootAgent, orphan])).includes('unknown_parent'));
});

test('rejects a cyclic hierarchy that cannot be rendered as an organization', () => {
  const first = { ...rootAgent, parent_agent_id: 'finance.gig' };
  assert.ok(errorCodes(registry([first, childAgent])).includes('parent_cycle'));
});

test('requires implementation and evidence references for an active lifecycle', () => {
  const unsupported = { ...childAgent, source_refs: [], evidence_refs: [] };
  const codes = errorCodes(registry([rootAgent, unsupported]));
  assert.ok(codes.includes('missing_source_evidence'));
  assert.ok(codes.includes('missing_verification_evidence'));
});

test('requires a specification reference for a planned agent', () => {
  const unsupported = {
    ...childAgent,
    lifecycle: 'planned',
    source_refs: [],
    evidence_refs: [],
    runtime_families: [],
  };
  assert.ok(errorCodes(registry([rootAgent, unsupported])).includes('missing_plan_evidence'));
});

test('rejects absolute paths so a public registry remains portable', () => {
  const localOnly = { ...childAgent, source_refs: ['/Users/example/private/agent.sh'] };
  assert.ok(errorCodes(registry([rootAgent, localOnly])).includes('absolute_path'));
});

test('rejects secret-shaped fields even when a credential value looks harmless', () => {
  const leakedShape = { ...childAgent, api_key: 'placeholder' };
  assert.ok(errorCodes(registry([rootAgent, leakedShape])).includes('secret_field'));
});

test('rejects a skill ID that is absent from the canonical skill registry', () => {
  const unknown = { ...childAgent, skills: ['earn/not-real'] };
  const codes = errorCodes(registry([rootAgent, unknown]), { knownSkillIds: new Set(['report']) });
  assert.ok(codes.includes('unknown_skill'));
});

test('rejects an adapter ID that is absent from the canonical adapter registry', () => {
  const unknown = { ...childAgent, loop_adapters: ['missing-adapter'] };
  const codes = errorCodes(registry([rootAgent, unknown]), { knownAdapterIds: new Set(['financial-report-telegram']) });
  assert.ok(codes.includes('unknown_adapter'));
});

test('rejects a runtime family absent from the checked-in 399-job inventory', () => {
  const unknown = { ...childAgent, runtime_families: ['invented-loop'] };
  const codes = errorCodes(registry([rootAgent, unknown]), {
    knownRuntimeFamilies: new Set(['life-manager-runtime', 'gig-loop']),
  });
  assert.ok(codes.includes('unknown_runtime_family'));
});

test('rejects a repository evidence path that does not exist', () => {
  const missing = { ...childAgent, evidence_refs: ['docs/evidence/does-not-exist.md'] };
  assert.ok(errorCodes(registry([rootAgent, missing])).includes('missing_repo_path'));
});

test('rejects an effect class outside the public approval vocabulary', () => {
  const unsafe = { ...childAgent, effect_classes: ['teleport'] };
  assert.ok(errorCodes(registry([rootAgent, unsafe])).includes('invalid_effect_class'));
});

test('rejects a malformed registry instead of treating an empty agent list as valid', () => {
  const malformed = { schema_version: 2, generated_docs: {}, agents: [] };
  assert.ok(errorCodes(malformed).includes('schema_violation'));
});

test('rejects missing required agent fields and unsupported lifecycle values', () => {
  const { objective: _objective, ...missing } = childAgent;
  const unsupported = { ...childAgent, lifecycle: 'maybe_live' };
  const codes = errorCodes(registry([rootAgent, missing, unsupported]));
  assert.ok(codes.includes('schema_violation'));
});

test('rejects unknown agent fields so unvalidated policy cannot hide in the registry', () => {
  const unknown = { ...childAgent, auto_approve_everything: true };
  assert.ok(errorCodes(registry([rootAgent, unknown])).includes('unknown_agent_field'));
});

test('requires exactly one root orchestrator', () => {
  const secondRoot = { ...childAgent, agent_id: 'second-root', parent_agent_id: null };
  assert.ok(errorCodes(registry([rootAgent, secondRoot])).includes('invalid_root_count'));
});

test('rejects repository paths that escape through parent traversal', () => {
  const escaping = { ...childAgent, evidence_refs: ['../outside.md'] };
  assert.ok(errorCodes(registry([rootAgent, escaping])).includes('path_escape'));
});

test('rejects generated-document destinations outside the repository', () => {
  const escaping = registry();
  escaping.generated_docs.catalog = '../../agent-catalog.md';
  assert.ok(errorCodes(escaping).includes('path_escape'));
});

test('renders organs in stable product order regardless of registry input order', () => {
  const health = {
    ...childAgent,
    agent_id: 'health.physical',
    display_name: 'Physical Health Agent',
    organ: 'health',
    objective_ja: '睡眠、運動、食事、通院を支援する。',
    lifecycle: 'planned',
    source_refs: [],
    evidence_refs: ['docs/superpowers/specs/2026-08-01-life-manager-agent-registry-design.md'],
    runtime_families: [],
  };
  const output = renderReadmeSection(registry([childAgent, health, rootAgent]));
  assert.ok(output.indexOf('Executive') < output.indexOf('Health'));
  assert.ok(output.indexOf('Health') < output.indexOf('Finance'));
});

test('renders the same registry as a Japanese README organization view', () => {
  const output = renderReadmeSection(registry(), { locale: 'ja' });
  assert.match(output, /## エージェント組織/);
  assert.match(output, /🟠 旧runtimeで稼働/);
  assert.match(output, /スキル、scheduler、workerはエージェント数に含めません/);
  assert.match(output, /実行可能なリモートギグを探し、納品し、結果を検証する。/);
});

test('renders every agent exactly once in the detailed catalog', () => {
  const output = renderCatalog(registry());
  assert.equal(output.match(/`life-manager`/g)?.length, 1);
  assert.equal(output.match(/`finance\.gig`/g)?.length, 1);
  assert.match(output, /Legacy live/);
});

test('updates only the bounded README marker body', () => {
  const original = [
    '# Before',
    '<!-- AGENT-REGISTRY:START -->',
    'old generated body',
    '<!-- AGENT-REGISTRY:END -->',
    'After stays byte-identical',
    '',
  ].join('\n');
  const updated = updateMarkedSection(original, 'new generated body');
  assert.equal(updated, [
    '# Before',
    '<!-- AGENT-REGISTRY:START -->',
    'new generated body',
    '<!-- AGENT-REGISTRY:END -->',
    'After stays byte-identical',
    '',
  ].join('\n'));
});

test('detects generated documentation drift without writing files', () => {
  const value = registry();
  const readme = [
    '<!-- AGENT-REGISTRY:START -->',
    renderReadmeSection(value),
    '<!-- AGENT-REGISTRY:END -->',
    '',
  ].join('\n');
  const readmeJa = [
    '<!-- AGENT-REGISTRY:START -->',
    renderReadmeSection(value, { locale: 'ja' }),
    '<!-- AGENT-REGISTRY:END -->',
    '',
  ].join('\n');
  assert.equal(generatedDocsMatch(value, { readme, readmeJa, catalog: renderCatalog(value) }), true);
  assert.equal(generatedDocsMatch(value, {
    readme: readme.replace('Gig Work Agent', 'Drifted'),
    readmeJa,
    catalog: renderCatalog(value),
  }), false);
});
