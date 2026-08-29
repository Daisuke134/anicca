"use strict";

const test = require("node:test");
const assert = require("node:assert");
const vm = require("node:vm");
const { renderMoneyPrinterWebMcpScript } = require("./money-printer-webmcp.js");

test("Money Printer registers one top-level read-only WebMCP inspection tool", async () => {
  const script = renderMoneyPrinterWebMcpScript({ csrf: "csrf-secret-must-not-ship" });
  assert.match(script, /document\.modelContext\.registerTool\(/);
  assert.doesNotMatch(script, /csrf-secret-must-not-ship|x-lm-csrf|authorization|bearer|idempotency-key/i);

  const registrations = [];
  let request = null;
  const body = { observed_at: "2026-08-29T00:00:00.000Z", metrics: { paid_verified: "0" } };
  vm.runInNewContext(script, {
    document: {
      modelContext: {
        registerTool(tool) {
          registrations.push(tool);
          return Promise.resolve();
        },
      },
    },
    fetch: async (url, init) => {
      request = { url, init };
      return { ok: true, status: 200, json: async () => body };
    },
    Promise,
    Error,
    Object,
    String,
  });

  assert.equal(registrations.length, 1);
  const [tool] = registrations;
  assert.equal(tool.name, "inspect_money_printer");
  assert.deepEqual(Object.keys(tool).sort(), ["annotations", "description", "execute", "inputSchema", "name"]);
  assert.deepEqual(JSON.parse(JSON.stringify(tool.inputSchema)), {
    type: "object",
    properties: {},
    additionalProperties: false,
  });
  assert.equal(tool.annotations.readOnlyHint, true);

  assert.deepEqual(await tool.execute({}), body);
  assert.deepEqual(request, {
    url: "/api/panel/money-printer",
    init: { method: "GET", credentials: "same-origin", headers: { Accept: "application/json" } },
  });

  assert.doesNotThrow(() => vm.runInNewContext(script, { document: {} }));
});
