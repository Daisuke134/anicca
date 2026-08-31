"use strict";

const net = require("node:net");
const dns = require("node:dns").promises;
const { Agent: UndiciAgent, fetch: undiciFetch } = require("undici");

const MCP_REGISTRY = "https://registry.modelcontextprotocol.io/v0.1/servers";
const HUGGING_FACE_SPACES = "https://huggingface.co/api/spaces";
const PRODUCT_HUNT_GRAPHQL = "https://api.producthunt.com/v2/api/graphql";
const MAX_TOOLS = 12;
const DISCOVERY_TTL_MS = 60_000;
const discoveryCache = new Map();
const nonPublicIps = new net.BlockList();

for (const [network, prefix, family] of [
  ["0.0.0.0", 8, "ipv4"], ["10.0.0.0", 8, "ipv4"], ["100.64.0.0", 10, "ipv4"],
  ["127.0.0.0", 8, "ipv4"], ["169.254.0.0", 16, "ipv4"], ["172.16.0.0", 12, "ipv4"],
  ["192.0.0.0", 24, "ipv4"], ["192.0.2.0", 24, "ipv4"], ["192.31.196.0", 24, "ipv4"],
  ["192.52.193.0", 24, "ipv4"], ["192.88.99.0", 24, "ipv4"], ["192.168.0.0", 16, "ipv4"],
  ["192.175.48.0", 24, "ipv4"], ["198.18.0.0", 15, "ipv4"], ["198.51.100.0", 24, "ipv4"],
  ["203.0.113.0", 24, "ipv4"], ["224.0.0.0", 4, "ipv4"], ["240.0.0.0", 4, "ipv4"],
  ["::", 128, "ipv6"], ["::1", 128, "ipv6"], ["64:ff9b::", 96, "ipv6"],
  ["64:ff9b:1::", 48, "ipv6"], ["100::", 64, "ipv6"], ["2001::", 23, "ipv6"],
  ["2001:db8::", 32, "ipv6"], ["2002::", 16, "ipv6"], ["3fff::", 20, "ipv6"],
  ["5f00::", 16, "ipv6"], ["fc00::", 7, "ipv6"], ["fe80::", 10, "ipv6"], ["ff00::", 8, "ipv6"],
]) nonPublicIps.addSubnet(network, prefix, family);

function hubError(message, status = 400) {
  return Object.assign(new Error(message), { status });
}

function cleanText(value, max = 300) {
  return String(value == null ? "" : value).replace(/[\u0000-\u001f\u007f]/g, " ").replace(/\s+/g, " ").trim().slice(0, max);
}

function cleanQuery(value) {
  const query = cleanText(value || "automation", 80);
  return query || "automation";
}

function isPrivateIp(hostname) {
  const address = String(hostname || "").replace(/^\[|\]$/g, "");
  const version = net.isIP(address);
  return Boolean(version) && (version === 6 && address.toLowerCase().startsWith("::ffff:")
    || nonPublicIps.check(address, version === 4 ? "ipv4" : "ipv6"));
}

function isPublicHttpsUrl(value) {
  try {
    const url = new URL(String(value || ""));
    const hostname = url.hostname.toLowerCase();
    const domain = hostname.replace(/^\[|\]$/g, "").replace(/\.+$/, "");
    return url.protocol === "https:" && !url.username && !url.password && Boolean(hostname)
      && domain !== "localhost" && !domain.endsWith(".localhost") && !domain.endsWith(".local")
      && !isPrivateIp(hostname);
  } catch {
    return false;
  }
}

function source(id, label, status, detail) {
  return { id, label, status, detail };
}

async function fetchJson(fetchImpl, url, init = {}) {
  const response = await fetchImpl(url, { ...init, redirect: "manual", signal: init.signal || AbortSignal.timeout(5000) });
  if (!response.ok) throw new Error(`provider_${response.status}`);
  return response.json();
}

function registryOfficial(item) {
  return item && item._meta && item._meta["io.modelcontextprotocol.registry/official"] || {};
}

