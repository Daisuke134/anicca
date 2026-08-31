"use strict";

const { createHash } = require("node:crypto");
const { zonedSlotInstant } = require("./honne-ja-shadow-schedule.js");

const TIME_ZONE = "Asia/Tokyo";
const LIST_URL = "https://www.doorkeeper.jp/prefectures/tokyo/events";
const LIST_PAGE_LIMIT = 10;
const EVENT_REF = /^doorkeeper-event:\/\/event\/[1-9][0-9]*$/;
const EVENT_URL = /^https:\/\/([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)\.doorkeeper\.jp\/events\/([1-9][0-9]*)$/;
const TOKYO_VENUE_URL = "https://www.doorkeeper.jp/prefectures/tokyo";
const OFFLINE_MODE = "https://schema.org/OfflineEventAttendanceMode";
const IN_STOCK = "https://schema.org/InStock";
const UNAVAILABLE_MARKER = /(?:中止|延期|受付終了|満席|キャンセル待ち|wait\s*list|waitlist|sold\s*out|cancel(?:led|ed)?|\bfull\b)/i;
const MONEY_MARKER = /(?:[$€£¥￥]\s*\d|\b\d[\d,]*(?:\.\d+)?\s*(?:円|jpy|yen)|有料|参加費\s*(?:あり|必要)|料金\s*(?:あり|必要)|会場払い|payment\s+required)/i;
const READBACK_UNSAFE_MARKER = /(?:中止|延期|受付終了|支払い|決済|payment|pay(?:ment)?|credit\s*card|クレジット|wait\s*list|waitlist|キャンセル待ち|満席|エラー|\berror\b|\bfailed\b|失敗)/i;
const SAFE_CODES = new Set([
  "DOORKEEPER_LISTING_NAVIGATION_FAILED", "DOORKEEPER_LISTING_READ_FAILED",
  "DOORKEEPER_LISTING_RESULT_CONTRACT_FAILED", "DOORKEEPER_DISCOVERY_PAGE_LIMIT_FAILED",
  "DOORKEEPER_DETAIL_NAVIGATION_FAILED", "DOORKEEPER_DETAIL_READ_FAILED", "DOORKEEPER_DETAIL_IDENTITY_MISMATCH_FAILED",
  "DOORKEEPER_CALENDAR_CONFLICT_CHECK_FAILED", "DOORKEEPER_REGISTRATION_READ_FAILED",
]);

function invalid() {
  throw new Error("Doorkeeper workflow invalid");
}

function stageError(code) {
  const error = new Error("Doorkeeper workflow stage failed");
  error.code = code;
  return error;
}

function preserveSafe(error, fallback) {
  const code = String(error && error.code || "");
  return stageError(SAFE_CODES.has(code) ? code : fallback);
}

function actualNavigationUrl(page, response) {
  try {
    if (page && typeof page.url === "function") return String(page.url());
  } catch { return ""; }
  try {
    if (response && typeof response.url === "function") return String(response.url());
    if (response && typeof response.url === "string") return response.url;
  } catch { return ""; }
  return "";
}

function assertNavigationUrl(page, response, expected, code) {
  if (actualNavigationUrl(page, response) !== expected) throw stageError(code);
}

function localParts(value) {
  if (!(value instanceof Date) || !Number.isFinite(value.getTime())) invalid();
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone: TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(value).filter((part) => part.type !== "literal")
    .map((part) => [part.type, Number(part.value)]));
  if (![parts.year, parts.month, parts.day].every(Number.isInteger)) invalid();
  return parts;
}

function dateString(parts) {
  return [parts.year, parts.month, parts.day]
    .map((part) => String(part).padStart(2, "0")).join("-");
}

function candidateWindow(observed) {
  const parts = localParts(observed);
  const end = new Date(Date.UTC(parts.year, parts.month - 1, parts.day + 14));
  return Object.freeze({
    start: Date.parse(zonedSlotInstant(parts, "00:00", TIME_ZONE)),
    end: Date.parse(zonedSlotInstant({
      year: end.getUTCFullYear(),
      month: end.getUTCMonth() + 1,
      day: end.getUTCDate(),
    }, "00:00", TIME_ZONE)),
    start_day: dateString(parts),
    end_day: dateString({
      year: end.getUTCFullYear(),
      month: end.getUTCMonth() + 1,
      day: end.getUTCDate(),
    }),
  });
}

