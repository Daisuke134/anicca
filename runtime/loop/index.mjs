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
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

import { readDotenvFile } from './dotenv.mjs';
import { loadConfig } from './config.mjs';
import { selectTier } from './tier.mjs';
import { fetchUsdcBalance } from './balance.mjs';
import { assembleContext } from './context.mjs';
import { selfEval } from './self-eval.mjs';
import { think } from './brain.mjs';
import { parseToolCall } from './parse-tool-call.mjs';
import { runSkill } from './run-skill.mjs';
import { isEarnSlot, earnStrategyFor, earnSkillRelPath } from './earn-slot.mjs';
import { isLooping } from './loop-detect.mjs';
import { formatRecord } from './ledger-record.mjs';
import { appendLedgerLine, readLedgerLines } from './ledger.mjs';
import { classifyEarnResult, defaultEarnLedgerPath } from './earn-detect.mjs';
import { redactPrivateKeyPatterns } from './env-filter.mjs';
import { liveSlotNames } from './prompt.mjs';
import {
  filterCatalog,
  DEFAULT_BOOTSTRAP_RESERVE_USDC,
  hasOpenRiskPositionOfYield,
  hasOpenRiskPositionOfHlTrade,
} from './catalog-gate.mjs';

const execFileAsync = promisify(execFile);

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
  // S2 FIX (2026-06-22): the earn skill (+ its node_modules) lives in ANICCA_HOME (synced by the daemon),
  // NOT in the code repo — the old repoRoot path resolved to ~/anicca/skills/earn/lib/ledger.mjs which
  // does not exist there → ERR_MODULE_NOT_FOUND → isProfitable=()=>false on EVERY boot, so no wake could
  // ever be classified profitable. Resolve from ANICCA_HOME first (where the file + viem actually are),
  // fall back to the code repo for dev.
  const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..');
  // FIND-IMPL-006 FIX: the real export lives in skills/_shared/lib/ledger.mjs (record.mjs imports it from
  // ../../_shared/lib/ledger.mjs); the old skills/earn/lib/ledger.mjs path does NOT exist → isProfitable
  // silently fell back to ()=>false on every boot, so NO wake was ever classified profitable. Try the
  // real _shared path first (ANICCA_HOME then repo), keep the legacy paths as last-resort fallbacks.
  const candidates = [
    path.join(ANICCA_HOME, 'skills', '_shared', 'lib', 'ledger.mjs'),
    path.join(repoRoot, 'skills', '_shared', 'lib', 'ledger.mjs'),
    path.join(ANICCA_HOME, 'skills', 'earn', 'lib', 'ledger.mjs'),
    path.join(repoRoot, 'skills', 'earn', 'lib', 'ledger.mjs'),
  ];
  for (const p of candidates) {
    try { const m = await import(p); if (typeof m.isProfitable === 'function') { isProfitable = m.isProfitable; break; } } catch { /* try next */ }
  }
  if (!isProfitable) {
    process.stderr.write('[loop] WARNING: could not load isProfitable from earn skill; all wakes will be non-profitable\n');
    isProfitable = () => false;
  }
}

// Load the skill registry → live slots + catalog (spec 25 O1: the LLM picks
// among the REAL live skills, not an opaque single "earn" slot).
// anicca-agent-economy REQ-201: also capture each live slot's `risk`/`alwaysAvailable` classification
// (maintainer-set DATA in registry.json, not something inferred at runtime) so the per-wake bootstrap-
// reserve catalog gate below (filterCatalog) has real `riskTagOf`/`alwaysAvailableOf` inputs.
let activeSkillSlots = [];
let skillCatalog = {};
let riskTagBySlot = {};
let alwaysAvailableBySlot = {};
{
  const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..');
  const registryPath = path.join(repoRoot, 'skills', 'registry.json');
  try {
    const registry = JSON.parse(await fs.readFile(registryPath, 'utf8'));
    activeSkillSlots = liveSlotNames(registry);
    for (const name of activeSkillSlots) {
      const slotDef = registry.slots[name] || {};
      skillCatalog[name] = slotDef.summary || '';
      riskTagBySlot[name] = slotDef.risk;
      alwaysAvailableBySlot[name] = slotDef.alwaysAvailable === true;
    }
    process.stderr.write(`[loop] live skills: ${activeSkillSlots.join(', ') || '(none)'}\n`);
  } catch (err) {
    process.stderr.write(`[loop] WARNING: could not read registry.json (${err.message}); falling back to ['earn']\n`);
    activeSkillSlots = ['earn'];
  }
}

