"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");
const { handlePanelApiRequest } = require("./panel-api.js");

function commandStore() {
  const receipts = new Map();
  return {
    async readReceipt(_scope, key) { return receipts.get(key) || null; },
    async claimReceipt(_scope, key, value) { if (receipts.has(key)) return false; receipts.set(key, { ...value, result: null }); return true; },
    async finishReceipt(_scope, key, value) { receipts.set(key, value); },
  };
}

async function withServer(overrides, run) {
  const receipts = commandStore();
  const server = http.createServer((req, res) => Promise.resolve(handlePanelApiRequest(req, res, {
    sessionScopeImpl: async () => ({ uid: "tenant-a", chatId: "101", csrf: "csrf-a" }),
    panelOrigin: "https://panel.example",
    commandStore: receipts,
    ...overrides,
  })).catch((error) => { res.writeHead(500, { "content-type": "application/json" }); res.end(JSON.stringify({ error: error.message })); }));
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  try { return await run(`http://127.0.0.1:${server.address().port}`); }
  finally { await new Promise((resolve) => server.close(resolve)); }
}

function request(base, init = {}) {
  return fetch(`${base}/api/panel/automation-hub${init.query || ""}`, {
    method: init.method || "GET",
    headers: {
      Cookie: "lm_panel_session=test-session",
      ...(init.method === "POST" ? {
        origin: "https://panel.example", "content-type": "application/json",
        "x-lm-csrf": "csrf-a", "idempotency-key": "automation-01",
      } : {}),
      ...(init.headers || {}),
    },
    ...(init.body ? { body: JSON.stringify(init.body) } : {}),
  }).then(async (response) => ({ response, body: await response.json() }));
}

test("Automation Hub GET is tenant scoped and returns public catalog plus CSRF", async () => {
  const scopes = [];
  await withServer({
    automationStore: { async readStack(scope) { scopes.push(scope); return null; } },
    automationCatalog: async ({ query }) => ({ query, sources: [{ id: "mcp-registry", label: "Official MCP Registry", status: "ready", detail: "候補を取得済み" }], items: [] }),
  }, async (base) => {
    const result = await request(base, { query: "?q=video" });
    assert.equal(result.response.status, 200);
    assert.equal(result.body.query, "video");
    assert.equal(result.body.csrf, "csrf-a");
    assert.deepEqual(result.body.stack, { id: "default", name: "My automation", desired_state: "off", observed_state: "stopped", revision: 0, last_error_code: null, tools: [] });
  });
  assert.deepEqual(scopes, [{ uid: "tenant-a", chatId: "101", csrf: "csrf-a" }]);
});

test("Automation Hub toggle uses CSRF, exact origin, revision, and idempotent replay", async () => {
  const toggles = [];
  const automationStore = {
    async readStack() { return { id: "default", name: "Build flow", desired_state: "off", observed_state: "stopped", revision: 7, last_error_code: null, tools: [{ catalog_id: "mcp-registry:io.example/remote@1.0.0", source: "mcp-registry", name: "Remote", description: "", connection_kind: "remote_mcp", endpoint: "https://mcp.example/mcp", source_url: "https://example.com", version: "1.0.0", required_secrets: [] }] }; },
    async toggleStack(scope, value) {
      toggles.push({ scope, value });
      return { id: "default", name: "Build flow", desired_state: "on", observed_state: "running", revision: 8, tools: [{ catalog_id: "mcp-registry:io.example/remote@1.0.0" }] };
    },
  };
  await withServer({ automationStore, automationStackVerifier: async () => [{ catalog_id: "mcp-registry:io.example/remote@1.0.0", tool_count: 1 }] }, async (base) => {
    const body = { action: "toggle", enabled: true, revision: 7 };
    const first = await request(base, { method: "POST", body });
    assert.equal(first.response.status, 200);
    assert.equal(first.body.observed_state, "running");
    const replay = await request(base, { method: "POST", body });
    assert.deepEqual(replay.body, first.body);
    const rejected = await request(base, { method: "POST", body, headers: { origin: "https://evil.example", "idempotency-key": "automation-02" } });
    assert.equal(rejected.response.status, 403);
  });
  assert.equal(toggles.length, 1);
  assert.deepEqual(toggles[0].value, { enabled: true, revision: 7, verified: true });
});

test("Automation Hub rejects unknown body fields before mutation", async () => {
  let writes = 0;
  await withServer({ automationStore: { async toggleStack() { writes += 1; } } }, async (base) => {
    const result = await request(base, { method: "POST", body: { action: "toggle", enabled: true, revision: 0, endpoint: "https://evil.example" } });
    assert.equal(result.response.status, 400);
    assert.deepEqual(result.body, { error: "invalid_automation_mutation" });
  });
  assert.equal(writes, 0);
});

test("Automation Hub keeps OFF when MCP initialize or tools/list cannot be verified", async () => {
  let writes = 0;
  const automationStore = {
    async readStack() { return { id: "default", revision: 3, tools: [{ catalog_id: "mcp-registry:io.example/remote@1.0.0", source: "mcp-registry", endpoint: "https://mcp.example/mcp", required_secrets: [] }] }; },
    async toggleStack() { writes += 1; },
  };
  await withServer({
    automationStore,
    automationStackVerifier: async () => { throw Object.assign(new Error("mcp_connection_failed"), { status: 409 }); },
  }, async (base) => {
    const result = await request(base, { method: "POST", body: { action: "toggle", enabled: true, revision: 3 }, headers: { "idempotency-key": "automation-fail-01" } });
    assert.equal(result.response.status, 409);
    assert.deepEqual(result.body, { error: "mcp_connection_failed" });
  });
  assert.equal(writes, 0);
});
