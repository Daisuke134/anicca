"use strict";

const assert = require("node:assert/strict");
const { mock } = require("node:test");
const test = require("node:test");

const {
  createBoundedActionProposer,
  createPrivateValueResolver,
  createLumaPrivateValueResolver,
  createProductionBrowserHarness,
  inspectPageControls,
  operatePageControl,
} = require("./connector-production-browser-harness.js");
const { createBrowserHarnessAdapter } = require("./connector-browser-harness-adapter.js");

test("bounded proposer requests one structured action from Terra with sanitized controls only", async () => {
  let request;
  const proposer = createBoundedActionProposer({
    repoRoot: "/private/repo",
    evidenceDir: "/private/evidence",
    async runAgentRunner(input) {
      request = input;
      return {
        summary: { status: "success", selected_provider: "codex", selected_model: "gpt-5.6-terra" },
        value: { control: "register_button" },
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
      controls: [{ control: "register_button", kind: "button", label: "Register", required: false, submittable: true }],
    },
  });
  assert.deepEqual(action, { control: "register_button" });
  assert.equal(request.taskClass, "browser-lane-agent");
  assert.equal(request.timeoutMs, 30_000);
  assert.match(request.prompt, /one browser action/i);
  assert.match(request.prompt, /register_button/);
  assert.doesNotMatch(request.prompt, /purpose|method/i);
  assert.deepEqual(Object.keys(request.schema.properties), ["control"]);
  assert.deepEqual(request.schema.required, ["control"]);
  assert.doesNotMatch(request.prompt, /private-phone|cookie|password/i);
  assert.equal(JSON.stringify(request).includes("page_websocket"), false);
  assert.equal(JSON.stringify(request).includes("ws://"), false);
});

test("Connpass known form completes natively before the agent when the runner is unavailable", async () => {
  const radio = (control, label, question, group) => ({ control, kind: "radio", label, question, required: true, group });
  const groups = [radio("online_radio", "オンライン視聴枠（YouTube） 無料 参加者数 30人", "参加枠", "online"), radio("online_speaker", "オンライン登壇枠（Zoom） 無料 先着順 3/3人", "参加枠", "online"),
    radio("referral_radio", "Connpass", "このイベントは何を見て知りましたか？", "referral"), radio("referral_sns", "SNS", "このイベントは何を見て知りましたか？", "referral"),
    { control: "ack_one", kind: "radio", label: "はい、わかりました。", question: "speaker acknowledgement", required: false },
    { control: "ack_two", kind: "radio", label: "はい、わかりました。", question: "second speaker acknowledgement", required: false },
    { control: "confirm_button", kind: "button", label: "申し込みを確定する", required: false, submittable: true }];
  const groupOrder = { online: 0, referral: 1 };
  let step = 0;
  let agentCalls = 0;
  const operated = [];
  const page = Object.freeze({ page_id: "known-connpass-page", url() { return "https://osaka-driven-dev.connpass.com/event/400028/join/"; } });
  const proposer = createBoundedActionProposer({ repoRoot: "/private/repo", evidenceDir: "/private/evidence", async runAgentRunner() { agentCalls += 1; throw new Error("agent unavailable"); } });
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
    connpassWorkflow: { async readProviderState() { return step === 3 ? { status: "registered" } : { status: "absent" }; } },
    async inspectControls() { return groups.map((control) => ({ ...control, completed: control.group ? step > groupOrder[control.group] : false })); },
    proposeAction: proposer,
    async operateControl(input) { operated.push(input.action.control); step += 1; return { status: "success" }; },
    resolveValue: createPrivateValueResolver({ async readPeatixProfile() { throw new Error("private profile must not be read"); }, async readFormProfile() { throw new Error("form profile must not be read"); } }),
  });

  const result = await harness.runFallback({ provider: "connpass", candidate: { event_ref: "connpass-event://event/400028" }, page, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/KNOWNCONNPASS1", maxSteps: 10, expectedState: "registered_or_pending" });
  assert.equal(result.status, "completed");
  assert.equal(agentCalls, 0);
  assert.deepEqual(operated, ["online_radio", "referral_radio", "confirm_button"]);
});

test("Connpass resolver approves only the exact safe radio predicates", async () => {
  let privateReads = 0;
  const resolver = createPrivateValueResolver({ async readPeatixProfile() { privateReads += 1; return {}; }, async readFormProfile() { privateReads += 1; return { form_answers: {} }; } });
  const cases = [["オンライン視聴枠（YouTube） 無料 参加者数 30人", "参加枠", true], ["Connpass", "このイベントは何を見て知りましたか？", true], ["オンライン視聴枠（YouTube） 無料", "参加枠", true], ["オンライン視聴枠（YouTube） 無料 参加者数 30人", "", null], ["Connpass", "", null], ["オンライン登壇枠（Zoom） 無料 先着順 3/3人", "参加枠", null], ["オンライン視聴枠（YouTube） 有料 参加者数 30人", "参加枠", null], ["いいえ", "negative", null], ["X", "other referral", null], ["Connpass / SNS", "ambiguous", null], ["unknown", "unknown", null]];
  for (const [label, question, expected] of cases) {
    assert.equal(await resolver({ provider: "connpass", state: "connpass_join", control: { control: "safe_radio", kind: "radio", label, question, required: true } }), expected, label);
  }
  assert.equal(privateReads, 0);
});

test("Connpass native rejects an unqualified online label", async () => {
  let agentCalls = 0;
  const control = { control: "online_unqualified", kind: "radio", label: "オンライン参加", question: "参加方法", required: true };
  const proposer = createBoundedActionProposer({ repoRoot: "/private/repo", evidenceDir: "/private/evidence", async runAgentRunner(input) {
    agentCalls += 1;
    return { summary: { status: "success", selected_provider: "codex", selected_model: "gpt-5.6-terra" }, value: { control: input.schema.properties.control.enum[0] } };
  } });
  assert.deepEqual(await proposer({ provider: "connpass", target_id: "TARGET1", expected_state: "registered_or_pending", step: 1, observation: { controls: [control] } }), { control: control.control });
  assert.equal(agentCalls, 1);
});

test("Connpass native ignores safe-looking controls outside the exact join page", async () => {
  let agentCalls = 0;
  const control = { control: "online_nonjoin", kind: "radio", label: "オンライン視聴枠（YouTube） 無料 参加者数 30人", question: "参加枠", required: true };
  const proposer = createBoundedActionProposer({ repoRoot: "/private/repo", evidenceDir: "/private/evidence", async runAgentRunner(input) {
    agentCalls += 1;
    return { summary: { status: "success", selected_provider: "codex", selected_model: "gpt-5.6-terra" }, value: { control: input.schema.properties.control.enum[0] } };
  } });
  assert.deepEqual(await proposer({ provider: "connpass", target_id: "TARGET1", expected_state: "registered_or_pending", step: 1, observation: { state: "registration_page", controls: [control] } }), { control: control.control });
  assert.equal(agentCalls, 1);
  const resolver = createPrivateValueResolver({ readPeatixProfile: async () => ({ accept_organizer_privacy: true }), readFormProfile: async () => ({}) });
  assert.equal(await resolver({ provider: "connpass", state: "registration_page", control }), null);
});

test("Connpass native fails closed for duplicate safe viewing options", async () => {
  let agentCalls = 0;
  const controls = [
    { control: "online_one", kind: "radio", label: "オンライン視聴枠（YouTube） 無料 参加者数 30人", question: "参加枠", required: true },
    { control: "online_two", kind: "radio", label: "オンライン視聴枠（YouTube） 無料 参加者数 30人", question: "参加枠", required: true },
  ];
  const proposer = createBoundedActionProposer({ repoRoot: "/private/repo", evidenceDir: "/private/evidence", async runAgentRunner(input) {
    agentCalls += 1;
    return { summary: { status: "success", selected_provider: "codex", selected_model: "gpt-5.6-terra" }, value: { control: input.schema.properties.control.enum[0] } };
  } });
  assert.deepEqual(await proposer({ provider: "connpass", target_id: "TARGET1", expected_state: "registered_or_pending", step: 1, observation: { controls } }), { control: "online_one" });
  assert.equal(agentCalls, 1);
});

test("Connpass native requires known question context", async () => {
  const cases = [
    { control: "online_empty_question", kind: "radio", label: "オンライン視聴枠（YouTube） 無料 参加者数 30人", question: "", required: true },
    { control: "referral_empty_question", kind: "radio", label: "Connpass", question: "", required: true },
    { control: "ack_unknown_question", kind: "radio", label: "はい、わかりました。", question: "未登録質問", required: true },
  ];
  for (const control of cases) {
    let agentCalls = 0;
    const proposer = createBoundedActionProposer({ repoRoot: "/private/repo", evidenceDir: "/private/evidence", async runAgentRunner(input) {
      agentCalls += 1;
      return { summary: { status: "success", selected_provider: "codex", selected_model: "gpt-5.6-terra" }, value: { control: input.schema.properties.control.enum[0] } };
    } });
    assert.deepEqual(await proposer({ provider: "connpass", target_id: "TARGET1", expected_state: "registered_or_pending", step: 1, observation: { controls: [control] } }), { control: control.control });
    assert.equal(agentCalls, 1, control.control);
  }
});

test("Connpass fallback latches the first submit attempt across a path change", async () => {
  let href = "https://tokyo-builders.connpass.com/event/400028/";
  let proposals = 0;
  let operated = 0;
  const page = { url() { return href; } };
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
    connpassWorkflow: { async readProviderState() { return { status: "absent" }; } },
    async inspectControls() { return [{ control: proposals === 0 ? "submit_one" : "submit_two", kind: "button", label: "Register", required: false, submittable: true }]; },
    async proposeAction(input) { proposals += 1; return { purpose: "submit", method: "ax_click", control: input.observation.controls[0].control }; },
    async operateControl() { operated += 1; href = "https://tokyo-builders.connpass.com/event/400028/complete/"; return { status: "success" }; },
    async resolveValue() { return null; },
  });

  const result = await harness.runFallback({ provider: "connpass", candidate: { event_ref: "connpass-event://event/400028" }, page, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/CONNPASSLATCH1", maxSteps: 2, expectedState: "registered_or_pending" });
  assert.equal(result.status, "failed");
  assert.equal(result.safe_reason, "effect_unknown");
  assert.equal(proposals, 2);
  assert.equal(operated, 1);
});

test("bounded proposer accepts Peatix while sending only provider and sanitized controls", async () => {
  let request;
  const proposer = createBoundedActionProposer({
    repoRoot: "/private/repo", evidenceDir: "/private/evidence",
    async runAgentRunner(input) {
      request = input;
      return { summary: { status: "success", selected_provider: "codex", selected_model: "gpt-5.6-terra" }, value: { control: "name_field" } };
    },
  });
  const action = await proposer({ provider: "peatix", target_id: "OWNEDTARGET1", expected_state: "registered_or_pending", step: 1, observation: {
    state: "registration_page", controls: [{ control: "name_field", kind: "input", label: "Name", required: true }],
  } });
  assert.deepEqual(action, { control: "name_field" });
  assert.match(request.prompt, /Peatix/i);
  assert.doesNotMatch(JSON.stringify(request), /event_ref|private-phone|private@example|cookie|password|ws:\/\//i);
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
      if (selector === "input, textarea, select, button, a[role=button], a#confirm-button") {
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

test("page observation derives required from aria and supported required groups", async () => {
  const group = { className: "field required", getAttribute() { return null; }, querySelector() { return null; } };
  const make = (aria, required, closest) => ({ tagName: "INPUT", type: "text", required, dataset: {}, labels: [{ innerText: "Field" }], innerText: "", value: "", getAttribute(name) { return name === "aria-required" ? aria : ""; }, closest });
  const elements = [make("false", false, () => group), make("true", false, () => null), make("false", true, () => null)];
  const controls = await inspectPageControls({ page: { locator() { return { async evaluateAll(callback) { return callback(elements); } }; } } });
  assert.deepEqual(controls.map((control) => control.required), [true, true, true]);
});

test("parent derives the action method and purpose from the selected control kind", async () => {
  const cases = [["text_field", "input", "fill", "ax_fill"], ["notes_field", "textarea", "fill", "ax_fill"], ["ticket_field", "select", "fill", "ax_select"], ["agree_check", "checkbox", "fill", "ax_check"], ["choice_radio", "radio", "fill", "ax_check"], ["submit_button", "button", "submit", "ax_click"], ["submit_link", "link", "submit", "ax_click"]];
  const controls = cases.map(([control, kind]) => ({ control, kind, label: control, required: kind !== "button" && kind !== "link", submittable: kind === "button" })); const calls = [];
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { return { status: "absent" }; } },
    inspectControls: async ({ page }) => [controls.find((item) => item.control === page.page_id)],
    async proposeAction() { return { purpose: "submit", method: "ax_check", control: "text_field" }; },
    async operateControl(input) { calls.push(input.action); return { status: "success" }; },
    async resolveValue() { return "parent-value"; },
  });
  for (const [control, kind] of cases) {
    const result = await harness.performAction({ page: { page_id: control }, action: { purpose: "submit", method: "ax_check", control } });
    assert.deepEqual(result, kind === "link" ? { status: "failed" } : { status: "success" });
  }
  assert.deepEqual(calls, cases.filter(([, kind]) => kind !== "link").map(([control, , purpose, method]) => ({ purpose, method, control })));
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
        { control: "phone_field", kind: "input", label: "Phone", required: true, completed: performed > 0 },
        { control: "register_button", kind: "button", label: "Register", required: false, submittable: true },
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
      return [{ control: "apply_button", kind: "button", label: "Apply", required: false, submittable: true }];
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

test("production harness uses Peatix parent readback for a Peatix fallback", async () => {
  const page = Object.freeze({ page_id: "owned-peatix-page" }); let operated = false;
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
    connpassWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
    peatixWorkflow: { async readProviderState(input) { assert.equal(input.page, page); return operated ? { status: "pending" } : { status: "absent" }; } },
    async inspectControls() { return [{ control: "name_field", kind: "input", label: "Name", required: true }]; },
    async proposeAction() { return { purpose: "submit", method: "ax_click", control: "name_field" }; },
    async operateControl() { operated = true; return { status: "success" }; },
    async resolveValue() { return "parent-owned"; },
  });
  const result = await harness.runFallback({ provider: "peatix", candidate: { event_ref: "peatix-event://event/1" }, page,
    pageWebsocket: "ws://127.0.0.1:9222/devtools/page/OWNEDTARGET1", maxSteps: 10, expectedState: "registered_or_pending" });
  assert.equal(result.status, "completed");
});

test("production harness accepts Meetup and completes only after same-page parent registered readback", async () => {
  const page = Object.freeze({ page_id: "owned-meetup-page" });
  let operated = 0;
  let readbacks = 0;
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
    connpassWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
    peatixWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
    meetupWorkflow: {
      async readProviderState(input) {
        assert.equal(input.page, page);
        readbacks += 1;
        return operated > 0 ? { status: "registered" } : { status: "absent" };
      },
    },
    async inspectControls() {
      return [{ control: "meetup_submit", kind: "button", label: "Attend", required: false, submittable: true }];
    },
    async proposeAction() { return { purpose: "submit", method: "ax_click", control: "meetup_submit" }; },
    async operateControl(input) { assert.equal(input.page, page); operated += 1; return { status: "success" }; },
    async resolveValue() { return null; },
  });

  const result = await harness.runFallback({
    provider: "meetup",
    candidate: { event_ref: "meetup-event://event/315756352" },
    page,
    pageWebsocket: "ws://127.0.0.1:9222/devtools/page/MEETUPTARGET1",
    maxSteps: 2,
    expectedState: "registered_or_pending",
  });
  assert.equal(result.status, "completed");
  assert.equal(result.provider_state.status, "registered");
  assert.equal(operated, 1);
  assert.equal(readbacks, 1);
});

test("provider-neutral resolver returns only parent-owned Peatix/form values", async () => {
  const resolver = createPrivateValueResolver({
    readPeatixProfile: async () => ({ name: "Private Name", email: "private@example.test", family_name_kana: "サクラ", given_name_kana: "テスト", accept_organizer_privacy: true }),
    readFormProfile: async () => ({ phone: "+81 90 0000 0000", form_answers: { "Which role?": "Founder", "Approved option": ["Yes"] } }),
  });
  const control = (kind, label) => ({ control: "safe_control", kind, label, required: true });
  assert.equal(await resolver({ provider: "peatix", control: control("input", "Name") }), "Private Name");
  assert.equal(await resolver({ provider: "peatix", control: control("input", "Email") }), "private@example.test");
  assert.equal(await resolver({ provider: "peatix", control: control("input", "Family name kana") }), "サクラ");
  assert.equal(await resolver({ provider: "peatix", control: control("input", "Phone") }), "+81 90 0000 0000");
  assert.equal(await resolver({ provider: "peatix", control: control("select", "Which role?") }), "Founder");
  assert.equal(await resolver({ provider: "peatix", control: control("input", "Invented question") }), null);
});

test("Eventbrite attendee resolver maps exact incomplete fields to the private profile", async () => {
  let profile = { given_name: "GivenFixture", family_name: "FamilyFixture", email: "EmailFixture" };
  const resolver = createPrivateValueResolver({ readPeatixProfile: async () => profile, readFormProfile: async () => ({ form_answers: {} }) });
  const control = (label, extra = {}) => ({ control: "eventbrite_attendee_field", kind: "input", label, required: true, completed: false, submittable: false, ...extra });
  assert.equal(await resolver({ provider: "eventbrite", control: control("First name") }), "GivenFixture");
  assert.equal(await resolver({ provider: "eventbrite", control: control("Last name") }), "FamilyFixture");
  assert.equal(await resolver({ provider: "eventbrite", control: control("Email") }), "EmailFixture");
  assert.equal(await resolver({ provider: "eventbrite", control: control("Confirm email") }), "EmailFixture");
  for (const [label, extra] of [["first name"], ["First name please"], ["Unknown"], ["First name", { kind: "checkbox" }], ["First name", { completed: true }], ["First name", { required: false }], ["First name", { kind: "button", submittable: true }]]) {
    assert.equal(await resolver({ provider: "eventbrite", control: control(label, extra) }), null, label);
  }
  assert.equal(await resolver({ provider: "peatix", control: control("First name") }), null);
  profile = { given_name: " GivenFixture ", family_name: "FamilyFixture", email: "EmailFixture" };
  assert.equal(await resolver({ provider: "eventbrite", control: control("First name") }), null);
  for (const given_name of [undefined, "x".repeat(2_001)]) {
    profile = { given_name, family_name: "FamilyFixture", email: "EmailFixture" };
    assert.equal(await resolver({ provider: "eventbrite", control: control("First name") }), null);
  }
  profile = null;
  assert.equal(await resolver({ provider: "eventbrite", control: control("Email") }), null);
});

test("provider-neutral resolver rejects a radio option from a different form question", async () => { const resolver = createPrivateValueResolver({ readPeatixProfile: async () => ({ accept_organizer_privacy: false }), readFormProfile: async () => ({ form_answers: { "Role question": "Yes", "Other question": "No" } }) });
  const control = (question) => ({ control: "safe_radio", kind: "radio", label: "Yes", question, required: true });
  assert.equal(await resolver({ provider: "peatix", control: control("Other question") }), null); assert.equal(await resolver({ provider: "peatix", control: control("Role question") }), true);
});

test("provider-neutral resolver supports Peatix confirm Kana names and exact privacy consent label", async () => { const resolver = createPrivateValueResolver({ readPeatixProfile: async () => ({ family_name_kana: "サクラ", given_name_kana: "テスト", name_kanji: "桜 太郎", name_hiragana: "さくら てすと", accept_organizer_privacy: true }), readFormProfile: async () => ({ form_answers: {} }) });
  const control = (kind, label) => ({ control: "safe_control", kind, label, required: true });
  assert.equal(await resolver({ provider: "peatix", control: control("input", "お名前（漢字）") }), "桜 太郎");
  assert.equal(await resolver({ provider: "peatix", control: control("input", "お名前（ひらがな）") }), "さくら てすと");
  assert.equal(await resolver({ provider: "peatix", control: control("input", "お名前（漢字）追加") }), null);
  assert.equal(await resolver({ provider: "peatix", control: control("input", "お名前（ひらがな）追加") }), null);
  assert.equal(await resolver({ provider: "peatix", control: control("input", "lastname_edit") }), "サクラ"); assert.equal(await resolver({ provider: "peatix", control: control("input", "firstname_edit") }), "テスト");
  assert.equal(await resolver({ provider: "peatix", control: { ...control("radio", "確認し同意する。"), question: "主催者のプライバシーポリシーを読んだ・確認した" } }), true);
  assert.equal(await resolver({ provider: "peatix", control: control("radio", "確認し同意する。") }), null); assert.equal(await resolver({ provider: "peatix", control: { ...control("radio", "確認し同意する。"), question: "別の質問" } }), null);
  for (const label of ["Last name", "First name", "姓", "名"]) assert.equal(await resolver({ provider: "peatix", control: control("input", label) }), null);
});

