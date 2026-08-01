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

function normalizeLumaCandidate(input = {}) {
  const identity = lumaEventIdentity(input.href);
  const title = boundedText(input.title, 300);
  const cardText = boundedText(input.cardText, 4000);
  const timelineText = boundedText(input.timelineText, 8000);
  if (!identity || !title || !cardText || !timelineText) return null;
  const date = timelineText.match(/([0-9]{1,2}月[0-9]{1,2}日(?:\s+[^\s]+曜日)?)/);
  const time = cardText.match(/(?:^|\s)([0-2]?[0-9]:[0-5][0-9])(?:\s|$)/);
  return Object.freeze({
    provider: "luma",
    canonical_url: identity.canonicalUrl,
    event_ref: `luma-event://event/${identity.slug}`,
    title,
    date_label: date ? date[1] : "",
    time_label: time ? time[1] : "",
    discovery_text: cardText,
  });
}

async function collectLumaInventory(options = {}) {
  const readSnapshot = options.readSnapshot;
  const advance = options.advance;
  const maxRounds = Number(options.maxRounds || 60);
  const stableEndRounds = Number(options.stableEndRounds || 3);
  if (
    typeof readSnapshot !== "function"
    || typeof advance !== "function"
    || !Number.isInteger(maxRounds)
    || maxRounds < 1
    || maxRounds > 200
    || !Number.isInteger(stableEndRounds)
    || stableEndRounds < 1
    || stableEndRounds > 10
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
      const candidate = normalizeLumaCandidate(raw);
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
  }));
}

module.exports = {
  collectLumaInventory,
  discoverLumaTokyo,
  lumaEventIdentity,
  normalizeLumaCandidate,
  readLumaTimelineSnapshot,
  advanceLumaTimeline,
};
