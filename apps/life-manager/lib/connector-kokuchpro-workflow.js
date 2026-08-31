"use strict";

const { createHash } = require("node:crypto");
const { zonedSlotInstant } = require("./honne-ja-shadow-schedule.js");

const TIME_ZONE = "Asia/Tokyo";
const LISTING_BASE = "https://www.kokuchpro.com/s/area-%E6%9D%B1%E4%BA%AC%E9%83%BD/charge-0/";
const EVENT_URL = /^https:\/\/www\.kokuchpro\.com\/event\/([0-9a-f]{32})(?:\/([1-9][0-9]{0,19}))?\/$/;
const REGISTERED_ENTRY_URL = /^https:\/\/www\.kokuchpro\.com\/entry\/[0-9a-f]{32}\/$/;
const EVENT_RAW_PER_CARD = 100;
const EVENT_RAW_TOTAL = 4_000;
const ISO_TIME = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,3}))?)?(Z|[+-]\d{2}:?\d{2})$/;
const JSONLD_NODE_LIMIT = 256;
const LOGIN_URL = "https://www.kokuchpro.com/auth/login/";
const READBACK_FORM_LIMIT = 32;
const READBACK_PASSWORD_LIMIT = 16;
const CONTROL = /[\u0000-\u001F\u007F-\u009F]/;
const OFFLINE_MODE = new Set(["https://schema.org/OfflineEventAttendanceMode", "http://schema.org/OfflineEventAttendanceMode"]);
const IN_STOCK = new Set(["InStock", "https://schema.org/InStock", "http://schema.org/InStock"]);
const NON_TOKYO_ADDRESS = /(?:北海道|(?:青森|岩手|宮城|秋田|山形|福島|茨城|栃木|群馬|埼玉|千葉|神奈川|新潟|富山|石川|福井|山梨|長野|岐阜|静岡|愛知|三重|滋賀|兵庫|奈良|和歌山|鳥取|島根|岡山|広島|山口|徳島|香川|愛媛|高知|福岡|佐賀|長崎|熊本|大分|宮崎|鹿児島|沖縄)県|(?:大阪|京都)府|(?:大阪|京都|神戸|名古屋|千葉|さいたま|横浜|川崎|札幌|仙台|福岡|広島|那覇)市)/;
const SAFE_CODES = new Set("KOKUCHPRO_LISTING_NAVIGATION_FAILED KOKUCHPRO_LISTING_READ_FAILED KOKUCHPRO_LISTING_RESULT_CONTRACT_FAILED KOKUCHPRO_DETAIL_NAVIGATION_FAILED KOKUCHPRO_DETAIL_READ_FAILED KOKUCHPRO_DETAIL_RESULT_CONTRACT_FAILED KOKUCHPRO_DETAIL_IDENTITY_MISMATCH_FAILED KOKUCHPRO_CALENDAR_CONFLICT_CHECK_FAILED KOKUCHPRO_AUDIT_FAILED".split(" "));

function invalid() { throw new Error("KokuchPro workflow invalid"); }
function stageError(code) { const error = new Error("KokuchPro workflow stage failed"); error.code = code; return error; }
function preserveSafe(error, fallback) { const code = String(error && error.code || ""); return stageError(SAFE_CODES.has(code) ? code : fallback); }

function exactUrl(value) {
  if (typeof value !== "string") return null;
  const match = EVENT_URL.exec(value);
  return match ? Object.freeze({ canonical_url: value, event_key: match[1], occurrence_id: match[2] || null }) : null;
}

function canonicalKokuchProBinding(value) {
  const row = typeof value === "string" ? { canonical_url: value } : value;
  if (!row || typeof row !== "object" || Array.isArray(row)) return null;
  const urlValues = ["canonical_url", "href", "url"].filter((key) => Object.hasOwn(row, key)).map((key) => row[key]);
  if (!urlValues.length || urlValues.some((raw) => typeof raw !== "string" || raw !== urlValues[0])) return null;
  const parsed = exactUrl(urlValues[0]);
  if (!parsed) return null;
  const eventRef = `kokuchpro-event://event/${parsed.event_key}${parsed.occurrence_id ? `/${parsed.occurrence_id}` : ""}`;
  if (Object.hasOwn(row, "event_ref") && row.event_ref !== eventRef) return null;
  if (Object.hasOwn(row, "event_key") && row.event_key !== parsed.event_key) return null;
  if (Object.hasOwn(row, "occurrence_id") && row.occurrence_id !== parsed.occurrence_id) return null;
  return Object.freeze({ event_ref: eventRef, canonical_url: parsed.canonical_url });
}

