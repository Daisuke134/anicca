"use strict";

const { canonicalEventUrl } = require("./canonical-event-url.js");
const { buildConnpassBrowserHandoff } = require("./event-source-handoff.js");

const DATE = /^(\d{4})-(\d{2})-(\d{2})$/;
const EVENT_PATH = /^\/event\/([1-9][0-9]*)\/?$/;

function invalid() { throw new Error("Connpass browser discovery unavailable"); }

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

async function readCalendarBindings(page) {
  if (!page || typeof page.evaluate !== "function") invalid();
  return page.evaluate(() => [...document.querySelectorAll('a[href*="/event/"]')].map((anchor) => {
    const url = new URL(anchor.href, location.href);
    const match = /^\/event\/([1-9][0-9]*)\/?$/.exec(url.pathname);
    const rowText = String(anchor.closest("li")?.innerText || "").replace(/\s+/g, " ");
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
    const canonical = document.querySelector('link[rel="canonical"]')?.href || location.href;
    const match = /\/event\/([1-9][0-9]*)\/?/.exec(new URL(canonical, location.href).pathname);
    return {
      event_ref: match ? `connpass-event://event/${match[1]}` : null,
      canonical_url: match ? `${new URL(canonical, location.href).origin}/event/${match[1]}/` : null,
      title: event.name || text("h1"),
      summary: event.headline || null,
      description: event.description || text('[class*="description"]'),
      starts_at: event.startDate || null,
      ends_at: event.endDate || null,
      venue_name: locationValue.name || text('[class*="event-place"]'),
      address: typeof addressValue === "string" ? addressValue
        : [addressValue.streetAddress, addressValue.addressLocality, addressValue.addressRegion]
          .filter(Boolean).join(" ") || null,
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
  readCalendarBindings,
  readEventDetail,
};