function exactUrl(value) {
  const raw = String(value == null ? "" : value).trim();
  const match = EVENT_URL.exec(raw);
  return match && match[1] !== "www"
    ? Object.freeze({ canonical_url: raw, group: match[1], id: match[2] }) : null;
}

function canonicalBinding(value) {
  const row = typeof value === "string" ? { canonical_url: value } : value;
  if (!row || typeof row !== "object" || Array.isArray(row)) return null;
  const parsed = exactUrl(row.canonical_url || row.href || row.url);
  if (!parsed) return null;
  const eventRef = `doorkeeper-event://event/${parsed.id}`;
  if (row.event_ref != null && String(row.event_ref) !== eventRef) return null;
  return Object.freeze({ event_ref: eventRef, canonical_url: parsed.canonical_url });
}

function exactCandidate(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)
    || value.provider !== "doorkeeper" || !EVENT_REF.test(String(value.event_ref || ""))) invalid();
  const binding = canonicalBinding(value);
  if (!binding || binding.event_ref !== value.event_ref || binding.canonical_url !== value.canonical_url) invalid();
  if (value.title != null && !String(value.title).trim()) invalid();
  if (value.starts_at != null && !Number.isFinite(Date.parse(String(value.starts_at)))) invalid();
  if (value.ends_at != null && !Number.isFinite(Date.parse(String(value.ends_at)))) invalid();
  if (value.starts_at != null && value.ends_at != null
    && Date.parse(value.starts_at) >= Date.parse(value.ends_at)) invalid();
  return value;
}

function parseListingDay(value) {
  const raw = String(value == null ? "" : value).trim();
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const check = new Date(Date.UTC(year, month - 1, day));
  return check.getUTCFullYear() === year && check.getUTCMonth() + 1 === month && check.getUTCDate() === day
    ? raw : null;
}

function parseListingDateText(value) {
  const raw = String(value == null ? "" : value).replace(/\s+/g, " ").trim();
  const match = /^(\d{4})年(\d{1,2})月(\d{1,2})日$/.exec(raw);
  if (!match) return null;
  return parseListingDay(`${match[1]}-${match[2].padStart(2, "0")}-${match[3].padStart(2, "0")}`);
}

function jsonLdEvent(raw) {
  const source = raw && typeof raw === "object" && !Array.isArray(raw)
    && (raw.jsonld !== undefined || raw.jsonLd !== undefined) ? (raw.jsonld ?? raw.jsonLd) : raw;
  const nodes = Array.isArray(source) ? source
    : source && Array.isArray(source["@graph"]) ? source["@graph"] : [source];
  return nodes.find((node) => {
    const type = node && node["@type"];
    const types = Array.isArray(type) ? type : [type];
    return types.some((value) => value === "Event" || String(value || "").endsWith("/Event"));
  }) || null;
}

function eventIdentityMatches(event, binding) {
  if (!event) return false;
  const main = event.mainEntityOfPage;
  const fallbackUrl = typeof main === "string" ? main : main && (main.url || main["@id"]);
  const eventUrl = event.url != null ? event.url : fallbackUrl;
  if (String(eventUrl || "").trim() !== binding.canonical_url) return false;
  const expectedId = binding.event_ref.split("/").pop();
  for (const value of [event.id, event.identifier, event["@id"]]) {
    if (value == null || String(value).trim() === "") continue;
    const raw = String(value).trim();
    if (/^[1-9][0-9]*$/.test(raw)) {
      if (raw !== expectedId) return false;
    } else if (raw !== binding.canonical_url && raw !== binding.event_ref) {
      return false;
    }
  }
  return true;
}

function controlsOf(raw) {
  const controls = raw && (raw.controls || raw.buttons || raw.visible_controls);
  if (!Array.isArray(controls)) return [];
  return controls.map((control) => (typeof control === "string"
    ? { text: control.trim(), visible: true }
    : { text: String(control && (control.text ?? control.label ?? control.innerText) || "").trim(), visible: control && control.visible === true }));
}

function bodyText(raw, event) {
  return [raw && (raw.body_text ?? raw.bodyText), raw && raw.description, event && event.description]
    .filter((value) => value != null && String(value).trim()).map((value) => String(value)).join(" ");
}