test("production harness rejects unapproved Peatix radio before DOM action", async () => {
  let operated = 0;
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { return { status: "absent" }; } },
    peatixWorkflow: { async readProviderState() { return { status: "absent" }; } },
    inspectControls: async () => [{ control: "unknown_radio", kind: "radio", label: "Invented answer", required: true }],
    proposeAction: async () => ({ purpose: "fill", method: "ax_check", control: "unknown_radio" }),
    operateControl: async () => { operated += 1; return { status: "success" }; },
    resolveValue: createPrivateValueResolver({ readPeatixProfile: async () => ({ accept_organizer_privacy: false }), readFormProfile: async () => ({ form_answers: {} }) }),
  });
  const result = await harness.runFallback({ provider: "peatix", candidate: { event_ref: "peatix-event://event/1" }, page: {},
    pageWebsocket: "ws://127.0.0.1:9222/devtools/page/OWNEDTARGET1", maxSteps: 1, expectedState: "registered_or_pending" });
  assert.equal(result.status, "failed"); assert.equal(result.safe_reason, "agent_action_failed"); assert.equal(operated, 0);
});

test("page observation exposes boolean completion without values", async () => {
  const make = (tagName, type, name, value, checked, innerText = "") => ({ tagName, type, name, value, checked, required: false, dataset: {}, labels: [], innerText, getAttribute(key) { return key === "name" ? name : ""; } });
  const elements = [make("INPUT", "text", "name", "secret-value", false), make("TEXTAREA", "", "notes", "", false), make("SELECT", "", "ticket", "option-1", false), make("INPUT", "checkbox", "agree", "on", true), make("INPUT", "radio", "choice", "one", false), make("INPUT", "radio", "choice", "two", true), make("INPUT", "radio", " choice ", "spaced", false, "Spaced option"), make("INPUT", "radio", "other", "yes", false), make("INPUT", "radio", "", "unnamed-one", false, "Unnamed one"), make("INPUT", "radio", "", "unnamed-two", true, "Unnamed two"), make("BUTTON", "submit", "", "", false, "Submit")];
  const controls = await inspectPageControls({ page: { locator() { return { async evaluateAll(callback) { return callback(elements); } }; } } });
  assert.deepEqual(controls.map(({ kind, completed }) => ({ kind, completed })), [{ kind: "input", completed: true }, { kind: "textarea", completed: false }, { kind: "select", completed: true }, { kind: "checkbox", completed: true }, { kind: "radio", completed: true }, { kind: "radio", completed: true }, { kind: "radio", completed: false }, { kind: "radio", completed: false }, { kind: "radio", completed: false }, { kind: "radio", completed: true }, { kind: "button", completed: false }]);
  assert.equal(Object.hasOwn(controls[0], "value"), false); assert.doesNotMatch(JSON.stringify(controls), /secret-value/);
});

test("bounded proposer excludes completed and optional answer controls from the structured enum", async () => {
  let request; const proposer = createBoundedActionProposer({ repoRoot: "/private/repo", evidenceDir: "/private/evidence", async runAgentRunner(input) { request = input; return { summary: { status: "success", selected_provider: "codex", selected_model: "gpt-5.6-terra" }, value: { control: "submit_button" } }; } });
  const action = await proposer({ provider: "peatix", target_id: "TARGET1", expected_state: "registered_or_pending", step: 1, observation: { controls: [{ control: "name_field", kind: "input", label: "Name", required: true, completed: true }, { control: "optional_notes", kind: "input", label: "Optional notes", required: false, completed: false }, { control: "submit_button", kind: "button", label: "Submit", required: false, completed: false, submittable: true }] } });
  assert.deepEqual(action, { control: "submit_button" }); assert.deepEqual(request.schema.properties.control.enum, ["submit_button"]); assert.match(request.prompt, /incomplete|completed/i); assert.doesNotMatch(JSON.stringify(request), /secret-value/);
});

test("bounded proposer fails closed before the agent when no actionable control remains", async () => {
  let calls = 0; const proposer = createBoundedActionProposer({ repoRoot: "/private/repo", evidenceDir: "/private/evidence", async runAgentRunner() { calls += 1; throw new Error("agent must not run"); } });
  const result = await proposer({ provider: "peatix", target_id: "TARGET1", expected_state: "registered_or_pending", step: 1, observation: { controls: [{ control: "name_field", kind: "input", label: "Name", required: true, completed: true }] } });
  assert.equal(result, null); assert.equal(calls, 0);
});

test("bounded proposer fails closed for a missing or unknown returned control", async () => {
  const proposer = createBoundedActionProposer({ repoRoot: "/private/repo", evidenceDir: "/private/evidence", async runAgentRunner() { return { summary: { status: "success", selected_provider: "codex", selected_model: "gpt-5.6-terra" }, value: { method: "ax_check", control: "invented_control" } }; } });
  const result = await proposer({ provider: "peatix", target_id: "TARGET1", expected_state: "registered_or_pending", step: 1, observation: { controls: [{ control: "required_field", kind: "input", label: "Required", required: true, completed: false }] } });
  assert.equal(result, null);
});

test("production harness rejects a completed fill before resolving or operating DOM", async () => {
  let resolves = 0; let operates = 0; const harness = createProductionBrowserHarness({ lumaWorkflow: { async readProviderState() { return { status: "absent" }; } }, inspectControls: async () => [{ control: "name_field", kind: "input", label: "Name", required: true, completed: true }], proposeAction: async () => ({ purpose: "fill", method: "ax_fill", control: "name_field" }), async operateControl() { operates += 1; return { status: "success" }; }, async resolveValue() { resolves += 1; return "parent-owned"; } });
  const result = await harness.runFallback({ provider: "luma", candidate: { event_ref: "luma-event://event/one" }, page: {}, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/TARGET1", maxSteps: 1, expectedState: "registered_or_pending" });
  assert.equal(result.status, "failed"); assert.equal(result.safe_reason, "agent_action_failed"); assert.equal(resolves, 0); assert.equal(operates, 0);
});

test("bounded proposer separates fallback evidence sequences on one target", async () => {
  const evidence = []; const proposer = createBoundedActionProposer({ repoRoot: "/private/repo", evidenceDir: "/private/evidence", async runAgentRunner(input) { evidence.push(input.evidenceDir); return { summary: { status: "success", selected_provider: "codex", selected_model: "gpt-5.6-terra" }, value: { control: "submit_button" } }; } });
  const base = { provider: "peatix", target_id: "TARGET1", expected_state: "registered_or_pending", observation: { controls: [{ control: "submit_button", kind: "button", label: "Submit", required: false, submittable: true }] } };
  await proposer({ ...base, step: 1 }); await proposer({ ...base, step: 2 }); await proposer({ ...base, step: 1 });
  assert.deepEqual(evidence, ["/private/evidence/target-TARGET1/fallback-1/step-1", "/private/evidence/target-TARGET1/fallback-1/step-2", "/private/evidence/target-TARGET1/fallback-2/step-1"]); assert.equal(evidence.some((value) => /candidate/i.test(value)), false);
});

test("production harness rejects an identical mutating action only after its first success and resets per fallback", async () => {
  let operated = 0; const page = { url() { return "https://peatix.com/sales/event/1/form?token=one"; } }; const harness = createProductionBrowserHarness({ lumaWorkflow: { async readProviderState() { return { status: "absent" }; } }, inspectControls: async () => [{ control: "submit_button", kind: "button", label: "Submit", required: false, submittable: true }], proposeAction: async () => ({ purpose: "submit", method: "ax_click", control: "submit_button" }), async operateControl() { operated += 1; return { status: "success" }; }, async resolveValue() { return null; } });
  const input = { provider: "luma", candidate: { event_ref: "luma-event://event/one" }, page, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/TARGET1", expectedState: "registered_or_pending" };
  const first = await harness.runFallback({ ...input, maxSteps: 2 }); assert.equal(first.safe_reason, "agent_action_failed"); assert.equal(operated, 1);
  const second = await harness.runFallback({ ...input, maxSteps: 1 }); assert.equal(second.safe_reason, "agent_step_limit"); assert.equal(operated, 2);
});

test("production harness allows the same mutating action after an exact page path change", async () => {
  let operated = 0; let href = "https://peatix.com/sales/event/1/form?token=one"; const page = { url() { return href; } }; const harness = createProductionBrowserHarness({ lumaWorkflow: { async readProviderState() { if (operated === 1) href = "https://peatix.com/sales/event/1/confirm#final"; return { status: "absent" }; } }, inspectControls: async () => [{ control: "submit_button", kind: "button", label: "Submit", required: false, submittable: true }], proposeAction: async () => ({ purpose: "submit", method: "ax_click", control: "submit_button" }), async operateControl() { operated += 1; return { status: "success" }; }, async resolveValue() { return null; } });
  const result = await harness.runFallback({ provider: "luma", candidate: { event_ref: "luma-event://event/one" }, page, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/TARGET1", maxSteps: 2, expectedState: "registered_or_pending" });
  assert.equal(result.safe_reason, "agent_step_limit"); assert.equal(operated, 2);
});

test("production harness treats equivalent activation methods as one repeated effect", async () => {
  let operated = 0; let method = "ax_click"; const page = { url() { return "https://peatix.com/sales/event/1/form"; } }; const harness = createProductionBrowserHarness({ lumaWorkflow: { async readProviderState() { return { status: "absent" }; } }, inspectControls: async () => [{ control: "submit_button", kind: "button", label: "Submit", required: false, submittable: true }], proposeAction: async () => ({ purpose: "submit", method, control: "submit_button" }), async operateControl() { operated += 1; method = "coordinate_click"; return { status: "success" }; }, async resolveValue() { return null; } });
  const result = await harness.runFallback({ provider: "luma", candidate: { event_ref: "luma-event://event/one" }, page, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/TARGET1", maxSteps: 2, expectedState: "registered_or_pending" });
  assert.equal(result.safe_reason, "agent_action_failed"); assert.equal(operated, 1);
});

test("inspector scopes submit to the registration form and fails closed for duplicate submits", async () => {
  const registrationForm = {}; const cookieForm = {};
  const make = (element) => ({ dataset: {}, labels: [], innerText: "", options: [], getAttribute() { return ""; }, closest() { return null; }, ...element });
  const elements = [
    make({ tagName: "INPUT", type: "text", required: true, value: "", form: registrationForm, labels: [{ innerText: "Name" }] }),
    make({ tagName: "INPUT", type: "submit", required: false, value: "Register", form: registrationForm }),
    make({ tagName: "INPUT", type: "submit", required: false, value: "Register duplicate", form: registrationForm }),
    make({ tagName: "INPUT", type: "submit", required: false, value: "Accept cookies", form: cookieForm }),
    make({ tagName: "BUTTON", type: "button", required: false, value: "private-button-value", form: registrationForm }),
  ];
  const controls = await inspectPageControls({ page: { locator() { return { async evaluateAll(callback) { return callback(elements); } }; } } });
  assert.equal(controls.find((control) => control.label === "Register").submittable, false);
  assert.equal(controls.find((control) => control.label === "Register duplicate").submittable, false);
  assert.equal(controls.find((control) => control.label === "Accept cookies").submittable, false);
  assert.equal(controls.some((control) => control.label === "private-button-value"), false);
});

test("inspector marks the lone registration submit and rejects a separate cookie submit", async () => {
  const registrationForm = {}; const cookieForm = {};
  const make = (element) => ({ dataset: {}, labels: [], innerText: "", options: [], getAttribute() { return ""; }, closest() { return null; }, ...element });
  const elements = [
    make({ tagName: "INPUT", type: "text", required: true, value: "", form: registrationForm, labels: [{ innerText: "Name" }] }),
    make({ tagName: "INPUT", type: "submit", required: false, value: "Register", form: registrationForm }),
    make({ tagName: "INPUT", type: "submit", required: false, value: "Accept cookies", form: cookieForm }),
  ];
  const controls = await inspectPageControls({ page: { locator() { return { async evaluateAll(callback) { return callback(elements); } }; } } });
  assert.equal(controls.find((control) => control.label === "Register").submittable, true);
  assert.equal(controls.find((control) => control.label === "Accept cookies").submittable, false);
});

test("inspector fails closed when registration and cookie forms both have required answers", async () => {
  const registrationForm = {}; const cookieForm = {};
  const make = (element) => ({ dataset: {}, labels: [], innerText: "", options: [], checked: false, getAttribute() { return ""; }, closest() { return null; }, ...element });
  const elements = [
    make({ tagName: "INPUT", type: "text", required: true, value: "", form: registrationForm, labels: [{ innerText: "Name" }] }),
    make({ tagName: "INPUT", type: "submit", required: false, value: "Register", form: registrationForm }),
    make({ tagName: "INPUT", type: "checkbox", required: true, value: "on", form: cookieForm, labels: [{ innerText: "Accept cookies" }] }),
    make({ tagName: "INPUT", type: "submit", required: false, value: "Save preferences", form: cookieForm }),
  ];
  const controls = await inspectPageControls({ page: { locator() { return { async evaluateAll(callback) { return callback(elements); } }; } } });
  assert.equal(controls.find((control) => control.label === "Register").submittable, false);
  assert.equal(controls.find((control) => control.label === "Save preferences").submittable, false);
});

test("parent rejects an injected submit while a required answer remains incomplete", async () => {
  let operated = 0;
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { return { status: "absent" }; } },
    inspectControls: async () => [
      { control: "name_field", kind: "input", label: "Name", required: true, completed: false },
      { control: "register_button", kind: "button", label: "Register", required: false, submittable: true },
    ],
    async proposeAction() { return { purpose: "submit", method: "ax_click", control: "register_button" }; },
    async operateControl() { operated += 1; return { status: "success" }; },
    async resolveValue() { return null; },
  });
  assert.deepEqual(await harness.performAction({ page: {}, action: { purpose: "submit", method: "ax_click", control: "register_button" } }), { status: "failed" });
  assert.equal(operated, 0);
});

test("same-page duplicate guard rejects a reindexed submit token", async () => {
  let operated = 0; let observations = 0;
  const page = { url() { return "https://peatix.com/sales/event/1/form"; } };
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { return { status: "absent" }; } },
    inspectControls: async () => {
      observations += 1;
      return [
        { control: "name_field", kind: "input", label: "Name", required: true, completed: true },
        { control: observations === 1 ? "submit_one" : "submit_two", kind: "button", label: "Register", required: false, submittable: true },
      ];
    },
    async proposeAction(input) { return { purpose: "submit", method: "ax_click", control: input.observation.controls.find((control) => control.kind === "button").control }; },
    async operateControl() { operated += 1; return { status: "success" }; },
    async resolveValue() { return null; },
  });
  const result = await harness.runFallback({ provider: "luma", candidate: { event_ref: "luma-event://event/one" }, page, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/TARGET1", maxSteps: 2, expectedState: "registered_or_pending" });
  assert.equal(result.safe_reason, "agent_action_failed");
  assert.equal(operated, 1);
});

test("inspector keeps input-submit value as a public label and marks only form submits", async () => {
  const form = {};
  const make = (element) => ({ dataset: {}, labels: [], innerText: "", options: [], getAttribute() { return ""; }, closest() { return null; }, ...element });
  const elements = [
    make({ tagName: "INPUT", type: "text", required: true, value: "private-answer", form, labels: [{ innerText: "Name" }] }),
    make({ tagName: "INPUT", type: "submit", required: false, value: "Register now", form }),
    make({ tagName: "BUTTON", type: "button", required: false, innerText: "Apply", form: null }),
    make({ tagName: "A", type: "", required: false, innerText: "Help", form: null }),
  ];
  const controls = await inspectPageControls({ page: { locator() { return { async evaluateAll(callback) { return callback(elements); } }; } } });
  const submit = controls.find((control) => control.label === "Register now");
  assert.ok(submit);
  assert.equal(submit.kind, "button");
  assert.equal(submit.submittable, true);
  assert.equal(controls.some((control) => control.label === "private-answer"), false);
  assert.equal(controls.find((control) => control.label === "Apply").submittable, false);
  assert.equal(controls.find((control) => control.label === "Help").submittable, false);
});

test("Connpass join inspector normalizes the measured ticket and question DOM", async () => {
  const form = {};
  const referralTitle = { textContent: "必須 このイベントは何を見て知りましたか？" };
  const referralGroup = {
    querySelector(selector) { return selector === ":scope > .question" ? referralTitle : null; },
  };
  const acknowledgementGroup = (textContent) => ({ querySelector(selector) { return selector === ":scope > .question" ? { textContent } : null; } });
  const make = (element) => ({
    dataset: {}, labels: [], innerText: "", options: [], value: "", checked: false,
    required: false, disabled: false, form, getAttribute() { return ""; }, closest() { return null; },
    ...element,
  });
  const participation = make({
    tagName: "INPUT", type: "radio", name: "participation_type",
    labels: [{ innerText: "オンライン視聴枠（YouTube） 無料 参加者数 30人" }],
  });
  const speaker = make({
    tagName: "INPUT", type: "radio", name: "participation_type",
    labels: [{ innerText: "オンライン登壇枠（Zoom） 無料 先着順 3/3人" }],
  });
  const referral = make({
    tagName: "INPUT", type: "radio", name: "q_434349", required: true, labels: [{ innerText: "Connpass" }],
    closest(selector) { return selector === ".question_list" ? referralGroup : null; },
  });
  const acknowledgementOne = make({
    tagName: "INPUT", type: "radio", name: "q_434350", labels: [{ innerText: "はい、わかりました。" }],
    closest(selector) { return selector === ".question_list" ? acknowledgementGroup("任意 speaker acknowledgement") : null; },
  });
  const acknowledgementTwo = make({
    tagName: "INPUT", type: "radio", name: "q_434351", labels: [{ innerText: "はい、わかりました。" }],
    closest(selector) { return selector === ".question_list" ? acknowledgementGroup("任意 second speaker acknowledgement") : null; },
  });
  const submit = make({ tagName: "BUTTON", type: "submit", innerText: "申し込みを確定する" });
  const elements = [participation, speaker, referral, acknowledgementOne, acknowledgementTwo, submit];
  const page = {
    url() { return "https://osaka-driven-dev.connpass.com/event/400028/join/"; },
    locator() { return { async evaluateAll(callback, context) { return callback(elements, context); } }; },
  };
  const pending = await inspectPageControls({ page, provider: "connpass" });
  assert.deepEqual(pending.map(({ label, question, required }) => ({ label, question, required })), [
    { label: "オンライン視聴枠（YouTube） 無料 参加者数 30人", question: "参加枠", required: true },
    { label: "オンライン登壇枠（Zoom） 無料 先着順 3/3人", question: "参加枠", required: true },
    { label: "Connpass", question: "このイベントは何を見て知りましたか？", required: true },
    { label: "はい、わかりました。", question: "speaker acknowledgement", required: false },
    { label: "はい、わかりました。", question: "second speaker acknowledgement", required: false },
    { label: "申し込みを確定する", question: undefined, required: false },
  ]);
  participation.checked = true;
  referral.checked = true;
  const complete = await inspectPageControls({ page, provider: "connpass" });
  assert.equal(complete.find((control) => control.label === "申し込みを確定する").submittable, true);

  for (const [provider, href] of [
    ["connpass", "https://connpass.com/event/400028/join/"],
    ["connpass", "https://osaka-driven-dev.connpass.com/event/400028/join"],
    ["connpass", "https://osaka-driven-dev.connpass.com/event/400028/join/?from=test"],
    ["connpass", "https://connpass.com/event/400028/JOIN/"],
    ["connpass", "https://connpass.com/EVENT/400028/JOIN/"],
    ["luma", "https://osaka-driven-dev.connpass.com/event/400028/join/"],
  ]) {
    const controls = await inspectPageControls({ provider, page: { url() { return href; }, locator() { return { async evaluateAll(callback, context) { return callback(elements, context); } }; } } });
    const viewing = controls.find((control) => control.label.startsWith("オンライン視聴枠"));
    assert.equal(viewing.required, provider === "connpass" && href === "https://connpass.com/event/400028/join/", `${provider} ${href}`);
    assert.equal(viewing.question, provider === "connpass" && href === "https://connpass.com/event/400028/join/" ? "参加枠" : undefined, `${provider} ${href}`);
  }

  const wrongName = { ...participation, name: "other_radio" };
  const wrongNameControls = await inspectPageControls({ provider: "connpass", page: { url() { return "https://osaka-driven-dev.connpass.com/event/400028/join/"; }, locator() { return { async evaluateAll(callback, context) { return callback([wrongName, submit], context); } }; } } });
  assert.equal(wrongNameControls[0].required, false);
  assert.equal(wrongNameControls[0].question, undefined);
});

test("Connpass exact join does not adopt a generic question outside .question_list", async () => {
  const form = {};
  const genericTitle = { textContent: "必須 参加枠" };
  const genericGroup = { querySelector(selector) { return selector === ":scope > .question" ? genericTitle : null; } };
  const outsideQuestion = {
    dataset: {}, labels: [{ innerText: "オンライン視聴枠（YouTube） 無料 参加者数 30人" }], innerText: "", options: [], value: "", checked: false,
    required: true, disabled: false, form, tagName: "INPUT", type: "radio", name: "other_radio",
    getAttribute() { return ""; },
    closest(selector) { return selector === "fieldset, dl.field, [role='group'], .field" ? genericGroup : null; },
  };
  const page = {
    url() { return "https://osaka-driven-dev.connpass.com/event/400028/join/"; },
    locator() { return { async evaluateAll(callback, context) { return callback([outsideQuestion], context); } }; },
  };
  const controls = await inspectPageControls({ page, provider: "connpass" });
  assert.equal(controls[0].question, undefined);
  let agentCalls = 0;
  const proposer = createBoundedActionProposer({ repoRoot: "/private/repo", evidenceDir: "/private/evidence", async runAgentRunner(input) {
    agentCalls += 1;
    return { summary: { status: "success", selected_provider: "codex", selected_model: "gpt-5.6-terra" }, value: { control: input.schema.properties.control.enum[0] } };
  } });
  assert.deepEqual(await proposer({ provider: "connpass", target_id: "TARGET1", expected_state: "registered_or_pending", step: 1, observation: { state: "connpass_join", controls } }), { control: controls[0].control });
  assert.equal(agentCalls, 1);
});

test("bounded proposer exposes pending answers first and only submittable buttons after completion", async () => {
  const enums = [];
  const proposer = createBoundedActionProposer({
    repoRoot: "/private/repo", evidenceDir: "/private/evidence",
    async runAgentRunner(input) {
      enums.push(input.schema.properties.control.enum);
      return { summary: { status: "success", selected_provider: "codex", selected_model: "gpt-5.6-terra" }, value: { control: input.schema.properties.control.enum[0] } };
    },
  });
  const controls = [
    { control: "name_field", kind: "input", label: "Name", required: true, completed: false },
    { control: "phone_field", kind: "input", label: "Phone", required: true, completed: true },
    { control: "cookie_button", kind: "button", label: "Accept all cookies", required: false, submittable: false },
    { control: "apply_button", kind: "button", label: "Apply", required: false, submittable: false },
    { control: "register_button", kind: "button", label: "Register", required: false, submittable: true },
    { control: "help_link", kind: "link", label: "Help", required: false, submittable: false },
  ];
  assert.deepEqual(await proposer({ provider: "peatix", target_id: "TARGET1", expected_state: "registered_or_pending", step: 1, observation: { controls } }), { control: "name_field" });
  assert.deepEqual(await proposer({ provider: "peatix", target_id: "TARGET1", expected_state: "registered_or_pending", step: 2, observation: { controls: controls.map((control) => control.control === "name_field" ? { ...control, completed: true } : control) } }), { control: "register_button" });
  assert.deepEqual(enums, [["name_field"], ["register_button"]]);
});

test("parent rejects arbitrary buttons and links even when an injected action selects them", async () => {
  let operated = 0;
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { return { status: "absent" }; } },
    inspectControls: async () => [
      { control: "cookie_button", kind: "button", label: "Accept all cookies", required: false, submittable: false },
      { control: "help_link", kind: "link", label: "Help", required: false, submittable: false },
    ],
    async proposeAction() { return { purpose: "submit", method: "ax_click", control: "cookie_button" }; },
    async operateControl() { operated += 1; return { status: "success" }; },
    async resolveValue() { return null; },
  });
  const page = {};
  assert.deepEqual(await harness.performAction({ page, action: { purpose: "submit", method: "ax_click", control: "cookie_button" } }), { status: "failed" });
  assert.deepEqual(await harness.performAction({ page, action: { purpose: "submit", method: "ax_click", control: "help_link" } }), { status: "failed" });
  assert.equal(operated, 0);
});

