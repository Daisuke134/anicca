"use strict";

const SECRET_PATTERNS = Object.freeze([
  /ghp_[0-9a-zA-Z]{36}/,
  /github_pat_\w{82}/,
  /glpat-[\w-]{20}/,
  /xoxb-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*/,
  /xox[pe](?:-[0-9]{10,13}){3}-[a-zA-Z0-9-]{28,34}/,
  /npm_[a-z0-9]{36}/i,
  /(?:A3T[A-Z0-9]|AKIA|ASIA|ABIA|ACCA)[A-Z2-7]{16}/,
  /sk_(?:test|live|prod)_[a-zA-Z0-9]{10,99}/,
  /AIza[\w-]{35}/,
  /sk-proj-(?:[A-Za-z0-9_-]{74}|[A-Za-z0-9_-]{58})T3BlbkFJ(?:[A-Za-z0-9_-]{74}|[A-Za-z0-9_-]{58})/,
  /re_[A-Za-z0-9_-]{32}/,
  /KEY[0-9A-F]{32}/,
  /[0-9]{5,16}:A[a-z0-9_-]{34}/i,
  /whsec_[a-zA-Z0-9]{32}/,
  /rk_(?:test|live|prod)_[a-zA-Z0-9]{10,99}/,
  /-----BEGIN[ A-Z0-9_-]{0,100}PRIVATE KEY(?: BLOCK)?-----[\s\S-]{64,}?KEY(?: BLOCK)?-----/i,
  /postgresql:\/\/[^:/?#\s]+:[^@/?#\s]+@[^/?#\s]+\/[^/?#\s]+/,
  /redis:\/\/[^:/?#\s]+:[^@/?#\s]+@[^/:?#\s]+:[0-9]+\/[0-9]+/,
  /mongodb\+srv:\/\/[^:/?#\s]+:[^@/?#\s]+@[^/?#\s]+\/[^/?#\s]+/,
]);

function stringContainsSensitiveDisplayValue(value) {
  return SECRET_PATTERNS.some((pattern) => pattern.test(value));
}

function containsSensitiveDisplayValue(value, seen = new WeakSet()) {
  if (typeof value === "string") return stringContainsSensitiveDisplayValue(value);
  if (!value || typeof value !== "object") return false;
  if (seen.has(value)) return false;
  seen.add(value);
  if (Array.isArray(value)) {
    return value.some((item) => containsSensitiveDisplayValue(item, seen));
  }
  return Object.entries(value).some(([key, item]) => (
    stringContainsSensitiveDisplayValue(key)
    || containsSensitiveDisplayValue(item, seen)
  ));
}

function safeHttpsLink(value) {
  if (typeof value !== "string" || containsSensitiveDisplayValue(value)) return null;
  try {
    const url = new URL(value);
    if (
      url.protocol !== "https:"
      || !url.hostname
      || url.username
      || url.password
      || url.search
    ) return null;
    return url.toString();
  } catch {
    return null;
  }
}

function safeDate(value) {
  if (typeof value !== "string" && typeof value !== "number") return null;
  const parsed = Date.parse(String(value));
  return Number.isFinite(parsed) ? new Date(parsed).toISOString().slice(0, 10) : null;
}

function formatCurrencyAmount(value, currency = "USD") {
  const amount = Number(value);
  if (!Number.isFinite(amount) || !/^[A-Z]{3}$/.test(String(currency || ""))) return null;
  return `${currency} ${amount.toFixed(2)}`;
}

module.exports = {
  SECRET_PATTERNS,
  containsSensitiveDisplayValue,
  formatCurrencyAmount,
  safeDate,
  safeHttpsLink,
};
