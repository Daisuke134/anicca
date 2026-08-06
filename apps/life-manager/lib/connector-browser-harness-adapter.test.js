"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { createBrowserHarnessAdapter } = require("./connector-browser-harness-adapter.js");

const PAGE_WS = "ws://127.0.0.1:9222/devtools/page/TARGETOWNED123";

test("bounded fallback discovers and executes only focused actions on the exact claimed page", async () => {
  const calls = [];
  const page = Object.freeze({ page_id: "owned-page-1" });
  const proposed = [
    { purpose: "fill", method: "ax_fill", control: "required_text" },
    { purpose: "submit", method: "ax_click", control: "registration_submit" },
  ];
  const adapter = createBrowserHarnessAdapter({
    async observePage(input) {
      assert.equal(input.page, page);
      calls.push(["observe", input.target_id]);
      return Object.freeze({ state: "registration_form", controls: ["required_text", "registration_submit"] });
    },
    async proposeAction(input) {
      assert.equal(input.page_websocket, PAGE_WS);
      assert.equal(Object.hasOwn(input, "browser"), false);
      assert.equal(Object.hasOwn(input, "browser_endpoint"), false);
      calls.push(["propose", input.step]);
      return proposed.shift() || Object.freeze({ purpose: "readback", method: "parent_readback", control: "registration_state" });
    },
    async performAction(input) {
      assert.equal(input.page, page);
      calls.push(["perform", input.action.purpose, input.action.method]);
      return Object.freeze({ status: "success" });
    },
    async readExpectedState(input) {
      calls.push(["readback", input.expected_state]);
      return calls.filter(([name]) => name === "perform").length === 2
        ? Object.freeze({ status: "registered" })
        : Object.freeze({ status: "absent" });
    },
  });

  const result = await adapter.runFallback({
    provider: "luma",
    page,
    pageWebsocket: PAGE_WS,
    expectedState: "registered_or_pending",
    maxSteps: 10,
  });

  assert.equal(result.status, "completed");
  assert.equal(result.provider_state.status, "registered");
  assert.deepEqual(result.repaired_actions, [
    { purpose: "fill", method: "ax_fill", control: "required_text" },
    { purpose: "submit", method: "ax_click", control: "registration_submit" },
  ]);
  assert.deepEqual(calls.filter(([name]) => name === "perform").length, 2);
});

test("adapter rejects browser-wide, Gig, credential-bearing, and non-page websocket endpoints", () => {
  const adapter = createBrowserHarnessAdapter({
    observePage() {}, proposeAction() {}, performAction() {}, readExpectedState() {},
  });
  const base = {
    provider: "luma",
    page: {},
    expectedState: "registered_or_pending",
    maxSteps: 10,
  };

  for (const pageWebsocket of [
    "ws://127.0.0.1:9222/devtools/browser/abcdef",
    "ws://127.0.0.1:9223/devtools/page/TARGETOWNED123",
    "ws://user:secret@127.0.0.1:9222/devtools/page/TARGETOWNED123",
    "ws://127.0.0.1:9222/devtools/page/",
  ]) {
    assert.throws(() => adapter.runFallback({ ...base, pageWebsocket }), /Browser Harness adapter invalid/);
  }
});

test("adapter blocks browser lifecycle actions proposed by an agent", async () => {
  for (const method of ["browser_close", "target_create", "target_close", "new_tab"]) {
    const adapter = createBrowserHarnessAdapter({
      async observePage() { return Object.freeze({ state: "form", controls: [] }); },
      async proposeAction() {
        return Object.freeze({ purpose: "submit", method, control: "registration_submit" });
      },
      async performAction() { throw new Error("blocked action must not execute"); },
      async readExpectedState() { return Object.freeze({ status: "absent" }); },
    });
    const result = await adapter.runFallback({
      provider: "luma", page: {}, pageWebsocket: PAGE_WS,
      expectedState: "registered_or_pending", maxSteps: 10,
    });
    assert.equal(result.status, "failed");
    assert.equal(result.safe_reason, "unsafe_agent_action");
    assert.deepEqual(result.repaired_actions, []);
  }
});

test("adapter stops after ten unsuccessful steps without changing the page owner", async () => {
  let performed = 0;
  const adapter = createBrowserHarnessAdapter({
    async observePage() { return Object.freeze({ state: "form", controls: ["next"] }); },
    async proposeAction() {
      return Object.freeze({ purpose: "observe", method: "ax_inspect", control: "next" });
    },
    async performAction() {
      performed += 1;
      return Object.freeze({ status: "success" });
    },
    async readExpectedState() { return Object.freeze({ status: "absent" }); },
  });

  const result = await adapter.runFallback({
    provider: "connpass", page: {}, pageWebsocket: PAGE_WS,
    expectedState: "registered_or_pending", maxSteps: 10,
  });

  assert.equal(result.status, "failed");
  assert.equal(result.safe_reason, "agent_step_limit");
  assert.equal(performed, 10);
  assert.equal(result.repaired_actions.length, 10);
});