test("known Peatix input button is suppressed while required answers remain and exposed after completion", async () => {
  const make = (element) => ({ dataset: {}, labels: [], innerText: "", options: [], getAttribute() { return ""; }, closest() { return null; }, ...element });
  const form = {}; const required = make({ tagName: "INPUT", type: "text", required: true, value: "", form, labels: [{ innerText: "Name" }] });
  const known = make({ tagName: "INPUT", type: "button", id: "form-submit-button", value: "確認画面へ進む", disabled: false, form: null });
  const elements = [required, known, make({ tagName: "BUTTON", type: "button", innerText: "Accept all cookies" }), make({ tagName: "BUTTON", type: "button", innerText: "Filter" })];
  const page = { url() { return "https://peatix.com/sales/event/5075819/form"; }, locator() { return { async evaluateAll(callback, context) { return callback(elements, context); } }; } };
  let request;
  const proposer = createBoundedActionProposer({ repoRoot: "/private/repo", evidenceDir: "/private/evidence", async runAgentRunner(input) { request = input; return { summary: { status: "success", selected_provider: "codex", selected_model: "gpt-5.6-terra" }, value: { control: input.schema.properties.control.enum[0] } }; } });
  const pending = await inspectPageControls({ page, provider: "peatix" });
  assert.deepEqual(await proposer({ provider: "peatix", target_id: "TARGET1", expected_state: "registered_or_pending", step: 1, observation: { controls: pending } }), { control: pending[0].control });
  required.value = "filled";
  const complete = await inspectPageControls({ page, provider: "peatix" });
  const submit = complete.find((control) => control.label === "確認画面へ進む");
  assert.ok(submit);
  assert.equal(submit.submittable, true);
  assert.deepEqual(await proposer({ provider: "peatix", target_id: "TARGET1", expected_state: "registered_or_pending", step: 2, observation: { controls: complete } }), { control: submit.control });
  assert.deepEqual(request.schema.properties.control.enum, [submit.control]);
});

test("known Peatix submit fails closed for zero, duplicate, wrong-id, disabled, and competing-answer variants", async () => {
  const make = (element) => ({ dataset: {}, labels: [], innerText: "", options: [], getAttribute() { return ""; }, closest() { return null; }, ...element });
  const form = {}; const answer = make({ tagName: "INPUT", type: "text", required: true, value: "filled", form, labels: [{ innerText: "Name" }] });
  const submit = (overrides = {}) => make({ tagName: "INPUT", type: "button", id: "form-submit-button", value: "確認画面へ進む", disabled: false, form: null, ...overrides });
  const cases = [
    ["zero", [answer]],
    ["duplicate", [answer, submit(), submit()]],
    ["wrong-id", [answer, submit({ id: "other-submit" })]],
    ["wrong-form-label", [answer, submit({ value: "チケットを申し込む" })]],
    ["disabled", [answer, submit({ disabled: true })]],
    ["competing-answer-form", [answer, submit(), make({ tagName: "INPUT", type: "checkbox", required: true, value: "on", form: {}, labels: [{ innerText: "Cookie" }] })]],
  ];
  for (const [, elements] of cases) {
    const controls = await inspectPageControls({ provider: "peatix", page: { url() { return "https://peatix.com/sales/event/5075819/form"; }, locator() { return { async evaluateAll(callback, context) { return callback(elements, context); } }; } } });
    assert.equal(controls.some((control) => control.submittable === true), false);
  }
});

test("known submit requires the Peatix provider and canonical form URL", async () => {
  const make = (element) => ({ dataset: {}, labels: [], innerText: "", options: [], getAttribute() { return ""; }, closest() { return null; }, ...element });
  const form = {}; const elements = [
    make({ tagName: "INPUT", type: "text", required: true, value: "filled", form, labels: [{ innerText: "Name" }] }),
    make({ tagName: "INPUT", type: "button", id: "form-submit-button", value: "確認画面へ進む", disabled: false, form: null }),
  ];
  const cases = [["luma", "https://peatix.com/sales/event/5075819/form"], ["peatix", "https://evil.example/sales/event/5075819/form"], ["peatix", "https://peatix.com/event/5075819"]];
  for (const [provider, href] of cases) {
    const controls = await inspectPageControls({ provider, page: { url() { return href; }, locator() { return { async evaluateAll(callback, context) { return callback(elements, context); } }; } } });
    assert.equal(controls.some((control) => control.submittable === true), false);
  }
  const crossEvent = await inspectPageControls({ provider: "peatix", event_id: "5075819", page: { url() { return "https://peatix.com/sales/event/9999999/form"; }, locator() { return { async evaluateAll(callback, context) { return callback(elements, context); } }; } } });
  assert.equal(crossEvent.some((control) => control.submittable === true), false);
});

test("production harness does not reuse a Peatix observation for another provider", async () => {
  let operated = 0; const providers = []; const page = { url() { return "https://peatix.com/sales/event/5075819/form"; } };
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { return { status: "absent" }; } },
    inspectControls: async ({ provider }) => { providers.push(provider); return [{ control: "known_submit", kind: "button", label: "Register", required: false, submittable: provider == null || provider === "peatix" }]; },
    async proposeAction() { return { purpose: "submit", method: "ax_click", control: "known_submit" }; },
    async operateControl() { operated += 1; return { status: "success" }; },
    async resolveValue() { return null; },
  });
  assert.deepEqual(await harness.performAction({ page, provider: "peatix", action: { purpose: "submit", method: "ax_click", control: "known_submit" } }), { status: "success" });
  assert.deepEqual(await harness.performAction({ page, provider: "luma", action: { purpose: "submit", method: "ax_click", control: "known_submit" } }), { status: "failed" });
  assert.equal(operated, 1);
  assert.deepEqual(providers, ["peatix", "luma"]);
});

test("production harness binds a cached observation to the same Peatix candidate event", async () => {
  let operated = 0; const eventIds = []; const page = { url() { return "https://peatix.com/sales/event/5104728/form"; } };
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { return { status: "absent" }; } },
    inspectControls: async ({ event_id }) => { eventIds.push(event_id); return [{ control: "known_submit", kind: "button", label: "Register", required: false, submittable: event_id === "5104728" }]; },
    async proposeAction() { return { purpose: "submit", method: "ax_click", control: "known_submit" }; },
    async operateControl() { operated += 1; return { status: "success" }; },
    async resolveValue() { return null; },
  });
  const action = { purpose: "submit", method: "ax_click", control: "known_submit" };
  assert.deepEqual(await harness.performAction({ page, provider: "peatix", candidate: { event_ref: "peatix-event://event/5104728" }, action }), { status: "success" });
  assert.deepEqual(await harness.performAction({ page, provider: "peatix", candidate: { event_ref: "peatix-event://event/9999999" }, action }), { status: "failed" });
  assert.equal(operated, 1);
  assert.deepEqual(eventIds, ["5104728", "9999999"]);
});

test("known Peatix submit fails closed beside an unlabeled required answer", async () => {
  const make = (element) => ({ dataset: {}, labels: [], innerText: "", options: [], getAttribute() { return ""; }, closest() { return null; }, ...element });
  const form = {}; const elements = [
    make({ tagName: "INPUT", type: "text", required: true, value: "filled", form }),
    make({ tagName: "INPUT", type: "button", id: "form-submit-button", value: "確認画面へ進む", disabled: false, form: null }),
  ];
  const controls = await inspectPageControls({ provider: "peatix", page: { url() { return "https://peatix.com/sales/event/5075819/form"; }, locator() { return { async evaluateAll(callback, context) { return callback(elements, context); } }; } } });
  assert.equal(controls.some((control) => control.submittable === true), false);
});

test("known Peatix confirm anchor is exposed only on the exact same-event confirmation page", async () => {
  const make = (element) => ({ dataset: {}, labels: [], innerText: "", options: [], disabled: false, hidden: false, isConnected: true, style: {}, getBoundingClientRect() { return { width: 120, height: 32 }; }, getAttribute() { return ""; }, closest() { return null; }, ...element });
  const form = {};
  const elements = [
    make({ tagName: "INPUT", type: "text", required: true, value: "filled", form, labels: [{ innerText: "Name" }] }),
    make({ tagName: "A", id: "confirm-button", innerText: "チケットを申し込む", form: null }),
    make({ tagName: "A", id: "help-link", innerText: "Help", form: null }),
    make({ tagName: "BUTTON", type: "button", innerText: "Accept cookies", form: null }),
  ];
  let selector = "";
  const page = {
    url() { return "https://peatix.com/sales/event/5104728/confirm"; },
    locator(value) {
      selector = value;
      return { async evaluateAll(callback, context) { return callback(elements, context); } };
    },
  };
  const controls = await inspectPageControls({ page, provider: "peatix", event_id: "5104728" });
  assert.match(selector, /a#confirm-button/);
  const confirm = controls.find((control) => control.label === "チケットを申し込む");
  assert.ok(confirm);
  assert.equal(confirm.kind, "button");
  assert.equal(confirm.submittable, true);
  assert.equal(controls.find((control) => control.label === "Help").kind, "link");
  assert.equal(controls.find((control) => control.label === "Help").submittable, false);
  assert.equal(controls.find((control) => control.label === "Accept cookies").submittable, false);
});

test("known Peatix confirm anchor fails closed when hidden, detached, CSS-hidden, or zero-sized", async () => {
  const make = (element = {}) => {
    const result = { dataset: {}, labels: [], innerText: "", options: [], disabled: false, hidden: false, isConnected: true, style: {}, ...element };
    result.getBoundingClientRect = () => result.rect || { width: 120, height: 32 };
    result.getAttribute = (name) => name === "hidden" ? (result.hidden ? "" : null) : name === "aria-hidden" ? (result.ariaHidden ? "true" : null) : "";
    result.closest = () => null;
    return result;
  };
  const variants = [
    ["hidden-attribute", { hidden: true }],
    ["aria-hidden", { ariaHidden: true }],
    ["css-display-none", { style: { display: "none" } }],
    ["css-visibility-hidden", { style: { visibility: "hidden" } }],
    ["ancestor-css-display-none", { parentElement: { style: { display: "none" } } }],
    ["zero-size", { rect: { width: 0, height: 0 } }],
    ["detached", { isConnected: false }],
  ];
  for (const [name, overrides] of variants) {
    const form = {};
    const elements = [
      make({ tagName: "INPUT", type: "text", required: true, value: "filled", form, labels: [{ innerText: "Name" }] }),
      make({ tagName: "A", id: "confirm-button", innerText: "チケットを申し込む", form: null, ...overrides }),
    ];
    const controls = await inspectPageControls({ provider: "peatix", event_id: "5104728", page: { url() { return "https://peatix.com/sales/event/5104728/confirm"; }, locator() { return { async evaluateAll(callback, context) { return callback(elements, context); } }; } } });
    assert.equal(controls.some((control) => control.submittable === true), false, name);
  }
});

test("known Peatix confirm fails closed for pending answers and identity, label, state, or uniqueness variants", async () => {
  const make = (element) => ({ dataset: {}, labels: [], innerText: "", options: [], disabled: false, getAttribute() { return ""; }, closest() { return null; }, ...element });
  const baseAnswer = { tagName: "INPUT", type: "text", required: true, value: "filled", form: {}, labels: [{ innerText: "Name" }] };
  const baseConfirm = { tagName: "A", id: "confirm-button", innerText: "チケットを申し込む", form: null };
  const cases = [
    ["pending", { answer: { value: "" } }],
    ["unlabeled", { answer: { labels: [] } }],
    ["zero-form-required-answer", { answer: { form: null } }],
    ["competing-answer-form", { competing: true }],
    ["wrong-provider", { provider: "luma" }],
    ["wrong-host", { href: "https://evil.example/sales/event/5104728/confirm" }],
    ["wrong-path", { href: "https://peatix.com/event/5104728" }],
    ["wrong-event", { href: "https://peatix.com/sales/event/9999999/confirm" }],
    ["wrong-tag", { confirm: { tagName: "BUTTON" } }],
    ["wrong-id", { confirm: { id: "other-confirm" } }],
    ["wrong-label", { confirm: { innerText: "申し込む" } }],
    ["form-associated", { confirm: { form: {} } }],
    ["disabled", { confirm: { disabled: true } }],
    ["duplicate", { duplicate: true }],
  ];
  for (const [name, variant] of cases) {
    const answer = make({ ...baseAnswer, ...(variant.answer || {}) });
    const confirm = make({ ...baseConfirm, ...(variant.confirm || {}) });
    const elements = [answer, ...(variant.competing ? [make({ tagName: "INPUT", type: "text", required: true, value: "filled", form: {}, labels: [{ innerText: "Email" }] })] : []), confirm, ...(variant.duplicate ? [make({ ...baseConfirm })] : [])];
    const href = variant.href || "https://peatix.com/sales/event/5104728/confirm";
    const controls = await inspectPageControls({
      page: { url() { return href; }, locator() { return { async evaluateAll(callback, context) { return callback(elements, context); } }; } },
      provider: variant.provider || "peatix",
      event_id: "5104728",
    });
    assert.equal(controls.some((control) => control.submittable === true), false, name);
  }
});

test("Peatix form submit waits for the bounded same-event confirm navigation before succeeding", async () => {
  let href = "https://peatix.com/sales/event/5104728/form";
  let clicks = 0;
  const waitCalls = [];
  const page = {
    url() { return href; },
    waitForURL(predicate, options) {
      waitCalls.push(options);
      return new Promise((resolve, reject) => {
        const started = Date.now();
        const poll = () => {
          if (predicate(href)) return resolve();
          if (Date.now() - started > 100) return reject(new Error("confirm navigation timeout"));
          setTimeout(poll, 1);
        };
        poll();
      });
    },
  };
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
    peatixWorkflow: { async readProviderState() { return href.endsWith("/confirm") ? { status: "pending" } : { status: "absent" }; } },
    async inspectControls() {
      return href.endsWith("/form")
        ? [{ control: "form_submit", kind: "button", label: "確認画面へ進む", required: false, submittable: true }]
        : [{ control: "confirm_anchor", kind: "button", label: "Review", required: false, submittable: false }];
    },
    async proposeAction(input) {
      return input.observation.controls[0].control === "form_submit"
        ? { purpose: "submit", method: "ax_click", control: "form_submit" }
        : null;
    },
    async operateControl() {
      clicks += 1;
      setTimeout(() => { href = "https://peatix.com/sales/event/5104728/confirm"; }, 5);
      return { status: "success" };
    },
    async resolveValue() { return null; },
  });
  const result = await harness.runFallback({
    provider: "peatix",
    candidate: { event_ref: "peatix-event://event/5104728" },
    page,
    pageWebsocket: "ws://127.0.0.1:9222/devtools/page/PEATIXCONFIRM1",
    maxSteps: 2,
    expectedState: "registered_or_pending",
  });
  assert.equal(result.status, "completed");
  assert.equal(clicks, 1);
  assert.equal(waitCalls.length, 1);
  assert.deepEqual(waitCalls[0], { waitUntil: "domcontentloaded", timeout: 30_000 });
  assert.deepEqual(result.repaired_actions, [{ purpose: "submit", method: "ax_click", control: "form_submit" }]);
});

test("Peatix form submit stops on a cross-event confirm mismatch before readback or final observation", async () => {
  let href = "https://peatix.com/sales/event/5104728/form";
  let observed = 0; let operated = 0; let readbacks = 0; let finalObserved = 0;
  const page = {
    url() { return href; },
    waitForURL(predicate) {
      assert.equal(predicate("https://peatix.com/sales/event/9999999/confirm"), false);
      return Promise.reject(new Error("cross-event confirm"));
    },
  };
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
    peatixWorkflow: { async readProviderState() { readbacks += 1; return { status: "pending" }; } },
    async inspectControls() {
      observed += 1;
      if (!href.endsWith("/form")) finalObserved += 1;
      return [{ control: "form_submit", kind: "button", label: "確認画面へ進む", required: false, submittable: true }];
    },
    async proposeAction() { return { purpose: "submit", method: "ax_click", control: "form_submit" }; },
    async operateControl() { operated += 1; href = "https://peatix.com/sales/event/9999999/confirm"; return { status: "success" }; },
    async resolveValue() { return null; },
  });
  const result = await harness.runFallback({ provider: "peatix", candidate: { event_ref: "peatix-event://event/5104728" }, page, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/PEATIXMISMATCH1", maxSteps: 2, expectedState: "registered_or_pending" });
  assert.equal(result.status, "failed");
  assert.equal(result.safe_reason, "agent_action_failed");
  assert.equal(observed, 1);
  assert.equal(operated, 1);
  assert.equal(readbacks, 0);
  assert.equal(finalObserved, 0);
});

test("Peatix final click settles delayed registration before one completed outcome", async () => {
  let registered = false; let finalReadbackConsumed = false; let clicks = 0; let reads = 0;
  const page = { url() { return "https://peatix.com/sales/event/5104728/confirm"; } };
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
    peatixWorkflow: { async readProviderState() { reads += 1; if (registered && !finalReadbackConsumed) { finalReadbackConsumed = true; return { status: "pending" }; } return { status: "absent" }; } },
    async inspectControls() { return [{ control: "confirm_button", kind: "button", label: "チケットを申し込む", required: false, submittable: true }]; },
    async proposeAction() { return { purpose: "submit", method: "ax_click", control: "confirm_button" }; },
    async operateControl() { clicks += 1; setTimeout(() => { registered = true; }, 10); return { status: "success" }; },
    async resolveValue() { return null; },
  });
  const result = await harness.runFallback({ provider: "peatix", candidate: { event_ref: "peatix-event://event/5104728" }, page, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/PEATIXFINALDELAY1", maxSteps: 2, expectedState: "registered_or_pending" });
  assert.equal(result.status, "completed");
  assert.equal(clicks, 1);
  assert.equal(result.provider_state.status, "pending");
  assert.ok(reads >= 1);
});