function registrySecrets(remote) {
  const headers = remote && remote.headers;
  if (Array.isArray(headers)) return headers.filter((header) => header && header.isSecret).map((header) => cleanText(header.name, 80)).filter(Boolean);
  if (!headers || typeof headers !== "object") return [];
  return Object.entries(headers).filter(([, value]) => value && typeof value === "object" && value.isSecret).map(([name]) => cleanText(name, 80)).filter(Boolean);
}

function normalizeRegistryItem(item) {
  const server = item && item.server;
  const official = registryOfficial(item);
  if (!server || official.status !== "active" || official.isLatest === false) return null;
  const name = cleanText(server.name, 180), version = cleanText(server.version, 80);
  if (!name || !version) return null;
  const remote = (Array.isArray(server.remotes) ? server.remotes : []).find((candidate) => candidate && ["streamable-http", "sse"].includes(candidate.type) && isPublicHttpsUrl(candidate.url));
  const sourceUrl = [server.websiteUrl, server.repository && server.repository.url, remote && remote.url].find(isPublicHttpsUrl) || "https://registry.modelcontextprotocol.io";
  return {
    catalog_id: `mcp-registry:${name}@${version}`,
    source: "mcp-registry",
    name: cleanText(server.title || name, 120),
    description: cleanText(server.description, 360),
    connection_kind: remote ? "remote_mcp" : "package_mcp",
    endpoint: remote ? remote.url : null,
    source_url: sourceUrl,
    version,
    required_secrets: remote ? registrySecrets(remote) : [],
    selectable: Boolean(remote),
  };
}

function normalizeHuggingFaceSpace(space) {
  const tags = Array.isArray(space && space.tags) ? space.tags : [];
  const id = cleanText(space && space.id, 180);
  if (!id || space.private === true || space.sdk !== "gradio" || !tags.includes("mcp-server")) return null;
  return {
    catalog_id: `hugging-face:${id}`,
    source: "hugging-face",
    name: cleanText(space.cardData && space.cardData.title || space.title || id, 120),
    description: cleanText(space.cardData && space.cardData.short_description || space.ai_short_description, 360),
    connection_kind: "hugging_face_mcp",
    endpoint: "https://huggingface.co/mcp",
    source_url: `https://huggingface.co/spaces/${id}`,
    version: cleanText(space.sha, 80) || null,
    required_secrets: ["HF_TOKEN"],
    selectable: true,
  };
}

function normalizeProductHuntPost(node) {
  const id = cleanText(node && node.id, 100);
  const sourceUrl = [node && node.url, node && node.website].find(isPublicHttpsUrl);
  if (!id || !sourceUrl) return null;
  return {
    catalog_id: `product-hunt:${id}`,
    source: "product-hunt",
    name: cleanText(node.name, 120),
    description: cleanText(node.tagline, 360),
    connection_kind: "discovery_only",
    endpoint: null,
    source_url: sourceUrl,
    version: null,
    required_secrets: [],
    selectable: false,
  };
}

async function discoverRegistry(query, opts) {
  const url = new URL(MCP_REGISTRY);
  url.searchParams.set("limit", "12");
  url.searchParams.set("version", "latest");
  url.searchParams.set("search", query);
  const body = await fetchJson(opts.fetchImpl, url);
  return (Array.isArray(body.servers) ? body.servers : []).map(normalizeRegistryItem).filter(Boolean);
}

async function discoverHuggingFace(query, opts) {
  const url = new URL(HUGGING_FACE_SPACES);
  url.searchParams.set("filter", "mcp-server");
  url.searchParams.set("limit", "50");
  url.searchParams.set("full", "true");
  const body = await fetchJson(opts.fetchImpl, url, opts.huggingFaceToken ? { headers: { Authorization: `Bearer ${opts.huggingFaceToken}` } } : {});
  const normalizedQuery = query.toLowerCase();
  return (Array.isArray(body) ? body : []).map(normalizeHuggingFaceSpace).filter(Boolean).filter((item) => !normalizedQuery || `${item.name} ${item.description} ${item.catalog_id}`.toLowerCase().includes(normalizedQuery)).slice(0, 12);
}

