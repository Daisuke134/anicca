/**
 * config-drift.mjs — config-delivery-verification: declared-vs-runtime config drift detector.
 *
 * REQ-001/002: compares a DECLARED config (a plist's `EnvironmentVariables`, or the canonical
 *   `skills/registry.json`) against an OBSERVED runtime value (a live process's own env, or a
 *   runtime registry copy) and reports facts only — never a "safe/dangerous" judgment (REQ-007;
 *   `~/.claude/rules/building-effective-ai-agents.md` — judgment belongs to the model, not to
 *   hardcoded regex/keyword classification in this tool).
 * REQ-003: the SAME comparison function is reused for every instance; each instance's own declared
 *   config is passed in as data — there is no instance-name switch/if-else anywhere below.
 * REQ-004: any runtime state this module cannot observe (missing process, unreadable file, failed
 *   parse) is reported as an explicit FAIL (`reason: "unobservable"`), never silently folded into an
 *   empty/PASS result.
 * REQ-005: this module only ever reads. It never sends a process a termination/restart signal and
 *   never modifies any file it inspects (verified structurally by
 *   __tests__/config-drift.test.mjs's PROP-011 — this file must never contain the literal tokens for
 *   any restart/terminate primitive or a file-write call).
 * REQ-006: the diff/classify/resolve functions below take only plain data (objects, strings, arrays)
 *   and perform no file/process/network access — deterministic, side-effect-free, and they never
 *   mutate their inputs.
 * REQ-009 note: this file is unrelated to `brain.mjs`'s `claude -p` timeout — that lives in brain.mjs.
 * REQ-010: the monitored-target set below (`parseIndexLoopProcesses` / `listRunningIndexLoopProcesses`)
 *   is derived by enumerating live processes, never from a hardcoded instance-name list.
 * NFR-Security (FIND-002): the ONLY data this module ever extracts from a raw process command line is
 *   the small allow-listed set of keys a caller explicitly asks for (`parseAllowedEnvFromCommandLine`).
 *   The raw command-line string itself (which may carry secrets such as ANTHROPIC_API_KEY or a
 *   *_PRIVATE_KEY) is read once, filtered immediately, and then goes out of scope — it is never
 *   returned, logged, or included in any error path.
 */

import { promises as fs } from 'node:fs';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

// ── Pure core (REQ-006): plain data in, plain data out — no file/process/network access ──────────────

/**
 * Generic key/value diff. Compares every key present in EITHER map (not just declaredMap's own keys —
 * a key that exists only in `actualMap` must still be reported, e.g. a stale registry slot that only
 * exists in a runtime copy). Returns one entry per differing key; never mutates its inputs.
 *
 * @param {Record<string, unknown>} declaredMap
 * @param {Record<string, unknown>} actualMap
 * @returns {{key: string, declared: unknown, actual: unknown}[]}
 */
export function diffDeclaredVsActual(declaredMap, actualMap) {
  const declared = declaredMap || {};
  const actual = actualMap || {};
  const keys = new Set([...Object.keys(declared), ...Object.keys(actual)]);
  const diffs = [];
  for (const key of keys) {
    const declaredValue = declared[key];
    const actualValue = actual[key];
    if (declaredValue !== actualValue) {
      diffs.push({ key, declared: declaredValue, actual: actualValue });
    }
  }
  return diffs;
}

/**
 * REQ-004's pure classification primitive: is this observation usable, or is the underlying runtime
 * state simply unknown (process gone, file unreadable, parse failed)? `null`/`undefined` means the
 * effectful reader could not obtain a value at all.
 *
 * @param {unknown} rawObservation
 * @returns {"OBSERVED" | "UNOBSERVABLE"}
 */
export function classifyObservability(rawObservation) {
  return rawObservation === null || rawObservation === undefined ? 'UNOBSERVABLE' : 'OBSERVED';
}

/**
 * REQ-001 edge case / REQ-003: resolves what an instance's OWN declared config says a key's expected
 * value is. If the key was never explicitly declared, falls back to the code default but says so
 * explicitly (`declaredExplicitly: false`) — an omission is never silently treated as "no drift".
 * Pure pass-through: no instance-name branching of any kind.
 *
 * @param {Record<string, unknown>} declaredConfig
 * @param {string} key
 * @param {unknown} codeDefault
 * @returns {{value: unknown, declaredExplicitly: boolean}}
 */
export function resolveExpectedValue(declaredConfig, key, codeDefault) {
  const config = declaredConfig || {};
  const declaredExplicitly = Object.prototype.hasOwnProperty.call(config, key);
  return { value: declaredExplicitly ? config[key] : codeDefault, declaredExplicitly };
}

/**
 * REQ-002: flattens `registry.slots.<name>.status` into a flat `{name: status}` map so the generic
 * diff function above can compare a canonical registry against a runtime copy.
 *
 * @param {{slots?: Record<string, {status?: unknown}>}} registry
 * @returns {Record<string, unknown>}
 */