function localParts(value) {
  if (!(value instanceof Date) || !Number.isFinite(value.getTime())) invalid();
  return Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone: TIME_ZONE, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(value).filter((part) => part.type !== "literal").map((part) => [part.type, Number(part.value)]));
}

function candidateWindow(now) {
  const parts = localParts(now);
  const end = new Date(Date.UTC(parts.year, parts.month - 1, parts.day + 14));
  return { start: Date.parse(zonedSlotInstant(parts, "00:00", TIME_ZONE)), end: Date.parse(zonedSlotInstant({
    year: end.getUTCFullYear(), month: end.getUTCMonth() + 1, day: end.getUTCDate(),
  }, "00:00", TIME_ZONE)) };
}

function listingUrl(observed) {
  const parts = localParts(observed);
  const end = new Date(Date.UTC(parts.year, parts.month - 1, parts.day + 14));
  const text = (value) => [value.year, value.month, value.day].map((part) => String(part).padStart(2, "0")).join("-");
  return `${LISTING_BASE}?et=0&start_date=${text(parts)}&end_date=${text({ year: end.getUTCFullYear(), month: end.getUTCMonth() + 1, day: end.getUTCDate() })}&enabled=1&sort=date`;
}

function assertPageUrl(page, expected, code) { if (page && typeof page.url === "function" && String(page.url()) !== expected) throw stageError(code); }
function calendarIntervals(calendar) { return Array.isArray(calendar) ? calendar : calendar && Array.isArray(calendar.busy_intervals) ? calendar.busy_intervals : []; }
function overlaps(candidate, busy) {
  if (!busy || busy.kind !== "timed") return false;
  const start = Date.parse(candidate.starts_at); const end = Date.parse(candidate.ends_at);
  const busyStart = Date.parse(busy.start_at); const busyEnd = Date.parse(busy.end_at);
  return [start, end, busyStart, busyEnd].every(Number.isFinite) && start < busyEnd && end > busyStart;
}

function exactCoverage(candidate, busy) { return overlaps(candidate, busy) && String(busy.connector_idempotency || "") === createHash("sha256").update(candidate.canonical_url, "utf8").digest("hex"); }
function defaultCalendarFree(candidate, calendar) { return !calendarIntervals(calendar).some((busy) => overlaps(candidate, busy) && !exactCoverage(candidate, busy)); }

function publicText(value, max) {
  return typeof value === "string" && value.length > 0 && value.length <= max
    && value === value.trim() && !CONTROL.test(value) ? value : null;
}

function parseIso(value) {
  const match = typeof value === "string" ? ISO_TIME.exec(value) : null;
  if (!match) return NaN;
  const [year, month, day, hour, minute] = match.slice(1, 6).map(Number);
  const second = Number(match[6] || 0);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (month < 1 || month > 12 || day < 1 || day > days[month - 1] || hour > 23 || minute > 59 || second > 59) return NaN;
  const base = new Date(0); base.setUTCFullYear(year, month - 1, day); base.setUTCHours(hour, minute, second, Number((match[7] || "").padEnd(3, "0")) || 0);
  if (!Number.isFinite(base.getTime())) return NaN;
  const zone = match[8].length === 5 ? `${match[8].slice(0, 3)}:${match[8].slice(3)}` : match[8];
  if (zone === "Z") return base.getTime();
  const zoneHour = Number(zone.slice(1, 3)); const zoneMinute = Number(zone.slice(4, 6));
  if (zoneHour > 23 || zoneMinute > 59) return NaN;
  const offset = (zone[0] === "+" ? 1 : -1) * (zoneHour * 60 + zoneMinute);
  return base.getTime() - offset * 60_000;
}

