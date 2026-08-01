"use strict";

const RESERVED_SLUGS = new Set([
  "app",
  "calendar",
  "discover",
  "help",
  "home",
  "pricing",
  "signin",
]);
const SLUG = /^[A-Za-z0-9_-]+$/;
const TOKYO_DISCOVER_URL = "https://luma.com/tokyo?k=p";

function boundedText(value, max) {
  const text = String(value == null ? "" : value).replace(/\s+/g, " ").trim();
  return text && text.length <= max ? text : "";
}

function tokyoDate(value) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(value);
  const map = Object.fromEntries(parts.map(({ type, value: part }) => [type, part]));
  return `${map.year}-${map.month}-${map.day}`;
}

function addDateDays(date, count) {
  const [year, month, day] = date.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day + count)).toISOString().slice(0, 10);
}

function resolveLumaDateLabel(labelValue, nowValue) {
  const label = boundedText(labelValue, 100);
  const nowMs = Date.parse(String(nowValue == null ? "" : nowValue));
  if (!label || !Number.isFinite(nowMs)) return "";
  const today = tokyoDate(new Date(nowMs));
  if (/^今日(?:\s|$)/.test(label)) return today;
  if (/^明日(?:\s|$)/.test(label)) return addDateDays(today, 1);
  const match = label.match(/(\d{1,2})月(\d{1,2})日/);
  if (!match) return "";
  const month = Number(match[1]);
  const day = Number(match[2]);
  let year = Number(today.slice(0, 4));
  const make = () => `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  let candidate = make();
  if (candidate < today) {
    year += 1;
    candidate = make();
  }
  const parsed = new Date(`${candidate}T00:00:00Z`);
  if (!Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== candidate) return "";
  return candidate;
}

function lumaEventIdentity(value) {
  let url;
  try {
    url = new URL(String(value == null ? "" : value).trim());
  } catch {
    return null;
  }
  const host = url.hostname.toLowerCase();
  const parts = url.pathname.split("/").filter(Boolean);
  if (
    url.protocol !== "https:"
    || url.username
    || url.password
    || !["luma.com", "www.luma.com", "lu.ma"].includes(host)
    || parts.length !== 1
    || !SLUG.test(parts[0])
    || RESERVED_SLUGS.has(parts[0].toLowerCase())
  ) {
    return null;
  }
  return {
    slug: parts[0],
    canonicalUrl: `https://luma.com/${parts[0]}`,
  };
}

function normalizeLumaCandidate(input = {}, options = {}) {
  const identity = lumaEventIdentity(input.href);
  const title = boundedText(input.title, 300);
  const cardText = boundedText(input.cardText, 4000);
  const timelineText = boundedText(input.timelineText, 8000);
  if (!identity || !title || !cardText || !timelineText) return null;
  const explicitDate = boundedText(input.dateLabel, 100);
  const date = timelineText.match(/(今日|明日|[0-9]{1,2}月[0-9]{1,2}日)(?:\s+[^\s]+曜日)?/);
  const dateLabel = explicitDate || (date ? date[0] : "");
  const time = cardText.match(/(?:^|\s)([0-2]?[0-9]:[0-5][0-9])(?:\s|$)/);
  return Object.freeze({
    provider: "luma",
    canonical_url: identity.canonicalUrl,
    event_ref: `luma-event://event/${identity.slug}`,
    title,
    date_label: dateLabel,
    event_date: resolveLumaDateLabel(dateLabel, options.now),
    time_label: time ? time[1] : "",
    discovery_text: cardText,
    attendance_mode: "in_person",
    location_scope: "tokyo",
  });
}

async function collectLumaInventory(options = {}) {
  const readSnapshot = options.readSnapshot;
  const advance = options.advance;
  const maxRounds = Number(options.maxRounds || 60);
  const stableEndRounds = Number(options.stableEndRounds || 3);
  const now = String(options.now == null ? "" : options.now).trim();
  if (
    typeof readSnapshot !== "function"
    || typeof advance !== "function"
    || !Number.isInteger(maxRounds)
    || maxRounds < 1
    || maxRounds > 200
    || !Number.isInteger(stableEndRounds)
    || stableEndRounds < 1
    || stableEndRounds > 10
    || !Number.isFinite(Date.parse(now))
  ) {
    throw new Error("Luma discovery configuration invalid");
  }

  const candidates = new Map();
  let stableRounds = 0;
  let previousHeight = null;
  for (let round = 1; round <= maxRounds; round += 1) {
    const snapshot = await readSnapshot();
    if (!Array.isArray(snapshot)) throw new Error("Luma discovery snapshot invalid");
    let added = 0;
    for (const raw of snapshot) {
      const candidate = normalizeLumaCandidate(raw, { now });
      if (!candidate || candidates.has(candidate.canonical_url)) continue;
      candidates.set(candidate.canonical_url, candidate);
      added += 1;
    }

    const state = await advance();
    const height = Number(state && state.scrollHeight);
    const stableHeight = Number.isFinite(height) && height === previousHeight;
    if (state && state.atEnd === true && added === 0 && stableHeight) {
      stableRounds += 1;
    } else {
      stableRounds = 0;
    }
    previousHeight = Number.isFinite(height) ? height : null;
    if (stableRounds >= stableEndRounds) {
      return Object.freeze({
        complete: true,
        rounds: round,
        candidates: Object.freeze([...candidates.values()]),
      });
    }
  }
  throw new Error("Luma inventory end unproven");
}

