"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { deriveAnchors } = require("./care-anchors");

const HOME = "東京都渋谷区神南1-2-3";
const OFFICE = "東京都千代田区丸の内1-1-1 オフィスタワー";

function events(location, startMsList) {
  return startMsList.map((startMs) => ({ location, startMs }));
}

test("home is the given address verbatim and null is allowed", () => {
  assert.equal(deriveAnchors({ homeAddress: HOME, calendarEvents: [], careHistory: [] }).home, HOME);
  assert.equal(deriveAnchors({ homeAddress: null, calendarEvents: [], careHistory: [] }).home, null);
});

test("work requires at least three occurrences of the same non-home location", () => {
  const twice = deriveAnchors({
    homeAddress: HOME,
    calendarEvents: events(OFFICE, [1000, 2000]),
    careHistory: [],
  });
  assert.equal(twice.work, null);

  const thrice = deriveAnchors({
    homeAddress: HOME,
    calendarEvents: events(OFFICE, [1000, 2000, 3000]),
    careHistory: [],
  });
  assert.equal(thrice.work, OFFICE);
});

test("home never becomes work no matter how often it appears", () => {
  const anchors = deriveAnchors({
    homeAddress: HOME,
    calendarEvents: events(HOME, [1000, 2000, 3000, 4000]),
    careHistory: [],
  });
  assert.equal(anchors.work, null);
});

test("work frequency ties break by most recent occurrence", () => {
  const gymLatest = "東京都新宿区西新宿2-2-2 ジム";
  const anchors = deriveAnchors({
    homeAddress: HOME,
    calendarEvents: [
      ...events(OFFICE, [1000, 2000, 3000]),
      ...events(gymLatest, [1500, 2500, 9000]),
    ],
    careHistory: [],
  });
  assert.equal(anchors.work, gymLatest);
});

test("the most frequent location wins even when a rarer one is more recent", () => {
  const rare = "東京都港区六本木3-3-3";
  const anchors = deriveAnchors({
    homeAddress: HOME,
    calendarEvents: [
      ...events(OFFICE, [1000, 2000, 3000, 4000]),
      ...events(rare, [9000, 9500, 9900]),
    ],
    careHistory: [],
  });
  assert.equal(anchors.work, OFFICE);
});

test("usual providers need at least two visits per care type, ties break by recency", () => {
  const anchors = deriveAnchors({
    homeAddress: HOME,
    calendarEvents: [],
    careHistory: [
      { careType: "haircut", location: "サロンA", startMs: 1000 },
      { careType: "haircut", location: "サロンA", startMs: 2000 },
      { careType: "haircut", location: "サロンB", startMs: 3000 },
      { careType: "dental", location: "歯科C", startMs: 1000 },
      { careType: "dental", location: "歯科C", startMs: 1500 },
      { careType: "dental", location: "歯科D", startMs: 4000 },
      { careType: "dental", location: "歯科D", startMs: 5000 },
      { careType: "clinic", location: "クリニックE", startMs: 1000 },
    ],
  });
  // haircut: サロンB has only 1 visit — サロンA (2 visits) is the usual shop.
  // dental: C and D both have 2 visits — D is more recent, D wins.
  // clinic: single visit — no usual provider.
  assert.deepEqual(anchors.usualProviders, [
    { careType: "dental", location: "歯科D" },
    { careType: "haircut", location: "サロンA" },
  ]);
});

test("empty inputs produce empty anchors, not errors", () => {
  assert.deepEqual(deriveAnchors({}), { home: null, work: null, usualProviders: [] });
});
