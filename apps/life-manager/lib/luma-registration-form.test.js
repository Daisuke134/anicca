"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  normalizeLumaRegistrationForm,
  readLumaRegistrationForm,
} = require("./luma-registration-form.js");

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

test("reads a closed structural schema without reading form values or a raw page body", async () => {
  let observerSource = "";
  const schema = await readLumaRegistrationForm({
    async evaluate(observer) {
      observerSource = String(observer);
      return [{
        label: "Which field best describes your work? *",
        name: "registration_answers.0.value",
        tag: "div",
        type: "multi-select",
        html_required: false,
        app_required: true,
        options: ["Technology", "Design"],
      }, {
        label: "I agree to the Code of Conduct and Media Release. *",
        name: "agreement",
        tag: "div",
        type: "checkbox",
        html_required: false,
        app_required: true,
        options: [],
      }];
    },
  });

  assert.deepEqual(schema, {
    kind: "luma_registration_form",
    fields: [{
      key: "registration_answers.0.value",
      label: "Which field best describes your work?",
      control: "multi_select",
      required: true,
      options: ["Technology", "Design"],
    }, {
      key: "agreement",
      label: "I agree to the Code of Conduct and Media Release.",
      control: "checkbox",
      required: true,
      options: [],
    }],
  });
  assert.doesNotMatch(
    observerSource,
    /document\.body|\.value\b|cookie|inputValue|outerHTML|innerText/i,
  );
});

test("the browser observer rejects one-time-code controls instead of treating them as phone fields", async () => {
  let observerSource = "";
  const result = await readLumaRegistrationForm({
    async evaluate(observer) {
      observerSource = String(observer);
      return null;
    },
  });

  assert.equal(result, null);
  assert.match(observerSource, /one-time-code/);
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
