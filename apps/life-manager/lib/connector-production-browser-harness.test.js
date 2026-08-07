"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  createBoundedActionProposer,
  createLumaPrivateValueResolver,
  createProductionBrowserHarness,
  inspectPageControls,
  operatePageControl,
} = require("./connector-production-browser-harness.js");

test("bounded proposer requests one structured action from Terra with sanitized controls only", async () => {
  let request;
  const proposer = createBoundedActionProposer({
    repoRoot: "/private/repo",
    evidenceDir: "/private/evidence",
    async runAgentRunner(input) {
      request = input;
      return {
        summary: { status: "success", selected_provider: "codex", selected_model: "gpt-5.6-terra" },
        value: { purpose: "submit", method: "ax_click", control: "register_button" },
      };
    },
  });
  const action = await proposer({
    provider: "luma",
    page_websocket: "ws://127.0.0.1:9222/devtools/page/OWNEDTARGET1",
    target_id: "OWNEDTARGET1",
    expected_state: "registered_or_pending",
    step: 2,
    observation: {
      state: "registration_page",
      controls: [{ control: "register_button", kind: "button", label: "Register", required: false }],
    },
  });
  assert.deepEqual(action, { purpose: "submit", method: "ax_click", control: "register_button" });
  assert.equal(request.taskClass, "browser-lane-agent");
  assert.equal(request.timeoutMs, 30_000);
  assert.match(request.prompt, /one browser action/i);
  assert.match(request.prompt, /register_button/);
  assert.doesNotMatch(request.prompt, /private-phone|cookie|password/i);
  assert.equal(JSON.stringify(request).includes("page_websocket"), false);
  assert.equal(JSON.stringify(request).includes("ws://"), false);
});

test("default page adapter observes labels and parent resolves private values before DOM actions", async () => {
  const phoneElement = {
    tagName: "INPUT",
    type: "tel",
    required: true,
    dataset: {},
    labels: [{ innerText: "Phone number" }],
    innerText: "",
    options: [],
    getAttribute(name) { return name === "role" ? null : ""; },
  };
  const buttonElement = {
    tagName: "BUTTON",
    type: "submit",
    required: false,
    dataset: {},
    labels: [],
    innerText: "Register",
    options: [],
    getAttribute(name) { return name === "aria-label" ? "Register" : null; },
  };
  const calls = [];
  const locators = new Map();
  const page = {
    locator(selector) {
      if (selector === "input, textarea, select, button, a[role=button]") {
        return { async evaluateAll(callback) { return callback([phoneElement, buttonElement]); } };
      }
      if (!locators.has(selector)) {
        locators.set(selector, {
          async count() { return 1; },
          async fill(value) { calls.push(["fill", selector, value]); },
          async click() { calls.push(["click", selector]); },
          async check() { calls.push(["check", selector]); },
          async selectOption(value) { calls.push(["select", selector, value]); },
        });
      }
      return locators.get(selector);
    },
    keyboard: { async press(key) { calls.push(["key", key]); } },
  };
  const controls = await inspectPageControls({ page });
  assert.deepEqual(controls.map(({ kind, label, required }) => ({ kind, label, required })), [
    { kind: "input", label: "Phone number", required: true },
    { kind: "button", label: "Register", required: false },
  ]);
  assert.match(controls[0].control, /^control_[0-9]+$/);
  assert.equal(phoneElement.dataset.lmConnectorControl, controls[0].control);

  const resolveValue = createLumaPrivateValueResolver({
    readProfile: async () => ({ phone: "private-phone", form_answers: {} }),
  });
  const value = await resolveValue({ control: controls[0] });
  assert.equal(value, "private-phone");
  await operatePageControl({
    page,
    control: controls[0],
    action: { purpose: "fill", method: "ax_fill", control: controls[0].control },
    value,
  });
  await operatePageControl({
    page,
    control: controls[1],
    action: { purpose: "submit", method: "ax_click", control: controls[1].control },
    value: null,
  });
  assert.deepEqual(calls.map(([name, , input]) => [name, input]), [
    ["fill", "private-phone"],
    ["click", undefined],
  ]);
});