function detailTiming(input = {}) {
  if (!input || typeof input !== "object" || Array.isArray(input)) invalid();
  const { binding, detail, now } = input;
  const selected = canonicalKokuchProBinding(binding);
  if (!selected) invalid();
  const parsed = exactUrl(selected.canonical_url);
  const detailUrls = ["canonical_url", "href", "url"].filter((key) => Object.hasOwn(detail || {}, key));
  if (!detail || typeof detail !== "object" || Array.isArray(detail)
    || detailUrls.some((key) => detail[key] !== selected.canonical_url)
    || !Object.hasOwn(detail, "canonical_url")
    || (Object.hasOwn(detail, "event_ref") && detail.event_ref !== selected.event_ref)
    || detail.event_key !== parsed.event_key
    || detail.occurrence_id !== parsed.occurrence_id) invalid();
  const starts = parseIso(detail.starts_at);
  const ends = parseIso(detail.ends_at);
  if (!Number.isFinite(starts) || !Number.isFinite(ends) || ends <= starts) return null;
  const window = candidateWindow(now);
  return Object.freeze({ selected, parsed, starts, ends, withinWindow: starts >= window.start && starts < window.end });
}

function normalizeKokuchProDetail(input = {}) {
  const timing = detailTiming(input);
  if (!timing) return null;
  const { detail } = input;
  const { selected, starts, ends, withinWindow } = timing;
  const title = publicText(detail.title, 500);
  const venue = publicText(detail.venue, 1000);
  const address = publicText(detail.address, 1000);
  if (!title || !venue || !address) return null;
  if (detail.event_format !== "offline" || detail.fee_scheme !== "free"
    || detail.registration_status !== "open" || detail.is_full !== false
    || !address.startsWith("東京都")) return null;
  const tickets = detail.tickets;
  const ticket = Array.isArray(tickets) && tickets.length === 1 ? tickets[0] : null;
  const ticketId = ticket && typeof ticket.id === "string" && /^[A-Za-z0-9._:-]{1,128}$/.test(ticket.id)
    ? ticket.id : null;
  if (!ticket || typeof ticket !== "object" || Array.isArray(ticket)
    || !ticketId
    || ticket.status !== "available" || ticket.price_currency !== "JPY" || ticket.price_minor !== 0) return null;
  if (!withinWindow) return null;
  return Object.freeze({ provider: "kokuchpro", event_ref: selected.event_ref, canonical_url: selected.canonical_url,
    title, starts_at: new Date(starts).toISOString(), ends_at: new Date(ends).toISOString(), venue, address,
    registration_status: "available", ticket_id: ticketId, ticket_price_status: "free", ticket_price_minor: 0 });
}