function locationIsTokyo(event) {
  const locations = Array.isArray(event && event.location) ? event.location : [event && event.location];
  return locations.length > 0 && locations.every((location) => {
    const address = location && (location.address || location);
    if (typeof address === "string") return /(?:東京|Tokyo)/i.test(address);
    if (!address || typeof address !== "object") return false;
    const countryValue = address.addressCountry || address.country || "";
    const country = String(typeof countryValue === "object" ? countryValue.name : countryValue).trim().toLowerCase();
    if (country && !["jp", "japan", "日本"].includes(country)) return false;
    const text = [address.addressLocality, address.city, address.addressRegion, address.region,
      address.streetAddress, address.postalCode].filter(Boolean).join(" ");
    return /(?:東京|Tokyo)/i.test(text);
  });
}

function offlineMode(event) {
  const modes = Array.isArray(event && event.eventAttendanceMode)
    ? event.eventAttendanceMode : [event && event.eventAttendanceMode];
  return modes.length > 0 && modes.every((mode) => String(mode || "") === OFFLINE_MODE);
}

function freeOffers(event, canonicalUrl) {
  const offers = Array.isArray(event && event.offers) ? event.offers : [event && event.offers];
  if (!offers.length || offers.some((offer) => !offer || typeof offer !== "object" || Array.isArray(offer))) return false;
  return offers.every((offer) => {
    const price = offer.price;
    const numericZero = typeof price === "number"
      ? Number.isFinite(price) && price === 0
      : typeof price === "string" && /^\s*0+(?:\.0+)?\s*$/.test(price);
    return String(offer.url || "").trim() === canonicalUrl
      && String(offer.availability || "") === IN_STOCK
      && String(offer.priceCurrency || "") === "JPY"
      && numericZero;
  });
}

function normalizeDetail(binding, raw) {
  const event = jsonLdEvent(raw);
  if (!event) return null;
  if (!eventIdentityMatches(event, binding)) throw stageError("DOORKEEPER_DETAIL_IDENTITY_MISMATCH_FAILED");
  const starts = Date.parse(String(event.startDate || ""));
  const ends = Date.parse(String(event.endDate || ""));
  const title = String(event.name || "").trim();
  if (!title || !Number.isFinite(starts) || !Number.isFinite(ends)) return null;
  const controls = controlsOf(raw);
  const text = bodyText(raw, event);
  const unavailable = UNAVAILABLE_MARKER.test(text) || controls.some((control) => UNAVAILABLE_MARKER.test(control.text));
  const submitControls = controls.filter((control) => control.text === "申し込む" && control.visible);
  const candidate = Object.freeze({
    provider: "doorkeeper",
    event_ref: binding.event_ref,
    canonical_url: binding.canonical_url,
    title,
    starts_at: new Date(starts).toISOString(),
    ends_at: new Date(ends).toISOString(),
    registration_status: "available",
    ticket_price_status: "free",
    ticket_price_minor: 0,
  });
  return Object.freeze({ candidate, free_open: starts < ends && offlineMode(event)
    && locationIsTokyo(event) && freeOffers(event, binding.canonical_url)
    && submitControls.length === 1 && submitControls[0].visible
    && !unavailable && !MONEY_MARKER.test(text) });
}

function calendarIntervals(calendar) {
  return Array.isArray(calendar) ? calendar
    : calendar && Array.isArray(calendar.busy_intervals) ? calendar.busy_intervals : [];
}

function overlaps(candidate, busy) {
  if (!busy || busy.kind !== "timed") return false;
  const start = Date.parse(candidate.starts_at);
  const end = Date.parse(candidate.ends_at);
  const busyStart = Date.parse(busy.start_at);
  const busyEnd = Date.parse(busy.end_at);
  return [start, end, busyStart, busyEnd].every(Number.isFinite)
    && start < busyEnd && end > busyStart;
}

function exactCoverage(candidate, busy) {
  return overlaps(candidate, busy)
    && String(busy.connector_idempotency || "") === createHash("sha256")
      .update(candidate.canonical_url, "utf8").digest("hex");
}

function defaultCalendarFree(candidate, calendar) {
  return !calendarIntervals(calendar).some((busy) => overlaps(candidate, busy) && !exactCoverage(candidate, busy));
}

