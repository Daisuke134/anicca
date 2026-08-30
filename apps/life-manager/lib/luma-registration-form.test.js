"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  normalizeLumaRegistrationForm,
  readLumaRegistrationForm,
} = require("./luma-registration-form.js");

test("observes required name-less Luma comboboxes as synthetic dropdown fields", async () => {
  let observerSource = "";
  const options = ["Yes", "No"].map((value) => ({
    textContent: value,
    getAttribute(attribute) { return attribute === "aria-label" ? value : null; },
  }));
  const combo = {
    tagName: "INPUT",
    labels: [],
    parentElement: null,
    getAttribute(attribute) {
      return {
        role: "combobox",
        "aria-haspopup": "listbox",
        "aria-required": "true",
        "aria-label": "Would you like to attend? *",
      }[attribute] || null;
    },
    hasAttribute() { return false; },
    matches() { return false; },
    querySelector() { return null; },
    querySelectorAll(selector) { return selector.includes("[role='option']") ? options : []; },
    contains() { return false; },
    ownerDocument: { getElementById() { return null; } },
  };
  const scopeRoot = {
    parentElement: null,
    querySelectorAll(selector) {
      if (selector.includes("input[aria-required='true']")) return [combo];
      if (selector.includes("[role='combobox'][aria-haspopup='listbox']")) return [combo];
      return [];
    },
    querySelector() { return null; },
    matches() { return false; },
    contains(node) { return node === combo; },
  };

  const hadDocument = Object.hasOwn(global, "document");
  const previousDocument = global.document;
  global.document = {};
  let schema;
  try {
    schema = await readLumaRegistrationForm({
      async evaluate(observer) {
        observerSource = String(observer);
        return observer(scopeRoot);
      },
    });
  } finally {
    if (hadDocument) global.document = previousDocument;
    else delete global.document;
  }

  assert.deepEqual(schema, {
    kind: "luma_registration_form",
    fields: [{
      key: "luma_dropdown_0",
      label: "Would you like to attend?",
      control: "dropdown",
      required: true,
      options: ["Yes", "No"],
    }],
  });
  assert.doesNotMatch(observerSource, /\.value\b|inputValue|outerHTML|document\.body/i);
});

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

test("observes only controls under the evaluated dialog scope", async () => {
  const field = (name, label) => ({
    tagName: "INPUT",
    labels: [],
    parentElement: null,
    getAttribute(attribute) {
      return {
        name,
        type: "text",
        "aria-label": label,
      }[attribute] || null;
    },
    hasAttribute(attribute) { return attribute === "required"; },
    matches() { return false; },
    closest() { return null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    contains() { return false; },
    ownerDocument: { getElementById() { return null; } },
  });
  const pageOnlyField = field("page_only", "Page-only required question *");
  const dialogField = field("dialog_answer", "Dialog question *");
  const scopeRoot = (fields) => ({
    parentElement: null,
    querySelectorAll(selector) {
      return selector.includes("input[name]") || selector.includes("[required]") ? fields : [];
    },
    querySelector() { return null; },
    getElementById() { return null; },
    getAttribute() { return null; },
    matches() { return false; },
    contains(node) { return fields.includes(node); },
  });
  const pageRoot = scopeRoot([pageOnlyField]);
  const dialogRoot = scopeRoot([dialogField]);
  const hadDocument = Object.hasOwn(global, "document");
  const previousDocument = global.document;
  global.document = pageRoot;
  try {
    const schema = await readLumaRegistrationForm({
      async evaluate(observer) { return observer(dialogRoot); },
    });
    assert.deepEqual(schema, {
      kind: "luma_registration_form",
      fields: [{
        key: "dialog_answer",
        label: "Dialog question",
        control: "text",
        required: true,
        options: [],
      }],
    });
  } finally {
    if (hadDocument) global.document = previousDocument;
    else delete global.document;
  }
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
