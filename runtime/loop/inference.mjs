/**
 * inference.mjs — Effectful: HTTP POST to OPENAI_BASE_URL/v1/chat/completions
 *
 * REQ-001: Retry up to 3 times with 2s back-off on proxy failure.
 * REQ-011: ANICCA_BRAIN=proxy → HTTP; ANICCA_BRAIN=claude-p → subprocess.
 */

import https from 'node:https';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { buildSystemPrompt, buildUserMessage, getToolDefinitions } from './prompt.mjs';

const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 2000;

/**
 * Perform the THINK step: call the brain backend and return the raw response object.
 *
 * @param {object} ctx - WakeContext
 * @param {object} config - loaded config (OPENAI_BASE_URL, model, ANICCA_BRAIN, etc.)
 * @returns {Promise<object>} - raw response from brain (OpenAI-compatible or claude-p output)
 * @throws {Error} if all retries fail (caller writes wake_error ledger line)
 */
export async function think(ctx, config) {
  const brain = config.ANICCA_BRAIN || 'proxy';

  if (brain === 'claude-p') {
    return thinkClaudeP(ctx, config);
  }

  return thinkProxy(ctx, config);
}

// ── Proxy brain ──────────────────────────────────────────────────────────────

async function thinkProxy(ctx, config) {
  const baseUrl = config.OPENAI_BASE_URL || 'http://127.0.0.1:8402/v1';
  const url = baseUrl.replace(/\/+$/, '') + '/chat/completions';

  const systemPrompt = buildSystemPrompt(ctx);
  const userMessage = buildUserMessage(ctx);

  const body = JSON.stringify({
    model: ctx.model,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userMessage },
    ],
    tools: getToolDefinitions(),
    tool_choice: 'auto',
    max_tokens: 512,
  });

  let lastErr;
  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    if (attempt > 0) await sleep(RETRY_DELAY_MS);
    try {
      const raw = await httpPost(url, body);
      return JSON.parse(raw);
    } catch (err) {
      lastErr = err;
    }
  }
  throw new Error(`proxy_down: ${lastErr?.message || 'unknown'}`);
}

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

// ── claude -p brain ──────────────────────────────────────────────────────────

async function thinkClaudeP(ctx, config) {
  const claudeBin = config.CLAUDE_BIN || process.env.CLAUDE_BIN || 'claude';
  const model = config.ANICCA_BRAIN_MODEL || 'claude-sonnet-4-6';

  const systemPrompt = buildSystemPrompt(ctx);
  const userMessage = buildUserMessage(ctx);
  const fullPrompt = `${systemPrompt}\n\n${userMessage}\n\nRespond with a tool_calls JSON block.`;

  return new Promise((resolve, reject) => {
    let stdout = '';
    let stderr = '';

    // Build a scrubbed env (PROP-023: no private key in claude -p subprocess).
    // buildClaudeEnv scrubs synchronously — no await here (this is a non-async Promise executor).
    const childEnv = buildClaudeEnv(config);

    const proc = spawn(claudeBin, [
      '-p', fullPrompt,
      '--output-format', 'json',
      '--model', model,
    ], {
      env: childEnv,
      stdio: ['ignore', 'pipe', 'pipe'],
      timeout: 90000, // claude -p cold-start + ~5k-char prompt can exceed 30s
    });

    proc.stdout.on('data', d => { stdout += d; });
    proc.stderr.on('data', d => { stderr += d; });
    proc.on('error', (err) => {
      // Binary not found → reject so caller falls back to proxy
      reject(new Error(`claude_not_found: ${err.message}`));
    });
    proc.on('exit', (code) => {
      if (code !== 0 || !stdout.trim()) {
        reject(new Error(`claude_exit_${code}: ${stderr.slice(0, 200)}`));
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

/**
 * Build child env for claude -p: scrub private keys per REQ-004.
 */
function buildClaudeEnv(config) {
  // Inline scrub (synchronous) — we can't top-level await in the Promise callback
  const env = { ...process.env };
  const PRIVATE_KEY_REGEX = /(_WALLET_KEY|_PRIVATE_KEY|_PRIV_KEY)$/;
  const childEnv = {};
  for (const [k, v] of Object.entries(env)) {
    if (!PRIVATE_KEY_REGEX.test(k)) childEnv[k] = v;
  }
  return childEnv;
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}
