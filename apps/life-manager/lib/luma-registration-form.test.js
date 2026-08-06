"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { normalizeLumaRegistrationForm } = require("./luma-registration-form.js");

test("normalizes the live Luma golden trace including app-required custom controls", () => {
  const schema = normalizeLumaRegistrationForm([
    {
      label: "電話番号 *",
      name: "phone_number",
      tag: "input",
      type: "tel",
      html_required: true,
      app_required: true,
      options: [],
    },
    {
      label: "How would you describe your work, practice, or field? *",
      name: "registration_answers.0.value",
      tag: "div",
      type: "multi-select",
      html_required: false,
      app_required: true,
      options: ["Technology", "Design", "Founder"],
    },
    {
      label: "Which Instagram handle do you move through the world with? *",
      name: "registration_answers.1.value",
      tag: "input",
      type: "text",
      html_required: true,
      app_required: true,
      options: [],
    },
    {
      label: "I agree to the Code of Conduct and Media Release. *",
      name: "agreement",
      tag: "input",
      type: "checkbox",
      html_required: false,
      app_required: true,
      options: [],
    },
  ]);

  assert.deepEqual(schema, {
    kind: "luma_registration_form",
    fields: [
      { key: "phone_number", label: "電話番号", control: "phone", required: true, options: [] },
      {
        key: "registration_answers.0.value",
        label: "How would you describe your work, practice, or field?",
        control: "multi_select",
        required: true,
        options: ["Technology", "Design", "Founder"],
      },
      {
        key: "registration_answers.1.value",
        label: "Which Instagram handle do you move through the world with?",
        control: "text",
        required: true,
        options: [],
      },
      {
        key: "agreement",
        label: "I agree to the Code of Conduct and Media Release.",
        control: "checkbox",
        required: true,
        options: [],
      },
    ],
  });
});

test("rejects unlabeled, duplicate, secret-shaped, and unbounded form schemas", () => {
  const base = {
    label: "Question *",
    name: "registration_answers.1.value",
    tag: "input",
    type: "text",
    html_required: true,
    app_required: true,
    options: [],
  };
  for (const invalid of [
    [{ ...base, label: "" }],
    [base, base],
    [{ ...base, label: "API token", name: "secret" }],
    Array.from({ length: 51 }, (_, index) => ({ ...base, name: `answer.${index}` })),
  ]) {
    assert.throws(() => normalizeLumaRegistrationForm(invalid), /Luma registration form unavailable/);
  }
});