async function discoverProductHunt(query, opts) {
  const graphQuery = `query AutomationProducts { posts(first: 20) { edges { node { id name tagline url } } } }`;
  const body = await fetchJson(opts.fetchImpl, PRODUCT_HUNT_GRAPHQL, {
    method: "POST",
    headers: { Authorization: `Bearer ${opts.productHuntToken}`, "content-type": "application/json" },
    body: JSON.stringify({ query: graphQuery }),
  });
  if (Array.isArray(body.errors)) throw new Error("provider_graphql");
  const edges = body && body.data && body.data.posts && body.data.posts.edges;
  const normalizedQuery = query.toLowerCase();
  return (Array.isArray(edges) ? edges : []).map((edge) => normalizeProductHuntPost(edge && edge.node)).filter(Boolean)
    .filter((item) => !normalizedQuery || `${item.name} ${item.description}`.toLowerCase().includes(normalizedQuery)).slice(0, 12);
}

async function settledSource(id, label, operation) {
  try {
    return { source: source(id, label, "ready", "候補を取得済み"), items: await operation() };
  } catch {
    return { source: source(id, label, "unavailable", "現在取得できません"), items: [] };
  }
}

async function discoverAutomationCatalog(options = {}) {
  const fetchImpl = options.fetchImpl || fetch;
  const query = cleanQuery(options.query);
  const cache = options.cache === false ? null : options.cache || discoveryCache;
  const cacheKey = `${query.toLowerCase()}:${Boolean(options.productHuntToken)}:${Boolean(options.huggingFaceToken)}`;
  const nowMs = options.nowMs == null ? Date.now() : options.nowMs;
  const cached = cache && cache.get(cacheKey);
  if (cached && cached.expiresAt > nowMs) return structuredClone(cached.value);
  const providerOptions = { ...options, fetchImpl };
  const productOperation = options.productHuntToken
    ? settledSource("product-hunt", "Product Hunt", () => discoverProductHunt(query, providerOptions))
    : Promise.resolve({ source: source("product-hunt", "Product Hunt", "setup_required", "PRODUCT_HUNT_TOKEN が必要です"), items: [] });
  const results = await Promise.all([
    settledSource("mcp-registry", "Official MCP Registry", () => discoverRegistry(query, providerOptions)),
    settledSource("hugging-face", "Hugging Face MCP Spaces", () => discoverHuggingFace(query, providerOptions)),
    productOperation,
  ]);
  const value = { query, sources: results.map((result) => result.source), items: results.flatMap((result) => result.items) };
  if (cache) cache.set(cacheKey, { expiresAt: nowMs + DISCOVERY_TTL_MS, value });
  return structuredClone(value);
}

function parseRegistryId(catalogId) {
  const match = /^mcp-registry:([^@]{1,180})@([^@]{1,80})$/.exec(catalogId);
  return match ? { name: match[1], version: match[2] } : null;
}

async function resolveRegistry(catalogId, opts) {
  const ref = parseRegistryId(catalogId);
  if (!ref) throw hubError("invalid_catalog_id");
  const url = new URL(MCP_REGISTRY);
  url.searchParams.set("limit", "10");
  url.searchParams.set("search", ref.name);
  url.searchParams.set("version", ref.version);
  const body = await fetchJson(opts.fetchImpl, url);
  const match = (Array.isArray(body.servers) ? body.servers : []).map(normalizeRegistryItem).find((item) => item && item.catalog_id === catalogId);
  if (!match || !match.selectable) throw hubError("tool_not_selectable", 409);
  return match;
}

