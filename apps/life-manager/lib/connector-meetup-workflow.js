"use strict";

const { createHash } = require("node:crypto");
const { zonedSlotInstant } = require("./honne-ja-shadow-schedule.js");

const TIME_ZONE = "Asia/Tokyo";
const FIND_URL = "https://www.meetup.com/find/?keywords=free&location=jp--Tokyo&source=EVENTS";
const EVENT_REF = /^meetup-event:\/\/event\/[1-9][0-9]*$/;
const EVENT_URL = /^https:\/\/www\.meetup\.com\/([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)\/events\/([1-9][0-9]*)\/$/;
const OFFLINE_MODE = new Set(["https://schema.org/OfflineEventAttendanceMode"]);
const FREE_TEXT = /(?:\bfree\s+(?:event|admission|entry)\b|\b(?:event|admission|entry)\s+is\s+free\b|\b(?:participation|event)\s+fee\s*(?:[:：-]|is)?\s*free\b|無料(?:の)?イベント|(?:参加費|入場料|料金)\s*(?:は|が|[:：-])?\s*無料)/i;
const FREE_NEGATION = /(?:\b(?:not|no)\s+(?:an?\s+)?free\b|無料(?:(?:では|じゃ)(?:ない|ありません|ございません)|で(?:は)?(?:ない|ありません))|有料)/i;
const MONEY_MARKER = /(?:[$€£¥]\s*\d|\b\d[\d,]*(?:\.\d+)?\s*(?:jpy|yen|円)|\b(?:fee|charge|admission|cost|price)\s*[:：]?\s*[$€£¥]?\d|(?:参加費|料金|入場料)\s*[:：]?\s*\d|\b(?:one|a)\s+drink\b|\b(?:drink|gym)\s+(?:fee|charge|purchase|required)\b|\b(?:mandatory|必須)\s+(?:purchase|drink)|\b(?:purchase|drink|購入)\s+(?:required|必須)|ワンドリンク(?:制)?|ジム代|参加費\s*(?:あり|必要)|料金\s*(?:あり|必要)|購入(?:が)?(?:必須|必要)|必須購入|cash\s+payment)/i;
const UNAVAILABLE_MARKER = /(?:waitlist|wait\s*list|sold[- ]?out|\bfull\b|fully\s+booked|\bcancel(?:led|ed|lation)?\b|受付終了|キャンセル|満席|満員|定員)/i;
const REGISTRATION_WAIT_TIMEOUT_MS = 5_000;

function invalid() { throw new Error("Meetup workflow invalid"); }

function stageError(code) {
  const error = new Error("Meetup workflow stage failed");
  error.code = code;
  return error;
}

function exactUrl(value) {
  const raw = String(value == null ? "" : value).trim();
  const match = EVENT_URL.exec(raw);
  return match ? Object.freeze({ canonical_url: raw, group: match[1], id: match[2] }) : null;
}

function canonicalBinding(value) {
  const row = typeof value === "string" ? { canonical_url: value } : value;
  if (!row || typeof row !== "object" || Array.isArray(row)) return null;
  const parsed = exactUrl(row.canonical_url || row.href || row.url);
  if (!parsed) return null;
  const eventRef = `meetup-event://event/${parsed.id}`;
  if (row.event_ref != null && String(row.event_ref) !== eventRef) return null;
  return Object.freeze({ event_ref: eventRef, canonical_url: parsed.canonical_url });
}

function exactCandidate(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)
    || value.provider !== "meetup" || !EVENT_REF.test(String(value.event_ref || ""))) invalid();
  const binding = canonicalBinding(value);
  if (!binding || binding.event_ref !== value.event_ref || binding.canonical_url !== value.canonical_url) invalid();
  if (value.starts_at != null && !Number.isFinite(Date.parse(String(value.starts_at)))) invalid();
  if (value.ends_at != null && !Number.isFinite(Date.parse(String(value.ends_at)))) invalid();
  if (value.starts_at != null && value.ends_at != null && Date.parse(value.starts_at) >= Date.parse(value.ends_at)) invalid();
  return value;
}

