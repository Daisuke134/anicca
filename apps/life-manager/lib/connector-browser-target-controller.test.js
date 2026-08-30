"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { createConnectorBrowserTargetController } = require("./connector-browser-target-controller.js");

function fixture() {
  const calls = [];
  const baseline = { targetId: "BASELINE", async evaluate() { return 1; } };
  const owned = { targetId: "OWNED123", async evaluate() { calls.push(["evaluate", "OWNED123"]); return 1; } };
  const pages = [baseline];
  const liveTargetIds = new Set(["BASELINE"]);
  let targetInfosOverride;
  const context = {
    pages() { calls.push(["pages"]); return [...pages]; },
    async newCDPSession(page) {
      calls.push(["page-session", page.targetId]);
      return {
        async send(method) {
          calls.push(["page-send", page.targetId, method]);
          return { targetInfo: { targetId: page.targetId } };
        },
        async detach() { calls.push(["page-detach", page.targetId]); },
      };
    },
  };
  const browser = {
    contexts() { calls.push(["contexts"]); return [context]; },
    async newBrowserCDPSession() {
      calls.push(["browser-session"]);
      return {
        async send(method, params) {
          calls.push(["browser-send", method, params]);
          if (method === "Target.createTarget") {
            pages.push(owned);
            liveTargetIds.add("OWNED123");
            return { targetId: "OWNED123" };
          }
          if (method === "Target.getTargets") {
            return {
              targetInfos: targetInfosOverride === undefined
                ? [...liveTargetIds].map((targetId) => ({ targetId })) : targetInfosOverride,
            };
          }
          if (method === "Target.closeTarget") {
            liveTargetIds.delete(params.targetId);
            return { success: true };
          }
          throw new Error(`unexpected ${method}`);
        },
        async detach() { calls.push(["browser-detach"]); },
      };
    },
  };
  return {
    baseline,
    browser,
    calls,
    owned,
    removeOwnedTarget() { liveTargetIds.delete("OWNED123"); },
    setTargetInventory(value) { targetInfosOverride = value; },
  };
}

test("creates exactly one default-context target and binds only its exact Playwright page", async () => {
  const fx = fixture();
  const controller = createConnectorBrowserTargetController({ browser: fx.browser });

  const result = await controller.create();

  assert.equal(result.target_id, "OWNED123");
  assert.equal(result.page_websocket, "ws://127.0.0.1:9222/devtools/page/OWNED123");
  assert.equal(result.page, fx.owned);
  assert.equal(fx.calls.filter(([name, method]) => name === "browser-send" && method === "Target.createTarget").length, 1);
  assert.deepEqual(
    fx.calls.find(([name, method]) => name === "browser-send" && method === "Target.createTarget"),
    ["browser-send", "Target.createTarget", { url: "about:blank" }],
  );
  assert.equal(fx.calls.some(([name]) => name === "new-page"), false);
});

test("probes and closes only the exact Connector target", async () => {
  const fx = fixture();
  const controller = createConnectorBrowserTargetController({ browser: fx.browser });
  const target = await controller.create();

  assert.equal(await controller.probe(target.page_websocket), true);
  assert.equal(await controller.close(target.target_id), true);
  assert.deepEqual(
    fx.calls.filter(([name, method]) => name === "browser-send" && method === "Target.closeTarget"),
    [["browser-send", "Target.closeTarget", { targetId: "OWNED123" }]],
  );
});

test("closing an already-disappeared exact target is idempotent", async () => {
  const fx = fixture();
  const controller = createConnectorBrowserTargetController({ browser: fx.browser });
  const target = await controller.create();
  fx.removeOwnedTarget();

  assert.equal(await controller.close(target.target_id), true);
  assert.deepEqual(
    fx.calls.filter(([name, method]) => name === "browser-send" && method === "Target.closeTarget"),
    [],
  );
});

test("closing with a malformed target inventory rejects before Target.closeTarget", async () => {
  const fx = fixture();
  const controller = createConnectorBrowserTargetController({ browser: fx.browser });
  const target = await controller.create();

  for (const targetInfos of [[null], [{}], [{ targetId: "invalid target id" }]]) {
    fx.setTargetInventory(targetInfos);
    await assert.rejects(() => controller.close(target.target_id), /Connector target ID invalid/);
  }
  assert.deepEqual(
    fx.calls.filter(([name, method]) => name === "browser-send" && method === "Target.closeTarget"),
    [],
  );
});

test("refuses another port, malformed target IDs, and ambiguous browser contexts", async () => {
  const fx = fixture();
  assert.throws(
    () => createConnectorBrowserTargetController({ browser: fx.browser, endpoint: "http://127.0.0.1:9223" }),
    /endpoint/i,
  );
  assert.throws(
    () => createConnectorBrowserTargetController({
      browser: { ...fx.browser, contexts: () => [{}, {}] },
    }),
    /context/i,
  );
});