function riskTagOf(slotName) {
  return riskTagBySlot[slotName];
}
function alwaysAvailableOf(slotName) {
  return alwaysAvailableBySlot[slotName] === true;
}

/**
 * queryHlTradeOpenPositions — the REAL Hyperliquid position query REQ-201's `hl_trade` open-position
 * carve-out needs (see catalog-gate.mjs's hasOpenRiskPositionOfHlTrade, which invokes this ONLY when
 * balanceUsdc < BOOTSTRAP_RESERVE_USDC for the current wake). Reuses the SAME primitive
 * `skills/earn/hl-trade/hl.py account` already uses in production (its own `open_positions` array,
 * derived from `info.user_state(address).assetPositions` filtered to nonzero `szi`) by invoking it as a
 * subprocess -- the exact same tool `skills/earn/run.sh` already shells out to (same dedicated-venv
 * resolution: `skills/earn/hl-trade/.venv/bin/python` if present, else plain `python3`), not a new API
 * surface. Any failure (missing venv/deps, unfunded account, network) is caught by the caller
 * (hasOpenRiskPositionOfHlTrade), which fails OPEN (assumes a position may exist) rather than crashing
 * the wake loop or silently hiding `hl_trade` from an instance that might need it to close a position.
 */
async function queryHlTradeOpenPositions() {
  const hlDir = path.join(ANICCA_HOME, 'skills', 'earn', 'hl-trade');
  const hlScript = path.join(hlDir, 'hl.py');
  const venvPython = path.join(hlDir, '.venv', 'bin', 'python');
  let pythonBin = 'python3';
  try { await fs.access(venvPython); pythonBin = venvPython; } catch { /* fall back to system python3 */ }
  const { stdout } = await execFileAsync(pythonBin, [hlScript, 'account'], { timeout: 15000 });
  return JSON.parse(stdout);
}

// ── State ─────────────────────────────────────────────────────────────────────

