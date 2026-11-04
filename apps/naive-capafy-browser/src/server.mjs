import { timingSafeEqual } from 'node:crypto';
import { createClient } from '@usenaive-sdk/vetta';

const PROTOCOL_VERSION = '2025-06-18';
const MAX_REQUEST_BYTES = 65536;
const MAX_TEXT = 20000;
const COMPUTER_ID_RE = /^cmp_[a-z0-9]+$/;
const IDENTITY_ID_RE = /^idn_[a-z0-9]+$/;
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const TOOL_NAME = 'capafy_browser';

const inputSchema = {
  type: 'object',
  properties: {
    operation_id: { type: 'string', format: 'uuid', description: 'A new UUID for this exact browser operation; reuse it only to retry the same action.' },
    action: { type: 'string', enum: ['goto', 'click', 'type', 'extract', 'act', 'observe', 'links', 'screenshot', 'login', 'signup'] },
    url: { type: 'string', description: 'HTTPS Capafy URL; accepted only for goto.' },
    selector: { type: 'string', description: 'Page selector; accepted only for click, type or extract.' },
    text: { type: 'string', description: 'Non-secret text; accepted only for type.' },
    instruction: { type: 'string', description: 'A bounded page observation/action instruction.' },
    contains: { type: 'string', description: 'Optional link-text filter.' },
    limit: { type: 'integer', minimum: 1, maximum: 50 },
  },
  required: ['operation_id', 'action'],
  additionalProperties: false,
};

const tools = [{
  name: TOOL_NAME,
  title: 'Use the Capafy browser',
  description: 'Observe and operate the assigned Capafy browser. The browser is fixed to one Computer and Capafy domains. Use a new operation_id for each distinct action. Login and signup use only this agent’s server-configured Naive Identity and email.',
  inputSchema,
}];

const actionKeys = {
  goto: ['url'],
  click: ['selector'],
  type: ['selector', 'text'],
  extract: ['selector', 'instruction'],
  act: ['instruction'],
  observe: ['instruction'],
  links: ['contains', 'limit'],
  screenshot: [],
  login: [],
  signup: [],
};

function allowedUrl(value) {
  if (typeof value !== 'string' || value.length > 2048) return false;
  try {
    const url = new URL(value);
    return url.protocol === 'https:'
      && !url.username && !url.password
      && !url.port
      && (url.hostname === 'capafy.ai' || url.hostname.endsWith('.capafy.ai'));
  } catch {
    return false;
  }
}

function safeEquals(left, right) {
  if (typeof left !== 'string' || typeof right !== 'string') return false;
  const a = Buffer.from(left);
  const b = Buffer.from(right);
  return a.length === b.length && timingSafeEqual(a, b);
}

function jsonResponse(value, status = 200) {
  return Response.json(value, { status, headers: { 'cache-control': 'no-store' } });
}

function rpcError(id, code, message) {
  return jsonResponse({ jsonrpc: '2.0', id: id ?? null, error: { code, message } });
}

function toolError(code) {
  const content = [{ type: 'text', text: JSON.stringify({ error: code }) }];
  return { content, structuredContent: { error: code }, isError: true };
}

function boundedValue(value, limit = MAX_TEXT, depth = 0) {
  if (value === null || value === undefined || typeof value === 'boolean' || typeof value === 'number') return value ?? null;
  if (typeof value === 'string') return value.length > limit ? value.slice(0, limit) + '…[truncated]' : value;
  if (depth >= 6) return '[depth limit]';
  if (Array.isArray(value)) return value.slice(0, 100).map((item) => boundedValue(item, limit, depth + 1));
  if (typeof value !== 'object') return null;
  const out = {};
  for (const [key, item] of Object.entries(value).slice(0, 100)) {
    if (/password|secret|token|cookie|authorization|api[_-]?key/i.test(key)) continue;
    out[key] = boundedValue(item, limit, depth + 1);
  }
  return out;
}

function safeCapafyLink(href) {
  try {
    return allowedUrl(new URL(href, 'https://capafy.ai').href);
  } catch {
    return false;
  }
}