async function resolveHuggingFace(catalogId, opts) {
  const id = catalogId.slice("hugging-face:".length);
  if (!/^[A-Za-z0-9._-]{1,100}\/[A-Za-z0-9._-]{1,100}$/.test(id)) throw hubError("invalid_catalog_id");
  const url = `https://huggingface.co/api/spaces/${id.split("/").map(encodeURIComponent).join("/")}`;
  const item = normalizeHuggingFaceSpace(await fetchJson(opts.fetchImpl, url, opts.huggingFaceToken ? { headers: { Authorization: `Bearer ${opts.huggingFaceToken}` } } : {}));
  if (!item || item.catalog_id !== catalogId) throw hubError("tool_not_selectable", 409);
  return item;
}

async function resolveAutomationTools(catalogIds, options = {}) {
  const fetchImpl = options.fetchImpl || fetch;
  if (!Array.isArray(catalogIds) || catalogIds.length < 1 || catalogIds.length > MAX_TOOLS || new Set(catalogIds).size !== catalogIds.length) throw hubError("invalid_automation_mutation");
  const tools = await Promise.all(catalogIds.map((raw) => {
    const id = cleanText(raw, 280);
    if (id.startsWith("mcp-registry:")) return resolveRegistry(id, { ...options, fetchImpl });
    if (id.startsWith("hugging-face:")) return resolveHuggingFace(id, { ...options, fetchImpl });
    throw hubError("tool_not_selectable", 409);
  }));
  await Promise.all(tools.map(async (tool) => {
    if (!tool || !isPublicHttpsUrl(tool.endpoint)) throw hubError("unsafe_mcp_endpoint", 409);
    await assertPublicDns(new URL(tool.endpoint), options);
  }));
  return tools;
}

async function tenantHeaders(scope, tool, options) {
  const names = Array.isArray(tool.required_secrets) ? tool.required_secrets : [];
  if (!names.length) return {};
  if (typeof options.secretResolver !== "function") throw hubError("automation_configuration_required", 409);
  const values = await options.secretResolver(scope, { catalog_id: tool.catalog_id, names: [...names] });
  if (!values || typeof values !== "object" || names.some((name) => typeof values[name] !== "string" || !values[name])) throw hubError("automation_configuration_required", 409);
  if (tool.source === "hugging-face") return { Authorization: `Bearer ${values.HF_TOKEN}` };
  return Object.fromEntries(names.map((name) => [name, values[name]]));
}

async function assertPublicDns(endpoint, options) {
  const lookup = options.lookup || ((hostname) => dns.lookup(hostname, { all: true, verbatim: true }));
  const hostname = endpoint.hostname.replace(/^\[|\]$/g, "");
  let records;
  try { records = await lookup(hostname); }
  catch { throw hubError("mcp_dns_failed", 409); }
  const list = Array.isArray(records) ? records : [records];
  if (!list.length || list.some((record) => !record || !net.isIP(record.address) || isPrivateIp(record.address))) throw hubError("unsafe_mcp_endpoint", 409);
  return list.map((record) => ({ address: record.address, family: net.isIP(record.address) }));
}

function pinnedDispatcher(hostname, records) {
  let offset = 0;
  return new UndiciAgent({
    connect: {
      lookup(requestedHostname, lookupOptions, callback) {
        const expected = String(hostname).toLowerCase().replace(/\.+$/, "");
        const requested = String(requestedHostname).toLowerCase().replace(/\.+$/, "");
        if (requested !== expected) {
          callback(new Error("unsafe_mcp_endpoint"));
          return;
        }
        const family = Number(lookupOptions && lookupOptions.family) || 0;
        const candidates = records.filter((record) => !family || record.family === family);
        if (!candidates.length) {
          callback(Object.assign(new Error("ENOTFOUND"), { code: "ENOTFOUND" }));
          return;
        }
        if (lookupOptions && lookupOptions.all) {
          callback(null, candidates);
          return;
        }
        const record = candidates[offset++ % candidates.length];
        callback(null, record.address, record.family);
      },
    },
  });
}