test("Connpass final click settles delayed registration before one completed outcome", async () => {
  let registered = false; let clicks = 0; let observations = 0; let proposals = 0; let reads = 0;
  const page = { url() { return "https://tokyo-builders.connpass.com/event/400028/join/"; } };
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
    connpassWorkflow: { async readProviderState() { reads += 1; return registered ? { status: "registered" } : { status: "absent" }; } },
    async inspectControls() { observations += 1; return [{ control: "confirm_button", kind: "button", label: "申し込みを確定する", required: false, submittable: true }]; },
    async proposeAction() { proposals += 1; return { purpose: "submit", method: "ax_click", control: "confirm_button" }; },
    async operateControl() { clicks += 1; setTimeout(() => { registered = true; }, 10); return { status: "success" }; },
    async resolveValue() { return null; },
  });
  const result = await harness.runFallback({ provider: "connpass", candidate: { event_ref: "connpass-event://event/400028" }, page, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/CONNPASSFINALDELAY1", maxSteps: 2, expectedState: "registered_or_pending" });
  assert.equal(result.status, "completed"); assert.equal(result.provider_state.status, "registered"); assert.equal(clicks, 1);
  assert.equal(observations, 1); assert.equal(proposals, 1);
  assert.ok(reads >= 1);
});

test("Connpass final settlement fails closed for identity, label, duplicate, and reader variants", async () => {
  const base = { href: "https://tokyo-builders.connpass.com/event/400028/join/", candidate: { event_ref: "connpass-event://event/400028" }, controls: [{ control: "confirm_button", kind: "button", label: "申し込みを確定する", required: false, submittable: true }], reader: true };
  const variants = [
    ["wrong-url", { href: "https://tokyo-builders.connpass.com/event/400028/" }],
    ["wrong-event", { candidate: { event_ref: "connpass-event://event/400029" } }],
    ["wrong-label", { controls: [{ ...base.controls[0], label: "申し込みを確定" }] }],
    ["non-submittable", { controls: [{ ...base.controls[0], submittable: false }] }],
    ["duplicate", { controls: [base.controls[0], { ...base.controls[0], control: "confirm_two" }] }],
    ["missing-reader", { reader: false }],
  ];
  for (const [name, variant] of variants) {
    let operated = 0;
    const config = { ...base, ...variant };
    const harness = createProductionBrowserHarness({
      lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
      ...(config.reader ? { connpassWorkflow: { async readProviderState() { return { status: "absent" }; } } } : {}),
      async inspectControls() { return config.controls; },
      async operateControl() { operated += 1; return { status: "success" }; }, async resolveValue() { return null; },
      async proposeAction() { return { purpose: "submit", method: "ax_click", control: config.controls[0].control }; },
    });
    assert.deepEqual(await harness.performAction({ provider: "connpass", candidate: config.candidate, page: { url() { return config.href; } }, action: { purpose: "submit", method: "ax_click", control: config.controls[0].control } }), { status: "failed" }, name);
    assert.equal(operated, 0, name);
  }
});

