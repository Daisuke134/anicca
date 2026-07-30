// lib/providers/luma.js — Luma provider: DISCOVER + ACT(RSVP) for the events pack.
//
// v1 discovers and RSVPs on Luma ONLY (decision D1). The Luma session lives in the CloakBrowser
// daily-driver persistent profile and its confirmation mail lands in the operator mailbox, so a ban
// lands on the operator's own account. The Luma API is organiser-side and gated behind Luma Plus,
// so the attendee-side RSVP has to go through that browser.
//
// ── Why this file is shaped the way it is ────────────────────────────────────────────────────────
// The implementation it replaces (connpass-lt-discover.py:166) decided "registered" by matching
// DOM text, and the string it matched — キャンセル — appears in the cancellation policy printed on
// every event page. It therefore reported success unconditionally, forever, while doing nothing.
//
// So nothing here judges success from page text. `readRsvpOutcome` looks at exactly two things:
//   1. the URL Luma itself rewrote to carry a `?tk=` registration token, and
//   2. the HTTP status of the registration call, observed on the wire, not in the DOM.
// Page text is captured into the receipt as a DIAGNOSTIC only and is never read by the decision.
//
// And `rsvp` does not decide at all. It returns raw material; runtime/loop/outbound/evidence.mjs is
// the only thing allowed to say whether that material amounts to a verified registration.
//
// ── Why the "free" test is not `ticket_info.is_free` ─────────────────────────────────────────────
// Measured 2026-07-31 against the live Tokyo feed: the discover feed reports is_free=false for
// events whose only ticket type is `{type:"free", cents:null}` whenever the event requires approval
// or has more than one ticket type (Supabase Meetup Tokyo #1, Camp AI: Agents at Work and Codex
// Meetup Tokyo #2 all did). Trusting that field would reject free events, and its `true` branch is
// not a proof of freeness either. The authoritative signal is the event page's `ticket_types`, so a
// candidate stays "paid until proven free" (`NOT_HYDRATED`) until that page has been read.
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const EVENT_BASE = "https://luma.com";
const DISCOVER_API = "https://api.lu.ma/discover/get-paginated-events";

// Luma serves a different page to non-browser agents; every request here carries a real browser UA
// so that what the parser sees is what a browser would see.
const BROWSER_UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) " +
  "Chrome/131.0.0.0 Safari/537.36";

// The registration call Luma's own front-end makes. Matching on the request path (not on a response
// body, and never on rendered text) keeps this a network-level observation.
const REGISTER_CALL = /\/event\/(independent\/)?(register|join|add-guests)/i;

const SLUG_PATTERN = /^[A-Za-z0-9][A-Za-z0-9-]{2,80}$/;

// ─────────────────────────────────────────────────────────────────────── pure: parsing

/**
 * Pull the Next.js SSR payload out of a Luma page. Both the city page and an event page carry it.
 * @throws when the page is not a Luma SSR page (an anti-bot interstitial, a 404 shell, …).
 */
function parseNextData(html) {
  const text = String(html == null ? "" : html);
  const match = text.match(/<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/);
  if (!match) throw new Error("luma page carries no __NEXT_DATA__ payload");
  try {
    return JSON.parse(match[1]);
  } catch (error) {
    throw new Error(`luma __NEXT_DATA__ is not valid JSON: ${error.message}`);
  }
}

function ssrData(html) {
  const next = parseNextData(html);
  const data = next && next.props && next.props.pageProps
    && next.props.pageProps.initialData && next.props.pageProps.initialData.data;
  if (!data || typeof data !== "object") {
    throw new Error("luma __NEXT_DATA__ has no props.pageProps.initialData.data");
  }
  return data;
}

/**
 * A discover city page ("https://luma.com/tokyo").
 * @returns {{placeApiId: string, entries: object[]}} the place id the paginated API needs, plus the
 *          first page of entries the page was server-rendered with.
 */
function parseCityPage(html) {
  const data = ssrData(html);
  const placeApiId = String((data.place && data.place.api_id) || "");
  if (!placeApiId) throw new Error("luma city page carries no place api_id");
  return { placeApiId, entries: Array.isArray(data.events) ? data.events : [] };
}

