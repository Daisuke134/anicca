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
import { spawn } from 'node:child_process';
import { buildSystemPrompt, buildUserMessage, getToolDefinitions } from './prompt.mjs';
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

  const body = JSON.stringify({
    model: ctx.model,
    messages: [
      { role: 'system', content: buildSystemPrompt(ctx) },
      { role: 'user',   content: buildUserMessage(ctx) },
    ],
    tools: getToolDefinitions(),
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

  // Scrub private keys from child env (REQ-004 / PROP-023c)
  const childEnv = scrubPrivateKeys(process.env);

  return new Promise((resolve, reject) => {
    let stdout = '';
    let stderr = '';

    const proc = spawn(claudeBin, [
      '-p', prompt,
      '--output-format', 'json',
      '--model', model,
    ], {
      env: childEnv,
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
      res.on('end', () => resolve(data));
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