test("Peatix final click fails bounded when provider readback never settles", async () => {
  mock.timers.enable({ apis: ["Date", "setTimeout"] });
  try {
    let readStarted = false; let clicks = 0; let settled = false;
    const page = { url() { return "https://peatix.com/sales/event/5104728/confirm"; } };
    const harness = createProductionBrowserHarness({
      lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
      peatixWorkflow: { async readProviderState() { readStarted = true; return new Promise(() => {}); } },
      async inspectControls() { return [{ control: "confirm_button", kind: "button", label: "チケットを申し込む", required: false, submittable: true }]; },
      async proposeAction() { return { purpose: "submit", method: "ax_click", control: "confirm_button" }; },
      async operateControl() { clicks += 1; return { status: "success" }; },
      async resolveValue() { return null; },
    });
    const resultPromise = harness.runFallback({ provider: "peatix", candidate: { event_ref: "peatix-event://event/5104728" }, page, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/PEATIXNEVER1", maxSteps: 2, expectedState: "registered_or_pending" });
    for (let attempt = 0; attempt < 100 && !readStarted; attempt += 1) await Promise.resolve();
    assert.equal(readStarted, true);
    resultPromise.then(() => { settled = true; });
    mock.timers.tick(30_001);
    for (let attempt = 0; attempt < 20 && !settled; attempt += 1) await Promise.resolve();
    assert.equal(settled, true);
    const result = await resultPromise;
    assert.equal(result.status, "failed");
    assert.equal(result.safe_reason, "effect_unknown");
    assert.equal(clicks, 1);
  } finally {
    mock.timers.reset();
  }
});

test("Connpass final click fails bounded when provider readback never settles", async () => {
  mock.timers.enable({ apis: ["Date", "setTimeout"] });
  try {
    let readStarted = false; let clicks = 0; let settled = false; const page = { url() { return "https://tokyo-builders.connpass.com/event/400028/join/"; } };
    const harness = createProductionBrowserHarness({
      lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
      connpassWorkflow: { async readProviderState() { readStarted = true; return new Promise(() => {}); } },
      async inspectControls() { return [{ control: "confirm_button", kind: "button", label: "申し込みを確定する", required: false, submittable: true }]; },
      async proposeAction() { return { purpose: "submit", method: "ax_click", control: "confirm_button" }; },
      async operateControl() { clicks += 1; return { status: "success" }; },
      async resolveValue() { return null; },
    });
    const resultPromise = harness.runFallback({ provider: "connpass", candidate: { event_ref: "connpass-event://event/400028" }, page, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/CONNPASSFINALNEVER1", maxSteps: 2, expectedState: "registered_or_pending" });
    for (let attempt = 0; attempt < 100 && !readStarted; attempt += 1) await Promise.resolve();
    assert.equal(readStarted, true); resultPromise.then(() => { settled = true; });
    mock.timers.tick(30_001);
    for (let attempt = 0; attempt < 20 && !settled; attempt += 1) await Promise.resolve();
    assert.equal(settled, true);
    const result = await resultPromise;
    assert.equal(result.status, "failed"); assert.equal(result.safe_reason, "effect_unknown"); assert.equal(clicks, 1);
  } finally {
    mock.timers.reset();
  }
});

test("Doorkeeper final submit requires exact identity and registered readback", async () => {
  const candidate = { provider: "doorkeeper", event_ref: "doorkeeper-event://event/1001", canonical_url: "https://tokyo-builders.doorkeeper.jp/events/1001" };
  let registered = false; let clicks = 0; let reads = 0;
  const page = { url() { return candidate.canonical_url; } };
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
    doorkeeperWorkflow: { async readProviderState() { reads += 1; return registered ? (reads === 1 ? { status: "pending" } : { status: "registered" }) : { status: "absent" }; } },
    async inspectControls() { return [{ control: "doorkeeper_submit", kind: "button", label: "申し込む", required: false, submittable: true }]; },
    async proposeAction() { return { purpose: "submit", method: "ax_click", control: "doorkeeper_submit" }; },
    async operateControl() { clicks += 1; registered = true; return { status: "success" }; },
    async resolveValue() { return null; },
  });
  const result = await harness.runFallback({ provider: "doorkeeper", candidate, page, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/DOORKEEPER1", maxSteps: 2, expectedState: "registered_or_pending" });
  assert.equal(result.status, "completed");
  assert.equal(result.provider_state.status, "registered");
  assert.equal(clicks, 1);
  assert.ok(reads >= 1);
});

test("Doorkeeper final submit fails closed for identity, control, duplicate, and workflow variants", async () => {
  const candidate = { provider: "doorkeeper", event_ref: "doorkeeper-event://event/1001", canonical_url: "https://tokyo-builders.doorkeeper.jp/events/1001" };
  const button = { control: "doorkeeper_submit", kind: "button", label: "申し込む", required: false, submittable: true };
  const variants = [
    ["wrong-ref", { candidate: { ...candidate, event_ref: "doorkeeper-event://event/1002" } }],
    ["wrong-url", { href: "https://other.doorkeeper.jp/events/1001" }],
    ["duplicate", { controls: [button, { ...button, control: "doorkeeper_submit_two" }] }],
    ["non-button", { controls: [{ ...button, kind: "link", submittable: false }] }],
    ["non-submittable", { controls: [{ ...button, submittable: false }] }],
    ["wrong-label", { controls: [{ ...button, label: "申込む" }] }],
    ["missing-workflow", { workflow: false }],
  ];
  for (const [name, variant] of variants) {
    let operated = 0;
    const config = { ...variant, controls: variant.controls || [button] };
    const harness = createProductionBrowserHarness({
      lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
      ...(config.workflow === false ? {} : { doorkeeperWorkflow: { async readProviderState() { return { status: "registered" }; } } }),
      async inspectControls() { return config.controls; },
      async proposeAction() { return { purpose: "submit", method: "ax_click", control: config.controls[0].control }; },
      async operateControl() { operated += 1; return { status: "success" }; },
      async resolveValue() { return null; },
    });
    const result = await harness.performAction({ provider: "doorkeeper", candidate: config.candidate || candidate, page: { url() { return config.href || candidate.canonical_url; } }, action: { purpose: "submit", method: "ax_click", control: config.controls[0].control } });
    assert.deepEqual(result, { status: "failed" }, name);
    assert.equal(operated, 0, name);
  }
});

test("Doorkeeper does not complete a required fill from pending readback", async () => {
  const candidate = { provider: "doorkeeper", event_ref: "doorkeeper-event://event/1001", canonical_url: "https://tokyo-builders.doorkeeper.jp/events/1001" };
  let completed = false; let fills = 0; let submits = 0;
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
    doorkeeperWorkflow: { async readProviderState() { return { status: "pending" }; } },
    async inspectControls() { return [
      { control: "name_field", kind: "input", label: "Name", required: true, completed },
      { control: "doorkeeper_submit", kind: "button", label: "申し込む", required: false, submittable: true },
    ]; },
    async proposeAction({ observation }) { return { control: observation.controls.find((control) => control.kind === "input" && !control.completed)?.control || "doorkeeper_submit" }; },
    async operateControl({ control }) { if (control.kind === "input") { fills += 1; completed = true; } else submits += 1; return { status: "success" }; },
    async resolveValue() { return "attendee"; },
  });
  const result = await harness.runFallback({ provider: "doorkeeper", candidate, page: { url() { return candidate.canonical_url; } }, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/DOORKEEPERPENDING1", maxSteps: 1, expectedState: "registered_or_pending" });
  assert.equal(result.status, "failed");
  assert.equal(result.safe_reason, "agent_step_limit");
  assert.equal(fills, 1);
  assert.equal(submits, 0);
});

test("Doorkeeper rejects URL identity variants before any action", async () => {
  const base = { provider: "doorkeeper", event_ref: "doorkeeper-event://event/1001", canonical_url: "https://tokyo-builders.doorkeeper.jp/events/1001" };
  const invalidCanonical = [
    ["query", "https://tokyo-builders.doorkeeper.jp/events/1001?x=1"],
    ["fragment", "https://tokyo-builders.doorkeeper.jp/events/1001#final"],
    ["credentials", "https://user:pass@tokyo-builders.doorkeeper.jp/events/1001"],
    ["port", "https://tokyo-builders.doorkeeper.jp:443/events/1001"],
    ["www", "https://www.doorkeeper.jp/events/1001"],
    ["uppercase-group", "https://Tokyo-builders.doorkeeper.jp/events/1001"],
  ];
  const invalidCurrent = [
    ["query", "https://tokyo-builders.doorkeeper.jp/events/1001?x=1"],
    ["fragment", "https://tokyo-builders.doorkeeper.jp/events/1001#final"],
    ["credentials", "https://user:pass@tokyo-builders.doorkeeper.jp/events/1001"],
    ["port", "https://tokyo-builders.doorkeeper.jp:443/events/1001"],
    ["www", "https://www.doorkeeper.jp/events/1001"],
    ["uppercase-group", "https://Tokyo-builders.doorkeeper.jp/events/1001"],
  ];
  const assertRejected = async (name, candidate, href) => {
    let operated = 0;
    const harness = createProductionBrowserHarness({
      lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
      doorkeeperWorkflow: { async readProviderState() { return { status: "registered" }; } },
      async inspectControls() { return [{ control: "doorkeeper_submit", kind: "button", label: "申し込む", required: false, submittable: true }]; },
      async proposeAction() { return { control: "doorkeeper_submit" }; },
      async operateControl() { operated += 1; return { status: "success" }; },
      async resolveValue() { return null; },
    });
    const result = await harness.performAction({ provider: "doorkeeper", candidate, page: { url() { return href; } }, action: { purpose: "submit", method: "ax_click", control: "doorkeeper_submit" } });
    assert.deepEqual(result, { status: "failed" }, name);
    assert.equal(operated, 0, name);
  };
  for (const [name, canonical_url] of invalidCanonical) await assertRejected(`candidate-${name}`, { ...base, canonical_url }, base.canonical_url);
  for (const [name, href] of invalidCurrent) await assertRejected(`current-${name}`, base, href);
});

test("Doorkeeper final readback is bounded when it never settles", async () => {
  mock.timers.enable({ apis: ["Date", "setTimeout"] });
  try {
    let readStarted = false; let clicks = 0; let settled = false;
    const candidate = { provider: "doorkeeper", event_ref: "doorkeeper-event://event/1001", canonical_url: "https://tokyo-builders.doorkeeper.jp/events/1001" };
    const harness = createProductionBrowserHarness({
      lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
      doorkeeperWorkflow: { async readProviderState() { readStarted = true; return new Promise(() => {}); } },
      async inspectControls() { return [{ control: "doorkeeper_submit", kind: "button", label: "申し込む", required: false, submittable: true }]; },
      async proposeAction() { return { purpose: "submit", method: "ax_click", control: "doorkeeper_submit" }; },
      async operateControl() { clicks += 1; return { status: "success" }; },
      async resolveValue() { return null; },
    });
    const resultPromise = harness.runFallback({ provider: "doorkeeper", candidate, page: { url() { return candidate.canonical_url; } }, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/DOORKEEPERNEVER1", maxSteps: 2, expectedState: "registered_or_pending" });
    for (let attempt = 0; attempt < 100 && !readStarted; attempt += 1) await Promise.resolve();
    assert.equal(readStarted, true);
    resultPromise.then(() => { settled = true; });
    mock.timers.tick(30_001);
    for (let attempt = 0; attempt < 20 && !settled; attempt += 1) await Promise.resolve();
    const result = await resultPromise;
    assert.equal(result.status, "failed");
    assert.equal(result.safe_reason, "effect_unknown");
    assert.equal(clicks, 1);
  } finally {
    mock.timers.reset();
  }
});

test("Doorkeeper ambiguous click still uses readback and never clicks twice", async () => {
  const candidate = { provider: "doorkeeper", event_ref: "doorkeeper-event://event/1001", canonical_url: "https://tokyo-builders.doorkeeper.jp/events/1001" };
  for (const outcome of ["throw", "failed"]) {
    let registered = false; let clicks = 0;
    const harness = createProductionBrowserHarness({
      lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
      doorkeeperWorkflow: { async readProviderState() { return registered ? { status: "registered" } : { status: "absent" }; } },
      async inspectControls() { return [{ control: "doorkeeper_submit", kind: "button", label: "申し込む", required: false, submittable: true }]; },
      async proposeAction() { return { purpose: "submit", method: "ax_click", control: "doorkeeper_submit" }; },
      async operateControl() { clicks += 1; registered = true; if (outcome === "throw") throw new Error("ambiguous click"); return { status: "failed" }; },
      async resolveValue() { return null; },
    });
    const result = await harness.runFallback({ provider: "doorkeeper", candidate, page: { url() { return candidate.canonical_url; } }, pageWebsocket: `ws://127.0.0.1:9222/devtools/page/DOORKEEPER-${outcome}`, maxSteps: 2, expectedState: "registered_or_pending" });
    assert.equal(result.status, "completed", outcome);
    assert.equal(result.provider_state.status, "registered", outcome);
    assert.equal(clicks, 1, outcome);
  }
});

function makeDoorkeeperElement(overrides = {}) {
  const element = {
    tagName: "INPUT", type: "", id: "", name: "", value: "", innerText: "", textContent: "",
    labels: [], required: false, disabled: false, hidden: false, isConnected: true, style: {}, rect: { width: 120, height: 32 },
    dataset: {}, form: null, parentElement: null, ...overrides,
  };
  element.getAttribute = (name) => {
    if (name === "href") return element.href ?? null;
    if (name === "id") return element.id || null;
    if (name === "name") return element.name || null;
    if (name === "type") return element.type || null;
    if (name === "hidden") return element.hidden ? "" : null;
    if (name === "aria-hidden") return element.ariaHidden ? "true" : null;
    return element.attributes && Object.hasOwn(element.attributes, name) ? element.attributes[name] : null;
  };
  element.closest = () => null;
  element.getBoundingClientRect = () => element.rect;
  return element;
}

function makeDoorkeeperForm(id = "new_event_registration") {
  return { id, getAttribute(name) { return name === "id" ? id : null; } };
}

async function inspectDoorkeeperDom(elements, { provider = "doorkeeper", href = "https://techgym.doorkeeper.jp/events/198719", event_id = "198719", selectElements } = {}) {
  let selector = "";
  const page = {
    url() { return href; },
    locator(value) {
      selector = value;
      return { async evaluateAll(callback, context) {
        if (typeof selectElements === "function") return callback(selectElements(value, elements), context);
        const selected = value.includes('a[href="#new_registration_modal"]') ? elements : elements.filter((element) => !(String(element.tagName || "").toLowerCase() === "a" && element.href === "#new_registration_modal"));
        return callback(selected, context);
      } };
    },
  };
  const controls = await inspectPageControls({ page, provider, event_id });
  return { controls, selector };
}

test("non-Doorkeeper inspection keeps the old selector and ordinary controls", async () => {
  const ordinary = makeDoorkeeperElement({ tagName: "BUTTON", innerText: "Register" });
  const doorkeeperAnchor = makeDoorkeeperElement({ tagName: "A", href: "#new_registration_modal", innerText: "申し込む" });
  const { controls, selector } = await inspectDoorkeeperDom([doorkeeperAnchor, ordinary], {
    provider: "luma", href: "https://example.test/register", event_id: "",
    selectElements: (value) => value.includes('a[href="#new_registration_modal"]') ? [doorkeeperAnchor, ordinary] : [ordinary],
  });
  assert.equal(selector, "input, textarea, select, button, a[role=button], a#confirm-button");
  assert.deepEqual(controls.map(({ kind, label, submittable }) => ({ kind, label, submittable })), [{ kind: "button", label: "Register", submittable: false }]);
  const doorkeeper = await inspectDoorkeeperDom([doorkeeperAnchor], { provider: "doorkeeper" });
  assert.equal(doorkeeper.selector, "input, textarea, select, button, a[role=button], a#confirm-button, a[href=\"#new_registration_modal\"]");
});

test("Doorkeeper DOM inspector exposes only the exact visible trigger while modal is closed", async () => {
  const form = makeDoorkeeperForm();
  const elements = [
    makeDoorkeeperElement({ tagName: "A", href: "#new_registration_modal", innerText: "申し込む" }),
    makeDoorkeeperElement({ type: "email", id: "event_registration_email", name: "event_registration[email]", required: true, form, hidden: true, value: "private@example.com" }),
    makeDoorkeeperElement({ type: "submit", name: "commit", value: "申し込む", form, hidden: true }),
  ];
  const { controls, selector } = await inspectDoorkeeperDom(elements);
  assert.match(selector, /a\[href="#new_registration_modal"\]/);
  assert.deepEqual(controls.map(({ kind, label, submittable }) => ({ kind, label, submittable })), [{ kind: "link", label: "申し込む", submittable: false }]);
  assert.doesNotMatch(JSON.stringify(controls), /private@example\.com|event_registration\[email\]/);
});

test("Doorkeeper modal exposes public Email first and the exact single submit only after completion", async () => {
  const form = makeDoorkeeperForm();
  const trigger = makeDoorkeeperElement({ tagName: "A", href: "#new_registration_modal", innerText: "申し込む" });
  const email = makeDoorkeeperElement({ type: "email", id: "event_registration_email", name: "event_registration[email]", required: true, form, value: "" });
  const submit = makeDoorkeeperElement({ type: "submit", name: "commit", value: "申し込む", form });
  let { controls } = await inspectDoorkeeperDom([trigger, email, submit]);
  assert.deepEqual(controls.map(({ kind, label, required, submittable }) => ({ kind, label, required, submittable })), [
    { kind: "link", label: "申し込む", required: false, submittable: false },
    { kind: "input", label: "Email", required: true, submittable: false },
    { kind: "button", label: "申し込む", required: false, submittable: false },
  ]);
  assert.equal(controls.some((control) => control.submittable), false);
  email.value = "private@example.com";
  ({ controls } = await inspectDoorkeeperDom([trigger, email, submit]));
  assert.deepEqual(controls.map(({ kind, label, completed, submittable }) => ({ kind, label, completed, submittable })), [
    { kind: "link", label: "申し込む", completed: false, submittable: false },
    { kind: "input", label: "Email", completed: true, submittable: false },
    { kind: "button", label: "申し込む", completed: false, submittable: true },
  ]);
  assert.doesNotMatch(JSON.stringify(controls), /private@example\.com|event_registration\[email\]|secret|Jane Doe/);
});

test("Doorkeeper trigger requires exact identity, href, label, uniqueness, and visibility", async () => {
  const base = makeDoorkeeperElement({ tagName: "A", href: "#new_registration_modal", innerText: "申し込む" });
  const cases = [
    ["duplicate", [base, makeDoorkeeperElement({ tagName: "A", href: "#new_registration_modal", innerText: "申し込む" })], {}],
    ["wrong-href", [makeDoorkeeperElement({ tagName: "A", href: "#other", innerText: "申し込む" })], {}],
    ["wrong-label", [makeDoorkeeperElement({ tagName: "A", href: "#new_registration_modal", innerText: "参加する" })], {}],
    ["wrong-provider", [base], { provider: "peatix" }],
    ["wrong-page", [base], { href: "https://techgym.doorkeeper.jp/groups/198719" }],
    ["wrong-event", [base], { event_id: "198720" }],
    ["www", [base], { href: "https://www.doorkeeper.jp/events/198719" }],
    ["uppercase", [base], { href: "https://Techgym.doorkeeper.jp/events/198719" }],
    ["query", [base], { href: "https://techgym.doorkeeper.jp/events/198719?x=1" }],
    ["fragment", [base], { href: "https://techgym.doorkeeper.jp/events/198719#final" }],
    ["port", [base], { href: "https://techgym.doorkeeper.jp:443/events/198719" }],
    ["credentials", [base], { href: "https://user:pass@techgym.doorkeeper.jp/events/198719" }],
    ["hidden", [makeDoorkeeperElement({ ...base, hidden: true })], {}],
    ["detached", [makeDoorkeeperElement({ ...base, isConnected: false })], {}],
    ["css-hidden", [makeDoorkeeperElement({ ...base, style: { display: "none" } })], {}],
    ["zero-size", [makeDoorkeeperElement({ ...base, rect: { width: 0, height: 0 } })], {}],
  ];
  for (const [name, elements, context] of cases) {
    const { controls } = await inspectDoorkeeperDom(elements, context);
    assert.equal(controls.some((control) => control.kind === "link" && control.label === "申し込む"), false, name);
  }
});

test("Doorkeeper submit fails closed for duplicate, wrong-form, hidden, and ambiguous required answers", async () => {
  const makeCase = (extra = [], submitOverrides = {}) => {
    const form = makeDoorkeeperForm();
    const email = makeDoorkeeperElement({ type: "email", id: "event_registration_email", name: "event_registration[email]", required: true, form, value: "private@example.com" });
    const submit = makeDoorkeeperElement({ type: "submit", name: "commit", value: "申し込む", form, ...submitOverrides });
    return [makeDoorkeeperElement({ tagName: "A", href: "#new_registration_modal", innerText: "申し込む" }), email, submit, ...extra(form)];
  };
  const cases = [
    ["duplicate-submit", (form) => [makeDoorkeeperElement({ type: "submit", name: "commit", value: "申し込む", form })]],
    ["wrong-form", () => [], { form: makeDoorkeeperForm("cookie_form") }],
    ["hidden-submit", () => [], { hidden: true }],
    ["unlabeled-required-answer", (form) => [makeDoorkeeperElement({ type: "text", required: true, form, value: "secret" })]],
    ["ambiguous-required-answer", (form) => [makeDoorkeeperElement({ type: "text", required: true, form, value: "Jane Doe", labels: [{ innerText: "Email" }] })]],
  ];
  for (const [name, extra, submitOverrides] of cases) {
    const { controls } = await inspectDoorkeeperDom(makeCase(extra, submitOverrides));
    assert.equal(controls.some((control) => control.submittable === true), false, name);
    assert.doesNotMatch(JSON.stringify(controls), /private@example\.com|event_registration\[email\]|secret|Jane Doe/);
  }
});

function makeDoorkeeperAncestor(overrides = {}) {
  const ancestor = { hidden: false, ariaHidden: false, style: {}, computedStyle: null, rect: { width: 120, height: 32 }, parentElement: null, ...overrides };
  ancestor.getAttribute = (name) => name === "hidden" ? (ancestor.hidden ? "" : null) : name === "aria-hidden" ? (ancestor.ariaHidden ? "true" : null) : null;
  ancestor.hasAttribute = (name) => name === "hidden" && ancestor.hidden === true;
  ancestor.getBoundingClientRect = () => ancestor.rect;
  return ancestor;
}

test("Doorkeeper ancestor visibility is scoped to exactly one target control", async () => {
  const variants = [
    ["hidden-attribute", { hidden: true }],
    ["aria-hidden", { ariaHidden: true }],
    ["ancestor-style", { style: { display: "none" } }],
    ["computed-style", { computedStyle: { visibility: "hidden" } }],
    ["ancestor-zero-box", { rect: { width: 0, height: 0 } }],
  ];
  for (const [name, overrides] of variants) {
    for (const target of ["trigger", "email", "submit"]) {
      const form = makeDoorkeeperForm();
      const ancestor = makeDoorkeeperAncestor(overrides);
      const ownerDocument = { defaultView: { getComputedStyle(element) { return element.computedStyle || element.style || {}; } } };
      const controls = [
        ["trigger", makeDoorkeeperElement({ tagName: "A", href: "#new_registration_modal", innerText: "申し込む" })],
        ["email", makeDoorkeeperElement({ type: "email", id: "event_registration_email", name: "event_registration[email]", required: true, form, value: "private@example.com" })],
        ["submit", makeDoorkeeperElement({ type: "submit", name: "commit", value: "申し込む", form })],
      ].map(([kind, element]) => kind === target ? Object.assign(element, { parentElement: ancestor, ownerDocument }) : element);
      const { controls: observed } = await inspectDoorkeeperDom(controls);
      const trigger = observed.find((control) => control.kind === "link" && control.label === "申し込む");
      const email = observed.find((control) => control.label === "Email");
      const submittable = observed.filter((control) => control.submittable === true);
      if (target === "trigger") {
        assert.equal(trigger, undefined, `${name}/${target}`);
      } else if (target === "email") {
        assert.ok(trigger, `${name}/${target}`);
        assert.equal(email, undefined, `${name}/${target}`);
        assert.deepEqual(observed.map(({ kind, label, submittable }) => ({ kind, label, submittable })), [
          { kind: "link", label: "申し込む", submittable: false },
          { kind: "button", label: "申し込む", submittable: false },
        ], `${name}/${target}`);
        assert.equal(submittable.length, 0, `${name}/${target}`);
      } else {
        assert.ok(trigger, `${name}/${target}`);
        assert.deepEqual(email && { kind: email.kind, label: email.label, completed: email.completed, submittable: email.submittable }, { kind: "input", label: "Email", completed: true, submittable: false }, `${name}/${target}`);
        assert.equal(submittable.length, 0, `${name}/${target}`);
        assert.equal(observed.some((control) => control.kind === "button"), false, `${name}/${target}`);
      }
    }
  }
});

function makeDoorkeeperFallbackFixture(proposalForStep) {
  const candidate = { provider: "doorkeeper", event_ref: "doorkeeper-event://event/1001", canonical_url: "https://tokyo-builders.doorkeeper.jp/events/1001" };
  const page = { url() { return candidate.canonical_url; } };
  let modal = false; let email = ""; let registered = false; const operated = [];
  const controls = () => modal ? [
    { control: "doorkeeper_trigger", kind: "link", label: "申し込む", required: false, completed: false, submittable: false },
    { control: "event_email", kind: "input", label: "Email", required: true, completed: Boolean(email), submittable: false },
    { control: "doorkeeper_submit", kind: "button", label: "申し込む", required: false, completed: false, submittable: Boolean(email) },
  ] : [{ control: "doorkeeper_trigger", kind: "link", label: "申し込む", required: false, completed: false, submittable: false }];
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
    doorkeeperWorkflow: { async readProviderState() { return registered ? { status: "registered" } : { status: "absent" }; } },
    async inspectControls() { return controls(); },
    async proposeAction(input) {
      const selected = proposalForStep ? proposalForStep(input.step) : input.observation.controls.find((control) => control.required && !control.completed)?.control || input.observation.controls.find((control) => control.submittable)?.control || input.observation.controls[0].control;
      return { control: selected };
    },
    async operateControl({ control, action, value }) {
      operated.push({ control: control.control, method: action.method });
      if (control.control === "doorkeeper_trigger") modal = true;
      if (control.control === "event_email") email = value;
      if (control.control === "doorkeeper_submit") registered = true;
      return { status: "success" };
    },
    async resolveValue({ control }) { return control.control === "event_email" ? "member@example.test" : null; },
  });
  return { candidate, page, harness, operated };
}

test("Doorkeeper fallback performs trigger, Email fill, and one final submit", async () => {
  const { candidate, page, harness, operated } = makeDoorkeeperFallbackFixture();
  const result = await harness.runFallback({ provider: "doorkeeper", candidate, page, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/DOORKEEPERFLOW1", maxSteps: 3, expectedState: "registered_or_pending" });
  assert.equal(result.status, "completed");
  assert.deepEqual(result.repaired_actions, [
    { purpose: "submit", method: "ax_click", control: "doorkeeper_trigger" },
    { purpose: "fill", method: "ax_fill", control: "event_email" },
    { purpose: "submit", method: "ax_click", control: "doorkeeper_submit" },
  ]);
  assert.deepEqual(operated.map(({ control }) => control), ["doorkeeper_trigger", "event_email", "doorkeeper_submit"]);
});

test("Doorkeeper fallback latches a repeated trigger without blocking fill or final submit", async () => {
  const sequence = ["doorkeeper_trigger", "doorkeeper_trigger", "event_email", "doorkeeper_submit"];
  const { candidate, page, harness, operated } = makeDoorkeeperFallbackFixture((step) => sequence[step - 1]);
  const result = await harness.runFallback({ provider: "doorkeeper", candidate, page, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/DOORKEEPERFLOW2", maxSteps: 4, expectedState: "registered_or_pending" });
  assert.equal(result.status, "completed");
  assert.deepEqual(operated.map(({ control }) => control), ["doorkeeper_trigger", "event_email", "doorkeeper_submit"]);
});

test("Doorkeeper modal trigger rejects wrong provider, identity, label, duplicate, and action", async () => {
  const candidate = { provider: "doorkeeper", event_ref: "doorkeeper-event://event/1001", canonical_url: "https://tokyo-builders.doorkeeper.jp/events/1001" };
  const trigger = { control: "doorkeeper_trigger", kind: "link", label: "申し込む", required: false, completed: false, submittable: false };
  const cases = [
    ["arbitrary", { controls: [{ ...trigger, control: "help_link", label: "Help" }], action: { purpose: "submit", method: "ax_click", control: "help_link" } }],
    ["wrong-provider", { provider: "luma" }],
    ["wrong-identity", { candidate: { ...candidate, event_ref: "doorkeeper-event://event/1002" } }],
    ["wrong-current-url", { href: "https://tokyo-builders.doorkeeper.jp/events/1002" }],
    ["wrong-label", { controls: [{ ...trigger, label: "参加する" }] }],
    ["duplicate", { controls: [trigger, { ...trigger, control: "doorkeeper_trigger_two" }] }],
    ["wrong-action-token", { action: { purpose: "submit", method: "ax_click", control: "missing_trigger" } }],
    ["wrong-action-method", { action: { purpose: "fill", method: "ax_fill", control: trigger.control } }],
  ];
  for (const [name, variant] of cases) {
    let operated = 0; const config = { provider: "doorkeeper", candidate, controls: [trigger], action: { purpose: "submit", method: "ax_click", control: trigger.control }, ...variant };
    const harness = createProductionBrowserHarness({
      lumaWorkflow: { async readProviderState() { return { status: "absent" }; } },
      doorkeeperWorkflow: { async readProviderState() { return { status: "absent" }; } },
      async inspectControls() { return config.controls; }, async proposeAction() { return config.action; },
      async operateControl() { operated += 1; return { status: "success" }; }, async resolveValue() { return null; },
    });
    const result = await harness.performAction({ provider: config.provider, candidate: config.candidate, page: { url() { return config.href || candidate.canonical_url; } }, action: config.action });
    assert.deepEqual(result, { status: "failed" }, name); assert.equal(operated, 0, name);
  }
});

test("Doorkeeper default proposer chooses exact trigger, Email, and final submit without generic links", async () => {
  const trigger = { control: "doorkeeper_trigger", kind: "link", label: "申し込む", required: false, completed: false, submittable: false };
  const email = { control: "event_email", kind: "input", label: "Email", required: true, completed: false, submittable: false };
  const completedEmail = { ...email, completed: true };
  const submit = { control: "doorkeeper_submit", kind: "button", label: "申し込む", required: false, completed: false, submittable: true };
  let agentCalls = 0;
  const proposer = createBoundedActionProposer({ repoRoot: "/private/repo", evidenceDir: "/private/evidence", async runAgentRunner(input) {
    agentCalls += 1;
    return { summary: { status: "success", selected_provider: "codex", selected_model: "gpt-5.6-terra" }, value: { control: input.schema.properties.control.enum[0] } };
  } });
  const base = { provider: "doorkeeper", target_id: "DOORKEEPERDEFAULT1", expected_state: "registered_or_pending" };
  assert.deepEqual(await proposer({ ...base, step: 1, observation: { state: "registration_page", controls: [trigger] } }), { control: "doorkeeper_trigger" });
  assert.deepEqual(await proposer({ ...base, step: 2, observation: { state: "registration_page", controls: [trigger, email] } }), { control: "event_email" });
  assert.deepEqual(await proposer({ ...base, step: 3, observation: { state: "registration_page", controls: [trigger, completedEmail, submit] } }), { control: "doorkeeper_submit" });
  assert.equal(agentCalls, 2);
  assert.equal(await proposer({ ...base, step: 1, observation: { state: "registration_page", controls: [{ control: "help_link", kind: "link", label: "Help", required: false, completed: false, submittable: false }] } }), null);
});

test("Doorkeeper semantic trigger duplicates fail closed even when the duplicate token is invalid", async () => {
  const candidate = { provider: "doorkeeper", event_ref: "doorkeeper-event://event/1001", canonical_url: "https://tokyo-builders.doorkeeper.jp/events/1001" };
  const trigger = { control: "doorkeeper_trigger", kind: "link", label: "申し込む", required: false, completed: false, submittable: false };
  const duplicate = { ...trigger, control: "doorkeeper_invalid" };
  let agentCalls = 0;
  const proposer = createBoundedActionProposer({ repoRoot: "/private/repo", evidenceDir: "/private/evidence", async runAgentRunner() {
    agentCalls += 1;
    return { summary: { status: "success", selected_provider: "codex", selected_model: "gpt-5.6-terra" }, value: { control: trigger.control } };
  } });
  const observation = { state: "registration_page", controls: [trigger, duplicate] };
  assert.equal(await proposer({ provider: "doorkeeper", target_id: "DOORKEEPERDUPLICATE1", expected_state: "registered_or_pending", step: 1, observation }), null);
  assert.equal(agentCalls, 0);
  let operated = 0;
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { return { status: "absent" }; } },
    doorkeeperWorkflow: { async readProviderState() { return { status: "absent" }; } },
    async inspectControls() { return observation.controls; },
    async proposeAction() { return { control: trigger.control }; },
    async operateControl() { operated += 1; return { status: "success" }; },
    async resolveValue() { return null; },
  });
  const result = await harness.performAction({ provider: "doorkeeper", candidate, page: { url() { return candidate.canonical_url; } }, action: { purpose: "submit", method: "ax_click", control: trigger.control } });
  assert.deepEqual(result, { status: "failed" });
  assert.equal(operated, 0);
});

function makeEventbriteCta(overrides = {}) {
  const element = {
    tagName: "BUTTON",
    type: "button",
    innerText: "Get tickets",
    disabled: false,
    hidden: false,
    isConnected: true,
    style: {},
    dataset: {},
    ownerDocument: { defaultView: { getComputedStyle() { return {}; } } },
    parentElement: null,
    getAttribute(name) { return name === "data-testid" ? "conversion-bar-checkout-button" : null; },
    hasAttribute(name) { return name === "hidden" && this.hidden === true; },
    getBoundingClientRect() { return this.rect || { width: 120, height: 32 }; },
    ...overrides,
  };
  return element;
}

test("Eventbrite inspector binds the unique visible top CTA to the exact candidate page", async () => {
  const candidate = {
    provider: "eventbrite",
    event_ref: "eventbrite-event://event/1901",
    canonical_url: "https://www.eventbrite.com/e/tokyo-free-event-tickets-1901",
  };
  const inspect = async (elements, href = candidate.canonical_url, eventId = "1901", canonicalUrl = candidate.canonical_url) => inspectPageControls({
    provider: "eventbrite",
    event_id: eventId,
    canonical_url: canonicalUrl,
    page: { url() { return href; }, locator() { return { async evaluateAll(callback, context) { return callback(elements, context); } }; } },
  });
  const valid = await inspect([makeEventbriteCta(), makeEventbriteCta({ tagName: "BUTTON", innerText: "Reserve a spot" })]);
  assert.deepEqual(valid, []);
  for (const [name, duplicate] of [
    ["visible-fuzzy", makeEventbriteCta({ innerText: "Get tickets now" })],
    ["visible-disabled", makeEventbriteCta({ disabled: true })],
  ]) {
    assert.deepEqual(await inspect([makeEventbriteCta(), duplicate]), [], name);
  }
  const single = await inspect([makeEventbriteCta()]);
  assert.equal(single.length, 1);
  assert.deepEqual({ kind: single[0].kind, label: single[0].label, submittable: single[0].submittable }, { kind: "button", label: "Get tickets", submittable: true });
  const overflow = [makeEventbriteCta(), ...Array.from({ length: 99 }, () => makeEventbriteCta({ hidden: true })), makeEventbriteCta()];
  assert.equal(overflow.length, 101);
  assert.deepEqual(await inspect(overflow), [], "eventbrite-overflow-duplicate");
  for (const [name, element, href, id, url] of [
    ["fuzzy-label", makeEventbriteCta({ innerText: "Get tickets now" })],
    ["hidden", makeEventbriteCta({ hidden: true })],
    ["disabled", makeEventbriteCta({ disabled: true })],
    ["wrong-tag", makeEventbriteCta({ tagName: "A" })],
    ["wrong-type", makeEventbriteCta({ type: "submit" })],
    ["wrong-event", makeEventbriteCta(), candidate.canonical_url, "1902", candidate.canonical_url],
    ["wrong-page", makeEventbriteCta(), "https://www.eventbrite.com/e/other-tickets-1901"],
    ["query-page", makeEventbriteCta(), `${candidate.canonical_url}?aff=1`],
  ]) {
    assert.deepEqual(await inspect([element], href, id, url), [], name);
  }
});

test("Eventbrite CTA action clicks once and succeeds only on the exact checkout frame", async () => {
  const candidate = {
    provider: "eventbrite",
    event_ref: "eventbrite-event://event/1901",
    canonical_url: "https://www.eventbrite.com/e/tokyo-free-event-tickets-1901",
  };
  const trigger = { control: "eventbrite_checkout_1901", kind: "button", label: "Get tickets", required: false, completed: false, submittable: true };
  const run = async ({ frameUrls, pageUrls, action = { purpose: "submit", method: "ax_click", control: trigger.control }, controls = [trigger], provider = "eventbrite", candidateValue = candidate } = {}) => {
    let operated = 0; let resolved = 0; let reads = 0; let pageReads = 0;
    const page = {
      url() {
        pageReads += 1;
        return typeof pageUrls === "function" ? pageUrls(pageReads) : pageUrls || candidate.canonical_url;
      },
      frames() {
        reads += 1;
        const urls = typeof frameUrls === "function" ? frameUrls(reads) : frameUrls || [];
        return urls.map((entry) => {
          const frame = typeof entry === "string" ? { href: entry } : entry;
          return { url() { return frame.href; }, parentFrame() { return frame.main === true ? null : {}; } };
        });
      },
    };
    const harness = createProductionBrowserHarness({
      lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
      async inspectControls() { return controls; },
      async proposeAction() { return action; },
      async operateControl() { operated += 1; return { status: "success" }; },
      async resolveValue() { resolved += 1; return "private-value"; },
    });
    mock.timers.enable({ apis: ["Date", "setTimeout"] });
    try {
      const resultPromise = harness.performAction({ provider, candidate: candidateValue, page, action });
      let settled = false;
      resultPromise.then(() => { settled = true; });
      for (let attempt = 0; attempt < 1_300 && !settled; attempt += 1) {
        await Promise.resolve();
        mock.timers.tick(25);
      }
      const result = await resultPromise;
      return { result, operated, resolved };
    } finally {
      mock.timers.reset();
    }
  };
  const success = await run({ frameUrls: ["https://www.eventbrite.com/checkout-external?eid=1901"] });
  assert.deepEqual(success.result, { status: "success" });
  assert.equal(success.operated, 1);
  assert.equal(success.resolved, 0);
  const mainOnly = await run({ frameUrls: [{ href: "https://www.eventbrite.com/checkout-external?eid=1901", main: true }] });
  assert.deepEqual(mainOnly.result, { status: "failed" }, "main-frame-only");
  assert.equal(mainOnly.operated, 1);
  const parentNavigated = await run({
    frameUrls: ["https://www.eventbrite.com/checkout-external?eid=1901"],
    pageUrls: (poll) => poll <= 3 ? candidate.canonical_url : "https://www.eventbrite.com/checkout-external?eid=1901",
  });
  assert.deepEqual(parentNavigated.result, { status: "failed" }, "parent-navigation");
  assert.equal(parentNavigated.operated, 1);
  for (const [name, frameUrls] of [
    ["missing", []],
    ["wrong-origin", ["https://evil.example/checkout-external?eid=1901"]],
    ["wrong-path", ["https://www.eventbrite.com/checkout?eid=1901"]],
    ["wrong-event", ["https://www.eventbrite.com/checkout-external?eid=1902"]],
    ["exact-and-wrong-event", ["https://www.eventbrite.com/checkout-external?eid=1901", "https://www.eventbrite.com/checkout-external?eid=1902"]],
    ["duplicate", ["https://www.eventbrite.com/checkout-external?eid=1901", "https://www.eventbrite.com/checkout-external?eid=1901"]],
  ]) {
    const { result, operated } = await run({ frameUrls });
    assert.deepEqual(result, { status: "failed" }, name);
    assert.equal(operated, 1, name);
  }
  const unstable = await run({ frameUrls: (poll) => poll === 1
    ? ["https://www.eventbrite.com/checkout-external?eid=1901"]
    : ["https://www.eventbrite.com/checkout-external?eid=1901", "https://www.eventbrite.com/checkout-external?eid=1901"] });
  assert.deepEqual(unstable.result, { status: "failed" }, "frame-count-grew-after-first-poll");
  assert.equal(unstable.operated, 1);
  const lateDuplicate = await run({ frameUrls: (poll) => poll <= 2
    ? ["https://www.eventbrite.com/checkout-external?eid=1901"]
    : ["https://www.eventbrite.com/checkout-external?eid=1901", "https://www.eventbrite.com/checkout-external?eid=1901"] });
  assert.deepEqual(lateDuplicate.result, { status: "failed" }, "frame-count-grew-after-second-poll");
  assert.equal(lateDuplicate.operated, 1);
  for (const [name, action, provider, candidateValue, controls] of [
    ["wrong-action", { purpose: "fill", method: "ax_fill", control: trigger.control }],
    ["wrong-token", { purpose: "submit", method: "ax_click", control: "other_button" }],
    ["mixed-fuzzy-semantic", { purpose: "submit", method: "ax_click", control: trigger.control }, "eventbrite", candidate, [trigger, { ...trigger, control: "eventbrite_checkout_1902", label: "Get tickets now" }]],
    ["duplicate-semantic", { purpose: "submit", method: "ax_click", control: trigger.control }, "eventbrite", candidate, [trigger, { ...trigger, control: "eventbrite_checkout_1902" }]],
    ["wrong-provider", { purpose: "submit", method: "ax_click", control: trigger.control }, "luma"],
  ]) {
    const { result, operated } = await run({ frameUrls: ["https://www.eventbrite.com/checkout-external?eid=1901"], action, provider, candidateValue, controls });
    assert.deepEqual(result, { status: "failed" }, name);
    assert.equal(operated, 0, name);
  }
});

function makeEventbriteTicketElement({ tagName = "DIV", type = "", testId = "", innerText = "", ariaLabel = "", disabled = false, hidden = false, children = [], ...overrides } = {}) {
  const element = {
    tagName, type, innerText, textContent: innerText, disabled, hidden, isConnected: true,
    style: {}, dataset: testId ? { testid: testId } : {}, parentElement: null, children,
    getAttribute(name) {
      if (name === "data-testid") return testId;
      if (name === "aria-label") return ariaLabel;
      return null;
    },
    hasAttribute(name) { return name === "hidden" && hidden === true; },
    getBoundingClientRect() { return hidden ? { width: 0, height: 0 } : { width: 120, height: 32 }; },
    querySelectorAll() { return children.flatMap((child) => [child, ...(child.querySelectorAll ? child.querySelectorAll("*") : [])]); },
    ownerDocument: { defaultView: { getComputedStyle() { return {}; } } },
    ...overrides,
  };
  for (const child of children) child.parentElement = element;
  return element;
}

test("Eventbrite inspector exposes the exact free ticket Register control from the matching checkout child frame", async () => {
  const candidate = {
    provider: "eventbrite",
    event_ref: "eventbrite-event://event/1901",
    canonical_url: "https://www.eventbrite.com/e/tokyo-free-event-tickets-1901",
  };
  const increase = makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: "eds-stepper-increase-button", ariaLabel: "Increase quantity" });
  const decrease = makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: "eds-stepper-decrease-button", ariaLabel: "Decrease quantity", disabled: true });
  const quantity = makeEventbriteTicketElement({ testId: "eds-stepper-quantity", innerText: "1" });
  const stepper = makeEventbriteTicketElement({ testId: "eds-stepper", children: [decrease, quantity, increase] });
  const price = makeEventbriteTicketElement({ testId: "ticket-price__price", innerText: "Free" });
  const card = makeEventbriteTicketElement({ testId: "ticket-display-card-content-full-size", innerText: "General Admission", children: [stepper, price] });
  let primaryTestId = "eds-modal__primary-button";
  const primary = makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: "eds-modal__primary-button", innerText: "Register", getAttribute(name) {
    if (name === "data-testid") return primaryTestId;
    if (name === "aria-label") return "Register";
    return null;
  } });
  let ticketVisible = true; let operated = 0; let operatedFrame; let frameExtras = [];
  let frameInspectReads = 0; let mutationMode = "";
  let pageHref = candidate.canonical_url; let frameHref = "https://www.eventbrite.com/checkout-external?eid=1901"; let pageFrames;
  const frameElements = () => {
    frameInspectReads += 1;
    if (mutationMode && frameInspectReads === 2) {
      if (mutationMode === "paid") card.innerText = "General Admission Free 1,000円";
      if (mutationMode === "duplicate") frameExtras = [makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: primary.dataset.testid, innerText: "Register" })];
      if (mutationMode === "disabled") primary.disabled = true;
      if (mutationMode === "drift-page") pageHref = "https://www.eventbrite.com/e/tokyo-free-event-tickets-1902";
      if (mutationMode === "drift-frame") pageFrames = [frame, frame];
      if (mutationMode === "drift-eid") frameHref = "https://www.eventbrite.com/checkout-external?eid=1902";
    }
    return ticketVisible ? [card, stepper, quantity, increase, decrease, price, primary, ...frameExtras] : [primary];
  };
  const frame = {
    url() { return frameHref; },
    parentFrame() { return {}; },
    locator() { return { async evaluateAll(callback, context) { return callback(frameElements(), context); } }; },
  };
  pageFrames = [frame];
  const page = {
    url() { return pageHref; },
    frames() { return pageFrames; },
    locator() { return { async evaluateAll(callback, context) { return callback([], context); } }; },
  };
  for (const marker of ["$10", "JPY 1,000", "USD 10", "1,000円", "1000 円", "1,000 JPY", "10 USD", "cash", "paid", "door fee", "minimum purchase", "会場払い", "当日払い", "有料"]) {
    card.innerText = `General Admission Free ${marker}`;
    assert.deepEqual(await inspectPageControls({ page, provider: "eventbrite", event_id: "1901", canonical_url: candidate.canonical_url }), [], marker);
  }
  card.innerText = "General Admission Free";
  for (const [name, style] of [
    ["element-display-none", { display: "none" }],
    ["element-visibility-hidden", { visibility: "hidden" }],
    ["element-visibility-collapse", { visibility: "collapse" }],
    ["element-content-visibility-hidden", { contentVisibility: "hidden" }],
    ["element-opacity-zero", { opacity: "0" }],
  ]) {
    primary.style = style;
    assert.deepEqual(await inspectPageControls({ page, provider: "eventbrite", event_id: "1901", canonical_url: candidate.canonical_url }), [], name);
    primary.style = {};
  }
  for (const [name, style] of [
    ["ancestor-display-none", { display: "none" }],
    ["ancestor-visibility-hidden", { visibility: "hidden" }],
    ["ancestor-visibility-collapse", { visibility: "collapse" }],
    ["ancestor-content-visibility-hidden", { contentVisibility: "hidden" }],
    ["ancestor-opacity-zero", { opacity: "0" }],
  ]) {
    primary.parentElement = { style, parentElement: null };
    assert.deepEqual(await inspectPageControls({ page, provider: "eventbrite", event_id: "1901", canonical_url: candidate.canonical_url }), [], name);
    primary.parentElement = null;
  }
  const ownerDocument = primary.ownerDocument;
  primary.ownerDocument = { defaultView: { getComputedStyle() { return { opacity: "0" }; } } };
  assert.deepEqual(await inspectPageControls({ page, provider: "eventbrite", event_id: "1901", canonical_url: candidate.canonical_url }), [], "computed-opacity-zero");
  primary.ownerDocument = ownerDocument;
  card.innerText = "General Admission Free";
  primaryTestId = "EDS-MODAL__PRIMARY-BUTTON";
  assert.deepEqual(await inspectPageControls({ page, provider: "eventbrite", event_id: "1901", canonical_url: candidate.canonical_url }), [], "case-sensitive-primary-testid");
  primaryTestId = "eds-modal__primary-button";
  primary.disabled = true;
  assert.deepEqual(await inspectPageControls({ page, provider: "eventbrite", event_id: "1901", canonical_url: candidate.canonical_url }), [], "disabled-primary");
  primary.disabled = false;
  for (const [index, duplicate] of [
    makeEventbriteTicketElement({ testId: card.dataset.testid, innerText: "Duplicate card" }),
    makeEventbriteTicketElement({ testId: stepper.dataset.testid }),
    makeEventbriteTicketElement({ testId: quantity.dataset.testid, innerText: "1" }),
    makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: increase.dataset.testid, ariaLabel: "Increase quantity" }),
    makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: decrease.dataset.testid, ariaLabel: "Decrease quantity", disabled: true }),
    makeEventbriteTicketElement({ testId: price.dataset.testid, innerText: "Free" }),
    makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: primary.dataset.testid, innerText: "Register" }),
  ].entries()) {
    frameExtras = [duplicate];
    if (index === 1 || index === 5) { card.children.push(duplicate); duplicate.parentElement = card; }
    if (index >= 2 && index <= 4) { stepper.children.push(duplicate); duplicate.parentElement = stepper; }
    assert.deepEqual(await inspectPageControls({ page, provider: "eventbrite", event_id: "1901", canonical_url: candidate.canonical_url }), [], `same-testid-duplicate-${index}-${duplicate.dataset.testid}`);
    if (index === 1 || index === 5) card.children.pop();
    if (index >= 2 && index <= 4) stepper.children.pop();
  }
  frameExtras = [];
  for (const duplicate of [
    makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: primary.dataset.testid, innerText: "Register now" }),
    makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: primary.dataset.testid, innerText: "Register", hidden: true }),
    makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: primary.dataset.testid, innerText: "Register", disabled: true }),
  ]) {
    frameExtras = [duplicate];
    assert.deepEqual(await inspectPageControls({ page, provider: "eventbrite", event_id: "1901", canonical_url: candidate.canonical_url }), [], "primary-candidate-duplicate");
  }
  frameExtras = [];
  const controls = await inspectPageControls({ page, provider: "eventbrite", event_id: "1901", canonical_url: candidate.canonical_url });
  assert.deepEqual(controls, [{ control: "eventbrite_ticket_register_1901", kind: "button", label: "Register", required: false, completed: false, submittable: true }]);
  card.innerText = "General Admission Free — USD tickets only";
  assert.deepEqual(await inspectPageControls({ page, provider: "eventbrite", event_id: "1901", canonical_url: candidate.canonical_url }), controls, "currency-code-without-amount-is-not-paid");
  card.innerText = "General Admission Free";
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("readback must not run"); } },
    async inspectControls(input) { return inspectPageControls(input); },
    async proposeAction() { return { control: controls[0].control }; },
    async operateControl(input) { operated += 1; operatedFrame = input.frame; ticketVisible = false; return { status: "success" }; },
    async resolveValue() { throw new Error("private value must not resolve"); },
  });
  mock.timers.enable({ apis: ["Date", "setTimeout"] });
  try {
    const resultPromise = harness.performAction({ provider: "eventbrite", candidate, page, action: { purpose: "submit", method: "ax_click", control: controls[0].control } });
    let settled = false; resultPromise.then(() => { settled = true; });
    for (let attempt = 0; attempt < 1_300 && !settled; attempt += 1) { await Promise.resolve(); mock.timers.tick(25); }
    assert.deepEqual(await resultPromise, { status: "success" });
  } finally { mock.timers.reset(); }
  assert.equal(operated, 1);
  assert.equal(operatedFrame, frame);

  for (const mutation of ["paid", "duplicate", "disabled", "drift-page", "drift-frame", "drift-eid"]) {
    ticketVisible = true;
    card.innerText = "General Admission Free";
    primary.disabled = false;
    frameExtras = [];
    frameInspectReads = 0;
    pageHref = candidate.canonical_url;
    frameHref = "https://www.eventbrite.com/checkout-external?eid=1901";
    pageFrames = [frame];
    mutationMode = mutation;
    let mutationOperated = 0;
    const mutationHarness = createProductionBrowserHarness({
      lumaWorkflow: { async readProviderState() { throw new Error("readback must not run"); } },
      async inspectControls(input) { return inspectPageControls(input); },
      async proposeAction() { return { control: controls[0].control }; },
      async operateControl() { mutationOperated += 1; ticketVisible = false; return { status: "success" }; },
      async resolveValue() { throw new Error("private value must not resolve"); },
    });
    mock.timers.enable({ apis: ["Date", "setTimeout"] });
    try {
      const mutationPromise = mutationHarness.performAction({ provider: "eventbrite", candidate, page, action: { purpose: "submit", method: "ax_click", control: controls[0].control } });
      let settled = false; mutationPromise.then(() => { settled = true; });
      for (let attempt = 0; attempt < 1_300 && !settled; attempt += 1) { await Promise.resolve(); mock.timers.tick(25); }
      assert.deepEqual(await mutationPromise, { status: "failed" }, `pre-operate-${mutation}`);
    } finally { mock.timers.reset(); }
    assert.equal(mutationOperated, 0, `pre-operate-${mutation}-must-not-click`);
    mutationMode = "";
  }
});

