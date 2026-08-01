"use strict";

const { createHash } = require("node:crypto");

const { canonicalEventUrl } = require("./canonical-event-url.js");
const { isVerifiedLumaCandidateSequence } = require("./luma-candidate-loop.js");

const DATE = /^(\d{4})-(\d{2})-(\d{2})$/;
const CONNPASS_HOST = /^(?:[a-z0-9-]+\.)?connpass\.com$/i;
const SUBDOMAIN = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/;
const CAPABILITIES = new WeakSet();
const PLANS = new WeakSet();
const HANDOFFS = new WeakSet();

function invalid() { throw new Error("event source handoff invalid"); }

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => (
      `${JSON.stringify(key)}:${stableJson(value[key])}`
    )).join(",")}}`;
  }
  return JSON.stringify(value);
}

function verified(set, value) {
  const result = Object.freeze(value);
  set.add(result);
  return result;
}

function validDate(value) {
  const match = DATE.exec(String(value == null ? "" : value));
  if (!match) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(date.getTime())
    && date.getUTCFullYear() === Number(match[1])
    && date.getUTCMonth() + 1 === Number(match[2])
    && date.getUTCDate() === Number(match[3]);
}

function createEventSourceCapabilities(options = {}) {
  const rawKey = String(options.connpassApiKey == null ? "" : options.connpassApiKey);
  const hasKey = rawKey.length > 0;
  if (hasKey && (
    rawKey !== rawKey.trim()
    || rawKey.length < 24
    || rawKey.length > 512
    || /[\s\x00-\x1f\x7f]/.test(rawKey)
  )) invalid();
  return verified(CAPABILITIES, {
    policy_version: 1,
    sources: Object.freeze({
      luma: Object.freeze({
        status: "active",
        discovery_allowed: true,
        registration_allowed: true,
        coverage_credit: true,
        transport: "cloakbrowser_daily_driver",
      }),
      connpass: Object.freeze({
        status: hasKey ? "official_api_discovery_only" : "blocked_missing_key",
        discovery_allowed: hasKey,
        registration_allowed: false,
        coverage_credit: false,
        transport: hasKey ? "official_v2_get" : "none",
      }),
    }),
  });
}

function isVerifiedEventSourceCapabilities(value) {
  return Boolean(value && typeof value === "object" && CAPABILITIES.has(value));
}

function planEventSourceHandoff(input = {}) {
  const date = String(input.date == null ? "" : input.date);
  if (
    !validDate(date)
    || !isVerifiedLumaCandidateSequence(input.lumaOutcome)
    || input.lumaOutcome.status !== "next_provider_required"
    || input.lumaOutcome.reason !== "luma_candidates_exhausted"
    || !isVerifiedEventSourceCapabilities(input.capabilities)
  ) invalid();
  return verified(PLANS, {
    date,
    connpass_discovery_allowed: input.capabilities.sources.connpass.discovery_allowed,
  });
}

function safeText(value, max, required = false) {
  const text = String(value == null ? "" : value).replace(/\s+/g, " ").trim();
  if ((required && !text) || text.length > max) invalid();
  return text || null;
}

function connpassUrl(event, id) {
  if (event.url != null && String(event.url).trim()) {
    const canonical = canonicalEventUrl(event.url);
    if (!canonical || !CONNPASS_HOST.test(new URL(canonical).hostname)) invalid();
    return canonical;
  }
  const subdomain = String(event.group && event.group.subdomain || "").trim().toLowerCase();
  if (!SUBDOMAIN.test(subdomain)) invalid();
  return `https://${subdomain}.connpass.com/event/${id}/`;
}

function normalizeEvent(event) {
  if (!event || typeof event !== "object" || Array.isArray(event)) invalid();
  const id = Number(event.id);
  if (!Number.isSafeInteger(id) || id < 1) invalid();
  const startsAt = safeText(event.started_at, 64, true);
  const endsAt = safeText(event.ended_at, 64, true);
  if (!Number.isFinite(Date.parse(startsAt)) || !Number.isFinite(Date.parse(endsAt))) invalid();
  return Object.freeze({
    provider: "connpass",
    event_ref: `connpass-event://event/${id}`,
    canonical_url: connpassUrl(event, id),
    title: safeText(event.title, 500, true),
    summary: safeText(event.catch, 2_000),
    description: safeText(event.description, 100_000),
    starts_at: startsAt,
    ends_at: endsAt,
    venue_name: safeText(event.place, 1_000),
    address: safeText(event.address, 1_000),
    source_mode: "official_api_read_only",
    registration_allowed: false,
    coverage_credit: false,
  });
}

function handoff(core) {
  const digest = createHash("sha256").update(stableJson(core), "utf8").digest("hex");
  return verified(HANDOFFS, { handoff_id: `event-source-handoff:${digest}`, ...core });
}

async function executeEventSourceHandoff(input = {}) {
  const plan = input.plan;
  if (!plan || typeof plan !== "object" || !PLANS.has(plan)) invalid();
  if (!plan.connpass_discovery_allowed) {
    return handoff({
      date: plan.date,
      status: "waiting_for_authorized_source",
      coverage_status: "open",
      advisory_candidates: Object.freeze([]),
      coverage_credit_count: 0,
      network_call_count: 0,
      next_actions: Object.freeze(["watch_connpass_api_key", "rediscover_luma"]),
    });
  }
  if (!input.connpassClient || typeof input.connpassClient.searchEvents !== "function") invalid();

  const ymd = plan.date.replaceAll("-", "");
  const candidates = [];
  let start = 1;
  let available = null;
  let networkCalls = 0;
  for (let pageNumber = 0; pageNumber < 100; pageNumber += 1) {
    let page;
    try {
      networkCalls += 1;
      page = await input.connpassClient.searchEvents({ ymd: [ymd], count: 100, order: 2, start });
    } catch {
      return handoff({
        date: plan.date,
        status: "authorized_source_unavailable",
        coverage_status: "open",
        advisory_candidates: Object.freeze([]),
        coverage_credit_count: 0,
        network_call_count: networkCalls,
        next_actions: Object.freeze(["rediscover_luma", "retry_connpass_api"]),
      });
    }
    if (
      !page || typeof page !== "object" || Array.isArray(page)
      || !Number.isSafeInteger(page.results_returned) || page.results_returned < 0
      || !Number.isSafeInteger(page.results_available) || page.results_available < 0
      || !Number.isSafeInteger(page.results_start) || page.results_start !== start
      || !Array.isArray(page.events) || page.events.length !== page.results_returned
      || page.results_available < page.results_returned
      || (available !== null && page.results_available !== available)
    ) invalid();
    available = page.results_available;
    for (const event of page.events) candidates.push(normalizeEvent(event));
    if (candidates.length > available) invalid();
    if (candidates.length === available) break;
    if (page.results_returned === 0) invalid();
    start += page.results_returned;
    if (pageNumber === 99) invalid();
  }
  const empty = candidates.length === 0;
  return handoff({
    date: plan.date,
    status: empty ? "authorized_source_empty" : "advisory_candidates_found",
    coverage_status: "open",
    advisory_candidates: Object.freeze(candidates),
    coverage_credit_count: 0,
    network_call_count: networkCalls,
    next_actions: Object.freeze(["rediscover_luma"]),
  });
}

function isVerifiedEventSourceHandoff(value) {
  return Boolean(value && typeof value === "object" && HANDOFFS.has(value));
}

module.exports = {
  createEventSourceCapabilities,
  executeEventSourceHandoff,
  isVerifiedEventSourceCapabilities,
  isVerifiedEventSourceHandoff,
  planEventSourceHandoff,
};
