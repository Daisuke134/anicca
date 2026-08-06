"use strict";

const SAFE_KEY = /^[A-Za-z0-9_.-]{1,160}$/;
const SECRET_SHAPE = /(?:api[_ -]?key|access[_ -]?token|password|secret|cookie|session)/i;

function unavailable() {
  throw new Error("Luma registration form unavailable");
}

function cleanText(value, max = 500) {
  const text = String(value == null ? "" : value).replace(/\s+/g, " ").trim();
  if (!text || text.length > max || /[\x00-\x1f\x7f]/.test(text)) unavailable();
  return text;
}

function cleanLabel(value) {
  return cleanText(value).replace(/\s*\*\s*$/, "").trim();
}

function controlFor(field) {
  const type = String(field.type || "").trim().toLowerCase();
  const tag = String(field.tag || "").trim().toLowerCase();
  if (type === "tel") return "phone";
  if (type === "multi-select") return "multi_select";
  if (type === "checkbox") return "checkbox";
  if (type === "radio") return "radio";
  if (tag === "select") return "select";
  if (tag === "textarea") return "textarea";
  if (["text", "email", "url"].includes(type)) return type;
  unavailable();
}

function normalizeLumaRegistrationForm(rawFields) {
  if (!Array.isArray(rawFields) || rawFields.length < 1 || rawFields.length > 50) unavailable();
  const seen = new Set();
  const fields = rawFields.map((raw) => {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) unavailable();
    const key = String(raw.name == null ? "" : raw.name).trim();
    const label = cleanLabel(raw.label);
    if (!SAFE_KEY.test(key) || seen.has(key) || SECRET_SHAPE.test(`${key} ${label}`)) unavailable();
    seen.add(key);
    const options = Array.isArray(raw.options) ? raw.options.map((value) => cleanText(value, 200)) : unavailable();
    if (options.length > 100 || new Set(options).size !== options.length) unavailable();
    return Object.freeze({
      key,
      label,
      control: controlFor(raw),
      required: raw.html_required === true || raw.app_required === true,
      options: Object.freeze(options),
    });
  });
  return Object.freeze({ kind: "luma_registration_form", fields: Object.freeze(fields) });
}

module.exports = { normalizeLumaRegistrationForm };