function safeBrowserResult(result) {
  const links = Array.isArray(result?.links)
    ? result.links.filter((link) => safeCapafyLink(link.href)).slice(0, 50)
    : null;
  return {
    action: result?.action ?? null,
    url: allowedUrl(result?.url) ? result.url : null,
    text: typeof result?.text === 'string' ? boundedValue(result.text) : null,
    data: boundedValue(result?.data ?? null),
    links,
    elements: Array.isArray(result?.elements) ? boundedValue(result.elements.slice(0, 100)) : null,
    file_id: typeof result?.file_id === 'string' ? result.file_id : null,
    performed: result?.performed === true,
  };
}

function validateOperation(args) {
  if (!args || typeof args !== 'object' || Array.isArray(args)) return 'invalid_arguments';
  if (typeof args.operation_id !== 'string' || !UUID_RE.test(args.operation_id)) return 'invalid_operation_id';
  if (!Object.hasOwn(actionKeys, args.action)) return 'unsupported_action';
  const allowed = new Set(['operation_id', 'action', ...actionKeys[args.action]]);
  if (Object.keys(args).some((key) => !allowed.has(key))) return 'unexpected_argument';

  const shortString = (value, max = 1000) => typeof value === 'string' && value.length > 0 && value.length <= max;
  if (args.action === 'goto' && !allowedUrl(args.url)) return 'capafy_url_required';
  if (['click', 'type'].includes(args.action) && !shortString(args.selector, 512)) return 'selector_required';
  if (args.action === 'type' && !shortString(args.text)) return 'text_required';
  if (['act', 'observe'].includes(args.action) && !shortString(args.instruction)) return 'instruction_required';
  if (args.action === 'extract' && args.selector !== undefined && !shortString(args.selector, 512)) return 'invalid_selector';
  if (args.action === 'extract' && args.instruction !== undefined && !shortString(args.instruction)) return 'invalid_instruction';
  if (args.action === 'links' && args.contains !== undefined && !shortString(args.contains, 300)) return 'invalid_contains';
  if (args.action === 'links' && args.limit !== undefined && (!Number.isInteger(args.limit) || args.limit < 1 || args.limit > 50)) return 'invalid_limit';
  return null;
}

function clientFor(env, fetchImpl, operationId) {
  if (!env.NAIVE_API_KEY || !env.NAIVE_API_URL || !COMPUTER_ID_RE.test(env.NAIVE_COMPUTER_ID ?? '')) {
    throw Object.assign(new Error('app configuration unavailable'), { code: 'app_not_configured' });
  }
  const baseUrl = new URL(env.NAIVE_API_URL);
  if (baseUrl.origin !== 'https://api.vetta.sh' || baseUrl.pathname !== '/' || baseUrl.search || baseUrl.hash) {
    throw Object.assign(new Error('app API origin is invalid'), { code: 'invalid_app_api_origin' });
  }
  return createClient({
    baseUrl: baseUrl.origin,
    apiKey: env.NAIVE_API_KEY,
    fetch: fetchImpl,
    idempotencyKey: () => operationId,
  }).computers.browser(env.NAIVE_COMPUTER_ID);
}

async function runBrowser(args, env, fetchImpl) {
  const browser = clientFor(env, fetchImpl, args.operation_id);
  switch (args.action) {
    case 'goto': return browser.goto(args.url);
    case 'click': return browser.click(args.selector);
    case 'type': return browser.type(args.selector, args.text);
    case 'extract': return browser.extract({
      ...(args.selector === undefined ? {} : { selector: args.selector }),
      ...(args.instruction === undefined ? {} : { instruction: args.instruction }),
    });
    case 'act': return browser.act(args.instruction);
    case 'observe': return browser.observe(args.instruction);
    case 'links': return browser.links({
      ...(args.contains === undefined ? {} : { contains: args.contains }),
      ...(args.limit === undefined ? {} : { limit: args.limit }),
    });
    case 'screenshot': return browser.screenshot();
    case 'login': {
      if (!IDENTITY_ID_RE.test(env.NAIVE_IDENTITY_ID ?? '') || !allowedUrl(env.CAPAFY_LOGIN_URL)) {
        throw Object.assign(new Error('agent login is not configured'), { code: 'agent_login_not_configured' });
      }
      return browser.login({ service: 'capafy.ai', url: env.CAPAFY_LOGIN_URL, identity_id: env.NAIVE_IDENTITY_ID });
    }
    case 'signup': {
      if (!IDENTITY_ID_RE.test(env.NAIVE_IDENTITY_ID ?? '')
        || !allowedUrl(env.CAPAFY_SIGNUP_URL)
        || typeof env.CAPAFY_AGENT_EMAIL !== 'string'
        || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(env.CAPAFY_AGENT_EMAIL)) {
        throw Object.assign(new Error('agent signup is not configured'), { code: 'agent_signup_not_configured' });
      }
      return browser.signup({
        service: 'capafy.ai',
        url: env.CAPAFY_SIGNUP_URL,
        identity_id: env.NAIVE_IDENTITY_ID,
        email: env.CAPAFY_AGENT_EMAIL,
      });
    }
    default:
      throw Object.assign(new Error('unsupported action'), { code: 'unsupported_action' });
  }
}

