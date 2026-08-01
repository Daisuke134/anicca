#!/usr/bin/env node

import { existsSync, readFileSync } from 'node:fs';
import { dirname, isAbsolute, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ACTIVE_LIFECYCLES = new Set(['live', 'shadow', 'legacy_live', 'dormant']);
const SECRET_FIELD = /(^|_)(api_?key|private_?key|secret|token|password|credential)s?$/i;
const EFFECT_CLASSES = new Set(['none', 'read', 'draft', 'message', 'publish', 'money']);
const LIFECYCLES = new Set(['live', 'shadow', 'legacy_live', 'dormant', 'planned', 'deprecated']);
const ORGANS = new Set(['executive', 'health', 'finance', 'growth', 'technology', 'opportunity']);
const DEPLOYMENTS = new Set(['local', 'cloud']);
const AGENT_FIELDS = new Set([
  'agent_id',
  'display_name',
  'organ',
  'parent_agent_id',
  'objective',
  'objective_ja',
  'lifecycle',
  'deployments',
  'decision_owner',
  'skills',
  'tools',
  'loop_adapters',
  'runtime_families',
  'effect_classes',
  'source_refs',
  'evidence_refs',
]);

function repositoryPath(repoRoot, relativePath) {
  const root = repoRoot instanceof URL ? fileURLToPath(repoRoot) : repoRoot;
  return resolve(root, relativePath);
}

function escapesRepository(repoRoot, candidate) {
  if (isAbsolute(candidate)) return true;
  const root = resolve(repoRoot instanceof URL ? fileURLToPath(repoRoot) : repoRoot);
  const target = resolve(root, candidate);
  const fromRoot = relative(root, target);
  return fromRoot === '..' || fromRoot.startsWith(`..${process.platform === 'win32' ? '\\' : '/'}`) || isAbsolute(fromRoot);
}

function push(errors, code, agentId, detail) {
  errors.push({ code, agent_id: agentId ?? null, detail });
}

function secretFields(value, prefix = '') {
  if (!value || typeof value !== 'object') return [];
  const found = [];
  for (const [key, child] of Object.entries(value)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (SECRET_FIELD.test(key)) found.push(path);
    found.push(...secretFields(child, path));
  }
  return found;
}

function validatePaths(errors, agent, repoRoot) {
  for (const field of ['source_refs', 'evidence_refs']) {
    for (const ref of agent[field] ?? []) {
      if (isAbsolute(ref)) {
        push(errors, 'absolute_path', agent.agent_id, `${field}: ${ref}`);
        continue;
      }
      if (escapesRepository(repoRoot, ref)) {
        push(errors, 'path_escape', agent.agent_id, `${field}: ${ref}`);
        continue;
      }
      if (!existsSync(repositoryPath(repoRoot, ref))) {
        push(errors, 'missing_repo_path', agent.agent_id, `${field}: ${ref}`);
      }
    }
  }
}

function validateParentGraph(errors, agents) {
  const byId = new Map(agents.map((agent) => [agent.agent_id, agent]));
  const roots = agents.filter((agent) => agent.parent_agent_id === null);
  if (roots.length !== 1) {
    push(errors, 'invalid_root_count', null, `expected 1 root, found ${roots.length}`);
  }
  for (const agent of agents) {
    if (agent.parent_agent_id !== null && !byId.has(agent.parent_agent_id)) {
      push(errors, 'unknown_parent', agent.agent_id, agent.parent_agent_id);
    }
  }

  for (const agent of agents) {
    const seen = new Set();
    let cursor = agent;
    while (cursor?.parent_agent_id !== null && byId.has(cursor?.parent_agent_id)) {
      if (seen.has(cursor.agent_id)) {
        push(errors, 'parent_cycle', agent.agent_id, 'parent hierarchy contains a cycle');
        break;
      }
      seen.add(cursor.agent_id);
      cursor = byId.get(cursor.parent_agent_id);
    }
  }
}

function validateReferences(errors, agent, {
  knownSkillIds,
  knownAdapterIds,
  knownRuntimeFamilies,
}) {
  for (const skillId of agent.skills ?? []) {
    if (knownSkillIds && !knownSkillIds.has(skillId)) {
      push(errors, 'unknown_skill', agent.agent_id, skillId);
    }
  }
  for (const adapterId of agent.loop_adapters ?? []) {
    if (knownAdapterIds && !knownAdapterIds.has(adapterId)) {
      push(errors, 'unknown_adapter', agent.agent_id, adapterId);
    }
  }
  for (const family of agent.runtime_families ?? []) {
    if (knownRuntimeFamilies && !knownRuntimeFamilies.has(family)) {
      push(errors, 'unknown_runtime_family', agent.agent_id, family);
    }
  }
  for (const effectClass of agent.effect_classes ?? []) {
    if (!EFFECT_CLASSES.has(effectClass)) {
      push(errors, 'invalid_effect_class', agent.agent_id, effectClass);
    }
  }
}

function validStringArray(value, { nonempty = false } = {}) {
  return Array.isArray(value)
    && (!nonempty || value.length > 0)
    && value.every((item) => typeof item === 'string' && item.length > 0)
    && new Set(value).size === value.length;
}

function validateShape(errors, registry, agents) {
  const docs = registry?.generated_docs;
  if (
    registry?.schema_version !== 1
    || !docs
    || typeof docs.readme !== 'string'
    || typeof docs.readme_ja !== 'string'
    || typeof docs.catalog !== 'string'
    || agents.length === 0
  ) {
    push(errors, 'schema_violation', null, 'invalid top-level registry shape');
  }

  for (const agent of agents) {
    for (const field of Object.keys(agent)) {
      if (!AGENT_FIELDS.has(field)) push(errors, 'unknown_agent_field', agent.agent_id, field);
    }
    const requiredPresent = [...AGENT_FIELDS].every((field) => Object.hasOwn(agent, field));
    const valid = requiredPresent
      && typeof agent.agent_id === 'string'
      && /^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$/.test(agent.agent_id)
      && typeof agent.display_name === 'string'
      && agent.display_name.length > 0
      && ORGANS.has(agent.organ)
      && (agent.parent_agent_id === null || typeof agent.parent_agent_id === 'string')
      && typeof agent.objective === 'string'
      && agent.objective.length > 0
      && typeof agent.objective_ja === 'string'
      && agent.objective_ja.length > 0
      && LIFECYCLES.has(agent.lifecycle)
      && validStringArray(agent.deployments, { nonempty: true })
      && agent.deployments.every((deployment) => DEPLOYMENTS.has(deployment))
      && agent.decision_owner === 'model'
      && ['skills', 'tools', 'loop_adapters', 'runtime_families', 'effect_classes', 'source_refs', 'evidence_refs']
        .every((field) => validStringArray(agent[field]));
    if (!valid) push(errors, 'schema_violation', agent.agent_id, 'invalid agent shape');
  }
}

export function validateRegistry(registry, {
  repoRoot = new URL('..', import.meta.url),
  knownSkillIds,
  knownAdapterIds,
  knownRuntimeFamilies,
} = {}) {
  const errors = [];
  const agents = Array.isArray(registry?.agents) ? registry.agents : [];
  const seenIds = new Set();

  validateShape(errors, registry, agents);
  for (const [field, ref] of Object.entries(registry?.generated_docs ?? {})) {
    if (typeof ref === 'string' && escapesRepository(repoRoot, ref)) {
      push(errors, 'path_escape', null, `generated_docs.${field}: ${ref}`);
    }
  }

  for (const path of secretFields(registry)) {
    push(errors, 'secret_field', null, path);
  }

  for (const agent of agents) {
    if (seenIds.has(agent.agent_id)) {
      push(errors, 'duplicate_agent_id', agent.agent_id, agent.agent_id);
    }
    seenIds.add(agent.agent_id);

    if (ACTIVE_LIFECYCLES.has(agent.lifecycle)) {
      if (!Array.isArray(agent.source_refs) || agent.source_refs.length === 0) {
        push(errors, 'missing_source_evidence', agent.agent_id, agent.lifecycle);
      }
      if (!Array.isArray(agent.evidence_refs) || agent.evidence_refs.length === 0) {
        push(errors, 'missing_verification_evidence', agent.agent_id, agent.lifecycle);
      }
    }
    if (agent.lifecycle === 'planned' && (!Array.isArray(agent.evidence_refs) || agent.evidence_refs.length === 0)) {
      push(errors, 'missing_plan_evidence', agent.agent_id, agent.lifecycle);
    }
    validatePaths(errors, agent, repoRoot);
    validateReferences(errors, agent, { knownSkillIds, knownAdapterIds, knownRuntimeFamilies });
  }

  validateParentGraph(errors, agents);
  return errors;
}

function runCli() {
  const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
  const registryPath = process.argv[2] ? resolve(process.argv[2]) : resolve(repoRoot, 'agents/registry.json');
  const registry = JSON.parse(readFileSync(registryPath, 'utf8'));
  const skillRegistry = JSON.parse(readFileSync(resolve(repoRoot, 'skills/registry.json'), 'utf8'));
  const adapterRegistry = JSON.parse(readFileSync(resolve(repoRoot, 'apps/life-manager/config/loop-adapters.json'), 'utf8'));
  const runtimeInventory = JSON.parse(readFileSync(resolve(repoRoot, 'docs/migrations/openclaw/runtime-inventory.json'), 'utf8'));
  const errors = validateRegistry(registry, {
    repoRoot,
    knownSkillIds: new Set(Object.keys(skillRegistry.slots)),
    knownAdapterIds: new Set(adapterRegistry.adapters.map((adapter) => adapter.adapter_id)),
    knownRuntimeFamilies: new Set(runtimeInventory.jobs.map((job) => job.target_adapter).filter(Boolean)),
  });
  if (errors.length > 0) {
    process.stderr.write(`${JSON.stringify({ valid: false, errors }, null, 2)}\n`);
    process.exitCode = 1;
    return;
  }
  process.stdout.write(`${JSON.stringify({ valid: true, agents: registry.agents.length })}\n`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  runCli();
}
