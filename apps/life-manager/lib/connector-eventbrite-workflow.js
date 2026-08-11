"use strict";
const { createHash } = require("node:crypto");
const { zonedSlotInstant } = require("./honne-ja-shadow-schedule.js");
const TIME_ZONE = "Asia/Tokyo";
const LIST_URL = "https://www.eventbrite.com/d/japan--tokyo/free--events/";
const EVENT_REF = /^eventbrite-event:\/\/event\/[1-9][0-9]*$/;
const EVENT_PATH = /^\/e\/(?:([a-z0-9](?:[a-z0-9-]*[a-z0-9])?)-tickets-([1-9][0-9]*)|([1-9][0-9]*))$/i;
const OFFLINE_MODE = new Set(["https://schema.org/OfflineEventAttendanceMode", "http://schema.org/OfflineEventAttendanceMode"]);
const IN_STOCK = new Set(["InStock", "https://schema.org/InStock", "http://schema.org/InStock"]);
const BLOCKED_MARKER = /(?:sold[ -]?out|wait[ -]?list|waitlist|cancel(?:led|ed|lation)?|registration closed|event closed|error|failed|受付終了|キャンセル|満席|満員|売り切れ|販売終了|エラー)/i;
const MONEY_MARKER = /(?:[$€£¥￥]\s*\d|\b\d[\d,]*(?:\.\d+)?\s*(?:(?:jpy|yen)\b|円)|door\s*(?:price|fee)|at\s+the\s+door|participation\s+fee|admission\s+fee|entry\s+fee|payment\s+required|paid\s+at\s+door|参加費|入場料|会場払い|当日払い|有料|支払い(?:が)?(?:必要|必須))/i;
const EXPLICIT_FREE_MARKER = /(?:参加費(?:\s*は)?\s*(?:[:：]\s*)?無料|入場\s*無料)(?![ぁ-んァ-ヶ一-龯々ー])|\bfree\s+admission\b(?!\s+[A-Za-z0-9])|\bno\s+participation\s+fee\b(?!\s+[A-Za-z0-9])/gi;
const NEGATIVE_PURCHASE_MARKER = /\b(?:no\s+minimum\s+purchase|no\s+purchase\s+required)\b(?!\s+[A-Za-z0-9])/gi;
const MINIMUM_PURCHASE_MARKER = /(?:\bone\s+drink\s+minimum\b|\bminimum\s+purchase\b|\bpurchase\s+required\b|ワンドリンク必須)/i;
const READBACK_UNSAFE = /(?:payment|pay(?:ment)?|credit\s*card|checkout|error|failed|sold[ -]?out|wait[ -]?list|waitlist|cancel(?:led|ed)?|受付終了|キャンセル|満席|エラー|支払い)/i;
const COMPLETION_MARKER = /(?:registration\s+(?:is\s+)?(?:complete|completed|confirmed)|order\s+confirmed|ticket(?:s)?\s+confirmed|you(?:'re| are)\s+going|登録完了|申し込みが完了しました)/gi;
const SAFE_CODES = new Set("EVENTBRITE_LISTING_NAVIGATION_FAILED EVENTBRITE_LISTING_READ_FAILED EVENTBRITE_LISTING_RESULT_CONTRACT_FAILED EVENTBRITE_DETAIL_NAVIGATION_FAILED EVENTBRITE_DETAIL_READ_FAILED EVENTBRITE_DETAIL_IDENTITY_MISMATCH_FAILED EVENTBRITE_CALENDAR_CONFLICT_CHECK_FAILED EVENTBRITE_REGISTRATION_READ_FAILED".split(" "));
function invalid() { throw new Error("Eventbrite workflow invalid"); }
function stageError(code) {
  const error = new Error("Eventbrite workflow stage failed");
  error.code = code;
  return error;
}
function preserveSafe(error, fallback) { const code = String(error && error.code || ""); return stageError(SAFE_CODES.has(code) ? code : fallback); }
function exactUrl(value) {
  let url;
  try { url = new URL(String(value == null ? "" : value).trim()); } catch { return null; }
  if (url.protocol !== "https:" || url.hostname.toLowerCase() !== "www.eventbrite.com"
    || url.port || url.username || url.password) return null;
  const match = EVENT_PATH.exec(url.pathname);
  if (!match) return null;
  const id = match[2] || match[3];
  return Object.freeze({ canonical_url: `https://www.eventbrite.com${url.pathname}`, id });
}
function canonicalBinding(value) {
  const row = typeof value === "string" ? { canonical_url: value } : value;
  if (!row || typeof row !== "object" || Array.isArray(row)) return null;
  const parsed = exactUrl(row.canonical_url || row.href || row.url);
  if (!parsed) return null;
  const suppliedId = row.event_id ?? row.eventId ?? (row.dataset && row.dataset.eventId);
  if (suppliedId != null && String(suppliedId) !== parsed.id) return null;
  const eventRef = `eventbrite-event://event/${parsed.id}`;
  if (row.event_ref != null && String(row.event_ref) !== eventRef) return null;
  return Object.freeze({ event_ref: eventRef, canonical_url: parsed.canonical_url });
}
function listingFree(value) {
  const status = value && (value.paid_status ?? value.paidStatus ?? value.data_event_paid_status
    ?? (value.dataset && value.dataset.eventPaidStatus));
  return status == null || String(status).trim() === "" || /^(?:free|false|0)$/i.test(String(status).trim());
}
function exactCandidate(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)
    || value.provider !== "eventbrite" || !EVENT_REF.test(String(value.event_ref || ""))) invalid();
  const binding = canonicalBinding(value);
  if (!binding || binding.event_ref !== value.event_ref || binding.canonical_url !== value.canonical_url) invalid();
  if (value.title != null && !String(value.title).trim()) invalid();
  if (!Number.isFinite(Date.parse(String(value.starts_at || "")))
    || !Number.isFinite(Date.parse(String(value.ends_at || "")))
    || Date.parse(value.starts_at) >= Date.parse(value.ends_at)) invalid();
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
function jsonLdEvent(raw) {
  const source = raw && typeof raw === "object" && !Array.isArray(raw)
    && (raw.jsonld !== undefined || raw.jsonLd !== undefined) ? (raw.jsonld ?? raw.jsonLd) : raw;
  const nodes = Array.isArray(source) ? source
    : source && Array.isArray(source["@graph"]) ? source["@graph"] : [source];
  return nodes.find((node) => {
    const types = Array.isArray(node && node["@type"]) ? node["@type"] : [node && node["@type"]];
    return types.some((type) => type === "Event" || type === "SocialEvent"
      || /(?:^|\/)(?:Social)?Event$/.test(String(type || "")));
  }) || null;
}
function eventUrl(event) {
  const main = event && event.mainEntityOfPage;
  return String(event && event.url || (typeof main === "string" ? main : main && (main.url || main["@id"])) || "").trim();
}
function identifierValues(value) {
  const values = Array.isArray(value) ? value : [value];
  return values.flatMap((item) => {
    if (item && typeof item === "object") return [item.value, item.url, item["@id"]].filter((part) => part != null);
    return item == null ? [] : [item];
  }).map((item) => String(item).trim()).filter(Boolean);
}
function eventIdentityMatches(event, binding) {
  if (eventUrl(event) !== binding.canonical_url) return false;
  const id = binding.event_ref.split("/").pop();
  for (const value of [event && event.id, event && event.identifier, event && event["@id"]].flatMap(identifierValues)) {
    if (/^[1-9][0-9]*$/.test(value) ? value !== id : ![binding.canonical_url, binding.event_ref].includes(value)) return false;
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
function isTicketControl(text) { return text === "Get tickets" || text === "Reserve a spot"; }
function bodyText(raw, event) {
  return [raw && (raw.body_text ?? raw.bodyText), raw && raw.description, event && event.description]
    .filter((value) => value != null && String(value).trim()).map(String).join(" ");
}
function locationIsTokyo(event) {
  const locations = Array.isArray(event && event.location) ? event.location : [event && event.location];
  return locations.some((location) => {
    const address = location && (location.address || location);
    if (typeof address === "string") return /(?:Tokyo|東京)/i.test(address);
    if (!address || typeof address !== "object") return false;
    const country = String(address.addressCountry && typeof address.addressCountry === "object"
      ? address.addressCountry.name : address.addressCountry || address.country || "").toLowerCase();
    if (country && !["jp", "japan", "日本"].includes(country)) return false;
    return /(?:Tokyo|東京)/i.test([address.name, address.addressLocality, address.city, address.addressRegion,
      address.region, address.streetAddress, address.postalCode].filter(Boolean).join(" "));
  });
}
function offline(event) {
  const modes = Array.isArray(event && event.eventAttendanceMode) ? event.eventAttendanceMode : [event && event.eventAttendanceMode];
  return modes.length > 0 && modes.every((mode) => OFFLINE_MODE.has(String(mode || "")));
}
function numericZero(value) {
  if (typeof value === "number") return Number.isFinite(value) && value === 0;
  return typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value)) && Number(value) === 0;
}
function freeOffers(event, canonicalUrl) {
  const offers = Array.isArray(event && event.offers) ? event.offers : [event && event.offers];
  if (!offers.length || offers.some((offer) => !offer || typeof offer !== "object" || Array.isArray(offer))) return false;
  return offers.every((offer) => {
    if (String(offer.url || "").trim() !== canonicalUrl || !IN_STOCK.has(String(offer.availability || ""))) return false;
    const types = Array.isArray(offer["@type"]) ? offer["@type"] : [offer["@type"]];
    const allowed = (type) => /^(?:(?:https?:\/\/schema\.org\/)?(?:Aggregate)?Offer)$/.test(String(type || ""));
    if (!types.length || !types.every(allowed)) return false;
    const aggregate = types.some((type) => /^(?:(?:https?:\/\/schema\.org\/)?AggregateOffer)$/.test(String(type || "")));
    return aggregate ? numericZero(offer.lowPrice) && numericZero(offer.highPrice) : numericZero(offer.price);
  });
}
function normalizeDetail(binding, raw) {
  const event = jsonLdEvent(raw);
  if (!event) return null;
  if (!eventIdentityMatches(event, binding)) throw stageError("EVENTBRITE_DETAIL_IDENTITY_MISMATCH_FAILED");
  const starts = Date.parse(String(event.startDate || ""));
  const ends = Date.parse(String(event.endDate || ""));
  const title = String(event.name || "").trim();
  if (!title || !Number.isFinite(starts) || !Number.isFinite(ends) || starts >= ends) return null;
  const controls = controlsOf(raw);
  const detailText = bodyText(raw, event).replace(/\s+/g, " ").trim();
  const controlText = controls.map((control) => control.text).join(" ").replace(/\s+/g, " ").trim();
  const text = `${detailText} ${controlText}`.replace(/\s+/g, " ").trim();
  const paidDetailText = detailText.replace(NEGATIVE_PURCHASE_MARKER, " ").replace(EXPLICIT_FREE_MARKER, " ");
  const paidText = `${paidDetailText} ${controlText}`.replace(/\s+/g, " ").trim();
  const candidate = Object.freeze({
    provider: "eventbrite", event_ref: binding.event_ref, canonical_url: binding.canonical_url, title,
    starts_at: new Date(starts).toISOString(), ends_at: new Date(ends).toISOString(),
    registration_status: "available", ticket_price_status: "free", ticket_price_minor: 0,
  });
  return Object.freeze({ candidate, eligible: offline(event) && locationIsTokyo(event)
    && freeOffers(event, binding.canonical_url)
    && controls.filter((control) => control.visible).length === 1
    && controls.some((control) => control.visible && isTicketControl(control.text))
    && !BLOCKED_MARKER.test(text) && !MONEY_MARKER.test(paidText) && !MINIMUM_PURCHASE_MARKER.test(paidText) });
}
function calendarIntervals(calendar) {
  return Array.isArray(calendar) ? calendar : calendar && Array.isArray(calendar.busy_intervals) ? calendar.busy_intervals : [];
}
function overlaps(candidate, busy) {
  if (!busy || busy.kind !== "timed") return false;
  const start = Date.parse(candidate.starts_at); const end = Date.parse(candidate.ends_at);
  const busyStart = Date.parse(busy.start_at); const busyEnd = Date.parse(busy.end_at);
  return [start, end, busyStart, busyEnd].every(Number.isFinite) && start < busyEnd && end > busyStart;
}
function exactCoverage(candidate, busy) {
  return overlaps(candidate, busy) && String(busy.connector_idempotency || "") === createHash("sha256")
    .update(candidate.canonical_url, "utf8").digest("hex");
}
function defaultCalendarFree(candidate, calendar) {
  return !calendarIntervals(calendar).some((busy) => overlaps(candidate, busy) && !exactCoverage(candidate, busy));
}
function assertPageUrl(page, expected, code) {
  if (page && typeof page.url === "function" && String(page.url()) !== expected) throw stageError(code);
}
async function defaultReadListingBindings(page) {
  if (!page || typeof page.goto !== "function" || typeof page.evaluate !== "function") invalid();
  const listingUrls = [LIST_URL, `${LIST_URL}?page=2`, `${LIST_URL}?page=3`];
  const rows = [];
  for (const listingUrl of listingUrls) {
    try { await page.goto(listingUrl, { waitUntil: "domcontentloaded", timeout: 30_000 }); assertPageUrl(page, listingUrl, "EVENTBRITE_LISTING_NAVIGATION_FAILED"); }
    catch (error) { if (error && error.code) throw error; throw stageError("EVENTBRITE_LISTING_NAVIGATION_FAILED"); }
    try {
      const pageRows = await page.evaluate(() => [...document.querySelectorAll('[data-testid="search-event"]')].flatMap((root) => (
        [...root.querySelectorAll("a.event-card-link[data-event-id][href]")].map((anchor) => ({
          href: String(anchor.href || anchor.getAttribute("href") || ""),
          event_id: String(anchor.getAttribute("data-event-id") || (anchor.dataset && anchor.dataset.eventId) || ""),
          location: String(anchor.getAttribute("data-event-location") || (anchor.dataset && anchor.dataset.eventLocation) || ""),
          paid_status: String(anchor.getAttribute("data-event-paid-status") || (anchor.dataset && anchor.dataset.eventPaidStatus) || ""),
        }))
      )));
      if (!Array.isArray(pageRows)) throw new Error("listing contract");
      rows.push(...pageRows);
    } catch { throw stageError("EVENTBRITE_LISTING_READ_FAILED"); }
  }
  return rows;
}
async function defaultReadEventDetail(page, canonicalUrl) {
  if (!page || typeof page.goto !== "function" || typeof page.evaluate !== "function") invalid();
  try { await page.goto(canonicalUrl, { waitUntil: "domcontentloaded", timeout: 30_000 }); assertPageUrl(page, canonicalUrl, "EVENTBRITE_DETAIL_NAVIGATION_FAILED"); }
  catch (error) { if (error && error.code) throw error; throw stageError("EVENTBRITE_DETAIL_NAVIGATION_FAILED"); }
  try {
    return await page.evaluate(() => ({
      jsonld: [...document.querySelectorAll('script[type="application/ld+json"]')].flatMap((script) => { try { return [JSON.parse(script.textContent || "")]; } catch { return []; } }),
      body_text: document.body ? document.body.innerText : "",
      controls: [...document.querySelectorAll('[data-testid="conversion-bar-checkout-button"]')].map((node) => ({ text: String(node.innerText || node.textContent || "").trim(), visible: Boolean(node.offsetWidth || node.offsetHeight) })),
    }));
  } catch { throw stageError("EVENTBRITE_DETAIL_READ_FAILED"); }
}
async function defaultReadRegistrationView(page) {
  if (!page || typeof page.evaluate !== "function") invalid();
  let pageUrl = "";
  try { pageUrl = typeof page.url === "function" ? String(page.url()) : ""; } catch { return null; }
  try {
    const view = await page.evaluate(() => ({
      canonical_links: [...document.querySelectorAll("link[rel='canonical']")].map((node) => ({ href: String(node.href || node.getAttribute("href") || ""), visible: true })),
      controls: [...document.querySelectorAll('[data-testid="conversion-bar-checkout-button"]')].map((node) => ({ text: String(node.innerText || node.textContent || "").trim(), visible: Boolean(node.offsetWidth || node.offsetHeight) })),
      body_text: document.body ? document.body.innerText : "",
    }));
    return { page_url: pageUrl, ...(view || {}) };
  } catch { throw stageError("EVENTBRITE_REGISTRATION_READ_FAILED"); }
}
function normalizedView(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return {
    page_url: String(value.page_url || "").trim(),
    canonical_links: Array.isArray(value.canonical_links) ? value.canonical_links.map((link) => ({ href: String(link && (link.href || link.url) || "").trim(), visible: link && link.visible === true })) : [],
    controls: controlsOf(value), body_text: String(value.body_text || value.bodyText || ""),
    auth_required: value.auth_required === true, waitlist: value.waitlist === true,
  };
}
function completionCount(value) { return String(value || "").match(COMPLETION_MARKER)?.length || 0; }
const EVENTBRITE_CHECKOUT_FRAME_LIMIT = 16;
function eventbriteCheckoutFrameIdentity(frame, eventId) {
  if (!frame || typeof frame.url !== "function") return { checkout: true, valid: false };
  let href;
  try { href = String(frame.url()).trim(); } catch { return { checkout: true, valid: false }; }
  let url;
  try { url = new URL(href); } catch { return { checkout: true, valid: false }; }
  if (url.pathname !== "/checkout-external") return { checkout: false, valid: false };
  const ids = url.searchParams.getAll("eid");
  const authority = /^[a-z][a-z\d+.-]*:\/\/([^/?#]*)/i.exec(href)?.[1] || "";
  const valid = url.protocol === "https:" && url.hostname.toLowerCase() === "www.eventbrite.com"
    && authority.toLowerCase() === "www.eventbrite.com"
    && !url.port && !url.username && !url.password && !url.hash && !href.includes("#")
    && ids.length === 1 && ids[0] === String(eventId);
  return { checkout: true, valid };
}
async function readEventbriteDirectCheckoutCompletion(page, eventId) {
  if (!page || typeof page.mainFrame !== "function") return { status: "none" };
  let mainFrame;
  try { mainFrame = page.mainFrame(); } catch { return { status: "unavailable" }; }
  if (!mainFrame || typeof mainFrame.childFrames !== "function") return { status: "none" };
  let children;
  try { children = mainFrame.childFrames(); } catch { return { status: "unavailable" }; }
  if (!Array.isArray(children) || children.length > EVENTBRITE_CHECKOUT_FRAME_LIMIT) return { status: "unavailable" };
  const checkoutFrames = children.map((frame) => ({ frame, identity: eventbriteCheckoutFrameIdentity(frame, eventId) }))
    .filter(({ identity }) => identity.checkout);
  if (checkoutFrames.length === 0) return { status: "none" };
  if (checkoutFrames.length !== 1 || checkoutFrames[0].identity.valid !== true) return { status: "unavailable" };
  const frame = checkoutFrames[0].frame;
  if (typeof frame.evaluate !== "function") return { status: "unavailable" };
  let markers;
  try {
    markers = await frame.evaluate(() => {
      const text = String(document.body ? document.body.innerText || "" : "");
      const count = (marker) => text.split(marker).length - 1;
      const buttons = [...document.querySelectorAll("button")];
      const register = buttons.filter((button) => String(button.innerText || button.textContent || "")
        .replace(/\s+/g, " ").trim() === "Register").length;
      return { thanks: count("Thanks for your order!"), going: count("YOU'RE GOING TO"), register };
    });
  } catch { return { status: "unavailable" }; }
  if (!markers || typeof markers !== "object" || Array.isArray(markers)
    || !Number.isInteger(markers.thanks) || !Number.isInteger(markers.going) || !Number.isInteger(markers.register)
    || markers.thanks < 0 || markers.going < 0 || markers.register < 0) return { status: "unavailable" };
  return markers.thanks === 1 && markers.going === 1 && markers.register === 0
    ? { status: "complete" } : { status: "incomplete" };
}
function createEventbriteScriptFirstWorkflow(options = {}) {
  const now = options.now || (() => new Date());
  const readListingBindings = options.readListingBindings || options.readFindBindings || defaultReadListingBindings;
  const readEventDetail = options.readEventDetail || defaultReadEventDetail;
  const readRegistrationView = options.readRegistrationView || defaultReadRegistrationView;
  const isCalendarFree = options.isCalendarFree || defaultCalendarFree;
  const onDiscoveryAudit = options.onDiscoveryAudit || (() => {});
  if ([now, readListingBindings, readEventDetail, readRegistrationView, isCalendarFree, onDiscoveryAudit].some((value) => typeof value !== "function")) invalid();
  return Object.freeze({
    async discoverCandidates({ page, calendar }) {
      const observed = now();
      if (!(observed instanceof Date) || !Number.isFinite(observed.getTime())) invalid();
      let rows;
      try { rows = await readListingBindings(page, observed); } catch (error) { throw preserveSafe(error, "EVENTBRITE_LISTING_READ_FAILED"); }
      if (!Array.isArray(rows) || rows.length > 500) throw stageError("EVENTBRITE_LISTING_RESULT_CONTRACT_FAILED");
      const bindings = []; const seen = new Set();
      for (const row of rows) {
        if (!listingFree(row)) continue;
        const binding = canonicalBinding(row);
        if (!binding || seen.has(binding.event_ref)) continue;
        seen.add(binding.event_ref); bindings.push(binding);
      }
      const window = candidateWindow(observed); const exactCovered = []; const unprocessed = [];
      let withinWindowCount = 0; let eligibleCount = 0;
      for (const binding of bindings) {
        let raw; try { raw = await readEventDetail(page, binding.canonical_url); } catch (error) { throw preserveSafe(error, "EVENTBRITE_DETAIL_READ_FAILED"); }
        let normalized;
        try { normalized = normalizeDetail(binding, raw); } catch (error) {
          if (error && error.code === "EVENTBRITE_DETAIL_IDENTITY_MISMATCH_FAILED") throw error;
          continue;
        }
        if (!normalized) continue;
        const starts = Date.parse(normalized.candidate.starts_at);
        if (starts < window.start || starts >= window.end) continue;
        withinWindowCount += 1;
        if (!normalized.eligible) continue;
        eligibleCount += 1;
        let calendarFree;
        try { calendarFree = await isCalendarFree(normalized.candidate, calendar); } catch { throw stageError("EVENTBRITE_CALENDAR_CONFLICT_CHECK_FAILED"); }
        if (!calendarFree) continue;
        (calendarIntervals(calendar).some((busy) => exactCoverage(normalized.candidate, busy) ? true : false) ? exactCovered : unprocessed).push(normalized.candidate);
      }
      const selectedCount = exactCovered.length + unprocessed.length;
      await onDiscoveryAudit(Object.freeze({ discovered_count: rows.length, within_window_count: withinWindowCount, eligible_count: eligibleCount, calendar_free_count: selectedCount, selected_count: selectedCount }));
      return Object.freeze([...exactCovered, ...unprocessed]);
    },

    async runDirectAction({ page, candidate }) {
      exactCandidate(candidate); void page;
      return Object.freeze({ status: "failed", safe_reason: "eventbrite_direct_requires_harness" });
    },

    async readProviderState({ page, candidate }) {
      const selected = exactCandidate(candidate); let currentUrl = "";
      try { if (page && typeof page.url === "function") currentUrl = String(page.url()); } catch { return Object.freeze({ status: "unavailable" }); }
      if (currentUrl && currentUrl !== selected.canonical_url) return Object.freeze({ status: "unavailable" });
      let view; try { view = normalizedView(await readRegistrationView(page, selected)); } catch { return Object.freeze({ status: "unavailable" }); }
      if (!view || view.page_url !== selected.canonical_url) return Object.freeze({ status: "unavailable" });
      try { if (page && typeof page.url === "function" && String(page.url()) !== selected.canonical_url) return Object.freeze({ status: "unavailable" }); } catch { return Object.freeze({ status: "unavailable" }); }
      if (view.canonical_links.some((link) => link.href !== selected.canonical_url)) return Object.freeze({ status: "unavailable" });
      const visibleLinks = view.canonical_links.filter((link) => link.visible);
      const allControls = view.controls;
      const controls = allControls.filter((control) => control.visible);
      const text = `${view.body_text} ${allControls.map((control) => control.text).join(" ")}`;
      if (view.auth_required || view.waitlist || READBACK_UNSAFE.test(text)) return Object.freeze({ status: "unavailable" });
      const exactLink = visibleLinks.length === 1 && visibleLinks[0].href === selected.canonical_url && view.canonical_links.length === 1;
      const controlCompletion = allControls.some((control) => completionCount(control.text));
      const eventId = String(selected.event_ref).split("/").pop();
      const checkout = await readEventbriteDirectCheckoutCompletion(page, eventId);
      if (checkout.status === "unavailable") return Object.freeze({ status: "unavailable" });
      if (checkout.status === "complete") return Object.freeze({ status: exactLink ? "registered" : "unavailable" });
      if (checkout.status === "incomplete" && completionCount(view.body_text) !== 0) return Object.freeze({ status: "unavailable" });
      if (exactLink && completionCount(view.body_text) === 1 && !controlCompletion) return Object.freeze({ status: "registered" });
      const tickets = controls.filter((control) => isTicketControl(control.text));
      if (exactLink && controls.length === 1 && tickets.length === 1 && completionCount(view.body_text) === 0 && !controlCompletion) return Object.freeze({ status: "absent" });
      return Object.freeze({ status: "unavailable" });
    },
  });
}

module.exports = { createEventbriteScriptFirstWorkflow };