/** The paginated discover API response. */
function parseDiscoverPayload(payload) {
  const body = payload && typeof payload === "object" ? payload : {};
  return {
    entries: Array.isArray(body.entries) ? body.entries : [],
    hasMore: body.has_more === true,
    nextCursor: body.next_cursor == null ? null : String(body.next_cursor),
  };
}

function ticketType(raw) {
  const t = raw && typeof raw === "object" ? raw : {};
  return Object.freeze({
    apiId: String(t.api_id || ""),
    name: String(t.name || ""),
    type: String(t.type || ""),
    cents: t.cents == null ? null : Number(t.cents),
    minCents: t.min_cents == null ? null : Number(t.min_cents),
    requireApproval: t.require_approval === true,
    isHidden: t.is_hidden === true,
    maxCapacity: t.max_capacity == null ? null : Number(t.max_capacity),
  });
}

/** A ticket is FREE only when Luma types it free AND records no price of any kind. */
function isFreeTicket(ticket) {
  return ticket.type === "free" && ticket.cents == null && ticket.minCents == null;
}

function selectableTickets(ticketTypes) {
  return (ticketTypes || []).filter((ticket) => !ticket.isHidden);
}

/**
 * Normalise either a discover entry or an event page into one shape.
 * `ticketTypes === null` means "not hydrated yet" — NOT "this event has no tickets".
 */
function normalizeEvent(raw) {
  const source = raw && typeof raw === "object" ? raw : {};
  const event = source.event && typeof source.event === "object" ? source.event : {};
  const geo = (event.geo_address_info && typeof event.geo_address_info === "object")
    ? event.geo_address_info
    : {};
  const hasTicketTypes = Array.isArray(source.ticket_types);
  const info = source.ticket_info && typeof source.ticket_info === "object" ? source.ticket_info : {};
  const slug = String(event.url || "");
  return Object.freeze({
    id: String(event.api_id || source.api_id || ""),
    slug,
    url: slug ? `${EVENT_BASE}/${slug}` : "",
    name: String(event.name || ""),
    startsAt: event.start_at == null ? null : String(event.start_at),
    endsAt: event.end_at == null ? null : String(event.end_at),
    timezone: event.timezone == null ? null : String(event.timezone),
    locationType: String(event.location_type || ""),
    region: geo.region == null ? null : String(geo.region),
    city: geo.city == null ? null : String(geo.city),
    country: geo.country == null ? null : String(geo.country),
    countryCode: geo.country_code == null ? null : String(geo.country_code),
    // Luma withholds the street address until you are registered; `full_address` only shows up on a
    // re-read of the page once the RSVP has landed.
    venue: geo.full_address == null
      ? (geo.address == null ? null : String(geo.address))
      : String(geo.full_address),
    availability: String(source.registration_availability || ""),
    requiresApproval: info.require_approval === true,
    categories: Array.isArray(source.categories)
      ? Object.freeze(source.categories.map((c) => String((c && c.name) || c)))
      : null,
    ticketTypes: hasTicketTypes ? Object.freeze(source.ticket_types.map(ticketType)) : null,
    hydrated: hasTicketTypes,
  });
}

/** The event page wraps the same object; kept as a named door so callers read intent. */
function parseEventPage(html) {
  return normalizeEvent(ssrData(html));
}

// ─────────────────────────────────────────────────────────────────────── pure: screening

const DEFAULT_SCREEN = Object.freeze({
  regions: Object.freeze(["Tokyo"]),
  countryCodes: Object.freeze(["JP"]),
  requireOpen: true,
  allowApproval: false,
});

/**
 * Deterministic screening. This is the "denylist half" of QUALIFY (spec §3.1): it can only ever
 * REJECT, and only by reading structured fields Luma itself publishes. It never decides that an
 * event is worth attending — that judgment belongs to the model in the QUALIFY stage, reading the
 * event body.
 *
 * @returns {{ok: boolean, rejections: Array<{code: string, detail: string}>, ticket: object|null}}
 */