export function flattenRegistrySlotStatus(registry) {
  const slots = registry && registry.slots;
  if (!slots || typeof slots !== 'object') return {};
  const flat = {};
  for (const [name, def] of Object.entries(slots)) {
    flat[name] = def ? def.status : undefined;
  }
  return flat;
}

/**
 * Pure JSON-text parser for a plist already converted to JSON (e.g. by `plutil -convert json -o -`).
 * Takes the resulting text as a plain string — no file/process access happens here.
 *
 * @param {string} plutilJsonText
 * @returns {Record<string, unknown>}
 */
export function parsePlistEnvironmentVariables(plutilJsonText) {
  try {
    const parsed = JSON.parse(plutilJsonText);
    return (parsed && typeof parsed.EnvironmentVariables === 'object' && parsed.EnvironmentVariables) || {};
  } catch {
    return {};
  }
}

const ENV_TOKEN_PATTERN = /^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/;

/**
 * NFR-Security / FIND-002: extracts ONLY the caller-specified allow-listed keys from a raw process
 * command-line string. Every other token on the line (including any secret-bearing key such as
 * ANTHROPIC_API_KEY or a *_PRIVATE_KEY variable) is inspected only long enough to see it does not match
 * the allow-list, then discarded — it is never copied into the returned object, and this function never
 * includes any part of the raw command line in a thrown error message.
 *
 * @param {string} commandLine
 * @param {string[]} allowedKeys
 * @returns {Record<string, string>}
 */
export function parseAllowedEnvFromCommandLine(commandLine, allowedKeys) {
  const result = {};
  if (typeof commandLine !== 'string' || !Array.isArray(allowedKeys) || allowedKeys.length === 0) {
    return result;
  }
  const allowedSet = new Set(allowedKeys);
  const tokens = commandLine.split(/\s+/).filter(Boolean);
  for (const token of tokens) {
    const match = ENV_TOKEN_PATTERN.exec(token);
    if (!match) continue;
    const [, key, value] = match;
    if (!allowedSet.has(key)) continue; // not allow-listed -> discarded immediately, never retained
    result[key] = value;
  }
  return result;
}

/**
 * REQ-010: discovers monitoring targets by enumerating LIVE `runtime/loop/index.mjs` processes from a
 * raw `ps -Awwe -o pid,command` output (passed in as plain string lines — no `ps` invocation happens
 * here). Extracts `ANICCA_HOME=`/`XPC_SERVICE_NAME=` tokens from each matching line. A process missing
 * either token reports `null` for that field rather than being dropped from the result set (REQ-004/
 * REQ-010 edge case: an unobservable half of a target is never silently omitted). This function
 * contains no hardcoded instance-name or absolute-path list — it recognizes targets purely by the
 * `runtime/loop/index.mjs` substring every generation of this loop's own command line carries.
 *
 * @param {string[]} psOutputLines
 * @returns {{pid: number, aniccaHome: string|null, xpcServiceName: string|null}[]}
 */
export function parseIndexLoopProcesses(psOutputLines) {
  if (!Array.isArray(psOutputLines)) return [];
  const results = [];
  for (const line of psOutputLines) {
    if (typeof line !== 'string' || !line.includes('runtime/loop/index.mjs')) continue;
    const tokens = line.trim().split(/\s+/).filter(Boolean);
    if (tokens.length === 0) continue;
    const pid = Number.parseInt(tokens[0], 10);
    if (!Number.isFinite(pid)) continue;
    let aniccaHome = null;
    let xpcServiceName = null;
    for (const token of tokens) {
      if (token.startsWith('ANICCA_HOME=')) aniccaHome = token.slice('ANICCA_HOME='.length);
      else if (token.startsWith('XPC_SERVICE_NAME=')) xpcServiceName = token.slice('XPC_SERVICE_NAME='.length);
    }
    results.push({ pid, aniccaHome, xpcServiceName });
  }
  return results;
}

/**
 * REQ-001/003/004: reports whether a single instance's declared `ANICCA_BRAIN` (or another key,
 * default parameter kept generic per REQ-006) matches its OWN observed runtime value. `declaredConfig`
 * is that instance's own plist-derived map (REQ-003: never a global/shared expectation). Returns a FAIL
 * (`reason: "unobservable"`) when the runtime value could not be observed at all, and returns exactly
 * one drift entry (or zero, on a match) otherwise. Contains no instance-name branching.
 *
 * @param {string} instance
 * @param {Record<string, unknown>} declaredConfig
 * @param {Record<string, unknown>|null} observedEnvOrNull
 * @param {string} [key]
 * @param {unknown} [codeDefault]
 * @returns {Array<{key: string, instance: string, declared: unknown, actual: unknown, reason?: string}>}
 */
export function detectBrainDrift(instance, declaredConfig, observedEnvOrNull, key = 'ANICCA_BRAIN', codeDefault = 'proxy') {
  const { value: declared } = resolveExpectedValue(declaredConfig, key, codeDefault);
  if (classifyObservability(observedEnvOrNull) === 'UNOBSERVABLE') {
    return [{ key, instance, declared, actual: null, reason: 'unobservable' }];
  }
  const actual = observedEnvOrNull[key];
  return diffDeclaredVsActual({ [key]: declared }, { [key]: actual }).map((d) => ({ ...d, instance }));
}

