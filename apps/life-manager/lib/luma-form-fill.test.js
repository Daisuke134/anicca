"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { fillLumaRegistrationForm } = require("./luma-form-fill.js");

function dropdownFillFixture(optionCount = 1) {
  const calls = [];
  let roleLookups = 0;
  let selected = "";
  const control = {
    async count() { return 1; },
    async getAttribute(name) {
      if (name === "name") return null;
      if (name === "aria-required") return "true";
      return null;
    },
    async click() { calls.push("dropdown-click"); },
    async inputValue() { return selected; },
  };
  const controls = {
    async count() { return 1; },
    nth(index) { assert.equal(index, 0); return control; },
  };
  const option = {
    async count() { return optionCount; },
    async isVisible() { return true; },
    async click() { calls.push("option-click"); selected = "Yes"; },
  };
  return {
    calls,
    roleLookups: () => roleLookups,
    scope: {
      locator(selector) {
        assert.equal(selector, "[role='combobox'][aria-haspopup='listbox']");
        return controls;
      },
      getByRole(role, options) {
        roleLookups += 1;
        assert.equal(role, "option");
        assert.deepEqual(options, { name: "Yes", exact: true });
        return option;
      },
    },
  };
}

test("fills a synthetic Luma dropdown by exact visible option and inputValue readback", async () => {
  const fixture = dropdownFillFixture();

  const result = await fillLumaRegistrationForm(fixture.scope, {
    status: "ready",
    unresolved: [],
    answers: [{ key: "luma_dropdown_0", control: "dropdown", value: "Yes" }],
  });

  assert.deepEqual(result, { status: "filled", field_count: 1 });
  assert.deepEqual(fixture.calls, ["dropdown-click", "option-click"]);
});

test("fails closed when a synthetic Luma dropdown has ambiguous matching options", async () => {
  const fixture = dropdownFillFixture(2);

  await assert.rejects(() => fillLumaRegistrationForm(fixture.scope, {
    status: "ready",
    unresolved: [],
    answers: [{ key: "luma_dropdown_0", control: "dropdown", value: "Yes" }],
  }), /Luma registration form fill unavailable/);
  assert.equal(fixture.roleLookups(), 1);
  assert.deepEqual(fixture.calls, ["dropdown-click"]);
});

test("fills only exact planned controls and verifies every effect", async () => {
  const calls = [];
  const values = new Map();
  const checked = new Set();
  const locatorFor = (key) => ({
    async count() { return 1; },
    async fill(value) { calls.push(["fill", key, value]); values.set(key, value); },
    async inputValue() { return values.get(key) || ""; },
    async check() { calls.push(["check", key]); checked.add(key); },
    async isChecked() { return checked.has(key); },
  });
  const scope = {
    locator(selector) {
      const match = /^\[name="([A-Za-z0-9_.-]+)"\]$/.exec(selector);
      assert.ok(match);
      return locatorFor(match[1]);
    },
    getByText(option, options) {
      assert.deepEqual(options, { exact: true });
      return {
        async count() { return 1; },
        async click() { calls.push(["select", option]); checked.add(`option:${option}`); },
        async getAttribute(name) {
          assert.equal(name, "aria-pressed");
          return checked.has(`option:${option}`) ? "true" : "false";
        },
      };
    },
  };

  const result = await fillLumaRegistrationForm(scope, {
    status: "ready",
    unresolved: [],
    answers: [
      { key: "phone_number", control: "phone", value: "+81 90 0000 0000" },
      { key: "work", control: "multi_select", value: ["Technology", "Founder"] },
      { key: "agreement", control: "checkbox", value: true },
    ],
  });

  assert.deepEqual(result, { status: "filled", field_count: 3 });
  assert.deepEqual(calls, [
    ["fill", "phone_number", "+81 90 0000 0000"],
    ["select", "Technology"],
    ["select", "Founder"],
    ["check", "agreement"],
  ]);
});

test("non-ready, missing, ambiguous, or unverifiable controls fail before success", async () => {
  await assert.rejects(
    fillLumaRegistrationForm({}, { status: "candidate_not_actionable", answers: [], unresolved: [{}] }),
    /Luma registration form fill unavailable/,
  );
  for (const count of [0, 2]) {
    await assert.rejects(fillLumaRegistrationForm({
      locator() { return { async count() { return count; } }; },
    }, {
      status: "ready",
      unresolved: [],
      answers: [{ key: "phone_number", control: "phone", value: "+81 90 0000 0000" }],
    }), /Luma registration form fill unavailable/);
  }
});