function screenEvent(event, options = {}) {
  const opts = { ...DEFAULT_SCREEN, ...options };
  const rejections = [];
  const reject = (code, detail) => rejections.push(Object.freeze({ code, detail }));

  if (!event || typeof event !== "object" || !event.slug) {
    return Object.freeze({
      ok: false,
      rejections: Object.freeze([Object.freeze({ code: "UNPARSEABLE", detail: "event has no slug" })]),
      ticket: null,
    });
  }

  // An online event is a DEFECT, never a fallback. `location_type` is Luma's own enum
  // ("offline" / "online"), so this is a field read and not a guess about wording.
  if (event.locationType !== "offline") {
    reject("ONLINE_EVENT", `location_type is ${JSON.stringify(event.locationType)}, not "offline"`);
  }

  const regions = opts.regions || [];
  if (regions.length && !regions.includes(String(event.region))) {
    reject("REGION_EXCLUDED", `region ${JSON.stringify(event.region)} is not in ${regions.join("/")}`);
  }
  const countries = opts.countryCodes || [];
  if (countries.length && event.countryCode && !countries.includes(String(event.countryCode))) {
    reject("COUNTRY_EXCLUDED", `country ${JSON.stringify(event.countryCode)} is not in ${countries.join("/")}`);
  }

  // waitlist / sold-out are not registrations: they produce no ticket and no confirmation, so they
  // can never satisfy the evidence contract.
  if (opts.requireOpen && event.availability !== "open") {
    reject("NOT_OPEN", `registration_availability is ${JSON.stringify(event.availability)}`);
  }

  let ticket = null;
  if (!event.hydrated) {
    // Paid until proven free: the discover feed cannot prove freeness (see the header note).
    reject("NOT_HYDRATED", "ticket_types have not been read from the event page yet");
  } else {
    const selectable = selectableTickets(event.ticketTypes);
    const free = selectable.filter(isFreeTicket);
    if (free.length === 0) {
      reject("NOT_FREE", `no free ticket among ${selectable.length} ticket type(s)`);
    } else if (opts.ticketApiId || opts.ticketName) {
      ticket = free.find((t) => (opts.ticketApiId ? t.apiId === opts.ticketApiId : t.name === opts.ticketName)) || null;
      if (!ticket) {
        reject("TICKET_NOT_FOUND", `no free ticket named ${JSON.stringify(opts.ticketName || opts.ticketApiId)}`);
      }
    } else if (free.length > 1) {
      // Two free tickets on an offline event is the venue/online split (measured: 会場参加 vs
      // オンライン参加). Guessing which is in-person from its NAME would be exactly the string
      // matching this provider exists to avoid, and guessing wrong books an online seat — the
      // defect. So the engine refuses, and the caller (the model, in QUALIFY) must name one.
      reject(
        "TICKET_CHOICE_REQUIRED",
        `${free.length} free ticket types (${free.map((t) => t.name).join(" / ")}); caller must name one`,
      );
    } else {
      [ticket] = free;
    }
    if (ticket && ticket.requireApproval && opts.allowApproval !== true) {
      reject("APPROVAL_REQUIRED", `ticket ${JSON.stringify(ticket.name)} requires host approval`);
    }
  }

  return Object.freeze({
    ok: rejections.length === 0,
    rejections: Object.freeze(rejections),
    ticket: rejections.length === 0 ? ticket : null,
  });
}

// Ordering only. Luma publishes `categories` as structured tags on the event page, so this reads a
// field rather than pattern-matching prose. It decides NOTHING about whether to apply; it decides
// which candidate the model is asked about first.
const DEFAULT_CATEGORY_RANK = Object.freeze(["Crypto", "AI", "Tech"]);

function topicScore(event, rank = DEFAULT_CATEGORY_RANK) {
  const categories = (event && event.categories) || [];
  if (!categories.length) return 0;
  const hits = rank.filter((name) => categories.includes(name));
  if (!hits.length) return 0;
  // crypto+AI outranks crypto alone, which outranks AI, which outranks broader tech: a
  // co-occurrence is worth more than either tag by itself, and the earliest tag in `rank` wins ties.
  return (rank.length - rank.indexOf(hits[0])) * 10 + (hits.length - 1);
}

/** Highest topic score first, then soonest. Total and stable, so a pass is reproducible. */
function rankEvents(events, options = {}) {
  const rank = options.categoryRank || DEFAULT_CATEGORY_RANK;
  return [...(events || [])].sort((a, b) => {
    const delta = topicScore(b, rank) - topicScore(a, rank);
    if (delta !== 0) return delta;
    return String(a.startsAt || "").localeCompare(String(b.startsAt || ""));
  });
}