function eventNodes(raw) {
  const source = raw && Object.hasOwn(raw, "jsonld") ? raw.jsonld : raw && raw.jsonLd;
  const queue = Array.isArray(source) ? [...source] : [source];
  if (queue.length > JSONLD_NODE_LIMIT) return null;
  const events = [];
  for (let index = 0; index < queue.length; index += 1) {
    const node = queue[index];
    if (Array.isArray(node)) {
      if (queue.length + node.length > JSONLD_NODE_LIMIT) return null;
      queue.push(...node);
      continue;
    }
    if (!node || typeof node !== "object") continue;
    const types = Array.isArray(node["@type"]) ? node["@type"] : [node["@type"]];
    if (types.some((type) => ["Event", "https://schema.org/Event", "http://schema.org/Event"].includes(type))) events.push(node);
    if (!Object.hasOwn(node, "@graph")) continue;
    const graph = node["@graph"];
    if (Array.isArray(graph)) {
      if (queue.length + graph.length > JSONLD_NODE_LIMIT) return null;
      queue.push(...graph);
    } else if (graph && typeof graph === "object") {
      if (queue.length >= JSONLD_NODE_LIMIT) return null;
      queue.push(graph);
    } else if (graph != null) return null;
  }
  return events;
}
function locationFields(location) { const place = Array.isArray(location) ? (location.length === 1 ? location[0] : null) : location; if (!place || typeof place !== "object" || Array.isArray(place)) return { venue: "", address: "" }; const source = typeof place.address === "string" ? { name: place.address } : place.address; if (!source || typeof source !== "object" || Array.isArray(source)) return { venue: String(place.name || ""), address: "" }; const country = source.addressCountry && typeof source.addressCountry === "object" ? source.addressCountry.name : source.addressCountry; const region = String(source.addressRegion || "").trim(); const locality = String(source.addressLocality || "").trim(); const fields = [source.name, region, locality, source.streetAddress, source.postalCode].filter((value) => typeof value === "string" && value.trim()).map((value) => value.trim()); const address = fields.join(" ").trim(); if (country && !/^(?:JP|JPN|日本)$/i.test(String(country).trim())) return { venue: String(place.name || ""), address: "" }; if ((region && region !== "東京都") || NON_TOKYO_ADDRESS.test(address) || !address.startsWith("東京都")) return { venue: String(place.name || ""), address: "" }; return { venue: String(place.name || source.name || "").trim(), address }; }
function structuredDetail(raw, canonicalUrl) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw stageError("KOKUCHPRO_DETAIL_RESULT_CONTRACT_FAILED");
  if (Object.hasOwn(raw, "canonical_url") && String(raw.canonical_url || "") !== canonicalUrl) throw stageError("KOKUCHPRO_DETAIL_IDENTITY_MISMATCH_FAILED");
  const events = eventNodes(raw); if (!events || events.length !== 1) return null; const event = events[0];
  if (String(event.url || "").trim() !== canonicalUrl) throw stageError("KOKUCHPRO_DETAIL_IDENTITY_MISMATCH_FAILED");
  const parsed = exactUrl(canonicalUrl); const modes = Array.isArray(event.eventAttendanceMode) ? event.eventAttendanceMode : [event.eventAttendanceMode];
  const offline = modes.length === 1 && OFFLINE_MODE.has(String(modes[0] || "")); const offers = Array.isArray(event.offers) ? event.offers : [event.offers];
  const freeOffer = offers.length === 1 && offers.every((offer) => { const types = Array.isArray(offer && offer["@type"]) ? offer["@type"] : [offer && offer["@type"]]; return offer && typeof offer === "object" && types.length === 1 && ["Offer", "https://schema.org/Offer", "http://schema.org/Offer"].includes(types[0]) && String(offer.url || "").trim() === canonicalUrl && offer.priceCurrency === "JPY" && ((typeof offer.price === "number" && Number.isFinite(offer.price) && offer.price === 0) || (typeof offer.price === "string" && offer.price.trim() !== "" && Number(offer.price) === 0)) && IN_STOCK.has(String(offer.availability || "")); });
  const feeRows = Array.isArray(raw.fee_rows) ? raw.fee_rows : []; const freeFee = feeRows.filter((row) => row && String(row.label || "").trim() === "料金制度" && String(row.value || "").trim() === "無料イベント").length === 1;
  const freeTickets = (Array.isArray(raw.ticket_rows) ? raw.ticket_rows : []).filter((row) => row && String(row.label || "").trim() === "無料" && String(row.status || "").trim() === "募集中"); const hasFormFacts = Object.hasOwn(raw, "availability_values") || Object.hasOwn(raw, "entry_actions"); const values = Array.isArray(raw.availability_values) ? raw.availability_values.map(String) : []; const actions = Array.isArray(raw.entry_actions) ? raw.entry_actions.map(String) : []; const paired = hasFormFacts && Array.isArray(raw.availability_values) && Array.isArray(raw.entry_actions) && (values.length === 1 || values.length === 2) && values.length === actions.length && new Set(values).size === 1 && /^[1-9][0-9]{0,19}$/.test(values[0]) && actions.every((action) => action === `${canonicalUrl}entry/`); const availability = hasFormFacts ? (paired ? values[0] : "") : null; const ticket = freeTickets.length === 1 && (!hasFormFacts || paired) ? freeTickets[0] : null;
  const { venue, address } = locationFields(event.location);
  return { canonical_url: canonicalUrl, event_key: parsed.event_key, occurrence_id: parsed.occurrence_id, title: String(event.name || ""), starts_at: event.startDate, ends_at: event.endDate, venue, address, event_format: offline ? "offline" : "online", fee_scheme: freeOffer && freeFee ? "free" : "paid", registration_status: ticket ? "open" : "closed", is_full: false, tickets: ticket ? [{ id: availability === null ? String(ticket.id || "") : availability, status: "available", price_currency: "JPY", price_minor: 0 }] : [] };
}

