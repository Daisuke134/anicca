"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { searchCareCandidates, CATEGORY_KEYWORDS } = require("./care-candidate-search");

const HOME = "東京都渋谷区神南1-2-3";
const WORK = "東京都千代田区丸の内1-1-1";
const HOME_POINT = { lat: 35.6595, lng: 139.7005 };
const WORK_POINT = { lat: 35.6812, lng: 139.7671 };
const KYOTO_POINT = { lat: 35.0116, lng: 135.7681 }; // ~370km from both anchors

function place(placeId, name, point) {
  return { place_id: placeId, name, geometry: { location: point } };
}

// Fake Google Places API: text search dispatches on the query string
// (anchor geocoding, usual-provider resolution, and keyword discovery all go
// through the same Text Search endpoint), details dispatches on place_id.
function makePlacesApi({ geocodes = {}, searches = {}, details = {} }) {
  const queries = [];
  const fetchImpl = async (rawUrl) => {
    const url = new URL(rawUrl);
    const respond = (body) => ({ ok: true, json: async () => body });
    if (url.pathname.endsWith("/textsearch/json")) {
      const query = url.searchParams.get("query");
      queries.push(query);
      if (geocodes[query]) {
        return respond({
          status: "OK",
          results: [place(`geocode:${query}`, query, geocodes[query])],
        });
      }
      return respond({ status: "OK", results: searches[query] || [] });
    }
    if (url.pathname.endsWith("/details/json")) {
      const result = details[url.searchParams.get("place_id")];
      return respond(result ? { status: "OK", result } : { status: "NOT_FOUND" });
    }
    throw new Error(`unexpected url: ${rawUrl}`);
  };
  return { fetchImpl, queries };
}

test("a candidate outside both anchor radii is rejected even when the API returns it first", async () => {
  const keyword = CATEGORY_KEYWORDS.haircut;
  const { fetchImpl } = makePlacesApi({
    geocodes: { [HOME]: HOME_POINT, [WORK]: WORK_POINT },
    searches: {
      [keyword]: [
        place("kyoto-barber", "京都の床屋", KYOTO_POINT),
        place("tokyo-barber-1", "渋谷サロン1", { lat: 35.66, lng: 139.701 }),
        place("tokyo-barber-2", "丸の内サロン2", { lat: 35.6815, lng: 139.7675 }),
      ],
    },
    details: {
      "kyoto-barber": { website: "https://kyoto-barber.example/" },
      "tokyo-barber-1": { website: "https://tokyo1.example/" },
      "tokyo-barber-2": { website: "https://tokyo2.example/" },
    },
  });
  const receipt = await searchCareCandidates({
    category: "haircut",
    anchors: { home: HOME, work: WORK, usualProviders: [] },
    apiKey: "test-key",
    fetchImpl,
  });
  const ids = receipt.definitions.map((d) => d.providerId);
  assert.ok(!ids.includes("kyoto-barber"), "Kyoto barber must never reach a Tokyo user's list");
  assert.deepEqual(ids.sort(), ["tokyo-barber-1", "tokyo-barber-2"]);
});

test("a usual provider matching the category comes first regardless of distance", async () => {
  const keyword = CATEGORY_KEYWORDS.haircut;
  const usualLocation = "いつものサロン 渋谷";
  const { fetchImpl } = makePlacesApi({
    geocodes: { [HOME]: HOME_POINT },
    searches: {
      [usualLocation]: [
        // The usual shop sits far outside the discovery radius — it still wins.
        place("usual-salon", "いつものサロン", { lat: 35.7, lng: 139.8 }),
      ],
      [keyword]: [
        place("near-1", "至近サロン1", { lat: 35.6596, lng: 139.7006 }),
        place("near-2", "至近サロン2", { lat: 35.6597, lng: 139.7007 }),
      ],
    },
    details: {
      "usual-salon": { website: "https://usual-salon.example/" },
      "near-1": { website: "https://near1.example/" },
      "near-2": { website: "https://near2.example/" },
    },
  });
  const receipt = await searchCareCandidates({
    category: "haircut",
    anchors: { home: HOME, work: null, usualProviders: [{ careType: "haircut", location: usualLocation }] },
    apiKey: "test-key",
    fetchImpl,
  });
  assert.equal(receipt.definitions.length, 3);
  assert.equal(receipt.definitions[0].providerId, "usual-salon");
  assert.equal(receipt.definitions[0].usualProvider, true);
  assert.equal(receipt.definitions[0].proximityRank, 1);
  assert.deepEqual(receipt.definitions.slice(1).map((d) => d.usualProvider), [false, false]);
  assert.equal(receipt.shortfallReason, null);
});

test("a usual provider for a DIFFERENT category is ignored", async () => {
  const keyword = CATEGORY_KEYWORDS.haircut;
  const { fetchImpl, queries } = makePlacesApi({
    geocodes: { [HOME]: HOME_POINT },
    searches: {
      [keyword]: [place("near-1", "サロン1", { lat: 35.6596, lng: 139.7006 })],
    },
    details: { "near-1": { website: "https://near1.example/" } },
  });
  const receipt = await searchCareCandidates({
    category: "haircut",
    anchors: { home: HOME, work: null, usualProviders: [{ careType: "dental", location: "いつもの歯科" }] },
    apiKey: "test-key",
    fetchImpl,
  });
  assert.ok(!queries.includes("いつもの歯科"), "dental usual provider must not be resolved for a haircut search");
  assert.deepEqual(receipt.definitions.map((d) => d.usualProvider), [false]);
});