async function verifyAutomationTool(scope, tool, options) {
  if (!tool || !isPublicHttpsUrl(tool.endpoint)) throw hubError("unsafe_mcp_endpoint", 409);
  const endpoint = new URL(tool.endpoint);
  const records = await assertPublicDns(endpoint, options);
  const requestHeaders = await tenantHeaders(scope, tool, options);
  const dispatcher = typeof options.dispatcherFactory === "function"
    ? options.dispatcherFactory(endpoint.hostname.replace(/^\[|\]$/g, ""), records)
    : pinnedDispatcher(endpoint.hostname.replace(/^\[|\]$/g, ""), records);
  const fetchImpl = options.fetchImpl || undiciFetch;
  const guardedFetch = async (input, init = {}) => {
    const target = new URL(typeof input === "string" || input instanceof URL ? input : input.url);
    if (target.origin !== endpoint.origin || target.pathname !== endpoint.pathname || target.search !== endpoint.search) throw hubError("unsafe_mcp_endpoint", 409);
    const timeout = AbortSignal.timeout(options.timeoutMs || 5000);
    const signal = init.signal ? AbortSignal.any([init.signal, timeout]) : timeout;
    const response = await fetchImpl(input, { ...init, redirect: "manual", signal, dispatcher });
    if (response.status === 401 || response.status === 403) throw hubError("mcp_auth_failed", 409);
    if (response.status === 429) throw hubError("mcp_rate_limited", 409);
    if (response.status >= 300 && response.status < 400) throw hubError("unsafe_mcp_endpoint", 409);
    if (response.status >= 500) throw hubError("mcp_connection_failed", 409);
    return response;
  };
  let client;
  try {
    if (options.clientFactory) client = options.clientFactory();
    else {
      const { Client } = require("@modelcontextprotocol/sdk/client/index.js");
      client = new Client({ name: "mr-bot-automation-hub", version: "1.0.0" });
    }
    const transport = options.transportFactory
      ? options.transportFactory(endpoint, { fetch: guardedFetch, requestInit: { headers: requestHeaders } })
      : new (require("@modelcontextprotocol/sdk/client/streamableHttp.js").StreamableHTTPClientTransport)(endpoint, { fetch: guardedFetch, requestInit: { headers: requestHeaders } });
    await client.connect(transport);
    const result = await client.listTools();
    if (!result || !Array.isArray(result.tools)) throw new Error("invalid tools response");
    return { catalog_id: tool.catalog_id, tool_count: result.tools.length };
  } catch (error) {
    if (error && error.status) throw error;
    throw hubError("mcp_connection_failed", 409);
  } finally {
    if (client && typeof client.close === "function") {
      try { await client.close(); } catch { /* connection result already decides the gate */ }
    }
    if (dispatcher && typeof dispatcher.close === "function") {
      try { await dispatcher.close(); } catch { /* the request gate is already closed */ }
    }
  }
}

async function verifyAutomationStack(scope, stack, options = {}) {
  if (!stack || !Array.isArray(stack.tools) || stack.tools.length < 1 || stack.tools.length > MAX_TOOLS) throw hubError("invalid_automation_mutation");
  return Promise.all(stack.tools.map((tool) => verifyAutomationTool(scope, tool, options)));
}

function exactKeys(value, keys) {
  return value && typeof value === "object" && !Array.isArray(value)
    && Object.keys(value).length === keys.length && Object.keys(value).every((key) => keys.includes(key));
}

async function mutateAutomationHub(scope, body, options = {}) {
  const store = options.store;
  if (!store || !scope || !scope.uid || !scope.chatId) throw hubError("automation_unavailable", 503);
  if (body && body.action === "replace") {
    if (!exactKeys(body, ["action", "name", "catalog_ids", "revision"])) throw hubError("invalid_automation_mutation");
    const name = cleanText(body.name, 80);
    if (!name || !Number.isSafeInteger(body.revision) || body.revision < 0) throw hubError("invalid_automation_mutation");
    const resolveTools = options.resolveTools || ((ids) => resolveAutomationTools(ids, options));
    const tools = await resolveTools(body.catalog_ids);
    return store.replaceStack(scope, { name, revision: body.revision, tools });
  }
  if (body && body.action === "toggle") {
    if (!exactKeys(body, ["action", "enabled", "revision"]) || typeof body.enabled !== "boolean" || !Number.isSafeInteger(body.revision) || body.revision < 0) throw hubError("invalid_automation_mutation");
    let verified = false;
    if (body.enabled && typeof options.verifyStack === "function") {
      if (typeof store.readStack !== "function") throw hubError("automation_unavailable", 503);
      const stack = await store.readStack(scope);
      if (!stack || stack.revision !== body.revision) throw hubError("automation_revision_conflict", 409);
      await options.verifyStack(scope, stack, options);
      verified = true;
    }
    return store.toggleStack(scope, { enabled: body.enabled, revision: body.revision, verified });
  }
  throw hubError("invalid_automation_mutation");
}