async function defaultReadListingBindings(page, observed) {
  if (!page || typeof page.goto !== "function" || typeof page.evaluate !== "function") invalid(); const url = listingUrl(observed);
  try { await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30_000 }); assertPageUrl(page, url, "KOKUCHPRO_LISTING_NAVIGATION_FAILED"); } catch (error) { if (error && error.code === "KOKUCHPRO_LISTING_NAVIGATION_FAILED") throw error; throw stageError("KOKUCHPRO_LISTING_NAVIGATION_FAILED"); }
  let cards; try { cards = await page.evaluate(() => [...document.querySelectorAll(".event_list .event_item")].map((item) => { if (!item || typeof item.querySelectorAll !== "function") return null; const anchors = item.querySelectorAll('a[href^="https://www.kokuchpro.com/event/"]'); return anchors && typeof anchors[Symbol.iterator] === "function" ? [...anchors].map((anchor) => String(anchor && (anchor.href || anchor.getAttribute("href")) || "")) : null; })); } catch { throw stageError("KOKUCHPRO_LISTING_READ_FAILED"); }
  if (!Array.isArray(cards) || cards.length < 1 || cards.length > 40) throw stageError("KOKUCHPRO_LISTING_RESULT_CONTRACT_FAILED"); const result = []; const seen = new Set(); let rawCount = 0;
  for (const card of cards) {
    if (!Array.isArray(card) || card.length < 1 || card.length > EVENT_RAW_PER_CARD) throw stageError("KOKUCHPRO_LISTING_RESULT_CONTRACT_FAILED"); rawCount += card.length;
    if (rawCount > EVENT_RAW_TOTAL) throw stageError("KOKUCHPRO_LISTING_RESULT_CONTRACT_FAILED"); const cardSeen = new Set();
    for (const raw of card) { if (typeof raw !== "string") throw stageError("KOKUCHPRO_LISTING_RESULT_CONTRACT_FAILED"); const binding = canonicalKokuchProBinding(raw); if (!binding || cardSeen.has(binding.event_ref)) continue; cardSeen.add(binding.event_ref); if (cardSeen.size > 20) throw stageError("KOKUCHPRO_LISTING_RESULT_CONTRACT_FAILED"); if (seen.has(binding.event_ref)) continue; seen.add(binding.event_ref); result.push(binding); }
  }
  if (result.length > 800) throw stageError("KOKUCHPRO_LISTING_RESULT_CONTRACT_FAILED");
  return Object.freeze(result);
}

async function defaultReadEventDetail(page, canonicalUrl) {
  if (!page || typeof page.goto !== "function" || typeof page.evaluate !== "function") invalid();
  try { await page.goto(canonicalUrl, { waitUntil: "domcontentloaded", timeout: 30_000 }); assertPageUrl(page, canonicalUrl, "KOKUCHPRO_DETAIL_NAVIGATION_FAILED"); } catch (error) { if (error && error.code === "KOKUCHPRO_DETAIL_NAVIGATION_FAILED") throw error; throw stageError("KOKUCHPRO_DETAIL_NAVIGATION_FAILED"); }
  let raw; try { raw = await page.evaluate((expectedUrl) => { const text = (node) => String(node && (node.innerText || node.textContent) || "").replace(/\s+/g, " ").trim(); const jsonld = [...document.querySelectorAll('script[type="application/ld+json"]')].flatMap((script) => { try { return [JSON.parse(script.textContent || "")]; } catch { return []; } }); const selector = 'input#FormEntryAvailability[name="data[Form][entry_availability]"]'; const availability_values = [...document.querySelectorAll(selector)].map((input) => String(input.value || "")); const entry_actions = [...document.querySelectorAll("form")].filter((form) => form.querySelector(selector)).map((form) => String(form.action || form.getAttribute("action") || "")); const tableRows = [...document.querySelectorAll("tr")].map((row) => { const cells = [...row.querySelectorAll("th,td")].map(text); const node = row.querySelector("[data-ticket-id],a[href*='ticket'],input[name='ticket_id']"); const id = node && (node.getAttribute("data-ticket-id") || node.value || node.textContent); return { cells, id: id ? String(id).trim() : "" }; }); return { canonical_url: String((typeof location !== "undefined" && location.href) || expectedUrl), jsonld, fee_rows: tableRows.map((row) => ({ label: row.cells[0] || "", value: row.cells.slice(1).join(" ") })), ticket_rows: tableRows.filter((row) => row.cells.includes("無料") && row.cells.includes("募集中")).map((row) => ({ id: row.id, label: "無料", status: "募集中" })), availability_values, entry_actions }; }, canonicalUrl); assertPageUrl(page, canonicalUrl, "KOKUCHPRO_DETAIL_NAVIGATION_FAILED"); } catch (error) { if (error && error.code === "KOKUCHPRO_DETAIL_NAVIGATION_FAILED") throw error; throw stageError("KOKUCHPRO_DETAIL_READ_FAILED"); }
  try { return structuredDetail(raw, canonicalUrl); } catch (error) { if (error && error.code) throw error; throw stageError("KOKUCHPRO_DETAIL_RESULT_CONTRACT_FAILED"); }
}

