/**
 * index.mjs — Anicca ReAct automaton loop entry point.
 *
 * REQ-001: Single-wake lifecycle (context → THINK → parse → execute → persist → sleep)
 * REQ-002: Survival-tier model selection
 * REQ-003: Earn skill execution + isProfitable classification via WAKE_ID
 * REQ-004: Private-key isolation
 * REQ-005: Loop detect / idle guard
 * REQ-006: Graceful shutdown on SIGTERM
 * REQ-007: Ledger immutability (append-only)
 * REQ-008: Cloud portability (no macOS-specific code)
 * REQ-009: Config via env / .env file
 * REQ-011: Pluggable brain backend
 *
 * Start via: node runtime/loop/index.mjs
 * Or:        ./start-local.sh node runtime/loop/index.mjs
 */

import { promises as fs } from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

import { readDotenvFile } from './dotenv.mjs';
import { loadConfig } from './config.mjs';
import { selectTier } from './tier.mjs';
import { fetchUsdcBalance } from './balance.mjs';
import { assembleContext } from './context.mjs';
import { think } from './brain.mjs';
import { parseToolCall } from './parse-tool-call.mjs';
import { runSkill } from './run-skill.mjs';
import { isLooping } from './loop-detect.mjs';
import { formatRecord } from './ledger-record.mjs';
import { appendLedgerLine, readLedgerLines } from './ledger.mjs';
import { classifyEarnResult, defaultEarnLedgerPath } from './earn-detect.mjs';
import { redactPrivateKeyPatterns } from './env-filter.mjs';
import { liveSlotNames } from './prompt.mjs';

