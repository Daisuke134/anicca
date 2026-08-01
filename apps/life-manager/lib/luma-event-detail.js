"use strict";

const { lumaEventIdentity } = require("./luma-discovery.js");

const ATTENDANCE = new Map([
  ["https://schema.org/OfflineEventAttendanceMode", "in_person"],
  ["https://schema.org/OnlineEventAttendanceMode", "online"],
  ["https://schema.org/MixedEventAttendanceMode", "hybrid"],
]);
const EVENT_STATUS = new Map([
  ["https://schema.org/EventScheduled", "scheduled"],
  ["https://schema.org/EventCancelled", "cancelled"],
  ["https://schema.org/EventPostponed", "postponed"],
  ["https://schema.org/EventRescheduled", "rescheduled"],
]);

function bounded(value, max = 500) {
  const text = String(value == null ? "" : value).replace(/\s+/g, " ").trim();
  return text && text.length <= max ? text : "";
}

function explicitDate(value) {
  const text = bounded(value, 100);
  if (!text || !/[zZ]|[+-][0-9]{2}:[0-9]{2}$/.test(text)) return null;
  const time = Date.parse(text);
  return Number.isFinite(time) ? new Date(time).toISOString() : null;
}

function normalizedControls(value) {
  if (!Array.isArray(value)) return new Set();
  return new Set(value.map((item) => bounded(item, 200).toLowerCase()).filter(Boolean));
}

function includesAny(controls, values) {
  return values.some((value) => controls.has(value));
}

function rsvpStatus(controls) {
  if (includesAny(controls, [
    "参加予定",
    "登録済み",
    "マイチケット",
    "my ticket",
    "you're going",
    "you’re going",
    "going",
  ])) {
    return "registered";
  }
  const inPersonTickets = [...controls].filter((value) => (
    /(?:会場参加|現地参加|in[ -]?person|on[ -]?site)/i.test(value)
  ));
  if (
    inPersonTickets.length > 0
    && inPersonTickets.every((value) => /(?:売り切れ|満席|sold out)/i.test(value))
  ) {
    return "full";
  }
  if (includesAny(controls, ["sold out", "満席"])) return "full";
  if (includesAny(controls, ["join waitlist", "キャンセル待ちに登録", "キャンセル待ち"])) {
    return "waitlist";
  }
  if (includesAny(controls, ["request to join", "参加をリクエスト", "承認をリクエスト"])) {
    return "approval_required";
  }
  if (includesAny(controls, ["register", "参加登録", "sign up", "rsvp"])) return "available";
  return "unknown";
}

function normalizeLumaEventDetail(input = {}) {
  const identity = lumaEventIdentity(input.canonicalUrl);
  const rows = Array.isArray(input.jsonLd) ? input.jsonLd : [];
  const event = rows.find((row) => row && row["@type"] === "Event");
  if (!identity || !event) return null;
  const title = bounded(event.name, 300);
  const startsAt = explicitDate(event.startDate);
  const endsAt = explicitDate(event.endDate);
  const attendanceMode = ATTENDANCE.get(event.eventAttendanceMode);
  const eventStatus = EVENT_STATUS.get(event.eventStatus) || "unknown";
  const venueName = bounded(event.location && event.location.name, 500);
  if (
    !title
    || !startsAt
    || !endsAt
    || Date.parse(endsAt) <= Date.parse(startsAt)
    || !attendanceMode
    || !venueName
  ) {
    return null;
  }
  const controls = normalizedControls(input.controls);
  const authStatus = includesAny(controls, ["ログイン", "sign in", "log in"])
    ? "login_required"
    : "unknown";
  return Object.freeze({
    provider: "luma",
    canonical_url: identity.canonicalUrl,
    event_ref: `luma-event://event/${identity.slug}`,
    title,
    starts_at: startsAt,
    ends_at: endsAt,
    attendance_mode: attendanceMode,
    venue_name: venueName,
    event_status: eventStatus,
    auth_status: authStatus,
    rsvp_status: rsvpStatus(controls),
    capacity_status: "availability_control_only",
  });
}

async function readRawLumaEventDetail(page, canonicalUrl) {
  if (!page || typeof page.evaluate !== "function") {
    throw new Error("Luma event page unavailable");
  }
  return page.evaluate((eventUrl) => {
    const rows = [];
    for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
      try {
        const parsed = JSON.parse(script.textContent || "null");
        const values = Array.isArray(parsed) ? parsed : parsed && parsed["@graph"] || [parsed];
        for (const value of values) {
          if (!value || value["@type"] !== "Event") continue;
          rows.push({
            "@type": "Event",
            name: value.name,
            startDate: value.startDate,
            endDate: value.endDate,
            eventAttendanceMode: value.eventAttendanceMode,
            eventStatus: value.eventStatus,
            location: value.location && {
              "@type": value.location["@type"],
              name: value.location.name,
            },
          });
        }
      } catch {
        // Malformed provider metadata is ignored and fails closed during normalization.
      }
    }
    const controls = [...document.querySelectorAll(
      'button, a[role="button"], input[type="submit"]',
    )].map((element) => (
      element.innerText || element.value || element.getAttribute("aria-label") || ""
    )).map((value) => value.replace(/\s+/g, " ").trim()).filter(Boolean).slice(0, 100);
    return { canonicalUrl: eventUrl, jsonLd: rows, controls };
  }, canonicalUrl);
}

async function inspectLumaEvent(options = {}) {
  const dailyDriver = options.dailyDriver;
  const canonicalUrl = String(options.canonicalUrl || "").trim();
  const readRawDetail = options.readRawDetail || readRawLumaEventDetail;
  if (!dailyDriver || typeof dailyDriver.withLumaPage !== "function") {
    throw new Error("Luma daily-driver unavailable");
  }
  const detail = await dailyDriver.withLumaPage(canonicalUrl, async (page) => (
    normalizeLumaEventDetail(await readRawDetail(page, canonicalUrl))
  ));
  if (!detail) throw new Error("Luma provider detail unavailable");
  return detail;
}

module.exports = {
  inspectLumaEvent,
  normalizeLumaEventDetail,
  readRawLumaEventDetail,
};