function exactLoginUrl(value, entryPath) {
  if (typeof value !== "string") return false;
  const authority = /^https:\/\/([^/]+)(?:\/|$)/.exec(value);
  if (!authority || authority[1] !== "www.kokuchpro.com") return false;
  let parsed; try { parsed = new URL(value); } catch { return false; }
  if (parsed.pathname !== "/auth/login/" || parsed.hash) return false;
  const parts = parsed.search.slice(1).split("&"); if (parts.length !== 1) return false;
  const separator = parts[0].indexOf("="); if (separator <= 0 || parts[0].slice(0, separator) !== "continue") return false;
  try { return decodeURIComponent(parts[0].slice(separator + 1).replace(/\+/g, " ")) === entryPath; } catch { return false; }
}

async function readProviderStateFacts(page, mode, entryUrl, canonicalUrl) {
  return page.evaluate(({ mode: expectedMode, entryUrl: expectedEntry, canonicalUrl: expectedCanonical, loginUrl, formLimit, passwordLimit }) => {
    const forms = [...document.querySelectorAll("form")];
    if (forms.length > formLimit) return null;
    const facts = forms.map((form) => ({
      action: String(form && (form.action || form.getAttribute("action")) || ""),
      method: String(form && (form.method || form.getAttribute("method")) || "").toUpperCase(),
    }));
    if (expectedMode === "entry") return { entry_forms: facts.filter((form) => form.action === expectedEntry) };
    const passwords = [...document.querySelectorAll('input[type="password"]')];
    if (passwords.length > passwordLimit) return null;
    const visible = (node) => {
      if (!node || node.hidden === true || node.isConnected === false || String(node.getAttribute("aria-hidden") || "").toLowerCase() === "true") return false;
      let current = node;
      while (current) {
        if (current.hidden === true || String(current.getAttribute("aria-hidden") || "").toLowerCase() === "true") return false;
        const view = current.ownerDocument && current.ownerDocument.defaultView;
        const style = view && typeof view.getComputedStyle === "function" ? view.getComputedStyle(current) : current.style;
        if (style && [style.display, style.visibility, style.contentVisibility].some((value) => ["none", "hidden", "collapse"].includes(String(value || "").toLowerCase()))) return false;
        current = current.parentElement;
      }
      if (typeof node.getBoundingClientRect !== "function") return false;
      const rect = node.getBoundingClientRect();
      return Number(rect.width) > 0 && Number(rect.height) > 0;
    };
    const text = (node) => String(node && (node.innerText || node.textContent) || "").replace(/\s+/g, " ").trim();
    const href = (node) => {
      try {
        const raw = node.getAttribute("href") || node.getAttribute("data-href") || "";
        return new URL(raw, typeof location === "undefined" ? expectedCanonical : location.href).href;
      } catch { return ""; }
    };
    const links = [...document.querySelectorAll("a[href], [role='link'][href], [data-href]")].map((node) => ({
      href: href(node), text: text(node), visible: visible(node),
    }));
    const headings = [...document.querySelectorAll("h1,h2,h3,h4,h5,h6,[role='heading']")].map((node) => ({
      text: text(node), visible: visible(node),
    }));
    const common = {
      password_count: passwords.length,
      login_forms: facts.filter((form) => form.action === loginUrl),
      entry_forms: facts.filter((form) => form.action === expectedEntry),
    };
    if (expectedMode === "canonical") {
      return {
        ...common,
        registration_links: links.filter((link) => link.text === "申込情報を確認する"),
      };
    }
    return {
      ...common,
      detail_headings: headings.filter((heading) => heading.text === "申込詳細"),
      canonical_links: links.filter((link) => link.href === expectedCanonical),
    };
  }, { mode, entryUrl, canonicalUrl, loginUrl: LOGIN_URL, formLimit: READBACK_FORM_LIMIT, passwordLimit: READBACK_PASSWORD_LIMIT });
}