/** Screen a hydrated list, then rank the survivors. Returns both halves so failures stay visible. */
function selectEvents(events, options = {}) {
  const accepted = [];
  const rejected = [];
  for (const event of events || []) {
    const verdict = screenEvent(event, options);
    if (verdict.ok) accepted.push(Object.freeze({ ...event, ticket: verdict.ticket }));
    else {
      rejected.push(Object.freeze({
        slug: event && event.slug,
        name: event && event.name,
        rejections: verdict.rejections,
      }));
    }
  }
  return Object.freeze({
    accepted: Object.freeze(rankEvents(accepted, options)),
    rejected: Object.freeze(rejected),
  });
}

// ─────────────────────────────────────────────────────────────────────── pure: URLs and outcome

/**
 * EVIDENCE E3: the durable event URL. Never a one-shot `/join/complete/` result URL, and never a
 * URL carrying the per-guest `?tk=` / `?pk=` token (a secret, not a canonical page).
 */
function canonicalEventUrl(slugOrUrl) {
  const raw = String(slugOrUrl == null ? "" : slugOrUrl).trim();
  if (!raw) throw new Error("luma canonicalEventUrl needs a slug or URL");
  let slug = raw;
  if (/^https?:\/\//i.test(raw)) {
    let parsed;
    try {
      parsed = new URL(raw);
    } catch {
      throw new Error(`luma canonicalEventUrl cannot parse ${JSON.stringify(raw)}`);
    }
    const segments = parsed.pathname.split("/").filter(Boolean);
    if (!segments.length) throw new Error(`luma canonicalEventUrl found no slug in ${JSON.stringify(raw)}`);
    // A one-shot result URL and a per-guest ticket URL both end in something slug-shaped. Taking
    // the last segment of either would mint a canonical URL that 404s — the exact bug at
    // gcal_write.py:135. Refuse them by their PATH instead of hoping the tail looks wrong.
    if (segments[0] === "join" || segments[0] === "e") {
      throw new Error(`luma canonicalEventUrl refuses the one-shot/ticket URL ${JSON.stringify(raw)}`);
    }
    [slug] = segments.slice(-1);
  }
  if (!SLUG_PATTERN.test(slug)) {
    throw new Error(`luma canonicalEventUrl refuses ${JSON.stringify(slug)} as a slug`);
  }
  return `${EVENT_BASE}/${slug}`;
}

/**
 * Guest key extraction (spec §5 / TODO #8). Luma puts the key in the confirmation mail as
 * `https://luma.com/<slug>?pk=g-…` and in the ticket link `https://luma.com/e/ticket/<evt>?pk=g-…`.
 * Measured against a real message on 2026-07-31; there is no QR image in the mail.
 */
function extractGuestKey(text) {
  const body = String(text == null ? "" : text);
  const keys = new Set();
  let slug = null;
  let ticketUrl = null;
  const eventLink = /https:\/\/luma\.com\/([A-Za-z0-9][A-Za-z0-9-]{2,80})\?pk=(g-[A-Za-z0-9]+)/g;
  for (let m = eventLink.exec(body); m; m = eventLink.exec(body)) {
    if (m[1] === "e" || m[1] === "join") continue;
    if (!slug) slug = m[1];
    keys.add(m[2]);
  }
  const ticketLink = /https:\/\/luma\.com\/e\/ticket\/(evt-[A-Za-z0-9]+)\?pk=(g-[A-Za-z0-9]+)/g;
  for (let m = ticketLink.exec(body); m; m = ticketLink.exec(body)) {
    if (!ticketUrl) [ticketUrl] = m;
    keys.add(m[2]);
  }
  const joinLink = /https:\/\/luma\.com\/join\/(g-[A-Za-z0-9]+)/g;
  for (let m = joinLink.exec(body); m; m = joinLink.exec(body)) keys.add(m[1]);
  const list = [...keys];
  return Object.freeze({
    guestKey: list.length ? list[0] : null,
    guestKeys: Object.freeze(list),
    slug,
    ticketUrl,
  });
}