test("work anchor carries the search when home is null", async () => {
  const keyword = CATEGORY_KEYWORDS.dental;
  const { fetchImpl, queries } = makePlacesApi({
    geocodes: { [WORK]: WORK_POINT },
    searches: {
      [keyword]: [place("work-dental", "丸の内歯科", { lat: 35.6813, lng: 139.7672 })],
    },
    details: { "work-dental": { website: "https://work-dental.example/" } },
  });
  const receipt = await searchCareCandidates({
    category: "dental",
    anchors: { home: null, work: WORK, usualProviders: [] },
    apiKey: "test-key",
    fetchImpl,
  });
  assert.ok(queries.includes(WORK), "work address must be geocoded");
  assert.deepEqual(receipt.definitions.map((d) => d.providerId), ["work-dental"]);
});

test("the query is bound to the detected category keyword — a haircut search never queries dental", async () => {
  const { fetchImpl, queries } = makePlacesApi({
    geocodes: { [HOME]: HOME_POINT },
    searches: {},
    details: {},
  });
  await searchCareCandidates({
    category: "haircut",
    anchors: { home: HOME, work: null, usualProviders: [] },
    apiKey: "test-key",
    fetchImpl,
  });
  const discoveryQueries = queries.filter((q) => q !== HOME);
  assert.ok(discoveryQueries.length > 0, "at least one discovery query must be issued");
  assert.ok(discoveryQueries.every((q) => q.includes("美容")), `haircut queries must carry the haircut keyword, got: ${discoveryQueries}`);
  assert.ok(discoveryQueries.every((q) => !q.includes("歯科")), "haircut search must never query dental");
});

test("an unknown category fails closed instead of searching for nothing", async () => {
  await assert.rejects(
    () => searchCareCandidates({
      category: "yoga",
      anchors: { home: HOME, work: null, usualProviders: [] },
      apiKey: "test-key",
      fetchImpl: async () => { throw new Error("must not be called"); },
    }),
    /unknown care category/,
  );
});

test("a result without an official website is dropped (route judgment needs the URL)", async () => {
  const keyword = CATEGORY_KEYWORDS.haircut;
  const { fetchImpl } = makePlacesApi({
    geocodes: { [HOME]: HOME_POINT },
    searches: {
      [keyword]: [
        place("no-site", "サイト無し店", { lat: 35.6596, lng: 139.7006 }),
        place("with-site", "サイト有り店", { lat: 35.6597, lng: 139.7007 }),
      ],
    },
    details: {
      "no-site": {}, // exists but has no website field
      "with-site": { website: "https://with-site.example/" },
    },
  });
  const receipt = await searchCareCandidates({
    category: "haircut",
    anchors: { home: HOME, work: null, usualProviders: [] },
    apiKey: "test-key",
    fetchImpl,
  });
  assert.deepEqual(receipt.definitions.map((d) => d.providerId), ["with-site"]);
});

test("fewer than three candidates is reported honestly, never padded", async () => {
  const keyword = CATEGORY_KEYWORDS.haircut;
  const { fetchImpl } = makePlacesApi({
    geocodes: { [HOME]: HOME_POINT },
    searches: {
      [keyword]: [place("only-one", "唯一のサロン", { lat: 35.6596, lng: 139.7006 })],
    },
    details: { "only-one": { website: "https://only-one.example/" } },
  });
  const receipt = await searchCareCandidates({
    category: "haircut",
    anchors: { home: HOME, work: null, usualProviders: [] },
    apiKey: "test-key",
    fetchImpl,
  });
  assert.equal(receipt.definitions.length, 1);
  assert.equal(typeof receipt.shortfallReason, "string");
  assert.ok(receipt.shortfallReason.length > 0);
});

test("no resolvable anchors means an empty honest result, not a global search", async () => {
  const { fetchImpl, queries } = makePlacesApi({ geocodes: {}, searches: {}, details: {} });
  const receipt = await searchCareCandidates({
    category: "haircut",
    anchors: { home: null, work: null, usualProviders: [] },
    apiKey: "test-key",
    fetchImpl,
  });
  assert.deepEqual(receipt.definitions, []);
  assert.equal(typeof receipt.shortfallReason, "string");
  assert.deepEqual(queries, [], "no anchor means no discovery query at all");
});

test("definitions carry exactly the shape evaluateCareCandidates consumes", async () => {
  const keyword = CATEGORY_KEYWORDS.clinic;
  const { fetchImpl } = makePlacesApi({
    geocodes: { [HOME]: HOME_POINT },
    searches: {
      [keyword]: [place("c1", "クリニック1", { lat: 35.6596, lng: 139.7006 })],
    },
    details: { c1: { website: "https://c1.example/" } },
  });
  const receipt = await searchCareCandidates({
    category: "clinic",
    anchors: { home: HOME, work: null, usualProviders: [] },
    apiKey: "test-key",
    fetchImpl,
  });
  assert.deepEqual(Object.keys(receipt.definitions[0]).sort(), [
    "officialUrl", "providerId", "proximityRank", "publicName", "usualProvider",
  ]);
});
