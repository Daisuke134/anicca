"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { buildRollingEventCoverage } = require("./rolling-event-coverage.js");
const { collectLumaInventory } = require("./luma-discovery.js");
const { normalizeLumaEventDetail } = require("./luma-event-detail.js");
const {
  buildLumaDateInventory,
  inspectLumaDateInventory,
  isVerifiedLumaDateInventory,
} = require("./luma-date-inventory.js");

const COVERAGE = buildRollingEventCoverage({
  tenantId: "dais-local",
  timeZone: "Asia/Tokyo",
  now: "2026-08-01T16:00:00.000Z",
  resolvedDays: [],
});

function rawCard(slug) {
  return {
    href: `https://luma.com/${slug}`,
    title: `Event ${slug}`,
    cardText: `Event ${slug} 19:00`,
    timelineText: "8月2日 日曜日",
  };
}

async function verifiedInventory(slugs = ["tokyo-one", "tokyo-two", "tokyo-three"]) {
  let round = 0;
  return collectLumaInventory({
    readSnapshot: async () => {
      round += 1;
      return round === 1 ? slugs.map(rawCard) : [];
    },
    advance: async () => ({ atEnd: true, scrollHeight: 100 }),
    stableEndRounds: 1,
  });
}

function detail(slug, overrides = {}) {
  return normalizeLumaEventDetail({
    canonicalUrl: `https://luma.com/${slug}`,
    jsonLd: [{
      "@type": "Event",
      name: `Event ${slug}`,
      startDate: "2026-08-02T00:30:00.000Z",
      endDate: "2026-08-02T02:00:00.000Z",
      eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
      eventStatus: "https://schema.org/EventScheduled",
      location: { "@type": "Place", name: "Tokyo venue" },
      description: `Public description for ${slug}`,
      organizer: [{ "@type": "Organization", name: `Organizer ${slug}` }],
      attendee: [],
      ...overrides,
    }],
    controls: ["Register"],
  });
}

test("projects every verified detail into all 21 dates using the coverage timezone", async () => {
  const inventory = await verifiedInventory();
  const details = [
    detail("tokyo-one"),
    detail("tokyo-two", {
      startDate: "2026-08-22T14:30:00.000Z",
      endDate: "2026-08-22T15:30:00.000Z",
    }),
    detail("tokyo-three", {
      eventAttendanceMode: "https://schema.org/OnlineEventAttendanceMode",
      location: { "@type": "VirtualLocation", name: "Online" },
    }),
  ];
  const snapshot = buildLumaDateInventory({
    coverage: COVERAGE,
    inventory,
    details,
    now: "2026-08-02T01:00:00.000Z",
  });

  assert.equal(snapshot.complete, true);
  assert.equal(snapshot.days.length, 21);
  assert.deepEqual(snapshot.days.map((day) => day.date), COVERAGE.days.map((day) => day.date));
  assert.equal(snapshot.days[0].events[0].event_ref, "luma-event://event/tokyo-one");
  assert.equal(snapshot.days[0].events[0].description, "Public description for tokyo-one");
  assert.deepEqual(snapshot.days[0].events[0].organizer_names, ["Organizer tokyo-one"]);
  assert.equal(snapshot.days[0].events[0].participant_visibility, "unavailable");
  assert.equal(snapshot.days.at(-1).events[0].event_ref, "luma-event://event/tokyo-two");
  assert.deepEqual(snapshot.counts, {
    discovered: 3,
    inspected: 3,
    scheduled_in_person_in_window: 2,
    excluded: 1,
    dates_with_candidates: 2,
    dates_without_candidates: 19,
  });
  assert.match(snapshot.inventory_snapshot_id, /^luma-date-inventory:[0-9a-f]{64}$/);
  assert.equal(Object.isFrozen(snapshot), true);
  assert.equal(isVerifiedLumaDateInventory(snapshot), true);
  assert.equal(isVerifiedLumaDateInventory(structuredClone(snapshot)), false);
});

test("fails closed for fabricated provenance, missing details, duplicates, or URL mismatch", async () => {
  const inventory = await verifiedInventory(["tokyo-one", "tokyo-two"]);
  const one = detail("tokyo-one");
  const two = detail("tokyo-two");
  const cases = [
    { coverage: structuredClone(COVERAGE), inventory, details: [one, two] },
    { coverage: COVERAGE, inventory: structuredClone(inventory), details: [one, two] },
    { coverage: COVERAGE, inventory, details: [structuredClone(one), two] },
    { coverage: COVERAGE, inventory, details: [one] },
    { coverage: COVERAGE, inventory, details: [one, one] },
    { coverage: COVERAGE, inventory, details: [one, detail("tokyo-other")] },
  ];
  for (const input of cases) {
    assert.throws(() => buildLumaDateInventory({
      ...input,
      now: "2026-08-02T01:00:00.000Z",
    }), /Luma date inventory invalid/i);
  }
});

test("reads every discovered detail sequentially before building the snapshot", async () => {
  const inventory = await verifiedInventory(["tokyo-one", "tokyo-two"]);
  const calls = [];
  const snapshot = await inspectLumaDateInventory({
    coverage: COVERAGE,
    now: "2026-08-02T01:00:00.000Z",
    discoverTokyo: async () => {
      calls.push("discover");
      return inventory;
    },
    inspectEvent: async (url) => {
      calls.push(url);
      return detail(url.split("/").at(-1));
    },
  });

  assert.deepEqual(calls, [
    "discover",
    "https://luma.com/tokyo-one",
    "https://luma.com/tokyo-two",
  ]);
  assert.equal(snapshot.counts.inspected, 2);
});

test("does not convert a fully read zero-candidate date into coverage resolution", async () => {
  const inventory = await verifiedInventory(["tokyo-one"]);
  const snapshot = buildLumaDateInventory({
    coverage: COVERAGE,
    inventory,
    details: [detail("tokyo-one")],
    now: "2026-08-02T01:00:00.000Z",
  });
  assert.deepEqual(snapshot.days[1], {
    date: "2026-08-03",
    inventory_status: "complete",
    events: [],
  });
  assert.equal(COVERAGE.days[1].status, "open");
});