test("Eventbrite attendee inspector exposes only the exact required fields after the ticket card is gone", async () => {
  const candidate = { provider: "eventbrite", event_ref: "eventbrite-event://event/1901", canonical_url: "https://www.eventbrite.com/e/tokyo-free-event-tickets-1901" };
  const field = (name, type = "text", value = "") => makeEventbriteTicketElement({ tagName: "INPUT", type, name, required: true, value });
  const first = field("buyer.N-first_name", "text", " Given ");
  const last = field("buyer.N-last_name");
  const email = field("buyer.N-email", "email", "person@example.test");
  const confirm = field("buyer.confirmEmailAddress", "email");
  const marketing = field("marketing_opt_in", "checkbox"); marketing.required = false;
  const primary = makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: "eds-modal__primary-button", innerText: "Register" });
  const base = [first, last, email, confirm, marketing, primary];
  let frameElements = base;
  const frame = { url() { return "https://www.eventbrite.com/checkout-external?eid=1901"; }, parentFrame() { return {}; }, locator() { return { async evaluateAll(callback, context) { return callback(frameElements, context); } }; } };
  const page = { url() { return candidate.canonical_url; }, frames() { return [frame]; }, locator() { return { async evaluateAll(callback, context) { return callback([], context); } }; } };
  const inspect = () => inspectPageControls({ page, provider: "eventbrite", event_id: "1901", canonical_url: candidate.canonical_url });
  const expected = [{ control: "eventbrite_attendee_first_name_1901", kind: "input", label: "First name", required: true, completed: true, submittable: false }, { control: "eventbrite_attendee_last_name_1901", kind: "input", label: "Last name", required: true, completed: false, submittable: false }, { control: "eventbrite_attendee_email_1901", kind: "input", label: "Email", required: true, completed: true, submittable: false }, { control: "eventbrite_attendee_confirm_email_1901", kind: "input", label: "Confirm email", required: true, completed: false, submittable: false }];
  assert.deepEqual(await inspect(), expected);
  assert.doesNotMatch(JSON.stringify(await inspect()), /Given|person@example\.test|buyer\.(?:1|N)/);
  for (const [name, duplicate] of [["hidden-duplicate", { ...first, hidden: true }], ["disabled-duplicate", { ...first, disabled: true }], ["detached-duplicate", { ...first, isConnected: false }]]) {
    frameElements = [...base, duplicate];
    assert.deepEqual(await inspect(), [], name);
  }
  frameElements = base;
  for (const [name, extra] of [
    ["ticket-card-remains", makeEventbriteTicketElement({ testId: "ticket-display-card-content-full-size" })],
    ["unknown-required", makeEventbriteTicketElement({ tagName: "SELECT", name: "unknown", required: true })],
    ["duplicate", field("buyer.N-first_name")],
    ["wrong-type", { ...first, type: "email" }],
    ["wrong-tag", { ...first, tagName: "SELECT" }],
    ["wrong-name", { ...first, name: "buyer.N-middle_name" }],
    ["hidden", { ...first, hidden: true }],
    ["disabled", { ...first, disabled: true }],
  ]) {
    frameElements = ["duplicate", "ticket-card-remains", "unknown-required"].includes(name) ? [...base, extra] : [extra, last, email, confirm, marketing, primary];
    assert.deepEqual(await inspect(), [], name);
  }
  frameElements = [...base, ...Array.from({ length: 95 }, (_, index) => field(`unknown.${index}`))];
  assert.deepEqual(await inspect(), [], "over-100-controls");
  frameElements = base; const originalLocator = frame.locator;
  frame.locator = () => { throw new Error("fixture locator failure"); };
  assert.deepEqual(await inspect(), [], "locator-error");
  frame.locator = originalLocator; let operated = 0; let resolved = 0;
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
    async inspectControls(input) { return inspectPageControls(input); },
    async proposeAction() { return { control: expected[0].control }; },
    async operateControl() { operated += 1; return { status: "success" }; },
    async resolveValue() { resolved += 1; return "private"; },
  });
  assert.deepEqual(await harness.performAction({ provider: "eventbrite", candidate, page, action: { purpose: "fill", method: "ax_fill", control: expected[0].control } }), { status: "failed" });
  assert.equal(operated, 0);
  assert.equal(resolved, 0);
});

test("Eventbrite attendee inspector accepts the live literal N attendee field names", async () => {
  const candidate = { provider: "eventbrite", event_ref: "eventbrite-event://event/1901", canonical_url: "https://www.eventbrite.com/e/tokyo-free-event-tickets-1901" };
  const field = (name, type = "text") => makeEventbriteTicketElement({ tagName: "INPUT", type, name, required: true, value: "" });
  const makeFields = (names) => names.map((name, index) => field(name, index > 1 ? "email" : "text"));
  let elements = makeFields(["buyer.N-first_name", "buyer.N-last_name", "buyer.N-email", "buyer.confirmEmailAddress"]);
  const frame = { url() { return "https://www.eventbrite.com/checkout-external?eid=1901"; }, parentFrame() { return {}; }, locator() { return { async evaluateAll(callback, context) { return callback(elements, context); } }; } };
  const page = { url() { return candidate.canonical_url; }, frames() { return [frame]; }, locator() { return { async evaluateAll(callback, context) { return callback([], context); } }; } };
  const inspect = () => inspectPageControls({ provider: "eventbrite", page, event_id: "1901", canonical_url: candidate.canonical_url });
  assert.deepEqual(await inspect(), [
    { control: "eventbrite_attendee_first_name_1901", kind: "input", label: "First name", required: true, completed: false, submittable: false },
    { control: "eventbrite_attendee_last_name_1901", kind: "input", label: "Last name", required: true, completed: false, submittable: false },
    { control: "eventbrite_attendee_email_1901", kind: "input", label: "Email", required: true, completed: false, submittable: false },
    { control: "eventbrite_attendee_confirm_email_1901", kind: "input", label: "Confirm email", required: true, completed: false, submittable: false },
  ]);
  for (const names of [
    ["buyer.1-first_name", "buyer.1-last_name", "buyer.1-email", "buyer.confirmEmailAddress"],
    ["buyer.n-first_name", "buyer.n-last_name", "buyer.n-email", "buyer.confirmEmailAddress"],
    ["buyer.N-first_name-extra", "buyer.N-last_name", "buyer.N-email", "buyer.confirmEmailAddress"],
  ]) {
    elements = makeFields(names);
    assert.deepEqual(await inspect(), [], names[0]);
  }
});

