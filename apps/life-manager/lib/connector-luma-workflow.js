"use strict";

const {
  advanceLumaTimeline,
  collectLumaInventory,
  readLumaTimelineSnapshot,
} = require("./luma-discovery.js");
const {
  normalizeLumaEventDetail,
  readRawLumaEventDetail,
} = require("./luma-event-detail.js");
const { submitLumaOnPage } = require("./luma-browser-provider.js");

const TOKYO_DISCOVER_URL = "https://luma.com/tokyo?k=p";
const EVENT_REF = /^luma-event:\/\/event\/[A-Za-z0-9_-]+$/;
const CANONICAL_URL = /^https:\/\/luma\.com\/[A-Za-z0-9_-]+$/;
const FALLBACK_CODES = new Set([
  "LUMA_REQUIRED_PROFILE_FIELD_UNAVAILABLE",
  "LUMA_FORM_SCHEMA_UNAVAILABLE",
  "LUMA_FORM_PLAN_UNAVAILABLE",
  "LUMA_FORM_FILL_UNAVAILABLE",
  "LUMA_CONTROL_UNAVAILABLE",
  "LUMA_CONFIRM_UNAVAILABLE",
  "LUMA_BROWSER_ACTION_FAILED",
]);

function invalid() {
  throw new Error("Luma script-first workflow invalid");
}

function exactEvent(input) {
  if (
    !input || typeof input !== "object" || Array.isArray(input)
    || input.provider !== "luma"
    || !EVENT_REF.test(String(input.event_ref || ""))
    || !CANONICAL_URL.test(String(input.canonical_url || ""))
    || !Number.isFinite(Date.parse(String(input.starts_at || "")))
    || !Number.isFinite(Date.parse(String(input.ends_at || "")))
    || Date.parse(input.starts_at) >= Date.parse(input.ends_at)
  ) invalid();
  return input;
}

function isFreeOpen(candidate) {
  return candidate.event_status === "scheduled"
    && ["available", "approval_required"].includes(candidate.rsvp_status)
    && candidate.ticket_price_status === "free"
    && candidate.ticket_price_minor === 0;
}

function defaultCalendarFree(candidate, calendar) {
  const intervals = calendar && Array.isArray(calendar.busy_intervals)
    ? calendar.busy_intervals : [];
  const start = Date.parse(candidate.starts_at);
  const end = Date.parse(candidate.ends_at);
  return !intervals.some((busy) => (
    busy && busy.kind === "timed"
    && start < Date.parse(busy.end_at)
    && end > Date.parse(busy.start_at)
  ));
}

async function defaultDiscoverOnPage({ page }) {
  if (
    !page || typeof page.goto !== "function" || typeof page.evaluate !== "function"
    || typeof page.waitForTimeout !== "function"
  ) invalid();
  await page.goto(TOKYO_DISCOVER_URL, { waitUntil: "domcontentloaded", timeout: 30_000 });
  const inventory = await collectLumaInventory({
    readSnapshot: () => readLumaTimelineSnapshot(page),
    advance: () => advanceLumaTimeline(page),
  });
  const details = [];
  for (const candidate of inventory.candidates) {
    await page.goto(candidate.canonical_url, { waitUntil: "domcontentloaded", timeout: 30_000 });
    const detail = normalizeLumaEventDetail(
      await readRawLumaEventDetail(page, candidate.canonical_url),
    );
    if (detail) details.push(Object.freeze({ provider: "luma", ...detail }));
  }
  return Object.freeze(details);
}

async function defaultReadProviderStateOnPage({ page, candidate }) {
  const detail = normalizeLumaEventDetail(
    await readRawLumaEventDetail(page, candidate.canonical_url),
  );
  if (!detail) return Object.freeze({ status: "unavailable" });
  if (detail.rsvp_status === "registered") return Object.freeze({ status: "registered" });
  if (detail.rsvp_status === "available") return Object.freeze({ status: "absent" });
  return Object.freeze({ status: "unavailable" });
}

function normalizedProviderState(value) {
  const status = String(value && value.status || "");
  if (["registered", "pending"].includes(status)) {
    const receipt = String(value.provider_receipt_id || "");
    return Object.freeze({ status, ...(receipt ? { provider_receipt_id: receipt } : {}) });
  }
  if (["available", "absent"].includes(status)) return Object.freeze({ status: "absent" });
  return Object.freeze({ status: "unavailable" });
}

function createLumaScriptFirstWorkflow(options = {}) {
  const discoverOnPage = options.discoverOnPage || defaultDiscoverOnPage;
  const isCalendarFree = options.isCalendarFree || defaultCalendarFree;
  const submitOnPage = options.submitOnPage || submitLumaOnPage;
  const readProviderStateOnPage = options.readProviderStateOnPage || defaultReadProviderStateOnPage;
  const readLumaFormProfile = options.readLumaFormProfile;
  if (
    typeof discoverOnPage !== "function" || typeof isCalendarFree !== "function"
    || typeof submitOnPage !== "function" || typeof readProviderStateOnPage !== "function"
    || (readLumaFormProfile != null && typeof readLumaFormProfile !== "function")
  ) invalid();

  return Object.freeze({
    async discoverCandidates({ page, calendar }) {
      const observed = await discoverOnPage({ page });
      if (!Array.isArray(observed) || observed.length > 500) invalid();
      const result = [];
      for (const raw of observed) {
        const candidate = exactEvent(raw);
        if (!isFreeOpen(candidate)) continue;
        if (!await isCalendarFree(candidate, calendar)) continue;
        result.push(Object.freeze({ ...candidate }));
      }
      return Object.freeze(result);
    },

    async runDirectAction({ page, candidate }) {
      const selected = exactEvent(candidate);
      try {
        const outcome = await submitOnPage(page, selected, {
          readLumaFormProfile,
          agenticRegister: undefined,
        });
        return outcome && outcome.status === "registered"
          ? Object.freeze({ status: "completed", method: "luma_direct_submit" })
          : Object.freeze({ status: "failed", safe_reason: "direct_action_unverified" });
      } catch (error) {
        return Object.freeze({
          status: "failed",
          safe_reason: FALLBACK_CODES.has(String(error && error.code || ""))
            ? "direct_action_requires_fallback" : "direct_action_failed",
        });
      }
    },

    async readProviderState({ page, candidate }) {
      const selected = exactEvent(candidate);
      return normalizedProviderState(await readProviderStateOnPage({ page, candidate: selected }));
    },
  });
}

module.exports = { createLumaScriptFirstWorkflow };
