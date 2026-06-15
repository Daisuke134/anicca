const { test } = require("node:test");
const assert = require("node:assert");
const { createInbox } = require("../agentmail");

function fakeFetch(captured, response) {
  return async (url, opts) => {
    captured.url = url; captured.opts = opts;
    return response;
  };
}

test("createInbox POSTs to AgentMail with bearer auth + username", async () => {
  const cap = {};
  const f = fakeFetch(cap, { ok: true, status: 200, json: async () => ({ inbox_id: "anicca-c001@agentmail.to", address: "anicca-c001@agentmail.to" }) });
  const addr = await createInbox("anicca-c001", { apiKey: "k_test", f });
  assert.equal(addr, "anicca-c001@agentmail.to");
  assert.equal(cap.url, "https://api.agentmail.to/v0/inboxes");
  assert.equal(cap.opts.method, "POST");
  assert.equal(cap.opts.headers.Authorization, "Bearer k_test");
  assert.equal(JSON.parse(cap.opts.body).username, "anicca-c001");
});

test("createInbox falls back to address when inbox_id absent", async () => {
  const f = fakeFetch({}, { ok: true, status: 200, json: async () => ({ address: "anicca-c002@agentmail.to" }) });
  assert.equal(await createInbox("anicca-c002", { apiKey: "k", f }), "anicca-c002@agentmail.to");
});

test("createInbox throws on non-ok (no fake success)", async () => {
  const f = fakeFetch({}, { ok: false, status: 402, text: async () => "payment required" });
  await assert.rejects(() => createInbox("anicca-c003", { apiKey: "k", f }), /agentmail 402/i);
});

test("createInbox throws when API returns ok but no usable address", async () => {
  const f = fakeFetch({}, { ok: true, status: 200, json: async () => ({}) });
  await assert.rejects(() => createInbox("anicca-c004", { apiKey: "k", f }), /no inbox/i);
});

test("createInbox throws without an api key", async () => {
  await assert.rejects(() => createInbox("anicca-c005", { apiKey: "", f: async () => ({}) }), /api key/i);
});
