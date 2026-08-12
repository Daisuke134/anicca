"use strict";

const SAFE_KEY = /^[A-Za-z0-9_.-]{1,160}$/;

function unavailable() {
  throw new Error("Luma registration form fill unavailable");
}

async function exactLocator(scope, key) {
  if (!SAFE_KEY.test(String(key || "")) || !scope || typeof scope.locator !== "function") unavailable();
  const locator = scope.locator(`[name="${key}"]`);
  if (!locator || await locator.count() !== 1) unavailable();
  return locator;
}

async function fillScalar(scope, answer) {
  const locator = await exactLocator(scope, answer.key);
  if (typeof locator.fill !== "function" || typeof locator.inputValue !== "function") unavailable();
  await locator.fill(answer.value);
  if (String(await locator.inputValue()).trim() !== answer.value) unavailable();
}

async function fillCheckbox(scope, answer) {
  const locator = await exactLocator(scope, answer.key);
  if (answer.value !== true || typeof locator.check !== "function" || typeof locator.isChecked !== "function") unavailable();
  await locator.check();
  if (!await locator.isChecked()) unavailable();
}

async function fillMultiSelect(scope, answer) {
  if (!Array.isArray(answer.value) || answer.value.length < 1 || answer.value.length > 3 || typeof scope.getByText !== "function") {
    unavailable();
  }
  for (const option of answer.value) {
    const control = scope.getByText(option, { exact: true });
    if (!control || await control.count() !== 1 || typeof control.click !== "function") unavailable();
    await control.click();
    if (typeof control.getAttribute !== "function" || await control.getAttribute("aria-pressed") !== "true") unavailable();
  }
}

async function fillLumaRegistrationForm(scope, plan) {
  if (
    !plan || plan.status !== "ready" || !Array.isArray(plan.answers)
    || !Array.isArray(plan.unresolved) || plan.unresolved.length !== 0 || plan.answers.length > 50
  ) unavailable();
  for (const answer of plan.answers) {
    if (!answer || typeof answer !== "object" || Array.isArray(answer)) unavailable();
    if (answer.control === "multi_select") await fillMultiSelect(scope, answer);
    else if (answer.control === "checkbox") await fillCheckbox(scope, answer);
    else if (["phone", "text", "email", "url", "textarea", "select", "radio"].includes(answer.control)) {
      await fillScalar(scope, answer);
    } else unavailable();
  }
  return Object.freeze({ status: "filled", field_count: plan.answers.length });
}

module.exports = { fillLumaRegistrationForm };