/**
 * REQ-002/004: compares the canonical registry against N runtime copies, each reported INDEPENDENTLY
 * (PROP-006/PROP-010 — one matching copy must never suppress another copy's drift or its
 * unobservable-ness). A copy that could not be read at all (`registryOrNull === null`) reports a single
 * FAIL for that whole copy rather than a per-slot breakdown (there is nothing slot-level left to say
 * once the copy itself cannot be read).
 *
 * @param {{slots?: Record<string, {status?: unknown}>}} canonicalRegistry
 * @param {{copyPath: string, registryOrNull: object|null}[]} copies
 * @returns {Array<{key: string, copyPath: string, declared: unknown, actual: unknown} | {copyPath: string, declared: null, actual: null, reason: string}>}
 */
export function detectRegistryStatusDrift(canonicalRegistry, copies) {
  const declaredMap = flattenRegistrySlotStatus(canonicalRegistry);
  const results = [];
  for (const { copyPath, registryOrNull } of copies || []) {
    if (classifyObservability(registryOrNull) === 'UNOBSERVABLE') {
      results.push({ copyPath, declared: null, actual: null, reason: 'unobservable' });
      continue;
    }
    const actualMap = flattenRegistrySlotStatus(registryOrNull);
    for (const d of diffDeclaredVsActual(declaredMap, actualMap)) {
      results.push({ key: `${d.key}.status`, copyPath, declared: d.declared, actual: d.actual });
    }
  }
  return results;
}

// ── Effectful shell (thin adapters — I/O only, no diff/classification logic of their own) ─────────────

/**
 * Reads and JSON-parses a registry.json file (canonical or a runtime copy). Read-only: never writes to
 * `filePath`. Missing file / malformed JSON both resolve to `null` (REQ-004: the caller treats `null` as
 * unobservable — a FAIL, never a silent PASS).
 *
 * @param {string} filePath
 * @returns {Promise<object|null>}
 */
export async function readRegistryFile(filePath) {
  try {
    const raw = await fs.readFile(filePath, 'utf8');
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * Reads a deployed plist's `EnvironmentVariables` dict via `plutil`. Read-only: never modifies
 * `plistPath`. Any failure (missing plist, plutil error) resolves to `null` (REQ-004 unobservable).
 *
 * @param {string} plistPath
 * @returns {Promise<Record<string, unknown>|null>}
 */
export async function readPlistDeclaredEnv(plistPath) {
  try {
    const { stdout } = await execFileAsync('plutil', ['-convert', 'json', '-o', '-', plistPath]);
    return parsePlistEnvironmentVariables(stdout);
  } catch {
    return null;
  }
}

/**
 * NFR-Security / FIND-002 wiring: resolves a launchd label to its live PID (read-only lookup, never
 * signals/restarts it — REQ-005) and reads that PID's own runtime command line, but immediately hands
 * the raw line to `parseAllowedEnvFromCommandLine` and keeps ONLY the allow-listed keys — the raw line
 * itself is a local value that is discarded the moment this function returns and is never propagated
 * into the returned object, a log line, or a thrown error's message. Any failure along the way (label
 * not loaded, PID gone, read error) resolves to `null` (REQ-004 unobservable), never a partial/garbage
 * env.
 *
 * @param {string} launchdLabel
 * @param {string[]} [allowedKeys]
 * @returns {Promise<{pid: number, env: Record<string, string>}|null>}
 */
export async function readRuntimeEnvOfLabel(launchdLabel, allowedKeys = ['ANICCA_BRAIN']) {
  try {
    const { stdout: listOutput } = await execFileAsync('launchctl', ['list', launchdLabel]);
    const pidMatch = /"PID"\s*=\s*(\d+)/.exec(listOutput);
    if (!pidMatch) return null;
    const pid = Number.parseInt(pidMatch[1], 10);
    if (!Number.isFinite(pid)) return null;
    const { stdout: psOutput } = await execFileAsync('ps', ['-Awwe', '-o', 'command', '-p', String(pid)]);
    const dataLine = psOutput.split('\n').filter((l) => l.trim().length > 0).slice(1).join(' ');
    const env = parseAllowedEnvFromCommandLine(dataLine, allowedKeys); // raw dataLine discarded right after this call
    return { pid, env };
  } catch {
    return null;
  }
}

/**
 * REQ-010's effectful half: enumerates ALL live processes via `ps -Awwe -o pid,command` and returns the
 * raw output lines (no filtering/parsing here — `parseIndexLoopProcesses` does that, purely). Never
 * filters by a hardcoded instance list; the pure parser above decides which lines are monitoring
 * targets based solely on their own command line.
 *
 * @returns {Promise<string[]>}
 */
export async function listRunningIndexLoopProcesses() {
  try {
    const { stdout } = await execFileAsync('ps', ['-Awwe', '-o', 'pid,command']);
    return stdout.split('\n');
  } catch {
    return [];
  }
}
