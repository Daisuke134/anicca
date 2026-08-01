"use strict";

const API_ORIGIN = "https://connpass.com";
const EVENTS_PATH = "/api/v2/events/";
const API_KEY_REF = /^secret:\/\/[a-z0-9][a-z0-9._/-]{2,100}$/;

function violation() {
  throw new Error("connpass access policy violation");
}

function normalizeKeywords(values) {
  if (!Array.isArray(values) || values.length < 1 || values.length > 10) violation();
  const keywords = values.map((value) => String(value || "").trim());
  if (
    keywords.some((value) => value.length < 1 || value.length > 40 || /[,\r\n]/.test(value))
    || new Set(keywords).size !== keywords.length
  ) violation();
  return keywords;
}

function createConnpassAccessPolicy(options = {}) {
  const apiKeyRef = String(options.apiKeyRef || "").trim();
  if (apiKeyRef && !API_KEY_REF.test(apiKeyRef)) violation();

  return Object.freeze({
    planEventDiscovery(input = {}) {
      if (!apiKeyRef) {
        return Object.freeze({
          status: "disabled",
          reason: "api_key_unavailable",
        });
      }
      if (
        input.trigger !== "scheduled_cache"
        || input.prefecture !== "tokyo"
        || !Number.isInteger(input.retentionDays)
        || input.retentionDays < 1
        || input.retentionDays > 30
        || !Number.isInteger(input.minIntervalMs)
        || input.minIntervalMs < 5_000
      ) violation();
      const keywords = normalizeKeywords(input.keywords);
      return Object.freeze({
        status: "ready",
        method: "GET",
        origin: API_ORIGIN,
        path: EVENTS_PATH,
        query: Object.freeze({
          prefecture: "tokyo",
          keyword_or: keywords.join(","),
          order: "2",
          start: "1",
          count: "100",
        }),
        header: Object.freeze({
          name: "X-API-Key",
          value_ref: apiKeyRef,
        }),
        min_interval_ms: input.minIntervalMs,
        retention_days: input.retentionDays,
        audience: "self_only",
      });
    },
  });
}

module.exports = {
  createConnpassAccessPolicy,
};
