"use strict";

const net = require("node:net");
const dns = require("node:dns").promises;

const MCP_REGISTRY = "https://registry.modelcontextprotocol.io/v0.1/servers";
const HUGGING_FACE_SPACES = "https://huggingface.co/api/spaces";
const PRODUCT_HUNT_GRAPHQL = "https://api.producthunt.com/v2/api/graphql";
const MAX_TOOLS = 12;
const DISCOVERY_TTL_MS = 60_000;
const discoveryCache = new Map();

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
  if (net.isIP(hostname) === 4) {
    const octets = hostname.split(".").map(Number);
    return octets[0] === 10 || octets[0] === 127 || octets[0] === 0
      || (octets[0] === 100 && octets[1] >= 64 && octets[1] <= 127)
      || (octets[0] === 169 && octets[1] === 254)
      || (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31)
      || (octets[0] === 192 && (octets[1] === 0 || octets[1] === 168))
      || (octets[0] === 198 && [18, 19, 51].includes(octets[1]))
      || (octets[0] === 203 && octets[1] === 0 && octets[2] === 113)
      || octets[0] >= 224;
  }
  if (net.isIP(hostname) === 6) {
    const host = hostname.toLowerCase();
    return host === "::1" || host === "::" || host.startsWith("fc") || host.startsWith("fd")
      || host.startsWith("fe8") || host.startsWith("fe9") || host.startsWith("fea") || host.startsWith("feb")
      || host.startsWith("2001:db8:") || host.startsWith("::ffff:127.") || host.startsWith("::ffff:10.") || host.startsWith("::ffff:192.168.");
  }
  return false;
}

function isPublicHttpsUrl(value) {
  try {
    const url = new URL(String(value || ""));
    const hostname = url.hostname.toLowerCase();
    return url.protocol === "https:" && !url.username && !url.password && Boolean(hostname)
      && hostname !== "localhost" && !hostname.endsWith(".localhost") && !hostname.endsWith(".local")
      && !isPrivateIp(hostname);
  } catch {
    return false;
  }
}

function source(id, label, status, detail) {
  return { id, label, status, detail };
}

async function fetchJson(fetchImpl, url, init = {}) {
  const response = await fetchImpl(url, { ...init, signal: init.signal || AbortSignal.timeout(5000) });
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
  return Promise.all(catalogIds.map((raw) => {
    const id = cleanText(raw, 280);
    if (id.startsWith("mcp-registry:")) return resolveRegistry(id, { ...options, fetchImpl });
    if (id.startsWith("hugging-face:")) return resolveHuggingFace(id, { ...options, fetchImpl });
    throw hubError("tool_not_selectable", 409);
  }));
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
  let records;
  try { records = await lookup(endpoint.hostname); }
  catch { throw hubError("mcp_connection_failed", 409); }
  const list = Array.isArray(records) ? records : [records];
  if (!list.length || list.some((record) => !record || !net.isIP(record.address) || isPrivateIp(record.address))) throw hubError("unsafe_mcp_endpoint", 409);
}

async function verifyAutomationTool(scope, tool, options) {
  if (!tool || !isPublicHttpsUrl(tool.endpoint)) throw hubError("unsafe_mcp_endpoint", 409);
  const endpoint = new URL(tool.endpoint);
  await assertPublicDns(endpoint, options);
  const requestHeaders = await tenantHeaders(scope, tool, options);
  const fetchImpl = options.fetchImpl || fetch;
  const guardedFetch = async (input, init = {}) => {
    const target = new URL(typeof input === "string" || input instanceof URL ? input : input.url);
    if (target.origin !== endpoint.origin || target.pathname !== endpoint.pathname) throw hubError("unsafe_mcp_endpoint", 409);
    const timeout = AbortSignal.timeout(options.timeoutMs || 5000);
    const signal = init.signal ? AbortSignal.any([init.signal, timeout]) : timeout;
    return fetchImpl(input, { ...init, redirect: "manual", signal });
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
    return fetchJson(fetchImpl, `${base}/rest/v1/${url}`, { ...init, headers: { ...supabaseHeaders(options.supaKey), ...(init.headers || {}) } });
  }
  async function readStack(scope) {
    const query = new URLSearchParams({ uid: `eq.${scope.uid}`, stack_id: "eq.default", select: "stack_id,name,desired_state,observed_state,revision,last_error_code", limit: "1" });
    const rows = await request(`lm_automation_stacks?${query}`);
    if (!Array.isArray(rows) || !rows[0]) return null;
    const toolQuery = new URLSearchParams({ uid: `eq.${scope.uid}`, stack_id: "eq.default", select: "catalog_id,source,name,description,connection_kind,endpoint,source_url,version,required_secrets,position", order: "position.asc" });
    const tools = await request(`lm_automation_stack_tools?${toolQuery}`);
    return { id: rows[0].stack_id, name: rows[0].name, desired_state: rows[0].desired_state, observed_state: rows[0].observed_state, revision: Number(rows[0].revision), last_error_code: rows[0].last_error_code, tools: Array.isArray(tools) ? tools.map(({ position, ...tool }) => tool) : [] };
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
