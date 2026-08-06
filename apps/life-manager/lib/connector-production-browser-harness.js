"use strict";

const path = require("node:path");

const { createBrowserHarnessAdapter } = require("./connector-browser-harness-adapter.js");
const { runLocalAgentRunner } = require("./connector-luna-judgment.js");

const CONTROL = /^[a-z][a-z0-9_-]{1,63}$/;
const KINDS = new Set(["input", "textarea", "select", "checkbox", "radio", "button", "link"]);
const FILL = new Set(["ax_fill", "dom_fill", "ax_select"]);

function invalid() {
  throw new Error("Connector production Browser Harness invalid");
}

function safeControl(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) invalid();
  const control = String(input.control || "");
  const kind = String(input.kind || "");
  const label = String(input.label || "").replace(/\s+/g, " ").trim();
  if (
    !CONTROL.test(control) || !KINDS.has(kind) || !label || label.length > 300
    || /[\x00-\x1f\x7f]/.test(label) || typeof input.required !== "boolean"
  ) invalid();
  return Object.freeze({ control, kind, label, required: input.required });
}

async function inspectPageControls(input = {}) {
  const page = input.page;
  if (!page || typeof page.locator !== "function") invalid();
  const locator = page.locator("input, textarea, select, button, a[role=button]");
  if (!locator || typeof locator.evaluateAll !== "function") invalid();
  const observed = await locator.evaluateAll((elements) => elements.slice(0, 100).flatMap((element, index) => {
    const tag = String(element.tagName || "").toLowerCase();
    const type = String(element.type || "").toLowerCase();
    if (type === "hidden" || element.disabled === true) return [];
    const kind = tag === "input" && ["checkbox", "radio"].includes(type)
      ? type : tag === "a" ? "link" : tag;
    if (!["input", "textarea", "select", "checkbox", "radio", "button", "link"].includes(kind)) return [];
    const labels = Array.from(element.labels || []).map((label) => label.innerText || label.textContent || "");
    const label = [
      ...labels,
      element.getAttribute && element.getAttribute("aria-label"),
      element.getAttribute && element.getAttribute("placeholder"),
      element.getAttribute && element.getAttribute("name"),
      element.innerText,
    ].map((value) => String(value || "").replace(/\s+/g, " ").trim()).find(Boolean);
    if (!label) return [];
    const control = `control_${index + 1}`;
    element.dataset.lmConnectorControl = control;
    return [{ control, kind, label, required: element.required === true }];
  }));
  if (!Array.isArray(observed)) invalid();
  return Object.freeze(observed.map(safeControl));
}

async function operatePageControl(input = {}) {
  if (!input.page || typeof input.page.locator !== "function" || !input.control || !input.action) invalid();
  const token = String(input.control.control || "");
  if (!CONTROL.test(token) || input.action.control !== token) invalid();
  const locator = input.page.locator(`[data-lm-connector-control="${token}"]`);
  if (!locator || typeof locator.count !== "function" || await locator.count() !== 1) {
    return Object.freeze({ status: "failed" });
  }
  switch (input.action.method) {
    case "ax_fill":
    case "dom_fill":
      if (typeof input.value !== "string" || typeof locator.fill !== "function") return Object.freeze({ status: "failed" });
      await locator.fill(input.value);
      break;
    case "ax_check":
      if (typeof locator.check !== "function") return Object.freeze({ status: "failed" });
      await locator.check();
      break;
    case "ax_select":
      if (typeof locator.selectOption !== "function") return Object.freeze({ status: "failed" });
      await locator.selectOption(input.value);
      break;
    case "ax_click":
    case "coordinate_click":
      if (typeof locator.click !== "function") return Object.freeze({ status: "failed" });
      await locator.click();
      break;
    case "keyboard_submit":
      if (!input.page.keyboard || typeof input.page.keyboard.press !== "function") return Object.freeze({ status: "failed" });
      await input.page.keyboard.press("Enter");
      break;
    case "ax_inspect":
    case "dom_inspect":
    case "parent_readback":
      break;
    default:
      return Object.freeze({ status: "failed" });
  }
  return Object.freeze({ status: "success" });
}

function normalizedLabel(value) {
  return String(value || "").replace(/\s+/g, " ").trim().toLowerCase();
}

function createLumaPrivateValueResolver(options = {}) {
  const readProfile = options.readProfile;
  if (typeof readProfile !== "function") invalid();
  return async function resolveValue(input = {}) {
    const control = safeControl(input.control);
    const profile = await readProfile();
    if (!profile || typeof profile !== "object" || Array.isArray(profile)) invalid();
    const label = normalizedLabel(control.label);
    if (/\b(phone|telephone|mobile|電話|携帯)\b/i.test(label)) {
      return typeof profile.phone === "string" ? profile.phone : null;
    }
    const answers = profile.form_answers;
    if (!answers || typeof answers !== "object" || Array.isArray(answers)) return null;
    const match = Object.entries(answers).find(([key]) => normalizedLabel(key) === label);
    return match ? match[1] : null;
  };
}

function absoluteDirectory(value) {
  const directory = path.resolve(String(value || ""));
  if (!path.isAbsolute(directory) || directory === path.parse(directory).root) invalid();
  return directory;
}