// Inline ULID generator (no npm dependency — uses crypto.randomUUID as entropy source)
function ulid() {
  const now = Date.now();
  const ts = now.toString(36).toUpperCase().padStart(10, '0').slice(-10);
  const rand = randomUUID().replace(/-/g, '').toUpperCase().slice(0, 16);
  return ts + rand;
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────

const ANICCA_HOME = process.env.ANICCA_HOME;
if (!ANICCA_HOME) {
  process.stderr.write('[loop] FATAL: ANICCA_HOME is not set. Set it to the absolute path of the agent home directory.\n');
  process.exit(1);
}

const dotenvText = await readDotenvFile(ANICCA_HOME);
const config = loadConfig(process.env, dotenvText);

const LEDGER_PATH = path.join(ANICCA_HOME, 'state', 'ledger.jsonl');
const GENESIS_PATH = path.join(ANICCA_HOME, 'identity', 'genesis.md');

// Read genesis prompt (missing = warn + empty string)
let genesisPrompt = '';
try {
  genesisPrompt = await fs.readFile(GENESIS_PATH, 'utf8');
} catch {
  process.stderr.write(`[loop] WARNING: genesis.md not found at ${GENESIS_PATH}\n`);
}

// Load isProfitable from earn skill.
// Canonical path: $repo_root/skills/earn/lib/ledger.mjs
// repo_root = dirname(dirname(dirname(this file))) since this file is at runtime/loop/index.mjs
let isProfitable;
{
  const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..');
  const earnLedgerPath = path.join(repoRoot, 'skills', 'earn', 'lib', 'ledger.mjs');
  try {
    const m = await import(earnLedgerPath);
    isProfitable = m.isProfitable;
  } catch {
    process.stderr.write('[loop] WARNING: could not load isProfitable from earn skill; all wakes will be non-profitable\n');
    isProfitable = () => false;
  }
}

// Load the skill registry → live slots + catalog (spec 25 O1: the LLM picks
// among the REAL live skills, not an opaque single "earn" slot).
let activeSkillSlots = [];
let skillCatalog = {};
{
  const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..');
  const registryPath = path.join(repoRoot, 'skills', 'registry.json');
  try {
    const registry = JSON.parse(await fs.readFile(registryPath, 'utf8'));
    activeSkillSlots = liveSlotNames(registry);
    for (const name of activeSkillSlots) {
      skillCatalog[name] = (registry.slots[name] && registry.slots[name].summary) || '';
    }
    process.stderr.write(`[loop] live skills: ${activeSkillSlots.join(', ') || '(none)'}\n`);
  } catch (err) {
    process.stderr.write(`[loop] WARNING: could not read registry.json (${err.message}); falling back to ['earn']\n`);
    activeSkillSlots = ['earn'];
  }
}

// ── State ─────────────────────────────────────────────────────────────────────

let currentTier = { tier: 'broke', model: config.ANICCA_FREE_MODEL || 'free/gpt-oss-120b' };
let recentActions = [];
let shuttingDown = false;
let currentChildKiller = null; // called to kill in-flight skill on SIGTERM

// ── SIGTERM handler (REQ-006) ─────────────────────────────────────────────────

process.on('SIGTERM', async () => {
  if (shuttingDown) return;
  shuttingDown = true;
  process.stderr.write('[loop] SIGTERM received — flushing shutdown ledger line\n');

  // Kill in-flight child if any
  if (currentChildKiller) {
    try { currentChildKiller(); } catch {}
    // Give child up to 5s to die
    await new Promise(r => setTimeout(r, 5000));
  }

  const wakeId = ulid();
  const record = formatRecord({
    ts: Math.floor(Date.now() / 1000),
    wake_id: wakeId,
    kind: 'shutdown',
    sleep_s: 0,
  });
  try {
    await appendLedgerLine(LEDGER_PATH, record);
  } catch (err) {
    process.stderr.write(`[loop] Could not write shutdown ledger line: ${err.message}\n`);
  }
  process.exit(0);
});

// ── Wake loop ─────────────────────────────────────────────────────────────────

process.stderr.write(`[loop] Starting Anicca loop. ANICCA_HOME=${ANICCA_HOME}\n`);

while (!shuttingDown) {
  await runOneWake();
}

// ── Single wake ───────────────────────────────────────────────────────────────

async function runOneWake() {
  if (shuttingDown) return;

  const wakeId = ulid();
  const ts = Math.floor(Date.now() / 1000);

  // 1. Load wallet address (no key derivation — REQ-004, REQ-008)
  const walletAddress = config.ANICCA_WALLET_ADDRESS || process.env.ANICCA_WALLET_ADDRESS || 'unknown';
  if (walletAddress === 'unknown') {
    process.stderr.write('[loop] WARNING: ANICCA_WALLET_ADDRESS not set, using "unknown"\n');
  }

  // 2. Fetch USDC balance (failure → keep prior tier, REQ-002)
  try {
    const balance = await fetchUsdcBalance(walletAddress, config);
    currentTier = selectTier(balance, config);
  } catch (err) {
    process.stderr.write(`[loop] Balance fetch failed: ${err.message} — keeping tier=${currentTier.tier}\n`);
  }

  // 3. Read recent ledger lines for context
  let recentLedger = [];
  try {
    const all = await readLedgerLines(LEDGER_PATH);
    recentLedger = all.slice(-20);
  } catch {}

  // 4. Loop-detect check (REQ-005)
  const loopWindow = cfgNum(config.LOOP_DETECT_WINDOW, 3);
  if (loopWindow > 0 && isLooping(recentActions, loopWindow)) {
    process.stderr.write(`[loop] Loop detected (${loopWindow} identical actions) — sleeping\n`);
    const sleepS = cfgNum(config.SLEEP_LOOP_DETECT_S, 300);
    const record = formatRecord({ ts, wake_id: wakeId, kind: 'loop_detect', sleep_s: sleepS });
    await safeAppend(LEDGER_PATH, record);
    await sleepSecs(sleepS);
    return;
  }

  // 5. Assemble context
  const ctx = assembleContext({
    walletAddress,
    balanceUsdc: currentTier.tier === 'broke' ? 0 : undefined, // balance already reflected in tier
    tier: currentTier.tier,
    model: currentTier.model,
    recentLedgerLines: recentLedger,
    genesisPrompt,
    wakeId,
    ts,
    activeSkillSlots,
    skillCatalog,
  });

  // 6. THINK (brain call)
  let rawResponse;
  try {
    rawResponse = await think(ctx, config);
  } catch (err) {
    process.stderr.write(`[loop] THINK failed: ${err.message}\n`);
    const sleepS = cfgNum(config.SLEEP_ERROR_S, 60);
    const record = formatRecord({
      ts,
      wake_id: wakeId,
      kind: 'wake_error',
      sleep_s: sleepS,
      error: 'proxy_down',
      model: currentTier.model,
    });
    await safeAppend(LEDGER_PATH, record);
    await sleepSecs(sleepS);
    return;
  }

  // 7. Parse tool call
  const toolCall = parseToolCall(rawResponse);

  if (!toolCall) {
    // Text-only narrate wake
    const sleepS = cfgNum(config.SLEEP_BASE_S, 120);
    const record = formatRecord({
      ts,
      wake_id: wakeId,
      kind: 'narrate',
      sleep_s: sleepS,
      model: currentTier.model,
    });
    await safeAppend(LEDGER_PATH, record);
    await sleepSecs(sleepS);
    return;
  }

  const { slot, args } = toolCall;

  // Sleep tool call
  if (slot === 'sleep') {
    const sleepS = args.seconds != null ? Number(args.seconds) : cfgNum(config.SLEEP_BASE_S, 120);
    const record = formatRecord({
      ts,
      wake_id: wakeId,
      kind: 'narrate',
      sleep_s: sleepS,
      model: currentTier.model,
      note: args.reason || 'agent chose to sleep',
    });
    await safeAppend(LEDGER_PATH, record);
    await sleepSecs(sleepS);
    return;
  }

  // 8. Execute skill
  recentActions.push({ slot, args: args || {} });
  const windowBuf = Math.max(loopWindow * 2, 10);
  if (recentActions.length > windowBuf) {
    recentActions = recentActions.slice(-windowBuf);
  }

  let skillResult;
  let childKillRef = { kill: null };
  currentChildKiller = () => { if (childKillRef.kill) childKillRef.kill(); };

  try {
    skillResult = await runSkillWithKillRef(slot, args, wakeId, config, childKillRef);
  } finally {
    currentChildKiller = null;
  }

  if (shuttingDown) return;

  // 9. Classify earn result (REQ-003 critical invariant)
  let kind = 'wake';
  let profitable = false;

  if (skillResult.notFound) {
    kind = 'skill_missing';
  } else if (skillResult.timedOut) {
    kind = 'skill_timeout';
  } else if (skillResult.exitCode !== 0) {
    kind = 'skill_error';
  } else if (slot === 'earn') {
    // Only classify earn from the earn-ledger line (exit code 0 alone is NOT sufficient)
    const earnLedgerPath = defaultEarnLedgerPath(config);
    const { profitable: p } = await classifyEarnResult(wakeId, earnLedgerPath, isProfitable);
    profitable = p;
  }

  // 10. Persist ledger line (REQ-007)
  const sleepS = cfgNum(config.SLEEP_BASE_S, 120);

  // Redact any private key patterns from observation (PROP-020)
  const safeObservation = redactPrivateKeyPatterns(skillResult.output || '').slice(0, 500);

  const recordFields = {
    ts,
    wake_id: wakeId,
    kind,
    sleep_s: sleepS,
    model: currentTier.model,
    slot,
    ...(kind === 'wake' ? { profitable } : {}),
    ...(skillResult.exitCode != null ? { exit_code: skillResult.exitCode } : {}),
  };

  // Verify ledger line has no private key pattern (PROP-020)
  const recordStr = formatRecord(recordFields);
  const safeRecord = redactPrivateKeyPatterns(recordStr);
  await safeAppend(LEDGER_PATH, safeRecord);

  await sleepSecs(sleepS);
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Run a skill but also expose a kill function so SIGTERM can terminate it.
 */
async function runSkillWithKillRef(slot, args, wakeId, config, killRef) {
  // Import spawn to get the child PID for SIGTERM forwarding
  const { spawn } = await import('node:child_process');
  const { access } = await import('node:fs/promises');
  const { scrubPrivateKeys: scrub, redactPrivateKeyPatterns: redact } = await import('./env-filter.mjs');

  // Resolve skill path
  let skillPath;
  if (slot === 'earn' && config.ANICCA_EARN_SKILL) {
    skillPath = config.ANICCA_EARN_SKILL;
  } else {
    skillPath = path.join(ANICCA_HOME, 'skills', slot.replace('/', path.sep), 'run.sh');
  }

  try { await access(skillPath); }
  catch { return { output: `${slot} skill not found`, exitCode: null, timedOut: false, notFound: true }; }

  const timeoutMs = cfgNum(config.SKILL_TIMEOUT_S, 120) * 1000;
  const childEnv = buildSkillEnv(slot, wakeId, config, scrub);

  return new Promise((resolve) => {
    let output = '';
    let timedOut = false;

    const proc = spawn(skillPath, [], {
      env: childEnv,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    // Expose kill function for SIGTERM handler
    killRef.kill = () => {
      try { proc.kill('SIGTERM'); } catch {}
      setTimeout(() => { try { proc.kill('SIGKILL'); } catch {} }, 5000);
    };

    proc.stdout.on('data', d => { output += d; });
    proc.stderr.on('data', d => { output += d; });

    const timer = setTimeout(() => {
      timedOut = true;
      try { proc.kill('SIGTERM'); } catch {}
      setTimeout(() => { try { proc.kill('SIGKILL'); } catch {} }, 2000);
    }, timeoutMs);

    proc.on('exit', (code) => {
      clearTimeout(timer);
      killRef.kill = null;
      if (timedOut) {
        resolve({ output: `${slot} skill timeout`, exitCode: null, timedOut: true, notFound: false });
        return;
      }
      resolve({ output: redact(output), exitCode: code, timedOut: false, notFound: false });
    });

    proc.on('error', (err) => {
      clearTimeout(timer);
      killRef.kill = null;
      resolve({ output: `${slot} skill error: ${err.message}`, exitCode: null, timedOut: false, notFound: true });
    });
  });
}

function buildSkillEnv(slot, wakeId, config, scrub) {
  const base = scrub(process.env);
  if (slot === 'earn') {
    return {
      ...base,
      EARN_MODE:     process.env.EARN_MODE     || 'discover',
      EARN_STRATEGY: process.env.EARN_STRATEGY || '0xwork',
      WAKE_ID:       wakeId,
      ...(config.EARN_LEDGER ? { EARN_LEDGER: config.EARN_LEDGER } : {}),
    };
  }
  return { ...base, WAKE_ID: wakeId };
}

async function safeAppend(ledgerPath, line) {
  try {
    await appendLedgerLine(ledgerPath, line);
  } catch (err) {
    process.stderr.write(`[loop] Ledger append failed: ${err.message}\n`);
    // Sleep error period; do not crash
    await sleepSecs(config.SLEEP_ERROR_S ?? 60);
  }
}

function sleepSecs(s) {
  const ms = Math.max(0, Math.floor(Number(s) * 1000));
  return new Promise(r => setTimeout(r, ms));
}

/** Safely read a numeric config value, using fallback only when value is null/undefined (not when 0). */
function cfgNum(val, fallback) {
  return val != null ? Number(val) : fallback;
}
