/**
 * run-skill.mjs — Effectful: spawn skills/earn/run.sh with scrubbed env.
 *
 * REQ-003: Tool execution — earn skill.
 * REQ-004: Private-key isolation — never pass *_WALLET_KEY/*_PRIVATE_KEY/*_PRIV_KEY to child.
 * REQ-008: No macOS-only code.
 */

import { spawn } from 'node:child_process';
import path from 'node:path';
import { scrubPrivateKeys, redactPrivateKeyPatterns } from './env-filter.mjs';

/**
 * Spawn a skill entrypoint and return combined stdout+stderr.
 *
 * @param {string} slot - skill slot name (e.g. 'earn')
 * @param {object} args - tool call arguments from the model
 * @param {string} wakeId - ULID of the current wake
 * @param {object} config - loaded config (ANICCA_HOME, SKILL_TIMEOUT_S, ANICCA_EARN_SKILL, EARN_LEDGER)
 * @returns {Promise<{ output: string, exitCode: number|null, timedOut: boolean, notFound: boolean }>}
 */
export async function runSkill(slot, args, wakeId, config) {
  const skillPath = resolveSkillPath(slot, config);

  // Check existence
  const { access } = await import('node:fs/promises');
  try {
    await access(skillPath);
  } catch {
    return { output: `${slot} skill not found`, exitCode: null, timedOut: false, notFound: true };
  }

  const timeoutMs = (Number(config.SKILL_TIMEOUT_S) || 120) * 1000;

  // Build env: start with scrubbed parent env
  const childEnv = buildSkillEnv(slot, wakeId, config);

  return new Promise((resolve) => {
    let output = '';
    let timedOut = false;

    const proc = spawn(skillPath, [], {
      env: childEnv,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    proc.stdout.on('data', d => { output += d; });
    proc.stderr.on('data', d => { output += d; });

    const timer = setTimeout(() => {
      timedOut = true;
      proc.kill('SIGTERM');
      setTimeout(() => { try { proc.kill('SIGKILL'); } catch {} }, 2000);
    }, timeoutMs);

    proc.on('exit', (code) => {
      clearTimeout(timer);
      if (timedOut) {
        resolve({ output: `${slot} skill timeout`, exitCode: null, timedOut: true, notFound: false });
        return;
      }
      // Redact any private key patterns from observation (REQ-004 / PROP-020)
      const safeOutput = redactPrivateKeyPatterns(output);
      resolve({ output: safeOutput, exitCode: code, timedOut: false, notFound: false });
    });

    proc.on('error', (err) => {
      clearTimeout(timer);
      resolve({ output: `${slot} skill error: ${err.message}`, exitCode: null, timedOut: false, notFound: true });
    });
  });
}

/**
 * Build the environment for the skill subprocess.
 * - Scrubs private keys from parent env (REQ-004)
 * - Adds skill-specific vars (EARN_MODE, EARN_STRATEGY, WAKE_ID, EARN_LEDGER)
 */
function buildSkillEnv(slot, wakeId, config) {
  const scrubbed = scrubPrivateKeys(process.env);
  const codeRoot = config.ANICCA_CODE_ROOT || process.env.ANICCA_CODE_ROOT;

  if (slot === 'earn') {
    return {
      ...scrubbed,
      ...(codeRoot ? { ANICCA_CODE_ROOT: codeRoot } : {}),
      // DEFAULT = actually EARN, not narrate. The old defaults (discover + 0xwork) meant every earn
      // wake just wrote a "discover" narrate line and waited for an external poster task that never
      // came — so anicca NEVER earned (ledger = endless earn_usdc:0). Fixed 2026-06-21:
      //   EARN_MODE=execute  → perform a real on-chain earn this wake (not a narrate stub)
      //   EARN_STRATEGY=yield → the reliable, always-available earner (deploy idle USDC to Beefy/Aave
      //     v3 yield; execute-yield.mjs keeps a compute buffer + ensures gas, safe to run each wake).
      //     0xwork/swap/x402 remain available via env override when the model picks them.
      EARN_MODE:     process.env.EARN_MODE     || 'execute',
      EARN_STRATEGY: process.env.EARN_STRATEGY || 'yield',
      WAKE_ID:       wakeId,
      // Earn ledger path — skill will default to $HERE/state/earn-ledger.jsonl
      // but we can override via EARN_LEDGER if the test needs a custom path
      ...(config.EARN_LEDGER ? { EARN_LEDGER: config.EARN_LEDGER } : {}),
    };
  }

  return { ...scrubbed, ...(codeRoot ? { ANICCA_CODE_ROOT: codeRoot } : {}), WAKE_ID: wakeId };
}

/**
 * Resolve the skill entrypoint path.
 * - ANICCA_EARN_SKILL env var overrides the default path (used in tests)
 * - Default: $ANICCA_HOME/skills/<slot>/run.sh
 */
function resolveSkillPath(slot, config) {
  const codeRoot = config.ANICCA_CODE_ROOT || process.env.ANICCA_CODE_ROOT;
  if (slot === 'earn' && config.ANICCA_EARN_SKILL && !codeRoot) {
    return config.ANICCA_EARN_SKILL;
  }
  const root = codeRoot || config.ANICCA_HOME || process.cwd();
  return path.join(root, 'skills', slot.replace('/', path.sep), 'run.sh');
}