let currentTier = { tier: 'broke', model: config.ANICCA_FREE_MODEL || 'free/gpt-oss-120b' };
let recentActions = [];
// When a loop is detected, the repeated slot is parked here and FORBIDDEN on the next wake (then cleared
// once the model picks something else) — this is what actually breaks the cook/x402 spin (Dais 2026-06-22).
let avoidSlot = null;
// Escalating cooldown state (§24 adversary #4): a weak free model can ignore the prompt's "forbidden"
// steer and re-pick the SAME dead slot a few wakes later, re-triggering loop_detect on a flat sleep
// forever (observed live: hl_trade thrashed ~25x/session against a constant 300s cooldown). Track how
// many CONSECUTIVE loop_detect events fired on the same slot; each one doubles the next cooldown
// (capped) so repeat-offending costs more wall-clock time. Resets the moment the model diversifies away
// from avoidSlot — the agent's choice is never blocked, only the enforced pause after ignoring it grows.
let loopDetectStreak = 0;
let loopDetectSlot = null;
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
  let liquidUsdc = 0;
  try {
    const balance = await fetchUsdcBalance(walletAddress, config);
    liquidUsdc = typeof balance === 'number' ? balance : 0;
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

  // 3b. SELF-EVAL (H2): read the EARN ledger (the outcome trace, H1) and compute per-action realised P&L,
  // so the prompt can show the AI that e.g. hl-trade ×22 = $0 is a DEAD action. The AI then decides to
  // stop it itself (H3) — no hardcoded "avoid hl_trade" rule; we give it the money signal, it judges.
  let earnSteer = '';
  try {
    const earnLedgerPath = path.join(ANICCA_HOME, 'skills', 'earn', 'state', 'earn-ledger.jsonl');
    const raw = await fs.readFile(earnLedgerPath, 'utf8');
    const earnLines = raw.trim().split('\n').filter(Boolean)
      .map((l) => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);
    earnSteer = selfEval(earnLines, { window: 25 }).steer;
  } catch { /* no earn ledger yet → no steer */ }

  // 4. Loop-detect check (REQ-005). Sleeping alone did NOT break the loop — the model just re-picked the
  // same slot+args next wake (cook×19 / x402×10 with identical args, observed 2026-06-22). So when a loop
  // is detected we (a) remember the repeated slot, (b) RESET the action history so the detector doesn't
  // instantly re-fire on stale entries, and (c) sleep briefly — then the NEXT wake's prompt FORBIDS that
  // slot, forcing the model to diversify (try a different earn path / actually act on what it found).
  const loopWindow = cfgNum(config.LOOP_DETECT_WINDOW, 3);
  if (loopWindow > 0 && isLooping(recentActions, loopWindow)) {
    avoidSlot = recentActions[recentActions.length - 1]?.slot || null;
    // Same slot re-offending back-to-back → escalate; a different slot looping → fresh streak of 1.
    loopDetectStreak = (avoidSlot && avoidSlot === loopDetectSlot) ? loopDetectStreak + 1 : 1;
    loopDetectSlot = avoidSlot;
    process.stderr.write(`[loop] Loop detected on '${avoidSlot}' (streak ${loopDetectStreak}) — forbidding it next wake to force diversification\n`);
    recentActions = [];
    const baseSleepS = cfgNum(config.SLEEP_LOOP_DETECT_S, 300);
    const maxSleepS = cfgNum(config.SLEEP_LOOP_DETECT_MAX_S, 3600);
    const sleepS = Math.min(baseSleepS * (2 ** (loopDetectStreak - 1)), maxSleepS);
    const record = formatRecord({ ts, wake_id: wakeId, kind: 'loop_detect', slot: avoidSlot, sleep_s: sleepS, streak: loopDetectStreak });
    await safeAppend(LEDGER_PATH, record);
    await sleepSecs(sleepS);
    return;
  }

  // 5. Assemble context
  // PATCH 3: summarize the latest deployed position from the ledger (no extra RPC) so the prompt
  // shows the model its portfolio and it can DECIDE a strategy from it.
  const lastYield = (Array.isArray(recentLedger) ? recentLedger : []).slice().reverse()
    .find(l => String(l && l.source || '').startsWith('yield') && l.tx);
  const positionsSummary = lastYield
    ? `~$${lastYield.deposited_usdc ?? '?'} in ${lastYield.source} (last tx ${String(lastYield.tx).slice(0, 10)})`
    : '';

  // 5b. anicca-agent-economy REQ-201/202/203: bootstrap-reserve catalog eligibility gate. Below
  // BOOTSTRAP_RESERVE_USDC, hide capital-risking earn slots from THIS wake's catalog/tool menu --
  // except a slot the instance currently needs to close/withdraw an ALREADY-open position in (the
  // FIND-003 carve-out). `hasOpenRiskPositionOf('yield')` reuses the SAME already-fetched ledger scan
  // as `positionsSummary` above (no new I/O); `hasOpenRiskPositionOf('hl_trade')` is resolved via the
  // lazy, threshold-gated Hyperliquid query (catalog-gate.mjs's hasOpenRiskPositionOfHlTrade only
  // actually calls queryHlTradeOpenPositions when liquidUsdc is below the reserve). Both booleans are
  // fully resolved here, BEFORE the pure filterCatalog call, so filterCatalog itself stays pure.
  const openPositionYield = hasOpenRiskPositionOfYield(recentLedger);
  const openPositionHlTrade = await hasOpenRiskPositionOfHlTrade({
    balanceUsdc: liquidUsdc,
    reserveThresholdUsdc: DEFAULT_BOOTSTRAP_RESERVE_USDC,
    queryFn: queryHlTradeOpenPositions,
  });
  function hasOpenRiskPositionOf(slotName) {
    if (slotName === 'yield') return openPositionYield;
    if (slotName === 'hl_trade') return openPositionHlTrade;
    return false; // no carve-out mechanism specified/required for any other slot (REQ-201)
  }
  let eligibleSkillSlots = activeSkillSlots;
  try {
    eligibleSkillSlots = filterCatalog({
      balanceUsdc: liquidUsdc,
      allSlotNames: activeSkillSlots,
      riskTagOf,
      alwaysAvailableOf,
      hasOpenRiskPositionOf,
      reserveThresholdUsdc: DEFAULT_BOOTSTRAP_RESERVE_USDC,
    });
  } catch (err) {
    process.stderr.write(`[loop] catalog-gate filterCatalog failed (${err.message}) — falling back to the full unfiltered catalog\n`);
    eligibleSkillSlots = activeSkillSlots;
  }

  const ctx = assembleContext({
    walletAddress,
    balanceUsdc: liquidUsdc, // REAL liquid (was broke?0:undefined → always 0, so the buffer steer saw $0 for everyone)
    tier: currentTier.tier,
    model: currentTier.model,
    recentLedgerLines: recentLedger,
    genesisPrompt,
    wakeId,
    ts,
    activeSkillSlots: eligibleSkillSlots,
    skillCatalog,
    positionsSummary,
    earnSteer,
    avoidSlot,
    recentSlots: recentActions.map((a) => a.slot),
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

  // 8. Execute skill. The model picked a slot — if it's not the forbidden one, the diversification worked,
  // so clear the avoid flag AND the escalating-cooldown streak (the thrash pattern broke; a fresh streak
  // starts from 1 if this or any slot loops again later).
  if (slot !== avoidSlot) { avoidSlot = null; loopDetectStreak = 0; loopDetectSlot = null; }
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
  } else if (isEarnSlot(slot)) {
    // Only classify earn from the earn-ledger line (exit code 0 alone is NOT sufficient).
    // isEarnSlot covers the legacy action slots AND per-method nested earn/<sub> (gig/clip/affiliate/video/audit).
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
    // OBSERVABILITY: log the model's decided args (strategy + params) so we can SEE what it chose each
    // wake — without this the wake line had no `args`, which read as "the model decided nothing" when it
    // actually did. Empty object when the model passed none.
    ...(args && Object.keys(args).length ? { args } : {}),
    ...(kind === 'wake' ? { profitable } : {}),
    ...(skillResult.exitCode != null ? { exit_code: skillResult.exitCode } : {}),
    // DEEP FEEDBACK FIX (Dais 2026-06-22): record a short summary of what the skill ACTUALLY returned
    // (cook's findings, x402's sales=0, yield's action) so the NEXT wake's prompt shows OUTCOMES, not
    // just "I ran cook" — the model was re-cooking the same query because it never saw the result.
    ...(safeObservation ? { result: safeObservation.replace(/\s+/g, ' ').slice(0, 180) } : {}),
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
  // PATCH 6: the earn action slots (yield/hl_trade/x402_sell/token_launch) all run the one earn skill;
  // the slot names the strategy (mapped in buildSkillEnv). `earn` stays as the back-compat fat tool.
  // Single source of the slot→path rule (earn-slot.earnSkillRelPath): legacy action slots → the fat
  // skills/earn/run.sh; earn/<sub> + non-earn → skills/<slot>/run.sh. ANICCA_EARN_SKILL still overrides
  // the fat earn skill (tests). rel.split('/') keeps it cross-platform via path.join.
  const rel = earnSkillRelPath(slot);
  if (rel === 'earn/run.sh' && config.ANICCA_EARN_SKILL) {
    skillPath = config.ANICCA_EARN_SKILL;
  } else {
    skillPath = path.join(ANICCA_HOME, 'skills', ...rel.split('/'));
  }

  try { await access(skillPath); }
  catch { return { output: `${slot} skill not found`, exitCode: null, timedOut: false, notFound: true }; }

  const timeoutMs = cfgNum(config.SKILL_TIMEOUT_S, 120) * 1000;
  const childEnv = buildSkillEnv(slot, wakeId, config, scrub, args);

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

function buildSkillEnv(slot, wakeId, config, scrub, args) {
  const base = scrub(process.env);
  // O4: pass the model's decision to EVERY skill as $ANICCA_ARGS (JSON). HARD RULE #0 = the skill is
  // the tool, the MODEL decides the strategy/params; the skill reads its decision here. Optional —
  // skills keep a safe default when args is absent.
  const a = (args && typeof args === 'object') ? args : {};
  const ANICCA_ARGS = JSON.stringify(a);
  // PATCH 6: each earn ACTION is its own slot now — the SLOT names the strategy (yield/hl/x402/token).
  // `earn` stays as the back-compat fat tool that reads args.strategy.
  // isEarnSlot = legacy action slots {earn,yield,hl_trade,x402_sell,token_launch} ∪ per-method earn/<sub>.
  // earnStrategyFor: action slots → their map value; fat `earn` → null (keeps the args.strategy||yield
  // fallback below); earn/<sub> → '<sub>'. So every earn slot — incl gig/clip/affiliate/video — gets
  // EARN_LEDGER/EARN_MODE/WAKE_ID and can write the earn-ledger line the classify gate reads.
  if (isEarnSlot(slot)) {
    return {
      ...base,
      ANICCA_ARGS,
      EARN_MODE:     process.env.EARN_MODE     || 'execute',
      EARN_STRATEGY: process.env.EARN_STRATEGY || earnStrategyFor(slot) || (typeof a.strategy === 'string' && a.strategy.trim() ? a.strategy.trim() : 'yield'),
      WAKE_ID:       wakeId,
      ...(config.EARN_LEDGER ? { EARN_LEDGER: config.EARN_LEDGER } : {}),
    };
  }
  return { ...base, ANICCA_ARGS, WAKE_ID: wakeId };
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