function createBoundedActionProposer(options = {}) {
  const repoRoot = absoluteDirectory(options.repoRoot);
  const evidenceDir = absoluteDirectory(options.evidenceDir);
  const runAgentRunner = options.runAgentRunner || runLocalAgentRunner;
  if (typeof runAgentRunner !== "function") invalid();
  return async function proposeAction(input = {}) {
    const targetId = String(input.target_id || "");
    const step = Number(input.step);
    if (
      input.provider !== "luma" || !/^[A-Za-z0-9._-]{3,128}$/.test(targetId)
      || input.expected_state !== "registered_or_pending"
      || !Number.isInteger(step) || step < 1 || step > 10
      || !input.observation || !Array.isArray(input.observation.controls)
    ) invalid();
    const controls = input.observation.controls.map(safeControl);
    const result = await runAgentRunner({
      prompt: [
        "Choose exactly one browser action for the current Luma registration page.",
        "Return only purpose, method, and one control token from the supplied list.",
        "Prefer filling required ordinary fields before submitting. Never navigate, open or close pages, run commands, or edit code.",
        "The parent process owns all private values, executes the action, and verifies registered or pending state.",
        `Step: ${step} of 10`,
        `Page state: ${String(input.observation.state || "registration_page")}`,
        `Controls: ${JSON.stringify(controls)}`,
      ].join("\n"),
      schema: {
        type: "object",
        additionalProperties: false,
        required: ["purpose", "method", "control"],
        properties: {
          purpose: { type: "string", enum: ["observe", "fill", "submit", "readback"] },
          method: {
            type: "string",
            enum: [
              "ax_inspect", "dom_inspect", "parent_readback", "ax_fill", "dom_fill",
              "ax_check", "ax_select", "ax_click", "coordinate_click", "keyboard_submit",
            ],
          },
          control: { type: "string", enum: controls.map((control) => control.control) },
        },
      },
      taskClass: "browser-lane-agent",
      timeoutMs: 30_000,
      evidenceDir: path.join(evidenceDir, `target-${targetId}`, `step-${step}`),
      repoRoot,
    });
    if (
      !result || !result.summary || result.summary.status !== "success"
      || result.summary.selected_provider !== "codex" || result.summary.selected_model !== "gpt-5.6-terra"
      || !result.value || typeof result.value !== "object" || Array.isArray(result.value)
    ) invalid();
    return Object.freeze({
      purpose: String(result.value.purpose || ""),
      method: String(result.value.method || ""),
      control: String(result.value.control || ""),
    });
  };
}

function createProductionBrowserHarness(options = {}) {
  const lumaWorkflow = options.lumaWorkflow;
  const inspectControls = options.inspectControls;
  const proposeAction = options.proposeAction;
  const operateControl = options.operateControl;
  const resolveValue = options.resolveValue;
  if (
    !lumaWorkflow || typeof lumaWorkflow.readProviderState !== "function"
    || typeof inspectControls !== "function" || typeof proposeAction !== "function"
    || typeof operateControl !== "function" || typeof resolveValue !== "function"
  ) invalid();
  const registry = new WeakMap();

  async function observed(page) {
    const values = await inspectControls({ page });
    if (!Array.isArray(values) || values.length < 1 || values.length > 100) invalid();
    const controls = values.map(safeControl);
    if (new Set(controls.map((item) => item.control)).size !== controls.length) invalid();
    const observation = Object.freeze({
      state: "registration_page",
      controls: Object.freeze(controls),
    });
    registry.set(page, observation);
    return observation;
  }

  async function performAction(input = {}) {
    if (!input.page || !input.action || !CONTROL.test(String(input.action.control || ""))) invalid();
    const observation = registry.get(input.page) || await observed(input.page);
    const control = observation.controls.find((item) => item.control === input.action.control);
    if (!control) return Object.freeze({ status: "failed" });
    let value = null;
    if (FILL.has(input.action.method)) {
      value = await resolveValue({ page: input.page, control, action: input.action });
      if (
        !(typeof value === "string" || Array.isArray(value))
        || (typeof value === "string" && (!value.trim() || value.length > 2_000))
        || (Array.isArray(value) && (value.length < 1 || value.length > 3))
      ) return Object.freeze({ status: "failed" });
    }
    const result = await operateControl({
      page: input.page,
      control,
      action: input.action,
      value,
    });
    return result && result.status === "success"
      ? Object.freeze({ status: "success" })
      : Object.freeze({ status: "failed" });
  }

  async function runFallback(input = {}) {
    if (input.provider !== "luma" || !input.candidate) invalid();
    const adapter = createBrowserHarnessAdapter({
      observePage: ({ page }) => observed(page),
      proposeAction,
      performAction,
      readExpectedState: ({ page }) => lumaWorkflow.readProviderState({
        page,
        candidate: input.candidate,
      }),
    });
    return adapter.runFallback(input);
  }

  return Object.freeze({ performAction, runFallback });
}

module.exports = {
  createBoundedActionProposer,
  createLumaPrivateValueResolver,
  createProductionBrowserHarness,
  inspectPageControls,
  operatePageControl,
};