function localParts(value) {
  if (!(value instanceof Date) || !Number.isFinite(value.getTime())) invalid();
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone: TIME_ZONE, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(value).filter((part) => part.type !== "literal")
    .map((part) => [part.type, Number(part.value)]));
  if (![parts.year, parts.month, parts.day].every(Number.isInteger)) invalid();
  return parts;
}

function candidateWindow(observed) {
  const parts = localParts(observed);
  const end = new Date(Date.UTC(parts.year, parts.month - 1, parts.day + 14));
  return Object.freeze({
    start: Date.parse(zonedSlotInstant(parts, "00:00", TIME_ZONE)),
    end: Date.parse(zonedSlotInstant({
      year: end.getUTCFullYear(), month: end.getUTCMonth() + 1, day: end.getUTCDate(),
    }, "00:00", TIME_ZONE)),
  });
}

function calendarIntervals(calendar) {
  return Array.isArray(calendar) ? calendar
    : calendar && Array.isArray(calendar.busy_intervals) ? calendar.busy_intervals : [];
}

function overlaps(candidate, busy) {
  if (!busy || busy.kind !== "timed") return false;
  const start = Date.parse(candidate.starts_at); const end = Date.parse(candidate.ends_at);
  const busyStart = Date.parse(busy.start_at); const busyEnd = Date.parse(busy.end_at);
  return [start, end, busyStart, busyEnd].every(Number.isFinite)
    && start < busyEnd && end > busyStart;
}

function exactCoverage(candidate, busy) {
  return overlaps(candidate, busy)
    && String(busy.connector_idempotency || "") === createHash("sha256").update(candidate.canonical_url).digest("hex");
}

