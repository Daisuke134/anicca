/**
 * brain.mjs — Effectful: unified THINK step with fallback.
 *
 * REQ-011: Pluggable brain backend:
 *   ANICCA_BRAIN=proxy   → HTTP to OPENAI_BASE_URL (default)
 *   ANICCA_BRAIN=claude-p → spawn `claude -p` subprocess
 *   claude binary missing → fall back to proxy, never crash
 *
 * REQ-004: claude -p child env is scrubbed (no private keys).
 */

import https from 'node:https';
import http from 'node:http';
import os from 'node:os';
import { spawn } from 'node:child_process';
import { buildSystemPrompt, buildUserMessage, getToolDefinitions } from './prompt.mjs';
// spec 25 O1: expose each live skill as a pickable tool (enum on run_skill.slot).
import { scrubPrivateKeys } from './env-filter.mjs';

const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 2000;

/**
 * Execute the THINK step for the current wake.
 *
 * @param {object} ctx - WakeContext
 * @param {object} config - loaded config
 * @returns {Promise<object>} - raw response (OpenAI-compatible)
 * @throws only if both backends fail (caller writes wake_error)
 */
export async function think(ctx, config) {
  const brain = config.ANICCA_BRAIN || 'proxy';

  if (brain === 'claude-p') {
    try {
      return await thinkClaudeP(ctx, config);
    } catch (err) {
      process.stderr.write(`[brain] claude-p failed: ${err.message} — falling back to proxy\n`);
      // Fall through to proxy
    }
  }

  return thinkProxy(ctx, config);
}

// ── Proxy brain (HTTP POST) ──────────────────────────────────────────────────

async function thinkProxy(ctx, config) {
  const baseUrl = config.OPENAI_BASE_URL || 'http://127.0.0.1:8402/v1';
  const url = baseUrl.replace(/\/+$/, '') + '/chat/completions';

  // Policy 2026-06-21 (Dais): use the survival-tier model (ctx.model from tier.mjs). For LEAN
  // and FUNDED tiers that resolves to ClawRouter `auto` — paid (kimi-k2.7 ~$0.004/call typical)
  // is OK because net-positive (earn − burn) is the real goal, not zero compute. BROKE tier
  // (balance=0) stays on `free/gpt-oss-120b` as a safety floor since an empty wallet can't pay.
  // Operator override via ANICCA_MODEL.
  const body = JSON.stringify({
    model: config.ANICCA_MODEL || ctx.model || 'auto',
    messages: [
      { role: 'system', content: buildSystemPrompt(ctx) },
      { role: 'user',   content: buildUserMessage(ctx) },
    ],
    tools: getToolDefinitions(ctx.activeSkillSlots),
    tool_choice: 'auto',
    max_tokens: 512,
  });

  let lastErr;
  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    if (attempt > 0) await delay(RETRY_DELAY_MS);
    try {
      const raw = await httpPost(url, body);
      return JSON.parse(raw);
    } catch (err) {
      lastErr = err;
    }
  }
  throw new Error(`proxy_down: ${lastErr?.message || 'unknown'}`);
}

// ── Claude -p brain (subprocess) ────────────────────────────────────────────

async function thinkClaudeP(ctx, config) {
  const claudeBin = config.CLAUDE_BIN || process.env.CLAUDE_BIN || 'claude';
  const model = config.ANICCA_BRAIN_MODEL || 'claude-sonnet-4-6';

  const prompt = [
    buildSystemPrompt(ctx),
    '',
    buildUserMessage(ctx),
    '',
    'Respond with a JSON tool_calls block using run_skill or sleep.',
  ].join('\n');

  // MINIMAL env (not the full process.env): a full env + the project cwd makes `claude -p` load this
  // repo's .claude hooks/MCP/CLAUDE.md and HANG >2min (verified 2026-07-04: child at 0% CPU). The proven
  // 4-second recipe = minimal env (HOME+PATH) + a neutral cwd (/tmp), so claude only reads ~/.claude auth.
  // Private keys are excluded by construction here (we allow-list, not scrub). REQ-004 preserved.
  const scrubbed = scrubPrivateKeys(process.env);
  const childEnv = {
    HOME: process.env.HOME,
    PATH: process.env.PATH,
    ...(scrubbed.ANTHROPIC_API_KEY ? { ANTHROPIC_API_KEY: scrubbed.ANTHROPIC_API_KEY } : {}),
    ...(scrubbed.CLAUDE_CODE_OAUTH_TOKEN ? { CLAUDE_CODE_OAUTH_TOKEN: scrubbed.CLAUDE_CODE_OAUTH_TOKEN } : {}),
  };

  return new Promise((resolve, reject) => {
    let stdout = '';
    let stderr = '';

    const proc = spawn(claudeBin, [
      '-p', prompt,
      '--output-format', 'json',
      '--model', model,
    ], {
      env: childEnv,
      cwd: os.tmpdir(),   // neutral cwd → no project .claude/hooks loaded → no 2-min hang
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    proc.stdout.on('data', d => { stdout += d; });
    proc.stderr.on('data', d => { stderr += d; });

    proc.on('error', (err) => {
      reject(new Error(`claude_not_found: ${err.message}`));
    });

    proc.on('exit', (code) => {
      if (code !== 0) {
        reject(new Error(`claude_exit_${code}: ${stderr.slice(0, 200)}`));
        return;
      }
      if (!stdout.trim()) {
        reject(new Error(`claude_empty_output`));
        return;
      }
      try {
        resolve(JSON.parse(stdout));
      } catch {
        reject(new Error(`claude_invalid_json: ${stdout.slice(0, 200)}`));
      }
    });
  });
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function httpPost(url, body) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const lib = parsed.protocol === 'https:' ? https : http;
    const options = {
      hostname: parsed.hostname,
      port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
      path: parsed.pathname + parsed.search,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
        'Authorization': `Bearer ${process.env.OPENAI_API_KEY || 'x402-local'}`,
      },
      timeout: 30000,
    };
    const req = lib.request(options, (res) => {
      let data = '';
      res.on('data', c => { data += c; });
      res.on('end', () => {
        // #F1 (2026-07-06): a non-2xx here is a real upstream failure (observed live:
        // sol.blockrun.ai's free-model NVIDIA passthrough intermittently 403/429s —
        // transient: retrying the identical request succeeds within a few attempts).
        // Resolving unconditionally let that error BODY get JSON.parse'd and returned
        // as if it were a real completion, so the retry loop above never fired and
        // every failure silently surfaced as a harmless "narrate" wake instead of
        // wake_error (confirmed live 2026-07-07: a real 429 body parses as valid JSON
        // with no `choices` array, so parseToolCall sees null and index.mjs treats it
        // as text-only). Reject instead so the existing attempt/back-off loop actually
        // retries transient gateway errors.
        if (res.statusCode < 200 || res.statusCode >= 300) {
          reject(new Error(`HTTP ${res.statusCode}: ${data.slice(0, 300)}`));
          return;
        }
        resolve(data);
      });
    });
    req.on('timeout', () => { req.destroy(); reject(new Error('HTTP timeout')); });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

function delay(ms) {
  return new Promise(r => setTimeout(r, ms));
}