function apiErrorCode(error) {
  return typeof error?.code === 'string' && /^[a-z0-9_]{1,64}$/.test(error.code)
    ? error.code
    : 'browser_action_failed';
}

async function callTool(args, env, fetchImpl) {
  const invalid = validateOperation(args);
  if (invalid) return toolError(invalid);
  try {
    const result = await runBrowser(args, env, fetchImpl);
    const safe = safeBrowserResult(result);
    return { content: [{ type: 'text', text: JSON.stringify(safe) }], structuredContent: safe, isError: false };
  } catch (error) {
    return toolError(apiErrorCode(error));
  }
}

export function createBrowserMcpHandler({ env = process.env, fetchImpl = globalThis.fetch } = {}) {
  return async function handle(request) {
    const url = new URL(request.url);
    if (url.pathname === '/healthz' && request.method === 'GET') {
      return jsonResponse({ ok: true, app: 'naive-capafy-browser' });
    }
    if (url.pathname !== '/mcp') return new Response('Not found', { status: 404 });
    if (request.method !== 'POST') return new Response('Method not allowed', { status: 405, headers: { allow: 'POST' } });
    if (!env.VETTA_MCP_TOKEN) return new Response('App MCP is not configured', { status: 503 });
    if (!safeEquals(request.headers.get('authorization'), 'Bearer ' + env.VETTA_MCP_TOKEN)) {
      return new Response('Unauthorized', { status: 401, headers: { 'cache-control': 'no-store' } });
    }
    const length = Number(request.headers.get('content-length') ?? 0);
    if (length > MAX_REQUEST_BYTES) return new Response('Payload too large', { status: 413 });

    const raw = await request.text();
    if (new TextEncoder().encode(raw).byteLength > MAX_REQUEST_BYTES) return new Response('Payload too large', { status: 413 });
    let message;
    try {
      message = JSON.parse(raw);
    } catch {
      return jsonResponse({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error' } }, 400);
    }
    if (!message || Array.isArray(message) || typeof message !== 'object' || message.jsonrpc !== '2.0') {
      return rpcError(message?.id, -32600, 'Invalid Request');
    }
    const id = message.id;
    if (typeof message.method !== 'string') return rpcError(id, -32600, 'Invalid Request');
    if (message.method.startsWith('notifications/')) return new Response(null, { status: 202 });
    if (id === undefined) return new Response(null, { status: 202 });

    if (message.method === 'initialize') {
      return jsonResponse({
        jsonrpc: '2.0', id,
        result: {
          protocolVersion: message.params?.protocolVersion ?? PROTOCOL_VERSION,
          capabilities: { tools: {} },
          serverInfo: { name: 'naive-capafy-browser', version: '0.1.0' },
          instructions: 'Use this tool only for the assigned Capafy browser. Use a unique operation_id for every distinct action.',
        },
      });
    }
    if (message.method === 'ping') return jsonResponse({ jsonrpc: '2.0', id, result: {} });
    if (message.method === 'tools/list') return jsonResponse({ jsonrpc: '2.0', id, result: { tools } });
    if (message.method === 'tools/call') {
      if (message.params?.name !== TOOL_NAME) return rpcError(id, -32602, 'Unknown tool');
      const result = await callTool(message.params.arguments, env, fetchImpl);
      return jsonResponse({ jsonrpc: '2.0', id, result });
    }
    return rpcError(id, -32601, 'Method not found');
  };
}
