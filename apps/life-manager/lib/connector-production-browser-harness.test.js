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
  const page = Object.freeze({ page_id: "known-connpass-page" });
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
    assert.equal(await resolver({ provider: "connpass", control: { control: "safe_radio", kind: "radio", label, question, required: true } }), expected, label);
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
  let href = "https://tokyo-builders.connpass.com/event/400028/join/";
  let proposals = 0;
  let operated = 0;
  const page = { url() { return href; } };
  const harness = createProductionBrowserHarness({
    lumaWorkflow: { async readProviderState() { throw new Error("wrong provider"); } },
    connpassWorkflow: { async readProviderState() { return { status: "absent" }; } },
    async inspectControls() { return [{ control: proposals === 0 ? "submit_one" : "submit_two", kind: "button", label: "申し込みを確定する", required: false, submittable: true }]; },
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
