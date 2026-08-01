"use strict";

const API_URL = "https://connpass.com/api/v2/events/";
const ARRAY_KEYS = new Set(["event_id", "keyword", "keyword_or", "ym", "ymd", "publish_ym", "publish_ymd", "nickname"]);
const INTEGER_KEYS = new Set(["order", "start", "count"]);

function unavailable() {
  return new Error("connpass API unavailable");
}

function invalidQuery() {
  return new Error("connpass API query invalid");
}

function normalizeQuery(input = {}) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw invalidQuery();
  const params = new URLSearchParams();
  for (const [key, raw] of Object.entries(input)) {
    if (ARRAY_KEYS.has(key)) {
      if (!Array.isArray(raw) || raw.length < 1 || raw.length > 100) throw invalidQuery();
      for (const item of raw) {
        const value = String(item == null ? "" : item).trim();
        if (!value || value.length > 300) throw invalidQuery();
        if ((key === "ymd" || key === "publish_ymd") && !/^\d{8}$/.test(value)) throw invalidQuery();
        if ((key === "ym" || key === "publish_ym") && !/^\d{6}$/.test(value)) throw invalidQuery();
        if (key === "event_id" && !/^\d+$/.test(value)) throw invalidQuery();
        params.append(key, value);
      }
      continue;
    }
    if (INTEGER_KEYS.has(key)) {
      if (!Number.isSafeInteger(raw)) throw invalidQuery();
      if (key === "count" && (raw < 1 || raw > 100)) throw invalidQuery();
      if (key === "start" && raw < 1) throw invalidQuery();
      if (key === "order" && ![1, 2, 3].includes(raw)) throw invalidQuery();
      params.set(key, String(raw));
      continue;
    }
    throw invalidQuery();
  }
  return params;
}

function validPayload(payload) {
  return payload
    && Number.isSafeInteger(payload.results_returned)
    && Number.isSafeInteger(payload.results_available)
    && Number.isSafeInteger(payload.results_start)
    && Array.isArray(payload.events);
}

function createConnpassApiClient(options = {}) {
  const apiKey = String(options.apiKey == null ? "" : options.apiKey).trim();
  const fetchImpl = options.fetchImpl || globalThis.fetch;
  const now = options.now || Date.now;
  const sleep = options.sleep || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  if (
    apiKey.length < 24
    || apiKey.length > 512
    || /[\s\x00-\x1f\x7f]/.test(apiKey)
    || typeof fetchImpl !== "function"
    || typeof now !== "function"
    || typeof sleep !== "function"
  ) throw unavailable();

  let queue = Promise.resolve();
  let lastStartedAt = null;

  async function perform(query) {
    const params = normalizeQuery(query);
    const current = Number(now());
    if (!Number.isFinite(current)) throw unavailable();
    let started = current;
    if (lastStartedAt !== null) {
      const remaining = 5_000 - (current - lastStartedAt);
      if (remaining > 0) {
        await sleep(remaining);
        started = Number(now());
      }
    }
    if (!Number.isFinite(started)) throw unavailable();
    lastStartedAt = started;
    let response;
    try {
      response = await fetchImpl(`${API_URL}?${params.toString()}`, {
        method: "GET",
        headers: {
          Accept: "application/json",
          "X-API-Key": apiKey,
        },
      });
    } catch {
      throw unavailable();
    }
    if (!response || response.ok !== true || response.status !== 200) throw unavailable();
    let payload;
    try { payload = await response.json(); } catch { throw unavailable(); }
    if (!validPayload(payload)) throw unavailable();
    return Object.freeze({
      results_returned: payload.results_returned,
      results_available: payload.results_available,
      results_start: payload.results_start,
      events: Object.freeze(payload.events.map((event) => Object.freeze({ ...event }))),
    });
  }

  return Object.freeze({
    searchEvents(query) {
      const next = queue.then(() => perform(query));
      queue = next.catch(() => {});
      return next;
    },
  });
}

module.exports = {
  API_URL,
  createConnpassApiClient,
  normalizeQuery,
};
