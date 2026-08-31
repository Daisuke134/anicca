"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  discoverAutomationCatalog,
  createSupabaseAutomationStore,
  isPublicHttpsUrl,
  mutateAutomationHub,
  resolveAutomationTools,
  verifyAutomationStack,
} = require("./automation-hub.js");

function json(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

test("catalog joins official MCP, MCP-badged Hugging Face Spaces, and discovery-only Product Hunt", async () => {
  const calls = [];
  const fetchImpl = async (input, init = {}) => {
    const url = new URL(input);
    calls.push({ url, init });
    if (url.hostname === "registry.modelcontextprotocol.io") return json({ servers: [{
      server: {
        name: "io.example/remote", title: "Remote Worker", version: "1.2.3",
        description: "Runs a reviewed remote workflow.", websiteUrl: "https://example.com/worker",
        remotes: [{ type: "streamable-http", url: "https://mcp.example.com/mcp" }],
      },
      _meta: { "io.modelcontextprotocol.registry/official": { status: "active", isLatest: true } },
    }] });
    if (url.hostname === "huggingface.co" && url.pathname === "/api/spaces") return json([{ id: "maker/audio-tool", sdk: "gradio", private: false, tags: ["gradio", "mcp-server"], cardData: { title: "Audio Workflow Tool", short_description: "Cleans audio." } }]);
    if (url.hostname === "api.producthunt.com") return json({ data: { posts: { edges: [{ node: { id: "ph-1", name: "Workflow Finder", tagline: "Find automation products", url: "https://www.producthunt.com/posts/flow-finder", website: "https://flow.example" } }] } } });
    throw new Error(`unexpected ${url}`);
  };

  const result = await discoverAutomationCatalog({ query: "workflow", fetchImpl, productHuntToken: "ph-token" });
  assert.deepEqual(result.sources.map(({ id, status }) => ({ id, status })), [
    { id: "mcp-registry", status: "ready" },
    { id: "hugging-face", status: "ready" },
    { id: "product-hunt", status: "ready" },
  ]);
  assert.deepEqual(result.items.map(({ catalog_id, selectable, connection_kind }) => ({ catalog_id, selectable, connection_kind })), [
    { catalog_id: "mcp-registry:io.example/remote@1.2.3", selectable: true, connection_kind: "remote_mcp" },
    { catalog_id: "hugging-face:maker/audio-tool", selectable: true, connection_kind: "hugging_face_mcp" },
    { catalog_id: "product-hunt:ph-1", selectable: false, connection_kind: "discovery_only" },
  ]);
  assert.equal(calls.find((call) => call.url.hostname === "registry.modelcontextprotocol.io").url.searchParams.get("version"), "latest");
  assert.equal(calls.find((call) => call.url.hostname === "api.producthunt.com").init.headers.Authorization, "Bearer ph-token");
});

test("catalog degrades each provider independently and does not call Product Hunt without a token", async () => {
  const hosts = [];
  const result = await discoverAutomationCatalog({ query: "automation", cache: false, fetchImpl: async (input) => {
    const url = new URL(input); hosts.push(url.hostname);
    if (url.hostname === "registry.modelcontextprotocol.io") throw new Error("offline");
    return json([]);
  } });
  assert.deepEqual(result.sources.map(({ id, status }) => ({ id, status })), [
    { id: "mcp-registry", status: "unavailable" },
    { id: "hugging-face", status: "ready" },
    { id: "product-hunt", status: "setup_required" },
  ]);
  assert.equal(hosts.includes("api.producthunt.com"), false);
});

test("catalog caches one provider fan-out per query for a short window", async () => {
  let calls = 0;
  const cache = new Map();
  const fetchImpl = async (input) => { calls += 1; return json(new URL(input).hostname === "registry.modelcontextprotocol.io" ? { servers: [] } : []); };
  await discoverAutomationCatalog({ query: "cache me", fetchImpl, cache, nowMs: 1000 });
  await discoverAutomationCatalog({ query: "cache me", fetchImpl, cache, nowMs: 2000 });
  assert.equal(calls, 2);
  await discoverAutomationCatalog({ query: "cache me", fetchImpl, cache, nowMs: 62_000 });
  assert.equal(calls, 4);
});

test("only public HTTPS metadata can become a runnable remote endpoint", () => {
  for (const value of ["http://example.com/mcp", "https://localhost/mcp", "https://127.0.0.1/mcp", "https://10.0.0.1/mcp", "https://user:pass@example.com/mcp"]) {
    assert.equal(isPublicHttpsUrl(value), false, value);
  }
  assert.equal(isPublicHttpsUrl("https://mcp.example.com/mcp"), true);
});

test("resolver re-reads exact provider metadata and rejects discovery-only or missing ids", async () => {
  const fetchImpl = async (input) => {
    const url = new URL(input);
    if (url.hostname === "registry.modelcontextprotocol.io") return json({ servers: [{
      server: { name: "io.example/remote", title: "Remote", version: "1.2.3", remotes: [{ type: "streamable-http", url: "https://mcp.example.com/mcp" }] },
      _meta: { "io.modelcontextprotocol.registry/official": { status: "active", isLatest: true } },
    }] });
    if (url.hostname === "huggingface.co") return json({ id: "maker/audio-tool", sdk: "gradio", private: false, tags: ["gradio", "mcp-server"], cardData: { title: "Audio Tool" } });
    throw new Error("unexpected provider");
  };
  const tools = await resolveAutomationTools([
    "mcp-registry:io.example/remote@1.2.3",
    "hugging-face:maker/audio-tool",
  ], { fetchImpl });
  assert.deepEqual(tools.map((tool) => tool.catalog_id), ["mcp-registry:io.example/remote@1.2.3", "hugging-face:maker/audio-tool"]);
  await assert.rejects(resolveAutomationTools(["product-hunt:ph-1"], { fetchImpl }), /tool_not_selectable/);
});

test("stack mutation is revisioned, strips client metadata, and toggles desired state", async () => {
  const calls = [];
  const store = {
    async replaceStack(scope, value) { calls.push({ type: "replace", scope, value }); return { id: "default", name: value.name, desired_state: "off", observed_state: "stopped", revision: 4, tools: value.tools }; },
    async toggleStack(scope, value) { calls.push({ type: "toggle", scope, value }); return { id: "default", name: "Build flow", desired_state: value.enabled ? "on" : "off", observed_state: value.enabled ? "pending_start" : "pending_stop", revision: 5, tools: [{ catalog_id: "mcp-registry:io.example/remote@1.2.3" }] }; },
  };
  const resolved = [{ catalog_id: "mcp-registry:io.example/remote@1.2.3", source: "mcp-registry", name: "Remote", description: "", connection_kind: "remote_mcp", endpoint: "https://mcp.example.com/mcp", source_url: "https://mcp.example.com/mcp", version: "1.2.3", required_secrets: [] }];
  const scope = { uid: "tenant-a", chatId: "101" };
  const replaced = await mutateAutomationHub(scope, { action: "replace", name: "Build flow", catalog_ids: [resolved[0].catalog_id], revision: 3 }, { store, resolveTools: async () => resolved });
  assert.equal(replaced.revision, 4);
  assert.equal("injected" in calls[0].value, false);
  const toggled = await mutateAutomationHub(scope, { action: "toggle", enabled: true, revision: 4 }, { store });
  assert.equal(toggled.observed_state, "pending_start");
  assert.equal(calls[1].value.verified, false);
  await assert.rejects(mutateAutomationHub(scope, { action: "replace", name: "", catalog_ids: [], revision: 1 }, { store }), /invalid_automation_mutation/);
  await assert.rejects(mutateAutomationHub(scope, { action: "toggle", enabled: true, revision: 5, injected: true }, { store }), /invalid_automation_mutation/);
});

test("Supabase store binds every read and RPC to the session tenant and actor", async () => {
  const calls = [];
  const fetchImpl = async (input, init = {}) => {
    const url = new URL(input); calls.push({ url, init });
    if (url.pathname.endsWith("/rpc/toggle_lm_automation_stack")) return json([]);
    if (url.pathname.endsWith("/lm_automation_stacks")) return json([{ stack_id: "default", name: "Build flow", desired_state: "on", observed_state: "pending_start", revision: 2, last_error_code: null }]);
    if (url.pathname.endsWith("/lm_automation_stack_tools")) return json([{ catalog_id: "mcp-registry:io.example/remote@1.0.0", source: "mcp-registry", name: "Remote", description: "", connection_kind: "remote_mcp", endpoint: "https://mcp.example/mcp", source_url: "https://example.com", version: "1.0.0", required_secrets: [], position: 0 }]);
    throw new Error(`unexpected ${url}`);
  };
  const store = createSupabaseAutomationStore({ supaUrl: "https://db.example", supaKey: "service-key", fetchImpl });
  const stack = await store.toggleStack({ uid: "tenant-a", chatId: "101" }, { enabled: true, revision: 1, verified: true });
  assert.equal(stack.revision, 2);
  assert.deepEqual(JSON.parse(calls[0].init.body), { p_uid: "tenant-a", p_chat_id: "101", p_enabled: true, p_expected_revision: 1, p_verified: true });
  assert.equal(calls[1].url.searchParams.get("uid"), "eq.tenant-a");
  assert.equal(calls[2].url.searchParams.get("uid"), "eq.tenant-a");
  assert.equal(calls.every((call) => call.init.headers.Authorization === "Bearer service-key"), true);
});

test("MCP connection gate resolves public DNS, initializes, and lists tools before ON", async () => {
  const events = [];
  const stack = { tools: [{ catalog_id: "mcp-registry:io.example/remote@1.0.0", source: "mcp-registry", endpoint: "https://mcp.example.com/mcp", required_secrets: [] }] };
  const result = await verifyAutomationStack({ uid: "tenant-a", chatId: "101" }, stack, {
    lookup: async (hostname) => { events.push(`dns:${hostname}`); return [{ address: "93.184.216.34", family: 4 }]; },
    transportFactory: (url) => ({ url }),
    clientFactory: () => ({
      async connect(transport) { events.push(`connect:${transport.url.hostname}`); },
      async listTools() { events.push("tools/list"); return { tools: [{ name: "run" }] }; },
      async close() { events.push("close"); },
    }),
  });
  assert.deepEqual(result, [{ catalog_id: stack.tools[0].catalog_id, tool_count: 1 }]);
  assert.deepEqual(events, ["dns:mcp.example.com", "connect:mcp.example.com", "tools/list", "close"]);
});

test("MCP connection gate rejects private DNS and missing tenant secrets before connecting", async () => {
  const base = { catalog_id: "mcp-registry:io.example/remote@1.0.0", source: "mcp-registry", endpoint: "https://mcp.example.com/mcp", required_secrets: [] };
  await assert.rejects(verifyAutomationStack({ uid: "tenant-a", chatId: "101" }, { tools: [base] }, { lookup: async () => [{ address: "10.0.0.8", family: 4 }] }), /unsafe_mcp_endpoint/);
  await assert.rejects(verifyAutomationStack({ uid: "tenant-a", chatId: "101" }, { tools: [{ ...base, required_secrets: ["Authorization"] }] }, { lookup: async () => [{ address: "93.184.216.34", family: 4 }] }), /automation_configuration_required/);
});