function emptyStack() {
  return { id: "default", name: "My automation", desired_state: "off", observed_state: "stopped", revision: 0, last_error_code: null, tools: [] };
}

async function buildAutomationHub(scope, options = {}) {
  const store = options.store;
  const discoverCatalog = options.discoverCatalog || discoverAutomationCatalog;
  const [catalog, stack] = await Promise.all([
    discoverCatalog(options),
    store && store.readStack ? store.readStack(scope) : Promise.resolve(null),
  ]);
  return {
    ...catalog,
    stack: stack ? { ...stack, last_error_code: stack.last_error_code || null } : emptyStack(),
    limits: { max_tools: MAX_TOOLS },
    runtime: { mode: "approval_control", detail: "ON の前に MCP initialize と tools/list を確認し、認証情報不足や接続失敗は閉じたままにします。" },
  };
}

function supabaseHeaders(key) {
  return { apikey: key, Authorization: `Bearer ${key}` };
}

function createSupabaseAutomationStore(options = {}) {
  const base = String(options.supaUrl || "").replace(/\/$/, "");
  const fetchImpl = options.fetchImpl || fetch;
  async function request(url, init = {}) {
    let response;
    try {
      response = await fetchImpl(`${base}/rest/v1/${url}`, {
        ...init,
        redirect: "manual",
        signal: init.signal || AbortSignal.timeout(5000),
        headers: { ...supabaseHeaders(options.supaKey), ...(init.headers || {}) },
      });
    } catch {
      throw hubError("automation_unavailable", 503);
    }
    let body = null;
    try { body = await response.json(); } catch { /* handled below */ }
    if (!response.ok) {
      const message = cleanText(body && (body.message || body.error), 300).toLowerCase();
      if (message.includes("automation revision conflict")) throw hubError("automation_revision_conflict", 409);
      if (message.includes("scope mismatch")) throw hubError("automation_scope_rejected", 403);
      throw hubError("automation_unavailable", 503);
    }
    return body;
  }
  async function readStack(scope) {
    const row = await rpc("read_lm_automation_stack", { p_uid: scope.uid, p_chat_id: scope.chatId });
    if (row == null) return null;
    return { ...row, revision: Number(row.revision), tools: Array.isArray(row.tools) ? row.tools : [] };
  }
  async function rpc(name, body) {
    return request(`rpc/${name}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  }
  return {
    readStack,
    async replaceStack(scope, value) {
      await rpc("replace_lm_automation_stack", { p_uid: scope.uid, p_chat_id: scope.chatId, p_name: value.name, p_expected_revision: value.revision, p_tools: value.tools });
      return readStack(scope);
    },
    async toggleStack(scope, value) {
      await rpc("toggle_lm_automation_stack", { p_uid: scope.uid, p_chat_id: scope.chatId, p_enabled: value.enabled, p_expected_revision: value.revision, p_verified: value.verified === true });
      return readStack(scope);
    },
  };
}

module.exports = {
  MAX_TOOLS,
  buildAutomationHub,
  createSupabaseAutomationStore,
  discoverAutomationCatalog,
  isPublicHttpsUrl,
  mutateAutomationHub,
  normalizeHuggingFaceSpace,
  normalizeRegistryItem,
  resolveAutomationTools,
  verifyAutomationStack,
};