async function readLumaTimelineSnapshot(page) {
  if (!page || typeof page.evaluate !== "function") {
    throw new Error("Luma discovery page unavailable");
  }
  const snapshot = await page.evaluate(() => (
    [...document.querySelectorAll("a.event-link.content-link[href]")].map((link) => {
      const card = link.closest(".content-card");
      const timeline = link.closest(".timeline-section");
      return {
        href: link.href,
        title: link.getAttribute("aria-label") || "",
        cardText: card && card.innerText || "",
        timelineText: timeline && timeline.innerText || "",
        dateLabel: timeline && timeline.querySelector(".timeline-title .date")?.textContent || "",
      };
    })
  ));
  if (!Array.isArray(snapshot)) throw new Error("Luma discovery snapshot invalid");
  return snapshot;
}

async function advanceLumaTimeline(page) {
  if (
    !page
    || typeof page.evaluate !== "function"
    || typeof page.waitForTimeout !== "function"
  ) {
    throw new Error("Luma discovery page unavailable");
  }
  await page.evaluate(() => {
    const root = document.scrollingElement || document.documentElement;
    root.scrollTo(0, root.scrollHeight);
  });
  await page.waitForTimeout(1000);
  return page.evaluate(() => {
    const root = document.scrollingElement || document.documentElement;
    return {
      atEnd: root.scrollTop + window.innerHeight >= root.scrollHeight - 2,
      scrollHeight: root.scrollHeight,
    };
  });
}

async function discoverLumaTokyo(options = {}) {
  const dailyDriver = options.dailyDriver;
  if (!dailyDriver || typeof dailyDriver.withLumaPage !== "function") {
    throw new Error("Luma daily-driver unavailable");
  }
  const readSnapshot = options.readSnapshot || readLumaTimelineSnapshot;
  const advance = options.advance || advanceLumaTimeline;
  return dailyDriver.withLumaPage(TOKYO_DISCOVER_URL, (page) => collectLumaInventory({
    readSnapshot: () => readSnapshot(page),
    advance: () => advance(page),
    maxRounds: options.maxRounds,
    stableEndRounds: options.stableEndRounds,
    now: options.now,
  }));
}

function buildLumaDailyInventory(inventory, coverage) {
  if (!inventory || inventory.complete !== true || !Number.isInteger(inventory.rounds)) {
    throw new Error("Luma daily inventory incomplete");
  }
  if (!coverage || !Array.isArray(coverage.days) || coverage.days.length !== 21) {
    throw new Error("Luma daily inventory coverage invalid");
  }
  const dates = coverage.days.map(({ date }) => String(date || ""));
  if (dates[0] !== coverage.window_start || dates[20] !== coverage.window_end) {
    throw new Error("Luma daily inventory coverage invalid");
  }
  for (let index = 0; index < dates.length; index += 1) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(dates[index]) || (index > 0 && dates[index] !== addDateDays(dates[index - 1], 1))) {
      throw new Error("Luma daily inventory coverage invalid");
    }
  }
  if (!Array.isArray(inventory.candidates) || inventory.candidates.some(({ event_date: date }) => !/^\d{4}-\d{2}-\d{2}$/.test(String(date || "")))) {
    throw new Error("Luma daily inventory date unresolved");
  }
  const byDate = new Map(dates.map((date) => [date, []]));
  let outside = 0;
  for (const candidate of inventory.candidates) {
    const row = byDate.get(candidate.event_date);
    if (row) row.push(candidate.event_ref);
    else outside += 1;
  }
  const days = dates.map((date) => {
    const eventRefs = [...new Set(byDate.get(date))].sort();
    return Object.freeze({ date, complete: true, candidate_count: eventRefs.length, event_refs: Object.freeze(eventRefs) });
  });
  return Object.freeze({
    schema_version: 1,
    source_url: TOKYO_DISCOVER_URL,
    source_scope: "tokyo_in_person_main",
    global_end_proven: true,
    rounds: inventory.rounds,
    window_start: dates[0],
    window_end: dates[20],
    days: Object.freeze(days),
    in_window_candidate_count: days.reduce((sum, day) => sum + day.candidate_count, 0),
    out_of_window_candidate_count: outside,
  });
}

module.exports = {
  collectLumaInventory,
  buildLumaDailyInventory,
  discoverLumaTokyo,
  lumaEventIdentity,
  normalizeLumaCandidate,
  resolveLumaDateLabel,
  readLumaTimelineSnapshot,
  advanceLumaTimeline,
};