/** Parse a `gog gmail get --json` payload for a Luma confirmation. Pure; the fetch is the caller's. */
function parseConfirmationEmail(message) {
  const msg = message && typeof message === "object" ? message : {};
  const headers = msg.headers && typeof msg.headers === "object" ? msg.headers : {};
  const id = String((msg.message && msg.message.id) || msg.id || "");
  const found = extractGuestKey(JSON.stringify(msg));
  return Object.freeze({
    message_id: id || null,
    rfc822_message_id: headers.message_id ? String(headers.message_id) : null,
    subject: headers.subject ? String(headers.subject) : null,
    from: headers.from ? String(headers.from) : null,
    to: headers.to ? String(headers.to) : null,
    date: headers.date ? String(headers.date) : null,
    guestKey: found.guestKey,
    slug: found.slug,
    ticketUrl: found.ticketUrl,
  });
}

/**
 * Did the registration land? Two wire-level signals ONLY:
 *   tk   — Luma rewrote the address bar to carry a registration token we did not put there;
 *   http — the registration endpoint answered 2xx, observed on the network.
 * Page text is never consulted. A page that merely SAYS 参加確定！ proves nothing.
 */
function readRsvpOutcome(observation = {}) {
  const finalUrl = String(observation.finalUrl || "");
  let tk = null;
  if (finalUrl) {
    try {
      tk = new URL(finalUrl).searchParams.get("tk");
    } catch {
      tk = null;
    }
  }
  const calls = (observation.httpEvidence || [])
    .filter((call) => REGISTER_CALL.test(String((call && call.url) || "")));
  const accepted = calls.filter((call) => Number(call.status) >= 200 && Number(call.status) <= 299);
  const signals = [];
  if (tk) signals.push("tk_token");
  if (accepted.length) signals.push("register_2xx");
  return Object.freeze({
    registered: signals.length > 0,
    tk,
    signals: Object.freeze(signals),
    registerCalls: Object.freeze(calls),
    acceptedCall: accepted.length ? accepted[accepted.length - 1] : null,
  });
}

/**
 * Shape a receipt (+ freshly read artifact bytes, + an observed HEAD status, + an optional
 * confirmation mail) into the bundle runtime/loop/outbound/evidence.mjs judges.
 * This function ASSEMBLES. It does not decide — verifyEvidence does.
 */
function buildEvidence(receipt, extra = {}) {
  const r = receipt && typeof receipt === "object" ? receipt : {};
  const confirmation = extra.confirmation && extra.confirmation.message_id ? extra.confirmation : null;
  const e1 = confirmation
    ? { kind: "email", message_id: confirmation.message_id, subject: confirmation.subject || null }
    : (r.httpEvidence && r.httpEvidence.status != null
      ? { kind: "http", status: Number(r.httpEvidence.status), url: r.httpEvidence.url || null }
      : null);
  return Object.freeze({
    e1,
    e2: {
      path: r.artifactPath || null,
      ...(extra.artifactBytes ? { bytes: extra.artifactBytes } : {}),
    },
    e3: {
      url: r.canonicalUrl || null,
      source_url: r.requestedUrl || null,
      head_status: extra.headStatus == null ? null : Number(extra.headStatus),
    },
  });
}

// ─────────────────────────────────────────────────────────────────────── I/O: discover

function resolveFetch(opts) {
  const impl = opts && opts.fetchImpl;
  if (typeof impl === "function") return impl;
  if (typeof fetch === "function") return fetch;
  throw new Error("luma provider needs a fetch implementation");
}

const sleep = (ms) => new Promise((resolve) => { setTimeout(resolve, ms); });

async function fetchText(url, opts) {
  const doFetch = resolveFetch(opts);
  const response = await doFetch(url, {
    headers: { "user-agent": BROWSER_UA, accept: "text/html,application/json" },
    redirect: "follow",
  });
  if (!response.ok) throw new Error(`luma GET ${url} answered ${response.status}`);
  return response.text();
}

async function fetchJson(url, opts) {
  const doFetch = resolveFetch(opts);
  const response = await doFetch(url, {
    headers: { "user-agent": BROWSER_UA, accept: "application/json" },
    redirect: "follow",
  });
  if (!response.ok) throw new Error(`luma GET ${url} answered ${response.status}`);
  return response.json();
}

