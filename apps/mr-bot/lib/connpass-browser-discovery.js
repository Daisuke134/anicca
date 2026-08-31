"use strict";

const { canonicalEventUrl } = require("./canonical-event-url.js");
const { buildConnpassBrowserHandoff } = require("./event-source-handoff.js");

const DATE = /^(\d{4})-(\d{2})-(\d{2})$/;
const EVENT_PATH = /^\/event\/([1-9][0-9]*)\/?$/;

function invalid() { throw new Error("Connpass browser discovery unavailable"); }

function detailFieldInvalid(code) {
  const error = new Error("Connpass browser detail field unavailable");
  error.code = code;
  throw error;
}

function eventBinding(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) invalid();
  const canonical = canonicalEventUrl(value.canonical_url);
  if (!canonical) invalid();
  const parsed = new URL(canonical);
  const match = EVENT_PATH.exec(parsed.pathname);
  if (
    parsed.protocol !== "https:" || parsed.username || parsed.password || !match
    || !(parsed.hostname === "connpass.com" || parsed.hostname.endsWith(".connpass.com"))
    || String(value.event_ref || "") !== `connpass-event://event/${match[1]}`
  ) invalid();
  const calendarDate = value.calendar_date == null ? null : String(value.calendar_date);
  if (calendarDate !== null && !DATE.test(calendarDate)) invalid();
  return Object.freeze({
    event_ref: value.event_ref,
    canonical_url: canonical,
    ...(calendarDate ? { calendar_date: calendarDate } : {}),
  });
}