test("Eventbrite attendee inspector exposes a read-only final Register control after exact4 completion", async () => {
  const candidate = { provider: "eventbrite", event_ref: "eventbrite-event://event/1901", canonical_url: "https://www.eventbrite.com/e/tokyo-free-event-tickets-1901" };
  const field = (name, type = "text") => makeEventbriteTicketElement({ tagName: "INPUT", type, name, required: true, value: "complete" });
  const first = field("buyer.N-first_name"); const last = field("buyer.N-last_name"); const email = field("buyer.N-email", "email"); const confirm = field("buyer.confirmEmailAddress", "email");
  let primaryTestId = "eds-modal__primary-button";
  const primary = makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: "eds-modal__primary-button", innerText: "Register", getAttribute(name) {
    if (name === "data-testid") return primaryTestId;
    if (name === "aria-label") return "Register";
    return null;
  } });
  const marketing = makeEventbriteTicketElement({ tagName: "INPUT", type: "checkbox", name: "organizationMarketingOptIn", required: false, checked: false });
  const base = [first, last, email, confirm, primary, marketing]; let elements = [...base];
  const frame = { url() { return "https://www.eventbrite.com/checkout-external?eid=1901"; }, parentFrame() { return {}; }, locator() { return { async evaluateAll(callback, context) { return callback(elements, context); } }; } };
  const page = { url() { return candidate.canonical_url; }, frames() { return [frame]; }, locator() { return { async evaluateAll(callback, context) { return callback([], context); } }; } };
  const inspect = () => inspectPageControls({ provider: "eventbrite", page, event_id: "1901", canonical_url: candidate.canonical_url });
  assert.deepEqual(await inspect(), [
    { control: "eventbrite_attendee_first_name_1901", kind: "input", label: "First name", required: true, completed: true, submittable: false },
    { control: "eventbrite_attendee_last_name_1901", kind: "input", label: "Last name", required: true, completed: true, submittable: false },
    { control: "eventbrite_attendee_email_1901", kind: "input", label: "Email", required: true, completed: true, submittable: false },
    { control: "eventbrite_attendee_confirm_email_1901", kind: "input", label: "Confirm email", required: true, completed: true, submittable: false },
    { control: "eventbrite_attendee_register_1901", kind: "button", label: "Register", required: false, completed: false, submittable: true },
  ]);
  assert.equal(primary.dataset.lmConnectorControl, undefined);
  const reset = () => { first.value = "complete"; last.value = "complete"; email.value = "complete"; confirm.value = "complete"; primaryTestId = "eds-modal__primary-button"; primary.tagName = "BUTTON"; primary.type = "button"; primary.innerText = "Register"; primary.textContent = "Register"; primary.hidden = false; primary.isConnected = true; primary.disabled = false; marketing.checked = false; marketing.required = false; marketing.hidden = false; marketing.isConnected = true; marketing.disabled = false; elements = [...base]; };
  for (const [name, mutate] of [
    ["incomplete", () => { first.value = ""; }],
    ["primary-duplicate", () => { elements = [...base, makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: "eds-modal__primary-button", innerText: "Register" })]; }],
    ["primary-wrong-testid", () => { primaryTestId = "other"; }], ["primary-wrong-tag", () => { primary.tagName = "DIV"; }], ["primary-wrong-type", () => { primary.type = "submit"; }],
    ["primary-wrong-label", () => { primary.innerText = "Continue"; primary.textContent = "Continue"; }], ["primary-hidden", () => { primary.hidden = true; }], ["primary-detached", () => { primary.isConnected = false; }], ["primary-disabled", () => { primary.disabled = true; }],
    ["marketing-checked", () => { marketing.checked = true; }], ["marketing-required", () => { marketing.required = true; }], ["marketing-hidden", () => { marketing.hidden = true; }], ["marketing-disabled", () => { marketing.disabled = true; }],
    ["marketing-duplicate", () => { elements = [...base, makeEventbriteTicketElement({ tagName: "INPUT", type: "checkbox", name: "organizationMarketingOptIn", required: false, checked: false })]; }],
  ]) {
    reset(); mutate(); assert.equal((await inspect()).some((control) => control.control === "eventbrite_attendee_register_1901"), false, name);
  }
  reset(); elements = [...base, ...Array.from({ length: 96 }, (_, index) => makeEventbriteTicketElement({ tagName: "INPUT", type: "text", name: `extra-${index}` }))];
  assert.deepEqual(await inspect(), [], "over-101");
  reset(); let resolved = 0; let operated = 0;
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("final readback must not run"); } },
    async inspectControls(input) { return inspectPageControls(input); },
    async proposeAction() { return { control: "eventbrite_attendee_register_1901" }; },
    async operateControl() { operated += 1; return { status: "success" }; },
    async resolveValue() { resolved += 1; return "unexpected"; },
  });
  assert.deepEqual(await harness.performAction({ provider: "eventbrite", candidate, page, action: { purpose: "submit", method: "ax_click", control: "eventbrite_attendee_register_1901" } }), { status: "failed" });
  assert.equal(resolved, 0); assert.equal(operated, 0); assert.equal(primary.dataset.lmConnectorControl, undefined);
});

test("Eventbrite checked marketing input exposes an exact label opt-out control", async () => {
  const candidate = { provider: "eventbrite", event_ref: "eventbrite-event://event/1901", canonical_url: "https://www.eventbrite.com/e/tokyo-free-event-tickets-1901" };
  const field = (name, type = "text") => makeEventbriteTicketElement({ tagName: "INPUT", type, name, required: true, value: "complete" });
  const marketing = makeEventbriteTicketElement({ tagName: "INPUT", type: "checkbox", name: "organizationMarketingOptIn", id: "org-opt-in", required: false, checked: true });
  const label = makeEventbriteTicketElement({ tagName: "LABEL", innerText: "Organization updates", getAttribute(name) { return name === "for" ? "org-opt-in" : null; } });
  const primary = makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: "eds-modal__primary-button", innerText: "Register" });
  const elements = [field("buyer.N-first_name"), field("buyer.N-last_name"), field("buyer.N-email", "email"), field("buyer.confirmEmailAddress", "email"), marketing, label, primary];
  const frame = { url() { return "https://www.eventbrite.com/checkout-external?eid=1901"; }, parentFrame() { return {}; }, locator() { return { async evaluateAll(callback, context) { return callback(elements, context); } }; } };
  const page = { url() { return candidate.canonical_url; }, frames() { return [frame]; }, locator() { return { async evaluateAll(callback, context) { return callback([], context); } }; } };
  assert.deepEqual(await inspectPageControls({ provider: "eventbrite", page, event_id: "1901", canonical_url: candidate.canonical_url }), [
    { control: "eventbrite_attendee_first_name_1901", kind: "input", label: "First name", required: true, completed: true, submittable: false },
    { control: "eventbrite_attendee_last_name_1901", kind: "input", label: "Last name", required: true, completed: true, submittable: false },
    { control: "eventbrite_attendee_email_1901", kind: "input", label: "Email", required: true, completed: true, submittable: false },
    { control: "eventbrite_attendee_confirm_email_1901", kind: "input", label: "Confirm email", required: true, completed: true, submittable: false },
    { control: "eventbrite_marketing_opt_out_organization_1901", kind: "checkbox", label: "Organization updates", required: true, completed: false, submittable: false },
  ]);
  assert.equal(marketing.dataset.lmConnectorControl, "eventbrite_marketing_opt_out_organization_1901");
});

test("Eventbrite marketing opt-out clicks the verified input once without resolving a value", async () => {
  const candidate = { provider: "eventbrite", event_ref: "eventbrite-event://event/1901", canonical_url: "https://www.eventbrite.com/e/tokyo-free-event-tickets-1901" };
  const field = (name, type = "text") => makeEventbriteTicketElement({ tagName: "INPUT", type, name, required: true, value: "complete" });
  const marketing = makeEventbriteTicketElement({ tagName: "INPUT", type: "checkbox", name: "ebMarketingOptIn", id: "eb-opt-in", required: false, checked: true, hasAttribute(name) { return name === "checked"; } });
  const label = makeEventbriteTicketElement({ tagName: "LABEL", innerText: "Event updates", getAttribute(name) { return name === "for" ? "eb-opt-in" : null; } });
  const primary = makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: "eds-modal__primary-button", innerText: "Register" });
  const elements = [field("buyer.N-first_name"), field("buyer.N-last_name"), field("buyer.N-email", "email"), field("buyer.confirmEmailAddress", "email"), marketing, label, primary];
  let inputClicks = 0; let labelClicks = 0; let registerClicks = 0; let operateCalls = 0; let resolveCalls = 0;
  marketing.click = () => { inputClicks += 1; marketing.checked = false; };
  const frame = { url() { return "https://www.eventbrite.com/checkout-external?eid=1901"; }, parentFrame() { return {}; }, locator(selector) {
    const exact = /^input\[data-lm-connector-control="([^"]+)"\]\[name="([^"]+)"\]$/.exec(selector);
    if (exact) return { async count() { return exact[1] === "eventbrite_marketing_opt_out_eventbrite_1901" && exact[2] === "ebMarketingOptIn" ? 1 : 0; }, async uncheck(options) { assert.deepEqual(options, { force: true }); inputClicks += 1; marketing.checked = false; } };
    const token = /^\[data-lm-connector-control="([^"]+)"\]$/.exec(selector)?.[1]; const labelToken = /^label\[data-lm-connector-control="([^"]+)"\]$/.exec(selector)?.[1]; const compoundToken = /^label\[data-lm-connector-control="([^"]+)"\]\[for="([^"]+)"\]$/.exec(selector)?.[1];
    if (token || labelToken || compoundToken) return { async count() { return (token || labelToken || compoundToken) === "eventbrite_marketing_opt_out_eventbrite_1901" ? 1 : 0; }, async click() { labelClicks += 1; if (labelToken || compoundToken) registerClicks += 1; marketing.checked = false; } };
    return { async evaluateAll(callback, context) { return callback(elements, context); } };
  } };
  const page = { url() { return candidate.canonical_url; }, frames() { return [frame]; }, locator() { return { async evaluateAll(callback, context) { return callback([], context); } }; } };
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("marketing readback must not run"); } },
    async inspectControls(input) { return inspectPageControls(input); },
    async proposeAction() { return { control: "eventbrite_marketing_opt_out_eventbrite_1901" }; },
    async operateControl(input) { operateCalls += 1; assert.equal(input.frame, frame); return operatePageControl(input); },
    async resolveValue() { resolveCalls += 1; return "unexpected"; },
  });
  assert.deepEqual(await harness.performAction({ provider: "eventbrite", candidate, page, action: { purpose: "fill", method: "ax_uncheck", control: "eventbrite_marketing_opt_out_eventbrite_1901" } }), { status: "success" });
  assert.equal(inputClicks, 1); assert.equal(labelClicks, 0); assert.equal(registerClicks, 0); assert.equal(operateCalls, 1); assert.equal(resolveCalls, 0); assert.equal(marketing.checked, false); assert.equal(primary.dataset.lmConnectorControl, undefined);
});

test("Eventbrite marketing opt-out and final paths fail closed for DOM and action variants", async () => {
  const candidate = { provider: "eventbrite", event_ref: "eventbrite-event://event/1901", canonical_url: "https://www.eventbrite.com/e/tokyo-free-event-tickets-1901" };
  const field = (name, type = "text") => makeEventbriteTicketElement({ tagName: "INPUT", type, name, required: true, value: "complete" });
  const marketing = makeEventbriteTicketElement({ tagName: "INPUT", type: "checkbox", name: "organizationMarketingOptIn", id: "org-opt-in", required: false, checked: true });
  let labelFor = "org-opt-in";
  const label = makeEventbriteTicketElement({ tagName: "LABEL", innerText: "Organization updates", getAttribute(name) { return name === "for" ? labelFor : null; } });
  const primary = makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: "eds-modal__primary-button", innerText: "Register" });
  const base = [field("buyer.N-first_name"), field("buyer.N-last_name"), field("buyer.N-email", "email"), field("buyer.confirmEmailAddress", "email"), marketing, label, primary];
  const optToken = "eventbrite_marketing_opt_out_organization_1901"; const finalToken = "eventbrite_attendee_register_1901"; let elements = [...base];
  let mode = ""; let frameReads = 0; let pageFrameReads = 0; let pageHref = candidate.canonical_url; let frameHref = "https://www.eventbrite.com/checkout-external?eid=1901"; let pageFrames; let locatorCount = 1; let clicks = 0; let inputClicks = 0; let operates = 0; let resolves = 0;
  marketing.click = () => {
    inputClicks += 1;
    if (mode === "click-error") throw new Error("click failed");
    if (mode === "hidden-postcondition") { marketing.hidden = true; return; }
    if (mode !== "postcondition") marketing.checked = false;
  };
  const replacementFrame = { url() { return frameHref; }, parentFrame() { return {}; }, locator() { return { async evaluateAll(callback, context) { return callback(elements, context); } }; } };
  const frame = { url() { return frameHref; }, parentFrame() { return {}; }, locator(selector) {
    const exact = /^input\[data-lm-connector-control="([^"]+)"\]\[name="([^"]+)"\]$/.exec(selector);
    if (exact) return {
      async count() { return exact[1] === optToken && exact[2] === "organizationMarketingOptIn" ? locatorCount : 0; },
      async uncheck(options) { assert.deepEqual(options, { force: true }); inputClicks += 1; if (mode === "click-error") throw new Error("uncheck failed"); if (mode === "hidden-postcondition") { marketing.hidden = true; return; } if (mode !== "postcondition") marketing.checked = false; },
    };
    const token = /^\[data-lm-connector-control="([^"]+)"\]$/.exec(selector)?.[1]; const labelToken = /^label\[data-lm-connector-control="([^"]+)"\]$/.exec(selector)?.[1]; const compoundToken = /^label\[data-lm-connector-control="([^"]+)"\]\[for="([^"]+)"\]$/.exec(selector)?.[1];
    if (token || labelToken || compoundToken) return { async count() { return locatorCount; }, async click() { clicks += 1; if (mode === "click-error") throw new Error("click failed"); if (mode === "hidden-postcondition") marketing.hidden = true; else if (mode !== "postcondition") marketing.checked = false; } };
    return { async evaluateAll(callback, context) { frameReads += 1; if (mode === "dom-drift" && frameReads === 3) elements = [...elements, field("buyer.N-first_name")]; return callback(elements, context); } };
  } };
  pageFrames = [frame];
  const page = { url() { return pageHref; }, frames() { pageFrameReads += 1; if (pageFrameReads === 3 && mode === "page-drift") pageHref = "https://www.eventbrite.com/e/tokyo-free-event-tickets-1902"; if (pageFrameReads === 3 && mode === "eid-drift") frameHref = "https://www.eventbrite.com/checkout-external?eid=1902"; if (pageFrameReads === 3 && mode === "frame-drift") return [replacementFrame]; return pageFrames; }, locator() { return { async evaluateAll(callback, context) { return callback([], context); } }; } };
  const inspect = () => inspectPageControls({ provider: "eventbrite", page, event_id: "1901", canonical_url: candidate.canonical_url });
  const reset = () => { elements = [...base]; marketing.tagName = "INPUT"; marketing.type = "checkbox"; marketing.checked = true; marketing.required = false; marketing.hidden = false; marketing.isConnected = true; marketing.disabled = false; labelFor = "org-opt-in"; label.hidden = false; label.isConnected = true; primary.dataset.lmConnectorControl = undefined; pageHref = candidate.canonical_url; frameHref = "https://www.eventbrite.com/checkout-external?eid=1901"; pageFrames = [frame]; pageFrameReads = 0; frameReads = 0; locatorCount = 1; clicks = 0; inputClicks = 0; operates = 0; resolves = 0; mode = ""; };
  for (const [name, mutate, expectedOpt, expectedFinal] of [
    ["unchecked", () => { marketing.checked = false; }, false, true], ["checked2", () => { const eb = makeEventbriteTicketElement({ tagName: "INPUT", type: "checkbox", name: "ebMarketingOptIn", id: "eb-opt-in", required: false, checked: true }); const ebLabel = makeEventbriteTicketElement({ tagName: "LABEL", innerText: "Event updates", getAttribute(key) { return key === "for" ? "eb-opt-in" : null; } }); elements.push(eb, ebLabel); }, true, false],
    ["duplicate", () => { elements.push({ ...marketing }); }, false, false], ["raw-id-other-tag", () => { elements.push(makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", id: "org-opt-in" })); }, false, false], ["wrong-tag", () => { marketing.tagName = "DIV"; }, false, false], ["wrong-type", () => { marketing.type = "text"; }, false, false], ["required", () => { marketing.required = true; }, false, false], ["hidden", () => { marketing.hidden = true; }, false, false], ["detached", () => { marketing.isConnected = false; }, false, false], ["disabled", () => { marketing.disabled = true; }, false, false],
    ["missing-label", () => { elements = elements.filter((element) => element !== label); }, false, false], ["duplicate-label", () => { elements.push(makeEventbriteTicketElement({ tagName: "LABEL", innerText: "Duplicate", getAttribute(key) { return key === "for" ? "org-opt-in" : null; } })); }, false, false], ["hidden-label", () => { label.hidden = true; }, false, false], ["wrong-for", () => { labelFor = "wrong-id"; }, false, false],
  ]) {
    reset(); mutate(); const controls = await inspect(); assert.equal(controls.some((control) => control.control === optToken), expectedOpt, name); assert.equal(controls.some((control) => control.control === finalToken), expectedFinal, name);
  }
  reset(); elements = [...base, ...Array.from({ length: 94 }, (_, index) => makeEventbriteTicketElement({ tagName: "INPUT", type: "text", name: `extra-${index}` }))]; assert.deepEqual(await inspect(), [], "over-101");
  const harness = createProductionBrowserHarness({ lumaWorkflow: { async readProviderState() { throw new Error("marketing readback must not run"); } }, async inspectControls(input) { return inspectPageControls(input); }, async proposeAction() { return { control: optToken }; }, async operateControl(input) { operates += 1; return operatePageControl(input); }, async resolveValue() { resolves += 1; return "unexpected"; } });
  for (const [name, action, mutate, expectedOperate, expectedClicks, expectedInputClicks] of [
    ["wrong-action", { purpose: "fill", method: "ax_click", control: optToken }, null, 0, 0, 0], ["page-drift", { purpose: "fill", method: "ax_uncheck", control: optToken }, () => { mode = "page-drift"; }, 0, 0, 0], ["frame-drift", { purpose: "fill", method: "ax_uncheck", control: optToken }, () => { mode = "frame-drift"; }, 0, 0, 0], ["eid-drift", { purpose: "fill", method: "ax_uncheck", control: optToken }, () => { mode = "eid-drift"; }, 0, 0, 0], ["dom-drift", { purpose: "fill", method: "ax_uncheck", control: optToken }, () => { mode = "dom-drift"; }, 0, 0, 0], ["locator0", { purpose: "fill", method: "ax_uncheck", control: optToken }, () => { locatorCount = 0; mode = "locator0"; }, 1, 0, 0], ["locator2", { purpose: "fill", method: "ax_uncheck", control: optToken }, () => { locatorCount = 2; mode = "locator2"; }, 1, 0, 0], ["click-error", { purpose: "fill", method: "ax_uncheck", control: optToken }, () => { mode = "click-error"; }, 1, 0, 1], ["postcondition", { purpose: "fill", method: "ax_uncheck", control: optToken }, () => { mode = "postcondition"; }, 1, 0, 1], ["hidden-postcondition", { purpose: "fill", method: "ax_uncheck", control: optToken }, () => { mode = "hidden-postcondition"; }, 1, 0, 1],
    ["final-action", { purpose: "submit", method: "ax_click", control: finalToken }, () => { marketing.checked = false; }, 0, 0, 0],
  ]) {
    reset(); mutate?.(); const result = await harness.performAction({ provider: "eventbrite", candidate, page, action }); assert.deepEqual(result, { status: "failed" }, name); assert.equal(operates, expectedOperate, `${name}-operate`); assert.equal(clicks, expectedClicks, `${name}-label`); assert.equal(inputClicks, expectedInputClicks, `${name}-input`); assert.equal(resolves, 0, `${name}-resolve`);
  }
});

test("Eventbrite marketing token swap cannot activate the Register button", async () => {
  const candidate = { provider: "eventbrite", event_ref: "eventbrite-event://event/1901", canonical_url: "https://www.eventbrite.com/e/tokyo-free-event-tickets-1901" };
  const field = (name, type = "text") => makeEventbriteTicketElement({ tagName: "INPUT", type, name, required: true, value: "complete" });
  const marketing = makeEventbriteTicketElement({ tagName: "INPUT", type: "checkbox", name: "organizationMarketingOptIn", id: "org-opt-in", required: false, checked: true });
  const label = makeEventbriteTicketElement({ tagName: "LABEL", innerText: "Organization updates", getAttribute(name) { return name === "for" ? "org-opt-in" : null; } });
  const primary = makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: "eds-modal__primary-button", innerText: "Register" });
  const elements = [field("buyer.N-first_name"), field("buyer.N-last_name"), field("buyer.N-email", "email"), field("buyer.confirmEmailAddress", "email"), marketing, label, primary];
  const optToken = "eventbrite_marketing_opt_out_organization_1901"; let registerClicks = 0; let inputClicks = 0; let labelClicks = 0; let operateCalls = 0;
  marketing.click = () => { inputClicks += 1; marketing.checked = false; };
  const frame = { url() { return "https://www.eventbrite.com/checkout-external?eid=1901"; }, parentFrame() { return {}; }, locator(selector) {
    const exact = /^input\[data-lm-connector-control="([^"]+)"\]\[name="([^"]+)"\]$/.exec(selector);
    if (exact) {
      marketing.dataset.lmConnectorControl = undefined;
      primary.dataset.lmConnectorControl = optToken;
      return { async count() { return 0; }, async uncheck() { inputClicks += 1; marketing.checked = false; } };
    }
    const token = /^\[data-lm-connector-control="([^"]+)"\]$/.exec(selector)?.[1]; const labelToken = /^label\[data-lm-connector-control="([^"]+)"\]$/.exec(selector)?.[1]; const compoundToken = /^label\[data-lm-connector-control="([^"]+)"\]\[for="([^"]+)"\]$/.exec(selector)?.[1];
    if (token) {
      label.dataset.lmConnectorControl = undefined;
      primary.dataset.lmConnectorControl = token;
      return { async count() { return elements.filter((element) => element.dataset?.lmConnectorControl === token).length; }, async click() { labelClicks += 1; if (primary.dataset.lmConnectorControl === token) registerClicks += 1; else marketing.checked = false; } };
    }
    if (labelToken || compoundToken) return { async count() { return elements.filter((element) => element.dataset?.lmConnectorControl === (labelToken || compoundToken) && element.tagName === "LABEL").length; }, async click() { labelClicks += 1; marketing.checked = false; } };
    return { async evaluateAll(callback, context) { return callback(elements, context); } };
  } };
  const page = { url() { return candidate.canonical_url; }, frames() { return [frame]; }, locator() { return { async evaluateAll(callback, context) { return callback([], context); } }; } };
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("marketing readback must not run"); } },
    async inspectControls(input) { return inspectPageControls(input); }, async proposeAction() { return { control: optToken }; },
    async operateControl(input) { operateCalls += 1; return operatePageControl(input); }, async resolveValue() { throw new Error("resolver must not run"); },
  });
  assert.deepEqual(await harness.performAction({ provider: "eventbrite", candidate, page, action: { purpose: "fill", method: "ax_uncheck", control: optToken } }), { status: "failed" });
  assert.equal(operateCalls, 1); assert.equal(inputClicks, 0); assert.equal(labelClicks, 0); assert.equal(registerClicks, 0);
});