/** EVIDENCE E3: the caller observes HEAD here; the gate only judges the number it reports. */
async function headStatus(url, opts = {}) {
  const doFetch = resolveFetch(opts);
  const response = await doFetch(String(url), {
    method: "HEAD",
    headers: { "user-agent": BROWSER_UA },
    redirect: "follow",
  });
  return Number(response.status);
}

async function fetchEventPage(slug, opts = {}) {
  return parseEventPage(await fetchText(canonicalEventUrl(slug), opts));
}

/**
 * DISCOVER.
 *   1. read the city page for the discover place id (never hardcode one),
 *   2. page the public discover API for that place, optionally narrowed by Luma's own category tag,
 *   3. cheap-screen on the fields the feed carries (offline / region / open),
 *   4. hydrate the survivors from their event pages so freeness can actually be proven,
 *   5. screen again and rank.
 *
 * @returns {{ok: boolean, candidates: object[], rejected: object[], reason?: string}}
 */
async function discoverEvents(options = {}) {
  const opts = options && typeof options === "object" ? options : {};
  const city = String(opts.city || "tokyo");
  const limit = Number.isInteger(opts.paginationLimit) ? opts.paginationLimit : 100;
  const hydrateLimit = Number.isInteger(opts.hydrateLimit) ? opts.hydrateLimit : 12;
  const politeMs = Number.isInteger(opts.politeDelayMs) ? opts.politeDelayMs : 1000;

  let placeApiId = opts.placeApiId ? String(opts.placeApiId) : null;
  let entries = [];
  try {
    if (!placeApiId) {
      const cityPage = parseCityPage(await fetchText(`${EVENT_BASE}/${city}`, opts));
      placeApiId = cityPage.placeApiId;
      entries = cityPage.entries;
    }
    const params = new URLSearchParams({
      discover_place_api_id: placeApiId,
      pagination_limit: String(limit),
    });
    if (opts.categories) params.set("categories", String(opts.categories));
    const page = parseDiscoverPayload(await fetchJson(`${DISCOVER_API}?${params}`, opts));
    if (page.entries.length) entries = page.entries;
  } catch (error) {
    return Object.freeze({
      ok: false,
      candidates: Object.freeze([]),
      rejected: Object.freeze([]),
      reason: `luma_discover_failed: ${error.message}`,
    });
  }

  const feed = entries.map(normalizeEvent);
  // Cheap screen first, so the hydration budget is spent only on plausible events. NOT_HYDRATED,
  // NOT_FREE and TICKET_CHOICE_REQUIRED are expected here and are not yet reasons to drop anything:
  // only the event page can settle them.
  const deferred = new Set(["NOT_HYDRATED", "NOT_FREE", "TICKET_CHOICE_REQUIRED"]);
  const preliminary = feed.filter((event) => (
    !screenEvent(event, opts).rejections.some((r) => !deferred.has(r.code))
  ));

  const hydrated = [];
  const hydrationErrors = [];
  for (const event of preliminary.slice(0, hydrateLimit)) {
    try {
      hydrated.push(await fetchEventPage(event.slug, opts));
    } catch (error) {
      hydrationErrors.push({ slug: event.slug, error: error.message });
    }
    // connpass' ToS taught the house rule: never burst a third party's site (spec §7).
    if (politeMs > 0) await sleep(politeMs);
  }

  const selection = selectEvents(hydrated, opts);
  return Object.freeze({
    ok: true,
    place_api_id: placeApiId,
    candidates: selection.accepted,
    rejected: Object.freeze([...selection.rejected, ...hydrationErrors]),
    seen: feed.length,
  });
}

// ─────────────────────────────────────────────────────────────────────── I/O: RSVP