function localDate(instant, timeZone) {
  const date = new Date(instant);
  if (!Number.isFinite(date.getTime())) invalid();
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(date).filter((part) => part.type !== "literal")
    .map((part) => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

// The 4 accepted phrases below are the exact strings connpass renders on its
// join button (id="ParticipateButton") for an authenticated, eligible user —
// they are the same 4 strings `submitConnpassOnPage` targets via
// `getByRole("link", { name: /^(?:...)$/ })`, so this list is load-bearing
// for the working direct-submit flow and must not be loosened without new
// real evidence. A real anonymous fetch of 10 current Tokyo events
// (2026-08-17) shows connpass swaps that SAME button element to a login
// prompt ("ログイン・会員登録") plus a separate `<p class="em mb_5">イベント
// に申し込むには<br />ログインしてください</p>` when the session isn't
// logged in — that paragraph is not a button/link/input, so it never reaches
// `controls`, and none of these anonymous-session strings must ever be read
// as "available".
function normalizedRegistrationStatus(controls) {
  const text = (Array.isArray(controls) ? controls : []).map((value) => String(value).trim());
  if (text.some((value) => /^(?:参加票を表示|受付票を見る|申し込みをキャンセル|キャンセルする|Registered)$/.test(value))) return "registered";
  if (text.some((value) => /受付終了|募集終了|満員|定員に達しました/.test(value))) return "closed";
  if (text.some((value) => /^(?:このイベントに申し込む|イベントに申し込む|参加申し込み|申し込む)$/.test(value))) return "available";
  return "unknown";
}

// Real connpass.com/event/<id>/ pages (2026-08-17 sample: 390309, 391962,
// 392421, 399995, 403863, 403896, 403917, 403936, 403957, 403960) render the
// participation fee inside `<p class="join_fee">` per ticket tier — bare
// "無料" for a free tier, "2000円（前払い）"/"2000円（会場払い）" for a paid
// tier. That element matches the existing `[class*="fee"]` selector, so it
// already reaches `labels` (= `price_labels`); no selector change needed.
// Some events (391962) show TWO tiers, one free ("管理者" = staff) and one
// paid ("一般枠" = general) — treating that as free would register Dais into
// a page whose real ticket costs money, so ANY paid-looking label must win
// over a free-looking label from a different tier.
const PAID_LABEL = /[1-9][0-9,]*\s*(?:円|¥)/;
const FREE_LABEL = /(?:^|\s|参加費|費用|料金)(?:無料|free)(?:\s|$)/i;

function normalizedPrice(offers, labels) {
  const rows = Array.isArray(offers) ? offers : [];
  const offerPrices = rows.filter((offer) => offer && typeof offer === "object")
    .map((offer) => String(offer.price == null ? "" : offer.price).trim())
    .filter((value) => value !== "");
  const explicitFree = offerPrices.length > 0 && offerPrices.every((value) => /^(?:0|0\.0+)$/.test(value));
  const explicitPaid = offerPrices.some((value) => !/^(?:0|0\.0+)$/.test(value));

  const feeLabels = (Array.isArray(labels) ? labels : []).map((value) => String(value));
  const labelPaid = feeLabels.some((value) => PAID_LABEL.test(value));
  const labelFree = feeLabels.some((value) => FREE_LABEL.test(value));

  return !explicitPaid && !labelPaid && (explicitFree || labelFree)
    ? Object.freeze({ ticket_price_status: "free", ticket_price_minor: 0 })
    : Object.freeze({ ticket_price_status: "unknown", ticket_price_minor: null });
}

function normalizeConnpassEventDetail(input = {}) {
  const binding = eventBinding(input);
  const title = String(input.title || "").replace(/\s+/g, " ").trim();
  const startsAt = Date.parse(String(input.starts_at || ""));
  const endsAt = Date.parse(String(input.ends_at || ""));
  if (!title || title.length > 300) detailFieldInvalid("CONNPASS_DETAIL_TITLE_INVALID_FAILED");
  if (!Number.isFinite(startsAt)) detailFieldInvalid("CONNPASS_DETAIL_START_INVALID_FAILED");
  if (!Number.isFinite(endsAt)) detailFieldInvalid("CONNPASS_DETAIL_END_INVALID_FAILED");
  if (endsAt <= startsAt) detailFieldInvalid("CONNPASS_DETAIL_RANGE_INVALID_FAILED");
  return Object.freeze({
    provider: "connpass",
    event_ref: binding.event_ref,
    canonical_url: binding.canonical_url,
    title,
    starts_at: new Date(startsAt).toISOString(),
    ends_at: new Date(endsAt).toISOString(),
    venue_name: String(input.venue_name || "").replace(/\s+/g, " ").trim(),
    venue_address: String(input.address || "").replace(/\s+/g, " ").trim(),
    registration_status: normalizedRegistrationStatus(input.controls),
    ...normalizedPrice(input.offers, input.price_labels),
  });
}

async function readCalendarBindings(page) {
  if (!page || typeof page.evaluate !== "function") invalid();
  return page.evaluate(() => [...document.querySelectorAll('a[href*="/event/"]')].map((anchor) => {
    const url = new URL(anchor.href, location.href);
    const match = /^\/event\/([1-9][0-9]*)\/?$/.exec(url.pathname);
    // connpass renders the full date only inside `.tooltip` (`display:none` in
    // connpass.css), so `innerText` (render-aware) strips it on every calendar
    // row; `textContent` reads the DOM regardless of CSS visibility.
    const rowText = String(anchor.closest("li")?.textContent || "").replace(/\s+/g, " ");
    const dateMatch = /(20\d{2})[\/-](\d{1,2})[\/-](\d{1,2})/.exec(rowText);
    return match ? {
      event_ref: `connpass-event://event/${match[1]}`,
      canonical_url: `${url.origin}/event/${match[1]}/`,
      calendar_date: dateMatch
        ? `${dateMatch[1]}-${dateMatch[2].padStart(2, "0")}-${dateMatch[3].padStart(2, "0")}`
        : null,
    } : null;
  }).filter(Boolean));
}

async function readEventDetail(page) {
  if (!page || typeof page.evaluate !== "function") invalid();
  return page.evaluate(() => {
    const objects = [];
    for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
      try {
        const parsed = JSON.parse(script.textContent || "null");
        if (Array.isArray(parsed)) objects.push(...parsed);
        else if (parsed && Array.isArray(parsed["@graph"])) objects.push(...parsed["@graph"]);
        else if (parsed) objects.push(parsed);
      } catch {}
    }
    const event = objects.find((value) => {
      const type = value && value["@type"];
      return type === "Event" || (Array.isArray(type) && type.includes("Event"));
    }) || {};
    const locationValue = event.location || {};
    const addressValue = locationValue.address || {};
    const text = (selector) => String(document.querySelector(selector)?.textContent || "")
      .replace(/\s+/g, " ").trim() || null;
    const attr = (selector, name) => String(document.querySelector(selector)?.getAttribute(name) || "")
      .trim() || null;
    const canonical = document.querySelector('link[rel="canonical"]')?.href || location.href;
    const match = /\/event\/([1-9][0-9]*)\/?/.exec(new URL(canonical, location.href).pathname);
    const offers = (Array.isArray(event.offers) ? event.offers : [event.offers])
      .filter((offer) => offer && typeof offer === "object").slice(0, 100)
      .map((offer) => ({ price: offer.price, priceCurrency: offer.priceCurrency }));
    const controls = [...document.querySelectorAll(
      'button,a[role="button"],a.btn,input[type="submit"]',
    )].map((element) => String(
      element.innerText || element.value || element.getAttribute("aria-label") || "",
    ).replace(/\s+/g, " ").trim()).filter(Boolean).slice(0, 100);
    const priceLabels = [...document.querySelectorAll(
      '[class*="price"],[class*="fee"],[class*="amount"],dt,dd',
    )].map((element) => String(element.textContent || "").replace(/\s+/g, " ").trim())
      .filter((value) => value && value.length <= 300 && /(?:無料|free|参加費|¥|円)/i.test(value))
      .slice(0, 100);
    return {
      event_ref: match ? `connpass-event://event/${match[1]}` : null,
      canonical_url: match ? `${new URL(canonical, location.href).origin}/event/${match[1]}/` : null,
      title: event.name || text(".current_event_title") || text("h1"),
      summary: event.headline || null,
      description: event.description || text('[class*="description"]'),
      starts_at: event.startDate || attr(".dtstart .value-title", "title"),
      ends_at: event.endDate || attr(".dtend .value-title", "title"),
      venue_name: locationValue.name || text('[class*="event-place"]'),
      address: typeof addressValue === "string" ? addressValue
        : [addressValue.streetAddress, addressValue.addressLocality, addressValue.addressRegion]
          .filter(Boolean).join(" ") || null,
      offers,
      controls,
      price_labels: priceLabels,
    };
  });
}

async function discoverConnpassDateWithBrowser(input = {}) {
  const match = DATE.exec(String(input.date == null ? "" : input.date));
  const dailyDriver = input.dailyDriver;
  const timeZone = String(input.timeZone || "");
  if (!match || !timeZone || !dailyDriver || typeof dailyDriver.withEventPage !== "function") invalid();
  const calendarUrl = `https://connpass.com/calendar/?ym=${match[1]}${match[2]}&prefectures=13`;
  const rows = await dailyDriver.withEventPage("connpass", calendarUrl, readCalendarBindings);
  if (!Array.isArray(rows)) invalid();
  const unique = [];
  const seen = new Set();
  for (const raw of rows) {
    const binding = eventBinding(raw);
    if (binding.calendar_date && binding.calendar_date !== input.date) continue;
    if (!seen.has(binding.event_ref)) {
      seen.add(binding.event_ref);
      unique.push(binding);
    }
  }
  const candidates = [];
  for (const binding of unique) {
    const detail = await dailyDriver.withEventPage("connpass", binding.canonical_url, readEventDetail);
    const verified = eventBinding(detail);
    if (verified.event_ref !== binding.event_ref || verified.canonical_url !== binding.canonical_url) invalid();
    if (localDate(detail.starts_at, timeZone) === input.date) candidates.push(detail);
  }
  return buildConnpassBrowserHandoff({
    date: input.date,
    candidates,
    browserPageCount: unique.length + 1,
  });
}

module.exports = {
  discoverConnpassDateWithBrowser,
  normalizeConnpassEventDetail,
  readCalendarBindings,
  readEventDetail,
};
