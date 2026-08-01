#!/usr/bin/env node

import { readFileSync, renameSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { validateRegistry } from './validate-agent-registry.mjs';

export const START_MARKER = '<!-- AGENT-REGISTRY:START -->';
export const END_MARKER = '<!-- AGENT-REGISTRY:END -->';

const ORGAN_ORDER = ['executive', 'health', 'finance', 'growth', 'technology', 'opportunity'];
const ORGAN_LABEL = {
  executive: 'Executive',
  health: 'Health',
  finance: 'Finance / CFO',
  growth: 'Growth',
  technology: 'Technology / CTO',
  opportunity: 'Opportunity',
};
const ORGAN_LABEL_JA = {
  executive: '統括',
  health: '健康',
  finance: '財務 / CFO',
  growth: '成長',
  technology: '技術 / CTO',
  opportunity: '機会獲得',
};
const LIFECYCLE = {
  live: ['🟢', 'Live'],
  shadow: ['🟡', 'Shadow'],
  legacy_live: ['🟠', 'Legacy live'],
  dormant: ['⚫', 'Dormant'],
  planned: ['⚪', 'Planned'],
  deprecated: ['❌', 'Deprecated'],
};
const LIFECYCLE_JA = {
  live: ['🟢', '正規runtimeで稼働'],
  shadow: ['🟡', 'shadow検証中'],
  legacy_live: ['🟠', '旧runtimeで稼働'],
  dormant: ['⚫', '停止中'],
  planned: ['⚪', '計画中'],
  deprecated: ['❌', '廃止'],
};

function markdown(value) {
  return String(value).replaceAll('|', '\\|').replaceAll('\n', ' ');
}

function groupedAgents(registry) {
  const order = new Map(ORGAN_ORDER.map((organ, index) => [organ, index]));
  return [...registry.agents].sort((left, right) => {
    const organ = (order.get(left.organ) ?? 999) - (order.get(right.organ) ?? 999);
    if (organ !== 0) return organ;
    if (left.parent_agent_id === null && right.parent_agent_id !== null) return -1;
    if (right.parent_agent_id === null && left.parent_agent_id !== null) return 1;
    return left.agent_id.localeCompare(right.agent_id);
  });
}

export function renderReadmeSection(registry, { locale = 'en' } = {}) {
  const japanese = locale === 'ja';
  const lines = [
    japanese ? '## エージェント組織' : '## Agent organization',
    '',
    japanese
      ? 'Life Managerは専門エージェントを統括します。この表は[`agents/registry.json`](agents/registry.json)から生成され、スキル、scheduler、workerはエージェント数に含めません。'
      : 'Life Manager is the orchestrator of specialist agents. This table is generated from [`agents/registry.json`](agents/registry.json); skills, schedulers, and workers are intentionally not counted as agents.',
    '',
  ];
  const agents = groupedAgents(registry);
  for (const organ of ORGAN_ORDER) {
    const members = agents.filter((agent) => agent.organ === organ);
    if (members.length === 0) continue;
    lines.push(
      `### ${japanese ? ORGAN_LABEL_JA[organ] : ORGAN_LABEL[organ]}`,
      '',
      japanese ? '| 状態 | エージェント | 目的 | 実行面 |' : '| Status | Agent | Objective | Surface |',
      '|---|---|---|---|',
    );
    for (const agent of members) {
      const [icon, label] = (japanese ? LIFECYCLE_JA : LIFECYCLE)[agent.lifecycle];
      const objective = japanese ? agent.objective_ja : agent.objective;
      lines.push(`| ${icon} ${label} | **${markdown(agent.display_name)}** | ${markdown(objective)} | ${agent.deployments.join(' + ')} |`);
    }
    lines.push('');
  }
  lines.push(japanese
    ? '能力、effect、runtime family、証拠は生成された[詳細エージェント名簿](docs/agent-catalog.md)を参照してください。現在の健康状態はreceiptから算出し、Registryの状態だけで直近実行の成功を主張しません。'
    : 'See the generated [full agent catalog](docs/agent-catalog.md) for capabilities, effects, runtime-family mappings, and evidence. Runtime health is receipt-derived; a registry lifecycle is not a claim that the last run succeeded.');
  return lines.join('\n');
}

function displayList(values) {
  return values.length > 0 ? values.map((value) => `\`${value}\``).join(', ') : '—';
}

function evidenceLinks(refs) {
  return refs.map((ref) => `[${ref}](../${ref})`).join('<br>');
}

export function renderCatalog(registry) {
  const agents = groupedAgents(registry);
  const byId = new Map(agents.map((agent) => [agent.agent_id, agent]));
  const lines = [
    '# Life Manager Agent Catalog',
    '',
    '> GENERATED FILE — edit `agents/registry.json`, then run `node scripts/render-agent-catalog.mjs`.',
    '',
    `This catalog contains ${agents.length} agent roles. A role is included only when model-directed observation, judgment, tool use, feedback, and effect evidence are implemented or explicitly planned.`,
    '',
    'Lifecycle is the checked-in product state. Current health, last success, leases, and receipts belong to runtime state and must be joined at presentation time.',
    '',
  ];
  for (const organ of ORGAN_ORDER) {
    const members = agents.filter((agent) => agent.organ === organ);
    if (members.length === 0) continue;
    lines.push(`## ${ORGAN_LABEL[organ]}`, '');
    for (const agent of members) {
      const [icon, label] = LIFECYCLE[agent.lifecycle];
      const parent = agent.parent_agent_id ? byId.get(agent.parent_agent_id)?.display_name ?? 'Unknown' : '—';
      lines.push(
        `### ${agent.display_name} (\`${agent.agent_id}\`)`,
        '',
        agent.objective,
        '',
        '| Field | Value |',
        '|---|---|',
        `| Lifecycle | ${icon} ${label} |`,
        `| Parent | ${markdown(parent)} |`,
        `| Deployment | ${agent.deployments.join(' + ')} |`,
        `| Effects | ${displayList(agent.effect_classes)} |`,
        `| Skills | ${displayList(agent.skills)} |`,
        `| Tools | ${displayList(agent.tools)} |`,
        `| Canonical adapters | ${displayList(agent.loop_adapters)} |`,
        `| Legacy runtime families | ${displayList(agent.runtime_families)} |`,
        `| Source | ${evidenceLinks(agent.source_refs) || '—'} |`,
        `| Evidence/spec | ${evidenceLinks(agent.evidence_refs)} |`,
        '',
      );
    }
  }
  return `${lines.join('\n').trimEnd()}\n`;
}

export function updateMarkedSection(readme, body) {
  const start = readme.indexOf(START_MARKER);
  const end = readme.indexOf(END_MARKER);
  if (start < 0 || end < 0 || end < start) {
    throw new Error('README agent registry markers are missing or malformed');
  }
  const before = readme.slice(0, start + START_MARKER.length);
  const after = readme.slice(end);
  return `${before}\n${body.trim()}\n${after}`;
}

export function generatedDocsMatch(registry, { readme, readmeJa, catalog }) {
  let expectedReadme;
  let expectedReadmeJa;
  try {
    expectedReadme = updateMarkedSection(readme, renderReadmeSection(registry));
    expectedReadmeJa = updateMarkedSection(readmeJa, renderReadmeSection(registry, { locale: 'ja' }));
  } catch {
    return false;
  }
  return expectedReadme === readme
    && expectedReadmeJa === readmeJa
    && renderCatalog(registry) === catalog;
}

function loadReferences(repoRoot) {
  const skills = JSON.parse(readFileSync(resolve(repoRoot, 'skills/registry.json'), 'utf8'));
  const adapters = JSON.parse(readFileSync(resolve(repoRoot, 'apps/life-manager/config/loop-adapters.json'), 'utf8'));
  const inventory = JSON.parse(readFileSync(resolve(repoRoot, 'docs/migrations/openclaw/runtime-inventory.json'), 'utf8'));
  return {
    knownSkillIds: new Set(Object.keys(skills.slots)),
    knownAdapterIds: new Set(adapters.adapters.map((adapter) => adapter.adapter_id)),
    knownRuntimeFamilies: new Set(inventory.jobs.map((job) => job.target_adapter).filter(Boolean)),
  };
}

function atomicWrite(path, text) {
  const temporary = `${path}.${process.pid}.tmp`;
  writeFileSync(temporary, text);
  renameSync(temporary, path);
}

function runCli() {
  const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
  const registry = JSON.parse(readFileSync(resolve(repoRoot, 'agents/registry.json'), 'utf8'));
  const errors = validateRegistry(registry, { repoRoot, ...loadReferences(repoRoot) });
  if (errors.length > 0) {
    process.stderr.write(`${JSON.stringify({ valid: false, errors }, null, 2)}\n`);
    process.exitCode = 1;
    return;
  }
  const readmePath = resolve(repoRoot, registry.generated_docs.readme);
  const readmeJaPath = resolve(repoRoot, registry.generated_docs.readme_ja);
  const catalogPath = resolve(repoRoot, registry.generated_docs.catalog);
  const readme = readFileSync(readmePath, 'utf8');
  const readmeJa = readFileSync(readmeJaPath, 'utf8');
  const catalog = readFileSync(catalogPath, 'utf8');
  if (process.argv.includes('--check')) {
    if (!generatedDocsMatch(registry, { readme, readmeJa, catalog })) {
      process.stderr.write('Agent registry generated documentation is stale.\n');
      process.exitCode = 1;
      return;
    }
    process.stdout.write(`${JSON.stringify({ current: true, agents: registry.agents.length })}\n`);
    return;
  }
  atomicWrite(readmePath, updateMarkedSection(readme, renderReadmeSection(registry)));
  atomicWrite(readmeJaPath, updateMarkedSection(readmeJa, renderReadmeSection(registry, { locale: 'ja' })));
  atomicWrite(catalogPath, renderCatalog(registry));
  process.stdout.write(`${JSON.stringify({ rendered: true, agents: registry.agents.length })}\n`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  runCli();
}
