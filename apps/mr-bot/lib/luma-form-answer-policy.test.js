"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { buildLumaFormAnswerPlan } = require("./luma-form-answer-policy.js");

function schema(fields) {
  return { kind: "luma_registration_form", fields };
}

test("answers only exact profile-backed fields and explicit consent", () => {
  const result = buildLumaFormAnswerPlan({
    schema: schema([
      { key: "phone_number", label: "電話番号", control: "phone", required: true, options: [] },
      {
        key: "registration_answers.0.value",
        label: "How would you describe your work, practice, or field?",
        control: "multi_select",
        required: true,
        options: ["Technology", "Design", "Founder"],
      },
      {
        key: "agreement",
        label: "I agree to the Code of Conduct and Media Release.",
        control: "checkbox",
        required: true,
        options: [],
      },
    ]),
    profile: {
      phone: "+81 90 0000 0000",
      form_answers: {
        "How would you describe your work, practice, or field?": ["Technology", "Founder"],
      },
      consents: { code_of_conduct_and_media_release: true },
    },
  });

  assert.deepEqual(result, {
    status: "ready",
    answers: [
      { key: "phone_number", control: "phone", value: "+81 90 0000 0000" },
      {
        key: "registration_answers.0.value",
        control: "multi_select",
        value: ["Technology", "Founder"],
      },
      { key: "agreement", control: "checkbox", value: true },
    ],
    unresolved: [],
  });
});

test("a missing Instagram identity blocks this candidate without inventing a handle", () => {
  const result = buildLumaFormAnswerPlan({
    schema: schema([
      {
        key: "registration_answers.1.value",
        label: "Which Instagram handle do you move through the world with?",
        control: "text",
        required: true,
        options: [],
      },
    ]),
    profile: { phone: "+81 90 0000 0000", form_answers: {} },
  });

  assert.deepEqual(result, {
    status: "candidate_not_actionable",
    reason: "LUMA_REQUIRED_PROFILE_FIELD_UNAVAILABLE",
    answers: [],
    unresolved: [{
      key: "registration_answers.1.value",
      label: "Which Instagram handle do you move through the world with?",
    }],
  });
  assert.doesNotMatch(JSON.stringify(result), /N\/A|not active|instagram\.com/i);
});

test("rejects options outside the observed form and secret-shaped profile answers", () => {
  const field = {
    key: "registration_answers.0.value",
    label: "Primary field",
    control: "multi_select",
    required: true,
    options: ["Technology"],
  };
  assert.throws(() => buildLumaFormAnswerPlan({
    schema: schema([field]),
    profile: { form_answers: { "Primary field": ["Finance"] } },
  }), /Luma form answer policy unavailable/);
  assert.throws(() => buildLumaFormAnswerPlan({
    schema: schema([{ ...field, control: "text", options: [] }]),
    profile: { form_answers: { "Primary field": "token=secret-value" } },
  }), /Luma form answer policy unavailable/);
});