function defaultCalendarFree(candidate, calendar) {
  return !calendarIntervals(calendar).some((busy) => overlaps(candidate, busy) && !exactCoverage(candidate, busy));
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

function eventCanonicalUrl(event) {
  const main = event && event.mainEntityOfPage;
  return String(event && event.url || (typeof main === "string" ? main : main && (main["@id"] || main.url)) || "");
}

function controlsOf(raw) {
  const controls = raw && (raw.controls || raw.buttons || raw.visible_controls);
  if (!Array.isArray(controls)) return [];
  return controls.map((control) => (typeof control === "string"
    ? { text: control, visible: true } : {
      text: String(control && (control.text ?? control.label ?? control.innerText) || ""),
      visible: control && control.visible === true,
    }));
}

function locationIsTokyo(event) {
  const locations = Array.isArray(event.location) ? event.location : [event.location];
  return locations.some((location) => {
    const address = location && (location.address || location);
    if (!address || typeof address !== "object") return false;
    const countryValue = address.addressCountry || address.country || "";
    const country = String(typeof countryValue === "object" ? countryValue.name : countryValue).toLowerCase();
    const locality = String(address.addressLocality || address.city || "").toLowerCase();
    const region = String(address.addressRegion || address.region || "").toLowerCase();
    return ["jp", "japan", "日本"].includes(country)
      && (locality.includes("tokyo") || locality.includes("東京")
        || region.includes("tokyo") || region.includes("東京"));
  });
}

function bodyText(raw, event) {
  return [
    raw && raw.body_text,
    raw && raw.bodyText,
    raw && raw.description,
    event && event.description,
  ].filter((value) => value != null && String(value).trim()).join(" ");
}

function hasExplicitFreeText(value) {
  const text = String(value || "");
  return FREE_TEXT.test(text) && !FREE_NEGATION.test(text);
}

function hasPaidOffer(event) {
  const offers = Array.isArray(event && event.offers) ? event.offers : [event && event.offers];
  return offers.some((offer) => {
    if (!offer || typeof offer !== "object") return false;
    const price = offer.price ?? (offer.priceSpecification && offer.priceSpecification.price);
    const numeric = Number(price);
    return Number.isFinite(numeric) ? numeric > 0
      : Boolean(String(price || "").trim() && !/^(?:free|0(?:\.0+)?(?:\s*(?:jpy|yen|円))?)$/i.test(String(price).trim()));
  });
}

function scheduled(event) {
  const values = Array.isArray(event && (event.eventStatus || event.status))
    ? event.eventStatus || event.status : [event && (event.eventStatus || event.status)];
  return values.some((value) => {
    const status = String(value || "").toLowerCase();
    return status === "scheduled" || status === "eventscheduled" || status.endsWith("/eventscheduled");
  });
}

function normalizeDetail(binding, raw) {
  const event = jsonLdEvent(raw);
  if (!event || eventCanonicalUrl(event) !== binding.canonical_url) {
    throw stageError("MEETUP_DETAIL_IDENTITY_MISMATCH_FAILED");
  }
  const startsAt = Date.parse(String(event.startDate || ""));
  const endsAt = Date.parse(String(event.endDate || ""));
  if (!String(event.name || "").trim() || !Number.isFinite(startsAt) || !Number.isFinite(endsAt)) return null;
  return Object.freeze({
    provider: "meetup",
    event_ref: binding.event_ref,
    canonical_url: binding.canonical_url,
    title: String(event.name).trim(),
    starts_at: new Date(startsAt).toISOString(),
    ends_at: new Date(endsAt).toISOString(),
    registration_status: "available",
    ticket_price_status: "free",
    ticket_price_minor: 0,
    _scheduled: scheduled(event),
    _offline: (() => {
      const modes = (Array.isArray(event.eventAttendanceMode) ? event.eventAttendanceMode : [event.eventAttendanceMode])
        .filter((mode) => mode != null);
      return modes.length > 0 && modes.every((mode) => OFFLINE_MODE.has(String(mode)));
    })(),
    _tokyo: locationIsTokyo(event),
    _free_text: hasExplicitFreeText(bodyText(raw, event)),
    _paid_offer: hasPaidOffer(event),
    _blocked_text: UNAVAILABLE_MARKER.test(bodyText(raw, event)),
    _money_marker: MONEY_MARKER.test(bodyText(raw, event)),
    _attend_count: controlsOf(raw).filter((control) => control.visible && control.text === "Attend").length,
  });
}

function eligible(candidate, window) {
  const startsAt = Date.parse(candidate.starts_at); const endsAt = Date.parse(candidate.ends_at);
  return candidate._scheduled && candidate._offline && candidate._tokyo
    && Number.isFinite(startsAt) && Number.isFinite(endsAt) && startsAt < endsAt
    && startsAt >= window.start && startsAt < window.end
    && candidate._attend_count === 1 && candidate._free_text
    && !candidate._paid_offer && !candidate._money_marker && !candidate._blocked_text;
}

function publicCandidate(candidate) {
  const output = { ...candidate };
  for (const key of Object.keys(output)) if (key.startsWith("_")) delete output[key];
  return Object.freeze(output);
}

function normalizeDefaultFindHref(value) {
  const raw = typeof value === "string" ? value : value && value.canonical_url;
  let url;
  try { url = new URL(String(raw || "")); } catch { return null; }
  if (url.protocol !== "https:" || url.hostname !== "www.meetup.com"
    || url.port || url.username || url.password) return null;
  const canonicalUrl = `https://www.meetup.com${url.pathname}`;
  return exactUrl(canonicalUrl) ? Object.freeze({ canonical_url: canonicalUrl }) : null;
}

async function waitForRegistrationControl(page) {
  if (!page || typeof page.waitForFunction !== "function") {
    throw stageError("MEETUP_REGISTRATION_CONTROL_WAIT_FAILED");
  }
  try {
    await page.waitForFunction(() => {
      const terminal = /^(?:Attend|Edit RSVP|Going|Join\s+waitlist|Waitlist|Full|Sold\s+out|Cancelled|Canceled|Event\s+cancelled|Event\s+canceled|受付終了|キャンセル待ち|キャンセル|満席|満員|定員)$/i;
      return [...document.querySelectorAll("button,a")].some((node) => {
        const text = String(node.innerText || node.textContent || "").replace(/\s+/g, " ").trim();
        return Boolean((node.offsetWidth || node.offsetHeight) && terminal.test(text));
      });
    }, null, { timeout: REGISTRATION_WAIT_TIMEOUT_MS });
  } catch {
    throw stageError("MEETUP_REGISTRATION_CONTROL_WAIT_FAILED");
  }
}

async function defaultReadFindBindings(page) {
  if (!page || typeof page.goto !== "function" || typeof page.evaluate !== "function") invalid();
  await page.goto(FIND_URL, { waitUntil: "domcontentloaded", timeout: 30_000 });
  const hrefs = await page.evaluate(() => [...document.querySelectorAll("a[href]")].map((anchor) => anchor.href));
  if (!Array.isArray(hrefs)) invalid();
  return hrefs.map((href) => normalizeDefaultFindHref(href) || ({ canonical_url: String(href || "") }));
}

async function defaultReadEventDetail(input, suppliedCanonicalUrl) {
  const page = input && input.page ? input.page : input;
  const canonicalUrl = suppliedCanonicalUrl || input && input.canonicalUrl;
  if (!page || typeof page.goto !== "function" || typeof page.evaluate !== "function") invalid();
  await page.goto(canonicalUrl, { waitUntil: "domcontentloaded", timeout: 30_000 });
  await waitForRegistrationControl(page);
  return page.evaluate(() => {
    const jsonld = [...document.querySelectorAll('script[type="application/ld+json"]')].flatMap((script) => {
      try { return [JSON.parse(script.textContent || "")]; } catch { return []; }
    });
    const controls = [...document.querySelectorAll("button,a")].map((node) => ({
      text: String(node.innerText || node.textContent || "").trim(), visible: Boolean(node.offsetWidth || node.offsetHeight),
    }));
    return { jsonld, body_text: document.body ? document.body.innerText : "", controls };
  });
}

async function defaultReadRegistrationView(input) {
  const page = input && input.page ? input.page : input;
  if (!page || typeof page.evaluate !== "function") invalid();
  await waitForRegistrationControl(page);
  return page.evaluate(() => ({
    controls: [...document.querySelectorAll("button,a")].map((node) => ({
      text: String(node.innerText || node.textContent || "").trim(), visible: Boolean(node.offsetWidth || node.offsetHeight),
    })),
    auth_required: /log\s*in|sign\s*in|ログイン/i.test(document.body ? document.body.innerText : ""),
    waitlist: /wait\s*list|waitlist|満席|キャンセル/i.test(document.body ? document.body.innerText : ""),
  }));
}

function createMeetupScriptFirstWorkflow(options = {}) {
  const now = options.now || (() => new Date());
  const readFindBindings = options.readFindBindings || defaultReadFindBindings;
  const readEventDetail = options.readEventDetail || defaultReadEventDetail;
  const readRegistrationView = options.readRegistrationView || defaultReadRegistrationView;
  const isCalendarFree = options.isCalendarFree || defaultCalendarFree;
  const onDiscoveryAudit = options.onDiscoveryAudit || (() => {});
  if ([now, readFindBindings, readEventDetail, readRegistrationView, isCalendarFree, onDiscoveryAudit]
    .some((value) => typeof value !== "function")) invalid();

  return Object.freeze({
    async discoverCandidates({ page, calendar }) {
      const observed = now();
      if (!(observed instanceof Date) || !Number.isFinite(observed.getTime())) invalid();
      let rows;
      try { rows = await readFindBindings(page, observed); }
      catch { throw stageError("MEETUP_FIND_READ_FAILED"); }
      if (!Array.isArray(rows) || rows.length > 500) throw stageError("MEETUP_DISCOVERY_RESULT_CONTRACT_FAILED");
      const bindings = []; const seen = new Set();
      for (const row of rows) {
        const binding = canonicalBinding(row);
        if (!binding || seen.has(binding.event_ref)) continue;
        seen.add(binding.event_ref); bindings.push(binding);
      }
      const window = candidateWindow(observed);
      const exactCovered = []; const unprocessed = [];
      let normalizedCount = 0; let windowCount = 0; let freeOpenCount = 0;
      for (const binding of bindings) {
        let raw; try { raw = await readEventDetail(page, binding.canonical_url); }
        catch { throw stageError("MEETUP_DETAIL_READ_FAILED"); }
        let candidate;
        try { candidate = normalizeDetail(binding, raw); }
        catch (error) {
          if (error && error.code === "MEETUP_DETAIL_IDENTITY_MISMATCH_FAILED") throw error;
          continue;
        }
        if (!candidate) continue;
        normalizedCount += 1;
        const startsAt = Date.parse(candidate.starts_at);
        if (startsAt < window.start || startsAt >= window.end) continue;
        windowCount += 1;
        if (!eligible(candidate, window)) continue;
        freeOpenCount += 1;
        const visibleCandidate = publicCandidate(candidate);
        let calendarFree;
        try { calendarFree = await isCalendarFree(visibleCandidate, calendar); }
        catch { throw stageError("MEETUP_CALENDAR_CONFLICT_CHECK_FAILED"); }
        if (!calendarFree) continue;
        (calendarIntervals(calendar).some((busy) => exactCoverage(visibleCandidate, busy)) ? exactCovered : unprocessed)
          .push(visibleCandidate);
      }
      await onDiscoveryAudit(Object.freeze({
        observed_count: rows.length,
        normalized_count: normalizedCount,
        window_count: windowCount,
        free_open_count: freeOpenCount,
        calendar_free_count: exactCovered.length + unprocessed.length,
      }));
      return Object.freeze([...exactCovered, ...unprocessed]);
    },

    async runDirectAction({ page, candidate }) {
      exactCandidate(candidate);
      void page;
      return Object.freeze({ status: "failed", safe_reason: "meetup_direct_requires_harness" });
    },

    async readProviderState({ page, candidate }) {
      const selected = exactCandidate(candidate);
      let pageUrl = "";
      try { pageUrl = page && typeof page.url === "function" ? String(page.url()) : ""; } catch { return Object.freeze({ status: "unavailable" }); }
      if (pageUrl !== selected.canonical_url) return Object.freeze({ status: "unavailable" });
      let view;
      try { view = await readRegistrationView(page, selected); }
      catch { return Object.freeze({ status: "unavailable" }); }
      if (!view || typeof view !== "object" || Array.isArray(view)) return Object.freeze({ status: "unavailable" });
      try { if (String(page && typeof page.url === "function" ? page.url() : "") !== selected.canonical_url) return Object.freeze({ status: "unavailable" }); }
      catch { return Object.freeze({ status: "unavailable" }); }
      const controls = controlsOf(view);
      const registeredCount = controls.filter((control) => control.visible
        && ["Edit RSVP", "Going"].includes(control.text)).length;
      if (registeredCount === 1 && !view.auth_required && !view.waitlist) {
        return Object.freeze({ status: "registered" });
      }
      const attendCount = controls.filter((control) => control.visible && control.text === "Attend").length;
      if (registeredCount === 0 && attendCount === 1 && !view.auth_required && !view.waitlist) {
        return Object.freeze({ status: "absent" });
      }
      return Object.freeze({ status: "unavailable" });
    },
  });
}

module.exports = { createMeetupScriptFirstWorkflow };
