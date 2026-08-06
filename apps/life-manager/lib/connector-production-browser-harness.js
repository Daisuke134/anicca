"use strict";

const { createBrowserHarnessAdapter } = require("./connector-browser-harness-adapter.js");

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

module.exports = { createProductionBrowserHarness };