function sameEventDescendantUrl(value, canonicalUrl) {
  let current;
  let canonical;
  try {
    current = new URL(value);
    canonical = new URL(canonicalUrl);
  } catch { return false; }
  if (
    current.protocol !== "https:" || current.hostname !== "www.kokuchpro.com"
    || current.port || current.username || current.password || current.search || current.hash
  ) return false;
  return current.pathname.startsWith(canonical.pathname) && current.pathname !== canonical.pathname;
}

async function defaultReadProviderState(page, selected) {
  if (!page || typeof page.url !== "function" || typeof page.evaluate !== "function") return null;
  const entryUrl = `${selected.canonical_url}entry/`; const entryPath = new URL(entryUrl).pathname;
  const current = String(page.url());
  const mode = current === selected.canonical_url ? "canonical"
    : sameEventDescendantUrl(current, selected.canonical_url) ? "detail"
      : exactLoginUrl(current, entryPath) ? "login" : null;
  if (!mode) return null;
  const facts = await readProviderStateFacts(page, mode, entryUrl, selected.canonical_url);
  if (String(page.url()) !== current || !facts || typeof facts !== "object" || Array.isArray(facts)) return null;
  if (mode === "entry") {
    const forms = facts.entry_forms;
    return Array.isArray(forms) && (forms.length === 1 || forms.length === 2)
      && forms.every((form) => form && typeof form === "object" && !Array.isArray(form) && form.action === entryUrl && form.method === "POST") ? "absent" : null;
  }
  if (mode === "canonical") {
    const links = facts.registration_links;
    const forms = facts.entry_forms;
    const loginForms = facts.login_forms;
    const registered = Array.isArray(links) && (links.length === 1 || links.length === 2)
      && links.every((link) => link && REGISTERED_ENTRY_URL.test(String(link.href || ""))
        && link.text === "申込情報を確認する" && link.visible === true)
      && new Set(links.map((link) => link.href)).size === 1
      && Array.isArray(forms) && !forms.some((form) => form && form.method === "POST")
      && facts.password_count === 0 && Array.isArray(loginForms) && loginForms.length === 0;
    if (registered) return "registered";
    const hasRegistrationSignal = Array.isArray(links) && links.length > 0;
    return !hasRegistrationSignal && Array.isArray(forms)
      && (forms.length === 1 || forms.length === 2)
      && forms.every((form) => form && form.action === entryUrl && form.method === "POST") ? "absent" : null;
  }
  if (mode === "detail") {
    const headings = facts.detail_headings;
    const links = facts.canonical_links;
    const forms = facts.entry_forms;
    return Array.isArray(headings) && headings.filter((heading) => heading && heading.text === "申込詳細" && heading.visible === true).length === 1
      && Array.isArray(links) && links.filter((link) => link && link.href === selected.canonical_url && link.visible === true).length === 1
      && Array.isArray(forms) && !forms.some((form) => form && form.method === "POST")
      && facts.password_count === 0 && Array.isArray(facts.login_forms) && facts.login_forms.length === 0 ? "registered" : null;
  }
  const forms = facts.login_forms;
  return facts.password_count === 1 && Array.isArray(forms) && forms.length === 1
    && forms[0] && typeof forms[0] === "object" && !Array.isArray(forms[0])
    && forms[0].action === LOGIN_URL && forms[0].method === "POST" ? "auth_required" : null;
}