test("production harness lets the model choose controls but parent owns values actions and readback", async () => {
  const calls = [];
  const page = Object.freeze({ page_id: "owned-page" });
  const candidate = Object.freeze({ event_ref: "luma-event://event/one" });
  let performed = 0;
  const harness = createProductionBrowserHarness({
    lumaWorkflow: {
      async readProviderState(input) {
        calls.push(["readback", input]);
        return performed === 2 ? { status: "registered" } : { status: "absent" };
      },
    },
    async inspectControls(input) {
      assert.equal(input.page, page);
      calls.push(["inspect"]);
      return [
        { control: "phone_field", kind: "input", label: "Phone", required: true },
        { control: "register_button", kind: "button", label: "Register", required: false },
      ];
    },
    async proposeAction(input) {
      calls.push(["propose", input]);
      assert.equal(Object.hasOwn(input, "page"), false);
      assert.equal(Object.hasOwn(input, "browser"), false);
      return input.step === 1
        ? { purpose: "fill", method: "ax_fill", control: "phone_field" }
        : { purpose: "submit", method: "ax_click", control: "register_button" };
    },
    async operateControl(input) {
      calls.push(["operate", input]);
      performed += 1;
      if (input.action.control === "phone_field") assert.equal(input.value, "private-phone");
      return { status: "success" };
    },
    async resolveValue(input) {
      calls.push(["resolve", input.control.control]);
      return input.control.control === "phone_field" ? "private-phone" : null;
    },
  });

  const result = await harness.runFallback({
    provider: "luma",
    candidate,
    page,
    pageWebsocket: "ws://127.0.0.1:9222/devtools/page/OWNEDTARGET1",
    maxSteps: 10,
    expectedState: "registered_or_pending",
  });

  assert.equal(result.status, "completed");
  assert.equal(result.provider_state.status, "registered");
  assert.deepEqual(result.repaired_actions, [
    { purpose: "fill", method: "ax_fill", control: "phone_field" },
    { purpose: "submit", method: "ax_click", control: "register_button" },
  ]);
  assert.equal(calls.filter(([name]) => name === "inspect").length, 2);
  assert.equal(calls.filter(([name]) => name === "operate").length, 2);
  assert.equal(calls.filter(([name]) => name === "readback").length, 2);
  const promptInputs = calls.filter(([name]) => name === "propose").map(([, input]) => JSON.stringify(input));
  assert.equal(promptInputs.some((value) => value.includes("private-phone")), false);

  const replay = await harness.performAction({
    page,
    action: { purpose: "submit", method: "ax_click", control: "register_button" },
  });
  assert.deepEqual(replay, { status: "success" });
});

test("production harness uses Connpass parent readback for a Connpass fallback", async () => {
  const page = Object.freeze({ page_id: "owned-page" });
  let operated = false;
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
    connpassWorkflow: {
      async readProviderState(input) {
        assert.equal(input.page, page);
        return operated ? { status: "pending" } : { status: "absent" };
      },
    },
    async inspectControls() {
      return [{ control: "apply_button", kind: "button", label: "Apply", required: false }];
    },
    async proposeAction() { return { purpose: "submit", method: "ax_click", control: "apply_button" }; },
    async operateControl() { operated = true; return { status: "success" }; },
    async resolveValue() { return null; },
  });

  const result = await harness.runFallback({
    provider: "connpass",
    candidate: { event_ref: "connpass-event://event/401001" },
    page,
    pageWebsocket: "ws://127.0.0.1:9222/devtools/page/OWNEDTARGET1",
    maxSteps: 10,
    expectedState: "registered_or_pending",
  });

  assert.equal(result.status, "completed");
});
