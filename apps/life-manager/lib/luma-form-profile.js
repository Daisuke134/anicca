"use strict";

const fs = require("node:fs");
const path = require("node:path");

const ROOT_KEYS = Object.freeze(["consents", "form_answers", "phone", "schema_version"]);
const SECRET_VALUE = /(?:api[_ -]?key|access[_ -]?token|\btoken|password|secret|cookie|session)\s*[:=]/i;

function unavailable() { throw new Error("Luma form profile unavailable"); }

function safeText(value, max = 2_000) {
  const text = String(value == null ? "" : value).trim();
  if (!text || text.length > max || /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(text) || SECRET_VALUE.test(text)) {
    unavailable();
  }
  return text;
}

function answer(value) {
  if (typeof value === "boolean") return value;
  if (Array.isArray(value)) {
    if (value.length < 1 || value.length > 3) unavailable();
    const values = value.map((item) => safeText(item, 200));
    if (new Set(values).size !== values.length) unavailable();
    return Object.freeze(values);
  }
  if (typeof value !== "string") unavailable();
  return safeText(value);
}

function readLumaFormProfile(input = {}) {
  const file = path.resolve(String(input.path == null ? "" : input.path));
  if (!path.isAbsolute(file) || file === path.parse(file).root) unavailable();
  let parsed;
  try {
    const stat = fs.statSync(file);
    if (!stat.isFile() || stat.size < 2 || stat.size > 16_384 || (stat.mode & 0o777) !== 0o600) unavailable();
    parsed = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch { unavailable(); }
  if (
    !parsed || typeof parsed !== "object" || Array.isArray(parsed)
    || Object.keys(parsed).sort().join(",") !== [...ROOT_KEYS].sort().join(",")
    || parsed.schema_version !== 1
    || !parsed.form_answers || typeof parsed.form_answers !== "object" || Array.isArray(parsed.form_answers)
    || Object.keys(parsed.form_answers).length > 50
    || !parsed.consents || typeof parsed.consents !== "object" || Array.isArray(parsed.consents)
    || Object.keys(parsed.consents).join(",") !== "code_of_conduct_and_media_release"
    || typeof parsed.consents.code_of_conduct_and_media_release !== "boolean"
  ) unavailable();
  const formAnswers = Object.fromEntries(Object.entries(parsed.form_answers).map(([key, value]) => (
    [safeText(key, 500), answer(value)]
  )));
  return Object.freeze({
    schema_version: 1,
    phone: safeText(parsed.phone, 64),
    form_answers: Object.freeze(formAnswers),
    consents: Object.freeze({
      code_of_conduct_and_media_release: parsed.consents.code_of_conduct_and_media_release,
    }),
  });
}

module.exports = { readLumaFormProfile };