function exactCandidate(value) { if (!value || typeof value !== "object" || Array.isArray(value) || value.provider !== "kokuchpro" || !canonicalKokuchProBinding(value) || !String(value.title || "").trim() || !Number.isFinite(Date.parse(String(value.starts_at || ""))) || !Number.isFinite(Date.parse(String(value.ends_at || ""))) || Date.parse(value.starts_at) >= Date.parse(value.ends_at) || value.registration_status !== "available" || value.ticket_price_status !== "free" || value.ticket_price_minor !== 0 || typeof value.ticket_id !== "string" || !/^[A-Za-z0-9._:-]{1,128}$/.test(value.ticket_id)) invalid(); return value; }
function createKokuchProDiscoveryWorkflow(options = {}) {
  const now = options.now || (() => new Date()); const readListingBindings = options.readListingBindings || options.readListing || defaultReadListingBindings; const readEventDetail = options.readEventDetail || defaultReadEventDetail; const isCalendarFree = options.isCalendarFree || defaultCalendarFree; const onDiscoveryAudit = options.onDiscoveryAudit || (() => {});
  if ([now, readListingBindings, readEventDetail, isCalendarFree, onDiscoveryAudit].some((value) => typeof value !== "function")) invalid();
  return Object.freeze({
    async discoverCandidates({ page, calendar }) {
      const observed = now(); if (!(observed instanceof Date) || !Number.isFinite(observed.getTime())) invalid(); let rows;
      try { rows = await readListingBindings(page, observed); } catch (error) { throw preserveSafe(error, "KOKUCHPRO_LISTING_READ_FAILED"); } if (!Array.isArray(rows) || rows.length > 800) throw stageError("KOKUCHPRO_LISTING_RESULT_CONTRACT_FAILED");
      const bindings = []; const seen = new Set(); for (const row of rows) { const binding = canonicalKokuchProBinding(row); if (!binding || seen.has(binding.event_ref)) continue; seen.add(binding.event_ref); bindings.push(binding); }
      const exactCovered = []; const unprocessed = []; let withinWindowCount = 0; let eligibleCount = 0;
      for (const binding of bindings) {
        let raw; try { raw = await readEventDetail(page, binding.canonical_url); } catch (error) { throw preserveSafe(error, "KOKUCHPRO_DETAIL_READ_FAILED"); } try { assertPageUrl(page, binding.canonical_url, "KOKUCHPRO_DETAIL_NAVIGATION_FAILED"); } catch (error) { if (error && error.code === "KOKUCHPRO_DETAIL_NAVIGATION_FAILED") throw error; throw stageError("KOKUCHPRO_DETAIL_NAVIGATION_FAILED"); } if (raw == null) continue;
        let timing; try { timing = detailTiming({ binding, detail: raw, now: observed }); } catch (error) { throw preserveSafe(error, "KOKUCHPRO_DETAIL_RESULT_CONTRACT_FAILED"); } if (!timing || !timing.withinWindow) continue;
        withinWindowCount += 1;
        let candidate; try { candidate = normalizeKokuchProDetail({ binding, detail: raw, now: observed }); } catch (error) { throw preserveSafe(error, "KOKUCHPRO_DETAIL_RESULT_CONTRACT_FAILED"); } if (!candidate) continue;
        eligibleCount += 1; let free; try { free = await isCalendarFree(candidate, calendar); } catch { throw stageError("KOKUCHPRO_CALENDAR_CONFLICT_CHECK_FAILED"); } if (!free) continue;
        (calendarIntervals(calendar).some((busy) => exactCoverage(candidate, busy)) ? exactCovered : unprocessed).push(candidate);
      }
      const selectedCount = exactCovered.length + unprocessed.length; try { await onDiscoveryAudit(Object.freeze({ discovered_count: bindings.length, within_window_count: withinWindowCount, eligible_count: eligibleCount, calendar_free_count: selectedCount, selected_count: selectedCount })); } catch (error) { throw preserveSafe(error, "KOKUCHPRO_AUDIT_FAILED"); }
      return Object.freeze([...exactCovered, ...unprocessed]);
    },
    async runDirectAction({ candidate }) { exactCandidate(candidate); return Object.freeze({ status: "failed", safe_reason: "kokuchpro_direct_requires_harness" }); },
    async readProviderState({ page, candidate } = {}) {
      try { const selected = exactCandidate(candidate); const status = await defaultReadProviderState(page, selected); return Object.freeze({ status: status || "unavailable" }); }
      catch { return Object.freeze({ status: "unavailable" }); }
    },
  });
}

module.exports = { canonicalKokuchProBinding, normalizeKokuchProDetail, createKokuchProDiscoveryWorkflow };
