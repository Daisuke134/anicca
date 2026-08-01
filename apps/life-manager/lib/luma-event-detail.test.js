"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  inspectLumaEvent,
  normalizeLumaEventDetail,
} = require("./luma-event-detail.js");

function fixture(overrides = {}) {
  return {
    canonicalUrl: "https://luma.com/h8157e6c",
    jsonLd: [{
      "@type": "Event",
      name: "HYPER COASTER BEER RUN",
      startDate: "2026-08-02T09:30:00.000+09:00",
      endDate: "2026-08-02T12:00:00.000+09:00",
      eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
      eventStatus: "https://schema.org/EventScheduled",
      location: {
        "@type": "Place",
        name: "コースター・クラフトビール＆キッチン",
      },
    }],
    controls: ["ログイン", "参加登録", "ホストに連絡"],
    ...overrides,
  };
}

test("normalizes scheduled in-person detail and separates login from RSVP availability", () => {
  assert.deepEqual(normalizeLumaEventDetail(fixture()), {
    provider: "luma",
    canonical_url: "https://luma.com/h8157e6c",
    event_ref: "luma-event://event/h8157e6c",
    title: "HYPER COASTER BEER RUN",
    starts_at: "2026-08-02T00:30:00.000Z",
    ends_at: "2026-08-02T03:00:00.000Z",
    attendance_mode: "in_person",
    venue_name: "コースター・クラフトビール＆キッチン",
    event_status: "scheduled",
    auth_status: "login_required",
    rsvp_status: "available",
    capacity_status: "availability_control_only",
  });
});

test("keeps online events visible but marks them as not in-person", () => {
  const online = fixture({
    jsonLd: [{
      ...fixture().jsonLd[0],
      eventAttendanceMode: "https://schema.org/OnlineEventAttendanceMode",
      location: { "@type": "VirtualLocation", name: "Online" },
    }],
    controls: ["Register"],
  });

  assert.equal(normalizeLumaEventDetail(online).attendance_mode, "online");
  assert.equal(normalizeLumaEventDetail(online).rsvp_status, "available");
  assert.equal(normalizeLumaEventDetail(online).auth_status, "unknown");
});

test("classifies registered, waitlist, full, approval, and unknown controls exactly", () => {
  assert.equal(normalizeLumaEventDetail(fixture({ controls: ["参加予定"] })).rsvp_status, "registered");
  assert.equal(normalizeLumaEventDetail(fixture({ controls: ["Join Waitlist"] })).rsvp_status, "waitlist");
  assert.equal(normalizeLumaEventDetail(fixture({ controls: ["Sold Out"] })).rsvp_status, "full");
  assert.equal(normalizeLumaEventDetail(fixture({ controls: ["Request to Join"] })).rsvp_status, "approval_required");
  assert.equal(normalizeLumaEventDetail(fixture({ controls: ["ホストに連絡"] })).rsvp_status, "unknown");
});

test("hybrid event with a sold-out venue ticket is full even when online registration remains", () => {
  const detail = normalizeLumaEventDetail(fixture({
    controls: [
      "会場参加 売り切れ 無料",
      "オンライン参加 無料",
      "参加登録",
    ],
  }));

  assert.equal(detail.rsvp_status, "full");
});

test("rejects malformed provider detail instead of inventing date or venue", () => {
  assert.equal(normalizeLumaEventDetail(fixture({ jsonLd: [] })), null);
  assert.equal(normalizeLumaEventDetail(fixture({
    jsonLd: [{ ...fixture().jsonLd[0], startDate: "tomorrow" }],
  })), null);
  assert.equal(normalizeLumaEventDetail(fixture({
    canonicalUrl: "https://example.com/event",
  })), null);
});

test("event inspection uses the shared daily-driver and normalizes the provider readback", async () => {
  const calls = [];
  const page = { id: "owned-page" };
  const dailyDriver = {
    async withLumaPage(url, task) {
      calls.push(["withLumaPage", url]);
      return task(page);
    },
  };
  const detail = await inspectLumaEvent({
    dailyDriver,
    canonicalUrl: "https://luma.com/h8157e6c",
    readRawDetail: async (seenPage) => {
      assert.equal(seenPage, page);
      return fixture();
    },
  });

  assert.deepEqual(calls, [["withLumaPage", "https://luma.com/h8157e6c"]]);
  assert.equal(detail.event_ref, "luma-event://event/h8157e6c");
  assert.equal(detail.attendance_mode, "in_person");
});