// CTA wording differs per event and per locale. `.last` matters: the section HEADING often matches
// the same words as the button, and the first match is then the heading, not the control.
const CTA_SELECTORS = Object.freeze([
  'button:has-text("参加登録")',
  'button:has-text("One-Click Register")',
  'button:has-text("Request to Join")',
  'button:has-text("Register")',
]);
const NAME_SELECTORS = Object.freeze([
  'input[placeholder="お名前"]',
  'input[placeholder="Your Name"]',
  'input[placeholder="Name"]',
  'input[name="name"]',
]);
const EMAIL_SELECTORS = Object.freeze([
  'input[placeholder="you@email.com"]',
  'input[type="email"]',
]);
const SUBMIT_SELECTORS = Object.freeze([
  'button:has-text("参加登録")',
  'button:has-text("Register")',
  'button:has-text("送信")',
  'button:has-text("Submit")',
  'button:has-text("Request to Join")',
]);

async function clickFirstAvailable(scope, selectors, { timeout = 4000 } = {}) {
  for (const selector of selectors) {
    const locator = scope.locator(selector).last();
    try {
      if (await locator.count() === 0) continue;
      await locator.click({ timeout });
      return selector;
    } catch {
      // Matched something unclickable (hidden, detached). Try the next wording.
    }
  }
  return null;
}

async function fillFirstAvailable(scope, selectors, value, { timeout = 4000 } = {}) {
  for (const selector of selectors) {
    const locator = scope.locator(selector).last();
    try {
      if (await locator.count() === 0) continue;
      await locator.fill(String(value), { timeout });
      return selector;
    } catch {
      // ignore and try the next wording
    }
  }
  return null;
}

/**
 * ACT. Drives the SHARED CloakBrowser daily-driver over CDP.
 *
 * ★ Contract with that browser (non-negotiable) ★
 *   - attach to the EXISTING persistent context (`contexts()[0]`); never launch a second browser
 *     and never call launch_persistent_context on a profile that is already in use;
 *   - open a NEW page and close ONLY that page;
 *   - never close the context, never kill the browser process, never touch anyone else's tab.
 * The CDP URL must be supplied by the caller, which is expected to have obtained it from
 * browser-guard.sh. This provider deliberately knows no port number.
 *
 * @returns the raw material for the Evidence Contract. It does NOT decide success.
 */