async function defaultReadListingPage(page, pageNumber) {
  if (!page || typeof page.goto !== "function" || typeof page.evaluate !== "function") invalid();
  const url = pageNumber === 1 ? LIST_URL : `${LIST_URL}?page=${pageNumber}`;
  let response;
  try {
    response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30_000 });
  } catch { throw stageError("DOORKEEPER_LISTING_NAVIGATION_FAILED"); }
  assertNavigationUrl(page, response, url, "DOORKEEPER_LISTING_NAVIGATION_FAILED");
  let payload;
  try {
    payload = await page.evaluate(() => {
      const items = [...document.querySelectorAll(".global-event.events-list")]
        .filter((item) => item.querySelector("a[href]"));
      const rows = items.map((item) => {
        const titleAnchor = item.querySelector("a[href*='/events/']") || item.querySelector("a[href]");
        const dateNode = item.querySelector(".events-list-item-time-date");
        const venueAnchor = [...item.querySelectorAll("a[href]")].find((anchor) => /\/prefectures\/tokyo(?:$|[?#])/.test(anchor.href))
          || item.querySelector("a[href*='/prefectures/']");
        return {
          canonical_url: titleAnchor ? titleAnchor.href : "",
          day_text: dateNode ? String(dateNode.textContent || dateNode.innerText || "").trim() : "",
          venue_url: venueAnchor ? venueAnchor.href : "",
        };
      });
      const next = [...document.querySelectorAll("a[rel='next'], .pagination a")]
        .some((anchor) => anchor.href && /(?:次へ|next)/i.test(String(anchor.textContent || anchor.innerText || ""))
          && !/disabled/i.test(String(anchor.className || "")));
      return { rows, has_next: next };
    });
  } catch { throw stageError("DOORKEEPER_LISTING_READ_FAILED"); }
  if (!payload || typeof payload !== "object" || !Array.isArray(payload.rows) || typeof payload.has_next !== "boolean") {
    throw stageError("DOORKEEPER_LISTING_RESULT_CONTRACT_FAILED");
  }
  return Object.freeze({
    rows: payload.rows.map((row) => Object.freeze({
      canonical_url: String(row && (row.canonical_url || row.href || "")),
      day: parseListingDay(row && row.day) || parseListingDateText(row && row.day_text),
      venue_url: String(row && (row.venue_url || "")),
    })),
    has_next: payload.has_next,
  });
}

async function defaultReadEventDetail(page, canonicalUrl) {
  if (!page || typeof page.goto !== "function" || typeof page.evaluate !== "function") invalid();
  let response;
  try {
    response = await page.goto(canonicalUrl, { waitUntil: "domcontentloaded", timeout: 30_000 });
  } catch { throw stageError("DOORKEEPER_DETAIL_NAVIGATION_FAILED"); }
  assertNavigationUrl(page, response, canonicalUrl, "DOORKEEPER_DETAIL_NAVIGATION_FAILED");
  try {
    return await page.evaluate(() => {
      const jsonld = [...document.querySelectorAll('script[type="application/ld+json"]')].flatMap((script) => {
        try { return [JSON.parse(script.textContent || "")]; } catch { return []; }
      });
      const controls = [...document.querySelectorAll("a,button,input[type='submit']")].map((node) => ({
        text: String(node.innerText || node.textContent || node.value || "").trim(),
        visible: Boolean(node.offsetWidth || node.offsetHeight),
      }));
      return { jsonld, body_text: document.body ? document.body.innerText : "", controls };
    });
  } catch { throw stageError("DOORKEEPER_DETAIL_READ_FAILED"); }
}

async function defaultReadRegistrationView(page) {
  if (!page || typeof page.evaluate !== "function") invalid();
  let pageUrl = "";
  try { pageUrl = typeof page.url === "function" ? String(page.url()) : ""; } catch { pageUrl = ""; }
  try {
    const view = await page.evaluate(() => {
      const eventUrl = /^https:\/\/([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)\.doorkeeper\.jp\/events\/[1-9][0-9]*$/;
      const links = [...document.querySelectorAll("a[href],link[rel='canonical']")].map((node) => ({
        href: String(node.href || node.getAttribute("href") || ""),
        visible: node.tagName.toLowerCase() === "link" || Boolean(node.offsetWidth || node.offsetHeight),
      })).filter((link) => eventUrl.test(link.href));
      const uniqueLinks = [...links.reduce((map, link) => {
        const existing = map.get(link.href);
        map.set(link.href, existing ? { href: link.href, visible: existing.visible || link.visible } : link);
        return map;
      }, new Map()).values()];
      const controls = [...document.querySelectorAll("a,button,input[type='submit']")].map((node) => ({
        text: String(node.innerText || node.textContent || node.value || "").trim(),
        visible: Boolean(node.offsetWidth || node.offsetHeight),
      }));
      return { canonical_links: uniqueLinks, controls, body_text: document.body ? document.body.innerText : "" };
    });
    return { page_url: pageUrl, ...(view || {}) };
  } catch { throw stageError("DOORKEEPER_REGISTRATION_READ_FAILED"); }
}

function normalizedRegistrationView(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const links = Array.isArray(value.canonical_links) ? value.canonical_links.map((link) => ({
    href: String(link && (link.href || link.url) || "").trim(), visible: link && link.visible === true,
  })) : [];
  return {
    page_url: String(value.page_url || "").trim(),
    canonical_links: links,
    controls: controlsOf(value),
    body_text: String(value.body_text || value.bodyText || ""),
  };
}

function completionCount(text) {
  const source = String(text || "");
  const first = source.split("申し込みが完了しました").length - 1;
  const second = source.split("Your registration is complete").length - 1;
  return first + second;
}

// Measured live 2026-08-18 (see docs/superpowers/plans/2026-08-16-connector-core-recovery-execution-notes.md,
// "Doorkeeper is logged out too"): a logged-out doorkeeper.jp shows both a
// "ログイン" and a "新規登録" control in the page header, on every page —
// including the event page runDirectAction already has open (the runner
// navigates there before calling this), so no extra navigation is needed.
// Requiring both (not just one) keeps this from firing on an unrelated
// control that merely contains one of the two words, e.g. a genuinely
// closed or full event. Mirrors peatixSessionExpired in
// peatix-browser-provider.js.
async function doorkeeperSessionExpired(page) {
  if (!page || typeof page.evaluate !== "function") return false;
  let observed;
  try {
    observed = await page.evaluate(() => {
      const clean = (x) => String(x || "").replace(/\s+/g, " ").trim();
      const texts = new Set([...document.querySelectorAll("a,button")].map((el) => (
        clean(el.innerText || el.value || el.getAttribute("aria-label") || "")
      )));
      return { login: texts.has("ログイン"), signup: texts.has("新規登録") };
    });
  } catch { return false; }
  return Boolean(observed && observed.login === true && observed.signup === true);
}

function createDoorkeeperScriptFirstWorkflow(options = {}) {
  const now = options.now || (() => new Date());
  const readListingPage = options.readListingPage || defaultReadListingPage;
  const readEventDetail = options.readEventDetail || defaultReadEventDetail;
  const readRegistrationView = options.readRegistrationView || defaultReadRegistrationView;
  const isCalendarFree = options.isCalendarFree || defaultCalendarFree;
  const onDiscoveryAudit = options.onDiscoveryAudit || (() => {});
  if ([now, readListingPage, readEventDetail, readRegistrationView, isCalendarFree, onDiscoveryAudit]
    .some((value) => typeof value !== "function")) invalid();

  return Object.freeze({
    async discoverCandidates({ page, calendar }) {
      const observed = now();
      if (!(observed instanceof Date) || !Number.isFinite(observed.getTime())) invalid();
      const window = candidateWindow(observed);
      const bindings = [];
      const seen = new Set();
      let observedCount = 0;
      let windowCount = 0;
      let lastMaxDay = null;
      for (let pageNumber = 1; pageNumber <= LIST_PAGE_LIMIT; pageNumber += 1) {
        let payload;
        try { payload = await readListingPage(page, pageNumber); }
        catch (error) { throw preserveSafe(error, "DOORKEEPER_LISTING_READ_FAILED"); }
        if (!payload || typeof payload !== "object" || !Array.isArray(payload.rows)
          || typeof payload.has_next !== "boolean") throw stageError("DOORKEEPER_LISTING_RESULT_CONTRACT_FAILED");
        observedCount += payload.rows.length;
        for (const row of payload.rows) {
          const day = parseListingDay(row && row.day);
          if (day && (!lastMaxDay || day > lastMaxDay)) lastMaxDay = day;
          const binding = canonicalBinding(row);
          if (!binding || seen.has(binding.event_ref)) continue;
          seen.add(binding.event_ref);
          if (!day || day < window.start_day || day >= window.end_day
            || String(row.venue_url || "") !== TOKYO_VENUE_URL) continue;
          windowCount += 1;
          bindings.push(binding);
        }
        if (!payload.has_next || (lastMaxDay && lastMaxDay >= window.end_day)) break;
        if (pageNumber === LIST_PAGE_LIMIT) throw stageError("DOORKEEPER_DISCOVERY_PAGE_LIMIT_FAILED");
      }

      const exactCovered = [];
      const unprocessed = [];
      let freeOpenCount = 0;
      for (const binding of bindings) {
        let raw;
        try { raw = await readEventDetail(page, binding.canonical_url); }
        catch (error) { throw preserveSafe(error, "DOORKEEPER_DETAIL_READ_FAILED"); }
        let normalized;
        try { normalized = normalizeDetail(binding, raw); }
        catch (error) {
          if (String(error && error.code || "") === "DOORKEEPER_DETAIL_IDENTITY_MISMATCH_FAILED") throw error;
          continue;
        }
        if (!normalized) continue;
        const candidate = normalized.candidate;
        const startsAt = Date.parse(candidate.starts_at);
        if (startsAt < window.start || startsAt >= window.end || !normalized.free_open) continue;
        freeOpenCount += 1;
        let calendarFree;
        try { calendarFree = await isCalendarFree(candidate, calendar); }
        catch { throw stageError("DOORKEEPER_CALENDAR_CONFLICT_CHECK_FAILED"); }
        if (!calendarFree) continue;
        const covered = calendarIntervals(calendar).some((busy) => exactCoverage(candidate, busy));
        (covered ? exactCovered : unprocessed).push(candidate);
      }
      const selectedCount = exactCovered.length + unprocessed.length;
      await onDiscoveryAudit(Object.freeze({
        discovered_count: observedCount,
        within_window_count: windowCount,
        eligible_count: freeOpenCount,
        calendar_free_count: selectedCount,
        selected_count: selectedCount,
      }));
      return Object.freeze([...exactCovered, ...unprocessed]);
    },

    async runDirectAction({ page, candidate }) {
      exactCandidate(candidate);
      if (await doorkeeperSessionExpired(page)) {
        return Object.freeze({ status: "failed", safe_reason: "doorkeeper_session_expired" });
      }
      return Object.freeze({ status: "failed", safe_reason: "doorkeeper_direct_requires_harness" });
    },

    async readProviderState({ page, candidate }) {
      const selected = exactCandidate(candidate);
      let currentUrl = "";
      let hasCurrentUrl = false;
      try {
        hasCurrentUrl = Boolean(page && typeof page.url === "function");
        currentUrl = hasCurrentUrl ? String(page.url()) : "";
      } catch { return Object.freeze({ status: "unavailable" }); }
      if (hasCurrentUrl && currentUrl !== selected.canonical_url) return Object.freeze({ status: "unavailable" });
      let view;
      try { view = normalizedRegistrationView(await readRegistrationView(page, selected)); }
      catch { return Object.freeze({ status: "unavailable" }); }
      if (hasCurrentUrl) {
        try {
          if (String(page.url()) !== selected.canonical_url) return Object.freeze({ status: "unavailable" });
        } catch { return Object.freeze({ status: "unavailable" }); }
      }
      if (!view || view.page_url !== selected.canonical_url) return Object.freeze({ status: "unavailable" });
      const visibleLinks = view.canonical_links.filter((link) => link.visible);
      if (view.canonical_links.some((link) => link.href !== selected.canonical_url)
        || view.canonical_links.length > 1) return Object.freeze({ status: "unavailable" });
      const linkIsExact = visibleLinks.length === 1 && visibleLinks[0].href === selected.canonical_url;
      const body = view.body_text;
      const visibleControlText = view.controls.filter((control) => control.visible).map((control) => control.text).join(" ");
      const visibleControlUnsafe = READBACK_UNSAFE_MARKER.test(visibleControlText);
      const hiddenCompletionMarker = view.controls.some((control) => !control.visible && completionCount(control.text) > 0);
      if (hiddenCompletionMarker) return Object.freeze({ status: "unavailable" });
      if (linkIsExact && completionCount(body) === 1 && !READBACK_UNSAFE_MARKER.test(body) && !visibleControlUnsafe) {
        return Object.freeze({ status: "registered" });
      }
      const submitControls = view.controls.filter((control) => control.text === "申し込む");
      const visibleLinksSafe = visibleLinks.length === 0
        || (visibleLinks.length === 1 && visibleLinks[0].href === selected.canonical_url);
      if (visibleLinksSafe && submitControls.length === 1 && submitControls[0].visible && completionCount(body) === 0
        && !READBACK_UNSAFE_MARKER.test(body) && !visibleControlUnsafe) return Object.freeze({ status: "absent" });
      return Object.freeze({ status: "unavailable" });
    },
  });
}

module.exports = { createDoorkeeperScriptFirstWorkflow };