test("Eventbrite marketing final locator fails closed for label and input drift", async () => {
  const candidate = { provider: "eventbrite", event_ref: "eventbrite-event://event/1901", canonical_url: "https://www.eventbrite.com/e/tokyo-free-event-tickets-1901" };
  const field = (name, type = "text") => makeEventbriteTicketElement({ tagName: "INPUT", type, name, required: true, value: "complete" });
  const marketing = makeEventbriteTicketElement({ tagName: "INPUT", type: "checkbox", name: "organizationMarketingOptIn", id: "org-opt-in", required: false, checked: true });
  const label = makeEventbriteTicketElement({ tagName: "LABEL", innerText: "Organization updates", getAttribute(name) { return name === "for" ? "org-opt-in" : null; } });
  const registerLabel = makeEventbriteTicketElement({ tagName: "LABEL", innerText: "Register copy", getAttribute(name) { return name === "for" ? "register" : null; } });
  const primary = makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: "eds-modal__primary-button", innerText: "Register" });
  const elements = [field("buyer.N-first_name"), field("buyer.N-last_name"), field("buyer.N-email", "email"), field("buyer.confirmEmailAddress", "email"), marketing, label, registerLabel, primary];
  const optToken = "eventbrite_marketing_opt_out_organization_1901"; let mode = ""; let clicks = 0; let inputClicks = 0; let registerClicks = 0;
  marketing.click = () => { inputClicks += 1; marketing.checked = false; };
  const mutateDrift = () => {
    if (mode === "label-swap") { marketing.dataset.lmConnectorControl = undefined; label.dataset.lmConnectorControl = undefined; registerLabel.dataset.lmConnectorControl = optToken; }
    if (mode === "checked-drift") { marketing.checked = false; }
    if (mode === "hidden-drift") { marketing.hidden = true; }
    if (mode === "disabled-drift") { marketing.disabled = true; }
    if (mode === "required-drift") { marketing.required = true; }
    if (mode === "type-drift") { marketing.type = "text"; }
  };
  const frame = { url() { return "https://www.eventbrite.com/checkout-external?eid=1901"; }, parentFrame() { return {}; }, locator(selector) {
    const exact = /^input\[data-lm-connector-control="([^"]+)"\]\[name="([^"]+)"\]$/.exec(selector);
    if (exact) return { async count() { if (mode) mutateDrift(); return exact[1] === optToken && exact[2] === "organizationMarketingOptIn" && !mode ? 1 : 0; }, async uncheck(options) { assert.deepEqual(options, { force: true }); inputClicks += 1; marketing.checked = false; } };
    const token = /^\[data-lm-connector-control="([^"]+)"\]$/.exec(selector)?.[1]; const labelToken = /^label\[data-lm-connector-control="([^"]+)"\]$/.exec(selector)?.[1]; const compoundToken = /^label\[data-lm-connector-control="([^"]+)"\]\[for="([^"]+)"\]$/.exec(selector)?.[1]; const labelFor = /^label\[for="([^"]+)"\]$/.exec(selector)?.[1];
    if (token) return { async count() { return elements.filter((element) => element.dataset?.lmConnectorControl === token).length; } };
    if (labelToken || compoundToken || labelFor) {
      return { async count() { return 1; }, async click() { clicks += 1; mutateDrift(); if (mode === "checked-drift") marketing.checked = true; else if (registerLabel.dataset.lmConnectorControl !== optToken) marketing.checked = false; if (registerLabel.dataset.lmConnectorControl === optToken) registerClicks += 1; } };
    }
    return { async evaluateAll(callback, context) { return callback(elements, context); } };
  } };
  const page = { url() { return candidate.canonical_url; }, frames() { return [frame]; }, locator() { return { async evaluateAll(callback, context) { return callback([], context); } }; } };
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("marketing readback must not run"); } },
    async inspectControls(input) { return inspectPageControls(input); }, async proposeAction() { return { control: optToken }; },
    async operateControl(input) { return operatePageControl(input); }, async resolveValue() { throw new Error("resolver must not run"); },
  });
  const reset = () => { marketing.type = "checkbox"; marketing.checked = true; marketing.hidden = false; marketing.disabled = false; marketing.required = false; label.dataset.lmConnectorControl = undefined; registerLabel.dataset.lmConnectorControl = undefined; mode = ""; clicks = 0; inputClicks = 0; registerClicks = 0; };
  for (const name of ["label-swap", "checked-drift", "hidden-drift", "disabled-drift", "required-drift", "type-drift"]) {
    reset(); mode = name;
    const result = await harness.performAction({ provider: "eventbrite", candidate, page, action: { purpose: "fill", method: "ax_uncheck", control: optToken } });
    assert.deepEqual(result, { status: "failed" }, name); assert.equal(clicks, 0, `${name}-label`); assert.equal(inputClicks, 0, `${name}-input`); assert.equal(registerClicks, 0, `${name}-register`); if (name === "checked-drift") assert.equal(marketing.checked, false, `${name}-state`);
  }
});

test("Eventbrite marketing click-time identity rewire cannot redirect the exact input uncheck", async () => {
  const candidate = { provider: "eventbrite", event_ref: "eventbrite-event://event/1901", canonical_url: "https://www.eventbrite.com/e/tokyo-free-event-tickets-1901" };
  const field = (name, type = "text") => makeEventbriteTicketElement({ tagName: "INPUT", type, name, required: true, value: "complete" });
  const marketing = makeEventbriteTicketElement({ tagName: "INPUT", type: "checkbox", name: "organizationMarketingOptIn", id: "org-opt-in", required: false, checked: true });
  let labelFor = "org-opt-in"; let registerFor = "register";
  const label = makeEventbriteTicketElement({ tagName: "LABEL", innerText: "Organization updates", getAttribute(name) { return name === "for" ? labelFor : null; } });
  const registerLabel = makeEventbriteTicketElement({ tagName: "LABEL", innerText: "Register copy", getAttribute(name) { return name === "for" ? registerFor : null; } });
  const primary = makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", id: "register", testId: "eds-modal__primary-button", innerText: "Register" });
  const elements = [field("buyer.N-first_name"), field("buyer.N-last_name"), field("buyer.N-email", "email"), field("buyer.confirmEmailAddress", "email"), marketing, label, registerLabel, primary];
  const optToken = "eventbrite_marketing_opt_out_organization_1901";
  let mode = ""; let inputClicks = 0; let labelClicks = 0; let registerClicks = 0;
  marketing.click = () => { inputClicks += 1; marketing.checked = false; };
  const mutateClickTimeRewire = () => {
    label.dataset.lmConnectorControl = undefined;
    labelFor = "register";
    marketing.id = "verified-id";
    registerLabel.dataset.lmConnectorControl = optToken;
    registerFor = "verified-id";
    primary.id = "verified-id";
    registerClicks += 1;
  };
  const frame = { url() { return "https://www.eventbrite.com/checkout-external?eid=1901"; }, parentFrame() { return {}; }, locator(selector) {
    const exact = /^input\[data-lm-connector-control="([^"]+)"\]\[name="([^"]+)"\]$/.exec(selector);
    if (exact) return { async count() { return exact[1] === optToken && exact[2] === "organizationMarketingOptIn" ? 1 : 0; }, async uncheck(options) { assert.deepEqual(options, { force: true }); inputClicks += 1; marketing.checked = false; } };
    const labelToken = /^label\[data-lm-connector-control="([^"]+)"\]$/.exec(selector)?.[1]; const compoundToken = /^label\[data-lm-connector-control="([^"]+)"\]\[for="([^"]+)"\]$/.exec(selector)?.[1];
    if (labelToken || compoundToken) return { async count() { return 1; }, async click() { labelClicks += 1; if (mode === "click-time-rewire") mutateClickTimeRewire(); } };
    return { async evaluateAll(callback, context) { return callback(elements, context); } };
  } };
  const page = { url() { return candidate.canonical_url; }, frames() { return [frame]; }, locator() { return { async evaluateAll(callback, context) { return callback([], context); } }; } };
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("marketing readback must not run"); } },
    async inspectControls(input) { return inspectPageControls(input); }, async proposeAction() { return { control: optToken }; },
    async operateControl(input) { return operatePageControl(input); }, async resolveValue() { throw new Error("resolver must not run"); },
  });
  mode = "click-time-rewire";
  assert.deepEqual(await harness.performAction({ provider: "eventbrite", candidate, page, action: { purpose: "fill", method: "ax_uncheck", control: optToken } }), { status: "success" });
  assert.equal(inputClicks, 1); assert.equal(labelClicks, 0); assert.equal(registerClicks, 0); assert.equal(marketing.checked, false);
  assert.equal(marketing.id, "org-opt-in"); assert.equal(labelFor, "org-opt-in"); assert.equal(registerLabel.dataset.lmConnectorControl, undefined); assert.equal(primary.id, "register");
});

test("Eventbrite marketing opt-out never reads a page-owned input click accessor", async () => {
  const candidate = { provider: "eventbrite", event_ref: "eventbrite-event://event/1901", canonical_url: "https://www.eventbrite.com/e/tokyo-free-event-tickets-1901" };
  const field = (name, type = "text") => makeEventbriteTicketElement({ tagName: "INPUT", type, name, required: true, value: "complete" });
  const marketing = makeEventbriteTicketElement({ tagName: "INPUT", type: "checkbox", name: "organizationMarketingOptIn", id: "org-opt-in", required: false, checked: true });
  const label = makeEventbriteTicketElement({ tagName: "LABEL", innerText: "Organization updates", getAttribute(name) { return name === "for" ? "org-opt-in" : null; } });
  const primary = makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: "eds-modal__primary-button", innerText: "Register" });
  const elements = [field("buyer.N-first_name"), field("buyer.N-last_name"), field("buyer.N-email", "email"), field("buyer.confirmEmailAddress", "email"), marketing, label, primary];
  let getterReads = 0; let inputUnchecks = 0; let registerClicks = 0;
  Object.defineProperty(marketing, "click", { configurable: true, get() { getterReads += 1; registerClicks += 1; return () => { marketing.checked = false; }; } });
  const token = "eventbrite_marketing_opt_out_organization_1901";
  const frame = { url() { return "https://www.eventbrite.com/checkout-external?eid=1901"; }, parentFrame() { return {}; }, locator(selector) {
    const exact = /^input\[data-lm-connector-control="([^"]+)"\]\[name="([^"]+)"\]$/.exec(selector);
    if (exact) return { async count() { return exact[1] === token && exact[2] === "organizationMarketingOptIn" ? 1 : 0; }, async uncheck(options) { assert.deepEqual(options, { force: true }); inputUnchecks += 1; marketing.checked = false; } };
    return { async evaluateAll(callback, context) { return callback(elements, context); } };
  } };
  const page = { url() { return candidate.canonical_url; }, frames() { return [frame]; }, locator() { return { async evaluateAll(callback, context) { return callback([], context); } }; } };
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("marketing readback must not run"); } },
    async inspectControls(input) { return inspectPageControls(input); }, async proposeAction() { return { control: token }; },
    async operateControl(input) { return operatePageControl(input); }, async resolveValue() { throw new Error("resolver must not run"); },
  });
  assert.deepEqual(await harness.performAction({ provider: "eventbrite", candidate, page, action: { purpose: "fill", method: "ax_uncheck", control: token } }), { status: "success" });
  assert.equal(getterReads, 0); assert.equal(inputUnchecks, 1); assert.equal(registerClicks, 0); assert.equal(marketing.checked, false);
});

test("Eventbrite marketing opt-out fails when the input reverts during the stability window", async () => {
  const candidate = { provider: "eventbrite", event_ref: "eventbrite-event://event/1901", canonical_url: "https://www.eventbrite.com/e/tokyo-free-event-tickets-1901" };
  const field = (name, type = "text") => makeEventbriteTicketElement({ tagName: "INPUT", type, name, required: true, value: "complete" });
  const marketing = makeEventbriteTicketElement({ tagName: "INPUT", type: "checkbox", name: "organizationMarketingOptIn", id: "org-opt-in", required: false, checked: true });
  const label = makeEventbriteTicketElement({ tagName: "LABEL", innerText: "Organization updates", getAttribute(name) { return name === "for" ? "org-opt-in" : null; } });
  const primary = makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: "eds-modal__primary-button", innerText: "Register" });
  const elements = [field("buyer.N-first_name"), field("buyer.N-last_name"), field("buyer.N-email", "email"), field("buyer.confirmEmailAddress", "email"), marketing, label, primary];
  const token = "eventbrite_marketing_opt_out_organization_1901"; let inputUnchecks = 0; let reverts = 0;
  const revert = () => { reverts += 1; marketing.checked = true; };
  marketing.click = () => { inputUnchecks += 1; marketing.checked = false; setTimeout(revert, 10); };
  const frame = { url() { return "https://www.eventbrite.com/checkout-external?eid=1901"; }, parentFrame() { return {}; }, locator(selector) {
    const exact = /^input\[data-lm-connector-control="([^"]+)"\]\[name="([^"]+)"\]$/.exec(selector);
    if (exact) return { async count() { return exact[1] === token && exact[2] === "organizationMarketingOptIn" ? 1 : 0; }, async uncheck(options) { assert.deepEqual(options, { force: true }); inputUnchecks += 1; marketing.checked = false; setTimeout(revert, 10); } };
    return { async evaluateAll(callback, context) { return callback(elements, context); } };
  } };
  const page = { url() { return candidate.canonical_url; }, frames() { return [frame]; }, locator() { return { async evaluateAll(callback, context) { return callback([], context); } }; } };
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("marketing readback must not run"); } },
    async inspectControls(input) { return inspectPageControls(input); }, async proposeAction() { return { control: token }; },
    async operateControl(input) { return operatePageControl(input); }, async resolveValue() { throw new Error("resolver must not run"); },
  });
  mock.timers.enable({ apis: ["Date", "setTimeout"] });
  try {
    const resultPromise = harness.performAction({ provider: "eventbrite", candidate, page, action: { purpose: "fill", method: "ax_uncheck", control: token } });
    let settled = false; resultPromise.then(() => { settled = true; });
    for (let attempt = 0; attempt < 20 && !settled; attempt += 1) await Promise.resolve();
    for (let attempt = 0; attempt < 100 && !settled; attempt += 1) { await Promise.resolve(); mock.timers.tick(25); }
    assert.deepEqual(await resultPromise, { status: "failed" });
  } finally { mock.timers.reset(); }
  assert.equal(inputUnchecks, 1); assert.equal(reverts, 1); assert.equal(marketing.checked, true);
});

test("Eventbrite adapter forwards fill ax_uncheck exactly once", async () => {
  const action = { purpose: "fill", method: "ax_uncheck", control: "eventbrite_marketing_opt_out_eventbrite_1901" }; let proposals = 0; let performed = 0;
  const adapter = createBrowserHarnessAdapter({
    async observePage() { return { state: "registration_page", controls: [{ control: action.control, kind: "checkbox", label: "Event updates", required: true, completed: false, submittable: false }] }; },
    async proposeAction() { proposals += 1; return action; },
    async performAction(input) { performed += 1; assert.deepEqual(input.action, action); return { status: "success" }; },
    async readExpectedState() { return { status: "absent" }; },
  });
  assert.deepEqual(await adapter.runFallback({ provider: "eventbrite", page: {}, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/EVENTBRITEOPT1", maxSteps: 1, expectedState: "registered_or_pending" }), { status: "failed", safe_reason: "agent_step_limit", repaired_actions: [action] });
  assert.equal(proposals, 1); assert.equal(performed, 1);
});

test("Eventbrite attendee fill binds the selected field to the same checkout child frame", async () => {
  const candidate = { provider: "eventbrite", event_ref: "eventbrite-event://event/1901", canonical_url: "https://www.eventbrite.com/e/tokyo-free-event-tickets-1901" };
  const field = (name, type = "text") => makeEventbriteTicketElement({ tagName: "INPUT", type, name, required: true, value: "" });
  const first = field("buyer.N-first_name"); const last = field("buyer.N-last_name"); const email = field("buyer.N-email", "email"); const confirm = field("buyer.confirmEmailAddress", "email");
  const marketing = field("marketing_opt_in", "checkbox"); marketing.required = false;
  const primary = makeEventbriteTicketElement({ tagName: "BUTTON", type: "button", testId: "eds-modal__primary-button", innerText: "Register" });
  let elements = [first, last, email, confirm, marketing, primary]; let fillCalls = 0; let resolved = 0; let operateCalls = 0; let locatorCount = 1; let applyFill = true;
  let pageHref = candidate.canonical_url; let frameHref = "https://www.eventbrite.com/checkout-external?eid=1901"; let pageFrames;
  const frame = { url() { return frameHref; }, parentFrame() { return {}; }, locator(selector) {
    const token = /^\[data-lm-connector-control="([^"]+)"\]$/.exec(selector)?.[1];
    if (token) return { async count() { return locatorCount; }, async fill(value) { fillCalls += 1; if (applyFill) elements.find((element) => element.dataset.lmConnectorControl === token).value = value; } };
    return { async evaluateAll(callback, context) { return callback(elements, context); } };
  } };
  const replacementFrame = { url() { return frameHref; }, parentFrame() { return {}; }, locator() { return { async evaluateAll(callback, context) { return callback(elements, context); } }; } };
  pageFrames = [frame];
  const page = { url() { return pageHref; }, frames() { return pageFrames; }, locator() { return { async evaluateAll(callback, context) { return callback([], context); } }; } };
  const action = { purpose: "fill", method: "ax_fill", control: "eventbrite_attendee_first_name_1901" };
  let mutateAfterResolve = null; let resolvedValue = "GivenFixture";
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("readback must not run"); } },
    async inspectControls(input) { return inspectPageControls(input); },
    async proposeAction() { return { control: action.control }; },
    async operateControl(input) { operateCalls += 1; assert.equal(input.page, page); assert.equal(input.frame, frame); return operatePageControl(input); },
    async resolveValue(input) { resolved += 1; assert.equal(input.control.control, action.control); mutateAfterResolve?.(); return resolvedValue; },
  });
  assert.deepEqual(await harness.performAction({ provider: "eventbrite", candidate, page, action }), { status: "success" });
  assert.equal(resolved, 1); assert.equal(operateCalls, 1); assert.equal(fillCalls, 1); assert.equal(first.value, "GivenFixture"); assert.equal(first.dataset.lmConnectorControl, action.control);

  const reset = () => { first.value = ""; elements = [first, last, email, confirm, marketing, primary]; pageHref = candidate.canonical_url; frameHref = "https://www.eventbrite.com/checkout-external?eid=1901"; pageFrames = [frame]; fillCalls = 0; operateCalls = 0; resolved = 0; locatorCount = 1; applyFill = true; mutateAfterResolve = null; resolvedValue = "GivenFixture"; };
  for (const [name, badAction, mutate, expectedResolve, expectedOperate] of [
    ["wrong-action", { purpose: "submit", method: "ax_click", control: action.control }, null, 0, 0],
    ["missing-value", action, () => { resolvedValue = ""; }, 1, 0],
    ["page-drift", action, () => { pageHref = "https://www.eventbrite.com/e/tokyo-free-event-tickets-1902"; }, 1, 0],
    ["frame-drift", action, () => { pageFrames = [replacementFrame]; }, 1, 0],
    ["eid-drift", action, () => { frameHref = "https://www.eventbrite.com/checkout-external?eid=1902"; }, 1, 0],
    ["dom-drift", action, () => { elements = [...elements, field("buyer.N-first_name")]; }, 1, 0],
    ["locator-zero", action, () => { locatorCount = 0; }, 1, 1],
    ["locator-duplicate", action, () => { locatorCount = 2; }, 1, 1],
    ["postcondition", action, () => { applyFill = false; }, 1, 1],
  ]) {
    reset(); mutateAfterResolve = mutate;
    const result = await harness.performAction({ provider: "eventbrite", candidate, page, action: badAction });
    assert.deepEqual(result, { status: "failed" }, name);
    assert.equal(resolved, expectedResolve, `${name}-resolve`); assert.equal(operateCalls, expectedOperate, `${name}-operate`);
    assert.equal(fillCalls, expectedOperate === 1 && name === "postcondition" ? 1 : 0, `${name}-fill`);
  }
});