async function rsvp(eventUrl, identity = {}, options = {}) {
  const opts = options && typeof options === "object" ? options : {};
  const cdpUrl = String(opts.cdpUrl || "");
  if (!cdpUrl) throw new Error("luma.rsvp needs a leased cdpUrl (see browser-guard.sh acquire)");
  const requestedUrl = String(eventUrl || "");
  const canonicalUrl = canonicalEventUrl(requestedUrl);
  const artifactDir = String(opts.artifactDir || "");
  if (!artifactDir) throw new Error("luma.rsvp needs an artifactDir for the E2 screenshot");
  const name = String(identity.name || "");
  const email = String(identity.email || "");
  if (!name || !email) throw new Error("luma.rsvp needs identity {name, email}");

  const { chromium } = opts.playwright || require("playwright-core");
  const browser = await chromium.connectOverCDP(cdpUrl);
  let page = null;
  const httpEvidence = [];
  const diagnostics = [];
  try {
    const [context] = browser.contexts();
    if (!context) throw new Error("no existing browser context on the leased CDP endpoint");
    page = await context.newPage();
    page.on("response", (response) => {
      const url = response.url();
      if (!/api\.lu\.ma|luma\.com/.test(url)) return;
      httpEvidence.push({
        url,
        method: response.request().method(),
        status: response.status(),
        at: new Date().toISOString(),
      });
    });

    await page.goto(canonicalUrl, { waitUntil: "domcontentloaded", timeout: 45000 });
    await page.waitForTimeout(opts.hydrationMs == null ? 2500 : opts.hydrationMs);

    const ticketSelectors = opts.ticketName
      ? [
        `button:has-text(${JSON.stringify(opts.ticketName)})`,
        `label:has-text(${JSON.stringify(opts.ticketName)})`,
        `div[role="button"]:has-text(${JSON.stringify(opts.ticketName)})`,
      ]
      : null;

    // Named ticket first: on a venue/online split, the wrong default books the defect.
    if (ticketSelectors) {
      diagnostics.push(`ticket_click:${await clickFirstAvailable(page, ticketSelectors) || "none"}`);
      await page.waitForTimeout(800);
    }

    diagnostics.push(`cta:${await clickFirstAvailable(page, CTA_SELECTORS, { timeout: 8000 }) || "none"}`);
    await page.waitForTimeout(2000);

    // The modal is the last dialog on the page; scoping the fills to it keeps them off the
    // newsletter box that sits in the footer of many Luma pages.
    const dialog = page.locator('[role="dialog"]').last();
    const scope = (await dialog.count()) > 0 ? dialog : page;
    if (ticketSelectors) {
      diagnostics.push(`modal_ticket:${await clickFirstAvailable(scope, ticketSelectors) || "none"}`);
      await page.waitForTimeout(600);
    }
    diagnostics.push(`name:${await fillFirstAvailable(scope, NAME_SELECTORS, name) || "prefilled_or_absent"}`);
    diagnostics.push(`email:${await fillFirstAvailable(scope, EMAIL_SELECTORS, email) || "prefilled_or_absent"}`);
    if (identity.phone) {
      diagnostics.push(`phone:${await fillFirstAvailable(scope, ['input[type="tel"]'], identity.phone) || "absent"}`);
    }

    diagnostics.push(`submit:${await clickFirstAvailable(scope, SUBMIT_SELECTORS, { timeout: 8000 }) || "none"}`);

    // Wait for the WIRE, not for words: either Luma rewrites the URL with ?tk=, or the register
    // endpoint answers. Whichever comes first ends the wait; neither coming is an honest failure.
    const deadline = Date.now() + (opts.confirmTimeoutMs == null ? 30000 : opts.confirmTimeoutMs);
    while (Date.now() < deadline) {
      if (readRsvpOutcome({ finalUrl: page.url(), httpEvidence }).registered) break;
      await page.waitForTimeout(1000);
    }
    await page.waitForTimeout(1500);

    const outcome = readRsvpOutcome({ finalUrl: page.url(), httpEvidence });

    fs.mkdirSync(artifactDir, { recursive: true });
    const artifactPath = path.join(
      artifactDir,
      `luma-${canonicalUrl.split("/").pop()}-${new Date().toISOString().replace(/[:.]/g, "-")}.png`,
    );
    await page.screenshot({ path: artifactPath, fullPage: false });

    // The street address only becomes readable once registered; re-read the SSR payload afterwards.
    let venue = null;
    let startsAt = null;
    let guestKey = null;
    try {
      await page.reload({ waitUntil: "domcontentloaded", timeout: 45000 });
      await page.waitForTimeout(2000);
      const html = await page.content();
      const after = parseEventPage(html);
      venue = after.venue;
      startsAt = after.startsAt;
      guestKey = extractGuestKey(html).guestKey;
    } catch (error) {
      diagnostics.push(`post_read_failed:${error.message}`);
    }

    return Object.freeze({
      requestedUrl,
      canonicalUrl,
      // E1 material: the registration call as observed on the wire (null when none was seen).
      httpEvidence: outcome.acceptedCall ? Object.freeze({ kind: "http", ...outcome.acceptedCall }) : null,
      httpEvidenceAll: Object.freeze(httpEvidence),
      artifactPath,
      guestKey,
      venue,
      startsAt,
      observed: Object.freeze({
        finalUrl: page.url(),
        tk: outcome.tk,
        signals: outcome.signals,
        registerCalls: outcome.registerCalls,
        // Diagnostics only. Nothing above reads these strings.
        diagnostics: Object.freeze(diagnostics),
      }),
    });
  } finally {
    // Close OUR page only, then drop the CDP connection. Neither closes the shared browser.
    if (page) await page.close().catch(() => {});
    await browser.close().catch(() => {});
  }
}

module.exports = {
  // constants
  EVENT_BASE,
  DISCOVER_API,
  BROWSER_UA,
  DEFAULT_SCREEN,
  DEFAULT_CATEGORY_RANK,
  // pure
  parseNextData,
  parseCityPage,
  parseDiscoverPayload,
  parseEventPage,
  normalizeEvent,
  screenEvent,
  topicScore,
  rankEvents,
  selectEvents,
  canonicalEventUrl,
  extractGuestKey,
  parseConfirmationEmail,
  readRsvpOutcome,
  buildEvidence,
  // I/O
  discoverEvents,
  fetchEventPage,
  headStatus,
  rsvp,
};
