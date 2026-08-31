"use strict";

const SECRET_VALUE = /(?:api[_ -]?key|access[_ -]?token|\btoken|password|secret|cookie|session)\s*[:=]/i;

function unavailable() {
  throw new Error("Luma form answer policy unavailable");
}

function object(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) unavailable();
  return value;
}

function safeScalar(value) {
  if (typeof value === "boolean") return value;
  const text = String(value == null ? "" : value).trim();
  if (!text || text.length > 2_000 || /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(text) || SECRET_VALUE.test(text)) {
    unavailable();
  }
  return text;
}

function explicitAnswer(field, profile) {
  const answers = profile.form_answers && object(profile.form_answers);
  if (answers && Object.hasOwn(answers, field.key)) return answers[field.key];
  if (answers && Object.hasOwn(answers, field.label)) return answers[field.label];
  if (field.control === "phone" && profile.phone) return profile.phone;
  if (
    field.control === "checkbox"
    && /code of conduct/i.test(field.label)
    && /media release/i.test(field.label)
    && profile.consents
    && profile.consents.code_of_conduct_and_media_release === true
  ) return true;
  return undefined;
}

function verifiedValue(field, raw) {
  if (field.control === "multi_select") {
    if (!Array.isArray(raw) || raw.length < 1 || raw.length > 3) unavailable();
    const value = raw.map(safeScalar);
    if (new Set(value).size !== value.length || value.some((item) => !field.options.includes(item))) unavailable();
    return value;
  }
  if (field.control === "checkbox") {
    if (raw !== true) unavailable();
    return true;
  }
  return safeScalar(raw);
}

function buildLumaFormAnswerPlan(input = {}) {
  const schema = object(input.schema);
  const profile = object(input.profile);
  if (schema.kind !== "luma_registration_form" || !Array.isArray(schema.fields) || schema.fields.length > 50) {
    unavailable();
  }
  const answers = [];
  const unresolved = [];
  for (const field of schema.fields) {
    object(field);
    const raw = explicitAnswer(field, profile);
    if (raw === undefined) {
      if (field.required === true) unresolved.push({ key: field.key, label: field.label });
      continue;
    }
    answers.push({ key: field.key, control: field.control, value: verifiedValue(field, raw) });
  }
  if (unresolved.length > 0) {
    return Object.freeze({
      status: "candidate_not_actionable",
      reason: "LUMA_REQUIRED_PROFILE_FIELD_UNAVAILABLE",
      answers: Object.freeze(answers),
      unresolved: Object.freeze(unresolved),
    });
  }
  return Object.freeze({ status: "ready", answers: Object.freeze(answers), unresolved: Object.freeze([]) });
}

module.exports = { buildLumaFormAnswerPlan };
